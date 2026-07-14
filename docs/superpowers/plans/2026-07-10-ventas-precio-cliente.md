# Captura de pedidos y precios por cliente — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Dar de alta un addon nuevo (`distribuidora_ventas`) que soporte la captura de pedidos de clientes en Odoo con precio automático por lista de precios propia de cada cliente, y una fecha de entrega restringida a lunes/miércoles/viernes.

**Architecture:** Un solo addon Odoo, `distribuidora_ventas`, que depende de `sale`. No define modelos nuevos: (a) agrega datos de configuración (categorías de cliente) vía XML, y (b) extiende `sale.order` con una restricción (`@api.constrains`) sobre `commitment_date`. La asignación de precio por cliente usa el mecanismo nativo de `product.pricelist` de Odoo — no requiere código nuevo, solo se valida con un test de integración.

**Tech Stack:** Odoo 19 (Python 3.10-3.14), ORM de Odoo (`odoo.fields`, `odoo.api`), `odoo.tests.common.TransactionCase` para pruebas.

## Global Constraints

- Python 3.10–3.14 (según `CLAUDE.md` del repo).
- Imports ordenados: future → stdlib → third-party → odoo → odoo.addons (lo aplica `ruff`).
- Módulo nuevo vive en `addons/distribuidora_ventas/`, siguiendo la estructura de `addons/l10n_cr_fe_crlibre/` (el otro addon custom de este repo): `__init__.py`, `__manifest__.py`, `models/`, `data/`, `tests/`.
- Tests con `@tagged('post_install', '-at_install')`, igual que el resto del repo.
- No se toca `l10n_cr_fe_crlibre` ni ningún addon estándar de Odoo — este addon es aditivo, solo depende de `sale`.
- Fuera de alcance (confirmado en el spec): parseo automático de WhatsApp, consolidación de compra CENADA, inventario, entregas, migración real de datos desde GTI.

---

## Task 1: Scaffold del addon y categorías de cliente

**Files:**
- Create: `addons/distribuidora_ventas/__init__.py`
- Create: `addons/distribuidora_ventas/__manifest__.py`
- Create: `addons/distribuidora_ventas/data/res_partner_category_data.xml`
- Create: `addons/distribuidora_ventas/tests/__init__.py`
- Create: `addons/distribuidora_ventas/tests/test_partner_categories.py`

**Interfaces:**
- Produces: registros `res.partner.category` con XML IDs `distribuidora_ventas.res_partner_category_hotel`, `distribuidora_ventas.res_partner_category_supermercado`, `distribuidora_ventas.res_partner_category_restaurante` — usados en fases futuras para filtrar/reportar por tipo de cliente (spec §3.1).

- [ ] **Step 1: Escribir el test que falla (categorías todavía no existen)**

```python
# addons/distribuidora_ventas/tests/test_partner_categories.py
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestPartnerCategories(TransactionCase):

    def test_customer_categories_exist(self):
        hotel = self.env.ref('distribuidora_ventas.res_partner_category_hotel')
        supermercado = self.env.ref('distribuidora_ventas.res_partner_category_supermercado')
        restaurante = self.env.ref('distribuidora_ventas.res_partner_category_restaurante')
        self.assertEqual(hotel.name, 'Hotel')
        self.assertEqual(supermercado.name, 'Supermercado')
        self.assertEqual(restaurante.name, 'Restaurante')
```

```python
# addons/distribuidora_ventas/tests/__init__.py
from . import test_partner_categories
```

- [ ] **Step 2: Crear el manifest y el `__init__.py` raíz del addon (sin data todavía)**

```python
# addons/distribuidora_ventas/__manifest__.py
{
    'name': "Distribuidora - Ventas",
    'version': '19.0.1.0.0',
    'category': 'Sales/Sales',
    'summary': "Captura de pedidos y precios por cliente para la distribuidora",
    'author': "Distribuidora",
    'depends': ['sale'],
    'data': [],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
}
```

