# Part of Odoo. See LICENSE file for full copyright and licensing details.

import hashlib
import hmac
import uuid
from datetime import timedelta
from urllib.parse import urlencode

from odoo import _, api, fields, models, tools
from odoo.exceptions import RedirectWarning, ValidationError
from odoo.http import request

from odoo.addons.payment.logging import get_payment_logger
from odoo.addons.payment_razorpay import const
from odoo.addons.payment_razorpay.controllers.onboarding import RazorpayController


_logger = get_payment_logger(__name__)


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(
        selection_add=[('razorpay', "Razorpay")], ondelete={'razorpay': 'set default'}
    )
    razorpay_key_id = fields.Char(
        string="Razorpay Key Id",
        help="The key solely used to identify the account with Razorpay.",
        copy=False,
    )
    razorpay_key_secret = fields.Char(
        string="Razorpay Key Secret",
        copy=False,
        groups='base.group_system',
    )
    razorpay_webhook_secret = fields.Char(
        string="Razorpay Webhook Secret",
        copy=False,
        groups='base.group_system',
    )

    # OAuth fields
    razorpay_account_id = fields.Char(
        string="Razorpay Account ID",
        copy=False,
        groups='base.group_system',
    )
    razorpay_refresh_token = fields.Char(
        string="Razorpay Refresh Token",
        copy=False,
        groups='base.group_system',
    )
    razorpay_public_token = fields.Char(
        string="Razorpay Public Token",
        copy=False,
        groups='base.group_system',
    )
    razorpay_access_token = fields.Char(
        string="Razorpay Access Token",
        copy=False,
        groups='base.group_system',
    )
    razorpay_access_token_expiry = fields.Datetime(
        string="Razorpay Access Token Expiry",
        copy=False,
        groups='base.group_system',
    )

    # === COMPUTE METHODS === #

    def _compute_feature_support_fields(self):
        """ Override of `payment` to enable additional features. """
        super()._compute_feature_support_fields()
        self.filtered(lambda p: p.code == 'razorpay').update({
            'support_manual_capture': 'full_only',
            'support_refund': 'partial',
            'support_tokenization': True,
        })

    def _get_supported_currencies(self):
        """ Override of `payment` to return the supported currencies. """
        supported_currencies = super()._get_supported_currencies()
        if self.code == 'razorpay':
            supported_currencies = supported_currencies.filtered(
                lambda c: c.name in const.SUPPORTED_CURRENCIES
            )
        return supported_currencies

    # === CONSTRAINT METHODS === #

    @api.constrains('state')
    def _check_razorpay_credentials_are_set_before_enabling(self):
        """ Check that the Razorpay credentials are valid when the provider is enabled.

        :raise ValidationError: If the Razorpay credentials are not valid.
        """
        for provider in self.filtered(lambda p: p.code == 'razorpay' and p.state != 'disabled'):
            if not provider.razorpay_account_id:
                if not provider.razorpay_key_id or not provider.razorpay_key_secret:
                    raise ValidationError(_(
                        "Razorpay credentials are missing. Click the \"Connect\" button to set up"
                        " your account."
                    ))

    # === CRUD METHODS === #

    def _get_default_payment_method_codes(self):
        """ Override of `payment` to return the default payment method codes. """
        self.ensure_one()
        if self.code != 'razorpay':
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

        if self.code != 'razorpay':
            return super().action_start_onboarding(menu_id=menu_id)

        if self.company_id.currency_id.name not in const.SUPPORTED_CURRENCIES:
            raise RedirectWarning(
                _(
                    "Razorpay is not available in your country; please use another payment"
                    " provider."
                ),
                self.env.ref('payment.action_payment_provider').id,
                _("Other Payment Providers"),
            )

        params = {
            'return_url': tools.urls.urljoin(self.get_base_url(), RazorpayController.OAUTH_RETURN_URL),
            'provider_id': self.id,
            'csrf_token': request.csrf_token(),
        }
        authorization_url = f'{const.OAUTH_URL}/authorize?{urlencode(params)}'
        return {
            'type': 'ir.actions.act_url',
            'url': authorization_url,
            'target': 'self',
        }

    def _get_reset_values(self):
        """Override of `payment` to supply the provider-specific credential values to reset."""
        if self.code != 'razorpay':
            return super()._get_reset_values()

        return {
            'razorpay_account_id': None,
            'razorpay_public_token': None,
            'razorpay_refresh_token': None,
            'razorpay_access_token': None,
            'razorpay_access_token_expiry': None,
        }

    def action_razorpay_create_webhook(self):
        """ Create a webhook and display a toast notification.

        Note: `self.ensure_one()`

        :return: The feedback notification.
        :rtype: dict
        """
        self.ensure_one()

        webhook_secret = uuid.uuid4().hex  # Generate a random webhook secret.
        payload = {
            'url': tools.urls.urljoin(self.get_base_url(), '/payment/razorpay/webhook'),
            'alert_email': self.env.user.partner_id.email,
            'secret': webhook_secret,
            'events': const.HANDLED_WEBHOOK_EVENTS,
        }
        self._send_api_request(
            'POST',
            f'accounts/{self.razorpay_account_id}/webhooks',
            json=payload,
            api_version='v2',
        )
        self.razorpay_webhook_secret = webhook_secret

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'message': _("Your Razorpay webhook was successfully set up!"),
                'next': {'type': 'ir.actions.client', 'tag': 'soft_reload'},
            },
        }

    # === BUSINESS METHODS - PAYMENT FLOW === #

    def _get_validation_amount(self):
        """ Override of `payment` to return the amount for Razorpay validation operations.

        :return: The validation amount.
        :rtype: float
        """
        res = super()._get_validation_amount()
        if self.code != 'razorpay':
            return res

        return 1.0

    def _razorpay_calculate_signature(self, data, is_redirect=True):
        """ Compute the signature for the request's data according to the Razorpay documentation.

        See https://razorpay.com/docs/webhooks/validate-test#validate-webhooks.

        :param bytes data: The data to sign.
        :param bool is_redirect: Whether the data should be treated as redirect data or as coming
                                 from a webhook notification.
        :return: The calculated signature.
        :rtype: str
        """
        if is_redirect:
            secret = self.razorpay_key_secret
            signing_string = f'{data["razorpay_order_id"]}|{data["razorpay_payment_id"]}'
            return hmac.new(
                secret.encode(), msg=signing_string.encode(), digestmod=hashlib.sha256
            ).hexdigest()
        else:  # payment data
            secret = self.razorpay_webhook_secret
            if not secret:
                _logger.warning("Missing webhook secret; aborting signature calculation.")
                return None
            return hmac.new(secret.encode(), msg=data, digestmod=hashlib.sha256).hexdigest()

    # === BUSINESS METHODS - OAUTH FLOW === #

    def _razorpay_refresh_access_token(self):
        """ Refresh the access token.

        Note: `self.ensure_one()`

        :return: dict
        """
        self.ensure_one()
        proxy_payload = self._prepare_json_rpc_payload(
            {'refresh_token': self.razorpay_refresh_token}
        )

        response_content = self._send_api_request(
            'POST',
            '/refresh_access_token',
            json=proxy_payload,
            is_proxy_request=True,
        )
        if response_content.get('access_token'):
            expiry = fields.Datetime.now() + timedelta(seconds=int(response_content['expires_in']))
            self.write({
                'razorpay_public_token': response_content['public_token'],
                'razorpay_refresh_token': response_content['refresh_token'],
                'razorpay_access_token': response_content['access_token'],
                'razorpay_access_token_expiry': expiry,
            })

    # === REQUEST HELPERS === #

    def _build_request_url(self, endpoint, *, api_version='v1', is_proxy_request=False, **kwargs):
        if self.code != 'razorpay':
            return super()._build_request_url(
                endpoint, api_version=api_version, is_proxy_request=is_proxy_request, **kwargs
            )
        if is_proxy_request:
            return f'{const.OAUTH_URL}{endpoint}'
        return f'https://api.razorpay.com/{api_version}/{endpoint}'

    def _build_request_headers(self, *args, is_proxy_request=False, **kwargs):
        if self.code != 'razorpay':
            return super()._build_request_headers(
                *args, is_proxy_request=is_proxy_request, **kwargs
            )

        headers = None
        if not is_proxy_request and self.razorpay_access_token and not self.razorpay_key_id:
            if self.razorpay_access_token_expiry < fields.Datetime.now():
                self._razorpay_refresh_access_token()
            headers = {'Authorization': f'Bearer {self.razorpay_access_token}'}
        return headers

    def _build_request_auth(self, *, is_proxy_request=False, **kwargs):
        """Override of `payment` to build the request Auth."""
        if self.code != 'razorpay':
            return super()._build_request_auth(is_proxy_request=is_proxy_request, **kwargs)

        auth = tuple()
        if not is_proxy_request and self.razorpay_key_id:
            auth = (self.razorpay_key_id, self.razorpay_key_secret)
        return auth

    def _parse_response_error(self, response):
        if self.code != 'razorpay':
            return super()._parse_response_error(response)
        return response.json().get('error', {}).get('description', '')

    def _parse_response_content(self, response, *, is_proxy_request=False, **kwargs):
        if self.code != 'razorpay' or not is_proxy_request:
            return super()._parse_response_content(
                response, is_proxy_request=is_proxy_request, **kwargs
            )
        return self._parse_proxy_response(response)
