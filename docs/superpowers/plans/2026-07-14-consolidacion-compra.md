# Consolidación de compra para CENADA — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Un asistente que, dada una fecha de entrega (lunes/miércoles/viernes), genera un PDF con el total por producto entre todos los pedidos confirmados de esa fecha.

**Architecture:** Addon nuevo `distribuidora_compras` (depende de `sale` y `purchase` — este último solo para ubicar el menú bajo la app de Compras, no se toca ningún modelo de compras). Un wizard `TransientModel` concentra la lógica de agregación (Task 1); una vista de formulario + acción de reporte QWeb-PDF exponen esa lógica al usuario (Task 2).

**Tech Stack:** Odoo 19 (Python 3.10-3.14), `odoo.tests.common.TransactionCase`, QWeb.

## Global Constraints

- Python 3.10–3.14 (según `CLAUDE.md` del repo).
- Imports ordenados: future → stdlib → third-party → odoo → odoo.addons (lo aplica `ruff`).
- Addon nuevo en `addons/distribuidora_compras/`, con `wizards/`, `report/`, `security/`, `tests/`.
- Tests con `@tagged('post_install', '-at_install')`, `TransactionCase`, igual que `distribuidora_ventas`.
- La comparación de fecha debe hacerse en hora de Costa Rica, usando `fields.Datetime.context_timestamp(record, record.commitment_date)` — mismo patrón ya usado y corregido en `addons/distribuidora_ventas/models/sale_order.py` para evitar el bug de zona horaria UTC-vs-local.
- No se generan órdenes de compra (`purchase.order`), no se separa la lista por origen (CENADA vs. proveedor) — confirmado fuera de alcance en el spec (`docs/superpowers/specs/2026-07-14-consolidacion-compra-design.md`).
- No se toca el addon `distribuidora_ventas` — este es aditivo, un addon nuevo.

---

## Task 1: Wizard y lógica de agregación

**Files:**
- Create: `addons/distribuidora_compras/__init__.py`
- Create: `addons/distribuidora_compras/__manifest__.py`
- Create: `addons/distribuidora_compras/wizards/__init__.py`
- Create: `addons/distribuidora_compras/wizards/compra_consolidada_wizard.py`
- Create: `addons/distribuidora_compras/security/ir.model.access.csv`
- Create: `addons/distribuidora_compras/tests/__init__.py`
- Create: `addons/distribuidora_compras/tests/test_compra_consolidada_wizard.py`

**Interfaces:**
- Produces: modelo `distribuidora.compra.consolidada.wizard` con campo `fecha_entrega` (Date) y método `_get_consolidated_lines(self)` → `list[dict]`, cada dict con claves `'product'` (recordset `product.product`), `'qty'` (float) y `'uom'` (str, nombre de la unidad de medida). Usado por Task 2 para renderizar el PDF.

- [ ] **Step 1: Escribir los tests que fallan (el módulo todavía no existe)**

