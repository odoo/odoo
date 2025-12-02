# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.tools.urls import urljoin as url_join

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.const import REPORT_REASONS_MAPPING
from odoo.addons.payment.logging import get_payment_logger
from odoo.addons.payment_flutterwave import const


_logger = get_payment_logger(__name__)


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(
        selection_add=[('flutterwave', "Flutterwave")], ondelete={'flutterwave': 'set default'}
    )
    flutterwave_public_key = fields.Char(
        string="Flutterwave Public Key",
        help="The key solely used to identify the account with Flutterwave.",
        required_if_provider='flutterwave',
        copy=False,
    )
    flutterwave_secret_key = fields.Char(
        string="Flutterwave Secret Key",
        required_if_provider='flutterwave',
        copy=False,
        groups='base.group_system',
    )
    flutterwave_webhook_secret = fields.Char(
        string="Flutterwave Webhook Secret",
        required_if_provider='flutterwave',
        copy=False,
        groups='base.group_system',
    )

    #=== COMPUTE METHODS ===#

    def _compute_feature_support_fields(self):
        """ Override of `payment` to enable additional features. """
        super()._compute_feature_support_fields()
        self.filtered(lambda p: p.code == 'flutterwave').update({
            'support_tokenization': True,
        })

    def _get_supported_currencies(self):
        """ Override of `payment` to return the supported currencies. """
        supported_currencies = super()._get_supported_currencies()
        if self.code == 'flutterwave':
            supported_currencies = supported_currencies.filtered(
                lambda c: c.name in const.SUPPORTED_CURRENCIES
            )
        return supported_currencies

    # === CRUD METHODS === #

    def _get_default_payment_method_codes(self):
        """ Override of `payment` to return the default payment method codes. """
        self.ensure_one()
        if self.code != 'flutterwave':
            return super()._get_default_payment_method_codes()
        return const.DEFAULT_PAYMENT_METHOD_CODES

    # === BUSINESS METHODS ===#

    @api.model
    def _get_compatible_providers(self, *args, is_validation=False, report=None, **kwargs):
        """ Override of `payment` to filter out Flutterwave providers for validation operations. """
        providers = super()._get_compatible_providers(
            *args, is_validation=is_validation, report=report, **kwargs
        )

        if is_validation:
            unfiltered_providers = providers
            providers = providers.filtered(lambda p: p.code != 'flutterwave')
            payment_utils.add_to_report(
                report,
                unfiltered_providers - providers,
                available=False,
                reason=REPORT_REASONS_MAPPING['validation_not_supported'],
            )

        return providers

    # === REQUEST HELPERS === #

    def _build_request_url(self, endpoint, **kwargs):
        """Override of `payment` to build the request URL."""
        if self.code != 'flutterwave':
            return super()._build_request_url(endpoint, **kwargs)
        return url_join('https://api.flutterwave.com/v3/', endpoint)

    def _build_request_headers(self, *args, **kwargs):
        """Override of `payment` to build the request headers."""
        if self.code != 'flutterwave':
            return super()._build_request_headers(*args, **kwargs)
        return {'Authorization': f'Bearer {self.flutterwave_secret_key}'}

    def _parse_response_error(self, response):
        """Override of `payment` to parse the error message."""
        if self.code != 'flutterwave':
            return super()._parse_response_error(response)
        return response.json().get('message', '')

    def _parse_response_content(self, response, **kwargs):
        """Override of `payment` to parse the response content."""
        if self.code != 'flutterwave':
            return super()._parse_response_content(response, **kwargs)
        return response.json()['data']
