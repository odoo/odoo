# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.tools import urls

from odoo.addons.payment.logging import get_payment_logger
from odoo.addons.payment_mercado_pago import const


_logger = get_payment_logger(__name__)


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(
        selection_add=[('mercado_pago', "Mercado Pago")], ondelete={'mercado_pago': 'set default'}
    )
    mercado_pago_access_token = fields.Char(
        string="Mercado Pago Access Token",
        required_if_provider='mercado_pago',
        groups='base.group_system',
    )

    # === COMPUTE METHODS === #

    def _get_supported_currencies(self):
        """ Override of `payment` to return the supported currencies. """
        supported_currencies = super()._get_supported_currencies()
        if self.code == 'mercado_pago':
            supported_currencies = supported_currencies.filtered(
                lambda c: c.name in const.SUPPORTED_CURRENCIES
            )
        return supported_currencies

    # === CRUD METHODS === #

    def _get_default_payment_method_codes(self):
        """ Override of `payment` to return the default payment method codes. """
        self.ensure_one()
        if self.code != 'mercado_pago':
            return super()._get_default_payment_method_codes()
        return const.DEFAULT_PAYMENT_METHOD_CODES

    # === REQUEST HELPERS === #

    def _build_request_url(self, endpoint, **kwargs):
        """Override of `payment` to build the request URL."""
        if self.code != 'mercado_pago':
            return super()._build_request_url(endpoint, **kwargs)
        return urls.urljoin('https://api.mercadopago.com', endpoint)

    def _build_request_headers(self, *args, **kwargs):
        """Override of `payment` to build the request headers."""
        if self.code != 'mercado_pago':
            return super()._build_request_headers(*args, **kwargs)
        return {
            'Authorization': f'Bearer {self.mercado_pago_access_token}',
            'X-Platform-Id': 'dev_cdf1cfac242111ef9fdebe8d845d0987',
        }

    def _parse_response_error(self, response):
        """Override of `payment` to parse the error message."""
        if self.code != 'mercado_pago':
            return super()._parse_response_error(response)
        return response.json().get('message', '')