```python
# addons/distribuidora_ventas/__init__.py
```

- [ ] **Step 3: Instalar el módulo y correr el test para confirmar que falla**

Run: `python odoo-bin -d distribuidora_test -i distribuidora_ventas --test-enable --test-tags distribuidora_ventas --stop-after-init`

Expected: FAIL — `ValueError: External ID not found in the system: distribuidora_ventas.res_partner_category_hotel`

- [ ] **Step 4: Agregar el data file con las tres categorías**

```xml
<!-- addons/distribuidora_ventas/data/res_partner_category_data.xml -->
<odoo>
    <record id="res_partner_category_hotel" model="res.partner.category">
        <field name="name">Hotel</field>
    </record>
    <record id="res_partner_category_supermercado" model="res.partner.category">
        <field name="name">Supermercado</field>
    </record>
    <record id="res_partner_category_restaurante" model="res.partner.category">
        <field name="name">Restaurante</field>
    </record>
</odoo>
```

- [ ] **Step 5: Registrar el data file en el manifest**

```python
# addons/distribuidora_ventas/__manifest__.py
    'data': [
        'data/res_partner_category_data.xml',
    ],
```

- [ ] **Step 6: Reinstalar el módulo y correr el test para confirmar que pasa**

Run: `python odoo-bin -d distribuidora_test -u distribuidora_ventas --test-enable --test-tags distribuidora_ventas --stop-after-init`

Expected: PASS — `test_customer_categories_exist` en verde, 0 fallos.

- [ ] **Step 7: Commit**

```bash
git add addons/distribuidora_ventas/__init__.py addons/distribuidora_ventas/__manifest__.py \
        addons/distribuidora_ventas/data/res_partner_category_data.xml \
        addons/distribuidora_ventas/tests/__init__.py addons/distribuidora_ventas/tests/test_partner_categories.py
git commit -m "feat(distribuidora_ventas): scaffold addon con categorias de cliente"
```

---

## Task 2: Fecha de entrega restringida a lunes/miércoles/viernes

**Files:**
- Create: `addons/distribuidora_ventas/models/__init__.py`
- Create: `addons/distribuidora_ventas/models/sale_order.py`
- Create: `addons/distribuidora_ventas/tests/test_sale_order_delivery_day.py`
- Modify: `addons/distribuidora_ventas/__init__.py` (importar `models`)
- Modify: `addons/distribuidora_ventas/tests/__init__.py` (importar el nuevo test)

**Interfaces:**
- Consumes: ninguno de tasks anteriores.
- Produces: restricción sobre `sale.order.commitment_date` — cualquier fecha de entrega que no caiga en lunes/miércoles/viernes lanza `ValidationError` al guardar la orden (spec §3.3, §6).

- [ ] **Step 1: Escribir el test que falla**

```python
# addons/distribuidora_ventas/tests/test_sale_order_delivery_day.py
from datetime import datetime

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestSaleOrderDeliveryDay(TransactionCase):

    def setUp(self):
        super().setUp()
        self.partner = self.env['res.partner'].create({'name': 'Cliente Test'})

    def test_monday_is_accepted(self):
        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'commitment_date': datetime(2026, 7, 13, 8, 0, 0),  # lunes
        })
        self.assertTrue(order)

    def test_wednesday_is_accepted(self):
        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'commitment_date': datetime(2026, 7, 15, 8, 0, 0),  # miercoles
        })
        self.assertTrue(order)

    def test_friday_is_accepted(self):
        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'commitment_date': datetime(2026, 7, 17, 8, 0, 0),  # viernes
        })
        self.assertTrue(order)

    def test_tuesday_is_rejected(self):
        with self.assertRaises(ValidationError):
            self.env['sale.order'].create({
                'partner_id': self.partner.id,
                'commitment_date': datetime(2026, 7, 14, 8, 0, 0),  # martes
            })

    def test_sunday_is_rejected(self):
        with self.assertRaises(ValidationError):
            self.env['sale.order'].create({
                'partner_id': self.partner.id,
                'commitment_date': datetime(2026, 7, 19, 8, 0, 0),  # domingo
            })
```

