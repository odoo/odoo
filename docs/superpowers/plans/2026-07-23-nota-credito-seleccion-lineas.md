# Selección de líneas en Nota de Crédito parcial — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** En el asistente "Revertir" de Odoo, dejar que el usuario elija con checkboxes cuáles líneas de producto de la factura original entran en la nota de crédito, en vez de copiar siempre todas y obligar a borrarlas una por una.

**Architecture:** Extiende el wizard ya inherit-ado `account.move.reversal` (`l10n_cr_fe_crlibre/wizards/account_move_reversal.py`) con un campo Many2many nuevo (`l10n_cr_fe_line_ids`) que el usuario llena antes de confirmar, y un override de `refund_moves()` (el método detrás del botón "Revertir") que, después de que Odoo crea el espejo completo como siempre, borra del borrador resultante las líneas de producto que no fueron seleccionadas.

**Tech Stack:** Odoo 19 ORM (Python), vistas XML, `odoo.tests.common.TransactionCase`.

## Global Constraints

- No se modifica ningún archivo bajo `odoo/` ni `addons/account/` (código core de Odoo) — solo `addons/l10n_cr_fe_crlibre/`, siguiendo el patrón `_inherit` ya usado en todo el módulo.
- El dominio de líneas seleccionables es `display_type = 'product'` (confirmado contra `account/models/account_move_line.py:313` en este Odoo 19 — no es `False` como en versiones viejas de Odoo).
- El checklist y su filtrado solo aplican cuando `l10n_cr_fe_motivo` es distinto de `'anulacion_total'`. Para `'anulacion_total'` el comportamiento actual (espejo completo automático) no cambia.
- El filtrado se engancha únicamente a `refund_moves()` (botón "Revertir"). `modify_moves()` (botón "Revertir y crear factura") no se toca — investigar de nuevo antes de extenderlo ahí, porque en ese camino `self.new_move_ids` termina apuntando a la factura de reemplazo, no a la nota de crédito (ver `addons/account/wizard/account_move_reversal.py:110-153`).
- Ninguna línea seleccionada llega con cantidad distinta a la original de la factura — el usuario la edita manualmente después, igual que hoy (comportamiento ya aprendido, sin cambios).

---

### Task 1: Campo de selección + vista + validación de "nada seleccionado"

**Files:**
- Modify: `addons/l10n_cr_fe_crlibre/wizards/account_move_reversal.py`
- Modify: `addons/l10n_cr_fe_crlibre/views/account_move_reversal_views.xml`
- Test: `addons/l10n_cr_fe_crlibre/tests/test_account_move_reversal.py`

**Interfaces:**
- Consumes: `L10N_CR_FE_MOTIVO_NC`, `L10N_CR_FE_MOTIVO_CODIGO_MAP`, `L10N_CR_FE_CODIGO_REFERENCIA` (ya importados en el wizard desde `models/account_move.py`); campos existentes `l10n_cr_fe_applicable`, `l10n_cr_fe_motivo`, `move_ids`, `new_move_ids` (este último, nativo de `account.move.reversal`).
- Produces: campo `l10n_cr_fe_line_ids` (Many2many a `account.move.line`) y método `_l10n_cr_fe_is_partial_correction() -> bool` en el wizard — ambos usados por Task 2.

- [ ] **Step 1: Escribir el test que falla — valida que se exige al menos una línea seleccionada**

En `addons/l10n_cr_fe_crlibre/tests/test_account_move_reversal.py`, agregar al final de la clase `TestAccountMoveReversalFe` (después de `test_refund_moves_copies_motivo_to_credit_note`):

