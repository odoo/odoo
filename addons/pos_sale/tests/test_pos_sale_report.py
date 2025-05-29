# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo
from odoo import fields
from odoo.addons.point_of_sale.tests.common import TestPoSCommon


@odoo.tests.tagged('post_install', '-at_install')
class TestPoSSaleReport(TestPoSCommon):

    def setUp(self):
        super(TestPoSSaleReport, self).setUp()
        self.config = self.basic_config
        self.product0 = self.create_product('Product 0', self.categ_basic, 0.0, 0.0)
        self.partner_1 = self.env['res.partner'].create({'name': 'Test Partner 1'})
        # Ensure that adding a uom to the product with a factor != 1 
        # does not cause an error in weight and volume calculation
        self.product0.uom_id = self.env['uom.uom'].search([('name', '=', 'Dozens')], limit=1)

    def test_weight_and_volume(self):
        self.product0.product_tmpl_id.weight = 3
        self.product0.product_tmpl_id.volume = 4

        self.open_new_session()
        session = self.pos_session
        orders = []

        # Process two orders
        orders.append(self.create_ui_order_data([(self.product0, 3)]))
        orders.append(self.create_ui_order_data([(self.product0, 1)]))
        self.env['pos.order'].sync_from_ui(orders)
        # Duplicate the first line of the first order
        session.order_ids[0].lines.copy()

        session.action_pos_session_closing_control()

        # PoS Orders have negative IDs to avoid conflict, so reports[0] will correspond to the newest order
        reports = self.env['sale.report'].sudo().search([('product_id', '=', self.product0.id)], order='id', limit=2)
        self.assertEqual(reports[0].weight, 3)
        self.assertEqual(reports[0].volume, 4)
        self.assertEqual(reports[1].weight, 18)
        self.assertEqual(reports[1].volume, 24)

    def test_weight_and_volume_product_variant(self):
        colors = ['red', 'blue']
        prod_attr = self.env['product.attribute'].create({'name': 'Color', 'create_variant': 'dynamic'})
        prod_attr_values = self.env['product.attribute.value'].create([{'name': color, 'attribute_id': prod_attr.id, 'sequence': 1} for color in colors])

        uom_unit = self.env.ref('uom.product_uom_unit')
        product_template = self.env['product.template'].create({
            'name': 'Sofa',
            'uom_id': uom_unit.id,
            'uom_po_id': uom_unit.id,
            'attribute_line_ids': [(0, 0, {
                'attribute_id': prod_attr.id,
                'value_ids': [(6, 0, prod_attr_values.ids)]
            })]
        })
        prod_tmpl_attrs = self.env['product.template.attribute.value'].search([
            ('attribute_line_id', '=', product_template.attribute_line_ids.id),
            ('product_attribute_value_id', 'in', prod_attr_values.ids)
        ])

        product_1 = product_template._create_product_variant(prod_tmpl_attrs[0])
        product_1.weight = 1
        product_1.volume = 1

        product_2 = product_template._create_product_variant(prod_tmpl_attrs[1])
        product_2.weight = 2
        product_2.volume = 2

        self.open_new_session()
        session = self.pos_session

        order = self.create_ui_order_data([(product_1, 3), (product_2, 3)])
        self.env['pos.order'].sync_from_ui([order])

        session.action_pos_session_closing_control()

        report = self.env['sale.report'].sudo().search([('product_id', '=', product_1.id)], order='id', limit=1)
        self.assertEqual(report.weight, 3)
        self.assertEqual(report.weight, 3)
        report = self.env['sale.report'].sudo().search([('product_id', '=', product_2.id)], order='id', limit=1)
        self.assertEqual(report.weight, 6)
        self.assertEqual(report.weight, 6)

    def test_different_shipping_address(self):
        product_0 = self.create_product('Product 0', self.categ_basic, 0.0, 0.0)
        sale_order = self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'partner_shipping_id': self.other_customer.id,
            'order_line': [(0, 0, {
                'product_id': product_0.id,
            })],
        })
        self.open_new_session()

        data = self.create_ui_order_data([(product_0, 1)], self.customer, True)
        data['lines'][0][2]['sale_order_origin_id'] = sale_order.id
        data['lines'][0][2]['sale_order_line_id'] = sale_order.order_line[0].id
        order_ids = self.env['pos.order'].sync_from_ui([data])

        move_id = self.env['account.move'].browse(order_ids['pos.order'][0]['account_move'])
        self.assertEqual(move_id.partner_id.id, self.customer.id)
        self.assertEqual(move_id.partner_shipping_id.id, self.other_customer.id)

    def test_warehouse(self):

        self.open_new_session()
        session = self.pos_session
        orders = []

        # Process two orders
        orders.append(self.create_ui_order_data([(self.product0, 3)]))
        self.env['pos.order'].sync_from_ui(orders)

        session.action_pos_session_closing_control()

        reports = self.env['sale.report'].sudo().search([('product_id', '=', self.product0.id)], order='id', limit=2)
        self.assertEqual(reports[0].warehouse_id.id, self.config.picking_type_id.warehouse_id.id)

    def test_qty_deliverd_qty_to_deliver_in_sales_report(self):
        """
            Track the quantity of products ordered based on their picking state. for example : If an order is created for 3 products
            with the option to ship later, the products will be listed under qty_to_deliver in the sales report until the picking state
            is validated. Once validated and marked as done, the quantity will shift to qty_delivered.
        """
        self.config.ship_later = True
        self.open_new_session()
        session = self.pos_session

        orders = []

        orders.append(self.create_ui_order_data([(self.product0, 5)], self.partner_1))
        orders[0]['shipping_date'] = fields.Date.to_string(fields.Date.today())

        order = self.env['pos.order'].sync_from_ui(orders)
        order = self.env['pos.order'].browse(order['pos.order'][0]['id'])

        session.action_pos_session_closing_control()

        report = self.env['sale.report'].sudo().search([('product_id', '=', self.product0.id)], order='id')

        self.assertEqual(report.qty_to_deliver, 5)
        self.assertEqual(report.qty_delivered, 0)

        order.picking_ids.move_ids.quantity = 5.0
        order.picking_ids.button_validate()
        # flush computations and clear the cache before checking again the report
        self.env.flush_all()
        self.env.clear()

        report = self.env['sale.report'].sudo().search([('product_id', '=', self.product0.id)], order='id')

        self.assertEqual(report.qty_to_deliver, 0)
        self.assertEqual(report.qty_delivered, 5)
