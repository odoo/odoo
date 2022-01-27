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

    def _make_http_get_request(self, url, params=None):
        """ Make an HTTP GET request to the provided URL.

        :param str url: The URL to make the request to
        :param dict params: The parameters to be sent in the query string
        :return: The response of the request
        :rtype: :class:`requests.models.Response`
        """
        formatted_params = self._format_http_request_payload(payload=params)
        return self.opener.get(url, params=formatted_params)

    def _make_http_post_request(self, url, data=None):
        """ Make an HTTP POST request to the provided URL.

        :param str url: The URL to make the request to
        :param dict data: The data to be send in the request body
        :return: The response of the request
        :rtype: :class:`requests.models.Response`
        """
        formatted_data = self._format_http_request_payload(payload=data)
        return self.opener.post(url, data=formatted_data)

    def _format_http_request_payload(self, payload=None):
        """ Format a request payload to replace float values by their string representation.

        :param dict payload: The payload to format
        :return: The formatted payload
        :rtype: dict
        """
        formatted_payload = {}
        if payload is not None:
            for k, v in payload.items():
                formatted_payload[k] = str(v) if isinstance(v, float) else v
        return formatted_payload

    def _make_json_request(self, url, data=None):
        """ Make a JSON request to the provided URL.

        :param str url: The URL to make the request to
        :param dict data: The data to be send in the request body in JSON format
        :return: The response of the request
        :rtype: :class:`requests.models.Response`
        """
        data = self._ensure_csrf_token(payload=data)
        return self.opener.post(url, json=data)

    def _make_json_rpc_request(self, url, data=None):
        """ Make a JSON-RPC request to the provided URL.

        :param str url: The URL to make the request to
        :param dict data: The data to be send in the request body in JSON-RPC 2.0 format
        :return: The response of the request
        :rtype: :class:`requests.models.Response`
        """
        def _build_jsonrpc_payload(_data):
            return {
                'jsonrpc': '2.0',
                'method': 'call',
                'id': str(uuid4()),
                'params': _data,
            }

        data = self._ensure_csrf_token(payload=data)
        return self.opener.post(url, json=_build_jsonrpc_payload(data))

    def _ensure_csrf_token(self, payload=None):
        """ Check if a CSRF token is needed in the request payload and add one if so.

        :param dict payload: The payload of the request
        :return: The payload with a CSRF token
        :rtype: dict
        """
        payload = {} if payload is None else payload
        if not getattr(self, 'session', None):  # A CSRF token is required
            self.authenticate('', '')  # Create a session first
        payload['csrf_token'] = http.WebRequest.csrf_token(self)
        return payload

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

    def get_tx_manage_context(self):
        response = self.portal_payment_method()

        self.assertEqual(response.status_code, 200)

        return self._get_tx_context(response, 'o_payment_manage')

    # payment/transaction #
    #######################
    def portal_transaction(self, **route_kwargs):
        """/payment/transaction feedback

        :returns: processing values for given route_kwargs
        :rtype: dict
        """
        uri = '/payment/transaction'
        url = self._build_url(uri)

        return self._make_json_rpc_request(url, route_kwargs)

    def get_processing_values(self, **route_kwargs):
        response = self.portal_transaction(**route_kwargs)

        self.assertEqual(response.status_code, 200)

        resp_content = json.loads(response.content)
        return resp_content['result']
