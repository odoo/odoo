# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests

@odoo.tests.tagged("post_install", "-at_install")
class TestFrontend(odoo.tests.HttpCase):
    def setUp(self):
        super().setUp()
        self.pos_config_view_mode = self.env["pos.config"].create(
            {
                "name": "Bar",
                "module_pos_restaurant": True,
                "is_table_management": True,
                "self_order_view_mode": True,
                "self_order_table_mode": False,
            }
        )
        # self.pos_config_pay_after_each_mode = self.env["pos.config"].create(
        #     {
        #         "name": "Bar",
        #         "module_pos_restaurant": True,
        #         "is_table_management": True,
        #         "self_order_view_mode": True,
        #         "self_order_table_mode": True,
        #     }
        # )
        # self.pos_config_pay_after_meal_mode = self.env["pos.config"].create(
        #     {
        #         "name": "Bar",
        #         "module_pos_restaurant": True,
        #         "is_table_management": True,
        #         "self_order_view_mode": True,
        #         "self_order_table_mode": True,
        #         "self_order_pay_after": "meal",
        #     }
        # )
        basic_product = lambda i: {
            "name": f"Product {i}",
            "type": "product",
            "available_in_pos": True,
            "list_price": i,
            "taxes_id": False,
        }
        self.env["product.product"].create([basic_product(i) for i in range(1, 1000)])

    def test_self_order_view_mode_tour(self):
        self.start_tour(
            self.pos_config_view_mode._get_self_order_route(),
            "pos_qr_menu_tour",
            login=None,
            watch=True,
            step_delay=500,
        )

    # def test_self_order_pay_after_each_tour(self):
    #     self.start_tour(
    #         self.pos_config_pay_after_meal_mode._get_self_order_route(),
    #         "self_order_pay_after_each_tour",
    #         login=None,
    #         watch=True,
    #         step_delay=500,
    #     )

    # def test_self_order_pay_after_meal_tour(self):
    #     self.start_tour(
    #         # f"/menu/{self.pos_config_pay_after_meal_mode.id}",
    #         self.pos_config_pay_after_meal_mode._get_self_order_route(),
    #         "self_order_pay_after_meal_tour",
    #         login=None,
    #         watch=True,
    #         step_delay=500,
    #     )
