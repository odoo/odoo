# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests
from odoo.addons.pos_self_order.tests.self_order_common_test import SelfOrderCommonTest
from unittest.mock import patch


@odoo.tests.tagged("post_install", "-at_install")
class TestSelfOrderMobile(SelfOrderCommonTest):
    def test_self_order_mobile(self):
        self.pos_config.write({
            'self_ordering_mode': 'mobile',
            'self_ordering_pay_after': 'each',
            'self_ordering_service_mode': 'table',
        })

        floor = self.env["restaurant.floor"].create({
            "name": 'Main Floor',
            "background_color": 'rgb(249,250,251)',
            "table_ids": [(0, 0, {
                "table_number": 1,
            }), (0, 0, {
                "table_number": 2,
            }), (0, 0, {
                "table_number": 3,
            })],
        })

        # Only set one floor to the pos_config, otherwise it can have two table with the same name
        # which will cause the test to fail
        self.pos_config.write({
            "floor_ids": [(6, 0, [floor.id])],
        })

        self.pos_config.with_user(self.pos_user).open_ui()
        self.pos_config.current_session_id.set_opening_control(0, "")
        self_route = self.pos_config._get_self_order_route()

        # Test selection of different presets
        self.start_tour(self_route, "self_mobile_each_table_takeaway_in")
        self.start_tour(self_route, "self_mobile_each_table_takeaway_out")
        orders = self.env['pos.order'].search([], order="id desc", limit=2)
        self.assertEqual(orders[0].preset_id, self.out_preset)
        self.assertEqual(orders[1].preset_id, self.in_preset)

        self.pos_config.write({
            'self_ordering_service_mode': 'counter',
        })

        # Mobile, each, counter
        self.start_tour(self_route, "self_mobile_each_counter_takeaway_in")
        self.start_tour(self_route, "self_mobile_each_counter_takeaway_out")

        self.env['pos.order'].search([('state', '=', 'draft')]).write({'state': 'cancel'})
        self.pos_config.write({
            'self_ordering_pay_after': 'meal',
            'self_ordering_service_mode': 'table',
        })

        # Mobile, meal, table
        self.start_tour(self_route, "self_mobile_meal_table_takeaway_in")
        self.start_tour(self_route, "self_mobile_meal_table_takeaway_out")

        self.env['pos.order'].search([('state', '=', 'draft')]).write({'state': 'cancel'})
        self.pos_config.write({
            'self_ordering_service_mode': 'counter',
        })

        # Mobile, meal, counter
        self.start_tour(self_route, "self_mobile_meal_counter_takeaway_in")
        self.start_tour(self_route, "self_mobile_meal_counter_takeaway_out")

        # Cancel in meal
        self.start_tour(self_route, "self_order_mobile_meal_cancel")

        self.env['pos.order'].search([('state', '=', 'draft')]).write({'state': 'cancel'})
        self.pos_config.write({
            'self_ordering_pay_after': 'each',
        })

        # Cancel in each
        self.start_tour(self_route, "self_order_mobile_each_cancel")

        self.pos_config.write({
            'self_ordering_service_mode': 'table',
        })

        self_route_table = self.pos_config._get_self_order_route(table_id=floor.table_ids[0].id)
        self.start_tour(self_route_table, "self_mobile_auto_table_selection_takeaway_in")

    def test_self_order_category_with_only_special_products(self):
        # A category containing only special products must not be visible
        self.pos_config.write({
            'self_ordering_mode': 'mobile',
            'self_ordering_pay_after': 'each',
            'self_ordering_service_mode': 'table',
        })

        test_categ_misc = self.env['pos.category'].create({
            'name': 'Specials',
        })

        prod1 = self.env['product.product'].create({
            'name': 'Special 1',
            'is_storable': True,
            'list_price': 0,
            'taxes_id': False,
            'available_in_pos': True,
            'pos_categ_ids': [(4, test_categ_misc.id)],
            'default_code': '12345',
        })

        prod2 = self.env['product.product'].create({
            'name': 'Special 2',
            'is_storable': True,
            'list_price': 0,
            'taxes_id': False,
            'available_in_pos': True,
            'pos_categ_ids': [(4, test_categ_misc.id)],
            'default_code': '12345',
        })
        self.pos_config.with_user(self.pos_user).open_ui()
        self.pos_config.current_session_id.set_opening_control(0, "")
        self_route = self.pos_config._get_self_order_route()

        with patch("odoo.addons.point_of_sale.models.pos_config.PosConfig._get_special_products", return_value=prod1 + prod2):
            self.start_tour(self_route, "self_order_mobile_special_products_category")

    def test_self_order_mobile_0_price_order(self):
        self.pos_config.write({
            'self_ordering_mode': 'mobile',
            'self_ordering_pay_after': 'each',
            'self_ordering_service_mode': 'table',
        })

        floor = self.env["restaurant.floor"].create({
            "name": 'Main Floor',
            "background_color": 'rgb(249,250,251)',
            "table_ids": [(0, 0, {
                "table_number": 1,
            }), (0, 0, {
                "table_number": 2,
            }), (0, 0, {
                "table_number": 3,
            })],
        })

        # Only set one floor to the pos_config, otherwise it can have two table with the same name
        # which will cause the test to fail
        self.pos_config.write({
            "floor_ids": [(6, 0, [floor.id])],
        })

        self.pos_config.with_user(self.pos_user).open_ui()
        self.pos_config.current_session_id.set_opening_control(0, "")
        self_route = self.pos_config._get_self_order_route()

        # Zero priced order
        self.start_tour(self_route, "self_order_mobile_0_price_order")

        order = self.env['pos.order'].search([], limit=1)
        self.assertEqual(order.picking_count, 1)

    def test_order_table_assignement(self):
        """
        In pay after meal: table is set via table_id fields
        In pay after each: table is set via floating_order_name eg: Self-Order T1
        """
        self.env['product.product'].search([('name', '=', 'Coca-Cola')]).write({'lst_price': 0})
        self.pos_config.write({
            'use_presets': False,
            'self_ordering_mode': 'mobile',
            'self_ordering_pay_after': 'each',
            'self_ordering_service_mode': 'table',
            'floor_ids': [(5, 0), (0, 0, {
                'name': 'Main Floor',
                'background_color': 'rgb(249,250,251)',
                'table_ids': [(0, 0, {
                    'table_number': 1,
                })],
            })],
        })

        self.pos_config.with_user(self.pos_user).open_ui()
        self.pos_config.current_session_id.set_opening_control(0, "")
        self_route = self.pos_config._get_self_order_route()
        self.start_tour(self_route, "test_order_table_assignement_each")
        last_order = self.env['pos.order'].search([], order="id desc", limit=1)
        self.assertEqual(last_order.table_id.id, False)
        self.assertEqual(last_order.floating_order_name, "Self-Order T 1")

        self.pos_config.write({'self_ordering_pay_after': 'meal'})
        self.start_tour(self_route, "test_order_table_assignement_meal")
        last_order = self.env['pos.order'].search([], order="id desc", limit=1)
        self.assertEqual(last_order.table_id.table_number, 1)
        self.assertNotEqual(last_order.floating_order_name, "Self-Order T 1")

    def test_sub_categories_products_displayed(self):
        miscellaneous = self.env['pos.category'].search([('name', '=', 'Miscellaneous')], limit=1)
        soda = self.env['pos.category'].create({
            'name': 'Soda',
            'parent_id': miscellaneous.id,
            'sequence': 1,
        })
        empty_parent_category = self.env['pos.category'].create({'name': 'Parent'})
        child_category = self.env['pos.category'].create({
            'name': 'Child',
            'parent_id': empty_parent_category.id,
        })
        grand_child_category = self.env['pos.category'].create({
            'name': 'Grandchild',
            'parent_id': child_category.id,
        })

        self.cola.write({'pos_categ_ids': [(6, 0, [soda.id])]})
        self.fanta.write({'pos_categ_ids': [(6, 0, [grand_child_category.id])]})

        # Mobile
        self.pos_config.write({
            'self_ordering_mode': 'mobile',
            'self_ordering_pay_after': 'each',
            'self_ordering_service_mode': 'table',
            'use_presets': False,
            'iface_available_categ_ids': [(6, 0, [miscellaneous.id, soda.id, empty_parent_category.id, child_category.id, grand_child_category.id])],
        })

        self.pos_config.with_user(self.pos_user).open_ui()
        self.pos_config.current_session_id.set_opening_control(0, "")
        self_route = self.pos_config._get_self_order_route()
        self.start_tour(self_route, "test_sub_categories_products_displayed")

        # Consultation
        self.pos_config.current_session_id.action_pos_session_closing_control()
        self.pos_config.write({'self_ordering_mode': 'consultation'})
        self.pos_config.with_user(self.pos_user).open_ui()
        self_route = self.pos_config._get_self_order_route()
        self.start_tour(self_route, "test_sub_categories_products_displayed")

        # Kiosk
        self.pos_config.current_session_id.action_pos_session_closing_control()
        self.pos_config.write({'self_ordering_mode': 'kiosk'})
        self.pos_config.with_user(self.pos_user).open_ui()
        self_route = self.pos_config._get_self_order_route()
        self.start_tour(self_route, "test_sub_categories_products_displayed")

    def test_mobile_self_order_preparation_changes(self):
        self.pos_config.write({
            'self_ordering_mode': 'mobile',
            'self_ordering_pay_after': 'each',
            'self_ordering_service_mode': 'table',
            'use_presets': False,
        })

        self.pos_config.with_user(self.pos_user).open_ui()
        self.pos_config.current_session_id.set_opening_control(0, "")

        # create self-order from mobile
        self.start_tour(self.pos_config._get_self_order_route(), 'test_mobile_self_order_preparation_changes')
        order = self.pos_config.current_session_id.order_ids[0]
        self.assertEqual(order.state, 'draft')
        self.assertEqual(len(order.lines), 2)

        # Check self-order in pos-terminal are not prompted for Send-for-Preparation
        self.start_tour('/pos/ui?config_id=%d' % self.pos_config.id, 'test_pos_self_order_preparation_changes', login='pos_user')
