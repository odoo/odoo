# Consolidación de compra según fecha del pedido (enmienda a Fase 3)

- **Fecha:** 2026-07-15
- **Estado:** Aprobado (diseño)
- **Alcance:** El asistente de consolidación de compra deja de agrupar por `commitment_date` (fecha de entrega) y pasa a agrupar por `date_order` (fecha en que se tomó/confirmó el pedido). Se oculta el campo "Fecha de entrega" del formulario del pedido, ya que deja de usarse para cualquier cosa.
- **Enmienda a:** `docs/superpowers/specs/2026-07-14-consolidacion-compra-design.md` (Fase 3), que basaba la consolidación en la fecha de entrega. También sigue a `docs/superpowers/specs/2026-07-14-quitar-restriccion-fecha-entrega-design.md`, que ya había quitado la restricción de días sobre ese mismo campo.

---

## 1. Contexto

En uso real, el campo "Fecha de entrega" quedaba vacío la mayoría de las veces — vive en una pestaña secundaria del formulario del pedido y es fácil de pasar por alto, y el personal no le encontró valor real: los días de reparto ya son conocidos por todos de memoria, sin necesidad de anotarlos pedido por pedido. Como consecuencia, la consolidación de compra (Fase 3) salía vacía aunque hubiera pedidos confirmados, porque dependía de ese campo.

La alternativa: usar `date_order`, el campo nativo de Odoo que registra cuándo se confirmó el pedido. En este negocio los pedidos se confirman al instante al digitarlos (sin quedar pendientes como cotización — decisión ya tomada en la Fase 1), así que `date_order` coincide en la práctica con el día en que se tomó el pedido, sin que nadie tenga que llenar nada a mano.

## 2. Objetivo y definición de "hecho"

Que la consolidación de compra funcione sin depender de ningún campo que el personal tenga que llenar manualmente — se arma sola a partir de cuándo se confirmaron los pedidos.

**Éxito =** con 2-3 pedidos de prueba confirmados el mismo día (sin tocar ningún campo de fecha de entrega), el asistente con la fecha de hoy como valor por defecto genera correctamente el total consolidado por producto.

## 3. Diseño

### 3.1 `distribuidora_ventas` — ocultar el campo "Fecha de entrega"

Se agrega una vista que hereda el formulario nativo de `sale.order` y oculta el campo `commitment_date` (y su fila completa, incluida la fecha esperada que lo acompaña). El campo sigue existiendo a nivel de base de datos (es nativo de Odoo, no se puede quitar sin tocar el addon `sale`), simplemente deja de mostrarse — nadie lo va a llenar ni por error.

### 3.2 `distribuidora_compras` — cambiar la base de agregación

En `compra_consolidada_wizard.py`:

- El campo `fecha_entrega` se renombra a `fecha_pedido` (Date), con etiqueta "Fecha de pedidos".
- El valor por defecto pasa a ser simplemente la fecha de hoy (`fields.Date.context_today(self)`) — se elimina toda la lógica de "próximo lunes/miércoles/viernes" (`DELIVERY_WEEKDAYS`, el ciclo de búsqueda), ya no aplica.
- `_get_consolidated_lines()` busca pedidos confirmados (`state = 'sale'`) cuyo `date_order` caiga en `fecha_pedido`, comparando en hora de Costa Rica (mismo patrón ya usado y probado con `commitment_date`, ahora aplicado a `date_order`).

El reporte PDF y su vista (`compra_consolidada_wizard_views.xml`, `compra_consolidada_report.xml`) actualizan sus etiquetas de "Fecha de entrega" a "Fecha de pedidos".

## 4. Flujo

```
1. Durante el día se van tomando y confirmando pedidos (Fase 1) — cada uno
   queda con su date_order al momento de confirmarse, sin que nadie
   toque ningún campo de fecha de entrega.
2. La persona encargada abre "Consolidación de compra" — la fecha de hoy
   ya viene puesta por defecto.
3. Click en "Generar lista" → suma, por producto, todos los pedidos
   confirmados ese mismo día.
4. Se imprime y se usa igual que antes.
```

## 5. Fuera de alcance de esta fase

- Cualquier uso del campo `commitment_date` en el resto del sistema — queda oculto, no eliminado de la base de datos.
- Cambios a `distribuidora_ventas` más allá de ocultar ese campo.

## 6. Estrategia de pruebas

- Crear 2-3 pedidos de prueba confirmados el mismo día (sin fijar `commitment_date`), con líneas del mismo producto en cantidades distintas — confirmar que el total agregado por `date_order` es la suma correcta.
- Confirmar que un pedido confirmado un día distinto no se incluye en la suma.
- Confirmar que la comparación de fecha usa hora de Costa Rica (un pedido confirmado cerca de la medianoche UTC debe agruparse según el día calendario local, no el UTC).
- Confirmar que el campo "Fecha de entrega" ya no aparece en el formulario del pedido.
