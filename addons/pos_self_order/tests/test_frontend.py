# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests
from odoo.addons.pos_self_order.tests.self_order_common_test import SelfOrderCommonTest


@odoo.tests.tagged("post_install", "-at_install")
class TestFrontendMobile(SelfOrderCommonTest):

    def test_self_order_menu_only_tour(self):
        self.pos_config.self_order_table_mode = False
        self.start_tour(
            self.pos_config._get_self_order_route(),
            "self_order_menu_only_tour",
            login=None,
        )

    def test_self_order_pay_after_meal_tour(self):
        self.pos_config.self_order_table_mode = True
        self.pos_config.self_order_pay_after = "meal"
        self.pos_config.with_user(self.pos_user).open_ui()
        self.start_tour(
            self.pos_config._get_self_order_route(),
            "self_order_after_meal_cart_tour",
            login=None,
        )
        self.start_tour(
            self.pos_config._get_self_order_route(),
            "self_order_after_meal_product_tour",
            login=None,
        )

    def test_self_order_menu_only_accessing_without_token_tour(self):
        self.pos_config.self_order_table_mode = True
        self.pos_config.with_user(self.pos_user).open_ui()
        self.start_tour(
            f"/menu/{self.pos_config.id}",
            "self_order_menu_only_tour",
            login=None,
        )
    def test_self_order_my_orders_tour(self):
        self.pos_config.self_order_table_mode = True
        self.pos_config.self_order_pay_after = "meal"
        self.pos_config.with_user(self.pos_user).open_ui()
        self.start_tour(
            self.pos_config._get_self_order_route(),
            "test_self_order_my_orders_tour",
            login=None,
        )

    def test_kiosk_order_tour(self):
        self.pos_config.self_order_kiosk = True
        self.pos_config.with_user(self.pos_user).open_ui()
        self.start_tour(
            self.pos_config.self_order_kiosk_url,
            "kiosk_order_tour",
            login=None,
        )
        order_count = self.env['pos.order'].search_count([('tracking_number', '=', 'A1')])
        self.assertEqual(order_count, 1)

    def test_kiosk_order_table_service_tour(self):
        self.pos_config.self_order_kiosk = True
        self.pos_config.self_order_kiosk_mode = "table"
        self.pos_config.with_user(self.pos_user).open_ui()
        self.start_tour(
            self.pos_config.self_order_kiosk_url,
            "kiosk_order_tour_table_service",
            login=None,
        )
        order_count = self.env['pos.order'].search_count([('tracking_number', '=', 'A1')])
        self.assertEqual(order_count, 1)

    def test_kiosk_order_takeaway_tour(self):
        self.pos_config.self_order_kiosk = True
        self.pos_config.self_order_kiosk_mode = "table"
        self.pos_config.self_order_kiosk_takeaway = True
        self.pos_config.with_user(self.pos_user).open_ui()
        self.start_tour(
            self.pos_config.self_order_kiosk_url,
            "kiosk_order_tour_takeaway",
            login=None,
        )
