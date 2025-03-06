# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests
from odoo.addons.pos_self_order.tests.self_order_common_test import SelfOrderCommonTest
from odoo import Command


@odoo.tests.tagged("post_install", "-at_install")
class TestSelfOrderKiosk(SelfOrderCommonTest):
    def test_self_order_kiosk(self):
        self_route = self.pos_config._get_self_order_route()
        self.pos_config.write({
            'self_ordering_mode': 'kiosk',
            'self_ordering_pay_after': 'each',
            'self_ordering_service_mode': 'table',
        })
        self.pos_config.with_user(self.pos_user).open_ui()
        self.pos_config.current_session_id.set_opening_control(0, "")

        tax_10_inc = self.env['account.tax'].create({
            "name": "10% incl",
            "amount": 10,
            "amount_type": "percent",
            "type_tax_use": "sale",
            "price_include_override": "tax_included",
            "include_base_amount": True,
        })

        tax_10_excl = self.env['account.tax'].create({
            "name": "10% excl",
            "amount": 10,
            "amount_type": "percent",
            "type_tax_use": "sale",
        })

        self.env['product.product'].create({
            'name': 'Yummy Burger',
            'available_in_pos': True,
            'list_price': 10,
            'taxes_id': [Command.set([tax_10_inc.id])],
        })

        self.env['product.product'].create({
            'name': 'Taxi Burger',
            'available_in_pos': True,
            'list_price': 10,
            'taxes_id': [Command.set([tax_10_inc.id, tax_10_excl.id])],
        })

        # With preset location choices
        self.start_tour(self_route, "self_kiosk_each_counter_takeaway_in")
        self.start_tour(self_route, "self_kiosk_each_counter_takeaway_out")

        self.pos_config.write({
            'available_preset_ids': [(5, 0)],
        })

        # Without location choices, since we need preset to do so.
        self.start_tour(self_route, "self_kiosk_each_table_takeaway_in")
        self.pos_config.write({
            'self_ordering_service_mode': 'counter',
        })
        self.pos_config.default_preset_id.service_at = 'counter'
        self.start_tour(self_route, "self_kiosk_each_table_takeaway_out")

        # Cancel behavior
        self.start_tour(self_route, "self_order_kiosk_cancel")

    def test_duplicate_order_kiosk(self):
        self.pos_config.write({
            'use_presets': False,
            'default_preset_id': False,
            'available_preset_ids': [(5, 0)],
            'self_ordering_mode': 'kiosk',
            'self_ordering_pay_after': 'each',
            'self_ordering_service_mode': 'counter',
        })
        self.pos_config.with_user(self.pos_user).open_ui()
        self.pos_config.current_session_id.set_opening_control(0, "")
        self_route = self.pos_config._get_self_order_route()
        self.start_tour(self_route, "self_simple_order")
        orders = self.env['pos.order'].search(['&', ('state', '=', 'draft'), '|', ('config_id', '=', self.pos_config.id), ('config_id', 'in', self.pos_config.trusted_config_ids.ids)])
        self.assertEqual(len(orders), 1)

    def test_order_price_null(self):
        self.cola.list_price = 0.00
        self.pos_config.write({
            'use_presets': False,
            'default_preset_id': False,
            'available_preset_ids': [(5, 0)],
            'self_ordering_mode': 'kiosk',
            'self_ordering_pay_after': 'each',
        })

        self.pos_config.with_user(self.pos_user).open_ui()
        self.pos_config.current_session_id.set_opening_control(0, "")
        self_route = self.pos_config._get_self_order_route()
        self.start_tour(self_route, "self_order_price_null")

    def test_self_order_language_changes(self):
        self.env['res.lang']._activate_lang('fr_FR')
        self.pos_config.write({
            'self_ordering_available_language_ids': [Command.link(lang.id) for lang in self.env['res.lang'].search([])],
            'available_preset_ids': [(5, 0)],
            'self_ordering_mode': 'kiosk',
            'self_ordering_pay_after': 'each'
        })

        self.pos_config.with_user(self.pos_user).open_ui()
        self_route = self.pos_config._get_self_order_route()
        self.start_tour(self_route, "self_order_language_changes")

    def test_self_order_kiosk_combo_sides(self):
        combo = self.env["product.combo"].create(
            {
                "name": "Desk Accessories Combo",
                "combo_item_ids": [
                    Command.create({
                        "product_id": self.desk_organizer.id,
                        "extra_price": 0,
                    }),
                ],
            }
        )
        self.env["product.product"].create(
            {
                "available_in_pos": True,
                "list_price": 40,
                "name": "Office Combo",
                "type": "combo",
                "combo_ids": [
                    (6, 0, [combo.id])
                ],
            }
        )
        self.pos_config.write({
            'self_ordering_mode': 'kiosk',
            'self_ordering_pay_after': 'each',
            'self_ordering_service_mode': 'table',
        })
        self.pos_config.with_user(self.pos_user).open_ui()
        self.pos_config.current_session_id.set_opening_control(0, "")
        self_route = self.pos_config._get_self_order_route()
        self.start_tour(self_route, "test_self_order_kiosk_combo_sides")
