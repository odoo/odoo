# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo

from odoo.addons.point_of_sale.tests.common import TestPoSCommon


@odoo.tests.tagged('post_install', '-at_install')
class TestPoSSaleReport(TestPoSCommon):

    def setUp(self):
        super(TestPoSSaleReport, self).setUp()
        self.config = self.basic_config
        self.product0 = self.create_product('Product 0', self.categ_basic, 0.0, 0.0)

    def test_weight_and_volume(self):
        self.product0.product_tmpl_id.weight = 3
        self.product0.product_tmpl_id.volume = 4

        self.open_new_session()
        session = self.pos_session
        orders = []

        # Process two orders
        orders.append(self.create_ui_order_data([(self.product0, 3)]))
        orders.append(self.create_ui_order_data([(self.product0, 1)]))
        self.env['pos.order'].create_from_ui(orders)
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
        self.env['pos.order'].create_from_ui([order])

        session.action_pos_session_closing_control()

        report = self.env['sale.report'].sudo().search([('product_id', '=', product_1.id)], order='id', limit=1)
        self.assertEqual(report.weight, 3)
        self.assertEqual(report.weight, 3)
        report = self.env['sale.report'].sudo().search([('product_id', '=', product_2.id)], order='id', limit=1)
        self.assertEqual(report.weight, 6)
        self.assertEqual(report.weight, 6)
