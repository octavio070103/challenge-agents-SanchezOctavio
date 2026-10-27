import os
import tempfile
import pytest
from datetime import datetime
from src.exceptions import (
    ReservaError,
    ValidationError,
    UnidadNoEncontradaError,
    SolicitanteInvalidoError,
    HorarioInvalidoError,
    SuperposicionError,
    ReservaNotFoundError,
)
from src.models import Reserva, EstadoReserva
from src.inventory import cargar_inventario
from src.repository import ReservaRepository
from src.service import ReservaService


@pytest.fixture
def temp_db_path(tmp_path):
    """Crea una ruta a base de datos SQLite temporal aislada para cada test."""
    db_file = tmp_path / "test_reservas.db"
    return str(db_file)


@pytest.fixture
def service(temp_db_path):
    """Instancia del servicio configurado con inventario real y db temporal."""
    return ReservaService(db_path=temp_db_path, inventory_path="data/inventory.json")


# ==============================================================================
# 1. Carga de Inventario
# ==============================================================================
def test_cargar_inventario_catalogo_fijo():
    """Verifica la carga del inventario desde data/inventory.json."""
    unidades = cargar_inventario("data/inventory.json")
    ids = [u.id for u in unidades]
    assert "MIC-01" in ids
    assert "MIC-02" in ids
    assert "OSC-01" in ids
    assert "MUL-01" in ids
    assert "FUE-01" in ids
    assert len(unidades) == 5


# ==============================================================================
# 2. Creación Válida
# ==============================================================================
def test_creacion_reserva_valida_con_strings_iso(service):
    """Crea una reserva válida pasando fechas en formato ISO 8601."""
    reserva = service.crear_reserva(
        unidad_id="MIC-01",
        solicitante="Investigador Turing",
        fecha_inicio="2026-11-10T10:00",
        fecha_fin="2026-11-10T12:00",
    )
    assert reserva.id is not None
    assert reserva.unidad_id == "MIC-01"
    assert reserva.solicitante == "Investigador Turing"
    assert reserva.fecha_inicio == datetime(2026, 11, 10, 10, 0)
    assert reserva.fecha_fin == datetime(2026, 11, 10, 12, 0)
    assert reserva.estado == EstadoReserva.ACTIVA.value


def test_creacion_reserva_valida_con_objetos_datetime(service):
    """Crea una reserva válida usando directamente objetos datetime naive."""
    inicio = datetime(2026, 11, 10, 14, 0)
    fin = datetime(2026, 11, 10, 16, 0)
    reserva = service.crear_reserva(
        unidad_id="OSC-01",
        solicitante="Dra. Lovelace",
        fecha_inicio=inicio,
        fecha_fin=fin,
    )
    assert reserva.id is not None
    assert reserva.unidad_id == "OSC-01"
    assert reserva.fecha_inicio == inicio
    assert reserva.fecha_fin == fin
    assert reserva.estado == "ACTIVA"


# ==============================================================================
# 3. Rechazo de Superposiciones (Misma unidad física)
# ==============================================================================
def test_rechazo_superposicion_identica(service):
    """Rechaza reserva con exactamente el mismo rango horario."""
    service.crear_reserva("MIC-01", "User 1", "2026-11-10T10:00", "2026-11-10T12:00")
    with pytest.raises(SuperposicionError):
        service.crear_reserva("MIC-01", "User 2", "2026-11-10T10:00", "2026-11-10T12:00")


def test_rechazo_superposicion_interna(service):
    """Rechaza reserva que cae completamente dentro de una reserva existente."""
    service.crear_reserva("MIC-01", "User 1", "2026-11-10T10:00", "2026-11-10T12:00")
    with pytest.raises(SuperposicionError):
        service.crear_reserva("MIC-01", "User 2", "2026-11-10T10:30", "2026-11-10T11:30")


def test_rechazo_superposicion_envolvente(service):
    """Rechaza reserva que engloba por completo a una reserva existente."""
    service.crear_reserva("MIC-01", "User 1", "2026-11-10T10:30", "2026-11-10T11:30")
    with pytest.raises(SuperposicionError):
        service.crear_reserva("MIC-01", "User 2", "2026-11-10T10:00", "2026-11-10T12:00")


def test_rechazo_superposicion_parcial_inicio(service):
    """Rechaza reserva que inicia antes y termina durante una existente."""
    service.crear_reserva("MIC-01", "User 1", "2026-11-10T10:00", "2026-11-10T12:00")
    with pytest.raises(SuperposicionError):
        service.crear_reserva("MIC-01", "User 2", "2026-11-10T09:30", "2026-11-10T10:30")


