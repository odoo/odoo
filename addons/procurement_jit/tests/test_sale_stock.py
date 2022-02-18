# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.sale.tests.common import TestSaleCommon
from odoo.tests import Form


class TestSaleStockOnly(TestSaleCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

    def test_automatic_assign(self):
        """
        This test ensures that when a picking is generated from a SO, the quantities are
        automatically reserved (the automatic reservation should only happen when `procurement_jit`
        is installed)
        """
        product = self.env['product.product'].create({'name': 'Super Product', 'type': 'product'})
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1)
        self.env['stock.quant']._update_available_quantity(product, warehouse.lot_stock_id, 3)

        so_form = Form(self.env['sale.order'])
        so_form.partner_id = self.partner_a
        with so_form.order_line.new() as line:
            line.product_id = product
            line.product_uom_qty = 3
        so = so_form.save()
        so.action_confirm()

        picking = so.picking_ids
        self.assertEqual(picking.state, 'assigned')
        self.assertEqual(picking.move_lines.reserved_availability, 3.0)

        picking.move_lines.quantity_done = 1
        action = picking.button_validate()
        wizard = Form(self.env[action['res_model']].with_context(action['context'])).save()
        wizard.process()

        backorder = picking.backorder_ids
        self.assertEqual(backorder.state, 'assigned')
        self.assertEqual(backorder.move_lines.reserved_availability, 2.0)
