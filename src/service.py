"""Servicio de lógica de negocio y orquestación para el sistema de reservas."""

from datetime import datetime
from pathlib import Path
from typing import Any, List, Optional, Union
from src.exceptions import (
    ValidationError,
    UnidadNoEncontradaError,
    SolicitanteInvalidoError,
    HorarioInvalidoError,
    SuperposicionError,
    ReservaNotFoundError,
)
from src.inventory import cargar_inventario, DEFAULT_INVENTORY_PATH
from src.models import Reserva, EstadoReserva
from src.repository import ReservaRepository, DEFAULT_DB_PATH


class ReservaService:
    """Gestiona la disponibilidad, validaciones y creación de reservas."""

    def __init__(
        self,
        db_path: Union[str, Path] = DEFAULT_DB_PATH,
        inventory_path: Union[str, Path] = DEFAULT_INVENTORY_PATH,
        repository: Optional[ReservaRepository] = None,
    ):
        self.repository = repository or ReservaRepository(db_path=db_path)
        self.inventory_path = inventory_path
        self._recargar_catalogo()

    def _recargar_catalogo(self) -> None:
        """Carga y actualiza en memoria el catálogo de unidades del laboratorio."""
        self.unidades = cargar_inventario(self.inventory_path)
        self.catalogo_ids = {u.id for u in self.unidades}

    @staticmethod
    def _parse_datetime(val: Any) -> datetime:
        """
        Parsea y valida que la fecha sea un objeto datetime naive en formato local.
        Acepta objetos datetime o cadenas ISO 8601 (YYYY-MM-DDTHH:MM).
        """
        if isinstance(val, datetime):
            if val.tzinfo is not None:
                raise ValidationError("Las fechas deben ser naive (sin zona horaria explícita).")
            return val

        if isinstance(val, str):
            try:
                dt = datetime.fromisoformat(val)
                if dt.tzinfo is not None:
                    raise ValidationError("Las fechas deben ser naive (sin zona horaria explícita).")
                return dt
            except ValueError as e:
                raise ValidationError(f"Formato de fecha inválido. Se espera ISO 8601 ('YYYY-MM-DDTHH:MM'): {e}") from e

        raise ValidationError(f"Tipo de fecha inválido: {type(val)}. Se espera str ISO 8601 o datetime.")

    def _validar_datos(
        self,
        unidad_id: Any,
        solicitante: Any,
        inicio: datetime,
        fin: datetime,
    ) -> None:
        """Ejecuta las validaciones de campos de dominio."""
        if not unidad_id or unidad_id not in self.catalogo_ids:
            raise UnidadNoEncontradaError(
                f"La unidad '{unidad_id}' no existe en el catálogo fijo de equipos."
            )

        if not isinstance(solicitante, str) or not solicitante.strip():
            raise SolicitanteInvalidoError(
                "El campo 'solicitante' debe ser una cadena no vacía y no puede contener solo espacios."
            )

        if inicio >= fin:
            raise HorarioInvalidoError(
                f"La fecha de inicio ({inicio}) debe ser estrictamente anterior a la fecha de fin ({fin})."
            )

    def consultar_disponibilidad(
        self,
        unidad_id: str,
        fecha_inicio: Union[str, datetime],
        fecha_fin: Union[str, datetime],
    ) -> bool:
        """
        Consulta si una unidad física está disponible en el intervalo dado.
        Aplica las reglas de superposición ignorando reservas canceladas.
        """
        inicio = self._parse_datetime(fecha_inicio)
        fin = self._parse_datetime(fecha_fin)
        
        if not unidad_id or unidad_id not in self.catalogo_ids:
            raise UnidadNoEncontradaError(
                f"La unidad '{unidad_id}' no existe en el catálogo fijo de equipos."
            )
            
        if inicio >= fin:
            raise HorarioInvalidoError(
                f"La fecha de inicio ({inicio}) debe ser estrictamente anterior a la fecha de fin ({fin})."
            )

        reservas_activas = self.repository.obtener_activas_por_unidad(unidad_id)
        for r in reservas_activas:
            # Regla de superposición: (inicio_nuevo < fin_existente) AND (fin_nuevo > inicio_existente)
            if inicio < r.fecha_fin and fin > r.fecha_inicio:
                return False

        return True

    def crear_reserva(
        self,
        unidad_id: str,
        solicitante: str,
        fecha_inicio: Union[str, datetime],
        fecha_fin: Union[str, datetime],
    ) -> Reserva:
        """
        Crea y persiste una nueva reserva tras validar todos los campos y solapamientos.
        """
        inicio = self._parse_datetime(fecha_inicio)
        fin = self._parse_datetime(fecha_fin)

        self._validar_datos(
            unidad_id=unidad_id,
            solicitante=solicitante,
            inicio=inicio,
            fin=fin,
        )

        if not self.consultar_disponibilidad(unidad_id, inicio, fin):
            raise SuperposicionError(
                f"Conflicto de horario: La unidad '{unidad_id}' ya posee una reserva activa en el rango solicitado."
            )

        nueva_reserva = Reserva(
            unidad_id=unidad_id,
            solicitante=solicitante.strip(),
            fecha_inicio=inicio,
            fecha_fin=fin,
            estado=EstadoReserva.ACTIVA.value,
        )
        return self.repository.guardar(nueva_reserva)

    def cancelar_reserva(self, reserva_id: int) -> Reserva:
        """
        Cancela una reserva existente, conservando su registro e historial y liberando el horario.
        """
        reserva = self.repository.obtener_por_id(reserva_id)
        if not reserva:
            raise ReservaNotFoundError(f"No existe ninguna reserva con ID {reserva_id}.")

        self.repository.actualizar_estado(reserva_id, EstadoReserva.CANCELADA.value)
        reserva.estado = EstadoReserva.CANCELADA.value
        return reserva

    def obtener_reserva(self, reserva_id: int) -> Optional[Reserva]:
        """Recupera una reserva por ID."""
        return self.repository.obtener_por_id(reserva_id)

    def listar_reservas(
        self, unidad_id: Optional[str] = None, solo_activas: bool = False
    ) -> List[Reserva]:
        """Lista las reservas registradas según filtros."""
        return self.repository.obtener_todas(unidad_id=unidad_id, solo_activas=solo_activas)

    def limpiar_reservas(self) -> None:
        """Elimina todas las reservas registradas en la base de datos sin alterar el inventario."""
        self.repository.limpiar_reservas()
