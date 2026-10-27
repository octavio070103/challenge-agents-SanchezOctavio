"""Modelos de datos para el dominio de reservas."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional, Any, Dict


class EstadoReserva(str, Enum):
    """Estados posibles para una reserva."""
    ACTIVA = "ACTIVA"
    CANCELADA = "CANCELADA"


@dataclass(frozen=True)
class Unidad:
    """Entidad del inventario fijo de equipos de laboratorio."""
    id: str
    name: str


@dataclass
class Reserva:
    """Entidad que representa una reserva de un equipo de laboratorio."""
    unidad_id: str
    solicitante: str
    fecha_inicio: datetime
    fecha_fin: datetime
    estado: str = EstadoReserva.ACTIVA.value
    id: Optional[int] = None

    @property
    def inicio(self) -> datetime:
        """Alias para fecha_inicio."""
        return self.fecha_inicio

    @property
    def fin(self) -> datetime:
        """Alias para fecha_fin."""
        return self.fecha_fin

    def to_dict(self) -> Dict[str, Any]:
        """Convierte la reserva a un diccionario."""
        return {
            "id": self.id,
            "unidad_id": self.unidad_id,
            "solicitante": self.solicitante,
            "fecha_inicio": self.fecha_inicio.strftime("%Y-%m-%dT%H:%M"),
            "fecha_fin": self.fecha_fin.strftime("%Y-%m-%dT%H:%M"),
            "estado": self.estado,
        }
