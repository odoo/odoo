# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests
from odoo.addons.pos_self_order.tests.self_order_common_test import SelfOrderCommonTest
from odoo import Command


@odoo.tests.tagged("post_install", "-at_install")
class TestSelfOrderKiosk(SelfOrderCommonTest):
    def test_self_order_kiosk(self):
        self.pos_config.write({
            'takeaway': True,
            'self_ordering_takeaway': True,
            'self_ordering_mode': 'kiosk',
            'self_ordering_pay_after': 'each',
            'self_ordering_service_mode': 'table',
        })

        self.pos_config.with_user(self.pos_user).open_ui()
        self.pos_config.current_session_id.set_opening_control(0, "")
        self_route = self.pos_config._get_self_order_route()

        # Kiosk, each, table
        self.start_tour(self_route, "self_kiosk_each_table_takeaway_in", timeout=120)
        self.start_tour(self_route, "self_kiosk_each_table_takeaway_out", timeout=120)

        self.pos_config.write({
            'self_ordering_service_mode': 'counter',
        })

        # Kiosk, each, counter
        self.start_tour(self_route, "self_kiosk_each_counter_takeaway_in", timeout=120)
        self.start_tour(self_route, "self_kiosk_each_counter_takeaway_out", timeout=120)

        # Cancel behavior
        self.start_tour(self_route, "self_order_kiosk_cancel")

    def test_duplicate_order_kiosk(self):
        self.pos_config.write({
            'self_ordering_takeaway': False,
            'self_ordering_mode': 'kiosk',
            'self_ordering_pay_after': 'each',
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
            'self_ordering_takeaway': False,
            'self_ordering_mode': 'kiosk',
            'self_ordering_pay_after': 'each',
        })

        self.pos_config.with_user(self.pos_user).open_ui()
        self.pos_config.current_session_id.set_opening_control(0, "")
        self_route = self.pos_config._get_self_order_route()
        self.start_tour(self_route, "self_order_price_null")

    def test_self_order_language_changes(self):
        self.env['res.lang']._activate_lang('fr_FR')

        product = self.env['product.product'].create({
            'name': "Test Product",
            'list_price': 100,
            'taxes_id': False,
            'available_in_pos': True,
        })
        product.with_context(lang='fr_FR').name = "Produit Test"

        self.pos_config.write({
            'self_ordering_available_language_ids': [Command.link(lang.id) for lang in self.env['res.lang'].search([])],
            'self_ordering_takeaway': False,
            'self_ordering_mode': 'kiosk',
            'self_ordering_pay_after': 'each'
        })

        link = self.env['pos_self_order.custom_link'].search(
            [('pos_config_ids', '=', self.pos_config.id), ('name', '=', 'Order Now')]
        )
        link.with_context(lang='fr_FR').name = "Commander maintenant"

        self.pos_config.with_user(self.pos_user).open_ui()
        self.pos_config.current_session_id.set_opening_control(0, "")
        self_route = self.pos_config._get_self_order_route()
        self.start_tour(self_route, 'self_order_language_changes')

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
            'takeaway': False,
            'self_ordering_takeaway': False,
            'self_ordering_mode': 'kiosk',
            'self_ordering_pay_after': 'each',
        })
        self.pos_config.with_user(self.pos_user).open_ui()
        self.pos_config.current_session_id.set_opening_control(0, "")
        self_route = self.pos_config._get_self_order_route()
        self.start_tour(self_route, "test_self_order_kiosk_combo_sides")

    def test_self_order_pricelist(self):
        # ignore pre-existing pricelists for the purpose of this test
        self.env['product.pricelist'].search([]).write({'active': False})
        pricelist = self.env['product.pricelist'].create({
            'name': "Test pricelist",
            'company_id': self.env.company.id,
            'item_ids': [
                Command.create({
                    'compute_price': 'fixed',
                    'fixed_price': 1,
                    'min_quantity': 3,
                    'applied_on': '1_product',
                    'product_tmpl_id': self.cola.product_tmpl_id.id,
                })
            ],
        })

        self.pos_config.write({
            'takeaway': False,
            'self_ordering_takeaway': False,
            'self_ordering_mode': 'kiosk',
            'self_ordering_pay_after': 'each',
            'available_pricelist_ids': [Command.set(pricelist.ids)],
            'pricelist_id': pricelist.id,
        })

        self.pos_config.with_user(self.pos_user).open_ui()
        self.pos_config.current_session_id.set_opening_control(0, "")
        self_route = self.pos_config._get_self_order_route()
        self.start_tour(self_route, 'self_order_pricelist')
