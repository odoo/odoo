# Part of Odoo. See LICENSE file for full copyright and licensing details.

import hashlib
import hmac
import logging
import pprint
import uuid
from datetime import timedelta
from urllib.parse import urlencode

import requests

from odoo import _, fields, models
from odoo.exceptions import RedirectWarning, ValidationError
from odoo.http import request

from odoo.addons.payment_razorpay import const
from odoo.addons.payment_razorpay.controllers.onboarding import RazorpayController


_logger = logging.getLogger(__name__)


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(
        selection_add=[('razorpay', "Razorpay")], ondelete={'razorpay': 'set default'}
    )
    razorpay_key_id = fields.Char(
        string="Razorpay Key Id", help="The key solely used to identify the account with Razorpay."
    )
    razorpay_key_secret = fields.Char(string="Razorpay Key Secret", groups='base.group_system')
    razorpay_webhook_secret = fields.Char(
        string="Razorpay Webhook Secret", groups='base.group_system'
    )

    # OAuth fields
    razorpay_account_id = fields.Char(string="Razorpay Account ID", groups='base.group_system')
    razorpay_refresh_token = fields.Char(
        string="Razorpay Refresh Token", groups='base.group_system'
    )
    razorpay_public_token = fields.Char(string="Razorpay Public Token", groups='base.group_system')
    razorpay_access_token = fields.Char(string="Razorpay Access Token", groups='base.group_system')
    razorpay_access_token_expiry = fields.Datetime(
        string="Razorpay Access Token Expiry", groups='base.group_system'
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

    # === ACTIONS METHODS === #

    def action_razorpay_redirect_to_oauth_url(self):
        """ Redirect to the Razorpay OAuth URL.

        Note: `self.ensure_one()`

        :return: An URL action to redirect to the Razorpay OAuth URL.
        :rtype: dict
        """
        self.ensure_one()

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
            'return_url': f'{self.get_base_url()}{RazorpayController.OAUTH_RETURN_URL}',
            'provider_id': self.id,
            'csrf_token': request.csrf_token(),
        }
        authorization_url = f'{const.OAUTH_URL}/authorize?{urlencode(params)}'
        return {
            'type': 'ir.actions.act_url',
            'url': authorization_url,
            'target': 'self',
        }

    def action_razorpay_reset_oauth_account(self):
        """ Reset the Razorpay OAuth account.

        Note: self.ensure_one()

        :return: None
        """
        self.ensure_one()

        return self.write({
            'razorpay_account_id': None,
            'razorpay_public_token': None,
            'razorpay_refresh_token': None,
            'razorpay_access_token': None,
            'razorpay_access_token_expiry': None,
            'state': 'disabled',
            'is_published': False,
        })

    def action_razorpay_create_webhook(self):
        """ Create a webhook and display a toast notification.

        Note: `self.ensure_one()`

        :return: The feedback notification.
        :rtype: dict
        """
        self.ensure_one()

        webhook_secret = uuid.uuid4().hex  # Generate a random webhook secret.
        payload = {
            'url': f'{self.get_base_url()}/payment/razorpay/webhook',
            'alert_email': self.env.user.partner_id.email,
            'secret': webhook_secret,
            'events': const.HANDLED_WEBHOOK_EVENTS,
        }
        self._make_request(
            'POST',
            f'accounts/{self.razorpay_account_id}/webhooks',
            json_payload=payload,
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

    def _get_supported_currencies(self):
        """ Override of `payment` to return the supported currencies. """
        supported_currencies = super()._get_supported_currencies()
        if self.code == 'razorpay':
            supported_currencies = supported_currencies.filtered(
                lambda c: c.name in const.SUPPORTED_CURRENCIES
            )
        return supported_currencies

    def _build_request_url(self, endpoint, *, api_version='v1', is_proxy_request=False, **kwargs):
        if self.code != 'razorpay':
            return super()._build_request_url(endpoint, **kwargs)
        if is_proxy_request:
            return f'{const.OAUTH_URL}{endpoint}'
        return f'https://api.razorpay.com/{api_version}/{endpoint}'

    def _prepare_request_headers(self, *, method=None, is_proxy_request=False, **kwargs):
        if self.code != 'razorpay':
            return super()._prepare_request_headers(method=method, **kwargs)
        headers = None
        if not is_proxy_request and self.razorpay_access_token:
            headers = {'Authorization': f'Bearer {self.razorpay_access_token}'}
        return headers

    def _prepare_request_auth(self, *, is_proxy_request=False, **kwargs):
        if self.code != 'razorpay':
            return super()._prepare_request_auth(is_proxy_request=is_proxy_request, **kwargs)
        auth = None
        if not is_proxy_request and self.razorpay_key_id:
            auth = (self.razorpay_key_id, self.razorpay_key_secret)
        return auth

    def _parse_response_error(self, response):
        if self.code != 'razorpay':
            return super()._parse_response_error(response)
        return response.json().get('error', {}).get('description', '')

    def _parse_response_content(self, response, *, is_proxy_request=False, **kwargs):
        if self.code != 'razorpay' or not is_proxy_request:
            return super()._parse_response_content(response)
        return self._parse_proxy_response(response)

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
        else:  # Notification data.
            secret = self.razorpay_webhook_secret
            if not secret:
                _logger.warning("Missing webhook secret; aborting signature calculation.")
                return None
            return hmac.new(secret.encode(), msg=data, digestmod=hashlib.sha256).hexdigest()

    def _get_default_payment_method_codes(self):
        """ Override of `payment` to return the default payment method codes. """
        default_codes = super()._get_default_payment_method_codes()
        if self.code != 'razorpay':
            return default_codes
        return const.DEFAULT_PAYMENT_METHOD_CODES

    def _get_validation_amount(self):
        """ Override of `payment` to return the amount for Razorpay validation operations.

        :return: The validation amount.
        :rtype: float
        """
        res = super()._get_validation_amount()
        if self.code != 'razorpay':
            return res

        return 1.0

    # === BUSINESS METHODS - OAUTH FLOW === #

    def _razorpay_refresh_access_token(self):
        """ Refresh the access token.

        Note: `self.ensure_one()`

        :return: dict
        """
        self.ensure_one()
        proxy_payload = self._prepare_proxy_request_payload(
            payload={'refresh_token': self.razorpay_refresh_token}
        )

        response_content = self._make_request(
            'POST',
            '/refresh_access_token',
            json_payload=proxy_payload,
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
