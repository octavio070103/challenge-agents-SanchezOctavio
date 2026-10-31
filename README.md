# Sistema de Reservas de Equipos de Laboratorio
## Seccion 1 : Especificacion 
### Problema
La Coordinacion de un laboratorio gestiona las solicitudes de reserva medianete mensajes y una planilla manual. Los cuales presentan problemas de superposicion de horarios y pedidos, asi como cancelaciones que no liberar el recurso para futuras reservas,reglas muy pocos claras o ambiguas respecto a las reservas y sin trazabilidad de las mismas.

### Alcance
Sistema local de gestión de reservas que permite consultar disponibilidad, registrar reservas y cancelarlas conservando el historial en una base de datos SQLite local (`data/reservas.db`).

### Inventario Precargado
| ID de unidad | Equipo |
| :--- | :--- |
| `MIC-01` | Microscopio digital |
| `MIC-02` | Microscopio digital |
| `OSC-01` | Osciloscopio |
| `MUL-01` | Multímetro |
| `FUE-01` | Fuente de alimentación |

### Reglas de Negocio y Supuestos Técnicos
1. **Identificación y Campos**: Toda reserva posee un ID único, `unidad_id` (debe existir en el inventario), `solicitante` (string no vacío ni compuesto solo por espacios), `inicio`, `fin` y `estado` (`ACTIVA` o `CANCELADA`).
2. **Formato de Fechas y Zona Horaria (Supuesto)**: Se utiliza formato ISO 8601 local (`YYYY-MM-DDTHH:MM`) *naive* (sin zona horaria explícita), asumiendo que toda la operación ocurre en la hora local del laboratorio.
3. **Tratamiento de Fechas Pasadas y Límites (Supuesto)**: No se bloquean fechas pasadas respecto al reloj del sistema para permitir pruebas automáticas deterministas y reproducibles en cualquier momento. El intervalo debe cumplir estrictamente `inicio < fin`, sin límite máximo de duración ni anticipación.
4. **Superposición y Límites Consecutivos**: Una reserva `ACTIVA` bloquea el intervalo `[inicio, fin)`. Se rechaza cualquier nueva reserva para la misma unidad si `inicio_nuevo < fin_existente` y `fin_nuevo > inicio_existente`. Se permiten turnos inmediatamente consecutivos (ej. 10:00 a 11:00 y 11:00 a 12:00).
5. **Simultaneidad**: Unidades físicas distintas (ej. `MIC-01` y `MIC-02`) pueden reservarse en el mismo horario sin conflicto.
6. **Cancelación e Historial**: Cancelar una reserva cambia su estado a `CANCELADA`, conserva su registro e ID para auditoría/historial y libera inmediatamente el intervalo horario para nuevas reservas.

### Criterios de Aceptación Verificables
* **CA-01**: Dado un `unidad_id` existente y datos válidos, se genera una reserva en estado `ACTIVA` con un ID único.
* **CA-02**: Rechazar con error de validación cualquier solicitud con `solicitante` vacío, compuesto solo por espacios o de tipo no string.
* **CA-03**: Rechazar cualquier intervalo donde `fecha_inicio >= fecha_fin` o con formato de fecha inválido.
* **CA-04**: Si existe una reserva activa para una unidad de 10:00 a 11:00, rechazar cualquier solicitud para esa misma unidad que solape en $[inicio, fin)$, incluyendo solapamientos parciales internos o envolventes.
* **CA-05**: Si existe una reserva activa de 10:00 a 11:00, aceptar solicitudes de 11:00 a 12:00 o de 09:00 a 10:00 (límites consecutivos).
* **CA-06**: Dos unidades físicas diferentes pueden reservarse en franjas horarias exactamente iguales.
* **CA-07**: Al cancelar una reserva existente, su estado pasa a `CANCELADA`, permanece consultable en el historial y el intervalo queda disponible para una nueva reserva en ese mismo horario.
* **CA-08**: Toda reserva (activa o cancelada) debe persistir intacta en `data/reservas.db` tras detener y reiniciar el proceso.

## Sección 2: Solución

