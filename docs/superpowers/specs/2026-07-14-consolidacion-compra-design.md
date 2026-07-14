# Consolidación de compra para CENADA y proveedores cercanos (Fase 3 — Compras)

- **Fecha:** 2026-07-14
- **Estado:** Aprobado (diseño)
- **Alcance:** Un asistente que, dada una fecha de entrega (lunes/miércoles/viernes), genera un PDF con el total por producto necesario entre todos los pedidos confirmados de ese ciclo — la lista que hoy se arma a mano para salir a comprar al CENADA y avisarle a los proveedores cercanos. No genera órdenes de compra formales ni separa la lista por origen.
- **Continúa de:** `docs/superpowers/specs/2026-07-10-captura-pedidos-ventas-design.md` (Fase 1 — captura de pedidos) y `docs/superpowers/specs/2026-07-14-ajuste-cantidad-antes-de-facturar-design.md` (Fase 2 — ajuste de cantidad).

---

## 1. Contexto

Recapitulando el ciclo real del negocio: los pedidos de todos los clientes se toman un día (ej. sábado) y se digitan en el sistema (Fase 1). Con esos pedidos hay que armar la lista general de compra — hoy se hace a mano — para salir de madrugada al CENADA (mercado mayorista) y para avisarle a los proveedores cercanos cuánto traer a la bodega.

En el CENADA compran tanto a proveedores fijos como, cuando hace falta, a quien tenga el producto disponible ese día — no hay un vendedor único registrado por producto. A los proveedores cercanos también se les avisa cada ciclo cuánto traer, según la demanda de ese ciclo (no manejan una cantidad fija de antemano). Por eso, lo que realmente hace falta no es una orden de compra formal a un proveedor específico, sino **una lista clara del total necesario por producto** — con eso, la persona que compra decide en el momento dónde conseguir cada cosa. Esa lista se lleva impresa, porque en el CENADA no siempre hay forma de consultar el sistema.

## 2. Objetivo y definición de "hecho"

Dada una fecha de entrega, el sistema debe generar un PDF que muestre, para cada producto pedido por cualquier cliente con entrega en esa fecha, la cantidad total a comprar (suma de todos los pedidos confirmados de esa fecha).

**Éxito =** con 2-3 pedidos de prueba confirmados con la misma fecha de entrega, cada uno con líneas del mismo producto en cantidades distintas, el PDF generado muestra la suma correcta por producto — no los pedidos por separado.

## 3. Diseño

### 3.1 Addon nuevo `distribuidora_compras`

Se crea un addon separado de `distribuidora_ventas`, con dependencia de `sale` (para leer `sale.order`/`sale.order.line`). Aunque esta fase solo lee datos de ventas, el propósito de este addon es la compra — separarlo deja espacio limpio para cuando más adelante se generen órdenes de compra reales, sin mezclar esa responsabilidad dentro del addon de ventas.

### 3.2 Asistente `distribuidora.compra.consolidada.wizard` (`TransientModel`)

- Campo `fecha_entrega` (Date), con valor por defecto la próxima fecha de entrega que corresponda (el lunes, miércoles o viernes más próximo a partir de hoy).
- Botón "Generar lista" → busca todas las `sale.order` con `state = 'sale'` cuyo `commitment_date` caiga en `fecha_entrega`, agrupa sus líneas por `product_id` y suma `product_uom_qty`.
- La comparación de fecha se hace en hora de Costa Rica, no en UTC — mismo cuidado que se tomó en la Fase 1 al corregir el bug de zona horaria de la restricción de fecha de entrega (`commitment_date` es UTC internamente; comparar el día calendario directo sobre el valor UTC llevaría al mismo error de límite de día que ya se corrigió ahí).

### 3.3 Reporte PDF

Lista simple con: producto, unidad de medida, cantidad total. Sin precios, sin desglose por cliente, sin separar por origen (CENADA vs. proveedor) — la persona que compra decide eso con su propio criterio. Si no hay pedidos confirmados para la fecha elegida, el PDF se genera igual, con un aviso de que no hay nada que comprar para esa fecha (no un error).

## 4. Flujo

```
1. Todos los pedidos del ciclo ya están confirmados en el sistema (Fase 1).
2. La persona encargada abre el asistente "Consolidación de compra",
   elige (o deja) la fecha de entrega correspondiente.
3. Click en "Generar lista" → el sistema suma, por producto, todas las
   cantidades pedidas por todos los clientes con esa fecha de entrega.
4. Se imprime el PDF y se lleva al CENADA / se usa para avisar a los
   proveedores cercanos cuánto traer.
```

## 5. Fuera de alcance de esta fase

- Separar la lista por origen (qué se compra en CENADA vs. qué se le pide a cada proveedor fijo).
- Generar órdenes de compra (`purchase.order`) reales o formales.
- Registrar el costo real de lo comprado en CENADA, o compararlo contra lo presupuestado.
- Cualquier automatización de aviso a proveedores (llamada, WhatsApp, etc.) — la lista solo informa, la comunicación con proveedores sigue siendo manual.
- Entregas y rutas de reparto (fase futura).

## 6. Estrategia de pruebas

- Crear 2-3 pedidos de prueba confirmados con la misma `fecha_entrega`, cada uno con una línea del mismo producto en cantidades distintas (ej. 2 kg, 3 kg, 5 kg) — confirmar que el total agregado es la suma correcta (10 kg).
- Confirmar que un pedido confirmado con una fecha de entrega distinta a la elegida no se incluye en la suma.
- Confirmar que un pedido en estado borrador (no confirmado) con la misma fecha de entrega no se incluye en la suma.
- Confirmar que elegir una fecha sin pedidos confirmados genera el PDF con el aviso de "nada que comprar", no un error.
- Confirmar que la comparación de fecha usa hora de Costa Rica (un pedido con `commitment_date` que cruce la medianoche UTC pero corresponda al día local elegido debe incluirse correctamente).
