"""Pruebas unitarias y de integración para la interfaz de línea de comandos (CLI) en main.py."""

import pytest
from main import main


@pytest.fixture
def cli_db_path(tmp_path):
    """Ruta a base de datos SQLite temporal para pruebas de CLI."""
    return str(tmp_path / "cli_test_reservas.db")


def test_cli_inventario(cli_db_path, capsys):
    """Verifica que el subcomando 'inventario' liste las 5 unidades del catálogo fijo."""
    exit_code = main(["--db", cli_db_path, "inventario"])
    captured = capsys.readouterr()
    salida = captured.out

    assert exit_code == 0
    assert "MIC-01" in salida
    assert "MIC-02" in salida
    assert "OSC-01" in salida
    assert "MUL-01" in salida
    assert "FUE-01" in salida
    assert "Microscopio digital" in salida
    assert "Osciloscopio" in salida


def test_cli_disponibilidad_libre_y_ocupada(cli_db_path, capsys):
    """Verifica que 'disponibilidad' informe DISPONIBLE o NO DISPONIBLE según corresponda."""
    # Inicialmente disponible
    code1 = main([
        "--db", cli_db_path,
        "disponibilidad",
        "--unidad", "MIC-01",
        "--inicio", "2026-11-10T10:00",
        "--fin", "2026-11-10T12:00",
    ])
    out1 = capsys.readouterr().out
    assert code1 == 0
    assert "DISPONIBLE" in out1
    assert "NO DISPONIBLE" not in out1

    # Crear reserva en ese horario
    code_res = main([
        "--db", cli_db_path,
        "reservar",
        "--unidad", "MIC-01",
        "--solicitante", "Ana Lovelace",
        "--inicio", "2026-11-10T10:00",
        "--fin", "2026-11-10T12:00",
    ])
    capsys.readouterr()
    assert code_res == 0

    # Ahora debe informar NO DISPONIBLE
    code2 = main([
        "--db", cli_db_path,
        "disponibilidad",
        "--unidad", "MIC-01",
        "--inicio", "2026-11-10T10:30",
        "--fin", "2026-11-10T11:30",
    ])
    out2 = capsys.readouterr().out
    assert code2 == 0
    assert "NO DISPONIBLE" in out2


def test_cli_reservar_y_listar(cli_db_path, capsys):
    """Verifica la creación de reservas con 'reservar' y su visualización con 'listar'."""
    code = main([
        "--db", cli_db_path,
        "reservar",
        "--unidad", "OSC-01",
        "--solicitante", "Alan Turing",
        "--inicio", "2026-11-10T14:00",
        "--fin", "2026-11-10T16:00",
    ])
    out_res = capsys.readouterr().out
    assert code == 0
    assert "OSC-01" in out_res
    assert "Alan Turing" in out_res
    assert "ACTIVA" in out_res

    # Listar reservas
    code_list = main(["--db", cli_db_path, "listar"])
    out_list = capsys.readouterr().out
    assert code_list == 0
    assert "OSC-01" in out_list
    assert "Alan Turing" in out_list
    assert "2026-11-10T14:00" in out_list
    assert "2026-11-10T16:00" in out_list
    assert "ACTIVA" in out_list


def test_cli_cancelar_y_filtros_listar(cli_db_path, capsys):
    """Verifica 'cancelar --id' y los filtros '--unidad' y '--solo-activas' de 'listar'."""
    # Crear 2 reservas en MIC-01 y 1 en FUE-01
    main([
        "--db", cli_db_path,
        "reservar",
        "--unidad", "MIC-01",
        "--solicitante", "Usuario Uno",
        "--inicio", "2026-11-10T08:00",
        "--fin", "2026-11-10T09:00",
    ])
    main([
        "--db", cli_db_path,
        "reservar",
        "--unidad", "MIC-01",
        "--solicitante", "Usuario Dos",
        "--inicio", "2026-11-10T10:00",
        "--fin", "2026-11-10T11:00",
    ])
    main([
        "--db", cli_db_path,
        "reservar",
        "--unidad", "FUE-01",
        "--solicitante", "Usuario Tres",
        "--inicio", "2026-11-10T08:00",
        "--fin", "2026-11-10T09:00",
    ])
    capsys.readouterr()

    # Cancelar reserva ID 1
    code_cancel = main(["--db", cli_db_path, "cancelar", "--id", "1"])
    out_cancel = capsys.readouterr().out
    assert code_cancel == 0
    assert "CANCELADA" in out_cancel
    assert "liberado" in out_cancel.lower()

    # Listar por unidad MIC-01 (debe mostrar tanto la CANCELADA como la ACTIVA)
    code_mic = main(["--db", cli_db_path, "listar", "--unidad", "MIC-01"])
    out_mic = capsys.readouterr().out
    assert code_mic == 0
    assert "Usuario Uno" in out_mic
    assert "CANCELADA" in out_mic
    assert "Usuario Dos" in out_mic
    assert "ACTIVA" in out_mic
    assert "Usuario Tres" not in out_mic

    # Listar por unidad MIC-01 y --solo-activas (solo debe mostrar Usuario Dos)
    code_activas = main(["--db", cli_db_path, "listar", "--unidad", "MIC-01", "--solo-activas"])
    out_activas = capsys.readouterr().out
    assert code_activas == 0
    assert "Usuario Uno" not in out_activas
    assert "Usuario Dos" in out_activas


