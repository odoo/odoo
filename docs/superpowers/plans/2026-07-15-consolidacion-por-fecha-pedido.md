# Consolidación de compra según fecha del pedido — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** El asistente de consolidación de compra agrupa por `date_order` (fecha de confirmación del pedido) en vez de `commitment_date` (fecha de entrega), y el campo "Fecha de entrega" se oculta del formulario del pedido.

**Architecture:** Dos cambios independientes en dos addons distintos: `distribuidora_compras` (renombra el campo del wizard y cambia la base de la búsqueda) y `distribuidora_ventas` (agrega una vista que hereda el formulario nativo de `sale.order` para ocultar el grupo de "Shipping"/fecha de entrega).

**Tech Stack:** Odoo 19 (Python 3.10-3.14), `odoo.tests.common.TransactionCase`, QWeb, vistas XML.

## Global Constraints

- Python 3.10–3.14 (según `CLAUDE.md` del repo).
- Imports ordenados: future → stdlib → third-party → odoo → odoo.addons (lo aplica `ruff`).
- Tests con `@tagged('post_install', '-at_install')`, `TransactionCase`, igual que el resto de ambos addons.
- `date_order` es un campo nativo `required=True` en `sale.order` — a diferencia de `commitment_date`, nunca es `False`, así que la búsqueda no necesita filtrar por "distinto de falso".
- **Dato de la API de Odoo verificado en esta versión:** al confirmar un pedido (`action_confirm`), Odoo sobreescribe `date_order` con la fecha/hora de confirmación (`addons/sale/models/sale_order.py:1218-1229`, `_prepare_confirmation_values`). En los tests, para simular un pedido "confirmado en tal fecha", hay que confirmar primero y después sobreescribir `date_order` a mano con `order.date_order = ...` — asignarlo en el `create()` no sobrevive a la confirmación.
- La comparación de fecha sigue usando `fields.Datetime.context_timestamp(record, record.date_order)` en hora de Costa Rica, mismo patrón ya usado con `commitment_date`.
- No se agrega ningún campo nuevo para "conservar" `commitment_date` — el campo nativo sigue existiendo en la base de datos, solo se oculta de la vista (spec §3.1, §5).

---

## Task 1: `distribuidora_compras` — agrupar por fecha del pedido

**Files:**
- Modify: `addons/distribuidora_compras/wizards/compra_consolidada_wizard.py`
- Modify: `addons/distribuidora_compras/wizards/compra_consolidada_wizard_views.xml`
- Modify: `addons/distribuidora_compras/report/compra_consolidada_report.xml`
- Modify: `addons/distribuidora_compras/tests/test_compra_consolidada_wizard.py`
- Modify: `addons/distribuidora_compras/tests/test_compra_consolidada_report.py`

**Interfaces:**
- Produces: el campo `fecha_pedido` (Date) reemplaza a `fecha_entrega` en `distribuidora.compra.consolidada.wizard`. `_get_consolidated_lines()` mantiene la misma forma de retorno (`list[dict]` con `product`/`qty`/`uom`), solo cambia qué campo del pedido usa para filtrar.

- [ ] **Step 1: Reescribir los tests para usar `fecha_pedido`/`date_order` (van a fallar: el campo viejo todavía existe, el nuevo no)**

