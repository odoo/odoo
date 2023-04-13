# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests


@odoo.tests.tagged("post_install", "-at_install")
class TestFrontendMobile(odoo.tests.HttpCase):
    browser_size = "375x667"
    touch_enabled = True

    def setUp(self):
        super().setUp()
        self.pos_config = self.env["pos.config"].create(
            {
                "name": "BarTest",
                "module_pos_restaurant": True,
                "self_order_view_mode": True,
                "self_order_table_mode": False,
            }
        )
        basic_product = lambda i: {
            "name": f"Product {i} test",
            "type": "product",
            "available_in_pos": True,
            "list_price": i,
            "taxes_id": False,
        }
        self.env["product.product"].create([basic_product(i) for i in range(1, 1000)])

    def test_self_order_view_mode_tour(self):
        self.pos_config.self_order_table_mode = False
        self.start_tour(
            self.pos_config._get_self_order_route(),
            "pos_qr_menu_tour",
            login=None,
        )

    def test_self_order_tour(self):
        self.pos_config.self_order_table_mode = True
        self.pos_config.self_order_pay_after = "meal"
        self.pos_config.open_ui()
        self.start_tour(
            self.pos_config._get_self_order_route(),
            "self_order_tour",
            login=None,
        )
