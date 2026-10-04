# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import Command
from odoo.tests import Form, tagged

from odoo.addons.mrp.tests.common import TestMrpCommon


@tagged('post_install', '-at_install')
class TestMrpProductionOverQty(TestMrpCommon):
    """Regression for opw-6568704.

    When a manufacturing order is produced for more than a planned quantity that
    was later reduced, the finished move's demand can be left out of sync with
    ``product_qty``. In that state ``_post_inventory`` used to scale the produced
    quantity by ``unit_factor`` (= demand / product_qty), inflating the finished
    move (e.g. producing 10 against a plan of 2 recorded 10 * (10 / 2) = 50).
    """

    def _make_bom(self):
        finished = self.env['product.product'].create({'name': 'OPW6568704 Finished', 'type': 'consu'})
        component = self.env['product.product'].create({'name': 'OPW6568704 Component', 'type': 'consu'})
        bom = self.env['mrp.bom'].create({
            'product_tmpl_id': finished.product_tmpl_id.id,
            'product_qty': 10.0,
            'type': 'normal',
            'bom_line_ids': [Command.create({'product_id': component.id, 'product_qty': 1.0})],
        })
        return finished, bom

    def _finished_move(self, mo, product):
        return mo.move_finished_ids.filtered(lambda m: m.product_id == product)

    def test_overproduction_after_qty_reduction_not_double_scaled(self):
        finished, bom = self._make_bom()

        # Control: an ordinary MO records exactly the manufactured quantity.
        control = self.env['mrp.production'].create({
            'product_id': finished.id, 'bom_id': bom.id, 'product_qty': 10.0})
        control.action_confirm()
        with Form(control) as form:
            form.qty_producing = 10.0
        control.with_context(skip_consumption=True, skip_backorder=True).button_mark_done()
        self.assertEqual(control.state, 'done')
        self.assertEqual(self._finished_move(control, finished).quantity, 10.0)

        # Bug scenario: confirm for 10 (finished demand = 10), register 10 as
        # produced, then reduce the plan to 2 so the finished move demand (10) is
        # left out of sync with product_qty (2). The finished move must still be
        # produced as 10, not 10 * (10 / 2) = 50.
        mo = self.env['mrp.production'].create({
            'product_id': finished.id, 'bom_id': bom.id, 'product_qty': 10.0})
        mo.action_confirm()
        with Form(mo) as form:
            form.qty_producing = 10.0
        mo.product_qty = 2.0
        self.assertEqual(
            self._finished_move(mo, finished).product_uom_qty, 10.0,
            "precondition: the finished move demand stays out of sync with product_qty")
        mo.with_context(skip_consumption=True, skip_backorder=True).button_mark_done()
        self.assertEqual(mo.state, 'done')
        self.assertEqual(
            self._finished_move(mo, finished).quantity, 10.0,
            "finished quantity must equal the produced quantity (10), not be inflated by unit_factor")