```python
# addons/distribuidora_compras/tests/test_compra_consolidada_wizard.py
from datetime import date, datetime

from odoo import fields
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestCompraConsolidadaWizard(TransactionCase):

    def setUp(self):
        super().setUp()
        self.product = self.env['product.product'].create({'name': 'Papa', 'list_price': 500.0})
        self.partner = self.env['res.partner'].create({'name': 'Cliente Test'})

    def _create_confirmed_order(self, product, qty, order_date):
        order = self.env['sale.order'].create({'partner_id': self.partner.id})
        self.env['sale.order.line'].create({
            'order_id': order.id,
            'product_id': product.id,
            'product_uom_qty': qty,
        })
        order.action_confirm()
        # action_confirm sobreescribe date_order con la hora de confirmacion;
        # lo fijamos despues para simular un pedido confirmado en una fecha concreta.
        order.date_order = order_date
        return order

    def test_sums_quantities_across_confirmed_orders_same_date(self):
        order_date = datetime(2026, 7, 20, 15, 0, 0)
        self._create_confirmed_order(self.product, 2, order_date)
        self._create_confirmed_order(self.product, 3, order_date)
        self._create_confirmed_order(self.product, 5, order_date)

        wizard = self.env['distribuidora.compra.consolidada.wizard'].create({
            'fecha_pedido': order_date.date(),
        })
        lines = wizard._get_consolidated_lines()

        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]['product'], self.product)
        self.assertEqual(lines[0]['qty'], 10)
        self.assertEqual(lines[0]['uom'], self.product.uom_id.name)

    def test_excludes_orders_with_different_order_date(self):
        self._create_confirmed_order(self.product, 2, datetime(2026, 7, 20, 15, 0, 0))
        self._create_confirmed_order(self.product, 100, datetime(2026, 7, 22, 15, 0, 0))

        wizard = self.env['distribuidora.compra.consolidada.wizard'].create({
            'fecha_pedido': date(2026, 7, 20),
        })
        lines = wizard._get_consolidated_lines()

        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]['qty'], 2)

    def test_excludes_unconfirmed_orders(self):
        order = self.env['sale.order'].create({'partner_id': self.partner.id})
        self.env['sale.order.line'].create({
            'order_id': order.id,
            'product_id': self.product.id,
            'product_uom_qty': 7,
        })
        # No se confirma: queda en borrador, con date_order de creacion.

        wizard = self.env['distribuidora.compra.consolidada.wizard'].create({
            'fecha_pedido': fields.Datetime.context_timestamp(order, order.date_order).date(),
        })

        self.assertEqual(wizard._get_consolidated_lines(), [])

    def test_no_orders_for_date_returns_empty_list(self):
        wizard = self.env['distribuidora.compra.consolidada.wizard'].create({
            'fecha_pedido': date(2099, 1, 1),
        })
        self.assertEqual(wizard._get_consolidated_lines(), [])

    def test_uses_costa_rica_local_date_not_utc(self):
        # 2026-07-21 02:00 UTC == 2026-07-20 20:00 America/Costa_Rica (lunes de noche).
        # Si la comparacion usara el dia UTC crudo, este pedido quedaria en "martes"
        # y no se incluiria al pedir la lista del lunes 2026-07-20.
        self._create_confirmed_order(self.product, 4, datetime(2026, 7, 21, 2, 0, 0))

        wizard = self.env['distribuidora.compra.consolidada.wizard'].with_context(
            tz='America/Costa_Rica'
        ).create({
            'fecha_pedido': date(2026, 7, 20),
        })
        lines = wizard._get_consolidated_lines()

        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]['qty'], 4)
```

```python
# addons/distribuidora_compras/tests/test_compra_consolidada_report.py
from datetime import date, datetime

from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestCompraConsolidadaReport(TransactionCase):

    def setUp(self):
        super().setUp()
        self.product = self.env['product.product'].create({'name': 'Papa', 'list_price': 500.0})
        self.partner = self.env['res.partner'].create({'name': 'Cliente Test'})
        order = self.env['sale.order'].create({'partner_id': self.partner.id})
        self.env['sale.order.line'].create({
            'order_id': order.id,
            'product_id': self.product.id,
            'product_uom_qty': 6,
        })
        order.action_confirm()
        order.date_order = datetime(2026, 7, 20, 15, 0, 0)

    def test_report_renders_consolidated_quantity(self):
        wizard = self.env['distribuidora.compra.consolidada.wizard'].create({
            'fecha_pedido': date(2026, 7, 20),
        })
        html, _report_type = self.env['ir.actions.report']._render_qweb_html(
            'distribuidora_compras.action_report_compra_consolidada', wizard.ids
        )
        content = html.decode()
        self.assertIn('Papa', content)
        self.assertIn('6.0', content)

    def test_report_renders_empty_notice_when_no_orders(self):
        wizard = self.env['distribuidora.compra.consolidada.wizard'].create({
            'fecha_pedido': date(2099, 1, 1),
        })
        html, _report_type = self.env['ir.actions.report']._render_qweb_html(
            'distribuidora_compras.action_report_compra_consolidada', wizard.ids
        )
        content = html.decode()
        self.assertIn('No hay pedidos confirmados', content)
```

