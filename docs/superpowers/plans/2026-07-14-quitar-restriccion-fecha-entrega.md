# Quitar restricción de fecha de entrega — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Que `sale.order.commitment_date` acepte cualquier fecha, sin restricción de día de la semana.

**Architecture:** Se elimina la validación `@api.constrains` agregada en la Fase 1 (era todo el contenido de `distribuidora_ventas/models/sale_order.py`, así que el archivo y el paquete `models/` completo se eliminan). Se reemplaza el test que probaba la restricción por uno que confirma que cualquier día se acepta.

**Tech Stack:** Odoo 19 (Python 3.10-3.14), `odoo.tests.common.TransactionCase`.

## Global Constraints

- Python 3.10–3.14 (según `CLAUDE.md` del repo).
- Imports ordenados: future → stdlib → third-party → odoo → odoo.addons (lo aplica `ruff`).
- Tests con `@tagged('post_install', '-at_install')`, igual que el resto del addon.
- No se toca `distribuidora_compras` — su sugerencia de próximo lunes/miércoles/viernes en el asistente de consolidación de compra queda igual (es solo un valor por defecto, no una restricción, y no depende de este código).
- No se agrega ningún aviso/advertencia en su lugar — se confirmó explícitamente que no hace falta (spec §3.1, §4).

---

## Task 1: Quitar la restricción y su test

**Files:**
- Create: `addons/distribuidora_ventas/tests/test_sale_order_accepts_any_delivery_date.py`
- Delete: `addons/distribuidora_ventas/models/sale_order.py`
- Delete: `addons/distribuidora_ventas/models/__init__.py`
- Delete: `addons/distribuidora_ventas/tests/test_sale_order_delivery_day.py`
- Modify: `addons/distribuidora_ventas/__init__.py`
- Modify: `addons/distribuidora_ventas/tests/__init__.py`

**Interfaces:**
- Consumes: ninguno — no hay dependencias de otras tasks (task única).
- Produces: ningún método/campo nuevo. El comportamiento visible es que `sale.order.create()`/`write()` con cualquier `commitment_date` ya no lanza `ValidationError`.

- [ ] **Step 1: Escribir el test que falla contra el código actual (la restricción todavía existe)**

```python
# addons/distribuidora_ventas/tests/test_sale_order_accepts_any_delivery_date.py
from datetime import datetime

from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestSaleOrderAcceptsAnyDeliveryDate(TransactionCase):

    def setUp(self):
        super().setUp()
        self.partner = self.env['res.partner'].create({'name': 'Cliente Test'})

    def test_tuesday_is_accepted(self):
        # 2026-07-14 es martes: antes de este cambio, la restriccion de
        # distribuidora_ventas lo rechazaba.
        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'commitment_date': datetime(2026, 7, 14, 8, 0, 0),
        })
        self.assertTrue(order)

    def test_sunday_is_accepted(self):
        # 2026-07-19 es domingo: antes de este cambio, tambien se rechazaba.
        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'commitment_date': datetime(2026, 7, 19, 8, 0, 0),
        })
        self.assertTrue(order)
```

Agregar el import a `tests/__init__.py` sin quitar todavía el del test viejo (el viejo sigue existiendo por ahora, se borra en el Step 3):

```python
# addons/distribuidora_ventas/tests/__init__.py
from . import test_partner_categories
from . import test_sale_order_delivery_day
from . import test_customer_pricelist
from . import test_invoice_from_order_quantity
from . import test_sale_order_accepts_any_delivery_date
```

- [ ] **Step 2: Correr los tests para confirmar que el nuevo falla (la restricción sigue activa)**

Run: `MSYS_NO_PATHCONV=1 docker exec erp-odoo-1 odoo -d odoo --db_host=db --db_user=odoo --db_password=odoo --http-port=8099 --gevent-port=8101 -u distribuidora_ventas --test-enable --test-tags /distribuidora_ventas --stop-after-init`

Expected: FAIL — `test_tuesday_is_accepted` y `test_sunday_is_accepted` fallan con `ValidationError: La fecha de entrega debe ser lunes, miércoles o viernes...`. Los demás tests del addon (categorías, pricelist, cantidad facturada, y los del archivo viejo de restricción) siguen en verde.

- [ ] **Step 3: Eliminar la restricción, el archivo viejo de test, y sus imports**

```bash
rm addons/distribuidora_ventas/models/sale_order.py
rm addons/distribuidora_ventas/models/__init__.py
rmdir addons/distribuidora_ventas/models
rm addons/distribuidora_ventas/tests/test_sale_order_delivery_day.py
```

```python
# addons/distribuidora_ventas/__init__.py
# (archivo queda vacio: se borra la linea "from . import models",
#  ya no hay paquete models/ en este addon)
```

```python
# addons/distribuidora_ventas/tests/__init__.py
from . import test_partner_categories
from . import test_customer_pricelist
from . import test_invoice_from_order_quantity
from . import test_sale_order_accepts_any_delivery_date
```

- [ ] **Step 4: Actualizar el módulo y correr los tests para confirmar que pasan**

Run: `MSYS_NO_PATHCONV=1 docker exec erp-odoo-1 odoo -d odoo --db_host=db --db_user=odoo --db_password=odoo --http-port=8099 --gevent-port=8101 -u distribuidora_ventas --test-enable --test-tags /distribuidora_ventas --stop-after-init`

Expected: PASS — `0 failed, 0 error(s) of 6 tests` (11 tests antes de este cambio, menos los 7 de `test_sale_order_delivery_day.py` que se eliminaron, más los 2 nuevos = 6). Confirmar también que `TestSaleOrderDeliveryDay` no aparece en ningún lado del output — ya no debe existir.

- [ ] **Step 5: Commit**

```bash
git add addons/distribuidora_ventas/__init__.py addons/distribuidora_ventas/tests/__init__.py \
        addons/distribuidora_ventas/tests/test_sale_order_accepts_any_delivery_date.py
git add -u addons/distribuidora_ventas/models addons/distribuidora_ventas/tests/test_sale_order_delivery_day.py
git commit -m "fix(distribuidora_ventas): quitar restriccion de fecha de entrega lunes/miercoles/viernes"
```

---

## Task 2: Verificación manual

**Files:** ninguno (verificación manual, sin cambios de código).

- [ ] **Step 1: Actualizar el módulo en la base local**

Run: `MSYS_NO_PATHCONV=1 docker exec erp-odoo-1 odoo -d odoo --db_host=db --db_user=odoo --db_password=odoo --http-port=8099 --gevent-port=8101 -u distribuidora_ventas --stop-after-init`

- [ ] **Step 2: Reiniciar el servidor web para que recargue el código**

Run: `docker restart erp-odoo-1` (el servidor de `localhost:8069` no recarga código Python en caliente; sin este paso, el navegador seguiría viendo la restricción vieja aunque la base de datos ya esté actualizada).

- [ ] **Step 3: Confirmar en la UI**

En `http://localhost:8069`, abrir o crear un pedido, poner la "Fecha de entrega" (pestaña "Otra información") en un martes o domingo, guardar → confirmar que ya no aparece el mensaje de error.