### Estructura del Proyecto y Decisiones Técnicas
- [`data/inventory.json`](./data/inventory.json): Catálogo de equipos precargado de solo lectura.
- `data/reservas.db`: Archivo SQLite local donde persisten las reservas y sus estados.
- [`src/models.py`](./src/models.py): Entidades `Unidad`, `Reserva` y enum `EstadoReserva`.
- [`src/exceptions.py`](./src/exceptions.py): Jerarquía de errores de dominio tipificados (`ValidationError`, `UnidadNoEncontradaError`, `SolicitanteInvalidoError`, `HorarioInvalidoError`, `SuperposicionError`, `ReservaNotFoundError`).
- [`src/inventory.py`](./src/inventory.py): Módulo de lectura y validación del inventario fijo.
- [`src/repository.py`](./src/repository.py): Capa de acceso a SQLite con *context managers* para cierre determinista de conexiones.
- [`src/service.py`](./src/service.py): Motor de reglas de negocio (`ReservaService`).
- [`tests/test_reservas.py`](./tests/test_reservas.py): Suite exhaustiva de pruebas unitarias y de persistencia.

### Requisitos Previos y Versiones Verificadas
- **Sistema Operativo**: Windows (`win32`) / Linux
- **Python**: `3.12.2`
- **Pytest**: `9.1.1` (con `pluggy-1.7.0`)

### Instalación, Persistencia, Comandos y Ejemplo de Entrada/Salida
1. Crear y activar entorno virtual:
   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```
2. Instalar dependencias:
   ```powershell
   pip install -r requirements.txt
   ```
3. Ejecución de pruebas automáticas:
   ```powershell
   .\venv\Scripts\python -m pytest tests/ -v
   ```
4. **Comandos de la Aplicación (CLI en `main.py`) y Ejemplo Reproducible**:
   ```powershell
   # Consultar catálogo fijo de equipos
   .\venv\Scripts\python main.py inventario

   # Consultar disponibilidad de una unidad en un intervalo
   .\venv\Scripts\python main.py disponibilidad --unidad MIC-01 --inicio 2026-11-10T10:00 --fin 2026-11-10T11:00

   # Crear reserva válida (MIC-01 de 10:00 a 11:00)
   .\venv\Scripts\python main.py reservar --unidad MIC-01 --solicitante "Dra. Gomez" --inicio 2026-11-10T10:00 --fin 2026-11-10T11:00

   # Intento de superposición rechazado (MIC-01 de 10:30 a 11:30 -> Error de superposición)
   .\venv\Scripts\python main.py reservar --unidad MIC-01 --solicitante "Ing. Perez" --inicio 2026-11-10T10:30 --fin 2026-11-10T11:30

   # Turno consecutivo permitido (MIC-01 de 11:00 a 12:00) y simultáneo en otra unidad (MIC-02 de 10:00 a 11:00)
   .\venv\Scripts\python main.py reservar --unidad MIC-01 --solicitante "Ing. Perez" --inicio 2026-11-10T11:00 --fin 2026-11-10T12:00
   .\venv\Scripts\python main.py reservar --unidad MIC-02 --solicitante "Lic. Diaz" --inicio 2026-11-10T10:00 --fin 2026-11-10T11:00

   # Cancelar reserva por ID conservando historial y liberando horario
   .\venv\Scripts\python main.py cancelar --id 1

   # Listar historial completo (activas y canceladas)
   .\venv\Scripts\python main.py listar

   # Reiniciar base de datos (borra todas las reservas registradas)
   .\venv\Scripts\python main.py reset
   ```
5. **Persistencia, Reinicio de Datos y Limitaciones**:
   - **Dónde persisten los datos**: Las reservas y sus estados (`ACTIVA` / `CANCELADA`) persisten automáticamente en el archivo SQLite local `data/reservas.db` (o en la ruta indicada por `--db`). El catálogo inicial se carga en modo solo lectura desde `data/inventory.json`.
   - **Advertencia sobre reinicio de datos**: Ejecutar `python main.py reset` (o invocar `limpiar_reservas()` / eliminar `data/reservas.db`) **borra de forma permanente todas las reservas activas y el historial de cancelaciones**, conservando intacto únicamente el catálogo de equipos en `data/inventory.json`.
   - **Pendientes y Limitaciones**:
    * *Episodio 1*: Completado (Dominio, SQLite y pruebas unitarias de reglas base)
    * *Episodio 2*: Completado (Persistencia de activas y canceladas tras reinicio, liberación de horarios y método de reseteo)
    * *Episodio 3*: Completado (CLI en `main.py` con subcomandos y pruebas en `test_cli.py`)
    * *Limitaciones conocidas del diseño*: Sistema monousuario local sin concurrencia distribuida en tiempo real y sin autenticación multiusuario ni interfaz web (ambas declaradas fuera de alcance por la consigna)

### Verificación de Pruebas Automáticas (Distinción Agente vs. Ejecución Humana)
- **Informado por el agente**:
  - *Episodio 1*: 33 pruebas aprobadas en `0.59s`.
  - *Episodio 2*: 34 pruebas aprobadas en `0.73s`.
  - *Episodio 3*: 40 pruebas aprobadas (`tests/test_reservas.py` + `tests/test_cli.py`) en `0.85s`.
- **Verificación humana realmente ejecutada**: Se ejecutó manualmente en PowerShell (`Python 3.12.2`, `pytest 9.1.1`) la suite completa de 40 pruebas automáticas (`tests/test_reservas.py` y `tests/test_cli.py`), verificando que las 40 pruebas pasan al 100%:

```powershell
PS> .\venv\Scripts\python -m pytest tests/ -v
platform win32 -- Python 3.12.2, pytest-9.1.1, pluggy-1.7.0
collected 40 items

