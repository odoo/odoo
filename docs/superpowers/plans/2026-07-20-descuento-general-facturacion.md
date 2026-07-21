# Descuento general en Facturación — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Un botón "Descuento general" en la factura de cliente (borrador) que aplica un % de descuento a toda la factura, con impuestos calculados correctamente.

**Architecture:** Un wizard `TransientModel` en `distribuidora_ventas` reutiliza el motor genérico de descuentos de Odoo (`account.tax._prepare_global_discount_lines`, ya usado internamente por el asistente nativo de Preventas) para crear una línea de descuento en `account.move`. Sin cambios en `sale.order`/Preventas.

**Tech Stack:** Odoo 19 (Python 3.10-3.14), `odoo.tests.common.TransactionCase`, vistas XML.

## Global Constraints

- Imports ordenados: future → stdlib → third-party → odoo → odoo.addons (lo aplica `ruff`).
- Tests con `@tagged('post_install', '-at_install')`, `TransactionCase`, igual que el resto del addon.
- No se toca `sale.order` ni ninguna vista de Preventas — el descuento existente ahí sigue igual (spec §4).
- Solo modo "porcentaje general" — no monto fijo, no "en todas las líneas" (spec §4, confirmado).
- Solo facturas de cliente (`move_type in ('out_invoice', 'out_refund')`) — no facturas de proveedor (spec §4).
- El botón solo debe estar disponible mientras la factura está en borrador (`state == 'draft'`) (spec §3.2).
- **Dato de la API de Odoo verificado en esta versión (prototipado en vivo contra una factura real, no solo leído del código):**
  - `account.move.line.display_type` vale `'product'` para una línea de producto normal — a diferencia de `sale.order.line.display_type`, que es `False`/vacío. El filtro de líneas debe ser `line.display_type == 'product'`, **no** `not line.display_type` (ese error se probó y se confirmó que devuelve 0 líneas).
  - `account.tax._prepare_base_line_for_taxes_computation`, `_add_tax_details_in_base_lines`, `_round_base_lines_tax_details` y `_prepare_global_discount_lines` son genéricos (viven en `account`, no en `sale`) y funcionan igual de bien pasándoles `account.move.line` que `sale.order.line` — verificado con una factura de prueba real: 2 unidades a ₡1000 + IVA 13%, descuento de 10% → `amount_untaxed` bajó de 2000.0 a 1800.0 exacto.
  - `_prepare_global_discount_lines` con `amount_type='percent'` espera `amount` en escala 0-100 (ej. `10.0` para 10%), igual que el campo nativo `discount` de `account.move.line` — no hace falta convertir a fracción 0-1.
  - `account.move.line` no tiene el campo `technical_price_unit` que sí tiene `sale.order.line` — no incluirlo en los valores de creación.

---

## Task 1: Wizard y lógica de aplicación del descuento

**Files:**
- Create: `addons/distribuidora_ventas/wizards/__init__.py`
- Create: `addons/distribuidora_ventas/wizards/factura_descuento_wizard.py`
- Create: `addons/distribuidora_ventas/tests/test_factura_descuento_wizard.py`
- Modify: `addons/distribuidora_ventas/__init__.py`
- Modify: `addons/distribuidora_ventas/__manifest__.py`
- Modify: `addons/distribuidora_ventas/tests/__init__.py`

**Interfaces:**
- Produces: modelo `distribuidora.factura.descuento.wizard` con campos `move_id` (Many2one `account.move`) y `porcentaje` (Float, 0-100), y método `action_aplicar(self)` que agrega la línea de descuento a `move_id`. Usado por Task 2 desde el botón de la factura.

- [ ] **Step 1: Escribir los tests que fallan (el modelo todavía no existe)**

```python
# addons/distribuidora_ventas/tests/test_factura_descuento_wizard.py
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestFacturaDescuentoWizard(TransactionCase):

    def setUp(self):
        super().setUp()
        self.tax = self.env['account.tax'].search([
            ('type_tax_use', '=', 'sale'),
            ('company_id', '=', self.env.company.id),
        ], limit=1)
        self.product = self.env['product.product'].create({
            'name': 'Producto Test Descuento',
            'list_price': 1000.0,
            'taxes_id': [(6, 0, self.tax.ids)],
        })
        self.partner = self.env['res.partner'].create({'name': 'Cliente Test Descuento'})
        self.move = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner.id,
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product.id,
                'quantity': 2,
                'price_unit': 1000.0,
                'tax_ids': [(6, 0, self.tax.ids)],
            })],
        })

    def test_applies_percentage_discount_with_correct_taxes(self):
        self.assertEqual(self.move.amount_untaxed, 2000.0)
        wizard = self.env['distribuidora.factura.descuento.wizard'].create({
            'move_id': self.move.id,
            'porcentaje': 10.0,
        })
        wizard.action_aplicar()

        self.assertEqual(self.move.amount_untaxed, 1800.0)
        discount_lines = self.move.invoice_line_ids.filtered(
            lambda l: l.product_id == self.move.company_id.sale_discount_product_id
        )
        self.assertEqual(len(discount_lines), 1)
        self.assertEqual(discount_lines.price_unit, -200.0)

    def test_rejects_percentage_over_100(self):
        with self.assertRaises(ValidationError):
            self.env['distribuidora.factura.descuento.wizard'].create({
                'move_id': self.move.id,
                'porcentaje': 150.0,
            })

    def test_rejects_zero_percentage(self):
        with self.assertRaises(ValidationError):
            self.env['distribuidora.factura.descuento.wizard'].create({
                'move_id': self.move.id,
                'porcentaje': 0.0,
            })
```