```python
# addons/distribuidora_compras/tests/test_compra_consolidada_wizard.py
from datetime import date, datetime

from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestCompraConsolidadaWizard(TransactionCase):

    def setUp(self):
        super().setUp()
        self.product = self.env['product.product'].create({'name': 'Papa', 'list_price': 500.0})
        self.partner = self.env['res.partner'].create({'name': 'Cliente Test'})

    def _create_confirmed_order(self, product, qty, commitment_date):
        # with_context(tz=...) asegura que la restriccion de fecha de entrega
        # de distribuidora_ventas (instalado en la misma base) evalue el dia
        # en hora de Costa Rica al confirmar, igual que hace el wizard al leer.
        order = self.env['sale.order'].with_context(tz='America/Costa_Rica').create({
            'partner_id': self.partner.id,
            'commitment_date': commitment_date,
        })
        self.env['sale.order.line'].create({
            'order_id': order.id,
            'product_id': product.id,
            'product_uom_qty': qty,
        })
        order.action_confirm()
        return order

    def test_sums_quantities_across_confirmed_orders_same_date(self):
        # 2026-07-20 es lunes.
        delivery_date = datetime(2026, 7, 20, 15, 0, 0)
        self._create_confirmed_order(self.product, 2, delivery_date)
        self._create_confirmed_order(self.product, 3, delivery_date)
        self._create_confirmed_order(self.product, 5, delivery_date)

        wizard = self.env['distribuidora.compra.consolidada.wizard'].create({
            'fecha_entrega': delivery_date.date(),
        })
        lines = wizard._get_consolidated_lines()

        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]['product'], self.product)
        self.assertEqual(lines[0]['qty'], 10)
        self.assertEqual(lines[0]['uom'], self.product.uom_id.name)

    def test_excludes_orders_with_different_delivery_date(self):
        # 2026-07-20 lunes, 2026-07-22 miercoles.
        self._create_confirmed_order(self.product, 2, datetime(2026, 7, 20, 15, 0, 0))
        self._create_confirmed_order(self.product, 100, datetime(2026, 7, 22, 15, 0, 0))

        wizard = self.env['distribuidora.compra.consolidada.wizard'].create({
            'fecha_entrega': date(2026, 7, 20),
        })
        lines = wizard._get_consolidated_lines()

        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]['qty'], 2)

    def test_excludes_unconfirmed_orders(self):
        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'commitment_date': datetime(2026, 7, 20, 15, 0, 0),
        })
        self.env['sale.order.line'].create({
            'order_id': order.id,
            'product_id': self.product.id,
            'product_uom_qty': 7,
        })
        # No se confirma: queda en borrador.

        wizard = self.env['distribuidora.compra.consolidada.wizard'].create({
            'fecha_entrega': date(2026, 7, 20),
        })

        self.assertEqual(wizard._get_consolidated_lines(), [])

    def test_no_orders_for_date_returns_empty_list(self):
        wizard = self.env['distribuidora.compra.consolidada.wizard'].create({
            'fecha_entrega': date(2099, 1, 1),
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
            'fecha_entrega': date(2026, 7, 20),
        })
        lines = wizard._get_consolidated_lines()

        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]['qty'], 4)
```

```python
# addons/distribuidora_compras/tests/__init__.py
from . import test_compra_consolidada_wizard
```

- [ ] **Step 2: Crear el manifest, `__init__.py` raíz y de `wizards/` (sin el modelo todavía)**

```python
# addons/distribuidora_compras/__manifest__.py
{
    'name': "Distribuidora - Compras",
    'version': '19.0.1.0.0',
    'category': 'Inventory/Purchase',
    'summary': "Consolidacion de compra para CENADA y proveedores cercanos",
    'author': "Distribuidora",
    'depends': ['sale', 'purchase'],
    'data': [
        'security/ir.model.access.csv',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
}
```

```python
# addons/distribuidora_compras/__init__.py
from . import wizards
```

```python
# addons/distribuidora_compras/wizards/__init__.py
```

- [ ] **Step 3: Instalar el módulo y correr los tests para confirmar que fallan**

Run: `MSYS_NO_PATHCONV=1 docker exec erp-odoo-1 odoo -d odoo --db_host=db --db_user=odoo --db_password=odoo --http-port=8099 --gevent-port=8101 -i distribuidora_compras --test-enable --test-tags /distribuidora_compras --stop-after-init`

Expected: FAIL — `KeyError: 'distribuidora.compra.consolidada.wizard'` (el modelo todavía no existe).

- [ ] **Step 4: Implementar el wizard**

```python
# addons/distribuidora_compras/wizards/compra_consolidada_wizard.py
from collections import defaultdict
from datetime import timedelta

from odoo import api, fields, models

DELIVERY_WEEKDAYS = {0, 2, 4}  # lunes, miercoles, viernes (Python: lunes=0)


class CompraConsolidadaWizard(models.TransientModel):
    _name = 'distribuidora.compra.consolidada.wizard'
    _description = "Consolidacion de compra por fecha de entrega"

    fecha_entrega = fields.Date(
        string="Fecha de entrega",
        required=True,
        default=lambda self: self._default_fecha_entrega(),
    )

    @api.model
    def _default_fecha_entrega(self):
        today = fields.Date.context_today(self)
        offset = 0
        while (today + timedelta(days=offset)).weekday() not in DELIVERY_WEEKDAYS:
            offset += 1
        return today + timedelta(days=offset)

    def _get_consolidated_lines(self):
        self.ensure_one()
        orders = self.env['sale.order'].search([
            ('state', '=', 'sale'),
            ('commitment_date', '!=', False),
        ])
        matching_orders = orders.filtered(
            lambda o: fields.Datetime.context_timestamp(o, o.commitment_date).date() == self.fecha_entrega
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
```

```python
# addons/distribuidora_compras/wizards/__init__.py
from . import compra_consolidada_wizard
```

```csv
# addons/distribuidora_compras/security/ir.model.access.csv
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_distribuidora_compra_consolidada_wizard,distribuidora.compra.consolidada.wizard,model_distribuidora_compra_consolidada_wizard,base.group_user,1,1,1,1
```

