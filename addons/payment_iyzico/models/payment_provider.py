# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import hashlib
import hmac
import json
import logging
import pprint
import random
import requests
import string

from odoo import fields, models
from odoo.exceptions import ValidationError

from odoo.addons.payment_iyzico import const

_logger = logging.getLogger(__name__)


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(
        selection_add=[('iyzico', "Iyzico")], ondelete={'iyzico': 'set default'}
    )
    iyzico_key_id = fields.Char(
        string="Iyzico Key Id",
        help="The key solely used to identify the account with Iyzico.",
        required_if_provider='iyzico',
    )
    iyzico_key_secret = fields.Char(
        string="Iyzico Key Secret",
        required_if_provider='iyzico',
        groups='base.group_system',
    )

    # === BUSINESS METHODS === #

    def _iyzico_make_request(self, endpoint, payload=None):
        """ Make a request to Iyzico API to create or verify the transaction token.

        Note: self.ensure_one()

        :param dict payload: The payload of the request.
        :return: The JSON-formatted content of the response.
        :rtype: dict
        :raise ValidationError: If an HTTP error occurs.
        """
        self.ensure_one()

        url = self._iyzico_get_api_url() + endpoint
        request_string = json.dumps(payload or {})

        # Generate random string of 8 charecters
        random_string = self._iyzico_generate_random_string()
        data_string = random_string + endpoint + request_string
        signature = self._iyzico_generate_signature(data_string)

        authorization_params = [
            'apiKey:' + self.iyzico_key_id,
            'randomKey:' + random_string,
            'signature:' + signature
        ]

        # Base64 encoding
        hash_base64 = base64.b64encode('&'.join(authorization_params).encode()).decode()

        headers = {
            'Accept': 'application/json',
            'Authorization': f'IYZWSv2 {hash_base64}',
            'Content-type': 'application/json',
            'x-iyzi-client-version': 'iyzipay-python-1.0.45',
            'x-iyzi-rnd': random_string,
        }
        try:
            response = requests.post(url, data=request_string, headers=headers, timeout=10)
            try:
                response.raise_for_status()
            except requests.exceptions.HTTPError:
                _logger.exception(
                    "Invalid API request at %s with data:\n%s", url, pprint.pformat(payload)
                )
                raise ValidationError(
                    "Iyzico: " + self.env._("The communication with the API failed.")
                )
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            _logger.exception("Unable to reach %s", url)
            raise ValidationError(
                "Iyzico: " + self.env._("The communication with the API failed.")
            )

        response_content = response.json()
        error_code = response_content.get('errorCode')
        if error_code:
            error_message = response_content.get('errorMessage')
            raise ValidationError("Iyzico: " + self.env._(
                "The communication with the API failed. Iyzico gave us the following information: "
                "'%(error_message)s' (code %(error_code)s)",
                error_message=error_message, error_code=error_code,
            ))

        return response_content

    def _iyzico_calculate_signature(self, data):
        """ Compute the signature for the provided data according to the Iyzico documentation.

        :param dict data: The data to sign.
        :return: The calculated signature.
        :rtype: str
        """

        def strip_tailing_zero(amount):
            return amount.endswith('.0') and amount.replace('.0', '') or amount

        # Create the key for HMAC
        data_to_encrypt = ':'.join([
            data.get('paymentStatus'),
            data.get('paymentId'),
            data.get('currency'),
            data.get('basketId'),
            data.get('conversationId'),
            strip_tailing_zero(str(data.get('paidPrice'))),
            strip_tailing_zero(str(data.get('price'))),
            data.get('token'),
        ])

        return self._iyzico_generate_signature(data_to_encrypt)

    # === BUSINESS METHODS - GETTERS === #

    def _get_default_payment_method_codes(self):
        """ Override of `payment` to return the default payment method codes. """
        default_codes = super()._get_default_payment_method_codes()
        if self.code != 'iyzico':
            return default_codes
        return const.DEFAULT_PAYMENT_METHOD_CODES

    def _get_supported_currencies(self):
        """ Override of `payment` to return the supported currencies. """
        supported_currencies = super()._get_supported_currencies()
        if self.code == 'iyzico':
            supported_currencies = supported_currencies.filtered(
                lambda c: c.name in const.SUPPORTED_CURRENCIES
            )
        return supported_currencies

    def _iyzico_generate_random_string(self, size=8):
        """ Generate random string of ascii letters and digits of given size.

        :param int size: Required length of random string (default 8).
        :return: Random string of given size.
        :rtype: str
        """
        return ''.join(
            random.SystemRandom().choice(
                string.ascii_letters + string.digits
            ) for _ in range(size)
        )

    def _iyzico_generate_signature(self, data_to_encrypt):
        """ Generate siqngature to call Iyzico API or Verify received response.

        :param str data_to_encrypt: Data to generate signature from.
        :return: Hexadecimal string to used as signature.
        :rtype: str
        """
        secret_key = bytes(self.iyzico_key_secret.encode('utf-8'))
        hmac_obj = hmac.new(secret_key, digestmod=hashlib.sha256)
        hmac_obj.update(data_to_encrypt.encode('utf-8'))

        return hmac_obj.hexdigest()

    def _iyzico_get_api_url(self):
        """ Return the API URL according to the provider state (test or enabled).

        Note: self.ensure_one()

        :return: The API URL of Iyzico
        :rtype: str
        """
        self.ensure_one()

        if self.state == 'enabled':
            return 'https://api.iyzipay.com'
        else:
            return 'https://sandbox-api.iyzipay.com'
