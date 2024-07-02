# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

import secrets
import string

from odoo import _, api, exceptions, fields, models
from werkzeug.urls import url_join, url_encode
from odoo.addons.iap.tools import iap_tools
from datetime import timedelta

from odoo.exceptions import UserError

from odoo.addons.payment_razorpay_oauth import const


_logger = logging.getLogger(__name__)


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    # Use for OAuth
    razorpay_authorization_state = fields.Char(string='Authorization State', groups='base.group_system', copy=False)
    razorpay_public_token = fields.Char(string='Public Token', groups='base.group_system', copy=False)
    razorpay_refresh_token = fields.Char(string='Refresh Token', groups='base.group_system', copy=False)
    razorpay_access_token = fields.Char(string='Access Token', groups='base.group_system', copy=False)
    razorpay_access_token_expiration = fields.Datetime(string='Access Token Expiration', groups='base.group_system', copy=False)
    razorpay_account_id = fields.Char(string="Customer Account ID", copy=False)
    razorpay_webhook_id = fields.Char(string="Webhook ID", copy=False)

    _sql_constraints = [
        ('unique_razorpay_authorization_state', 'UNIQUE(razorpay_authorization_state)', 'Authorization State must be unique!'),
    ]

    # === BASE METHODS ===#

    @api.onchange('state')
    def _onchange_state(self):
        for provider in self.filtered(lambda p: p.code == 'razorpay'):
            change_from_test = provider._origin.state == 'test' and (provider.state == 'disabled' or provider.state == 'enabled')
            if self.razorpay_public_token and (provider.state == 'test' or change_from_test):
                self.write({
                    'razorpay_access_token': False,
                    'razorpay_refresh_token': False,
                    'razorpay_access_token_expiration': False,
                    'razorpay_public_token': False,
                    'razorpay_key_id': False,
                    'razorpay_key_secret': False,
                    'razorpay_webhook_secret': False,
                })

    def _get_razorpay_oauth_url(self):
        """ Get the OAuth URL for Razorpay.
        :return: The OAuth URL.
        :rtype: str
        """
        self.ensure_one()
        OAUTH_URL = const.OAUTH_TEST_URL if self.state == 'test' else const.OAUTH_URL
        return self.env['ir.config_parameter'].sudo().get_param('payment_razorpay.oauth_url', OAUTH_URL)

    def _get_razorpay_access_token(self):
        super()._get_razorpay_access_token()
        return self.razorpay_access_token

    # === ONBOARDING APIS ===#

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
        return url_join(oauth_url, 'api/razorpay/1/authorize?%s' % url_encode({
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
        request_url = url_join(self._get_razorpay_oauth_url(), '/api/razorpay/1/get_refresh_token')
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
        request_url = url_join(self._get_razorpay_oauth_url(), '/api/razorpay/1/revoked')
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
        if response.get('message') or response.get('error').get('code') == 'http_error':
            is_successful = True
            self.write({
                'razorpay_access_token': False,
                'razorpay_refresh_token': False,
                'razorpay_access_token_expiration': False,
                'razorpay_public_token': False,
                'razorpay_key_id': False,
                'razorpay_key_secret': False,
                'razorpay_webhook_secret': False,
                'state': 'disabled'
            })
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': is_successful and 'info' or 'warning',
                'sticky': False,
                'message': _("Disconnected %s", is_successful and _("successfully") or _("Not successfully")),
                'next': {'type': 'ir.actions.client', 'tag': 'reload'}
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
        request_url = url_join(self._get_razorpay_oauth_url(), '/api/razorpay/1/create_webhook')
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
            raise UserError(_("Unable to connect with Razorpay. Razorpay gave us the following information: %s", str(e)))
        if response.get('id'):
            self.write({
                'razorpay_webhook_secret': dbuuid,
                'razorpay_webhook_id': response['id'],
            })
        else:
            error = response.get('error', {})
            if self.razorpay_webhook_id and error.get('code') == 'http_error':
                self.razorpay_webhook_id = False
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'type': 'warning',
                        'message': _("Can't update webhook because it's already deleted in Razorpay"),
                        'next': {'type': 'ir.actions.client', 'tag': 'reload'}
                    }
                }
            elif error.get('code') == 'http_error':
                _logger.exception("Error on connect with Razorpay %s", error.get('message', str(error)))
                raise UserError(_('Unable/Unauthorized to connect Razorpay.'))
            elif error:
                raise UserError(error.get('description', str(error)))
            _logger.exception("Unknown Error during creating the webhook. %s", str(response))
            raise UserError(_("Unknown Error"))
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'info',
                'message': _("Webhook successfully updated"),
                'next': {'type': 'ir.actions.client', 'tag': 'reload'}
            }
        }

    def razorpay_delete_webhook(self):
        """ This method is designed to delete the Razorpay webhook associated with the current Odoo instance.
            The function constructs the necessary parameters and makes a request to the Razorpay API to delete the webhook.
        """
        self.ensure_one()
        dbuuid = self.env['ir.config_parameter'].sudo().get_param('database.uuid')
        request_url = url_join(self._get_razorpay_oauth_url(), '/api/razorpay/1/delete_webhook')
        params = {
            'dbuuid': dbuuid,
            'account_id': self.razorpay_account_id,
            'webhook_id': self.razorpay_webhook_id,
            'access_token': self.razorpay_access_token,
        }
        try:
            response = iap_tools.iap_jsonrpc(request_url, params=params, timeout=60)
        except exceptions.AccessError as e:
            raise UserError(_("Unable to connect with Razorpay. Razorpay gave us the following information: %s", str(e)))
        if isinstance(response, dict) and response.get('error'):
            error = response['error']
            raise UserError(error.get('description', '') or error.get('message', str(error)))
        self.write({
            'razorpay_webhook_secret': False,
            'razorpay_webhook_id': False,
        })
