# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import re

from odoo import _, api, fields, models

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.logging import get_payment_logger
from odoo.addons.payment_adyen import const


_logger = get_payment_logger(__name__)


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

    # === CRUD METHODS === #

    @api.model_create_multi
    def create(self, vals_list):
        for values in vals_list:
            self._adyen_extract_prefix_from_api_url(values)
        return super().create(vals_list)

    def write(self, vals):
        self._adyen_extract_prefix_from_api_url(vals)
        return super().write(vals)

    def _get_default_payment_method_codes(self):
        """Override of `payment` to return the default payment method codes."""
        self.ensure_one()
        if self.code != 'adyen':
            return super()._get_default_payment_method_codes()
        return const.DEFAULT_PAYMENT_METHOD_CODES

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

    # === COMPUTE METHODS === #

    def _compute_feature_support_fields(self):
        """ Override of `payment` to enable additional features. """
        super()._compute_feature_support_fields()
        self.filtered(lambda p: p.code == 'adyen').update({
            'support_manual_capture': 'partial',
            'support_refund': 'partial',
            'support_tokenization': True,
        })

    # === BUSINESS METHODS === #

    def _adyen_get_inline_form_values(self, pm_code, amount=None, currency=None):
        """ Return a serialized JSON of the required values to render the inline form.

        Note: `self.ensure_one()`

        :param str pm_code: The code of the payment method whose inline form to render.
        :param float amount: The transaction amount.
        :param res.currency currency: The transaction currency.
        :return: The JSON serial of the required values to render the inline form.
        :rtype: str
        """
        self.ensure_one()

        inline_form_values = {
            'client_key': self.adyen_client_key,
            'adyen_pm_code': const.PAYMENT_METHODS_MAPPING.get(pm_code, pm_code),
            'formatted_amount': self._adyen_get_formatted_amount(amount, currency),
        }
        return json.dumps(inline_form_values)

    def _adyen_get_formatted_amount(self, amount=None, currency=None):
        """ Return the amount in the format required by Adyen.

        The formatted amount is a dict with keys 'value' and 'currency'.

        :param float amount: The transaction amount.
        :param res.currency currency: The transaction currency.
        :return: The Adyen-formatted amount.
        :rtype: dict
        """
        currency_code = currency and currency.name
        converted_amount = amount and currency_code and payment_utils.to_minor_currency_units(
            amount, currency, const.CURRENCY_DECIMALS.get(currency_code)
        )
        return {
            'value': converted_amount,
            'currency': currency_code,
        }

    def _adyen_compute_shopper_reference(self, partner_id):
        """ Compute a unique reference of the partner for Adyen.

        This is used for the `shopperReference` field in communications with Adyen and stored in the
        `adyen_shopper_reference` field on `payment.token` if the payment method is tokenized.

        :param recordset partner_id: The partner making the transaction, as a `res.partner` id
        :return: The unique reference for the partner
        :rtype: str
        """
        return f'ODOO_PARTNER_{partner_id}'

    # === REQUEST HELPERS === #

    def _build_request_url(self, endpoint, *, endpoint_param=None, **kwargs):
        """Override of `payment` to build the request URL based on the API URL prefix.

        The final URL follows the pattern `<_base>/V<_version>/<_endpoint>`.
        """
        if self.code != 'adyen':
            return self._build_request_url(endpoint, endpoint_param=endpoint_param, **kwargs)

        version = const.API_ENDPOINT_VERSIONS[endpoint]
        endpoint = endpoint if not endpoint_param else endpoint.format(endpoint_param)
        prefix_ = self.adyen_api_url_prefix.rstrip('/')  # Remove potential trailing slash.
        endpoint = endpoint.lstrip('/')  # Remove potential leading slash.
        test_mode_ = self.state == 'test'
        prefix_ = f'{prefix_}.adyen' if test_mode_ else f'{prefix_}-checkout-live.adyenpayments'
        return f'https://{prefix_}.com/checkout/V{version}/{endpoint}'

    def _build_request_headers(self, method, *args, idempotency_key=None, **kwargs):
        """Override of `payment` to include the API key and idempotency key in the headers."""
        if self.code != 'adyen':
            return super()._build_request_headers(
                method, *args, idempotency_key=idempotency_key, **kwargs
            )

        headers = {'X-API-Key': self.adyen_api_key}
        if method == 'POST' and idempotency_key:
            headers['idempotency-key'] = idempotency_key
        return headers

    def _parse_response_error(self, response):
        """Override of `payment` to extract the error message from the response."""
        if self.code != 'adyen':
            return super()._parse_response_error(response)
        return response.json().get('message', '')
