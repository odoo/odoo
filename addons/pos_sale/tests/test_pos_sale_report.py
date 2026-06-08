# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo
from odoo.addons.point_of_sale.tests.common import TestPoSCommon
from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon


@odoo.tests.tagged('post_install', '-at_install')
class TestPoSSaleReport(TestPoSCommon, TestPointOfSaleHttpCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.pos_user.write({
            'group_ids': [
                (4, cls.env.ref('sales_team.group_sale_salesman_all_leads').id),
            ]
        })

    def setUp(self):
        super(TestPoSSaleReport, self).setUp()
        self.config = self.basic_config
        self.product0 = self.create_product('Product 0', self.categ_basic, 0.0, 0.0)
        self.partner_1 = self.env['res.partner'].create({'name': 'Test Partner 1'})
        # Ensure that adding a uom to the product with a factor != 1
        # does not cause an error in weight and volume calculation
        self.uom_reference = self.env['uom.uom'].create({
            'name': 'Reference Unit',
            'relative_factor': 1,
        })
        self.uom_dozen = self.env['uom.uom'].create({
            'name': 'Dozen',
            'relative_factor': 12,
            'relative_uom_id': self.uom_reference.id,
        })
        self.product0.uom_id = self.uom_dozen

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

    def test_refund_line_report_prices_sign(self):
        test_product = self.env['product.product'].create({
            'name': 'Test Product',
            'list_price': 10.00,
            'taxes_id': False,
            'available_in_pos': True,
        })
        self.main_pos_config.with_user(self.pos_user).open_ui()
        current_session = self.main_pos_config.current_session_id

        self.start_tour("/pos/ui/%d" % self.main_pos_config.id, 'refund_multiple_products_amounts_compliance', login="pos_user")

        total_cash_payment = sum(current_session.mapped('order_ids.payment_ids').filtered(
            lambda payment: payment.payment_method_id.type == 'cash').mapped('amount')
        )
        current_session.post_closing_cash_details(total_cash_payment)
        current_session.close_session_from_ui()
        self.assertEqual(current_session.state, 'closed')

        report = self.env['sale.report'].sudo().search([('product_id', '=', test_product.id), ('name', 'ilike', '% REFUND')], order='id', limit=1)
        self.assertEqual(report.product_uom_qty, -2)
        self.assertEqual(report.price_subtotal, report.product_uom_qty * test_product.list_price)
        self.assertEqual(report.price_total, report.price_subtotal)

    def test_weight_and_volume_product_variant(self):
        colors = ['red', 'blue']
        prod_attr = self.env['product.attribute'].create({'name': 'Color', 'create_variant': 'dynamic'})
        prod_attr_values = self.env['product.attribute.value'].create([{'name': color, 'attribute_id': prod_attr.id, 'sequence': 1} for color in colors])

        uom_unit = self.env.ref('uom.product_uom_unit')
        product_template = self.env['product.template'].create({
            'name': 'Sofa',
            'uom_id': uom_unit.id,
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
        sale_order = self.env['sale.order'].sudo().create({
            'partner_id': self.customer.id,
            'partner_shipping_id': self.other_customer.id,
            'order_line': [(0, 0, {
                'product_id': product_0.id,
            })],
        })
        self.open_new_session()

        data = self.create_ui_order_data([(product_0, 1)], {}, self.customer, True)
        data['lines'][0][2]['sale_order_origin_id'] = sale_order.id
        data['lines'][0][2]['sale_order_line_id'] = sale_order.order_line[0].id
        order_ids = self.env['pos.order'].sync_from_ui([data])

        move_id = self.env['account.move'].browse(order_ids['pos.order'][0]['account_move'])
        self.assertEqual(move_id.partner_id.id, self.customer.id)
        self.assertEqual(move_id.partner_shipping_id.id, self.other_customer.id)