- [ ] **Step 5: Correr los tests para confirmar que pasan**

Run: `MSYS_NO_PATHCONV=1 docker exec erp-odoo-1 odoo -d odoo --db_host=db --db_user=odoo --db_password=odoo --http-port=8099 --gevent-port=8101 -u distribuidora_compras --test-enable --test-tags /distribuidora_compras --stop-after-init`

Expected: PASS — `0 failed, 0 error(s) of 5 tests`.

- [ ] **Step 6: Commit**

```bash
git add addons/distribuidora_compras/__init__.py addons/distribuidora_compras/__manifest__.py \
        addons/distribuidora_compras/wizards/__init__.py addons/distribuidora_compras/wizards/compra_consolidada_wizard.py \
        addons/distribuidora_compras/security/ir.model.access.csv \
        addons/distribuidora_compras/tests/__init__.py addons/distribuidora_compras/tests/test_compra_consolidada_wizard.py
git commit -m "feat(distribuidora_compras): wizard de consolidacion de compra por fecha de entrega"
```

---

## Task 2: Vista, menú y reporte PDF

**Files:**
- Create: `addons/distribuidora_compras/wizards/compra_consolidada_wizard_views.xml`
- Create: `addons/distribuidora_compras/report/compra_consolidada_report.xml`
- Create: `addons/distribuidora_compras/tests/test_compra_consolidada_report.py`
- Modify: `addons/distribuidora_compras/__manifest__.py` (agregar los dos XML a `data`)
- Modify: `addons/distribuidora_compras/tests/__init__.py` (agregar el import)

**Interfaces:**
- Consumes: `distribuidora.compra.consolidada.wizard._get_consolidated_lines()` (Task 1) desde el template QWeb.
- Produces: acción de reporte `distribuidora_compras.action_report_compra_consolidada`, usada por el botón `action_generar_lista` del wizard.

- [ ] **Step 1: Escribir los tests que fallan (la acción de reporte todavía no existe)**

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
        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'commitment_date': datetime(2026, 7, 20, 15, 0, 0),  # lunes
        })
        self.env['sale.order.line'].create({
            'order_id': order.id,
            'product_id': self.product.id,
            'product_uom_qty': 6,
        })
        order.action_confirm()

    def test_report_renders_consolidated_quantity(self):
        wizard = self.env['distribuidora.compra.consolidada.wizard'].create({
            'fecha_entrega': date(2026, 7, 20),
        })
        html, _report_type = self.env['ir.actions.report']._render_qweb_html(
            'distribuidora_compras.action_report_compra_consolidada', wizard.ids
        )
        content = html.decode()
        self.assertIn('Papa', content)
        self.assertIn('6.0', content)

    def test_report_renders_empty_notice_when_no_orders(self):
        wizard = self.env['distribuidora.compra.consolidada.wizard'].create({
            'fecha_entrega': date(2099, 1, 1),
        })
        html, _report_type = self.env['ir.actions.report']._render_qweb_html(
            'distribuidora_compras.action_report_compra_consolidada', wizard.ids
        )
        content = html.decode()
        self.assertIn('No hay pedidos confirmados', content)
```

```python
# addons/distribuidora_compras/tests/__init__.py
from . import test_compra_consolidada_wizard
from . import test_compra_consolidada_report
```

- [ ] **Step 2: Correr los tests para confirmar que fallan**

Run: `MSYS_NO_PATHCONV=1 docker exec erp-odoo-1 odoo -d odoo --db_host=db --db_user=odoo --db_password=odoo --http-port=8099 --gevent-port=8101 -u distribuidora_compras --test-enable --test-tags /distribuidora_compras --stop-after-init`

Expected: FAIL — `ValueError: External ID not found: distribuidora_compras.action_report_compra_consolidada`.

- [ ] **Step 3: Crear la vista del wizard, la acción de ventana y el menú**

```xml
<!-- addons/distribuidora_compras/wizards/compra_consolidada_wizard_views.xml -->
<odoo>
    <record id="view_compra_consolidada_wizard_form" model="ir.ui.view">
        <field name="name">distribuidora.compra.consolidada.wizard.form</field>
        <field name="model">distribuidora.compra.consolidada.wizard</field>
        <field name="arch" type="xml">
            <form string="Consolidación de compra">
                <group>
                    <field name="fecha_entrega"/>
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

- [ ] **Step 4: Crear la acción de reporte y el template QWeb**