def test_cli_reset_limpia_base_de_datos(cli_db_path, capsys):
    """Verifica que el subcomando 'reset' invoque limpiar_reservas() y muestre advertencia explícita."""
    main([
        "--db", cli_db_path,
        "reservar",
        "--unidad", "MUL-01",
        "--solicitante", "Usuario Temporal",
        "--inicio", "2026-11-10T09:00",
        "--fin", "2026-11-10T10:00",
    ])
    capsys.readouterr()

    code_reset = main(["--db", cli_db_path, "reset"])
    out_reset = capsys.readouterr().out
    assert code_reset == 0
    assert "advertencia" in out_reset.lower() or "eliminaron" in out_reset.lower()

    # Verificar que listar ya no devuelve reservas
    code_list = main(["--db", cli_db_path, "listar"])
    out_list = capsys.readouterr().out
    assert code_list == 0
    assert "Usuario Temporal" not in out_list


def test_cli_manejo_errores_sin_tracebacks(cli_db_path, capsys):
    """
    Verifica que los errores de dominio (unidad inválida, superposición, horario inválido,
    reserva inexistente) devuelvan código != 0 y mensajes claros sin tracebacks crudos.
    """
    # 1. Unidad inexistente
    code_unidad = main([
        "--db", cli_db_path,
        "reservar",
        "--unidad", "NO-EXISTE",
        "--solicitante", "Test",
        "--inicio", "2026-11-10T10:00",
        "--fin", "2026-11-10T11:00",
    ])
    captured = capsys.readouterr()
    combined = captured.out + captured.err
    assert code_unidad != 0
    assert "NO-EXISTE" in combined
    assert "Traceback" not in combined

    # 2. Horario inválido (inicio >= fin)
    code_horario = main([
        "--db", cli_db_path,
        "reservar",
        "--unidad", "MIC-01",
        "--solicitante", "Test",
        "--inicio", "2026-11-10T12:00",
        "--fin", "2026-11-10T10:00",
    ])
    captured = capsys.readouterr()
    combined = captured.out + captured.err
    assert code_horario != 0
    assert "Traceback" not in combined

    # 3. Superposición horaria
    main([
        "--db", cli_db_path,
        "reservar",
        "--unidad", "MIC-01",
        "--solicitante", "Primero",
        "--inicio", "2026-11-10T10:00",
        "--fin", "2026-11-10T12:00",
    ])
    capsys.readouterr()

    code_solapada = main([
        "--db", cli_db_path,
        "reservar",
        "--unidad", "MIC-01",
        "--solicitante", "Segundo",
        "--inicio", "2026-11-10T11:00",
        "--fin", "2026-11-10T13:00",
    ])
    captured = capsys.readouterr()
    combined = captured.out + captured.err
    assert code_solapada != 0
    assert "Conflicto" in combined or "solap" in combined.lower() or "activa" in combined.lower()
    assert "Traceback" not in combined

    # 4. Cancelar reserva inexistente
    code_no_encontrada = main(["--db", cli_db_path, "cancelar", "--id", "999"])
    captured = capsys.readouterr()
    combined = captured.out + captured.err
    assert code_no_encontrada != 0
    assert "999" in combined
    assert "Traceback" not in combined

