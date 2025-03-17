# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests
from odoo.addons.pos_self_order.tests.self_order_common_test import SelfOrderCommonTest
from odoo.tests import Command

@odoo.tests.tagged("post_install", "-at_install")
class TestSelfOrderKioskStripe(SelfOrderCommonTest):
    def test_self_order_kiosk_stripe(self):
        self.pos_config.write({
            'takeaway': True,
            'self_ordering_takeaway': True,
            'self_ordering_mode': 'kiosk',
            'self_ordering_pay_after': 'each',
            'self_ordering_service_mode': 'table',
        })
        stripe = self.env['pos.payment.method'].create({
            'name': 'Stripe',
            'use_payment_terminal': 'stripe',
        })

        self.env['pos.payment.method'].create({
            'name': 'Stripe 2',
            'use_payment_terminal': 'stripe',
        })

        self.pos_config.write({
            'payment_method_ids': [Command.set([stripe.id])]
        })

        res = self.pos_config.load_self_data()
        self.assertEqual(len(res['pos.payment.method']['data']), 1, 'Only one payment method should be loaded')
        self.assertEqual(res['pos.payment.method']['data'][0]['name'], 'Stripe', 'The loaded payment method should be Stripe')
