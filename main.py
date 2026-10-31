"""Interfaz de línea de comandos (CLI) para el Sistema de Reservas de Laboratorio."""

import argparse
import sys
from typing import List, Optional

from src.exceptions import ReservaError
from src.repository import DEFAULT_DB_PATH
from src.service import ReservaService


def construir_parser() -> argparse.ArgumentParser:
    """Construye y configura el parser de argumentos de la CLI."""
    parent_db = argparse.ArgumentParser(add_help=False)
    parent_db.add_argument(
        "--db",
        default=argparse.SUPPRESS,
        help="Ruta al archivo SQLite de reservas (por defecto: data/reservas.db)",
    )

    parser = argparse.ArgumentParser(
        prog="main.py",
        description="Sistema Local de Gestión de Reservas de Equipos de Laboratorio",
    )
    parser.add_argument(
        "--db",
        default=str(DEFAULT_DB_PATH),
        help="Ruta al archivo SQLite de reservas (por defecto: data/reservas.db)",
    )

    subparsers = parser.add_subparsers(dest="subcomando", required=True, help="Operación a realizar")

    # 1. Subcomando: inventario
    subparsers.add_parser(
        "inventario",
        parents=[parent_db],
        help="Lista las unidades del catálogo fijo de equipos del laboratorio",
    )

    # 2. Subcomando: disponibilidad
    p_disp = subparsers.add_parser(
        "disponibilidad",
        parents=[parent_db],
        help="Consulta si una unidad física está disponible en un intervalo horario",
    )
    p_disp.add_argument("--unidad", required=True, help="ID de la unidad (ej. MIC-01)")
    p_disp.add_argument("--inicio", required=True, help="Fecha/hora de inicio ISO 8601 (YYYY-MM-DDTHH:MM)")
    p_disp.add_argument("--fin", required=True, help="Fecha/hora de fin ISO 8601 (YYYY-MM-DDTHH:MM)")

    # 3. Subcomando: reservar
    p_res = subparsers.add_parser(
        "reservar",
        parents=[parent_db],
        help="Crea una nueva reserva para una unidad física",
    )
    p_res.add_argument("--unidad", required=True, help="ID de la unidad (ej. MIC-01)")
    p_res.add_argument("--solicitante", required=True, help="Nombre del solicitante")
    p_res.add_argument("--inicio", required=True, help="Fecha/hora de inicio ISO 8601 (YYYY-MM-DDTHH:MM)")
    p_res.add_argument("--fin", required=True, help="Fecha/hora de fin ISO 8601 (YYYY-MM-DDTHH:MM)")

    # 4. Subcomando: cancelar
    p_can = subparsers.add_parser(
        "cancelar",
        parents=[parent_db],
        help="Cancela una reserva existente conservando su registro en el historial",
    )
    p_can.add_argument("--id", type=int, required=True, dest="reserva_id", help="ID numérico de la reserva")

    # 5. Subcomando: listar
    p_list = subparsers.add_parser(
        "listar",
        parents=[parent_db],
        help="Lista el historial de reservas registradas",
    )
    p_list.add_argument("--unidad", default=None, help="Filtrar por ID de unidad (opcional)")
    p_list.add_argument(
        "--solo-activas",
        action="store_true",
        help="Mostrar únicamente reservas con estado ACTIVA",
    )

    # 6. Subcomando: reset
    subparsers.add_parser(
        "reset",
        parents=[parent_db],
        help="Elimina todas las reservas activas y canceladas de la base de datos SQLite",
    )

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """Punto de entrada principal de la CLI. Retorna 0 en éxito o 1 en caso de error."""
    parser = construir_parser()
    args = parser.parse_args(argv)

    try:
        service = ReservaService(db_path=args.db)

        if args.subcomando == "inventario":
            print("Catálogo Fijo de Equipos de Laboratorio:")
            print(f"{'ID':<10} | {'EQUIPO'}")
            print("-" * 40)
            for unidad in service.unidades:
                print(f"{unidad.id:<10} | {unidad.name}")
            return 0

        if args.subcomando == "disponibilidad":
            disponible = service.consultar_disponibilidad(
                unidad_id=args.unidad,
                fecha_inicio=args.inicio,
                fecha_fin=args.fin,
            )
            estado_txt = "DISPONIBLE" if disponible else "NO DISPONIBLE"
            print(
                f"Estado de disponibilidad para '{args.unidad}' "
                f"[{args.inicio} -> {args.fin}]: {estado_txt}"
            )
            return 0

        if args.subcomando == "reservar":
            reserva = service.crear_reserva(
                unidad_id=args.unidad,
                solicitante=args.solicitante,
                fecha_inicio=args.inicio,
                fecha_fin=args.fin,
            )
            inicio_fmt = reserva.fecha_inicio.strftime("%Y-%m-%dT%H:%M")
            fin_fmt = reserva.fecha_fin.strftime("%Y-%m-%dT%H:%M")
            print(
                f"Reserva creada exitosamente: ID={reserva.id} | "
                f"Unidad={reserva.unidad_id} | Solicitante='{reserva.solicitante}' | "
                f"Inicio={inicio_fmt} | Fin={fin_fmt} | Estado={reserva.estado}"
            )
            return 0

        if args.subcomando == "cancelar":
            reserva = service.cancelar_reserva(args.reserva_id)
            inicio_fmt = reserva.fecha_inicio.strftime("%Y-%m-%dT%H:%M")
            fin_fmt = reserva.fecha_fin.strftime("%Y-%m-%dT%H:%M")
            print(
                f"Reserva ID={reserva.id} actualizada a estado '{reserva.estado}'. "
                f"El horario [{inicio_fmt} -> {fin_fmt}] para la unidad '{reserva.unidad_id}' "
                f"ha sido liberado y el registro se conserva en el historial."
            )
            return 0

        if args.subcomando == "listar":
            reservas = service.listar_reservas(
                unidad_id=args.unidad,
                solo_activas=args.solo_activas,
            )
            if not reservas:
                print("No se encontraron reservas registradas con los criterios indicados.")
                return 0

            print(
                f"{'ID':<4} | {'UNIDAD':<8} | {'SOLICITANTE':<22} | "
                f"{'INICIO':<16} | {'FIN':<16} | {'ESTADO'}"
            )
            print("-" * 82)
            for r in reservas:
                inicio_fmt = r.fecha_inicio.strftime("%Y-%m-%dT%H:%M")
                fin_fmt = r.fecha_fin.strftime("%Y-%m-%dT%H:%M")
                print(
                    f"{r.id:<4} | {r.unidad_id:<8} | {r.solicitante:<22} | "
                    f"{inicio_fmt:<16} | {fin_fmt:<16} | {r.estado}"
                )
            return 0

        if args.subcomando == "reset":
            service.limpiar_reservas()
            print(
                "ADVERTENCIA: Se eliminaron todas las reservas activas y el historial de "
                "reservas canceladas de la base de datos SQLite. El inventario en "
                "data/inventory.json permanece intacto."
            )
            return 0

        return 0

    except ReservaError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