```python
    def test_refund_moves_requires_at_least_one_selected_line_for_partial_motivo(self):
        from odoo.exceptions import UserError
        wizard = self.env['account.move.reversal'].with_context(
            active_model='account.move', active_ids=self.invoice.ids).create({
                'journal_id': self.invoice.journal_id.id,
                'l10n_cr_fe_motivo': 'correccion_monto',
            })
        with self.assertRaises(UserError):
            wizard.refund_moves()

    def test_refund_moves_anulacion_total_does_not_require_line_selection(self):
        wizard = self.env['account.move.reversal'].with_context(
            active_model='account.move', active_ids=self.invoice.ids).create({
                'journal_id': self.invoice.journal_id.id,
                'l10n_cr_fe_motivo': 'anulacion_total',
            })
        action = wizard.refund_moves()
        credit_note = self.env['account.move'].browse(action['res_id'])
        credit_lines = credit_note.invoice_line_ids.filtered(lambda l: l.display_type == 'product')
        self.assertEqual(len(credit_lines), 1)
```

- [ ] **Step 2: Correr los tests para confirmar que fallan**

Run: `MSYS_NO_PATHCONV=1 docker exec erp-odoo-1 odoo -d odoo --addons-path=/usr/lib/python3/dist-packages/odoo/addons,/mnt/extra-addons -u l10n_cr_fe_crlibre --test-enable --test-tags /l10n_cr_fe_crlibre:TestAccountMoveReversalFe.test_refund_moves_requires_at_least_one_selected_line_for_partial_motivo --stop-after-init --http-port=8169 --db_host=db --db_user=odoo --db_password=odoo`

Expected: FAIL — `AttributeError` o similar, porque `refund_moves()` todavía no valida nada (el test espera un `UserError` que no se lanza).

- [ ] **Step 3: Agregar el campo `l10n_cr_fe_line_ids` y la validación en el wizard**

Reemplazar el contenido completo de `addons/l10n_cr_fe_crlibre/wizards/account_move_reversal.py` por:

```python
from odoo import _, api, fields, models
from odoo.exceptions import UserError

from odoo.addons.l10n_cr_fe_crlibre.models.account_move import (
    L10N_CR_FE_CODIGO_REFERENCIA,
    L10N_CR_FE_MOTIVO_CODIGO_MAP,
    L10N_CR_FE_MOTIVO_NC,
)


class AccountMoveReversal(models.TransientModel):
    _inherit = 'account.move.reversal'

    l10n_cr_fe_applicable = fields.Boolean(compute='_compute_l10n_cr_fe_applicable')
    l10n_cr_fe_is_admin = fields.Boolean(compute='_compute_l10n_cr_fe_is_admin')
    l10n_cr_fe_motivo = fields.Selection(L10N_CR_FE_MOTIVO_NC, string="Motivo de la nota de crédito")
    l10n_cr_fe_codigo_referencia = fields.Selection(
        L10N_CR_FE_CODIGO_REFERENCIA, string="Código de referencia Hacienda",
        compute='_compute_l10n_cr_fe_codigo_referencia', store=True, readonly=False)
    l10n_cr_fe_line_ids = fields.Many2many(
        'account.move.line', string="Líneas a corregir",
        domain="[('move_id', 'in', move_ids), ('display_type', '=', 'product')]")

    @api.depends('move_ids')
    def _compute_l10n_cr_fe_applicable(self):
        for wizard in self:
            wizard.l10n_cr_fe_applicable = bool(
                wizard.move_ids and len(wizard.move_ids) == 1
                and wizard.move_ids.move_type == 'out_invoice'
                and wizard.move_ids.l10n_cr_fe_clave)

    def _compute_l10n_cr_fe_is_admin(self):
        is_admin = self.env.user.has_group('l10n_cr_fe_crlibre.group_fe_admin')
        for wizard in self:
            wizard.l10n_cr_fe_is_admin = is_admin

    @api.depends('l10n_cr_fe_motivo')
    def _compute_l10n_cr_fe_codigo_referencia(self):
        for wizard in self:
            wizard.l10n_cr_fe_codigo_referencia = L10N_CR_FE_MOTIVO_CODIGO_MAP.get(wizard.l10n_cr_fe_motivo)

    def _prepare_default_reversal(self, move):
        return {
            **super()._prepare_default_reversal(move),
            'l10n_cr_fe_motivo': self.l10n_cr_fe_motivo,
            'l10n_cr_fe_codigo_referencia': self.l10n_cr_fe_codigo_referencia,
            'l10n_cr_fe_razon': self.reason,
        }

    def _l10n_cr_fe_is_partial_correction(self):
        self.ensure_one()
        return bool(
            self.l10n_cr_fe_applicable
            and self.l10n_cr_fe_motivo
            and self.l10n_cr_fe_motivo != 'anulacion_total')

    def refund_moves(self):
        if self._l10n_cr_fe_is_partial_correction() and not self.l10n_cr_fe_line_ids:
            raise UserError(_("Selecciona al menos un producto a corregir."))
        return super().refund_moves()
```

