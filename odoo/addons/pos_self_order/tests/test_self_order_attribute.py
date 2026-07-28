# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests
from odoo.addons.pos_self_order.tests.self_order_common_test import SelfOrderCommonTest


@odoo.tests.tagged("post_install", "-at_install")
class TestSelfOrderAttribute(SelfOrderCommonTest):
    def test_self_order_attribute(self):
        self.pos_config.write({
            'self_ordering_default_user_id': self.pos_admin.id,
            'self_ordering_takeaway': False,
            'self_ordering_mode': 'mobile',
            'self_ordering_pay_after': 'each',
            'self_ordering_service_mode': 'counter',
        })

        product = self.env['product.product'].search([('name', '=', 'Desk Organizer')])[0]
        product.attribute_line_ids[0].product_template_value_ids[0].price_extra = 0.0
        product.attribute_line_ids[0].product_template_value_ids[1].price_extra = 1.0
        product.attribute_line_ids[0].product_template_value_ids[2].price_extra = 2.0

        self.pos_config.with_user(self.pos_user).open_ui()
        self_route = self.pos_config._get_self_order_route()

        self.start_tour(self_route, "self_attribute_selector")
        order = self.pos_config.current_session_id.order_ids[0]
        self.assertEqual(order.lines[0].price_extra, 1.0)
        self.assertEqual(order.lines[1].price_extra, 2.0)