```xml
<!-- addons/distribuidora_compras/report/compra_consolidada_report.xml -->
<odoo>
    <record id="action_report_compra_consolidada" model="ir.actions.report">
        <field name="name">Lista de compra consolidada</field>
        <field name="model">distribuidora.compra.consolidada.wizard</field>
        <field name="report_type">qweb-pdf</field>
        <field name="report_name">distribuidora_compras.report_compra_consolidada_document</field>
        <field name="print_report_name">'Lista de compra %s' % (object.fecha_entrega)</field>
    </record>

    <template id="report_compra_consolidada_document">
        <t t-call="web.html_container">
            <t t-foreach="docs" t-as="doc">
                <t t-call="web.external_layout">
                    <div class="page">
                        <h2>Lista de compra consolidada</h2>
                        <p>Fecha de entrega: <span t-esc="doc.fecha_entrega"/></p>
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
                                    <td colspan="3">No hay pedidos confirmados para esta fecha de entrega.</td>
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

- [ ] **Step 5: Agregar el método que dispara el reporte desde el wizard**

```python
# addons/distribuidora_compras/wizards/compra_consolidada_wizard.py
# Agregar este metodo a la clase CompraConsolidadaWizard, despues de _get_consolidated_lines:

    def action_generar_lista(self):
        self.ensure_one()
        return self.env.ref('distribuidora_compras.action_report_compra_consolidada').report_action(self)
```

- [ ] **Step 6: Registrar los dos XML nuevos en el manifest**

```python
# addons/distribuidora_compras/__manifest__.py
    'data': [
        'security/ir.model.access.csv',
        'wizards/compra_consolidada_wizard_views.xml',
        'report/compra_consolidada_report.xml',
    ],
```

- [ ] **Step 7: Actualizar el módulo y correr los tests para confirmar que pasan**

Run: `MSYS_NO_PATHCONV=1 docker exec erp-odoo-1 odoo -d odoo --db_host=db --db_user=odoo --db_password=odoo --http-port=8099 --gevent-port=8101 -u distribuidora_compras --test-enable --test-tags /distribuidora_compras --stop-after-init`

Expected: PASS — `0 failed, 0 error(s) of 7 tests` (5 de Task 1 + 2 nuevos).

- [ ] **Step 8: Commit**

```bash
git add addons/distribuidora_compras/wizards/compra_consolidada_wizard_views.xml \
        addons/distribuidora_compras/wizards/compra_consolidada_wizard.py \
        addons/distribuidora_compras/report/compra_consolidada_report.xml \
        addons/distribuidora_compras/__manifest__.py \
        addons/distribuidora_compras/tests/__init__.py addons/distribuidora_compras/tests/test_compra_consolidada_report.py
git commit -m "feat(distribuidora_compras): vista, menu y reporte PDF de la lista consolidada"
```

---

## Task 3: Verificación manual end-to-end

**Files:** ninguno (verificación manual, sin cambios de código).

**Interfaces:**
- Consumes: addon `distribuidora_compras` completo (Tasks 1-2), instalado en la base local.

- [ ] **Step 1: Confirmar que el módulo está instalado**

Run: `MSYS_NO_PATHCONV=1 docker exec erp-odoo-1 odoo -d odoo --db_host=db --db_user=odoo --db_password=odoo --http-port=8099 --gevent-port=8101 -u distribuidora_compras --stop-after-init`

- [ ] **Step 2: Crear 2-3 pedidos de prueba confirmados con la misma fecha de entrega**

En la UI (`http://localhost:8069`): Ventas → crear 2-3 órdenes con distintos clientes, todas con la misma `Fecha de entrega` (un lunes, miércoles o viernes próximo) y al menos una línea del mismo producto en cada una, con cantidades distintas. Confirmar cada una.

- [ ] **Step 3: Generar la lista consolidada**

Ir a Compras → "Consolidación de compra", confirmar que la fecha por defecto es una fecha de entrega válida, dejarla o ajustarla a la fecha usada en el Step 2, click en "Generar lista".

- [ ] **Step 4: Verificar el PDF**

Confirmar que el PDF muestra el producto con la cantidad total sumada de los 2-3 pedidos (no cada pedido por separado), y que un producto que solo apareció en uno de los pedidos también sale con su cantidad correcta.

- [ ] **Step 5: Verificar el caso vacío**

Repetir el asistente eligiendo una fecha sin pedidos confirmados (ej. muy en el futuro) → confirmar que el PDF sale con el aviso de que no hay nada que comprar, no un error.