tests/test_cli.py::test_cli_inventario PASSED                                                      [  2%]
tests/test_cli.py::test_cli_disponibilidad_libre_y_ocupada PASSED                                  [  5%]
tests/test_cli.py::test_cli_reservar_y_listar PASSED                                               [  7%]
tests/test_cli.py::test_cli_cancelar_y_filtros_listar PASSED                                       [ 10%]
tests/test_cli.py::test_cli_reset_limpia_base_de_datos PASSED                                      [ 12%]
tests/test_cli.py::test_cli_manejo_errores_sin_tracebacks PASSED                                   [ 15%]
tests/test_reservas.py::test_cargar_inventario_catalogo_fijo PASSED                                [ 17%]
tests/test_reservas.py::test_creacion_reserva_valida_con_strings_iso PASSED                        [ 20%]
tests/test_reservas.py::test_creacion_reserva_valida_con_objetos_datetime PASSED                   [ 22%]
tests/test_reservas.py::test_rechazo_superposicion_identica PASSED                                 [ 25%]
tests/test_reservas.py::test_rechazo_superposicion_interna PASSED                                  [ 27%]
tests/test_reservas.py::test_rechazo_superposicion_envolvente PASSED                               [ 30%]
tests/test_reservas.py::test_rechazo_superposicion_parcial_inicio PASSED                           [ 32%]
tests/test_reservas.py::test_rechazo_superposicion_parcial_fin PASSED                              [ 35%]
tests/test_reservas.py::test_limites_consecutivos_posterior PASSED                                 [ 37%]
tests/test_reservas.py::test_limites_consecutivos_anterior PASSED                                  [ 40%]
tests/test_reservas.py::test_simultaneidad_en_unidades_distintas PASSED                            [ 42%]
tests/test_reservas.py::test_cancelacion_libera_horario_para_nueva_reserva PASSED                  [ 45%]
tests/test_reservas.py::test_cancelar_reserva_inexistente PASSED                                   [ 47%]
tests/test_reservas.py::test_consultar_disponibilidad PASSED                                       [ 50%]
tests/test_reservas.py::test_unidad_invalida_rechazada[MIC-99] PASSED                              [ 52%]
tests/test_reservas.py::test_unidad_invalida_rechazada[INVALID] PASSED                             [ 55%]
tests/test_reservas.py::test_unidad_invalida_rechazada[] PASSED                                    [ 57%]
tests/test_reservas.py::test_unidad_invalida_rechazada[   ] PASSED                                 [ 60%]
tests/test_reservas.py::test_unidad_invalida_rechazada[None] PASSED                                [ 62%]
tests/test_reservas.py::test_solicitante_invalido_rechazado[] PASSED                               [ 65%]
tests/test_reservas.py::test_solicitante_invalido_rechazado[   ] PASSED                            [ 67%]
tests/test_reservas.py::test_solicitante_invalido_rechazado[\t\n] PASSED                           [ 70%]
tests/test_reservas.py::test_solicitante_invalido_rechazado[None] PASSED                           [ 72%]
tests/test_reservas.py::test_solicitante_invalido_rechazado[123] PASSED                            [ 75%]
tests/test_reservas.py::test_fecha_inicio_mayor_o_igual_a_fin_rechazada PASSED                     [ 77%]
tests/test_reservas.py::test_formato_fecha_invalido_rechazado[no-es-fecha] PASSED                  [ 80%]
tests/test_reservas.py::test_formato_fecha_invalido_rechazado[2026/11/10 10:00] PASSED             [ 82%]
tests/test_reservas.py::test_formato_fecha_invalido_rechazado[12345] PASSED                        [ 85%]
tests/test_reservas.py::test_formato_fecha_invalido_rechazado[None] PASSED                         [ 87%]
tests/test_reservas.py::test_persistencia_recarga_sqlite PASSED                                    [ 90%]
tests/test_reservas.py::test_limpiar_reservas PASSED                                               [ 92%]
tests/test_reservas.py::test_rechazo_fechas_con_timezone_aware PASSED                              [ 95%]
tests/test_reservas.py::test_listar_reservas_y_filtros PASSED                                      [ 97%]
tests/test_reservas.py::test_rutas_por_defecto PASSED                                              [100%]