- [ ] **Step 4: Agregar el campo a la vista, visible solo para motivos parciales**

En `addons/l10n_cr_fe_crlibre/views/account_move_reversal_views.xml`, reemplazar el `<field name="arch" type="xml">` completo por:

```xml
        <field name="arch" type="xml">
            <field name="reason" position="before">
                <field name="l10n_cr_fe_applicable" invisible="1"/>
                <field name="l10n_cr_fe_is_admin" invisible="1"/>
                <field name="l10n_cr_fe_motivo" invisible="not l10n_cr_fe_applicable"
                       required="l10n_cr_fe_applicable"/>
                <field name="l10n_cr_fe_codigo_referencia" invisible="not l10n_cr_fe_applicable"
                       readonly="not l10n_cr_fe_is_admin"/>
                <field name="l10n_cr_fe_line_ids"
                       invisible="not l10n_cr_fe_applicable or l10n_cr_fe_motivo == 'anulacion_total'">
                    <list>
                        <field name="product_id"/>
                        <field name="quantity"/>
                        <field name="price_unit"/>
                        <field name="price_subtotal" string="Importe"/>
                    </list>
                </field>
            </field>
        </field>
```

- [ ] **Step 5: Correr los tests para confirmar que pasan**

Run: `MSYS_NO_PATHCONV=1 docker exec erp-odoo-1 odoo -d odoo --addons-path=/usr/lib/python3/dist-packages/odoo/addons,/mnt/extra-addons -u l10n_cr_fe_crlibre --test-enable --test-tags /l10n_cr_fe_crlibre:TestAccountMoveReversalFe --stop-after-init --http-port=8169 --db_host=db --db_user=odoo --db_password=odoo`

Expected: PASS — todos los tests de `TestAccountMoveReversalFe`, incluyendo los 2 nuevos y los 3 preexistentes (sin regresión).

- [ ] **Step 6: Commit**

```bash
git add addons/l10n_cr_fe_crlibre/wizards/account_move_reversal.py addons/l10n_cr_fe_crlibre/views/account_move_reversal_views.xml addons/l10n_cr_fe_crlibre/tests/test_account_move_reversal.py
git commit -m "feat(l10n_cr_fe): campo de seleccion de lineas en el asistente de Nota de Credito"
```

---

### Task 2: Filtrar las líneas no seleccionadas en la nota de crédito creada

**Files:**
- Modify: `addons/l10n_cr_fe_crlibre/wizards/account_move_reversal.py`
- Test: `addons/l10n_cr_fe_crlibre/tests/test_account_move_reversal.py`

**Interfaces:**
- Consumes: `l10n_cr_fe_line_ids` y `_l10n_cr_fe_is_partial_correction()` de Task 1; `move_ids`, `new_move_ids` (nativos de `account.move.reversal`).
- Produces: método `_l10n_cr_fe_remove_unselected_lines()` en el wizard, llamado desde `refund_moves()`. Comportamiento final observable: la nota de crédito creada por "Revertir" solo contiene las líneas de producto que el usuario marcó (para motivos distintos de `anulacion_total`).

- [ ] **Step 1: Escribir los tests que fallan**

En `addons/l10n_cr_fe_crlibre/tests/test_account_move_reversal.py`, agregar dentro de `TestAccountMoveReversalFe` un helper y 3 tests nuevos, después de los tests agregados en Task 1:

```python
    def _create_multi_line_invoice(self):
        product_b = self.env['product.product'].create({
            'name': 'Producto B', 'l10n_cr_fe_cabys': '0111101000001'})
        product_c = self.env['product.product'].create({
            'name': 'Producto C', 'l10n_cr_fe_cabys': '0111101000002'})
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'company_id': self.company.id,
            'partner_id': self.partner.id,
            'l10n_cr_fe_clave': '6' * 50,
            'l10n_cr_fe_state': 'aceptado',
            'invoice_line_ids': [
                (0, 0, {'product_id': self.product.id, 'quantity': 5, 'price_unit': 1200.0,
                        'name': 'Producto demo', 'tax_ids': [(6, 0, [])]}),
                (0, 0, {'product_id': product_b.id, 'quantity': 1, 'price_unit': 600.0,
                        'name': 'Producto B', 'tax_ids': [(6, 0, [])]}),
                (0, 0, {'product_id': product_c.id, 'quantity': 5, 'price_unit': 1500.0,
                        'name': 'Producto C', 'tax_ids': [(6, 0, [])]}),
            ],
        })
        invoice.action_post()
        return invoice

    def test_refund_moves_keeps_only_selected_lines(self):
        invoice = self._create_multi_line_invoice()
        lines = invoice.invoice_line_ids.filtered(lambda l: l.display_type == 'product')
        wizard = self.env['account.move.reversal'].with_context(
            active_model='account.move', active_ids=invoice.ids).create({
                'journal_id': invoice.journal_id.id,
                'l10n_cr_fe_motivo': 'correccion_monto',
                'l10n_cr_fe_line_ids': [(6, 0, lines[0].ids)],
            })
        action = wizard.refund_moves()
        credit_note = self.env['account.move'].browse(action['res_id'])
        credit_lines = credit_note.invoice_line_ids.filtered(lambda l: l.display_type == 'product')
        self.assertEqual(len(credit_lines), 1)
        self.assertEqual(credit_lines.product_id, lines[0].product_id)
        self.assertEqual(credit_lines.quantity, 5)

    def test_refund_moves_keeps_multiple_selected_lines(self):
        invoice = self._create_multi_line_invoice()
        lines = invoice.invoice_line_ids.filtered(lambda l: l.display_type == 'product')
        selected = lines[0] | lines[2]
        wizard = self.env['account.move.reversal'].with_context(
            active_model='account.move', active_ids=invoice.ids).create({
                'journal_id': invoice.journal_id.id,
                'l10n_cr_fe_motivo': 'devolucion_mercancia',
                'l10n_cr_fe_line_ids': [(6, 0, selected.ids)],
            })
        action = wizard.refund_moves()
        credit_note = self.env['account.move'].browse(action['res_id'])
        credit_lines = credit_note.invoice_line_ids.filtered(lambda l: l.display_type == 'product')
        self.assertEqual(len(credit_lines), 2)
        self.assertEqual(
            set(credit_lines.mapped('product_id.id')),
            {lines[0].product_id.id, lines[2].product_id.id})

    def test_refund_moves_anulacion_total_keeps_all_lines_regardless_of_selection(self):
        invoice = self._create_multi_line_invoice()
        wizard = self.env['account.move.reversal'].with_context(
            active_model='account.move', active_ids=invoice.ids).create({
                'journal_id': invoice.journal_id.id,
                'l10n_cr_fe_motivo': 'anulacion_total',
            })
        action = wizard.refund_moves()
        credit_note = self.env['account.move'].browse(action['res_id'])
        credit_lines = credit_note.invoice_line_ids.filtered(lambda l: l.display_type == 'product')
        self.assertEqual(len(credit_lines), 3)
```

- [ ] **Step 2: Correr los tests para confirmar que fallan**

