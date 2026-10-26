# Sistema de Reservas de Laboratorio - Instrucciones de Agente

## Filosofía de Trabajo
- Metodología estricta: TDD (Test-Driven Development). Escribir primero las pruebas unitarias y luego la implementación.
- Todo cambio debe ser reproducible localmente mediante pytest sin requerir servicios ni credenciales de IA externas.

## Catálogo Fijo de Equipos 
- MIC-01: Microscopio digital
- MIC-02: Microscopio digital
- OSC-01: Osciloscopio
- MUL-01: Multímetro
- FUE-01: Fuente de alimentación

## Reglas de Negocio
1. Campos de reserva: 
   - `id`: Identificador único (autoincremental o UUID).
   - `unidad_id`: Debe coincidir estrictamente con una unidad del catálogo fijo.
   - `solicitante`: String no vacío ni compuesto exclusivamente por espacios en blanco.
   - `fecha_inicio`: Objeto `datetime` / Formato ISO 8601 (`YYYY-MM-DDTHH:MM`).
   - `fecha_fin`: Objeto `datetime` / Formato ISO 8601 (`YYYY-MM-DDTHH:MM`).
   - `estado`: Valor exacto `'ACTIVA'` o `'CANCELADA'`.
2. Validación temporal: fecha_inicio < fecha_fin.
3. Superposición: Rechazar solapamientos para reservas con estado 'ACTIVA' de la misma unidad física. Condición de solapamiento: (inicio_nuevo < fin_existente) AND (fin_nuevo > inicio_existente).
4. Turnos contiguos: Si una reserva termina exactamente a las 11:00, otra reserva de la misma unidad puede iniciar en el mismo horario exactamente a las 11:00 (ambas son válidas y no colisionan).
5. Simultaneidad: Diferentes unidades físicas (ej. MIC-01 y MIC-02) pueden reservarse en el mismo rango horario.
6. Cancelación: Libera el horario para futuras reservas, pero el registro original se conserva con su ID y estado 'CANCELADA' para tener un historial.
7. Consulta de disponibilidad: Permitir consultar si una unidad está libre en un intervalo dado aplicando exactamente las mismas reglas de superposición (ignorando canceladas).
9. Persistencia: Almacenar en SQLite local ('data/reservas.db') para que los datos persistan tras detener y reiniciar.

## Restricciones
- **Zona horaria y Fechas**: Usar objetos `datetime` naive parseados desde ISO 8601 (`YYYY-MM-DDTHH:MM`), asumiendo hora local del laboratorio. Permitir fechas en cualquier año/mes para facilitar tests deterministas.
- **Restricciones**: No modificar `data/inventory.json`. El inventario usa las claves `"id"` y `"name"`.
- **Estructura**: Colocar el código fuente dentro de `src/` y las pruebas automáticas en `tests/`.