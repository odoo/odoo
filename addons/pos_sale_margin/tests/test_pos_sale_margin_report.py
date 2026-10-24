# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import odoo
from odoo import Command

from odoo.addons.point_of_sale.tests.common import TestPoSCommon


@odoo.tests.tagged('post_install', '-at_install')
class TestPoSSaleMarginReport(TestPoSCommon):

    def setUp(self):
        super(TestPoSSaleMarginReport, self).setUp()
        self.config = self.basic_config

    def test_pos_sale_margin_report(self):

        product1 = self.create_product('Product 1', self.categ_basic, 150, standard_price=50)

        self.open_new_session()
        session = self.pos_session

        self.env['pos.order'].create({
            'session_id': session.id,
            'lines': [(0, 0, {
                'name': "OL/0001",
                'product_id': product1.id,
                'price_unit': 450,
                'discount': 5.0,
                'qty': 1.0,
                'price_subtotal': 150,
                'price_subtotal_incl': 150,
                'total_cost': 50,
            }),],
            'amount_total': 150.0,
            'amount_tax': 0.0,
            'amount_paid': 0.0,
            'amount_return': 0.0,
        })

        # PoS Orders have negative IDs to avoid conflict, so reports[0] will correspond to the newest order
        reports = self.env['sale.report'].sudo().search([('product_id', '=', product1.id)], order='id')

        self.assertEqual(reports[0].margin, 100)

    def test_pos_sale_margin_report_refund_sign(self):
        product = self.create_product('Refund Product', self.categ_basic, 150, standard_price=0)

        self.open_new_session()
        self.env['pos.order'].create({
            'session_id': self.pos_session.id,
            'is_refund': True,
            'lines': [(0, 0, {
                'name': "OL/0001",
                'product_id': product.id,
                'price_unit': 150,
                'qty': -1.0,
                'price_subtotal': 150,
                'price_subtotal_incl': 150,
                'total_cost': 0,
            })],
            'amount_total': -150.0,
            'amount_tax': 0.0,
            'amount_paid': 0.0,
            'amount_return': 0.0,
        })

        reports = self.env['sale.report'].sudo().search([('product_id', '=', product.id)], order='id')
        self.assertEqual(reports[0].margin, -150)

    def test_sale_margin_after_pos_settlement_two_step_delivery(self):
        """Test Settling a two-step delivery Sales Order in POS must not reset the
        sale line cost to 0 it keeps the product cost.
        """
        self.env.user.group_ids |= self.env.ref('sales_team.group_sale_salesman')
        warehouse = self.config.picking_type_id.warehouse_id
        warehouse.delivery_steps = 'pick_ship'
        self.categ_basic.property_cost_method = 'average'
        product = self.create_product('AVCO product', self.categ_basic, 150, standard_price=100)
        self.env['stock.quant']._update_available_quantity(product, warehouse.lot_stock_id, 10)
        sale_order = self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'warehouse_id': warehouse.id,
            'order_line': [Command.create({
                'product_id': product.id,
                'product_uom_qty': 1,
                'price_unit': 150,
                'tax_ids': [Command.clear()],
            })],
        })
        sale_order.action_confirm()
        sale_line = sale_order.order_line
        self.assertEqual(sale_line.purchase_price, 100)
        sale_order.picking_ids.button_validate()
        self.open_new_session()
        order_data = self.create_ui_order_data([{
            'product': product,
            'quantity': 1,
            'sale_order_origin_id': sale_order.id,
            'sale_order_line_id': sale_line.id,
        }], customer=self.customer)
        result = self.env['pos.order'].sync_from_ui([order_data])
        pos_order = self.env['pos.order'].browse(result['pos.order'][0]['id'])
        self.assertEqual(pos_order.picking_ids.state, 'done')
        self.assertEqual(pos_order.picking_ids.move_ids.value, 100)
        self.assertRecordValues(sale_line, [{
            'qty_delivered': 1,
            'purchase_price': 100,
            'margin': 50,
            'margin_percent': 1 / 3,
        }])
