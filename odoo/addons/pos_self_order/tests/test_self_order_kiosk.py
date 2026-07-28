# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests
from odoo.addons.pos_self_order.tests.self_order_common_test import SelfOrderCommonTest


@odoo.tests.tagged("post_install", "-at_install")
class TestSelfOrderKiosk(SelfOrderCommonTest):
    def test_self_order_kiosk(self):
        self.pos_config.write({
            'self_ordering_takeaway': True,
            'self_ordering_mode': 'kiosk',
            'self_ordering_pay_after': 'each',
            'self_ordering_service_mode': 'table',
        })

        self.pos_config.with_user(self.pos_user).open_ui()
        self_route = self.pos_config._get_self_order_route()

        # Kiosk, each, table
        self.start_tour(self_route, "self_kiosk_each_table_takeaway_in")
        self.start_tour(self_route, "self_kiosk_each_table_takeaway_out")

        self.pos_config.write({
            'self_ordering_service_mode': 'counter',
        })

        # Kiosk, each, counter
        self.start_tour(self_route, "self_kiosk_each_counter_takeaway_in")
        self.start_tour(self_route, "self_kiosk_each_counter_takeaway_out")

        # Cancel behavior
        self.start_tour(self_route, "self_order_kiosk_cancel")

    def test_duplicate_order_kiosk(self):
        self.pos_config.write({
            'self_ordering_takeaway': False,
            'self_ordering_mode': 'kiosk',
            'self_ordering_pay_after': 'each',
        })
        self.pos_config.with_user(self.pos_user).open_ui()
        self_route = self.pos_config._get_self_order_route()
        self.start_tour(self_route, "self_simple_order")
        orders = self.pos_config.current_session_id.order_ids
        self.assertEqual(len(orders.export_for_ui_shared_order(self.pos_config.id)), 1)