- [ ] **Step 2: Correr los tests para confirmar que fallan (el campo `fecha_pedido` todavía no existe)**

Run: `MSYS_NO_PATHCONV=1 docker exec erp-odoo-1 odoo -d odoo --db_host=db --db_user=odoo --db_password=odoo --http-port=8099 --gevent-port=8101 -u distribuidora_compras --test-enable --test-tags /distribuidora_compras --stop-after-init`

Expected: FAIL — error de campo inexistente (`fecha_pedido`) al crear el wizard en los tests.

- [ ] **Step 3: Reescribir el wizard**

```python
# addons/distribuidora_compras/wizards/compra_consolidada_wizard.py
from collections import defaultdict

from odoo import fields, models


class CompraConsolidadaWizard(models.TransientModel):
    _name = 'distribuidora.compra.consolidada.wizard'
    _description = "Consolidacion de compra por fecha de pedido"

    fecha_pedido = fields.Date(
        string="Fecha de pedidos",
        required=True,
        default=lambda self: fields.Date.context_today(self),
    )

    def _get_consolidated_lines(self):
        self.ensure_one()
        orders = self.env['sale.order'].search([
            ('state', '=', 'sale'),
        ])
        matching_orders = orders.filtered(
            lambda o: fields.Datetime.context_timestamp(o, o.date_order).date() == self.fecha_pedido
        )
        totals = defaultdict(float)
        uom_by_product = {}
        for line in matching_orders.order_line:
            if line.display_type or not line.product_id:
                continue
            totals[line.product_id] += line.product_uom_qty
            uom_by_product[line.product_id] = line.product_uom_id.name
        return [
            {'product': product, 'qty': qty, 'uom': uom_by_product[product]}
            for product, qty in totals.items()
        ]

    def action_generar_lista(self):
        self.ensure_one()
        return self.env.ref('distribuidora_compras.action_report_compra_consolidada').report_action(self)
```

- [ ] **Step 4: Actualizar la vista del wizard y el reporte para usar `fecha_pedido`**

```xml
<!-- addons/distribuidora_compras/wizards/compra_consolidada_wizard_views.xml -->
<odoo>
    <record id="view_compra_consolidada_wizard_form" model="ir.ui.view">
        <field name="name">distribuidora.compra.consolidada.wizard.form</field>
        <field name="model">distribuidora.compra.consolidada.wizard</field>
        <field name="arch" type="xml">
            <form string="Consolidación de compra">
                <group>
                    <field name="fecha_pedido"/>
                </group>
                <footer>
                    <button name="action_generar_lista" string="Generar lista" type="object" class="btn-primary"/>
                    <button string="Cancelar" class="btn-secondary" special="cancel"/>
                </footer>
            </form>
        </field>
    </record>

    <record id="action_compra_consolidada_wizard" model="ir.actions.act_window">
        <field name="name">Consolidación de compra</field>
        <field name="res_model">distribuidora.compra.consolidada.wizard</field>
        <field name="view_mode">form</field>
        <field name="target">new</field>
    </record>

    <menuitem id="menu_compra_consolidada"
              name="Consolidación de compra"
              parent="purchase.menu_purchase_root"
              action="action_compra_consolidada_wizard"
              sequence="100"/>
</odoo>
```