```python
# addons/distribuidora_ventas/tests/__init__.py
from . import test_partner_categories
from . import test_customer_pricelist
from . import test_invoice_from_order_quantity
from . import test_sale_order_accepts_any_delivery_date
from . import test_sale_order_form_hides_commitment_date
from . import test_pricelist_menu
from . import test_factura_descuento_wizard
```

- [ ] **Step 2: Crear el `__init__.py` de `wizards/` (sin el modelo todavía) y actualizar el `__init__.py` raíz**

```python
# addons/distribuidora_ventas/wizards/__init__.py
from . import factura_descuento_wizard
```

```python
# addons/distribuidora_ventas/__init__.py
from . import wizards
```

- [ ] **Step 3: Correr los tests para confirmar que fallan**

Run: `MSYS_NO_PATHCONV=1 docker exec erp-odoo-1 odoo -d odoo --db_host=db --db_user=odoo --db_password=odoo --http-port=8099 --gevent-port=8101 -u distribuidora_ventas --test-enable --test-tags /distribuidora_ventas --stop-after-init`

Expected: FAIL — error de módulo/atributo porque `factura_descuento_wizard.py` todavía no existe (el `wizards/__init__.py` del Step 2 falla al importar).

- [ ] **Step 4: Implementar el wizard**

```python
# addons/distribuidora_ventas/wizards/factura_descuento_wizard.py
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.fields import Command


class FacturaDescuentoWizard(models.TransientModel):
    _name = 'distribuidora.factura.descuento.wizard'
    _description = "Descuento general para facturas de cliente"

    move_id = fields.Many2one(
        'account.move', required=True,
        default=lambda self: self.env.context.get('active_id'),
    )
    porcentaje = fields.Float(string="Porcentaje de descuento", required=True)

    @api.constrains('porcentaje')
    def _check_porcentaje(self):
        for wizard in self:
            if not 0 < wizard.porcentaje <= 100:
                raise ValidationError(_(
                    "El porcentaje de descuento debe ser mayor a 0 y menor o igual a 100."
                ))

    def _get_discount_product(self):
        self.ensure_one()
        company = self.move_id.company_id
        discount_product = company.sale_discount_product_id
        if not discount_product:
            discount_product = self.env['product.product'].create({
                'name': _("Descuento"),
                'type': 'service',
                'invoice_policy': 'order',
                'list_price': 0.0,
                'company_id': company.id,
            })
            company.sale_discount_product_id = discount_product
        return discount_product

    def action_aplicar(self):
        self.ensure_one()
        move = self.move_id
        AccountTax = self.env['account.tax']

        product_lines = move.invoice_line_ids.filtered(lambda line: line.display_type == 'product')
        base_lines = [
            AccountTax._prepare_base_line_for_taxes_computation(line) for line in product_lines
        ]
        AccountTax._add_tax_details_in_base_lines(base_lines, move.company_id)
        AccountTax._round_base_lines_tax_details(base_lines, move.company_id)

        def grouping_function(base_line):
            return {'product_id': None}

        discount_base_lines = AccountTax._prepare_global_discount_lines(
            base_lines=base_lines,
            company=move.company_id,
            amount_type='percent',
            amount=self.porcentaje,
            computation_key=f'distribuidora_descuento_general,{self.id}',
            grouping_function=grouping_function,
        )

        discount_product = self._get_discount_product()

        move.invoice_line_ids = [
            Command.create({
                'name': _("Descuento %(percent)s%%", percent=self.porcentaje),
                'product_id': discount_product.id,
                'price_unit': base_line['price_unit'],
                'quantity': base_line['quantity'],
                'tax_ids': [Command.set(base_line['tax_ids'].ids)],
                'extra_tax_data': AccountTax._export_base_line_extra_tax_data(base_line),
                'sequence': 999,
            })
            for base_line in discount_base_lines
        ]
```

