# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests
from odoo.addons.pos_self_order.tests.self_order_common_test import SelfOrderCommonTest


@odoo.tests.tagged("post_install", "-at_install")
class TestSelfOrderMobile(SelfOrderCommonTest):
    def test_self_order_mobile(self):
        self.pos_config.write({
            'self_ordering_takeaway': True,
            'self_ordering_mode': 'mobile',
            'self_ordering_pay_after': 'each',
            'self_ordering_service_mode': 'table',
        })

        self.pos_config.with_user(self.pos_user).open_ui()
        self_route = self.pos_config._get_self_order_route()

        # Mobile, each, table
        self.start_tour(self_route, "self_mobile_each_table_takeaway_in")
        self.start_tour(self_route, "self_mobile_each_table_takeaway_out")

        self.pos_config.write({
            'self_ordering_service_mode': 'counter',
        })

        # Mobile, each, counter
        self.start_tour(self_route, "self_mobile_each_counter_takeaway_in")
        self.start_tour(self_route, "self_mobile_each_counter_takeaway_out")

        self.pos_config.write({
            'self_ordering_pay_after': 'meal',
            'self_ordering_service_mode': 'table',
        })

        # Mobile, meal, table
        self.start_tour(self_route, "self_mobile_meal_table_takeaway_in")
        self.start_tour(self_route, "self_mobile_meal_table_takeaway_out")

        self.pos_config.write({
            'self_ordering_service_mode': 'counter',
        })

        # Mobile, meal, counter
        self.start_tour(self_route, "self_mobile_meal_counter_takeaway_in")
        self.start_tour(self_route, "self_mobile_meal_counter_takeaway_out")

        # Cancel in meal
        self.start_tour(self_route, "self_order_mobile_meal_cancel")

        self.pos_config.write({
            'self_ordering_pay_after': 'each',
        })

        # Cancel in each
        self.start_tour(self_route, "self_order_mobile_each_cancel")
