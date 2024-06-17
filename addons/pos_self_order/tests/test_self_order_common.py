# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests
from odoo.addons.pos_self_order.tests.self_order_common_test import SelfOrderCommonTest


@odoo.tests.tagged("post_install", "-at_install")
class TestSelfOrderCommon(SelfOrderCommonTest):
    def test_self_order_common(self):
        self.pos_config.write({
            'self_ordering_takeaway': True,
            'self_ordering_mode': 'kiosk',
            'self_ordering_pay_after': 'each',
            'self_ordering_service_mode': 'table',
        })

        self_route = self.pos_config._get_self_order_route()

        # Verify behavior when self Order is closed
        self.start_tour(self_route, "self_order_is_close")

    def test_self_order_consultation_open(self):
        """Verify than when the pos is open and self ordering is set to consultation the banner isn't shown"""
        self.pos_config.write({'self_ordering_mode': 'consultation'})

        self_route = self.pos_config._get_self_order_route()

        # Verify behavior when self Order is opened
        self.pos_config.with_user(self.pos_user).open_ui()
        self.start_tour(self_route, "self_order_is_open_consultation")
