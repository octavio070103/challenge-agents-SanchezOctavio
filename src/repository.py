"""Repositorio SQLite para la persistencia de reservas."""

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Generator, List, Optional, Union
from src.models import Reserva, EstadoReserva


DEFAULT_DB_PATH = Path("data") / "reservas.db"


class ReservaRepository:
    """Maneja la persistencia y consultas de reservas en SQLite."""

    def __init__(self, db_path: Union[str, Path] = DEFAULT_DB_PATH):
        self.db_path = str(db_path)
        self._init_db()

    @contextmanager
    def _connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Crea una conexión que garantiza el cierre de descriptores al salir."""
        if self.db_path != ":memory:":
            db_dir = Path(self.db_path).parent
            if db_dir and not db_dir.exists():
                db_dir.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _init_db(self) -> None:
        """Inicializa el esquema de la base de datos si no existe."""
        with self._connection() as conn:
            with conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS reservas (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        unidad_id TEXT NOT NULL,
                        solicitante TEXT NOT NULL,
                        fecha_inicio TEXT NOT NULL,
                        fecha_fin TEXT NOT NULL,
                        estado TEXT NOT NULL CHECK(estado IN ('ACTIVA', 'CANCELADA'))
                    );
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_reservas_unidad_estado 
                    ON reservas(unidad_id, estado);
                """)

    @staticmethod
    def _row_to_reserva(row: sqlite3.Row) -> Reserva:
        """Transforma una fila de SQLite en un objeto Reserva."""
        return Reserva(
            id=row["id"],
            unidad_id=row["unidad_id"],
            solicitante=row["solicitante"],
            fecha_inicio=datetime.fromisoformat(row["fecha_inicio"]),
            fecha_fin=datetime.fromisoformat(row["fecha_fin"]),
            estado=row["estado"],
        )

    def guardar(self, reserva: Reserva) -> Reserva:
        """Inserta una nueva reserva en la base de datos y le asigna su id generado."""
        query = """
            INSERT INTO reservas (unidad_id, solicitante, fecha_inicio, fecha_fin, estado)
            VALUES (?, ?, ?, ?, ?)
        """
        inicio_str = reserva.fecha_inicio.strftime("%Y-%m-%dT%H:%M")
        fin_str = reserva.fecha_fin.strftime("%Y-%m-%dT%H:%M")

        with self._connection() as conn:
            with conn:
                cursor = conn.cursor()
                cursor.execute(
                    query,
                    (
                        reserva.unidad_id,
                        reserva.solicitante,
                        inicio_str,
                        fin_str,
                        reserva.estado,
                    ),
                )
                reserva_id = cursor.lastrowid

        return Reserva(
            id=reserva_id,
            unidad_id=reserva.unidad_id,
            solicitante=reserva.solicitante,
            fecha_inicio=reserva.fecha_inicio,
            fecha_fin=reserva.fecha_fin,
            estado=reserva.estado,
        )

    def obtener_por_id(self, reserva_id: int) -> Optional[Reserva]:
        """Recupera una reserva por su identificador único."""
        query = "SELECT id, unidad_id, solicitante, fecha_inicio, fecha_fin, estado FROM reservas WHERE id = ?"
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (reserva_id,))
            row = cursor.fetchone()
            if row:
                return self._row_to_reserva(row)
        return None

    def actualizar_estado(self, reserva_id: int, nuevo_estado: str) -> bool:
        """Actualiza el estado de una reserva ('ACTIVA' o 'CANCELADA')."""
        if nuevo_estado not in (EstadoReserva.ACTIVA.value, EstadoReserva.CANCELADA.value):
            raise ValueError(f"Estado inválido: {nuevo_estado}")

        query = "UPDATE reservas SET estado = ? WHERE id = ?"
        with self._connection() as conn:
            with conn:
                cursor = conn.cursor()
                cursor.execute(query, (nuevo_estado, reserva_id))
                return cursor.rowcount > 0

    def obtener_activas_por_unidad(self, unidad_id: str) -> List[Reserva]:
        """Obtiene todas las reservas con estado ACTIVA para una unidad específica."""
        query = """
            SELECT id, unidad_id, solicitante, fecha_inicio, fecha_fin, estado
            FROM reservas
            WHERE unidad_id = ? AND estado = 'ACTIVA'
            ORDER BY fecha_inicio ASC
        """
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (unidad_id,))
            rows = cursor.fetchall()
            return [self._row_to_reserva(r) for r in rows]

    def obtener_todas(
        self, unidad_id: Optional[str] = None, solo_activas: bool = False
    ) -> List[Reserva]:
        """Retorna reservas filtrando opcionalmente por unidad y estado activo."""
        conditions = []
        params = []
        if unidad_id:
            conditions.append("unidad_id = ?")
            params.append(unidad_id)
        if solo_activas:
            conditions.append("estado = 'ACTIVA'")

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        query = f"""
            SELECT id, unidad_id, solicitante, fecha_inicio, fecha_fin, estado
            FROM reservas
            {where_clause}
            ORDER BY fecha_inicio ASC
        """
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [self._row_to_reserva(r) for r in rows]
