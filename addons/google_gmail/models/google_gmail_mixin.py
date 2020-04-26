# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import requests

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.translate import _

from odoo.addons.google_account.models.google_service import GOOGLE_TOKEN_ENDPOINT, TIMEOUT


class GoogleGmailMixin(models.AbstractModel):

    _name = 'google.gmail.mixin'
    _description = 'Google Gmail Mixin'

    is_gmail = fields.Boolean('Gmail Authentication')
    google_gmail_authorization_code = fields.Char(string='Authorization Code')
    google_gmail_refresh_token = fields.Char(string='Refresh Token')
    google_gmail_uri = fields.Char(compute='_compute_gmail_uri', string='URI', help='The URL to generate the authorization code from Google')

    @api.model
    def create(self, values):
        if values.get('google_gmail_authorization_code'):
            # Generate the refresh token
            values['google_gmail_refresh_token'] = self.env['google.service'].generate_refresh_token('gmail', values['google_gmail_authorization_code'])

        return super(GoogleGmailMixin, self).create(values)

    def write(self, values):
        if (
            values.get('google_gmail_authorization_code')
            and values.get('google_gmail_authorization_code') != self.google_gmail_authorization_code
        ):
            # Update the refresh token
            values['google_gmail_refresh_token'] = self.env['google.service'].generate_refresh_token('gmail', values['google_gmail_authorization_code'])

        return super(GoogleGmailMixin, self).write(values)

    @api.depends('google_gmail_authorization_code')
    def _compute_gmail_uri(self):
        google_gmail_uri = self.env['google.service']._get_google_token_uri('gmail', scope=self._get_google_scope())
        for server in self:
            server.google_gmail_uri = google_gmail_uri

    @api.model
    def _get_access_token(self, refresh_token):
        Config = self.env['ir.config_parameter'].sudo()
        user_is_admin = self.env.is_admin()

        google_gmail_client_id = Config.get_param('google_gmail_client_id')
        google_gmail_client_secret = Config.get_param('google_gmail_client_secret')

        if not google_gmail_client_id or not google_gmail_client_secret:
            raise UserError(
                _('Google Gmail is not yet configured.')
                if user_is_admin else
                _('Google Gmail is not yet configured. Please contact your administrator.')
            )

        if not refresh_token:
            raise UserError(
                _('The refresh token for authentication is not set.')
                if user_is_admin else
                _('Google Gmail is not yet configured. Please contact your administrator.')
            )

        try:
            result = requests.post(
                GOOGLE_TOKEN_ENDPOINT,
                data={
                    'client_id': google_gmail_client_id,
                    'client_secret': google_gmail_client_secret,
                    'refresh_token': refresh_token,
                    'grant_type': 'refresh_token',
                    'scope': self._get_google_scope(),
                },
                headers={'Content-type': 'application/x-www-form-urlencoded'},
                timeout=TIMEOUT,
            )
            result.raise_for_status()
        except requests.HTTPError:
            if user_is_admin:
                raise UserError(_('Something went wrong during the token generation. Please request again an authorization code .'))
            else:
                raise UserError(_('Google Gmail is not yet configured. Please contact your administrator.'))

        return result.json().get('access_token')

    def _get_google_scope(self):
        return 'https://mail.google.com/'

    def _generate_oauth2_string(self, user, refresh_token):
        """Generate a OAuth2 string which can be used for authentication.

        :param user: Email address of the Gmail account to authenticate
        :param refresh_token: Refresh token for the given Gmail account

        :return: The SASL argument for the OAuth2 mechanism.
        """
        access_token = self._get_access_token(refresh_token)
        return f'user={user}\1auth=Bearer {access_token}\1\1'
