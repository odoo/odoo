# Quitar restricción de fecha de entrega (enmienda a Fase 1 — Ventas)

- **Fecha:** 2026-07-14
- **Estado:** Aprobado (diseño)
- **Alcance:** Eliminar la validación que restringía `sale.order.commitment_date` a lunes/miércoles/viernes. Cualquier fecha queda permitida, sin aviso ni bloqueo.
- **Enmienda a:** `docs/superpowers/specs/2026-07-10-captura-pedidos-ventas-design.md` (Fase 1), que introdujo esta restricción — se revierte esa decisión puntual, el resto de esa fase (categorías de cliente, precio por lista de precios del cliente) no cambia.

---

## 1. Contexto

La Fase 1 asumió que la empresa reparte siempre lunes, miércoles y viernes, y agregó una validación que rechazaba cualquier otra fecha de entrega. En la práctica, en días festivos y a fin de año el CENADA cambia sus horarios de plazas, y la empresa termina repartiendo en días que normalmente no son de reparto. La validación dura bloqueaba esos casos legítimos y no tiene forma de anticiparlos (no hay un calendario de excepciones que mantener).

## 2. Objetivo y definición de "hecho"

Que se pueda guardar y confirmar un pedido con cualquier fecha de entrega, sin importar el día de la semana, sin ningún mensaje de error ni advertencia.

**Éxito =** un pedido con `commitment_date` en cualquier día (incluyendo los que antes se rechazaban, ej. martes o domingo) se guarda y confirma sin error.

## 3. Diseño

### 3.1 `distribuidora_ventas` — eliminar el modelo entero

El archivo `addons/distribuidora_ventas/models/sale_order.py` no tenía otro contenido más que esta validación (`DELIVERY_WEEKDAYS`, `_check_commitment_date_is_delivery_day`) — se elimina el archivo completo, y se quita su import de `addons/distribuidora_ventas/models/__init__.py`.

El archivo de test correspondiente, `addons/distribuidora_ventas/tests/test_sale_order_delivery_day.py`, probaba exactamente el comportamiento que se está quitando — se elimina, y se quita su import de `addons/distribuidora_ventas/tests/__init__.py`. Se reemplaza por un test nuevo y más simple que confirma que cualquier día de la semana se acepta sin error.

### 3.2 `distribuidora_compras` — sin cambios

El asistente de "Consolidación de compra" sigue sugiriendo el próximo lunes/miércoles/viernes como fecha por defecto (`_default_fecha_entrega` en `compra_consolidada_wizard.py`). Es solo un punto de partida cómodo para el caso normal, no una restricción — el usuario puede cambiarlo a cualquier fecha para los casos excepcionales. No depende de `distribuidora_ventas` ni de la validación que se está quitando, así que no hay nada que ajustar ahí.

## 4. Fuera de alcance de esta fase

- Cualquier forma de aviso/advertencia no bloqueante sobre días atípicos (se descartó explícitamente).
- Un calendario de excepciones o configuración de días de reparto — se decidió no restringir nada en vez de mantener una lista de excepciones.
- Cambios al asistente de consolidación de compra.

## 5. Estrategia de pruebas

- Confirmar que un pedido con `commitment_date` en martes, domingo, o cualquier otro día se guarda y confirma sin `ValidationError` (antes, estos días eran rechazados).
