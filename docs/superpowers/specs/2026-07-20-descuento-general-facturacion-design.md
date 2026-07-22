# Descuento general en Facturación

- **Fecha:** 2026-07-20
- **Estado:** Aprobado (diseño)
- **Alcance:** Un asistente en la factura de cliente que aplica un descuento general (%) a toda la factura, reutilizando el motor de cálculo de impuestos nativo de Odoo. Sin cambios en Preventas (Ventas).

---

## 1. Contexto

Odoo trae nativo un asistente de "Descuento" en el pedido de venta (Preventas), con modo "Descuento general" que agrega una línea de descuento calculando impuestos correctamente. Ese asistente vive únicamente en `sale.order` — no hay equivalente en la factura de cliente (`account.move`).

Para esta empresa, el descuento se termina de decidir cuando están revisando y facturando (mismo momento en que ya ajustan cantidades reales, Fase 2), no al tomar el pedido. Se investigó el código de Odoo: el cálculo de impuestos del descuento (`AccountTax._prepare_global_discount_lines`, en el módulo `account`, genérico) no es exclusivo de `sale` — el asistente de Preventas es solo una capa de interfaz sobre esa pieza genérica. Se puede construir el mismo tipo de asistente para `account.move`, reutilizando ese motor ya probado, en vez de calcular impuestos desde cero.

El botón/campo de descuento en Preventas **no se toca** — sigue disponible ahí también, sin cambios.

## 2. Objetivo y definición de "hecho"

Que, sobre una factura de cliente en borrador, se pueda aplicar un % de descuento general con un botón, y que la factura resultante refleje el descuento con los impuestos calculados correctamente.

**Éxito =** con una factura de prueba con 2-3 líneas de productos (con IVA), aplicar un 10% de descuento general agrega una línea de descuento con el monto e impuestos correctos, y el total de la factura baja el 10% correspondiente.

## 3. Diseño

### 3.1 Asistente `distribuidora.factura.descuento.wizard` (`TransientModel`)

- Campo `porcentaje` (Float), único campo del asistente.
- Botón "Aplicar" → toma las líneas de producto de la factura (`account.move.line`, excluyendo secciones/notas), las prepara con `AccountTax._prepare_base_line_for_taxes_computation` (mismo método genérico que usa el asistente de Preventas, funciona igual con líneas de factura), llama a `AccountTax._prepare_global_discount_lines(amount_type='percent', amount=porcentaje, ...)`, y crea las líneas de descuento resultantes en la factura.
- Sigue el mismo patrón que el asistente nativo `sale.order.discount` (modo "Descuento general"): usa un producto de descuento (reutiliza `company.sale_discount_product_id`, el mismo que ya usa Preventas — si no existe, se crea igual que hace el asistente nativo).

### 3.2 Botón "Descuento general" en la factura

Vive en `distribuidora_ventas` (continuación del flujo precio → cantidad → descuento antes de facturar ya construido ahí). Visible solo cuando la factura está en borrador (`state == 'draft'`) — una vez validada, no se puede aplicar (igual que el asistente nativo de Preventas se oculta con el pedido bloqueado).

### 3.3 Descuento por línea en Facturación

Ya existe nativo (columna "Disc.%" en las líneas de factura). Se agrega solo una vista que la muestre por defecto (`optional="show"` en vez de `optional="hide"`), para que no haya que buscarla en el selector de columnas cada vez.

## 4. Fuera de alcance

- Cualquier cambio en Preventas (`sale.order`) — el botón/campo de descuento existente ahí sigue igual, sin tocar.
- Modo "monto fijo" o "en todas las líneas" del asistente — solo porcentaje general (confirmado).
- Descuento en facturas de proveedor (vendor bills) — solo facturas de cliente.

## 5. Estrategia de pruebas

- Crear una factura de prueba con 2-3 líneas de producto con impuesto, aplicar un 10% de descuento general, confirmar que se agrega una línea de descuento y que el total baja el 10% correcto (impuestos incluidos).
- Confirmar que el botón no aparece (o está inactivo) en una factura ya validada.
- Confirmar que la columna de descuento por línea aparece visible por defecto en la factura, sin tener que activarla a mano.
