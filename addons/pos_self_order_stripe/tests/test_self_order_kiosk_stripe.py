# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import odoo.tests
from unittest.mock import patch
from odoo.addons.pos_self_order.tests.self_order_common_test import SelfOrderCommonTest
from odoo.tests import Command

@odoo.tests.tagged("post_install", "-at_install")
class TestSelfOrderKioskStripe(SelfOrderCommonTest):

    def setUp(self):
        super().setUp()
        self.pos_config.write({
            'self_ordering_mode': 'kiosk',
            'self_ordering_pay_after': 'each',
            'self_ordering_service_mode': 'table',
        })
        self.stripe = self.env['pos.payment.method'].create({
            'name': 'Stripe',
            'use_payment_terminal': 'stripe',
        })

        self.env['pos.payment.method'].create({
            'name': 'Stripe 2',
            'use_payment_terminal': 'stripe',
        })

        self.pos_config.write({
            'payment_method_ids': [Command.set([self.stripe.id])],
            'access_token': 'access_token',
        })

        self.headers = {
            "Content-Type": "application/json",
        }

    def _build_payload(self, params=None):
        """
        Helper to properly build jsonrpc payload
        """
        return {
            "jsonrpc": "2.0",
            "method": "call",
            "id": 0,
            "params": params or {},
        }

    def test_self_order_kiosk_stripe(self):
        res = self.pos_config.load_self_data()
        pm = res.get('pos.payment.method', [])
        self.assertEqual(len(pm), 1, 'Only one payment method should be loaded')
        self.assertEqual(pm[0]['name'], 'Stripe', 'The loaded payment method should be Stripe')

    def test_get_stripe_creditentials(self):
        """This test make sure the get_stripe_creditentials method does not crash because of `_verify_authorization` method"""
        self.pos_config.open_ui()
        stripe_connection_token = "odoo.addons.pos_stripe.models.pos_payment_method.PosPaymentMethod.stripe_connection_token"
        connection_token = {'object': 'terminal.connection_token', 'secret': 'pst_test_YWNjdF8xUXR003cnRmp4b'}
        with patch(
            stripe_connection_token, return_value=connection_token
        ):
                payload = self._build_payload({'access_token': 'access_token', 'payment_method_id': self.stripe.id})
                response = self.url_open('/pos-self-order/stripe-connection-token', data=json.dumps(payload), headers=self.headers, timeout=60000)
                json_response = json.loads(response.text)
                self.assertTrue(json_response.get('result').get('object'), 'terminal.connection_token')

    def test_stripe_capture_payment(self):
        """This test make sure the stripe_capture_payment method does not crash because of `_verify_authorization` method"""
        self.pos_config.access_token = 'access_token'
        self.pos_config.open_ui()
        stripe_capture_payment = "odoo.addons.pos_stripe.models.pos_payment_method.PosPaymentMethod.stripe_capture_payment"
        order = self.env['pos.order'].create({
            'company_id': self.env.company.id,
            'session_id': self.pos_config.current_session_id.id,
            'lines': [Command.create({
                'product_id': self.fanta.id,
                'price_unit': 10,
                'discount': 0,
                'qty': 1,
                'price_subtotal': 10,
                'price_subtotal_incl': 10,
            })],
            'amount_paid': 10.0,
            'amount_total': 10.0,
            'amount_tax': 0.0,
            'amount_return': 0.0,
            'to_invoice': True,
            'last_order_preparation_change': '{}',
            'access_token': 'order_access',
        })
        with patch(
                stripe_capture_payment, return_value={'id': '1', 'status': 'succeeded', 'amount': 1000}
            ):
                payload = self._build_payload({'access_token': 'access_token', 'order_access_token': 'order_access', 'payment_intent_id': '1', 'payment_method_id': self.stripe.id})
                self.url_open('/pos-self-order/stripe-capture-payment', data=json.dumps(payload), headers=self.headers, timeout=60000)
                self.assertTrue(order.state == 'paid', 'The order should be paid')

    def test_kiosk_without_payment_terminal(self):
        """ Verify that kiosk should not ask for payment when valid payment method is not configured. """
        invalid_pm = self.bank_payment_method  # 'Bank' is not a valid payment method for kiosk mode
        self.pos_config.write({
            'self_ordering_mode': 'kiosk',
            'self_ordering_service_mode': 'counter',
            'use_presets': False,
            'payment_method_ids': [(6, 0, invalid_pm.ids)],
        })
        self.pos_config.with_user(self.pos_user).open_ui()
        self.pos_config.current_session_id.set_opening_control(0, "")
        self_route = self.pos_config._get_self_order_route()
        self.start_tour(self_route, "test_kiosk_without_payment_terminal")

        order = self.pos_config.current_session_id.order_ids[0]
        self.assertEqual(order.state, 'draft', 'The order should be draft')
        self.assertFalse(order.payment_ids, 'No payments should be registered for the order')
