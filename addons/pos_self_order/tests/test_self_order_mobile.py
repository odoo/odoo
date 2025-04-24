# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests
from odoo.addons.pos_self_order.tests.self_order_common_test import SelfOrderCommonTest


@odoo.tests.tagged("post_install", "-at_install")
class TestSelfOrderMobile(SelfOrderCommonTest):
    def test_self_order_mobile(self):
        self.setup_test_self_presets()
        self.pos_config.write({
            'self_ordering_mode': 'mobile',
            'self_ordering_pay_after': 'each',
            'self_ordering_service_mode': 'table',
        })

        self.setup_self_floor_and_table()

        self.pos_config.with_user(self.pos_user).open_ui()
        self.pos_config.current_session_id.set_opening_control(0, "")

        # Test selection of different presets
        self.start_pos_self_tour("self_mobile_each_table_takeaway_in")
        self.start_pos_self_tour("self_mobile_each_table_takeaway_out")
        orders = self.env['pos.order'].search([], order="id desc", limit=2)
        self.assertEqual(orders[0].preset_id, self.out_preset)
        self.assertEqual(orders[1].preset_id, self.in_preset)

        self.pos_config.write({
            'self_ordering_service_mode': 'counter',
        })

        # Mobile, each, counter
        self.start_pos_self_tour("self_mobile_each_counter_takeaway_in")
        self.start_pos_self_tour("self_mobile_each_counter_takeaway_out")

        self.env['pos.order'].search([]).write({'state': 'cancel'})
        self.pos_config.write({
            'self_ordering_pay_after': 'meal',
            'self_ordering_service_mode': 'table',
        })

        # Mobile, meal, table
        self.start_pos_self_tour("self_mobile_meal_table_takeaway_in")
        self.start_pos_self_tour("self_mobile_meal_table_takeaway_out")

        self.env['pos.order'].search([]).write({'state': 'cancel'})
        self.pos_config.write({
            'self_ordering_service_mode': 'counter',
        })

        # Mobile, meal, counter
        self.start_pos_self_tour("self_mobile_meal_counter_takeaway_in")
        self.start_pos_self_tour("self_mobile_meal_counter_takeaway_out")

        # Cancel in meal
        self.start_pos_self_tour("self_order_mobile_meal_cancel")

        self.env['pos.order'].search([]).write({'state': 'cancel'})
        self.pos_config.write({
            'self_ordering_pay_after': 'each',
        })

        # Cancel in each
        self.start_pos_self_tour("self_order_mobile_each_cancel")
