# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
from uuid import uuid4

from lxml import etree, objectify

from odoo import http
from odoo.tests import HttpCase

from odoo.addons.payment.tests.utils import PaymentTestUtils


class PaymentHttpCommon(PaymentTestUtils, HttpCase):
    """ HttpCase common to build and simulate requests going through payment controllers.

    Only use if you effectively want to test controllers.
    If you only want to test 'models' code, the PaymentCommon should be sufficient.

    Note: This Common is expected to be used in parallel with the main PaymentCommon.
    """

    # Helpers #
    ###########

    def _build_jsonrpc_payload(self, params):
        """Helper to properly build jsonrpc payload"""
        if not getattr(self, 'session', None):
            # We need to create a session (public if no login & passwd)
            # before generating a csrf token
            self.authenticate('', '')
        params['csrf_token'] = http.WebRequest.csrf_token(self)
        return {
            "jsonrpc": "2.0",
            "method": "call",
            "id": str(uuid4()),
            "params": params,
        }

    def _make_http_get_request(self, url, params):
        formatted_data = dict()
        for k, v in params.items():
            if isinstance(v, float):
                formatted_data[k] = str(v)
            else:
                formatted_data[k] = v
        return self.opener.get(url, params=formatted_data)

    def _make_json_request(self, url, params):
        data = self._build_jsonrpc_payload(params)
        return self.opener.post(url, json=data)

    def _get_tx_context(self, response, form_name):
        """Extracts txContext & other form info (acquirer & token ids)
        from a payment response (with manage/checkout html form)

        :param response: http Response, with a payment form as text
        :param str form_name: o_payment_manage / o_payment_checkout
        :return: Transaction context (+ acquirer_ids & token_ids)
        :rtype: dict
        """
        # Need to specify an HTML parser as parser
        # Otherwise void elements (<img>, <link> without a closing / tag)
        # are considered wrong and trigger a lxml.etree.XMLSyntaxError
        html_tree = objectify.fromstring(
            response.text,
            parser=etree.HTMLParser(),
        )
        checkout_form = html_tree.xpath(f"//form[@name='{form_name}']")[0]
        values = {}
        for key, val in checkout_form.items():
            if key.startswith("data-"):
                formatted_key = key[5:].replace('-', '_')
                if formatted_key.endswith('_id'):
                    formatted_val = int(val)
                elif formatted_key == 'amount':
                    formatted_val = float(val)
                else:
                    formatted_val = val
                values[formatted_key] = formatted_val

        payment_options_inputs = html_tree.xpath("//input[@name='o_payment_radio']")
        acquirer_ids = []
        token_ids = []
        for p_o_input in payment_options_inputs:
            data = dict()
            for key, val in p_o_input.items():
                if key.startswith('data-'):
                    data[key[5:]] = val
            if data['payment-option-type'] == 'acquirer':
                acquirer_ids.append(int(data['payment-option-id']))
            else:
                token_ids.append(int(data['payment-option-id']))

        values.update({
            'acquirer_ids': acquirer_ids,
            'token_ids': token_ids,
        })

        return values

    # payment/pay #
    ###############

    def _prepare_pay_values(self, amount=0.0, currency=None, reference='', partner=None):
        """Prepare basic payment/pay route values

        NOTE: needs PaymentCommon to enable fallback values.

        :rtype: dict
        """
        amount = amount or self.amount
        currency = currency or self.currency
        reference = reference or self.reference
        partner = partner or self.partner
        return {
            'amount': amount,
            'currency_id': currency.id,
            'reference': reference,
            'partner_id': partner.id,
            'access_token': self._generate_test_access_token(partner.id, amount, currency.id),
        }

    def portal_pay(self, **route_kwargs):
        """/payment/pay txContext feedback

        NOTE: must be authenticated before calling method.
        Or an access_token should be specified in route_kwargs
        """
        uri = '/payment/pay'
        url = self._build_url(uri)
        return self._make_http_get_request(url, route_kwargs)

    def get_tx_checkout_context(self, **route_kwargs):
        response = self.portal_pay(**route_kwargs)

        self.assertEqual(response.status_code, 200)

        return self._get_tx_context(response, 'o_payment_checkout')

    # /my/payment_method #
    ######################

    def portal_payment_method(self):
        """/my/payment_method txContext feedback

        NOTE: must be authenticated before calling method
            validation flow is restricted to logged users
        """
        uri = '/my/payment_method'
        url = self._build_url(uri)
        return self._make_http_get_request(url, {})

    def get_tx_manage_context(self, **route_kwargs):
        response = self.portal_payment_method(**route_kwargs)

        self.assertEqual(response.status_code, 200)

        return self._get_tx_context(response, 'o_payment_manage')

    # payment/transaction #
    #######################
    def portal_transaction(self, **route_kwargs):
        """/payment/transaction feedback

        :return: The response to the json request
        """
        uri = '/payment/transaction'
        url = self._build_url(uri)
        response = self._make_json_request(url, route_kwargs)
        self.assertEqual(response.status_code, 200)  # Check the request went through.

        return response

    def get_processing_values(self, **route_kwargs):
        response = self.portal_transaction(**route_kwargs)

        self.assertEqual(response.status_code, 200)

        resp_content = json.loads(response.content)
        return resp_content['result']
