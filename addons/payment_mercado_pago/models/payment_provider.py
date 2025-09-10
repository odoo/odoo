# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
from datetime import timedelta
from urllib.parse import urlencode

from odoo import _, api, fields, models
from odoo.exceptions import RedirectWarning, ValidationError
from odoo.fields import Command
from odoo.http import request
from odoo.tools.urls import urljoin

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.const import REPORT_REASONS_MAPPING
from odoo.addons.payment.logging import get_payment_logger
from odoo.addons.payment_mercado_pago import const


_logger = get_payment_logger(__name__)


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(
        selection_add=[('mercado_pago', "Mercado Pago")], ondelete={'mercado_pago': 'set default'}
    )
    mercado_pago_account_country_id = fields.Many2one(
        string="Mercado Pago Account Country",
        help="The country of the Mercado Pago account. The currency will be updated to match the"
             " country of the Mercado Pago account.",
        comodel_name='res.country',
        inverse='_inverse_mercado_pago_account_country_id',
        domain=[('code', 'in', list(const.SUPPORTED_COUNTRIES))],
        required_if_provider='mercado_pago',
        copy=False,
    )
    # TODO anko remove in 19.1
    mercado_pago_is_oauth_supported = fields.Boolean(compute='_compute_mercado_pago_is_oauth_supported')

    # OAuth fields
    mercado_pago_access_token = fields.Char(
        string="Mercado Pago Access Token",
        copy=False,
        groups='base.group_system',
    )
    mercado_pago_access_token_expiry = fields.Datetime(
        string="Mercado Pago Access Token Expiry",
        copy=False,
        groups='base.group_system',
    )
    mercado_pago_refresh_token = fields.Char(
        string="Mercado Pago Refresh Token",
        copy=False,
        groups='base.group_system',
    )
    mercado_pago_public_key = fields.Char(
        string="Mercado Pago Public Key",
        copy=False,
        groups='base.group_system',
    )

    # === COMPUTE METHODS === #

    def _compute_feature_support_fields(self):
        """Override of `payment` to enable additional features."""
        super()._compute_feature_support_fields()
        self.filtered(lambda p: p.code == 'mercado_pago').update({
            'support_tokenization': True,
        })

    def _inverse_mercado_pago_account_country_id(self):
        for provider in self.filtered(
            lambda p: p.code == 'mercado_pago' and p.mercado_pago_account_country_id
        ):
            currency_code = const.CURRENCY_MAPPING.get(self.mercado_pago_account_country_id.code)
            currency = self.env['res.currency'].with_context(
                active_test=False,
            ).search([('name', '=', currency_code)], limit=1)
            provider.available_currency_ids = [Command.set(currency.ids)]

    def _compute_mercado_pago_is_oauth_supported(self):
        """Return current state of OAuth support by Odoo. To be removed in future versions."""
        self.mercado_pago_is_oauth_supported = False

    # === CONSTRAINT METHODS === #

    @api.constrains('state', 'mercado_pago_access_token')
    def _check_mercado_pago_credentials_are_set_before_enabling(self):
        """Check that the Mercado Pago credentials are valid when the provider is enabled.

        :raise ValidationError: If the Mercado Pago credentials are not set.
        """
        for provider in self.filtered(lambda p: p.code == 'mercado_pago' and p.state != 'disabled'):
            if not provider.mercado_pago_access_token:
                raise ValidationError(_(
                    "Mercado Pago credentials are missing. Click the \"Connect\" button to set up"
                    " your account."
                ))

    @api.constrains('allow_tokenization', 'mercado_pago_public_key')
    def _check_mercado_pago_credentials_are_set_before_allowing_tokenization(self):
        """Check that the OAuth credentials are valid when the tokenization is enabled.

        :raise ValidationError: If the Mercado Pago credentials are not valid.
        """
        if any(
            p.code == 'mercado_pago'
            and p.allow_tokenization
            and not p.mercado_pago_public_key
            for p in self
        ):
            raise ValidationError(_("Connect your account before enabling tokenization."))

    # === CRUD METHODS === #

    def _get_default_payment_method_codes(self):
        """ Override of `payment` to return the default payment method codes. """
        self.ensure_one()
        if self.code != 'mercado_pago':
            return super()._get_default_payment_method_codes()
        return const.DEFAULT_PAYMENT_METHOD_CODES

    # === ACTIONS METHODS === #

    def action_start_onboarding(self, menu_id=None):
        """Override of `payment` to redirect to the Mercado Pago OAuth URL.

        Note: `self.ensure_one()`

        :param int menu_id: The menu from which the onboarding is started, as an `ir.ui.menu` id.
        :return: An URL action to redirect to the Mercado Pago OAuth URL.
        :rtype: dict
        :raise RedirectWarning: If the company's currency is not supported.
        """
        self.ensure_one()

        if self.code != 'mercado_pago':
            return super().action_start_onboarding(menu_id=menu_id)

        if self.company_id.country_id.code not in const.SUPPORTED_COUNTRIES:
            raise RedirectWarning(
                _(
                    "Mercado Pago is not available in your country; please use another payment"
                    " provider."
                ),
                self.env.ref('payment.action_payment_provider').id,
                _("Other Payment Providers"),
            )

        if not self.mercado_pago_account_country_id:
            raise ValidationError(_("Set the account country before connecting the account."))

        # Encode the return URL parameters here rather than passing them in the 'state' parameter
        # from IAP, because Mercado Pago doesn't JSON dumps in that parameter.
        return_url_params = {
            'provider_id': self.id,
            'csrf_token': request.csrf_token(),
        }
        return_url = urljoin(self.get_base_url(), const.OAUTH_RETURN_ROUTE)
        proxy_url_params = {
            'return_url': f'{return_url}?{urlencode(return_url_params)}',
            'account_country_code': self.mercado_pago_account_country_id.code.lower(),
        }
        proxy_url = self._build_request_url('/authorize', is_proxy_request=True)
        return {
            'type': 'ir.actions.act_url',
            'url': f'{proxy_url}?{urlencode(proxy_url_params)}',
            'target': 'self',
        }

    def _get_reset_values(self):
        """Override of `payment` to supply the provider-specific credential values to reset."""
        if self.code != 'mercado_pago':
            return super()._get_reset_values()

        return {
            'mercado_pago_access_token': None,
            'mercado_pago_access_token_expiry': None,
            'mercado_pago_public_key': None,
            'mercado_pago_refresh_token': None,
            'allow_tokenization': False,  # The account must be connected to allow tokenization.
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
        """Return a serialized JSON of the values required to render the inline form.

        Note: `self.ensure_one()`

        :param int partner_id: The partner of the transaction, as a `res.partner` id.
        :return: The JSON serial of the inline form values.
        :rtype: str
        """
        self.ensure_one()

        partner = self.env['res.partner'].browse(partner_id).exists()
        inline_form_values = {
            'email': partner.email,
            'public_key': self.mercado_pago_public_key,
        }
        return json.dumps(inline_form_values)

    # === REQUEST HELPERS === #

    def _build_request_url(self, endpoint, *, is_proxy_request=False, **kwargs):
        """Override of `payment` to build the request URL."""
        if self.code != 'mercado_pago':
            return super()._build_request_url(endpoint, is_proxy_request=is_proxy_request, **kwargs)

        if is_proxy_request:
            return urljoin(f'{const.PROXY_URL}/1', endpoint)

        return urljoin('https://api.mercadopago.com', endpoint)

    def _build_request_headers(
        self,
        method,
        *args,
        idempotency_key=None,
        is_proxy_request=False,
        is_refresh_token_request=False,
        **kwargs,
    ):
        """Override of `payment` to build the request headers."""
        if self.code != 'mercado_pago':
            return super()._build_request_headers(
                method,
                *args,
                idempotency_key=idempotency_key,
                is_proxy_request=is_proxy_request,
                **kwargs,
            )

        headers = {
            'X-Platform-Id': 'dev_cdf1cfac242111ef9fdebe8d845d0987',
        }
        if method == 'POST' and idempotency_key:
            headers['X-Idempotency-Key'] = idempotency_key
        if not is_proxy_request and not is_refresh_token_request:
            access_token = self._mercado_pago_fetch_access_token()
            headers['Authorization'] = f'Bearer {access_token}'
        return headers

    def _mercado_pago_fetch_access_token(self):
        """Generate a new access token if it's expired, otherwise return the existing access token.

        Note: `self.ensure_one()`

        :return: A valid access token.
        :rtype: str
        :raise ValidationError: If the access token can not be fetched.
        """
        self.ensure_one()

        if (
            self.mercado_pago_access_token
            and (
                not self.mercado_pago_access_token_expiry  # Legacy access token
                or self.mercado_pago_access_token_expiry >= fields.Datetime.now()
            )
        ):
            return self.mercado_pago_access_token
        else:
            proxy_payload = self._prepare_json_rpc_payload(
                {
                    'refresh_token': self.mercado_pago_refresh_token,
                    'account_country_code': self.mercado_pago_account_country_id.code.lower(),
                }
            )
            response_content = self._send_api_request(
                'POST',
                '/refresh_access_token',
                json=proxy_payload,
                is_proxy_request=True,
                is_refresh_token_request=True,
            )
            expires_in = (
                fields.Datetime.now()
                + timedelta(seconds=int(response_content['expires_in']))
                - timedelta(days=31)
            )
            self.write({
                'mercado_pago_access_token': response_content['access_token'],
                'mercado_pago_access_token_expiry': expires_in,
                'mercado_pago_refresh_token': response_content['refresh_token'],
            })
            return self.mercado_pago_access_token

    def _parse_response_content(self, response, *, is_proxy_request=False, **kwargs):
        """Override of `payment` to parse the response content."""
        if self.code != 'mercado_pago' or not is_proxy_request:
            return super()._parse_response_content(
                response, is_proxy_request=is_proxy_request, **kwargs
            )
        return self._parse_proxy_response(response)

    def _parse_response_error(self, response):
        """Override of `payment` to parse the error message."""
        if self.code != 'mercado_pago':
            return super()._parse_response_error(response)
        return response.json().get('message', '')
