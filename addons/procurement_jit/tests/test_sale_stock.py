# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.sale.tests.test_sale_common import TestCommonSaleNoChart
from odoo.tests import Form


class TestSaleStockOnly(TestCommonSaleNoChart):

    @classmethod
    def setUpClass(cls):
        super(TestSaleStockOnly, cls).setUpClass()

        cls.setUpClassicProducts()

    def test_automatic_assign(self):
        """
        This test ensures that when a picking is generated from a SO, the quantities are
        automatically reserved (the automatic reservation should only happen when `procurement_jit`
        is installed)
        """
        product = self.product_map['prod_del']
        product.type = 'product'
        self.env['stock.quant']._update_available_quantity(product, self.env.ref('stock.stock_location_stock'), 3)

        so_form = Form(self.env['sale.order'])
        so_form.partner_id = self.partner_customer_usd
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
        wizard = self.env[action['res_model']].browse(action['res_id'])
        wizard.process()

        backorder = picking.backorder_ids
        self.assertEqual(backorder.state, 'assigned')
        self.assertEqual(backorder.move_lines.reserved_availability, 2.0)
