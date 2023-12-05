# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests
from odoo.addons.pos_self_order.tests.self_order_common_test import SelfOrderCommonTest


@odoo.tests.tagged("post_install", "-at_install")
<<<<<<< HEAD
class TestFrontendMobile(SelfOrderCommonTest):
||||||| parent of f9bf63941758 (temp)
class TestFrontend(odoo.tests.HttpCase):
    def setUp(self):
        super().setUp()
        self.pos_config = self.env["pos.config"].create(
            {
                "name": "Bar",
                "module_pos_restaurant": True,
                "iface_splitbill": True,
                "iface_printbill": True,
                "iface_orderline_notes": True,
                "start_category": True,
                "self_order_view_mode": True,
            }
        )
        basic_product = {
            "name": "Test Product",
            "type": "product",
            "available_in_pos": True,
            "list_price": 10,
            "taxes_id": False,
        }
        self.env["product.product"].create([basic_product for i in range(1000)])
=======
class TestFrontend(odoo.tests.HttpCase):
    def setUp(self):
        super().setUp()
        self.pos_config = self.env["pos.config"].create(
            {
                "name": "Bar",
                "module_pos_restaurant": True,
                "iface_splitbill": True,
                "iface_printbill": True,
                "iface_orderline_notes": True,
                "start_category": True,
                "self_order_view_mode": True,
            }
        )

        pos_categories = self.env['pos.category'].create([{
            'name': 'Test Tag 1',
        }, {
            'name': 'Test Tag 2',
        }])
        self.env['product.product'].create({
            "name": "Desk Test Product",
            "type": "product",
            "available_in_pos": True,
            "list_price": 10,
            "taxes_id": False,
            'pos_categ_id': pos_categories[0].id,
            'description_sale': 'Test Description',
        })

        basic_product = {
            "name": "Test Product",
            "type": "product",
            "available_in_pos": True,
            "list_price": 10,
            "taxes_id": False,
        }
        self.env["product.product"].create([basic_product for i in range(1000)])
>>>>>>> f9bf63941758 (temp)

    def test_self_order_menu_only_tour(self):
        self.pos_config.self_order_table_mode = False
        self.start_tour(
            self.pos_config._get_self_order_route(),
            "self_order_menu_only_tour",
            login=None,
        )

    def test_self_order_pay_after_meal_tour(self):
        # to test product with attribute no create variant
        product = self.env['product.product'].search([('name', '=', 'Desk Organizer')])[0]
        product.attribute_line_ids[0].product_template_value_ids[0].price_extra = 0.0
        product.attribute_line_ids[0].product_template_value_ids[1].price_extra = 1.0
        product.attribute_line_ids[0].product_template_value_ids[2].price_extra = 2.0
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
