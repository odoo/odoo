# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

from odoo.addons.payment.logging import get_payment_logger
from odoo.addons.payment_xendit import const


_logger = get_payment_logger(__name__)


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(
        selection_add=[('xendit', "Xendit")], ondelete={'xendit': 'set default'}
    )
    xendit_public_key = fields.Char(
        string="Xendit Public Key",
        required_if_provider='xendit',
        copy=False,
        groups='base.group_system',
    )
    xendit_secret_key = fields.Char(
        string="Xendit Secret Key",
        required_if_provider='xendit',
        copy=False,
        groups='base.group_system',
    )
    xendit_webhook_token = fields.Char(
        string="Xendit Webhook Token",
        required_if_provider='xendit',
        copy=False,
        groups='base.group_system',
    )

    # === COMPUTE METHODS === #

    def _compute_feature_support_fields(self):
        """ Override of `payment` to enable additional features. """
        super()._compute_feature_support_fields()
        self.filtered(lambda p: p.code == 'xendit').support_tokenization = True

    def _get_supported_currencies(self):
        """ Override of `payment` to return the supported currencies. """
        supported_currencies = super()._get_supported_currencies()
        if self.code == 'xendit':
            supported_currencies = supported_currencies.filtered(
                lambda c: c.name in const.SUPPORTED_CURRENCIES
            )
        return supported_currencies

    # === CRUD METHODS === #

    def _get_default_payment_method_codes(self):
        """ Override of `payment` to return the default payment method codes. """
        self.ensure_one()
        if self.code != 'xendit':
            return super()._get_default_payment_method_codes()
        return const.DEFAULT_PAYMENT_METHOD_CODES

    # === BUSINESS METHODS === #

    def _get_redirect_form_view(self, is_validation=False):
        """ Override of `payment` to avoid rendering the form view for validation operations.

        Unlike other compatible payment methods in Xendit, `Card` is implemented using a direct
        flow. To avoid rendering a useless template, and also to avoid computing wrong values, this
        method returns `None` for Xendit's validation operations (Card is and will always be the
        sole tokenizable payment method for Xendit).

        Note: `self.ensure_one()`

        :param bool is_validation: Whether the operation is a validation.
        :return: The view of the redirect form template or None.
        :rtype: ir.ui.view | None
        """
        self.ensure_one()

        if self.code == 'xendit' and is_validation:
            return None
        return super()._get_redirect_form_view(is_validation)

    # === REQUEST HELPERS ===#

    def _build_request_url(self, endpoint, **kwargs):
        """Override of `payment` to build the request URL."""
        if self.code != 'xendit':
            return super()._build_request_url(endpoint, **kwargs)
        return f'https://api.xendit.co/{endpoint}'

    def _build_request_auth(self, **kwargs):
        """Override of `payment` to build the request Auth."""
        if self.code != 'xendit':
            return super()._build_request_auth(**kwargs)
        return self.xendit_secret_key, ''

    def _parse_response_error(self, response):
        """Override of `payment` to parse the error message."""
        if self.code != 'xendit':
            return super()._parse_response_error(response)
        return response.json().get('message')
