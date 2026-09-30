# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.urls import urljoin

from odoo.addons.payment.logging import get_payment_logger
from odoo.addons.payment_toss_payments import const

_logger = get_payment_logger(__name__, const.SENSITIVE_KEYS)


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(
        selection_add=[('toss_payments', "Toss Payments")],
        ondelete={'toss_payments': 'set default'},
    )
    toss_payments_client_key = fields.Char(
        string="Toss Payments Client Key", required_if_provider='toss_payments', copy=False
    )
    toss_payments_secret_key = fields.Char(
        string="Toss Payments Secret Key",
        required_if_provider='toss_payments',
        copy=False,
        groups='base.group_system',
    )
    toss_payments_webhook_url = fields.Char(
        string="Toss Payments Webhook URL",
        compute='_compute_toss_payments_webhook_url',
        readonly=True,
    )

    # === COMPUTE METHODS === #

    def _get_supported_currencies(self):
        """Override of `payment` to return the supported currencies."""
        supported_currencies = super()._get_supported_currencies()
        if self.code == 'toss_payments':
            supported_currencies = supported_currencies.filtered(
                lambda c: c.name == const.SUPPORTED_CURRENCY
            )
        return supported_currencies

    def _compute_toss_payments_webhook_url(self):
        self.toss_payments_webhook_url = urljoin(self.get_base_url(), const.WEBHOOK_ROUTE)

    # ==== CONSTRAINT METHODS === #

    @api.constrains('available_currency_ids')
    def _check_available_currency_ids_only_contains_supported_currencies(self):
        for provider in self.filtered(lambda p: p.code == 'toss_payments'):
            if provider.available_currency_ids != self.env.ref('base.KRW'):
                raise ValidationError(self.env._("Currencies other than KRW are not supported."))

    # === CRUD METHODS === #

    def _get_default_payment_method_codes(self):
        """Override of `payment` to return the default payment method codes."""
        self.ensure_one()
        if self.code != 'toss_payments':
            return super()._get_default_payment_method_codes()
        return const.DEFAULT_PAYMENT_METHOD_CODES

    # === BUSINESS METHODS === #

    def _toss_payments_get_inline_form_values(self, pm_code):
        """Return a serialized JSON of the required values to initialize payment window.

        Note: `self.ensure_one()`

        :param str pm_code: The code of the payment method whose payment window is called.
        :return: The JSON serial of the required values to initialize the payment window.
        :rtype: str
        """
        self.ensure_one()

        inline_form_values = {
            'client_key': self.toss_payments_client_key,
            'toss_payments_pm_code': const.PAYMENT_METHODS_MAPPING.get(pm_code, pm_code),
        }
        return json.dumps(inline_form_values)

    # === REQUEST HELPERS === #

    def _build_request_url(self, endpoint, **kwargs):
        """Override of `payment` to build the request URL."""
        if self.code != 'toss_payments':
            return super()._build_request_url(endpoint, **kwargs)

        return urljoin('https://api.tosspayments.com/', endpoint)

    def _build_request_headers(self, method, endpoint, payload, **kwargs):
        """Override of `payment` to include the encoded secret key in the header."""
        if self.code != 'toss_payments':
            return super()._build_request_headers(method, endpoint, payload, **kwargs)

        return {'Idempotency-Key': f'{payload.get("orderId")}:{payload.get("paymentKey")}'}

    def _build_request_auth(self, **kwargs):
        """Override of `payment` to build the request Auth."""
        if self.code != 'toss_payments':
            return super()._build_request_auth(**kwargs)
        return self.toss_payments_secret_key, ''

    def _parse_response_error(self, response):
        """Override of `payment` to parse the error message."""
        if self.code != 'toss_payments':
            return super()._parse_response_error(response)

        return f'{response.json()["message"]} ({response.json()["code"]})'
