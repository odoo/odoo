# Ajuste de cantidad antes de facturar (Fase 2 — Ventas)

- **Fecha:** 2026-07-14
- **Estado:** Aprobado (diseño)
- **Alcance:** Que los productos de la distribuidora se facturen por cantidad pedida (no por cantidad entregada), de forma que el ajuste manual de cantidades — hecho hoy con lápiz sobre la hoja de pedido en papel — se traduzca en editar la línea del pedido ya confirmado y facturar exactamente esa cantidad, sin depender del flujo de entregas/inventario.
- **Continúa de:** `docs/superpowers/specs/2026-07-10-captura-pedidos-ventas-design.md` (Fase 1 — captura de pedidos y precio por cliente).

---

## 1. Contexto

El ciclo real de la distribuidora (aclarado tras la Fase 1): los pedidos de todos los clientes se toman un día (ej. sábado) y se digitan en el sistema — eso es lo que resuelve la Fase 1. Con esa lista se arma la compra: parte se compra en el CENADA en la madrugada del día siguiente, y parte la traen proveedores cercanos directo a la bodega. Ese mismo día se arman los pedidos físicos para repartir.

Al armar el pedido físico no siempre se completa exactamente lo pedido — por ejemplo, un cliente pidió 5 kg de papa pero solo se pudieron surtir 3 kg. Hoy, el colaborador que arma el pedido anota esa diferencia a mano sobre la hoja de papel del pedido (o marca una "x" si se cumplió completo). Cuando la hoja vuelve para facturar, la persona encargada compara la hoja con el pedido ya digitado, corrige la cantidad en el sistema donde hizo falta, y factura solo lo que realmente se entregó.

La empresa maneja prácticamente cero inventario: lo que se pide se compra y se entrega en el mismo ciclo, no hay stock de por medio. Esto es clave para el diseño: no conviene apoyarse en el flujo estándar de Odoo de facturar "por cantidad entregada" (que exige validar una entrega/bodega), porque eso arrastraría todo el tema de inventario que esta empresa no maneja y que quedó fuera de alcance.

## 2. Objetivo y definición de "hecho"

Que la persona que factura pueda, sobre un pedido ya confirmado (Fase 1):

1. Editar la cantidad de cualquier línea (ej. de 5 kg a 3 kg) directamente en el pedido.
2. Facturar ese pedido, y que la factura refleje exactamente la cantidad que quedó en la línea — no la cantidad originalmente pedida.
3. Todo esto sin necesidad de validar ninguna entrega ni tocar inventario primero.

**Éxito =** con un pedido de prueba confirmado, se edita la cantidad de una línea, se genera la factura, y el monto facturado corresponde a la cantidad editada.

## 3. Diseño

### 3.1 `product.template` — facturar por cantidad pedida (nativo, sin código nuevo)

Verificado directamente contra este Odoo (`odoo shell`, ver evidencia en el plan de implementación): un producto nuevo de tipo "Goods" (`consu`) — el tipo que usan los productos de fruta/verdura — obtiene `invoice_policy = 'order'` ("Cantidades pedidas") automáticamente al crearlo, mientras no se fije explícitamente `'delivery'`. Es el cómputo nativo `product.template._compute_invoice_policy()` de Odoo (`addons/sale/models/product_template.py`), no algo que dependa de este addon. Lo que se había visto como `'delivery'` en la base son datos de demostración que lo fijan a mano, no el comportamiento por defecto real.

No hace falta ningún código nuevo para este punto — solo dejar un test que deje constancia de que un producto nuevo, sin tocar el campo, efectivamente queda en `'order'`.

Con `invoice_policy = 'order'`, Odoo factura por la cantidad que esté en `sale.order.line.product_uom_qty` al momento de crear la factura — que es exactamente el campo que la persona corrige a mano siguiendo la hoja de papel.

### 3.2 `sale.order.line` — sin cambios

No se agrega ningún campo nuevo. La cantidad pedida originalmente se sobreescribe con la corrección — no se conserva un histórico (decisión explícita: no hace falta para esta empresa). Confirmar la orden no bloquea (`locked = false` por defecto en Odoo), así que la línea sigue siendo editable después de confirmada sin ningún cambio de configuración adicional.

### 3.3 Sin controles ni bloqueos

No se agrega ninguna validación que impida facturar antes de revisar cantidades, ni ninguna marca de "revisado" por línea. El control sigue siendo enteramente el proceso manual con la hoja de papel, igual que hoy — agregar un control automático sería resolver un problema que la empresa no tiene.

## 4. Flujo

```
1. Pedido ya confirmado (Fase 1), con las cantidades originalmente pedidas.
2. Se arma el pedido físico en bodega; el colaborador anota a mano en la
   hoja cualquier diferencia (cantidad menor, o "x" si se cumplió completo).
3. La hoja vuelve a la persona que factura.
4. Esa persona abre el pedido en el sistema y corrige la cantidad de cada
   línea que cambió, siguiendo las anotaciones de la hoja.
5. Factura el pedido → Odoo genera la factura por la cantidad que quedó en
   cada línea (gracias a invoice_policy = 'order'), sin pedir validar
   ninguna entrega.
```

## 5. Fuera de alcance de esta fase

- Conservar la cantidad originalmente pedida en algún campo separado.
- Cualquier marca o campo de "revisado" por línea.
- Bloqueos o validaciones que impidan facturar sin revisión previa.
- El flujo de entregas/rutas de reparto (Fase futura).
- La consolidación de compra para CENADA y proveedores cercanos (Fase futura).
- Migración de datos reales del catálogo de productos — este diseño solo fija el comportamiento por defecto para productos que se creen de aquí en adelante.

## 6. Estrategia de pruebas

- Crear un producto de prueba sin especificar `invoice_policy` explícitamente y confirmar que su valor por defecto es `'order'`.
- Crear un pedido confirmado con una línea de cantidad 5, editar la cantidad a 3 sobre el pedido ya confirmado (sin errores de bloqueo), generar la factura (`_create_invoices()`), y confirmar que la línea de factura resultante tiene cantidad 3 — no 5.
