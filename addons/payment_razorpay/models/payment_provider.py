# Part of Odoo. See LICENSE file for full copyright and licensing details.

import hashlib
import hmac
import logging
import pprint
import requests
import uuid

from hashlib import sha1
from datetime import timedelta
from werkzeug.urls import url_join, url_encode

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError, UserError

from odoo.addons.iap.tools import iap_tools
from odoo.addons.payment_razorpay import const

_logger = logging.getLogger(__name__)


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(
        selection_add=[('razorpay', "Razorpay")], ondelete={'razorpay': 'set default'}
    )
    razorpay_key_id = fields.Char(
        string="Razorpay Key Id",
        help="The key solely used to identify the account with Razorpay.",
        copy=False
    )
    razorpay_key_secret = fields.Char(
        string="Razorpay Key Secret",
        groups='base.group_system',
        copy=False
    )
    razorpay_webhook_secret = fields.Char(
        string="Razorpay Webhook Secret",
        groups='base.group_system',
        copy=False
    )

    # Use for Oauth
    razorpay_access_token = fields.Char(
        string='Access Token',
        groups='base.group_system',
        copy=False
    )
    razorpay_access_token_expiration = fields.Datetime(
        string='Access Token Expiration',
        groups='base.group_system',
        copy=False
    )
    razorpay_account_id = fields.Char(
        string="Customer Account ID",
        copy=False
    )
    razorpay_refresh_token = fields.Char(
        string='Refresh Token',
        groups='base.group_system',
        copy=False
    )
    razorpay_public_token = fields.Char(
        string='Public Token',
        groups='base.group_system',
        copy=False
    )

    #=== COMPUTE METHODS ===#

    def _compute_feature_support_fields(self):
        """ Override of `payment` to enable additional features. """
        super()._compute_feature_support_fields()
        self.filtered(lambda p: p.code == 'razorpay').update({
            'support_manual_capture': 'full_only',
            'support_refund': 'partial',
            'support_tokenization': True,
        })

    # === BUSINESS METHODS ===#

    def _get_supported_currencies(self):
        """ Override of `payment` to return the supported currencies. """
        supported_currencies = super()._get_supported_currencies()
        if self.code == 'razorpay':
            supported_currencies = supported_currencies.filtered(
                lambda c: c.name in const.SUPPORTED_CURRENCIES
            )
        return supported_currencies

    def _razorpay_make_request(self, endpoint, payload=None, method='POST'):
        """ Make a request to Razorpay API at the specified endpoint.

        Note: self.ensure_one()

        :param str endpoint: The endpoint to be reached by the request.
        :param dict payload: The payload of the request.
        :param str method: The HTTP method of the request.
        :return The JSON-formatted content of the response.
        :rtype: dict
        :raise ValidationError: If an HTTP error occurs.
        """
        self.ensure_one()

        url = url_join('https://api.razorpay.com/v1/', endpoint)
        headers = {}
        auth = None
        if self.razorpay_access_token_expiration <= fields.Datetime.now():
            self._razorpay_refresh_token()
        if self.razorpay_access_token:
            headers = {'Authorization': f'Bearer {self.razorpay_access_token}'}
        else:
            auth = (self.razorpay_key_id, self.razorpay_key_secret)

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

    # -------------------------------------------------------------------------
    # ONCHANGE METHODS
    # -------------------------------------------------------------------------

    @api.onchange('state')
    def _onchange_state(self):
        if self.razorpay_public_token and self._origin.state != self.state:
            self.write({
                'razorpay_access_token': False,
                'razorpay_refresh_token': False,
                'razorpay_access_token_expiration': False,
                'razorpay_public_token': False,
                'razorpay_key_id': False,
                'razorpay_key_secret': False,
                'razorpay_webhook_secret': False,
            })

    # -------------------------------------------------------------------------
    # OAUTH ACTIONS
    # -------------------------------------------------------------------------

    def action_razorpay_redirect_to_oauth_url(self):
        """
        Redirect to the Razorpay Oauth url.

        :return: A url action with Razorpay Oauth url.
        :rtype: dict
        """
        self.ensure_one()
        dbuuid = self.env['ir.config_parameter'].sudo().get_param('database.uuid')
        oauth_url = self._razorpay_get_oauth_url()
        params = {
            'dbuuid': dbuuid,
            'state': self._razorpay_generate_authorization_state(),
            'id': self.id,
            'redirect_url': self.get_base_url() + '/payment/razorpay/oauth/callback',
        }
        authorization_url = url_join(
            oauth_url, 'api/razorpay/1/authorize?%s'
            % url_encode(params)
        )
        return {
            'type': 'ir.actions.act_url',
            'url': authorization_url,
            'target': 'self',
        }

    def _razorpay_generate_authorization_state(self):
        """
        Generate a random 80-character string for use as a secure state parameter.

        :return: Random string.
        :rtype: str
        """
        database_uuid = self.env['ir.config_parameter'].sudo().get_param('database.uuid')
        current_date = fields.Datetime.now()
        return sha1(f'{database_uuid}{self.id}{current_date}'.encode()).hexdigest()

    def _razorpay_get_oauth_url(self):
        """
        Return the Oauth url for Razorpay.

        :return: The Razorpay Oauth url.
        :rtype: str
        """
        self.ensure_one()
        OAUTH_URL = const.OAUTH_TEST_URL if self.state == 'test' else const.OAUTH_URL
        return self.env['ir.config_parameter'].sudo().get_param('payment_razorpay.oauth_url', OAUTH_URL)

    def action_razorpay_create_or_update_webhook(self):
        """
        Create or update the Razorpay webhook.
        This method sets up or updates the webhook in Razorpay to keep payment states synced with
        Odoo. It sends a request to the Razorpay API with the necessary parameters.
        """
        self.ensure_one()
        response = self._razorpay_generate_webhook()
        error = response.get('error', {})
        if error.get('code') == 'http_error':
            _logger.exception("Error on connect with Razorpay %s",
                error.get('message', str(error))
            )
            raise UserError(_('Unable/Unauthorized to connect Razorpay.'))
        elif error:
            raise UserError(error.get('description', str(error)))
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'info',
                'message': _("Webhook successfully updated"),
                'next': {'type': 'ir.actions.client', 'tag': 'soft_reload'},
            },
        }

    def _razorpay_generate_webhook(self):
        webhook_url = url_join(self._razorpay_get_oauth_url(), '/api/razorpay/1/create_webhook')
        self.razorpay_webhook_secret = uuid.uuid4().hex
        params = {
            'account_id': self.razorpay_account_id,
            'access_token': self.razorpay_access_token,
            'webhook_url': self.get_base_url() + '/payment/razorpay/webhook',
            'webhook_secret': self.razorpay_webhook_secret,
        }

        try:
            response = iap_tools.iap_jsonrpc(webhook_url, params=params, timeout=60)
        except AccessError as e:
            raise UserError(
                _("Unable to create and update webhook."
                "Razorpay gave us the following information: %s",
                str(e))
            )

        return response

    def action_razorpay_revoked_token(self):
        """
        Revoke the Razorpay access token.
        This method generates a URL to revoke the Razorpay access token.
        After revocation the token will no longer be valid.

        :return: URL for revoking the access token.
        :rtype: str
        """
        self.write({
            'razorpay_account_id': False,
            'razorpay_access_token': False,
            'razorpay_refresh_token': False,
            'razorpay_access_token_expiration': False,
            'razorpay_public_token': False,
            'razorpay_webhook_secret': False,
            'state': 'disabled',
        })
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'sticky': False,
                'message': _("Successfully Disconnected"),
                'next': {'type': 'ir.actions.client', 'tag': 'soft_reload'},
            },
        }

    def _razorpay_refresh_token(self):
        """
        Refresh the Razorpay access token.
        This method retrieves a new access token using the refresh token and updates the record with
        the new token details. It handles errors if the token cannot be refreshed.

        :return: dict
        """
        self.ensure_one()
        request_url = url_join(self._razorpay_get_oauth_url(), '/api/razorpay/1/get_refresh_token')
        params = {
            'refresh_token': self.razorpay_refresh_token,
        }
        try:
            response = iap_tools.iap_jsonrpc(request_url, params=params, timeout=60)
        except AccessError:
            raise UserError(
                _('Something went wrong during refreshing the token.')
            )
        if response.get('error'):
            _logger.warning("Error :during refreshing token. %s", str(response['error']))

        if not response.get('access_token'):
            _logger.warning("New Token not exist in response. %s", response)

        expires_in = fields.Datetime.now() + timedelta(seconds=int(response['expires_in']))
        self.write({
            'razorpay_access_token': response.get('access_token'),
            'razorpay_public_token': response.get('public_token'),
            'razorpay_access_token_expiration': expires_in,
            'razorpay_refresh_token': response.get('refresh_token'),
        })
