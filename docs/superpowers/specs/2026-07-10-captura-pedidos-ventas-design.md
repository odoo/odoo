# Captura de pedidos y precios por cliente (Fase 1 — Ventas)

- **Fecha:** 2026-07-10
- **Estado:** Aprobado (diseño)
- **Alcance:** Reemplazar la digitación manual de pedidos en GTI por el módulo de Ventas de Odoo (`sale.order`), con precio automático por cliente vía listas de precios. Consolidación de compra para CENADA, inventario, entregas y facturación quedan para fases posteriores.
- **Precede a:** fases futuras de consolidación de compra (CENADA), entregas (lun/mié/vie) e inventario, que se diseñarán por separado sobre esta base.

---

## 1. Contexto

La empresa distribuye frutas, verduras y hortalizas a hoteles, supermercados y restaurantes en Costa Rica. Los pedidos llegan por llamada telefónica o WhatsApp y hoy se digitan manualmente en GTI, un sistema con deficiencias conocidas (incluida la facturación electrónica, que ya se está resolviendo aparte con `l10n_cr_fe_crlibre`).

El problema principal reportado para esta fase: **cada cliente tiene un precio negociado individualmente, producto por producto**, y en GTI ese precio hay que cambiarlo a mano cada vez que se arma un pedido o se factura — lo cual hace lenta la digitación.

Los pedidos no siguen un patrón fijo (no se repite lo mismo cada ciclo), el volumen es bajo (~20-30 pedidos por ciclo de entrega, una sola persona digitando), y una vez tomado el pedido no requiere aprobación: al ser clientes establecidos con precio ya acordado, el pedido queda confirmado de inmediato.

El catálogo de productos ya existe en Odoo como una lista general (sin precios por cliente todavía). Los contactos de clientes y sus precios negociados **no** están cargados; esta fase arranca con datos ficticios de placeholder que los dueños del negocio ajustarán después.

---

## 2. Objetivo y definición de "hecho"

Al tomar un pedido por teléfono o WhatsApp, el encargado debe poder:

1. Elegir el cliente en una orden de venta de Odoo.
2. Agregar líneas de producto, donde el precio de cada producto se autocompleta según la lista de precios de ese cliente específico — sin editar precios a mano.
3. Confirmar el pedido de inmediato (sin pasar por cotización/aprobación).
4. Registrar la fecha de entrega, restringida a lunes, miércoles o viernes.

**Éxito =** con 2-3 clientes de prueba, cada uno con su propia lista de precios, se arma un pedido por cliente y el precio correcto aparece solo al seleccionar el producto, sin ninguna edición manual de precio.

---

## 3. Modelo de datos

### 3.1 `res.partner` (clientes)

- Un contacto por cliente (hotel, supermercado o restaurante).
- Categoría/etiqueta de partner para poder filtrar y reportar por tipo de cliente en fases futuras (ej. agrupar entregas o compras por segmento). No se usa para calcular precio — el precio es 100% individual por cliente, no por categoría.
- Campo `property_product_pricelist` apuntando a la lista de precios propia de ese cliente.

### 3.2 `product.pricelist` (una por cliente)

- Se crea una lista de precios por cliente (o por grupo de clientes que compartan exactamente los mismos precios negociados, si ese caso llegara a existir).
- Reglas de tipo "Precio fijo" por producto (`product.pricelist.item`, `compute_price = 'fixed'`), sobre el catálogo de productos que ya existe en Odoo.
- Se arranca con precios ficticios/placeholder; los dueños del negocio los ajustan después editando directamente los ítems de cada lista — sin necesidad de tocar configuración.
- Se descartan explícitamente: (a) una lista única con descuento/recargo % por categoría de cliente — no aplica porque el precio no es un % sobre un base, es negociado producto por producto; (b) una tabla de precios por cliente construida a medida fuera del sistema de pricelists — reinventaría algo que Odoo ya resuelve nativamente, sumando código para mantener sin beneficio.

### 3.3 `sale.order`

- Sin cambios de flujo de estados: se crea y se confirma directo (`draft` → `sale`), sin paso de cotización enviada/aprobada.
- Campo de fecha de entrega (`commitment_date`, ya nativo) con una validación (`@api.constrains`) que rechace fechas que no caigan en lunes, miércoles o viernes.

---

## 4. Flujo de captura del pedido

```
1. Cliente llama o escribe por WhatsApp su pedido.
2. Encargado abre Ventas → Nueva orden → selecciona el cliente.
3. Por cada producto pedido: lo busca y lo agrega a la línea de la orden.
   → El precio unitario se completa solo, tomado de la pricelist del cliente.
4. Encargado define la fecha de entrega (lunes/miércoles/viernes).
5. Encargado confirma la orden → queda en firme (estado "sale"), lista para
   alimentar la consolidación de compra de una fase futura.
```

---

## 5. Fuera de alcance de esta fase

- Automatizar la lectura/parseo de mensajes de WhatsApp para crear pedidos — el encargado sigue leyendo el mensaje y digitando, ahora en Odoo en vez de GTI.
- Consolidación de la lista de compra para CENADA (agregación de demanda entre pedidos).
- Órdenes de compra a CENADA y a proveedores cercanos.
- Inventario, recepción de mercadería y entregas (rutas lun/mié/vie).
- Facturación (ya cubierta aparte por el trabajo en curso de `l10n_cr_fe_crlibre`).
- Migración real de clientes, productos y precios negociados desde GTI — se usan datos ficticios de partida en esta fase.

---

## 6. Estrategia de pruebas

- Crear 2-3 clientes de prueba, cada uno con su propia lista de precios (reglas de precio fijo distintas para los mismos productos).
- Armar una orden de venta por cliente, agregar las mismas líneas de producto en los tres casos, y confirmar que el precio unitario difiere correctamente según el cliente sin edición manual.
- Confirmar que una orden con `commitment_date` en martes/jueves/sábado/domingo es rechazada por la validación, y que lunes/miércoles/viernes se acepta.
- Confirmar que una orden se puede pasar de `draft` a `sale` sin pasos intermedios de aprobación.