```xml
<!-- addons/distribuidora_compras/report/compra_consolidada_report.xml -->
<odoo>
    <record id="action_report_compra_consolidada" model="ir.actions.report">
        <field name="name">Lista de compra consolidada</field>
        <field name="model">distribuidora.compra.consolidada.wizard</field>
        <field name="report_type">qweb-pdf</field>
        <field name="report_name">distribuidora_compras.report_compra_consolidada_document</field>
        <field name="print_report_name">'Lista de compra %s' % (object.fecha_pedido)</field>
    </record>

    <template id="report_compra_consolidada_document">
        <t t-call="web.html_container">
            <t t-foreach="docs" t-as="doc">
                <t t-call="web.external_layout">
                    <div class="page">
                        <h2>Lista de compra consolidada</h2>
                        <p>Fecha de pedidos: <span t-esc="doc.fecha_pedido"/></p>
                        <table class="table table-sm">
                            <thead>
                                <tr>
                                    <th>Producto</th>
                                    <th>Unidad</th>
                                    <th class="text-end">Cantidad</th>
                                </tr>
                            </thead>
                            <tbody>
                                <t t-set="lineas" t-value="doc._get_consolidated_lines()"/>
                                <tr t-if="not lineas">
                                    <td colspan="3">No hay pedidos confirmados para esta fecha.</td>
                                </tr>
                                <tr t-foreach="lineas" t-as="linea">
                                    <td><span t-esc="linea['product'].display_name"/></td>
                                    <td><span t-esc="linea['uom']"/></td>
                                    <td class="text-end"><span t-esc="linea['qty']"/></td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </t>
            </t>
        </t>
    </template>
</odoo>
```

- [ ] **Step 5: Actualizar el módulo y correr los tests para confirmar que pasan**

Run: `MSYS_NO_PATHCONV=1 docker exec erp-odoo-1 odoo -d odoo --db_host=db --db_user=odoo --db_password=odoo --http-port=8099 --gevent-port=8101 -u distribuidora_compras --test-enable --test-tags /distribuidora_compras --stop-after-init`

Expected: PASS — `0 failed, 0 error(s) of 7 tests` (5 del wizard + 2 del reporte).

- [ ] **Step 6: Commit**

```bash
git add addons/distribuidora_compras/wizards/compra_consolidada_wizard.py \
        addons/distribuidora_compras/wizards/compra_consolidada_wizard_views.xml \
        addons/distribuidora_compras/report/compra_consolidada_report.xml \
        addons/distribuidora_compras/tests/test_compra_consolidada_wizard.py \
        addons/distribuidora_compras/tests/test_compra_consolidada_report.py
git commit -m "feat(distribuidora_compras): consolidar por fecha del pedido en vez de fecha de entrega"
```

---

## Task 2: `distribuidora_ventas` — ocultar el campo de fecha de entrega

**Files:**
- Create: `addons/distribuidora_ventas/views/sale_order_views.xml`
- Create: `addons/distribuidora_ventas/tests/test_sale_order_form_hides_commitment_date.py`
- Modify: `addons/distribuidora_ventas/__manifest__.py`
- Modify: `addons/distribuidora_ventas/tests/__init__.py`

**Interfaces:**
- Consumes: ninguno de Task 1 — cambio independiente en otro addon.
- Produces: la vista de formulario de `sale.order` ya no muestra el grupo "Shipping" (que solo contenía la fecha de entrega).

- [ ] **Step 1: Escribir el test que falla (el grupo todavía es visible)**

```python
# addons/distribuidora_ventas/tests/test_sale_order_form_hides_commitment_date.py
import re

from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestSaleOrderFormHidesCommitmentDate(TransactionCase):

    def test_shipping_group_is_invisible(self):
        view = self.env['sale.order'].get_view(view_type='form')
        match = re.search(r'<group[^>]*name="sale_shipping"[^>]*>', view['arch'])
        self.assertIsNotNone(match, "no se encontro el grupo 'sale_shipping' en la vista combinada")
        self.assertIn('invisible', match.group(0))
```

```python
# addons/distribuidora_ventas/tests/__init__.py
from . import test_partner_categories
from . import test_customer_pricelist
from . import test_invoice_from_order_quantity
from . import test_sale_order_accepts_any_delivery_date
from . import test_sale_order_form_hides_commitment_date
```

