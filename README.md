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

## Sección 2: Solución

## Sección 3: Preparación del Agente
- **Entorno**: Antigravity IDE (Versión 2.5.5)
- **Modelo**: Gemini 3.8 Flash High Trust (seleccionado por velocidad de iteración en TDD y capacidad de uso de herramientas de sistema de archivos y terminal).
- **Instrucciones y Contexto**: Definidos en [`AGENT.md`](./AGENT.md). Se suministró como contexto `AGENT.md` y `data/inventory.json`, excluyendo `venv/`, `challenge-agents.pdf` y archivos de caché.
- **Permisos y Control Humano**: Permiso de lectura/escritura en `src/` y `tests/`. Ejecución de comandos de terminal (`pytest`) bajo supervisión y aprobación humana antes de cada commit.

## Sección 4: Registro de Decisiones y Tres Episodios de Delegación
