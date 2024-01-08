# Part of Odoo. See LICENSE file for full copyright and licensing details.

import hashlib
import hmac
import logging
import pprint
import secrets
import string
import requests

from werkzeug.urls import url_join, url_encode
from odoo.addons.iap.tools import iap_tools
from datetime import timedelta

from odoo import _, api, exceptions, fields, models
from odoo.exceptions import ValidationError, UserError

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
        required_if_provider='razorpay or not razorpay_public_token',
    )
    razorpay_key_secret = fields.Char(
        string="Razorpay Key Secret",
        required_if_provider='razorpay or not razorpay_public_token',
        groups='base.group_system',
    )
    razorpay_webhook_secret = fields.Char(
        string="Razorpay Webhook Secret",
        required_if_provider='razorpay or not razorpay_public_token',
        groups='base.group_system',
    )
    # Use for OAuth
    razorpay_authorization_code = fields.Char(string='Authorization Code', groups='base.group_system', copy=False, readonly=True)
    razorpay_authorization_state = fields.Char(string='Authorization State', groups='base.group_system', copy=False, readonly=True)
    razorpay_public_token = fields.Char(string='Public Token', groups='base.group_system', copy=False, readonly=True)
    razorpay_refresh_token = fields.Char(string='Refresh Token', groups='base.group_system', copy=False, readonly=True)
    razorpay_access_token = fields.Char(string='Access Token', groups='base.group_system', copy=False, readonly=True)
    razorpay_access_token_expiration = fields.Datetime(string='Access Token Expiration', groups='base.group_system', copy=False, readonly=True)
    razorpay_account_id = fields.Char(string="Customer Account ID", copy=False, readonly=True)
    razorpay_webhook_id = fields.Char(string="Webhook ID", copy=False, readonly=True)

    _sql_constraints = [
        ('unique_razorpay_authorization_state', 'UNIQUE(razorpay_authorization_state)', 'Authorization State must be unique!'),
        ('unique_razorpay_authorization_code', 'UNIQUE(razorpay_authorization_code)', 'Authorization Code must be unique!'),
    ]

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

    def _get_razorpay_oauth_url(self):
        """ Get the OAuth URL for Razorpay.

        :return: The OAuth URL.
        :rtype: str
        """
        OAUTH_TEST_URL = const.OAUTH_TEST_URL if 'state' == 'test' else const.OAUTH_URL
        return self.env['ir.config_parameter'].sudo().get_param('payment_razorpay.oauth_url', OAUTH_TEST_URL)

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

        use_oauth = bool(self.razorpay_access_token)
        if use_oauth:
            headers = {'Authorization': f'Bearer {self.razorpay_access_token}'}
        else:
            auth = (self.razorpay_key_id, self.razorpay_key_secret)
        try:
            if method == 'GET':
                response = requests.get(url, params=payload, headers=headers, auth=auth, timeout=10)
            else:
                response = requests.post(url, json=payload, headers=headers, auth=auth, timeout=10)
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
        response_json = response.json()
        return response_json

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
        return const.DEFAULT_PAYMENT_METHODS_CODES

    def _get_validation_amount(self):
        """ Override of `payment` to return the amount for Razorpay validation operations.

        :return: The validation amount.
        :rtype: float
        """
        res = super()._get_validation_amount()
        if self.code != 'razorpay':
            return res

        return 1.0

    def write(self, vals):
        res = super().write(vals)

        if 'state' in vals and vals['state'] == 'test':
            self._razorpay_provider_vals()

        if 'state' in vals and vals['state'] == 'enabled':
            self._check_account_activate()

        return res

    @api.onchange('state')
    def _onchange_state(self):
        if self.state == 'test':
            self._razorpay_provider_vals()

    def _razorpay_provider_vals(self):
        """ Create a vals

        :return: The razorpay provider
        :rtype: recordset of `payment.provider
        """
        self.write({
                'razorpay_access_token': False,
                'razorpay_refresh_token': False,
                'razorpay_access_token_expiration': False,
                'razorpay_public_token': False,
            })

    def _check_account_activate(self):

        self.ensure_one()

        if self.razorpay_account_id:
            dbuuid = self.env['ir.config_parameter'].sudo().get_param('database.uuid')
            request_url = url_join(self._get_razorpay_oauth_url(), '/iap/razorpay_proxy/v1/accounts')
            params = {
                'dbuuid': dbuuid,
                'account_id': self.razorpay_account_id,
            }
            try:
                response = iap_tools.iap_jsonrpc(request_url, params=params, timeout=60)
            except exceptions.AccessError:
                raise exceptions.UserError(
                    _('Something went wrong during activate accounts.')
                )
            if response.get('status' == 'activated'):
                self.write({
                    'state': 'enabled'
                })
        else:
            raise UserError(_('Please click on Connect Razorpay button to authorize your account'))

    def action_razorpay_connect_account(self):
        """ Create a Razorpay Connect account and redirect the user to the next onboarding step.
            If the provider is already enabled, close the current window. Otherwise, generate a Razorpay
            Connect onboarding link and redirect the user to it. If provided, the menu id is included in
            the URL the user is redirected to when coming back on Odoo after the onboarding. If the link
            generation failed, redirect the user to the provider form.

        :return: URL (The next step action)
        :rtype: str
        """
        self.ensure_one()
        if self.state == 'enabled':
            self.env['onboarding.onboarding.step'].action_validate_step_payment_provider()
            return {'type': 'ir.actions.act_window_close'}
        else:
            return {
                'type': 'ir.actions.act_url',
                'url': self._get_razorpay_authorize_url(),
                'target': 'self',
            }

    def _razorpay_generate_state(self):
        """ Generates a random string of 80 characters using the secrets module and the characters from ASCII letters and digits.
            This function might be useful for generating a secure state parameter,
            perhaps for use in authentication or authorization processes.

        return: str
        """
        return ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(80))

    def _get_razorpay_authorize_url(self):
        """ Generate the authorization URL for Razorpay integration.
            This function initiates the process of getting authorization for our application with Razorpay.
            The response will include state and code parameters. The generated URL includes necessary
            information such as state, scope, redirect_uri, request_url, and uuid.
            Note: This function relies on Razorpay's authorization flow.
            Note: Make sure to handle the response containing state and code appropriately.

        :return: The URL for authorization
        :rtype: dict
        """
        self.razorpay_authorization_state = self._razorpay_generate_state()
        IrConfigParameter_sudo = self.env['ir.config_parameter'].sudo()
        dbuuid = IrConfigParameter_sudo.get_param('database.uuid')
        oauth_url = self._get_razorpay_oauth_url()
        base_url = self.get_base_url()
        return url_join(oauth_url, 'iap/razorpay_proxy/v1/authorize?%s' % url_encode({
            'dbuuid': dbuuid,
            'state': self.razorpay_authorization_state,
            'redirect_url': base_url + '/payment/razorpay/oauth/callback',
        }))

    def cron_razorpay_refresh_token(self):
        """
            This cron job is designed to automatically refresh Razorpay access tokens for instances where the token is about to expire within the next day.
            It searches for records with the code 'razorpay', matching the provided refresh token, and with an access token expiration within the specified timeframe.
        """
        razorpay_need_refresh = self.search([
            ('code', '=', 'razorpay'),
            ('razorpay_refresh_token', '=', self.razorpay_refresh_token),
            ('razorpay_access_token_expiration', '<=', fields.Datetime.now() + timedelta(days=1))])
        for razorpay in razorpay_need_refresh:
            try:
                razorpay._razorpay_refresh_token()
                self.env.cr.commit()
            except exceptions.UserError as e:
                _logger.warning("Razorpay refresh token cron error %s", str(e))

    def _razorpay_refresh_token(self):
        """ Action to retrieve the refresh token URL for Razorpay.
            This action is used to trigger the process of refreshing the Razorpay access token. It returns
            an 'ir.actions.act_url' with the generated refresh token URL.
            Note: Make sure to handle the response containing the updated access token appropriately.

        :return: The action URL for refreshing the access token
        :rtype: dict
        """
        self.ensure_one()
        dbuuid = self.env['ir.config_parameter'].sudo().get_param('database.uuid')
        request_url = url_join(self._get_razorpay_oauth_url(), '/iap/razorpay_proxy/v1/get_refresh_token')
        params = {
            'dbuuid': dbuuid,
            'refresh_token': self.razorpay_refresh_token,
        }
        try:
            response = iap_tools.iap_jsonrpc(request_url, params=params, timeout=60)
        except exceptions.AccessError:
            raise exceptions.UserError(
                _('Something went wrong during refreshing the token.')
            )
        if response.get('error'):
            error = response['error']
            raise exceptions.UserError(
                _('Error :during refreshing token. %s', str(error))
            )
        if not response.get('access_token'):
            _logger.warning("Razorpay refresh token not found in responce %s", response)
            raise exceptions.UserError(
                _('New Token not exist in responce.')
            )
        expires_in = fields.Datetime.now() + timedelta(seconds=int(response.get('expires_in')))
        vals = {
            'razorpay_access_token': response.get('access_token'),
            'razorpay_public_token': response.get('public_token'),
            'razorpay_access_token_expiration': expires_in,
            'razorpay_refresh_token': response.get('refresh_token'),
        }
        self.write(vals)

    def action_razorpay_revoked_token(self):
        """ Action to revoke the Razorpay access token.
            This action is used to trigger the process of revoking the Razorpay access token. It returns
            an 'ir.actions.act_url' with the generated URL for revoking the access token.
            Note: After revocation, the access token will no longer be valid.

        :return: The action URL for revoking the access token
        :rtype: str
        """
        self.ensure_one()
        dbuuid = self.env['ir.config_parameter'].sudo().get_param('database.uuid')
        request_url = url_join(self._get_razorpay_oauth_url(), '/iap/razorpay_proxy/v1/revoked')
        params = {
            'dbuuid': dbuuid,
            'token_type_hint': "access_token",
            'access_token': self.razorpay_access_token,
        }
        is_successful = False
        try:
            self.razorpay_delete_webhook()
        except UserError as e:
            _logger.warning("Error on Delete webhook %s", str(e))
        try:
            response = iap_tools.iap_jsonrpc(request_url, params=params, timeout=60)
        except exceptions.AccessError:
            raise exceptions.UserError(
                _('Something went wrong during revoking the token.')
            )
        if response.get('message'):
            is_successful = True
            self.write({
                'razorpay_access_token': False,
                'razorpay_refresh_token': False,
                'razorpay_access_token_expiration': False,
                'razorpay_public_token': False,
                'state': 'disabled'
            })
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': is_successful and 'info' or 'warning',
                'sticky': False,
                'message': _("Revoked %s", is_successful and _("successful") or _("Not successful")),
                'next':{'type': 'ir.actions.client', 'tag': 'soft_reload'}
            }
        }

    def action_razorpay_create_and_update_webhook(self):
        """ This method is responsible for creating or updating the Razorpay webhook associated with the current Odoo instance.
            The webhook is crucial for updating payment states within Odoo when changes occur in Razorpay.

            If the base URL is modified, it is necessary to update the webhook to ensure seamless communication.
            The function constructs the necessary parameters and makes a request to create or update the webhook using the Razorpay API.

        """
        self.ensure_one()
        dbuuid = self.env['ir.config_parameter'].sudo().get_param('database.uuid')
        request_url = url_join(self._get_razorpay_oauth_url(), '/iap/razorpay_proxy/v1/create_webhook')
        params = {
            'dbuuid': dbuuid,
            'account_id': self.razorpay_account_id,
            'access_token': self.razorpay_access_token,
            'webhook_url': self.get_base_url() + '/payment/razorpay/webhook',
            'webhook_id': self.razorpay_webhook_id,
        }
        try:
            response = iap_tools.iap_jsonrpc(request_url, params=params, timeout=60)
        except exceptions.AccessError as e:
            _logger.exception("Something went wrong during creating the webhook. %s", str(e))
            raise UserError(_("Unable to connect with Razorpay"))
        if response.get('id'):
            self.write({
                'razorpay_webhook_secret': dbuuid,
                'razorpay_webhook_id': response['id'],
            })
        else:
            if response.get('error'):
                error = response['error']
                raise UserError(error.get('description', error.get('message', str(error))))
            _logger.exception("Unknown Error during creating the webhook. %s", str(response))
            raise UserError(_("Unknown Error"))
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'info',
                'message': _("Webhook update successful"),
                'next':{'type': 'ir.actions.client', 'tag': 'soft_reload'}
            }
        }

    def razorpay_delete_webhook(self):
        """ This method is designed to delete the Razorpay webhook associated with the current Odoo instance.
            The function constructs the necessary parameters and makes a request to the Razorpay API to delete the webhook.
        """
        self.ensure_one()
        dbuuid = self.env['ir.config_parameter'].sudo().get_param('database.uuid')
        request_url = url_join(self._get_razorpay_oauth_url(), '/iap/razorpay_proxy/v1/delete_webhook')
        params = {
            'dbuuid': dbuuid,
            'account_id': self.razorpay_account_id,
            'webhook_id': self.razorpay_webhook_id,
            'access_token': self.razorpay_access_token,
        }
        try:
            response = iap_tools.iap_jsonrpc(request_url, params=params, timeout=60)
        except exceptions.AccessError as e:
            _logger.exception("Something went wrong during creating the webhook. %s", str(e))
            raise UserError(_("Unable to connect with Razorpay"))
        if isinstance(response, dict) and response.get('error'):
            error = response['error']
            raise UserError(error.get('description', '') or error.get('message', str(error)))
        self.write({
            'razorpay_webhook_secret': False,
            'razorpay_webhook_id': False,
        })