def test_rechazo_superposicion_parcial_fin(service):
    """Rechaza reserva que inicia durante y termina después de una existente."""
    service.crear_reserva("MIC-01", "User 1", "2026-11-10T10:00", "2026-11-10T12:00")
    with pytest.raises(SuperposicionError):
        service.crear_reserva("MIC-01", "User 2", "2026-11-10T11:30", "2026-11-10T12:30")


# ==============================================================================
# 4. Límites Consecutivos (Turnos Contiguos Válidos)
# ==============================================================================
def test_limites_consecutivos_posterior(service):
    """Una reserva que inicia exactamente cuando otra termina no debe solaparse."""
    r1 = service.crear_reserva("MIC-01", "User 1", "2026-11-10T10:00", "2026-11-10T11:00")
    r2 = service.crear_reserva("MIC-01", "User 2", "2026-11-10T11:00", "2026-11-10T12:00")
    assert r1.id != r2.id
    assert r1.estado == "ACTIVA"
    assert r2.estado == "ACTIVA"


def test_limites_consecutivos_anterior(service):
    """Una reserva que termina exactamente cuando otra inicia no debe solaparse."""
    r1 = service.crear_reserva("MIC-01", "User 1", "2026-11-10T11:00", "2026-11-10T12:00")
    r2 = service.crear_reserva("MIC-01", "User 2", "2026-11-10T10:00", "2026-11-10T11:00")
    assert r1.id != r2.id
    assert r1.estado == "ACTIVA"
    assert r2.estado == "ACTIVA"


# ==============================================================================
# 5. Simultaneidad en Unidades Distintas
# ==============================================================================
def test_simultaneidad_en_unidades_distintas(service):
    """Dos unidades diferentes pueden reservarse exactamente en el mismo horario."""
    r1 = service.crear_reserva("MIC-01", "User 1", "2026-11-10T10:00", "2026-11-10T12:00")
    r2 = service.crear_reserva("MIC-02", "User 2", "2026-11-10T10:00", "2026-11-10T12:00")
    r3 = service.crear_reserva("OSC-01", "User 3", "2026-11-10T10:00", "2026-11-10T12:00")
    assert r1.id != r2.id != r3.id
    assert r1.estado == "ACTIVA"
    assert r2.estado == "ACTIVA"
    assert r3.estado == "ACTIVA"


# ==============================================================================
# 6. Cancelación y Liberación de Horarios
# ==============================================================================
def test_cancelacion_libera_horario_para_nueva_reserva(service):
    """Una reserva cancelada conserva su registro pero libera el rango para otra activa."""
    r1 = service.crear_reserva("MIC-01", "User 1", "2026-11-10T10:00", "2026-11-10T12:00")
    cancelada = service.cancelar_reserva(r1.id)
    assert cancelada.id == r1.id
    assert cancelada.estado == EstadoReserva.CANCELADA.value

    # Ahora debe permitir crear una nueva reserva en el mismo horario
    r2 = service.crear_reserva("MIC-01", "User 2", "2026-11-10T10:00", "2026-11-10T12:00")
    assert r2.id != r1.id
    assert r2.estado == EstadoReserva.ACTIVA.value


def test_cancelar_reserva_inexistente(service):
    """Intentar cancelar una reserva con id inexistente debe lanzar excepción."""
    with pytest.raises(ReservaNotFoundError):
        service.cancelar_reserva(99999)


# ==============================================================================
# 7. Consulta de Disponibilidad
# ==============================================================================
def test_consultar_disponibilidad(service):
    """Verifica que consultar_disponibilidad retorne True o False según las reglas."""
    # Unidad sin reservas
    assert service.consultar_disponibilidad("MUL-01", "2026-11-10T10:00", "2026-11-10T11:00") is True

    # Se reserva de 10:00 a 11:00
    service.crear_reserva("MUL-01", "User", "2026-11-10T10:00", "2026-11-10T11:00")

    # Mismo horario ocupado
    assert service.consultar_disponibilidad("MUL-01", "2026-11-10T10:00", "2026-11-10T11:00") is False
    # Solapamiento parcial
    assert service.consultar_disponibilidad("MUL-01", "2026-11-10T10:30", "2026-11-10T11:30") is False
    # Turno contiguo contiguo anterior y posterior deben estar disponibles
    assert service.consultar_disponibilidad("MUL-01", "2026-11-10T09:00", "2026-11-10T10:00") is True
    assert service.consultar_disponibilidad("MUL-01", "2026-11-10T11:00", "2026-11-10T12:00") is True
    # Otra unidad en el mismo horario debe estar disponible
    assert service.consultar_disponibilidad("FUE-01", "2026-11-10T10:00", "2026-11-10T11:00") is True


