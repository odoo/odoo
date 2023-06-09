# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import re
import json
import requests

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from odoo.addons.payment_adyen import const

_logger = logging.getLogger(__name__)


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(
        selection_add=[('adyen', "Adyen")], ondelete={'adyen': 'set default'})
    adyen_merchant_account = fields.Char(
        string="Merchant Account",
        help="The code of the merchant account to use with this provider",
        required_if_provider='adyen', groups='base.group_system')
    adyen_api_key = fields.Char(
        string="API Key", help="The API key of the webservice user", required_if_provider='adyen',
        groups='base.group_system')
    adyen_client_key = fields.Char(
        string="Client Key", help="The client key of the webservice user",
        required_if_provider='adyen')
    adyen_hmac_key = fields.Char(
        string="HMAC Key", help="The HMAC key of the webhook", required_if_provider='adyen',
        groups='base.group_system')
    adyen_api_url_prefix = fields.Char(
        string="API URL Prefix",
        help="The base URL for the API endpoints",
        required_if_provider='adyen',
    )

    #=== CRUD METHODS ===#

    @api.model_create_multi
    def create(self, values_list):
        for values in values_list:
            self._adyen_extract_prefix_from_api_url(values)
        return super().create(values_list)

    def write(self, values):
        self._adyen_extract_prefix_from_api_url(values)
        return super().write(values)

    @api.model
    def _adyen_extract_prefix_from_api_url(self, values):
        """ Update the create or write values with the prefix extracted from the API URL.

        :param dict values: The create or write values.
        :return: None
        """
        if values.get('adyen_api_url_prefix'):  # Test if we're duplicating a provider.
            values['adyen_api_url_prefix'] = re.sub(
                r'(?:https://)?(\w+-\w+).*', r'\1', values['adyen_api_url_prefix']
            )

    #=== COMPUTE METHODS ===#

    def _compute_feature_support_fields(self):
        """ Override of `payment` to enable additional features. """
        super()._compute_feature_support_fields()
        self.filtered(lambda p: p.code == 'adyen').update({
            'support_manual_capture': 'partial',
            'support_refund': 'partial',
            'support_tokenization': True,
        })

    #=== BUSINESS METHODS - PAYMENT FLOW ===#

    def _adyen_make_request(self, endpoint, endpoint_param=None, payload=None, method='POST'):
        """ Make a request to Adyen API at the specified endpoint.

        Note: self.ensure_one()

        :param str endpoint: The endpoint to be reached by the request
        :param str endpoint_param: A variable required by some endpoints which are interpolated with
                                   it if provided. For example, the provider reference of the source
                                   transaction for the '/payments/{}/refunds' endpoint.
        :param dict payload: The payload of the request
        :param str method: The HTTP method of the request
        :return: The JSON-formatted content of the response
        :rtype: dict
        :raise: ValidationError if an HTTP error occurs
        """

        def _build_url(prefix_, version_, endpoint_):
            """ Build an API URL by appending the version and endpoint to a base URL.

            The final URL follows this pattern: `<_base>/V<_version>/<_endpoint>`.

            :param str prefix_: The API URL prefix of the account.
            :param int version_: The version of the endpoint.
            :param str endpoint_: The endpoint of the URL.
            :return: The final URL.
            :rtype: str
            """
            prefix_ = prefix_.rstrip('/')  # Remove potential trailing slash
            endpoint_ = endpoint_.lstrip('/')  # Remove potential leading slash
            test_mode_ = self.state == 'test'
            prefix_ = f'{prefix_}.adyen' if test_mode_ else f'{prefix_}-checkout-live.adyenpayments'
            return f'https://{prefix_}.com/checkout/V{version_}/{endpoint_}'

        self.ensure_one()

        version = const.API_ENDPOINT_VERSIONS[endpoint]
        endpoint = endpoint if not endpoint_param else endpoint.format(endpoint_param)
        url = _build_url(self.adyen_api_url_prefix, version, endpoint)
        headers = {'X-API-Key': self.adyen_api_key}
        try:
            response = requests.request(method, url, json=payload, headers=headers, timeout=60)
            try:
                response.raise_for_status()
            except requests.exceptions.HTTPError:
                _logger.exception(
                    "invalid API request at %s with data %s: %s", url, payload, response.text
                )
                msg = response.json().get('message', '')
                raise ValidationError(
                    "Adyen: " + _("The communication with the API failed. Details: %s", msg)
                )
        except requests.exceptions.ConnectionError:
            _logger.exception("unable to reach endpoint at %s", url)
            raise ValidationError("Adyen: " + _("Could not establish the connection to the API."))
        return response.json()

    def _adyen_compute_shopper_reference(self, partner_id):
        """ Compute a unique reference of the partner for Adyen.

        This is used for the `shopperReference` field in communications with Adyen and stored in the
        `adyen_shopper_reference` field on `payment.token` if the payment method is tokenized.

        :param recordset partner_id: The partner making the transaction, as a `res.partner` id
        :return: The unique reference for the partner
        :rtype: str
        """
        return f'ODOO_PARTNER_{partner_id}'

    #=== BUSINESS METHODS - GETTERS ===#

    def _adyen_get_inline_form_values(self, pm_code):
        """ Return a serialized JSON of the required values to render the inline form.

        Note: `self.ensure_one()`

        :param str pm_code: The code of the payment method whose inline form to render.
        :return: The JSON serial of the required values to render the inline form.
        :rtype: str
        """
        self.ensure_one()

        inline_form_values = {
            'client_key': self.adyen_client_key,
            'adyen_pm_code': const.PAYMENT_METHODS_MAPPING.get(pm_code, pm_code),
        }
        return json.dumps(inline_form_values)
