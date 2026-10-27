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

### Instalación, Persistencia y Ejecución
1. Crear y activar entorno virtual:
   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```
2. Instalar dependencias de prueba:
   ```powershell
   pip install -r requirements.txt
   ```
3. Ejecución de pruebas automáticas:
   ```powershell
   .\venv\Scripts\python -m pytest tests/ -v
   ```
4. **Persistencia y Reinicio de Datos**:
   - Los datos persisten automáticamente en `data/reservas.db`. El catálogo inicial se lee desde `data/inventory.json`.
   - **Advertencia**: Reiniciar o eliminar la base de datos (`data/reservas.db`) borra de forma permanente todas las reservas activas y el historial de cancelaciones registradas.
5. **Pendientes y Limitaciones Actuales**:
   - *Pendiente para Episodio 2*: Ampliar el test de persistencia tras reinicio para validar explícitamente reservas en estado `CANCELADA` y método de limpieza de datos.
   - *Pendiente para Episodio 3*: Interfaz de línea de comandos (CLI) para operación manual desde terminal con ejemplos de entrada y salida.
   - *Limitaciones de diseño*: Diseñado para ejecución local monousuario; no incluye control de concurrencia distribuida ni manejo de husos horarios múltiples.

### Verificación de Pruebas Automáticas (Distinción Agente vs. Ejecución Humana)
- **Informado por el agente**: Ejecución de 33 pruebas unitarias aprobadas en `0.59s`.
- **Verificación humana realmente ejecutada**: Se ejecutó manualmente en PowerShell la comprobación de versiones y la suite completa de pruebas, obteniendo 33 pruebas aprobadas en `0.58s`:

```powershell
PS> .\venv\Scripts\python --version
Python 3.12.2
PS> .\venv\Scripts\python -m pytest --version
pytest 9.1.1
PS> .\venv\Scripts\python -m pytest tests/ -v
platform win32 -- Python 3.12.2, pytest-9.1.1, pluggy-1.7.0
collected 33 items

tests/test_reservas.py::test_cargar_inventario_catalogo_fijo PASSED                                [  3%]
tests/test_reservas.py::test_creacion_reserva_valida_con_strings_iso PASSED                        [  6%]
tests/test_reservas.py::test_creacion_reserva_valida_con_objetos_datetime PASSED                   [  9%]
tests/test_reservas.py::test_rechazo_superposicion_identica PASSED                                 [ 12%]
tests/test_reservas.py::test_rechazo_superposicion_interna PASSED                                  [ 15%]
tests/test_reservas.py::test_rechazo_superposicion_envolvente PASSED                               [ 18%]
tests/test_reservas.py::test_rechazo_superposicion_parcial_inicio PASSED                           [ 21%]
tests/test_reservas.py::test_rechazo_superposicion_parcial_fin PASSED                              [ 24%]
tests/test_reservas.py::test_limites_consecutivos_posterior PASSED                                 [ 27%]
tests/test_reservas.py::test_limites_consecutivos_anterior PASSED                                  [ 30%]
tests/test_reservas.py::test_simultaneidad_en_unidades_distintas PASSED                            [ 33%]
tests/test_reservas.py::test_cancelacion_libera_horario_para_nueva_reserva PASSED                  [ 36%]
tests/test_reservas.py::test_cancelar_reserva_inexistente PASSED                                   [ 39%]
tests/test_reservas.py::test_consultar_disponibilidad PASSED                                       [ 42%]
tests/test_reservas.py::test_unidad_invalida_rechazada[MIC-99] PASSED                              [ 45%]
tests/test_reservas.py::test_unidad_invalida_rechazada[INVALID] PASSED                             [ 48%]
tests/test_reservas.py::test_unidad_invalida_rechazada[] PASSED                                    [ 51%]
tests/test_reservas.py::test_unidad_invalida_rechazada[   ] PASSED                                 [ 54%]
tests/test_reservas.py::test_unidad_invalida_rechazada[None] PASSED                                [ 57%]
tests/test_reservas.py::test_solicitante_invalido_rechazado[] PASSED                               [ 60%]
tests/test_reservas.py::test_solicitante_invalido_rechazado[   ] PASSED                            [ 63%]
tests/test_reservas.py::test_solicitante_invalido_rechazado[\t\n] PASSED                           [ 66%]
tests/test_reservas.py::test_solicitante_invalido_rechazado[None] PASSED                           [ 69%]
tests/test_reservas.py::test_solicitante_invalido_rechazado[123] PASSED                            [ 72%]
tests/test_reservas.py::test_fecha_inicio_mayor_o_igual_a_fin_rechazada PASSED                     [ 75%]
tests/test_reservas.py::test_formato_fecha_invalido_rechazado[no-es-fecha] PASSED                  [ 78%]
tests/test_reservas.py::test_formato_fecha_invalido_rechazado[2026/11/10 10:00] PASSED             [ 81%]
tests/test_reservas.py::test_formato_fecha_invalido_rechazado[12345] PASSED                        [ 84%]
tests/test_reservas.py::test_formato_fecha_invalido_rechazado[None] PASSED                         [ 87%]
tests/test_reservas.py::test_persistencia_recarga_sqlite PASSED                                    [ 90%]
tests/test_reservas.py::test_rechazo_fechas_con_timezone_aware PASSED                              [ 93%]
tests/test_reservas.py::test_listar_reservas_y_filtros PASSED                                      [ 96%]
tests/test_reservas.py::test_rutas_por_defecto PASSED                                              [100%]

33 passed in 0.58s
```

## Sección 3: Preparación del Agente
- **Entorno (Harness)**: Antigravity IDE (Versión 2.5.5).
- **Modelo**: `Gemini 3.8 Flash High Trust`.
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