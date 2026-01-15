# Part of Odoo. See LICENSE file for full copyright and licensing details.

from contextlib import contextmanager

from lxml import etree, objectify

from odoo.tests import HttpCase, JsonRpcException
from odoo.tools import urls

from odoo.addons.payment.tests.common import PaymentCommon


class PaymentHttpCommon(PaymentCommon, HttpCase):
    """ HttpCase common to build and simulate requests going through payment controllers.

    Only use if you effectively want to test controllers.
    If you only want to test 'models' code, the PaymentCommon should be sufficient.
    """

    # Helpers #
    ###########

    def _build_url(self, route):
        return urls.urljoin(self.base_url(), route)

    def _make_http_get_request(self, url, params=None):
        """ Make an HTTP GET request to the provided URL.

        :param str url: The URL to make the request to
        :param dict params: The parameters to be sent in the query string
        :return: The response of the request
        :rtype: :class:`requests.models.Response`
        """
        formatted_params = self._format_http_request_payload(payload=params)
        return self.url_open(url, params=formatted_params)

    def _make_http_post_request(self, url, data=None):
        """ Make an HTTP POST request to the provided URL.

        :param str url: The URL to make the request to
        :param dict data: The data to be send in the request body
        :return: The response of the request
        :rtype: :class:`requests.models.Response`
        """
        formatted_data = self._format_http_request_payload(payload=data)
        return self.url_open(url, data=formatted_data, method='POST')

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
        return self.url_open(url, json=data)

    @contextmanager
    def _assertNotFound(self):
        with self.assertRaises(JsonRpcException) as cm:
            yield
        self.assertEqual(cm.exception.code, 404)

    def _get_payment_context(self, response):
        """Extracts the payment context & other form info (provider & token ids)
        from a payment response

        :param response: http Response, with a payment form as text
        :return: Transaction context (+ provider_ids & token_ids)
        :rtype: dict
        """
        # Need to specify an HTML parser as parser
        # Otherwise void elements (<img>, <link> without a closing / tag)
        # are considered wrong and trigger a lxml.etree.XMLSyntaxError
        html_tree = objectify.fromstring(
            response.text,
            parser=etree.HTMLParser(),
        )
        payment_form = html_tree.xpath('//form[@id="o_payment_form"]')[0]
        values = {}
        for key, val in payment_form.items():
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
        token_ids = []
        payment_method_ids = []
        for p_o_input in payment_options_inputs:
            data = dict()
            for key, val in p_o_input.items():
                if key.startswith('data-'):
                    data[key[5:]] = val
            if data['payment-option-type'] == 'token':
                token_ids.append(int(data['payment-option-id']))
            else:  # 'payment_method'
                payment_method_ids.append(int(data['payment-option-id']))

        values.update({
            'token_ids': token_ids,
            'payment_method_ids': payment_method_ids,
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

    def _portal_pay(self, **route_kwargs):
        """/payment/pay payment context feedback

        NOTE: must be authenticated before calling method.
        Or an access_token should be specified in route_kwargs
        """
        uri = '/payment/pay'
        url = self._build_url(uri)
        return self._make_http_get_request(url, route_kwargs)

    def _get_portal_pay_context(self, **route_kwargs):
        response = self._portal_pay(**route_kwargs)

        self.assertEqual(response.status_code, 200)

        return self._get_payment_context(response)

    # /my/payment_method #
    ######################

    def _portal_payment_method(self):
        """/my/payment_method payment context feedback

        NOTE: must be authenticated before calling method
            validation flow is restricted to logged users
        """
        uri = '/my/payment_method'
        url = self._build_url(uri)
        return self._make_http_get_request(url, {})

    def _get_portal_payment_method_context(self):
        response = self._portal_payment_method()

        self.assertEqual(response.status_code, 200)

        return self._get_payment_context(response)

    # payment/transaction #
    #######################

    def _prepare_transaction_values(self, payment_method_id, token_id, flow):
        """ Prepare the basic payment/transaction route values.

        :param int payment_option_id: The payment option handling the transaction, as a
                                      `payment.method` id or a `payment.token` id
        :param str flow: The payment flow
        :return: The route values
        :rtype: dict
        """
        return {
            'provider_id': self.provider.id,
            'payment_method_id': payment_method_id,
            'token_id': token_id,
            'amount': self.amount,
            'currency_id': self.currency.id,
            'partner_id': self.partner.id,
            'access_token': self._generate_test_access_token(
                self.partner.id, self.amount, self.currency.id
            ),
            'tokenization_requested': True,
            'landing_route': 'Test',
            'reference_prefix': 'test',
            'is_validation': False,
            'flow': flow,
        }

    def _portal_transaction(self, tx_route='/payment/transaction', **route_kwargs):
        """/payment/transaction feedback

        :return: The response to the json request
        """
        url = self._build_url(tx_route)
        return self.make_jsonrpc_request(url, route_kwargs)

    def _get_processing_values(self, **route_kwargs):
        return self._portal_transaction(**route_kwargs)
