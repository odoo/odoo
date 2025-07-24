# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
from datetime import timedelta

from werkzeug import urls

from odoo import _, api, fields, models

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.const import REPORT_REASONS_MAPPING
from odoo.addons.payment.logging import get_payment_logger
from odoo.addons.payment_mercado_pago import const
from odoo.addons.payment_mercado_pago.controllers.onboarding import MercadoPagoController
from odoo.exceptions import RedirectWarning

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

    def _compute_feature_support_fields(self):
        """ Override of `payment` to enable additional features. """
        super()._compute_feature_support_fields()
        self.filtered(lambda p: p.code == 'mercado_pago').update({
            'support_tokenization': True,
        })

    def _get_supported_currencies(self):
        """ Override of `payment` to return the supported currencies. """
        supported_currencies = super()._get_supported_currencies()
        if self.code == 'mercado_pago':
            supported_currencies = supported_currencies.filtered(
                lambda c: c.name in const.SUPPORTED_CURRENCIES
            )
        return supported_currencies

    # === CRUD METHODS === #
    @api.model_create_multi
    def create(self, vals_list):
        providers = super().create(vals_list)
        if any(provider.code == 'mercado_pago' for provider in providers):
            self._toggle_token_refresh_cron()
        return providers

    def write(self, vals):
        providers = super().write(vals)
        if 'state' in vals:
            if self.filtered(lambda p: p.code == 'mercado_pago'):
                self._toggle_token_refresh_cron()
        return providers

    @api.model
    def _toggle_token_refresh_cron(self):
        """ Enable the token refresh cron if Mercado Pago is not disabled and refresh token us
        present; disable it otherwise.

        This allows for saving resources on the cron's wake-up overhead when it has nothing to do.

        :return: None
        """
        token_refresh_cron = self.env.ref(
            'payment_mercado_pago.cron_token_refresh_mercado_pago', raise_if_not_found=False
        )
        if token_refresh_cron:
            any_active_mercado_pago_provider = bool(
                self.sudo().search_count(
                    [
                        ('code', '=', 'mercado_pago'),
                        ('state', '!=', 'disabled'),
                        ('mercado_pago_refresh_token', '!=', None)
                    ], limit=1
                )
            )
            token_refresh_cron.active = any_active_mercado_pago_provider

    def _get_default_payment_method_codes(self):
        """ Override of `payment` to return the default payment method codes. """
        self.ensure_one()
        if self.code != 'mercado_pago':
            return super()._get_default_payment_method_codes()
        return const.DEFAULT_PAYMENT_METHOD_CODES

    # === ACTIONS METHODS === #

    def action_start_onboarding(self, menu_id=None):
        """ Override of `payment` to redirect to the Razorpay OAuth URL.

        Note: `self.ensure_one()`

        :param int menu_id: The menu from which the onboarding is started, as an `ir.ui.menu` id.
        :return: An URL action to redirect to the Razorpay OAuth URL.
        :rtype: dict
        :raise RedirectWarning: If the company's currency is not supported.
        """
        self.ensure_one()

        if self.code != 'mercado_pago':
            return super().action_start_onboarding(menu_id=menu_id)

        if self.company_id.currency_id.name not in const.SUPPORTED_CURRENCIES:
            raise RedirectWarning(
                _(
                    "Mercado Pago is not available for your currencies; please use another payment"
                    " provider."
                ),
                self.env.ref('payment.action_payment_provider').id,
                _("Other Payment Providers"),
            )

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

    @api.model
    def _get_compatible_providers(self, *args, is_validation=False, report=None, **kwargs):
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

    def _mercado_pago_get_inline_form_values(self, partner_id):
        self.ensure_one()
        partner = self.env['res.partner'].browse(partner_id).exists()
        inline_form_values = {
            'email': partner.email,
            'mercado_pago_public_key': self.mercado_pago_public_key,
        }
        return json.dumps(inline_form_values)

    # === REQUEST HELPERS === #

    def _build_request_url(self, endpoint, *, is_proxy_request=False, **kwargs):
        """Override of `payment` to build the request URL."""
        if self.code != 'mercado_pago':
            return super()._build_request_url(endpoint, **kwargs)
        if is_proxy_request:
            return f'{const.OAUTH_URL}{endpoint}'
        return urls.url_join('https://api.mercadopago.com', endpoint)

    def _build_request_headers(self, method, *args, idempotency_key=None, is_proxy_request=False, **kwargs):
        """Override of `payment` to build the request headers."""
        if self.code != 'mercado_pago':
            return super()._build_request_headers(
                method,
                *args,
                idempotency_key=idempotency_key,
                is_proxy_request=is_proxy_request,
                **kwargs
            )

        headers = {
            'X-Platform-Id': 'dev_cdf1cfac242111ef9fdebe8d845d0987',
        }
        if method == 'POST' and idempotency_key:
            headers['X-Idempotency-Key'] = idempotency_key
        if not is_proxy_request and self.mercado_pago_access_token:
            headers['Authorization'] = f'Bearer {self.mercado_pago_access_token}'
        return headers

    def _parse_response_content(self, response, *, is_proxy_request=False, **kwargs):
        if self.code != 'mercado_pago' or not is_proxy_request:
            return super()._parse_response_content(response)
        return self._parse_proxy_response(response)

    def _parse_response_error(self, response):
        """Override of `payment` to parse the error message."""
        if self.code != 'mercado_pago':
            return super()._parse_response_error(response)
        return response.json().get('message', '')

    def _cron_refresh_token(self):
        self.ensure_one()

        proxy_payload = self._prepare_json_rpc_payload(
            {'mercado_pago_refresh_token': self.mercado_pago_refresh_token}
        )

        response_content = self._send_api_request(
            'POST',
            '/refresh_access_token',
            json=proxy_payload,
            is_proxy_request=True,
        )

        expires_in = (
            fields.Datetime.now()
            + timedelta(seconds=int(response_content['expires_in']))
            - timedelta(days=31)
        )
        self.write({
            'mercado_pago_access_token': response_content['access_token'],
            'mercado_pago_refresh_token': response_content['refresh_token'],
            'mercado_pago_access_token_expiry': expires_in,
        })
