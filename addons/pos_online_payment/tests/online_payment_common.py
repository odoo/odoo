# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo.tools import mute_logger
from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.addons.pos_online_payment.controllers.payment_portal import PaymentPortal


class OnlinePaymentCommon(PaymentHttpCommon):

    def _fake_http_get_request(self, route):
        url = self._build_url(route)
        response = self._make_http_get_request(url)
        self.assertEqual(response.status_code, 200)
        return response

    def _fake_open_pos_order_pay_page(self, pos_order_id, access_token):
        response = self._fake_http_get_request(PaymentPortal._get_pay_route(pos_order_id, access_token))
        return self._get_payment_context(response)

    def _fake_request_pos_order_pay_transaction_page(self, pos_order_id, route_values):
        uri = f'/pos/pay/transaction/{pos_order_id}'
        url = self._build_url(uri)
        return self.make_jsonrpc_request(url, route_values)

    def _fake_open_pos_order_pay_confirmation_page(self, pos_order_id, access_token, tx_id, exit_route=None):
        self._fake_http_get_request(PaymentPortal._get_landing_route(pos_order_id, access_token, tx_id=tx_id, exit_route=exit_route))

    def _fake_online_payment(self, pos_order_id, access_token, expected_payment_provider_id, exit_route=None):
        payment_context = self._fake_open_pos_order_pay_page(pos_order_id, access_token)

        # Code inspired by addons/payment/tests/test_flows.py
        # Route values are taken from payment_context result of /pay route to correctly simulate the flow
        route_values = {
            k: payment_context[k]
            for k in [
                'amount',
                'access_token',
                'landing_route',
            ]
        }
        route_values.update({
            'provider_id': self.provider.id,
            'payment_method_id': self.payment_method_id,
            'token_id': None,
            'flow': 'direct',
            'tokenization_requested': False,
        })

        with mute_logger('odoo.addons.payment.models.payment_transaction'):
            processing_values = self._fake_request_pos_order_pay_transaction_page(pos_order_id, route_values)
        tx_sudo = self._get_tx(processing_values['reference'])
        tx_sudo._set_done()
        self._fake_open_pos_order_pay_confirmation_page(pos_order_id, access_token, tx_sudo.id, exit_route=exit_route)