40 passed in 0.85s
```

## Sección 3: Preparación del Agente
- **Entorno (Harness)**: Antigravity IDE (Versión 2.5.5).
- **Modelos utilizados**: `Gemini 3.8 Flash High Trust` (Episodio 1) y `Gemini 4 Argon Medium` (Episodio 2 y 3).
- **Función y Motivo de Elección**: Agente de programación local sobre el repositorio; elegido por su baja latencia para ciclos cortos de TDD, lectura estructurada de archivos de contexto y capacidad de invocar herramientas del sistema de archivos y consola.
- **Instrucciones y Contexto Suministrado**: Las reglas operativas y de negocio están versionadas en [`AGENT.md`](./AGENT.md). Se suministró explícitamente `@AGENT.md` y `@data/inventory.json`, excluyendo mediante [`.gitignore`](./.gitignore) el entorno virtual `venv/`, cachés (`.pytest_cache/`, `__pycache__/`) y el documento de consigna `challenge-agents.pdf`.
- **Herramientas, Permisos y Controles Humanos**:
  - *Lectura y escritura*: Permitida dentro de `src/` y `tests/`, con revisión humana de *diffs* en el editor antes de aceptar cambios (*Accept Changes*).
  - *Ejecución en terminal*: Supervisada comando por comando mediante aprobación individual (*"Yes, allow this time"*) para lecturas (`Get-Content requirements.txt`, `git status`) y pruebas (`.\venv\Scripts\python -m pytest`). Los commits en Git son realizados exclusivamente por el humano tras verificar las pruebas.
- **Adaptación Específica Comprobable y Retención del Progreso**:
  - Se incorporó en [`AGENT.md`](./AGENT.md) (Regla 3 y 4) la condición exacta de solapamiento de intervalos semiabiertos `(inicio_nuevo < fin_existente) AND (fin_nuevo > inicio_existente)` para admitir turnos consecutivos sin falsos positivos, verificada en [`src/service.py`](./src/service.py) y [`tests/test_reservas.py`](./tests/test_reservas.py).
  - El progreso, las decisiones técnicas y las revisiones se conservan versionados en este [`README.md`](./README.md) y en el historial de commits de Git.

## Sección 4: Registro de Decisiones y Tres Episodios de Delegación

### Decisiones Técnicas Significativas
1. **Persistencia en SQLite (`sqlite3` estándar) frente a archivos JSON o ORM externo**: Se eligió SQLite nativo porque garantiza atomicidad, consultas filtradas por estado/unidad e integridad transaccional sin añadir dependencias externas fuera de la librería estándar de Python.
2. **Fechas ISO 8601 *naive* frente a *timezone-aware***: Al tratarse de un único laboratorio físico local, el uso de fechas *naive* (`YYYY-MM-DDTHH:MM`) simplifica la interfaz y evita errores de conversión horaria, rechazando explícitamente entradas con `tzinfo` para mantener consistencia en las comparaciones.

### Episodio 1: Implementación TDD del Dominio, Repositorio SQLite y Pruebas Unitarias
- **Objetivo y Requisito**: Implementar la lectura del inventario fijo (`data/inventory.json`), el almacenamiento en SQLite (`data/reservas.db`), las reglas de negocio (validación de campos, bloqueo por solapamiento, turnos consecutivos, simultaneidad por unidad y cancelación) y las pruebas unitarias bajo TDD.
- **Contexto suministrado y Extracto de Instrucción**:
  - *Contexto*: [`AGENT.md`](./AGENT.md) (líneas 1–33) y [`data/inventory.json`](./data/inventory.json) (líneas 1–22).
  - *Extracto de instrucción*: *"Siguiendo estrictamente las reglas de AGENT.md, crea en src/ la lógica de dominio y persistencia en SQLite (data/reservas.db) para cargar el inventario desde data/inventory.json, consultar disponibilidad y crear reservas validando todos los campos y superposiciones horarias. Crea también en tests/ las pruebas unitarias con pytest..."*
- **Acción o Resultado del Agente**:
  1. Aplicó TDD creando primero [`tests/test_reservas.py`](./tests/test_reservas.py) (+269 líneas) y solicitando permiso para ejecutar `pytest` en fase roja (*Red phase*).
  2. Implementó los módulos [`src/exceptions.py`](./src/exceptions.py), [`src/models.py`](./src/models.py), [`src/inventory.py`](./src/inventory.py), [`src/repository.py`](./src/repository.py), [`src/service.py`](./src/service.py) y [`src/__init__.py`](./src/__init__.py).
  3. Durante la validación en Windows, detectó bloqueos de archivo temporal con `tempfile.NamedTemporaryFile` y refactorizó [`src/repository.py`](./src/repository.py) (+48 -43 líneas) y [`tests/test_reservas.py`](./tests/test_reservas.py) (+4 -7 líneas) para usar cierres deterministas de conexión y el fixture `tmp_path` de `pytest`, logrando 33 tests aprobados en `0.59s`.
- **Decisión Humana (Aceptar / Corregir / Rechazar) y Motivo**: **Aceptado con observación para el Episodio 2**.
  - Se revisó manualmente la lógica de colisión en [`src/service.py`](./src/service.py), confirmando el cumplimiento de `(inicio_nuevo < fin_existente) and (fin_nuevo > inicio_existente)` solo sobre reservas `ACTIVA`.
  - Se ejecutó manualmente `.\venv\Scripts\python -m pytest tests/ -v` comprobando los 33 tests aprobados en `0.58s`.
  - *Motivo de ajuste en el siguiente episodio*: Al auditar `test_persistencia_recarga_sqlite` (línea 249 de [`tests/test_reservas.py`](./tests/test_reservas.py)), se observó que solo comprueba la persistencia tras reinicio de una reserva `ACTIVA`, faltando comprobar en dicho test que una reserva `CANCELADA` también persiste tras reiniciar y mantiene liberado su intervalo, tal como pide la consigna.
- **Evidencia Verificable**:
  - Archivos: [`src/service.py`](./src/service.py), [`src/repository.py`](./src/repository.py), [`tests/test_reservas.py`](./tests/test_reservas.py).
  - Commit: `55b193c`
### Episodio 2: Verificación de Persistencia de Reservas Activas y Canceladas tras Reinicio y Reinicio de Datos
- **Objetivo y Requisito**: Corregir la cobertura de persistencia detectada en la revisión humana del Episodio 1 para comprobar explícitamente que tanto las reservas `ACTIVA` como las `CANCELADA` persisten tras detener y reiniciar el servicio sin borrar datos (liberando efectivamente el horario), e implementar el método `limpiar_reservas()` para el reinicio controlado de la base de datos
- **Contexto suministrado y Extracto de Instrucción**:
  - *Contexto*: [`AGENT.md`](./AGENT.md), [`src/repository.py`](./src/repository.py), [`src/service.py`](./src/service.py) y [`tests/test_reservas.py`](./tests/test_reservas.py)
  - *Extracto de instrucción*: *"[AGENT.md],[repository.py],[service.py],[test_reservas.py]  Al revisar `test_persistencia_recarga_sqlite` en `tests/test_reservas.py`, observé que solo verifica la persistencia tras reinicio de una reserva en estado 'ACTIVA'. La consigna exige expresamente comprobar la persistencia de reservas activas y canceladas tras detener y reiniciar sin borrar datos, manteniendo liberado el intervalo.

    Siguiendo estrictamente la metodología TDD de AGENT.md (primero escribe/actualiza las pruebas en `tests/test_reservas.py`, ejecuta pytest para ver el fallo en fase roja y luego implementa en `src/`):

    1. En `tests/test_reservas.py`, amplía `test_persistencia_recarga_sqlite` (o agrega `test_persistencia_recarga_sqlite_activas_y_canceladas`) utilizando `temp_db_path` donde:
      - Se instancie `ReservaService` apuntando al archivo SQLite temporal.
      - Se cree una reserva R1 ('ACTIVA') y una reserva R2 ('ACTIVA').
      - Se cancele R1 (pasando a estado 'CANCELADA').
      - Se cierre/elimine la instancia del servicio para simular la detención total de la aplicación.
      - Se cree una nueva instancia de `ReservaService` sobre exactamente el mismo archivo SQLite (`temp_db_path`), simulando el reinicio sin borrar datos.
      - Se recupere R1 y se verifique que su `id`, `unidad_id`, `solicitante` e intervalo siguen intactos y con `estado == 'CANCELADA'`.
      - Se recupere R2 y se verifique que sigue intacta con `estado == 'ACTIVA'`.
      - Se cree una nueva reserva R3 para la misma unidad y en el mismo horario exacto que ocupaba R1, verificando que la creación es exitosa tras el reinicio (el intervalo sigue liberado) y que el horario de R2 sigue bloqueando superposiciones.
    2. Agrega obligatoriamente el método `limpiar_reservas()` en `ReservaRepository` (`src/repository.py`) y `ReservaService` (`src/service.py`) que elimine todas las reservas de la tabla SQLite sin afectar `data/inventory.json` (para permitir el reinicio controlado de datos requerido en la Sección 2 del README), junto con su prueba unitaria `test_limpiar_reservas` en `tests/test_reservas.py`.
    3. Ejecuta pytest para validar el ciclo TDD completo hasta que toda la suite pase al 100%."*

- **Acción o Resultado del Agente**:
  1. **Fase Roja (TDD Red Phase)**: Modificó [`tests/test_reservas.py`](./tests/test_reservas.py) (+71 -12 líneas) ampliando la prueba de persistencia con el escenario `R1` (cancelada), `R2` (activa) y `R3` (reutilización del intervalo liberado tras reinicio), más el nuevo test `test_limpiar_reservas`, y solicitó permiso para correr `.\venv\Scripts\python -m pytest tests/ -v` comprobando el fallo esperado
  2. **Fase Verde (TDD Green Phase)**: Implementó `ReservaRepository.limpiar_reservas()` en [`src/repository.py`](./src/repository.py) (+7 líneas, ejecutando `DELETE FROM reservas;` en transacción segura) y `ReservaService.limpiar_reservas()` en [`src/service.py`](./src/service.py) (+4 líneas) sin alterar `data/inventory.json`, solicitando permiso para re-ejecutar `pytest` e informando **34 passed in 0.73s**
- **Decisión Humana (Aceptar / Corregir / Rechazar) y Motivo**: **Aceptado**.
  - Se revisó el *diff* de los 3 archivos (+84 -14 líneas) antes de pulsar *Accept all*, verificando que `limpiar_reservas()` solo elimina filas de SQLite sin tocar el catálogo JSON y que el test destruye/reinstancia `ReservaService` sobre el mismo archivo `.db`
  - Se ejecutó manualmente en terminal `.\venv\Scripts\python -m pytest tests/ -v`, confirmando las **34 pruebas aprobadas**.
- **Evidencia Verificable**:
  - Archivos modificados: [`src/repository.py`](./src/repository.py), [`src/service.py`](./src/service.py), [`tests/test_reservas.py`](./tests/test_reservas.py)
  - Commit: `de24b1a`

### Episodio 3: Construcción TDD de la Interfaz de Línea de Comandos (CLI) y Manejo Limpio de Errores
- **Objetivo y Requisito**: Implementar la interfaz de consola local en `main.py` utilizando `argparse` para exponer todas las operaciones requeridas (`inventario`, `disponibilidad`, `reservar`, `cancelar`, `listar` y `reset`), capturando excepciones de dominio sin *tracebacks* crudos y verificando su comportamiento mediante pruebas automatizadas aisladas con `--db`
- **Contexto suministrado y Extracto de Instrucción**:
  - *Contexto*: [`AGENT.md`](./AGENT.md), [`src/service.py`](./src/service.py) y [`src/models.py`](./src/models.py) (además de la inspección automática de [`src/exceptions.py`](./src/exceptions.py))
  - *Extracto de instrucción*: *"Para el Episodio 3, necesitamos construir la interfaz de línea de comandos (CLI) local en `main.py` para operar el sistema desde consola, respetando estrictamente la metodología TDD de AGENT.md: 1. Fase Roja (TDD Red Phase): Crea primero `tests/test_cli.py` (utilizando `capsys` y `tmp_path` mediante el argumento `--db`) con pruebas automáticas para todos los subcomandos... 2. Fase Verde (TDD Green Phase): Implementa `main.py` en la raíz del proyecto utilizando `argparse` conectado a `ReservaService`... 3. Manejo de Errores: Captura de forma limpia todas las excepciones de `src/exceptions.py` imprimiendo mensajes de error claros (sin mostrar tracebacks crudos)..."*
- **Acción o Resultado del Agente**:
  1. **Fase Roja (TDD Red Phase)**: Creó [`tests/test_cli.py`](./tests/test_cli.py) (+240 líneas) con 6 pruebas integrales de consola y solicitó permiso para ejecutar `pytest`, verificando el fallo esperado (`ModuleNotFoundError: No module named 'main'`)
  2. **Fase Verde y Auto-corrección de Subparsers**: Creó [`main.py`](./main.py) (+185 líneas). Al ejecutar `pytest` para verificar los tests de CLI, detectó que los subparsers de `argparse` sobrescribían el valor por defecto del argumento global `--db`, por lo que editó [`main.py`](./main.py) (+6 -2 líneas) configurando `default=argparse.SUPPRESS` en la herencia de los subparsers
  3. **Validación Final**: Re-ejecutó la suite completa informando **40 passed in 0.85s**
- **Decisión Humana (Aceptar / Corregir / Rechazar) y Motivo**: **Aceptado**.
  - Se revisó el código de [`main.py`](./main.py) y [`tests/test_cli.py`](./tests/test_cli.py), verificando la captura limpia de `ReservaError` hacia `stderr` con código de salida `1` y el ajuste `argparse.SUPPRESS` para respetar la ruta `--db` tanto antes como después del subcomando.
  - Se ejecutó manualmente en terminal la suite de 40 pruebas (`pytest tests/ -v`) y los comandos reales de `python main.py` comprobando la persistencia entre ejecuciones y la advertencia del subcomando `reset`.
- **Evidencia Verificable**:
  - Archivos creados: [`main.py`](./main.py), [`tests/test_cli.py`](./tests/test_cli.py)
  - Commit: `3995c37`