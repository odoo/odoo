# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests
from odoo import Command
from odoo.addons.pos_self_order.tests.self_order_common_test import SelfOrderCommonTest
from odoo.addons.pos_online_payment.tests.online_payment_common import OnlinePaymentCommon


@odoo.tests.tagged("post_install", "-at_install")
class TestSelfOrderOnlinePaymentMethod(SelfOrderCommonTest, OnlinePaymentCommon):
    def setUp(self):
        super().setUp()
        self.online_payment_method = self.env["pos.payment.method"].create({
            "name": "Online",
            "journal_id": self.bank_journal.id,
            "is_online_payment": True,
            "online_payment_provider_ids": [Command.set([self.dummy_provider.id])],
        })

        self.pos_config.write(
            {
                "self_order_online_payment_method_id": self.online_payment_method.id,
                "payment_method_ids": [Command.set([self.online_payment_method.id])],
            }
        )

    def test_self_order_kiosk_loads_online_payment_method(self):
        self.pos_config.write({"self_ordering_mode": "kiosk"})

        payment_methods_to_load = self.pos_config.payment_method_ids._load_pos_self_data_search_read({}, self.pos_config)

        self.assertEqual(len(payment_methods_to_load), 1)
        self.assertEqual(payment_methods_to_load[0]["id"], self.online_payment_method.id)
        self.assertTrue(self.pos_config.has_valid_self_payment_method())

    def test_self_order_mobile_loads_online_payment_method_from_config(self):
        self.pos_config.write({
            "self_ordering_mode": "mobile",
            "payment_method_ids": [Command.set([])],
        })

        payment_methods_to_load = self.pos_config.payment_method_ids._load_pos_self_data_search_read({}, self.pos_config)

        self.assertEqual(len(payment_methods_to_load), 1)
        self.assertEqual(payment_methods_to_load[0]["id"], self.online_payment_method.id)
        self.assertTrue(self.pos_config.has_valid_self_payment_method())

    def test_self_order_kiosk_does_not_load_online_payment_method_from_config(self):
        self.pos_config.write({
            "self_ordering_mode": "kiosk",
            "payment_method_ids": [Command.set([])],
        })

        payment_methods_to_load = self.pos_config.payment_method_ids._load_pos_self_data_search_read({}, self.pos_config)

        self.assertEqual(len(payment_methods_to_load), 0)
        self.assertFalse(self.pos_config.has_valid_self_payment_method())