- [ ] **Step 2: Correr el test para confirmar que falla**

Run: `MSYS_NO_PATHCONV=1 docker exec erp-odoo-1 odoo -d odoo --db_host=db --db_user=odoo --db_password=odoo --http-port=8099 --gevent-port=8101 -u distribuidora_ventas --test-enable --test-tags /distribuidora_ventas --stop-after-init`

Expected: FAIL — `AssertionError: no se encontro el grupo 'sale_shipping'...` o, si lo encuentra, `'invisible' not found in ...` (el grupo existe pero sin marcar invisible todavia).

- [ ] **Step 3: Crear la vista que oculta el grupo**

```xml
<!-- addons/distribuidora_ventas/views/sale_order_views.xml -->
<odoo>
    <record id="view_order_form_hide_commitment_date" model="ir.ui.view">
        <field name="name">sale.order.form.hide.commitment.date</field>
        <field name="model">sale.order</field>
        <field name="inherit_id" ref="sale.view_order_form"/>
        <field name="arch" type="xml">
            <xpath expr="//group[@name='sale_shipping']" position="attributes">
                <attribute name="invisible">1</attribute>
            </xpath>
        </field>
    </record>
</odoo>
```

- [ ] **Step 4: Registrar la vista en el manifest**

```python
# addons/distribuidora_ventas/__manifest__.py
    'data': [
        'data/res_partner_category_data.xml',
        'views/sale_order_views.xml',
    ],
```

- [ ] **Step 5: Actualizar el módulo y correr el test para confirmar que pasa**

Run: `MSYS_NO_PATHCONV=1 docker exec erp-odoo-1 odoo -d odoo --db_host=db --db_user=odoo --db_password=odoo --http-port=8099 --gevent-port=8101 -u distribuidora_ventas --test-enable --test-tags /distribuidora_ventas --stop-after-init`

Expected: PASS — `0 failed, 0 error(s) of 7 tests` (6 anteriores + 1 nuevo).

- [ ] **Step 6: Commit**

```bash
git add addons/distribuidora_ventas/views/sale_order_views.xml \
        addons/distribuidora_ventas/__manifest__.py \
        addons/distribuidora_ventas/tests/__init__.py \
        addons/distribuidora_ventas/tests/test_sale_order_form_hides_commitment_date.py
git commit -m "feat(distribuidora_ventas): ocultar campo de fecha de entrega del formulario de pedido"
```

---

## Task 3: Verificación manual end-to-end

**Files:** ninguno (verificación manual, sin cambios de código).

- [ ] **Step 1: Actualizar ambos módulos y reiniciar el servidor web**

Run: `MSYS_NO_PATHCONV=1 docker exec erp-odoo-1 odoo -d odoo --db_host=db --db_user=odoo --db_password=odoo --http-port=8099 --gevent-port=8101 -u distribuidora_ventas,distribuidora_compras --test-enable --test-tags /distribuidora_ventas,/distribuidora_compras --stop-after-init`

Luego: `docker restart erp-odoo-1` (el servidor de `localhost:8069` no recarga código Python ni vistas en caliente).

- [ ] **Step 2: Confirmar que el campo de fecha de entrega ya no aparece**

En `http://localhost:8069`, abrir cualquier pedido → pestaña "Otra información" → confirmar que ya no está la sección "Shipping"/"Fecha de entrega".

- [ ] **Step 3: Crear 2-3 pedidos y confirmarlos el mismo día**

Crear pedidos con distintos clientes, con al menos una línea del mismo producto en cada uno, y confirmarlos (sin tocar ningún campo de fecha, ya que no aparece).

- [ ] **Step 4: Generar la lista consolidada**

Ir a Compras → "Consolidación de compra" → confirmar que la fecha por defecto es la de hoy → "Generar lista" → confirmar que aparece el producto con la cantidad total sumada de los pedidos confirmados ese día.