```python
# addons/distribuidora_ventas/tests/__init__.py
from . import test_partner_categories
from . import test_sale_order_delivery_day
```

- [ ] **Step 2: Correr el test para confirmar que falla**

Run: `python odoo-bin -d distribuidora_test -u distribuidora_ventas --test-enable --test-tags distribuidora_ventas --stop-after-init`

Expected: FAIL — `test_tuesday_is_rejected` y `test_sunday_is_rejected` fallan porque no se lanza `ValidationError` (no existe la restricción todavía).

- [ ] **Step 3: Implementar la restricción**

```python
# addons/distribuidora_ventas/models/sale_order.py
from odoo import _, api, models
from odoo.exceptions import ValidationError

DELIVERY_WEEKDAYS = {0, 2, 4}  # lunes, miercoles, viernes (Python: lunes=0)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.constrains('commitment_date')
    def _check_commitment_date_is_delivery_day(self):
        for order in self:
            if order.commitment_date and order.commitment_date.weekday() not in DELIVERY_WEEKDAYS:
                raise ValidationError(_(
                    "La fecha de entrega debe ser lunes, miércoles o viernes."
                ))
```

```python
# addons/distribuidora_ventas/models/__init__.py
from . import sale_order
```

```python
# addons/distribuidora_ventas/__init__.py
from . import models
```

- [ ] **Step 4: Correr el test para confirmar que pasa**

Run: `python odoo-bin -d distribuidora_test -u distribuidora_ventas --test-enable --test-tags distribuidora_ventas --stop-after-init`

Expected: PASS — los 5 tests de `TestSaleOrderDeliveryDay` en verde.

- [ ] **Step 5: Commit**

```bash
git add addons/distribuidora_ventas/__init__.py addons/distribuidora_ventas/models/__init__.py \
        addons/distribuidora_ventas/models/sale_order.py \
        addons/distribuidora_ventas/tests/__init__.py addons/distribuidora_ventas/tests/test_sale_order_delivery_day.py
git commit -m "feat(distribuidora_ventas): restringir fecha de entrega a lunes/miercoles/viernes"
```

---

## Task 3: Precio automático por lista de precios del cliente

**Files:**
- Create: `addons/distribuidora_ventas/tests/test_customer_pricelist.py`
- Modify: `addons/distribuidora_ventas/tests/__init__.py` (importar el nuevo test)

**Interfaces:**
- Consumes: ninguno de tasks anteriores (usa `product.pricelist`, `res.partner.property_product_pricelist` y `sale.order.line.price_unit`, todos nativos de Odoo `sale`).
- Produces: prueba de regresión que documenta y protege el comportamiento central del spec (§3.2, §5) — que el precio de línea de un pedido se toma solo de la lista de precios del cliente, sin edición manual.

Esta task no agrega código de producción: el comportamiento ya lo resuelve Odoo nativamente al asignar `property_product_pricelist` en el cliente. El test sirve para dejar constancia ejecutable de que la configuración (cliente → pricelist → precio fijo por producto) funciona como describe el spec, y para detectar cualquier regresión futura.

- [ ] **Step 1: Escribir el test**

