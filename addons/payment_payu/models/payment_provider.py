# Part of Odoo. See LICENSE file for full copyright and licensing details.

from typing import Literal

from odoo import api, fields, models
from odoo.exceptions import ValidationError

from odoo.addons.payment_payu import const as payu_const



class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(
        selection_add=[('payu', 'PayU')], ondelete={'payu': 'set default'},
    )
    payu_merchant_key = fields.Char(
        string='Merchant Key',
        help='The key solely used to identify the account with PayU.',
        required_if_provider='payu',
        copy=False,
    )
    payu_merchant_salt = fields.Char(
        string='Salt',
        help='The salt used to generate a hash.',
        required_if_provider='payu',
        copy=False,
    )

    # === COMPUTE METHODS === #

    def _compute_feature_support_fields(self):
        """ Override of `payment` to enable additional features. """
        super()._compute_feature_support_fields()
        self.filtered(lambda p: p.code == 'payu').update({
            'support_refund': 'partial',
        })

    # === CRUD METHODS === #

    def _get_supported_currencies(self):
        """ Override of `payment` to return the supported currencies. """
        supported_currencies = super()._get_supported_currencies()
        if self.code == 'payu':
            supported_currencies = supported_currencies.filtered(lambda c: c.name in payu_const.SUPPORTED_CURRENCIES)
        return supported_currencies

    def _get_default_payment_method_codes(self):
        """ Override of `payment` to return the default payment method codes. """
        self.ensure_one()
        if self.code != 'payu':
            return super()._get_default_payment_method_codes()
        return payu_const.DEFAULT_PAYMENT_METHOD_CODES

    # === REQUEST HELPERS === #

    def _build_request_url(self, endpoint, *, mode: Literal['payment', 'refund'] = 'payment', **kwargs):
        """ Override of `payment` to build the request URL. """
        if self.code != 'payu':
            return super()._build_request_url(endpoint, mode=mode, **kwargs)

        url_host = payu_const.TEST_BASE_URL if self.state == 'test' else payu_const.PROD_BASE_URL
        return f'https://{url_host}{endpoint}'

    def _build_request_headers(self, *args, mode: Literal['payment', 'refund'] = 'payment', **kwargs):
        """ Override of `payment` to build the request headers. """
        if self.code != 'payu':
            return super()._build_request_headers(*args, mode=mode, **kwargs)

        return {'Content-Type': 'application/x-www-form-urlencoded' if mode == 'refund' else 'application/json'}

    def _parse_response_content(self, response, *, mode: Literal['payment', 'refund'] = 'payment', **kwargs):
        """ Override of `payment` to parse response content. """
        if self.code != 'payu':
            return super()._parse_response_content(response, mode=mode, **kwargs)
        try:
            response_content = response.json()
        except ValueError:
            raise ValidationError(self.env._('Invalid response from Payu.'))

        if response_content.get('status') == 0:
            # status: (0: API failure, 1: API Success)
            raise ValidationError(
                self.env._('The payment provider rejected the request.\n%s', response_content.get('msg')),
            )
        return response_content

    def _parse_response_error(self, response):
        if self.code != 'payu':
            return super()._parse_response_error(response)
        try:
            response_json = response.json()
            response_msg = response_json.get('msg') or response_json.get('error_description')  # Refund or Onboarding
        except ValueError:
            raise ValidationError(self.env._('Error occurred while parsing message from Payu.'))
        return response_msg
