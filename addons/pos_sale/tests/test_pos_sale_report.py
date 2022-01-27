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
