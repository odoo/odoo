# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests
from odoo.addons.pos_self_order.tests.self_order_common_test import SelfOrderCommonTest
from odoo import Command


@odoo.tests.tagged("post_install", "-at_install")
class TestSelfOrderKiosk(SelfOrderCommonTest):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.pos_config.write({
            'self_ordering_mode': 'kiosk',
        })

    def test_self_order_kiosk(self):
        self.pos_config.write({
            'self_ordering_pay_after': 'each',
            'self_ordering_service_mode': 'table',
        })
        self.setup_test_self_presets()
        self.pos_config.with_user(self.pos_user).open_ui()
        self.pos_config.current_session_id.set_opening_control(0, "")

        self.letter_tray.write({
            'list_price': 10,
            'taxes_id': [(6, 0, [self.account_tax_10_incl.id])],
        })
        self.desk_organizer.write({
            'list_price': 10,
            'taxes_id': [Command.set([self.account_tax_10_incl.id, self.tax10.id])],
        })
        self.desk_pad.default_code = '12345'

        # With preset location choices
        self.start_pos_self_tour("self_kiosk_each_counter_takeaway_in")
        self.start_pos_self_tour("self_kiosk_each_counter_takeaway_out")

        self.pos_config.write({
            'available_preset_ids': [(5, 0)],
        })

        # Without location choices, since we need preset to do so.
        self.start_pos_self_tour("self_kiosk_each_table_takeaway_in")
        self.pos_config.write({
            'self_ordering_service_mode': 'counter',
        })
        self.pos_config.default_preset_id.service_at = 'counter'
        self.start_pos_self_tour("self_kiosk_each_table_takeaway_out")

        # Cancel behavior
        self.start_pos_self_tour("self_order_kiosk_cancel")

    def test_duplicate_order_kiosk(self):
        self.pos_config.with_user(self.pos_user).open_ui()
        self.pos_config.current_session_id.set_opening_control(0, "")
        self.start_pos_self_tour("kiosk_simple_order")
        orders = self.env['pos.order'].search(['&', ('state', '=', 'draft'), '|', ('config_id', '=', self.pos_config.id), ('config_id', 'in', self.pos_config.trusted_config_ids.ids)])
        self.assertEqual(len(orders), 1)

    def test_order_price_null(self):
        self.desk_organizer.write({'list_price': 0})
        self.pos_config.with_user(self.pos_user).open_ui()
        self.pos_config.current_session_id.set_opening_control(0, "")
        self.start_pos_self_tour("kiosk_order_price_null")

    def test_self_order_language_changes(self):
        self.env['res.lang']._activate_lang('fr_FR')
        self.desk_organizer.with_context(lang='fr_FR').name = "Organisateur de bureau"

        self.pos_config.write({
            'self_ordering_available_language_ids': [Command.link(lang.id) for lang in self.env['res.lang'].search([])],
        })
        link = self.env['pos_self_order.custom_link'].search(
            [('pos_config_ids', '=', self.pos_config.id), ('name', '=', 'Order Now')]
        )
        link.with_context(lang='fr_FR').name = "Commander maintenant"

        self.pos_config.with_user(self.pos_user).open_ui()
        self.pos_config.current_session_id.set_opening_control(0, "")
        self.start_pos_self_tour('self_order_language_changes')
