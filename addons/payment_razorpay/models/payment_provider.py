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
        _logger.info(
            "Sending '/accounts/%(account_id)s/webhooks' request:\n%(payload)s",
            {'account_id': self.razorpay_account_id, 'payload': pprint.pformat(payload)},
        )
        webhook_data = self._razorpay_make_request(
            f'accounts/{self.razorpay_account_id}/webhooks', payload=payload, api_version='v2'
        )
        _logger.info(
            "Response of '/accounts/%(account_id)s/webhooks' request:\n%(response)s",
            {'account_id': self.razorpay_account_id, 'response': pprint.pformat(webhook_data)},
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

    def _razorpay_make_request(self, endpoint, payload=None, method='POST', api_version='v1'):
        """ Make a request to Razorpay API at the specified endpoint.

        Note: self.ensure_one()

        :param str endpoint: The endpoint to be reached by the request.
        :param dict payload: The payload of the request.
        :param str method: The HTTP method of the request.
        :param str api_version: The version of the API to use.
        :return The JSON-formatted content of the response.
        :rtype: dict
        :raise ValidationError: If an HTTP error occurs.
        """
        self.ensure_one()
        url = f'https://api.razorpay.com/{api_version}/{endpoint}'
        headers = None
        if self.razorpay_access_token:
            headers = {'Authorization': f'Bearer {self.razorpay_access_token}'}
        auth = (self.razorpay_key_id, self.razorpay_key_secret) if self.razorpay_key_id else None
        try:
            if method == 'GET':
                response = requests.get(
                    url,
                    params=payload,
                    headers=headers,
                    auth=auth,
                    timeout=10,
                )
            else:
                response = requests.post(
                    url,
                    json=payload,
                    headers=headers,
                    auth=auth,
                    timeout=10,
                )
            try:
                response.raise_for_status()
            except requests.exceptions.HTTPError:
                _logger.exception(
                    "Invalid API request at %s with data:\n%s", url, pprint.pformat(payload),
                )
                raise ValidationError("Razorpay: " + _(
                    "Razorpay gave us the following information: '%s'",
                    response.json().get('error', {}).get('description')
                ))
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            _logger.exception("Unable to reach endpoint at %s", url)
            raise ValidationError(
                "Razorpay: " + _("Could not establish the connection to the API.")
            )
        return response.json()

    def _razorpay_calculate_signature(self, data):
        """ Compute the signature for the request's data according to the Razorpay documentation.

        See https://razorpay.com/docs/webhooks/validate-test#validate-webhooks.

        :param bytes data: The data to sign.
        :return: The calculated signature.
        :rtype: str
        """
        secret = self.razorpay_webhook_secret
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

    def _razorpay_make_proxy_request(self, endpoint, payload=None):
        """ Make a request to the Razorpay proxy at the specified endpoint.

        :param str endpoint: The proxy endpoint to be reached by the request; prefixed with '/'.
        :param dict payload: The payload of the request.
        :return: The JSON-formatted content of the response.
        :rtype: dict
        :raise ValidationError: If an HTTP error occurs.
        """
        proxy_payload = {
            'jsonrpc': '2.0',
            'id': uuid.uuid4().hex,
            'method': 'call',
            'params': payload,
        }
        url = f'{const.OAUTH_URL}{endpoint}'
        try:
            response = requests.post(url, json=proxy_payload, timeout=10)
            response.raise_for_status()
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            _logger.exception("Unable to reach endpoint at %s", url)
            raise ValidationError("Razorpay Proxy: " + _("Could not establish the connection."))
        except requests.exceptions.HTTPError:
            _logger.exception(
                "Invalid API request at %s with data %s", url, pprint.pformat(payload)
            )
            raise ValidationError(
                "Razorpay Proxy: " + _("An error occurred when communicating with the proxy.")
            )

        # Razorpay proxy endpoints always respond with HTTP 200 as they implement JSON-RPC 2.0.
        response_content = response.json()
        if response_content.get('error'):  # An exception was raised on the proxy side.
            error_message = response_content['error']['data']['message']
            _logger.exception("Request forwarded with error: %s", error_message)
            raise ValidationError(f"Razorpay Proxy: {error_message}")  # pylint: disable=missing-gettext

        return response_content['result']

    def _razorpay_refresh_access_token(self):
        """ Refresh the access token.

        Note: `self.ensure_one()`

        :return: dict
        """
        self.ensure_one()

        response_content = self._razorpay_make_proxy_request(
            '/refresh_access_token', payload={'refresh_token': self.razorpay_refresh_token}
        )
        if response_content.get('access_token'):
            expiry = fields.Datetime.now() + timedelta(seconds=int(response_content['expires_in']))
            self.write({
                'razorpay_public_token': response_content['public_token'],
                'razorpay_refresh_token': response_content['refresh_token'],
                'razorpay_access_token': response_content['access_token'],
                'razorpay_access_token_expiry': expiry,
            })