Run: `MSYS_NO_PATHCONV=1 docker exec erp-odoo-1 odoo -d odoo --addons-path=/usr/lib/python3/dist-packages/odoo/addons,/mnt/extra-addons -u l10n_cr_fe_crlibre --test-enable --test-tags /l10n_cr_fe_crlibre:TestAccountMoveReversalFe.test_refund_moves_keeps_only_selected_lines --stop-after-init --http-port=8169 --db_host=db --db_user=odoo --db_password=odoo`

Expected: FAIL — `test_refund_moves_keeps_only_selected_lines` falla porque la nota de crédito todavía tiene las 3 líneas (no se ha implementado el filtrado).

- [ ] **Step 3: Implementar el filtrado**

En `addons/l10n_cr_fe_crlibre/wizards/account_move_reversal.py`, reemplazar el método `refund_moves` (agregado en Task 1) y agregar el nuevo método justo después:

```python
    def refund_moves(self):
        if self._l10n_cr_fe_is_partial_correction() and not self.l10n_cr_fe_line_ids:
            raise UserError(_("Selecciona al menos un producto a corregir."))
        action = super().refund_moves()
        if self._l10n_cr_fe_is_partial_correction():
            self._l10n_cr_fe_remove_unselected_lines()
        return action

    def _l10n_cr_fe_remove_unselected_lines(self):
        self.ensure_one()
        original_lines = self.move_ids.invoice_line_ids.filtered(lambda l: l.display_type == 'product')
        new_lines = self.new_move_ids.invoice_line_ids.filtered(lambda l: l.display_type == 'product')
        selected_ids = set(self.l10n_cr_fe_line_ids.ids)
        lines_to_remove = self.env['account.move.line']
        for original_line, new_line in zip(original_lines, new_lines):
            if original_line.id not in selected_ids:
                lines_to_remove |= new_line
        lines_to_remove.unlink()
```

- [ ] **Step 4: Correr todos los tests del wizard para confirmar que pasan**

Run: `MSYS_NO_PATHCONV=1 docker exec erp-odoo-1 odoo -d odoo --addons-path=/usr/lib/python3/dist-packages/odoo/addons,/mnt/extra-addons -u l10n_cr_fe_crlibre --test-enable --test-tags /l10n_cr_fe_crlibre:TestAccountMoveReversalFe --stop-after-init --http-port=8169 --db_host=db --db_user=odoo --db_password=odoo`

Expected: PASS — los 8 tests de `TestAccountMoveReversalFe` (3 preexistentes + 2 de Task 1 + 3 de Task 2).

- [ ] **Step 5: Correr la suite completa del módulo para confirmar que no hay regresiones**

Run: `MSYS_NO_PATHCONV=1 docker exec erp-odoo-1 odoo -d odoo --addons-path=/usr/lib/python3/dist-packages/odoo/addons,/mnt/extra-addons -u l10n_cr_fe_crlibre --test-enable --test-tags /l10n_cr_fe_crlibre --stop-after-init --http-port=8169 --db_host=db --db_user=odoo --db_password=odoo`

Expected: `0 failed, 0 error(s)` en la línea final `odoo.tests.result`.

- [ ] **Step 6: Commit**

```bash
git add addons/l10n_cr_fe_crlibre/wizards/account_move_reversal.py addons/l10n_cr_fe_crlibre/tests/test_account_move_reversal.py
git commit -m "feat(l10n_cr_fe): filtrar lineas no seleccionadas al confirmar Nota de Credito parcial"
```

---

## Verificación manual pendiente (fuera de las tareas automatizadas)

Ninguna tarea de este plan corre un navegador — todas las pruebas son a nivel de modelo/ORM. El riesgo señalado en el spec (¿el campo `l10n_cr_fe_line_ids` realmente muestra checkboxes de selección en la UI, o Odoo lo renderiza distinto?) debe confirmarse manualmente en el navegador después de que ambas tareas estén mergeadas: crear una nota de crédito con motivo distinto de "Anulación total" sobre una factura de varias líneas y confirmar visualmente que el campo "Líneas a corregir" permite marcar/desmarcar filas antes de darle "Revertir". Si el checkbox no aparece como se espera, es un ajuste de vista (no de lógica) sobre lo ya implementado.
