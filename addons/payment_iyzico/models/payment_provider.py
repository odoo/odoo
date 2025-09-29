# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import hashlib
import hmac
import json
import random
import string

from odoo import _, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.urls import urljoin

from odoo.addons.payment_iyzico import const


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(
        selection_add=[('iyzico', "Iyzico")], ondelete={'iyzico': 'set default'}
    )
    iyzico_key_id = fields.Char(string="Iyzico API Key", required_if_provider='iyzico', copy=False)
    iyzico_key_secret = fields.Char(
        string="Iyzico Secret Key",
        required_if_provider='iyzico',
        copy=False,
        groups='base.group_system',
    )

    # === COMPUTE METHODS === #

    def _get_supported_currencies(self):
        """Override of `payment` to return the supported currencies."""
        supported_currencies = super()._get_supported_currencies()
        if self.code == 'iyzico':
            supported_currencies = supported_currencies.filtered(
                lambda c: c.name in const.SUPPORTED_CURRENCIES
            )
        return supported_currencies

    # === CRUD METHODS === #

    def _get_default_payment_method_codes(self):
        """Override of `payment` to return the default payment method codes."""
        self.ensure_one()
        if self.code != 'iyzico':
            return super()._get_default_payment_method_codes()
        return const.DEFAULT_PAYMENT_METHOD_CODES

    # === REQUEST HELPERS === #

    def _build_request_url(self, endpoint, **kwargs):
        """Override of `payment` to build the request URL."""
        if self.code != 'iyzico':
            return super()._build_request_url(endpoint, **kwargs)

        if self.state == 'enabled':
            api_url = 'https://api.iyzipay.com'
        else:
            api_url = 'https://sandbox-api.iyzipay.com'

        return urljoin(api_url, endpoint)

    def _build_request_headers(self, method, endpoint, payload, **kwargs):
        """Override of `payment` to build the request headers.

        See https://docs.iyzico.com/en/getting-started/preliminaries/authentication/hmacsha256-auth.
        """
        if self.code != 'iyzico':
            return super()._build_request_headers(method, endpoint, payload, **kwargs)

        random_string = ''.join(
            random.SystemRandom().choice(string.ascii_letters + string.digits) for _i in range(8)
        )
        signature = self._iyzico_calculate_signature(endpoint, payload, random_string)
        authorization_params = [
            f'apiKey:{self.iyzico_key_id}', f'randomKey:{random_string}', f'signature:{signature}'
        ]
        hash_base64 = base64.b64encode('&'.join(authorization_params).encode()).decode()
        return {
            'Authorization': f'IYZWSv2 {hash_base64}',
            'x-iyzi-rnd': random_string,
        }

    def _iyzico_calculate_signature(self, endpoint, payload, random_string):
        """Calculate the signature for the provided data.

        See https://docs.iyzico.com/en/getting-started/preliminaries/authentication/hmacsha256-auth.

        :param str endpoint: The endpoint of the API to reach with the request.
        :param dict payload: The payload of the request.
        :param str random_string: The random string to use for the signature.
        :return: The calculated signature.
        :rtype: str
        """
        payload_string = json.dumps(payload)
        data_string = f'{random_string}/{endpoint}{payload_string}'
        return hmac.new(
            self.iyzico_key_secret.encode(), msg=data_string.encode(), digestmod=hashlib.sha256
        ).hexdigest()

    def _parse_response_error(self, response):
        """Override of `payment` to parse the error message."""
        if self.code != 'iyzico':
            return super()._parse_response_error(response)
        return response.json().get('errorMessage')

    def _parse_response_content(self, response, **kwargs):
        """Override of `payment` to parse the response content."""
        if self.code != 'iyzico':
            return super()._parse_response_content(response, **kwargs)

        response_content = response.json()

        if response_content.get('status') != 'success':
            error_msg = response_content.get('errorMessage')
            raise ValidationError(_("The payment provider rejected the request.\n%s", error_msg))

        return response_content
