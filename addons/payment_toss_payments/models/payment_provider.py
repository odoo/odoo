# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64

from odoo import fields, models

from odoo.addons.payment_toss_payments import const
from odoo.addons.payment.logging import get_payment_logger

_logger = get_payment_logger(__name__)


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(
        selection_add=[('tosspayments', "Toss Payments")], ondelete={'tosspayments': 'set default'},
    )

    tosspayments_client_key = fields.Char(
        string="Toss Client Key", groups='base.group_system', required_if_provider='tosspayments',
    )
    tosspayments_secret_key = fields.Char(
        string="Toss Secret Key", groups='base.group_system', required_if_provider='tosspayments',
    )

    # === COMPUTE METHODS === #

    def _compute_feature_support_fields(self):
        """ Override of `payment` to enable additional features. """
        super()._compute_feature_support_fields()
        self.filtered(lambda p: p.code == 'tosspayments').update({
            'support_manual_capture': 'partial',
        })

    def _get_supported_currencies(self):
        """ Override of `payment` to return the supported currencies. """
        supported_currencies = super()._get_supported_currencies()
        if self.code == 'tosspayments':
            supported_currencies = supported_currencies.filtered(
                lambda c: c.name in const.SUPPORTED_CURRENCIES,
            )
        return supported_currencies

    # === CRUD METHODS === #
    # Note: methods below are used by the CRUD methods of the parent payment.provider model

    def _get_default_payment_method_codes(self):
        """ Override of `payment` to return the default payment method codes. """
        if self.code != 'tosspayments':
            return super()._get_default_payment_method_codes()
        return const.DEFAULT_PAYMENT_METHOD_CODES

    # === REQUEST HELPERS === #

    def _build_request_url(self, endpoint, *, endpoint_param=None, **kwargs):
        """ Override of `payment` to build the request URL. """
        if self.code != 'tosspayments':
            return self._build_request_url(endpoint, endpoint_param=endpoint_param, **kwargs)

        return f"https://api.tosspayments.com{endpoint}"

    def _build_request_headers(self, method, *args, idempotency_key=None, **kwargs):
        """ Override of `payment` to include the encoded secret key in the header """
        if self.code != 'tosspayments':
            return self._build_request_headers(
                method, *args, idempotency_key=idempotency_key, **kwargs,
            )

        encoded_key = base64.b64encode(f"{self.tosspayments_secret_key}:".encode())
        return {
            'Authorization': f"Basic {encoded_key.decode()}",
            'Content-Type': "application/json",
        }

    def _parse_response_error(self, response):
        """"Override of `payment` to parse the error message."""
        if self.provider_code != 'tosspayments':
            return super()._parse_response_error(response)

        try:
            message = response['error']['message']
        except (KeyError, TypeError):
            message = 'UNKNOWN_ERROR'
            _logger.warning("Parsing error response from payment provider API failed. Error message"
                            " will default to '%s'", message)
        finally:
            return message
