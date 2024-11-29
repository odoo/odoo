# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json

from urllib.parse import urlencode


from werkzeug import urls

from odoo.addons.payment.const import REPORT_REASONS_MAPPING
from odoo.addons.payment_mercado_pago.controllers.main import MercadoPagoController
from odoo.addons.payment_mercado_pago.controllers.onboarding import MercadoPagoController
from odoo import _, api, fields, models

from odoo.exceptions import ValidationError

from odoo.addons.payment.logging import get_payment_logger
from odoo.addons.payment_mercado_pago import const
from odoo.addons.payment_mercado_pago.controllers.onboarding import MercadoPagoController


_logger = get_payment_logger(__name__)


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(
        selection_add=[('mercado_pago', "Mercado Pago")], ondelete={'mercado_pago': 'set default'}
    )
    # OAuth fields
    mercado_pago_access_token = fields.Char(
        string="Mercado Pago Access Token", groups='base.group_system',
    )
    mercado_pago_access_token_expiry = fields.Datetime(
        string="Mercado Pago Access Token Expiry", groups='base.group_system'
    )
    mercado_pago_refresh_token = fields.Char(
        string="Mercado Pago Refresh Token", groups='base.group_system'
    )
    mercado_pago_public_key = fields.Char(
        string="Mercado Pago Public Key", groups='base.group_system'
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

    def _compute_feature_support_fields(self):
        """ Override of `payment` to enable additional features. """
        super()._compute_feature_support_fields()
        self.filtered(lambda p: p.code == 'mercado_pago').update({
            'support_tokenization': True,
        })

    # === ACTIONS METHODS === #

    def action_mercado_pago_redirect_to_oauth_url(self):
        """ Redirect to the Mercado Pago OAuth URL.

        Note: `self.ensure_one()`

        :return: An URL action to redirect to the Mercado Pago OAuth URL.
        :rtype: dict
        """
        self.ensure_one()

        authorization_url = self._get_oauth_url(
            proxy_url=const.OAUTH_URL,
            return_endpoint=MercadoPagoController.OAUTH_RETURN_URL
        )
        return {
            'type': 'ir.actions.act_url',
            'url': authorization_url,
            'target': 'self',
        }
    # === BUSINESS METHODS === #

    @api.model #TODO ANKO move
    def _get_compatible_providers(self, payment_utils=None, *args, is_validation=False, report=None, **kwargs):
        """ Override of `payment` to filter out Mercado Pago providers for validation operations.
        """
        providers = super()._get_compatible_providers(
            *args, is_validation=is_validation, report=report, **kwargs
        )

        if is_validation:
            unfiltered_providers = providers
            providers = providers.filtered(lambda p: p.code != 'mercado_pago')
            payment_utils.add_to_report(
                report,
                unfiltered_providers - providers,
                available=False,
                reason=REPORT_REASONS_MAPPING['validation_not_supported'],
            )

        return providers

    # === CRUD METHODS === #

    def _get_default_payment_method_codes(self):
        """ Override of `payment` to return the default payment method codes. """
        self.ensure_one()
        if self.code != 'mercado_pago':
            return super()._get_default_payment_method_codes()
        return const.DEFAULT_PAYMENT_METHOD_CODES

    # === REQUEST HELPERS === #

    def _build_request_url(self, endpoint, is_proxy_request=False, **kwargs):
        """Override of `payment` to build the request URL."""
        if self.code != 'mercado_pago':
            return super()._build_request_url(endpoint, **kwargs)
        if is_proxy_request:
            return f'{const.OAUTH_URL}{endpoint}'
        return urls.url_join('https://api.mercadopago.com', endpoint)

    def _build_request_headers(self, *args, is_proxy_request=False, **kwargs):
        """Override of `payment` to build the request headers."""
        if self.code != 'mercado_pago':
            return super()._build_request_headers(*args, **kwargs)

        headers = {
            'Authorization': f'Bearer {self.mercado_pago_access_token}',
            'X-Platform-Id': 'dev_cdf1cfac242111ef9fdebe8d845d0987',
        }
        if not is_proxy_request and self.mercado_pago_access_token:
            headers['Authorization'] = f'Bearer {self.mercado_pago_access_token}'
        return headers

    def _parse_response_error(self, response):
        """Override of `payment` to parse the error message."""
        if self.code != 'mercado_pago':
            return super()._parse_response_error(response)
        return response.json().get('message', '')

    def _mercado_pago_get_inline_form_values(self, partner_id):
        self.ensure_one()
        partner = self.env['res.partner'].browse(partner_id).exists()
        inline_form_values = {
            'email': partner.email,
            'mercado_pago_public_key': self.mercado_pago_public_key,
        }
        return json.dumps(inline_form_values)

    # def _mercado_pago_refresh_token(self):
    #     """ TODO ADD DOCSTRING"""
    #     #TODO ANKO make call to IAP proxy
    #     self.ensure_one()
    #
    #     proxy_payload = self._prepare_json_rpc_payload(
    #         {'mercado_pago_refresh_token': self.mercado_pago_refresh_token}
    #     )
    #     response_content = self._send_api_request(
    #         'POST',
    #         '/oauth/token',
    #         json=proxy_payload,
    #         is_proxy_request=True,
    #     )
    #     response_content = self._make_proxy_request( #Change to send api
    #         url=const.OAUTH_URL,
    #         endpoint=
    #         payload={'mercado_pago_refresh_token': self.mercado_pago_refresh_token}
    #     )
    #     expires_in = fields.Datetime.now() + timedelta(seconds=int(response_content['expires_in']))
    #     self.write({
    #         'mercado_pago_access_token': response_content['access_token'],
    #         'mercado_pago_refresh_token': response_content['refresh_token'],
    #         'mercado_pago_access_token_expiry': expires_in,
    #     })