- [ ] **Step 5: Registrar el depends en el manifest (todavía sin data XML — eso es Task 2)**

```python
# addons/distribuidora_ventas/__manifest__.py
    'depends': ['sale', 'account'],
```

- [ ] **Step 6: Actualizar el módulo y correr los tests para confirmar que pasan**

Run: `MSYS_NO_PATHCONV=1 docker exec erp-odoo-1 odoo -d odoo --db_host=db --db_user=odoo --db_password=odoo --http-port=8099 --gevent-port=8101 -u distribuidora_ventas --test-enable --test-tags /distribuidora_ventas --stop-after-init`

Expected: PASS — `0 failed, 0 error(s) of 10 tests` (7 anteriores + 3 nuevos).

- [ ] **Step 7: Commit**

```bash
git add addons/distribuidora_ventas/wizards/ addons/distribuidora_ventas/__init__.py \
        addons/distribuidora_ventas/__manifest__.py \
        addons/distribuidora_ventas/tests/__init__.py addons/distribuidora_ventas/tests/test_factura_descuento_wizard.py
git commit -m "feat(distribuidora_ventas): wizard de descuento general para facturas de cliente"
```

---

## Task 2: Botón en la factura y columna de descuento visible por defecto

**Files:**
- Create: `addons/distribuidora_ventas/wizards/factura_descuento_wizard_views.xml`
- Create: `addons/distribuidora_ventas/views/account_move_views.xml`
- Create: `addons/distribuidora_ventas/tests/test_factura_descuento_wizard_view.py`
- Modify: `addons/distribuidora_ventas/__manifest__.py`
- Modify: `addons/distribuidora_ventas/tests/__init__.py`

**Interfaces:**
- Consumes: `distribuidora.factura.descuento.wizard` y su método `action_aplicar()` (Task 1).
- Produces: acción `distribuidora_ventas.action_factura_descuento_wizard`, botón "Descuento general" en el formulario de factura.

- [ ] **Step 1: Escribir los tests que fallan (la vista/acción todavía no existe)**

```python
# addons/distribuidora_ventas/tests/test_factura_descuento_wizard_view.py
import re

from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestFacturaDescuentoWizardView(TransactionCase):

    def test_discount_button_present_and_points_to_wizard_action(self):
        action = self.env.ref('distribuidora_ventas.action_factura_descuento_wizard')
        view = self.env['account.move'].get_view(view_type='form')
        match = re.search(r'<button[^>]*string="Descuento general"[^>]*/>', view['arch'])
        self.assertIsNotNone(match, "no se encontro el boton 'Descuento general' en la vista combinada")
        self.assertIn(f'name="{action.id}"', match.group(0))

    def test_discount_field_shown_by_default_on_invoice_lines(self):
        view = self.env['account.move'].get_view(view_type='form')
        match = re.search(r'<field[^>]*name="discount"[^>]*width="50px"[^>]*/>', view['arch'])
        self.assertIsNotNone(match, "no se encontro el campo discount (ancho 50px) en la vista combinada")
        self.assertIn('optional="show"', match.group(0))
```

```python
# addons/distribuidora_ventas/tests/__init__.py
from . import test_partner_categories
from . import test_customer_pricelist
from . import test_invoice_from_order_quantity
from . import test_sale_order_accepts_any_delivery_date
from . import test_sale_order_form_hides_commitment_date
from . import test_pricelist_menu
from . import test_factura_descuento_wizard
from . import test_factura_descuento_wizard_view
```

- [ ] **Step 2: Correr los tests para confirmar que fallan**

Run: `MSYS_NO_PATHCONV=1 docker exec erp-odoo-1 odoo -d odoo --db_host=db --db_user=odoo --db_password=odoo --http-port=8099 --gevent-port=8101 -u distribuidora_ventas --test-enable --test-tags /distribuidora_ventas --stop-after-init`

Expected: FAIL — `ValueError: External ID not found: distribuidora_ventas.action_factura_descuento_wizard`.

- [ ] **Step 3: Crear la vista del wizard, la acción y el botón en la factura**

