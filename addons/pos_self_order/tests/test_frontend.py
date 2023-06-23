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
                "floor_ids": self.env["restaurant.floor"].search([]),
                "self_order_table_mode": False,
            }
        )

        # we need a default tax fixed at 15% to all product because in the test prices are based on this tax.
        # some time with the localization this may not be the case. So we force it.
        self.env['product.product'].search([]).taxes_id = self.env['account.tax'].create({
            'name': 'Default Tax for Self Order',
            'amount': 15,
            'amount_type': 'percent',
        })

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
        self.pos_config.open_ui()
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

    def test_self_order_pay_after_each_tour(self):
        self.pos_config.self_order_table_mode = True
        self.pos_config.self_order_pay_after = "each"
        self.pos_config.open_ui()

        self.start_tour(
            self.pos_config._get_self_order_route(),
            "self_order_after_each_cart_tour",
            login=None,
        )
