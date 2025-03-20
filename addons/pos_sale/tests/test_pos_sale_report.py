# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo
from odoo import fields
from odoo.addons.point_of_sale.tests.test_common import TestPointOfSaleDataHttpCommon


@odoo.tests.tagged('post_install', '-at_install')
class TestPoSSaleReport(TestPointOfSaleDataHttpCommon):

    def setUp(self):
        super().setUp()
        self.env.user.group_ids += self.env.ref('sales_team.group_sale_salesman')
        self.product_awesome_item.product_variant_id.write({
            'categ_id': self.product_category.id,
            'lst_price': 0,
            'list_price': 0,
        })

    def test_weight_and_volume(self):
        self.product_awesome_item.weight = 3
        self.product_awesome_item.volume = 4
        self.pos_config.open_ui()
        orders = []

        # Process two orders
        orders.append(self.make_order_data([
            {'product_id': self.product_awesome_item.product_variant_id, 'qty': 3, 'discount': 0},
        ]))
        orders.append(self.make_order_data([
            {'product_id': self.product_awesome_item.product_variant_id, 'qty': 1, 'discount': 0},
        ]))
        self.env['pos.order'].sync_from_ui(orders)
        # Duplicate the first line of the first order
        self.pos_config.current_session_id.order_ids[0].lines.copy()
        self.pos_config.current_session_id.action_pos_session_closing_control()

        # PoS Orders have negative IDs to avoid conflict, so reports[0] will correspond to the newest order
        reports = self.env['sale.report'].sudo().search([
            ('product_id', '=', self.product_awesome_item.product_variant_id.id)], order='id', limit=2)
        self.assertEqual(reports[0].weight, 3)
        self.assertEqual(reports[0].volume, 4)
        self.assertEqual(reports[1].weight, 18)
        self.assertEqual(reports[1].volume, 24)

    def test_weight_and_volume_product_variant(self):
        product_1 = self.product_configurable.product_variant_ids[0]
        product_1.weight = 1
        product_1.volume = 1
        product_2 = self.product_configurable.product_variant_ids[1]
        product_2.weight = 2
        product_2.volume = 2

        self.pos_config.open_ui()
        order = self.make_order_data([
            {'product_id': product_1, 'qty': 3, 'discount': 0},
            {'product_id': product_2, 'qty': 3, 'discount': 0},
        ], [
            {'payment_method_id': self.bank_payment_method, 'amount': 21},
        ])

        order = self.env['pos.order'].sync_from_ui([order])
        report = self.env['sale.report'].sudo().search([('product_id', '=', product_1.id)], order='id', limit=1)
        self.assertEqual(report.weight, 3)
        self.assertEqual(report.weight, 3)
        report = self.env['sale.report'].sudo().search([('product_id', '=', product_2.id)], order='id', limit=1)
        self.assertEqual(report.weight, 6)
        self.assertEqual(report.weight, 6)

    def test_different_shipping_address(self):
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_one.id,
            'partner_shipping_id': self.partner_two.id,
            'order_line': [(0, 0, {
                'product_id': self.product_awesome_item.product_variant_id.id,
            })],
        })

        self.pos_config.open_ui()
        order = self.create_order([{
            'product_id': self.product_awesome_item.product_variant_id,
            'qty': 1, 'discount': 0,
            'sale_order_origin_id': sale_order.id,
            'sale_order_line_id': sale_order.order_line[0].id,
        }], [
            {'payment_method_id': self.bank_payment_method, 'amount': 0},
        ], False, False, self.partner_one, True)

        self.assertEqual(order.account_move.partner_id.id, self.partner_one.id)
        self.assertEqual(order.account_move.partner_shipping_id.id, self.partner_two.id)

    def test_warehouse(self):
        # Process two orders
        self.pos_config.open_ui()
        self.create_order([
            {'product_id': self.product_awesome_item.product_variant_id, 'qty': 3, 'discount': 0},
        ], [
            {'payment_method_id': self.bank_payment_method, 'amount': 0},
        ])
        self.pos_config.current_session_id.action_pos_session_closing_control()

        reports = self.env['sale.report'].sudo().search([
            ('product_id', '=', self.product_awesome_item.product_variant_id.id)], order='id', limit=2)
        self.assertEqual(reports[0].warehouse_id.id, self.pos_config.picking_type_id.warehouse_id.id)

    def test_qty_deliverd_qty_to_deliver_in_sales_report(self):
        """
            Track the quantity of products ordered based on their picking state. for example : If an order is created for 3 products
            with the option to ship later, the products will be listed under qty_to_deliver in the sales report until the picking state
            is validated. Once validated and marked as done, the quantity will shift to qty_delivered.
        """
        self.pos_config.ship_later = True
        self.pos_config.open_ui()
        order = self.make_order_data([
            {'product_id': self.product_awesome_item.product_variant_id, 'qty': 5, 'discount': 0},
        ], [
            {'payment_method_id': self.bank_payment_method, 'amount': 0},
        ], False, False, self.partner_one)
        order['shipping_date'] = fields.Date.to_string(fields.Date.today())
        orders = self.env['pos.order'].sync_from_ui([order])
        order = self.env['pos.order'].browse(orders['pos.order'][0]['id'])
        self.pos_config.current_session_id.action_pos_session_closing_control()

        report = self.env['sale.report'].sudo().search([
            ('product_id', '=', self.product_awesome_item.product_variant_id.id)], order='id')
        self.assertEqual(report.qty_to_deliver, 5)
        self.assertEqual(report.qty_delivered, 0)

        order.picking_ids.move_ids.quantity = 5.0
        order.picking_ids.button_validate()
        # flush computations and clear the cache before checking again the report
        self.env.flush_all()
        self.env.clear()

        report = self.env['sale.report'].sudo().search([
            ('product_id', '=', self.product_awesome_item.product_variant_id.id)], order='id')

        self.assertEqual(report.qty_to_deliver, 0)
        self.assertEqual(report.qty_delivered, 5)