```python
# addons/distribuidora_ventas/tests/test_customer_pricelist.py
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestCustomerPricelist(TransactionCase):

    def setUp(self):
        super().setUp()
        self.product = self.env['product.product'].create({
            'name': 'Tomate',
            'type': 'consu',
            'list_price': 500.0,
        })
        self.pricelist_hotel = self.env['product.pricelist'].create({
            'name': 'Precios Hotel Test',
            'item_ids': [(0, 0, {
                'applied_on': '0_product_variant',
                'product_id': self.product.id,
                'compute_price': 'fixed',
                'fixed_price': 650.0,
            })],
        })
        self.pricelist_restaurante = self.env['product.pricelist'].create({
            'name': 'Precios Restaurante Test',
            'item_ids': [(0, 0, {
                'applied_on': '0_product_variant',
                'product_id': self.product.id,
                'compute_price': 'fixed',
                'fixed_price': 580.0,
            })],
        })
        self.hotel = self.env['res.partner'].create({
            'name': 'Hotel Test',
            'property_product_pricelist': self.pricelist_hotel.id,
        })
        self.restaurante = self.env['res.partner'].create({
            'name': 'Restaurante Test',
            'property_product_pricelist': self.pricelist_restaurante.id,
        })

    def test_order_line_price_follows_customer_pricelist(self):
        order_hotel = self.env['sale.order'].create({'partner_id': self.hotel.id})
        self.env['sale.order.line'].create({
            'order_id': order_hotel.id,
            'product_id': self.product.id,
            'product_uom_qty': 1,
        })
        order_restaurante = self.env['sale.order'].create({'partner_id': self.restaurante.id})
        self.env['sale.order.line'].create({
            'order_id': order_restaurante.id,
            'product_id': self.product.id,
            'product_uom_qty': 1,
        })

        self.assertEqual(order_hotel.order_line.price_unit, 650.0)
        self.assertEqual(order_restaurante.order_line.price_unit, 580.0)
```

```python
# addons/distribuidora_ventas/tests/__init__.py
from . import test_partner_categories
from . import test_sale_order_delivery_day
from . import test_customer_pricelist
```

- [ ] **Step 2: Correr el test y confirmar que pasa**

Run: `python odoo-bin -d distribuidora_test -u distribuidora_ventas --test-enable --test-tags distribuidora_ventas --stop-after-init`

Expected: PASS — `test_order_line_price_follows_customer_pricelist` en verde. (No debería fallar: es comportamiento nativo de Odoo; si falla, revisar que `type: 'consu'` tenga precios por variante habilitados y que `applied_on: '0_product_variant'` sea correcto para la versión de Odoo instalada.)

- [ ] **Step 3: Commit**

```bash
git add addons/distribuidora_ventas/tests/__init__.py addons/distribuidora_ventas/tests/test_customer_pricelist.py
git commit -m "test(distribuidora_ventas): validar precio de linea segun pricelist del cliente"
```

---

## Task 4: Verificación manual end-to-end

**Files:** ninguno (verificación manual, sin cambios de código).

**Interfaces:**
- Consumes: addon `distribuidora_ventas` completo (Tasks 1-3), instalado en una base de datos local.

- [ ] **Step 1: Instalar el módulo en una base local**

Run: `python odoo-bin -d distribuidora_demo -i distribuidora_ventas --stop-after-init`

- [ ] **Step 2: Levantar el servidor**

Run: `python odoo-bin -d distribuidora_demo --addons-path=addons,odoo/addons`

- [ ] **Step 3: Crear 2-3 clientes de prueba con listas de precios distintas**

En la UI (Ventas → Clientes): crear "Hotel Demo", "Restaurante Demo" y "Súper Demo". En cada uno, en la pestaña Ventas y Compras, crear/asignar una lista de precios propia con un precio fijo distinto para el mismo producto (ej. Tomate).

- [ ] **Step 4: Armar un pedido por cliente y confirmar el precio automático**

Ventas → Nueva orden → elegir cada cliente → agregar la línea de Tomate → confirmar visualmente que el precio unitario cambia solo, sin tocarlo, según el cliente elegido.

- [ ] **Step 5: Confirmar la fecha de entrega**

En cada orden, poner `Fecha de entrega` en un martes → confirmar que Odoo bloquea el guardado con el mensaje de validación. Cambiarla a lunes/miércoles/viernes → confirmar que guarda sin error.

- [ ] **Step 6: Confirmar la orden sin pasos intermedios**

Confirmar (botón "Confirmar") cada orden y verificar que pasa directo a estado "Orden de venta" (`sale`), sin pantalla de aprobación.
