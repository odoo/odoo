# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
import binascii
import hashlib
import hmac
import logging
import re

import requests

from odoo import api, fields, models
from odoo.exceptions import ValidationError

# Endpoints of the Checkout API.
# See https://docs.adyen.com/api-explorer/#/PaymentSetupAndVerificationService/v52/overview
API_ENDPOINTS = {
    'disable': {'path': '/disable', 'version': 49},
    'origin_keys': {'path': '/originKeys', 'version': 53},
    'payments': {'path': '/payments', 'version': 53},
    'payments_details': {'path': '/payments/details', 'version': 53},
    'payment_methods': {'path': '/paymentMethods', 'version': 53},
}

# Adyen-specific mapping of currency codes in ISO 4217 format to the number of decimals.
# Only currencies for which Adyen does not follow the ISO 4217 norm are listed here.
# See https://docs.adyen.com/development-resources/currency-codes
CURRENCY_DECIMALS = {
    'CLP': 2,
    'CVE': 0,
    'IDR': 0,
    'ISK': 2,
}

_logger = logging.getLogger(__name__)


class PaymentAcquirer(models.Model):

    _inherit = 'payment.acquirer'

    provider = fields.Selection(
        selection_add=[('adyen', "Adyen")], ondelete={'adyen': 'set default'}
    )
    adyen_merchant_account = fields.Char(
        string="Merchant Account",
        help="The code of the merchant account to use with this acquirer",
        required_if_provider='adyen', groups='base.group_system')
    adyen_api_key = fields.Char(
        string="API Key", help="The API key of the user account", required_if_provider='adyen',
        groups='base.group_system')
    adyen_hmac_key = fields.Char(
        string="HMAC Key", help="The HMAC key of the webhook", required_if_provider='adyen',
        groups='base.group_system')
    adyen_checkout_api_url = fields.Char(
        string="Checkout API URL", help="The base URL for the Checkout API endpoints",
        required_if_provider='adyen', groups='base.group_system')
    adyen_recurring_api_url = fields.Char(
        string="Recurring API URL", help="The base URL for the Recurring API endpoints",
        required_if_provider='adyen', groups='base.group_system')

    #=== COMPUTE METHODS ===#

    @api.model
    def _get_supported_features(self, provider):
        """Get the specification of features supported by Adyen.

        :param string provider: The provider of the acquirer
        :return: The supported features for this acquirer
        :rtype: dict
        """
        if provider != 'adyen':
            return super()._get_supported_features(provider)

        return {'tokenization': True}

    #=== CRUD METHODS ===#

    @api.model_create_multi
    def create(self, values_list):
        for values in values_list:
            self._adyen_trim_api_urls(values)
        return super().create(values_list)

    def write(self, values):
        self._adyen_trim_api_urls(values)
        return super().write(values)

    @api.model
    def _adyen_trim_api_urls(self, values):
        """ Remove the version and the endpoint from the url of Adyen API fields.

        :param dict values: The create or write values
        :return: None
        """
        for field_name in ('adyen_checkout_api_url', 'adyen_recurring_api_url'):
            if field_name in values:
                field_value = values[field_name]
                values[field_name] = re.sub(r'[vV]\d+(/.*)?', '', field_value)

    #=== BUSINESS METHODS ===#

    def _adyen_compute_signature(self, payload):
        """ Compute the HMAC SHA256 signature of a request from Adyen to Odoo.

        See https://docs.adyen.com/development-resources/webhooks/verify-hmac-signatures

        Note: self.ensure_one()

        :param dict payload: The request payload. The value `None` should only be assigned to a key
                            if it is its intended value, and not as a default for the key, since all
                            values are used in the signature computation.
        :return: The HMAC SHA256 signature of the request
        :rtype: bytes
        """

        def _flatten_dict(_value, _path_base='', _separator='.'):
            """ Recursively generate a flat representation of a dict.

            :param Object _value: The value to flatten. A dict or an already flat value
            :param str _path_base: They base path for keys of _value, including preceding separators
            :param str _separator: The string to use as a separator in the key path
            """
            if type(_value) == dict:  # The inner value is a dict, flatten it
                _path_base = _path_base if not _path_base else _path_base + _separator
                for _key in _value:
                    yield from _flatten_dict(_value[_key], _path_base + str(_key))
            else:  # The inner value cannot be flattened, yield it
                yield _path_base, _value

        def _to_escaped_string(_value):
            """ Escape payload values that are using illegal symbols and cast them to string.

            String values containing `\\` or `:` are prefixed with `\\`.
            Empty values (`None`) are replaced by an empty string.

            :param Object _value: The value to escape
            :return: The escaped value
            :rtype: string
            """
            if isinstance(_value, str):
                return _value.replace('\\', '\\\\').replace(':', '\\:')
            elif _value is None:
                return ''
            else:
                return str(_value)

        self.ensure_one()

        signature_keys = [
            'pspReference', 'originalReference', 'merchantAccountCode', 'merchantReference',
            'amount.value', 'amount.currency', 'eventCode', 'success'
        ]

        # Flatten the payload to allow accessing inner dicts naively
        flattened_payload = {k: v for k, v in _flatten_dict(payload)}
        # Build the list of signature values as per the list of required signature keys
        signature_values = [flattened_payload.get(key) for key in signature_keys]
        # Escape values using forbidden symbols
        escaped_values = [_to_escaped_string(value) for value in signature_values]
        # Concatenate values together with ':' as delimiter
        signing_string = ':'.join(escaped_values)
        # Convert the HMAC key to the binary representation
        binary_hmac_key = binascii.a2b_hex(self.adyen_hmac_key.encode('ascii'))
        # Calculate the HMAC with the binary representation of the signing string with SHA-256
        binary_hmac = hmac.new(binary_hmac_key, signing_string.encode('utf-8'), hashlib.sha256)
        # Calculate the signature by encoding the result with Base64
        signature = base64.b64encode(binary_hmac.digest())
        return signature

    def _adyen_compute_shopper_reference(self, partner_id):
        """ Compute a unique reference of the partner for Adyen.

        This is used for the `shopperReference` field in communications with Adyen and stored in the
        `adyen_shopper_reference` field on `payment.token` if the payment method is tokenized.

        :param recordset partner_id: The partner making the transaction, as a `res.partner` id
        :return: The unique reference for the partner
        :rtype: str
        """
        return f'ODOO_PARTNER_{partner_id}'

    def _adyen_make_request(self, base_url, endpoint_key, payload=None, method='POST'):
        """ Make a request to Adyen API at the specified endpoint.

        Note: self.ensure_one()

        :param str base_url: The base for the request URL. Depends on both the merchant and the API
        :param str endpoint_key: The identifier of the endpoint to be reached by the request
        :param dict payload: The payload of the request
        :param str method: The HTTP method of the request
        :return The JSON-formatted content of the response
        :rtype: dict
        :raise: ValidationError if an HTTP error occurs
        """

        def _build_url(_base_url, _version, _endpoint):
            """ Build an API URL by appending the version and endpoint to a base URL.

            The final URL follows this pattern : `<_base>/V<_version>/<_endpoint>`.

            :param str _base_url: The base of the url prefixed with `https://`
            :param int _version: The version of the endpoint
            :param str _endpoint: The endpoint of the URL.
            :return: The final URL
            :rtype: str
            """
            _base = _base_url.rstrip("/")  # Remove potential trailing slash
            _endpoint = _endpoint.lstrip("/")  # Remove potential leading slash
            return f'{_base}/V{_version}/{_endpoint}'

        self.ensure_one()

        version, endpoint = (API_ENDPOINTS[endpoint_key][k] for k in ('version', 'path'))
        url = _build_url(base_url, version, endpoint)
        headers = {'X-API-Key': self.adyen_api_key}
        response = requests.request(method, url, json=payload, headers=headers)
        if not response.ok:
            try:
                response.raise_for_status()
            except requests.exceptions.HTTPError:
                _logger.exception(response.text)
                # TODO try except in controller
                raise ValidationError(f"Adyen: {response.text}")
        return response.json()