```xml
<!-- addons/distribuidora_ventas/wizards/factura_descuento_wizard_views.xml -->
<odoo>
    <record id="view_factura_descuento_wizard_form" model="ir.ui.view">
        <field name="name">distribuidora.factura.descuento.wizard.form</field>
        <field name="model">distribuidora.factura.descuento.wizard</field>
        <field name="arch" type="xml">
            <form string="Descuento general">
                <group>
                    <field name="porcentaje"/>
                </group>
                <footer>
                    <button name="action_aplicar" string="Aplicar" type="object" class="btn-primary"/>
                    <button string="Cancelar" class="btn-secondary" special="cancel"/>
                </footer>
            </form>
        </field>
    </record>

    <record id="action_factura_descuento_wizard" model="ir.actions.act_window">
        <field name="name">Descuento general</field>
        <field name="res_model">distribuidora.factura.descuento.wizard</field>
        <field name="view_mode">form</field>
        <field name="target">new</field>
    </record>

    <record id="view_move_form_descuento_general" model="ir.ui.view">
        <field name="name">account.move.form.descuento.general</field>
        <field name="model">account.move</field>
        <field name="inherit_id" ref="account.view_move_form"/>
        <field name="arch" type="xml">
            <xpath expr="//group[hasclass('oe_invoice_lines_tab')]" position="before">
                <div class="float-end d-flex d-print-none gap-1 mb-2"
                     invisible="move_type not in ('out_invoice', 'out_refund') or state != 'draft'">
                    <button string="Descuento general"
                            name="%(distribuidora_ventas.action_factura_descuento_wizard)d"
                            type="action"
                            class="btn-secondary"/>
                </div>
            </xpath>
        </field>
    </record>
</odoo>
```

```xml
<!-- addons/distribuidora_ventas/views/account_move_views.xml -->
<odoo>
    <record id="view_move_form_discount_column_visible" model="ir.ui.view">
        <field name="name">account.move.form.discount.column.visible</field>
        <field name="model">account.move</field>
        <field name="inherit_id" ref="account.view_move_form"/>
        <field name="arch" type="xml">
            <xpath expr="//field[@name='invoice_line_ids']//list[@name='journal_items']/field[@name='discount']" position="attributes">
                <attribute name="optional">show</attribute>
            </xpath>
        </field>
    </record>
</odoo>
```

- [ ] **Step 4: Registrar los dos XML nuevos en el manifest**

```python
# addons/distribuidora_ventas/__manifest__.py
    'data': [
        'data/res_partner_category_data.xml',
        'views/sale_order_views.xml',
        'views/pricelist_menu.xml',
        'views/account_move_views.xml',
        'wizards/factura_descuento_wizard_views.xml',
    ],
```

- [ ] **Step 5: Actualizar el módulo y correr los tests para confirmar que pasan**

Run: `MSYS_NO_PATHCONV=1 docker exec erp-odoo-1 odoo -d odoo --db_host=db --db_user=odoo --db_password=odoo --http-port=8099 --gevent-port=8101 -u distribuidora_ventas --test-enable --test-tags /distribuidora_ventas --stop-after-init`

Expected: PASS — `0 failed, 0 error(s) of 12 tests` (10 de Task 1 + 2 nuevos).

- [ ] **Step 6: Commit**

```bash
git add addons/distribuidora_ventas/wizards/factura_descuento_wizard_views.xml \
        addons/distribuidora_ventas/views/account_move_views.xml \
        addons/distribuidora_ventas/__manifest__.py \
        addons/distribuidora_ventas/tests/__init__.py addons/distribuidora_ventas/tests/test_factura_descuento_wizard_view.py
git commit -m "feat(distribuidora_ventas): boton de descuento general y columna Disc.% visible en factura"
```

---

## Task 3: Verificación manual end-to-end

**Files:** ninguno (verificación manual, sin cambios de código).

- [ ] **Step 1: Actualizar el módulo y reiniciar el servidor web**

Run: `MSYS_NO_PATHCONV=1 docker exec erp-odoo-1 odoo -d odoo --db_host=db --db_user=odoo --db_password=odoo --http-port=8099 --gevent-port=8101 -u distribuidora_ventas --stop-after-init`

Luego: `docker restart erp-odoo-1` (el servidor de `localhost:8069` no recarga código/vistas en caliente).

- [ ] **Step 2: Crear y confirmar un pedido, facturarlo**

En `http://localhost:8069`: crear un pedido con 2-3 líneas de producto, confirmarlo, y generar la factura ("Crear factura").

- [ ] **Step 3: Aplicar el descuento general**

En la factura (todavía en borrador), confirmar que aparece el botón "Descuento general" cerca de las líneas/totales. Hacer clic, poner un porcentaje (ej. 10), "Aplicar" → confirmar que se agrega una línea de descuento y que el total baja el porcentaje correcto (impuestos incluidos).

- [ ] **Step 4: Confirmar que el botón desaparece al validar**

Validar la factura (Confirmar/Publicar) → confirmar que el botón "Descuento general" ya no aparece.

- [ ] **Step 5: Confirmar que Preventas no cambió**

Abrir un pedido de venta → confirmar que el botón "Descuento"/"Descuentos" original de Odoo sigue ahí sin cambios (no se tocó nada de Preventas).

- [ ] **Step 6: Confirmar la columna de descuento por línea**

En una factura nueva en borrador, confirmar que la columna "Disc.%" ya aparece visible en las líneas sin tener que activarla manualmente desde el selector de columnas.
