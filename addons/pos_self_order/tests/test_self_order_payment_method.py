# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests
from odoo import Command
from odoo.addons.pos_self_order.tests.self_order_common_test import SelfOrderCommonTest


@odoo.tests.tagged("post_install", "-at_install")
class TestSelfOrderPaymentMethod(SelfOrderCommonTest):
    def setUp(self):
        super().setUp()
        self.terminal_payment_method = self.env['pos.payment.method'].create({
            'name': 'Terminal',
            'journal_id': self.bank_journal.id,
            'use_payment_terminal': 'stripe',
        })

        self.pos_config.write(
            {
                "payment_method_ids": [Command.link(self.terminal_payment_method.id)],
            }
        )

    def test_self_order_kiosk_loads_terminal_payment_method(self):
        self.pos_config.write({"self_ordering_mode": "kiosk"})

        payment_methods_to_load = self.pos_config.payment_method_ids._load_pos_self_data_search_read({}, self.pos_config)

        self.assertEqual(len(payment_methods_to_load), 1)
        self.assertEqual(payment_methods_to_load[0]["id"], self.terminal_payment_method.id)
        self.assertTrue(self.pos_config.has_valid_self_payment_method())

    def test_self_order_non_kiosk_does_not_load_payment_method(self):
        for ordering_mode in ["mobile", "consultation"]:
            self.pos_config.write({"self_ordering_mode": ordering_mode})

            payment_methods_to_load = self.pos_config.payment_method_ids._load_pos_self_data_search_read({}, self.pos_config)

            self.assertEqual(len(payment_methods_to_load), 0)
            self.assertFalse(self.pos_config.has_valid_self_payment_method())
