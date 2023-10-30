# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests
from odoo.addons.pos_self_order.tests.self_order_common_test import SelfOrderCommonTest


@odoo.tests.tagged("post_install", "-at_install")
class TestSelfOrderCombo(SelfOrderCommonTest):
    def test_self_order_combo(self):
        self.pos_config.write({
            'self_ordering_default_user_id': self.pos_admin.id,
            'self_ordering_takeaway': False,
            'self_ordering_mode': 'mobile',
            'self_ordering_pay_after': 'each',
            'self_ordering_service_mode': 'counter',
        })

        self.pos_config.with_user(self.pos_user).open_ui()
        self_route = self.pos_config._get_self_order_route()

        self.start_tour(self_route, "self_combo_selector")