# ==============================================================================
# 8. Entradas Inválidas
# ==============================================================================
@pytest.mark.parametrize("unidad_invalida", ["MIC-99", "INVALID", "", "   ", None])
def test_unidad_invalida_rechazada(service, unidad_invalida):
    """Rechaza unidades que no existan estrictamente en el catálogo."""
    with pytest.raises(UnidadNoEncontradaError):
        service.crear_reserva(
            unidad_id=unidad_invalida,
            solicitante="Test",
            fecha_inicio="2026-11-10T10:00",
            fecha_fin="2026-11-10T11:00",
        )


@pytest.mark.parametrize("solicitante_invalido", ["", "   ", "\t\n", None, 123])
def test_solicitante_invalido_rechazado(service, solicitante_invalido):
    """Rechaza solicitantes vacíos, espacios en blanco o tipo no string."""
    with pytest.raises(SolicitanteInvalidoError):
        service.crear_reserva(
            unidad_id="MIC-01",
            solicitante=solicitante_invalido,
            fecha_inicio="2026-11-10T10:00",
            fecha_fin="2026-11-10T11:00",
        )


def test_fecha_inicio_mayor_o_igual_a_fin_rechazada(service):
    """Rechaza rangos donde fecha_inicio >= fecha_fin."""
    # Inicio igual a fin
    with pytest.raises(HorarioInvalidoError):
        service.crear_reserva("MIC-01", "Test", "2026-11-10T10:00", "2026-11-10T10:00")

    # Inicio posterior a fin
    with pytest.raises(HorarioInvalidoError):
        service.crear_reserva("MIC-01", "Test", "2026-11-10T12:00", "2026-11-10T10:00")


@pytest.mark.parametrize("fecha_invalida", ["no-es-fecha", "2026/11/10 10:00", 12345, None])
def test_formato_fecha_invalido_rechazado(service, fecha_invalida):
    """Rechaza formatos de fecha no parseables en ISO 8601 o tipos inválidos."""
    with pytest.raises(ValidationError):
        service.crear_reserva("MIC-01", "Test", fecha_invalida, "2026-11-10T11:00")


# ==============================================================================
# 9. Persistencia SQLite
# ==============================================================================
def test_persistencia_recarga_sqlite(temp_db_path):
    """Verifica que las reservas persistan en el archivo SQLite tras reiniciar el servicio."""
    # Instancia 1 crea reserva
    svc1 = ReservaService(db_path=temp_db_path, inventory_path="data/inventory.json")
    r1 = svc1.crear_reserva("FUE-01", "Persistente", "2026-11-10T08:00", "2026-11-10T09:30")

    # Instancia 2 se conecta a la misma base de datos
    svc2 = ReservaService(db_path=temp_db_path, inventory_path="data/inventory.json")
    r_cargada = svc2.obtener_reserva(r1.id)

    assert r_cargada is not None
    assert r_cargada.id == r1.id
    assert r_cargada.unidad_id == "FUE-01"
    assert r_cargada.solicitante == "Persistente"
    assert r_cargada.fecha_inicio == datetime(2026, 11, 10, 8, 0)
    assert r_cargada.fecha_fin == datetime(2026, 11, 10, 9, 30)
    assert r_cargada.estado == "ACTIVA"


def test_rechazo_fechas_con_timezone_aware(service):
    """Rechaza datetimes timezone-aware según las restricciones de AGENT.md."""
    from datetime import timezone
    dt_aware = datetime(2026, 11, 10, 10, 0, tzinfo=timezone.utc)
    with pytest.raises(ValidationError):
        service.crear_reserva("MIC-01", "Test", dt_aware, "2026-11-10T12:00")


def test_listar_reservas_y_filtros(service):
    """Verifica listar reservas con filtros por unidad y solo activas."""
    r1 = service.crear_reserva("MIC-01", "User A", "2026-11-10T08:00", "2026-11-10T09:00")
    r2 = service.crear_reserva("MIC-01", "User B", "2026-11-10T10:00", "2026-11-10T11:00")
    r3 = service.crear_reserva("MIC-02", "User C", "2026-11-10T08:00", "2026-11-10T09:00")
    service.cancelar_reserva(r1.id)

    # Todas las reservas
    todas = service.listar_reservas()
    assert len(todas) == 3

    # Solo de MIC-01
    mic1 = service.listar_reservas(unidad_id="MIC-01")
    assert len(mic1) == 2

    # Solo activas de MIC-01
    mic1_activas = service.listar_reservas(unidad_id="MIC-01", solo_activas=True)
    assert len(mic1_activas) == 1
    assert mic1_activas[0].id == r2.id


def test_rutas_por_defecto():
    """Verifica que las rutas por defecto apunten a data/reservas.db y data/inventory.json."""
    from pathlib import Path
    from src.repository import DEFAULT_DB_PATH
    from src.inventory import DEFAULT_INVENTORY_PATH

    assert DEFAULT_DB_PATH == Path("data") / "reservas.db"
    assert DEFAULT_INVENTORY_PATH == Path("data") / "inventory.json"

