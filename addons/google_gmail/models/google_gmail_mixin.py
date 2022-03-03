# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import time

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class GoogleGmailMixin(models.AbstractModel):

    _name = 'google.gmail.mixin'
    _description = 'Google Gmail Mixin'

    _SERVICE_SCOPE = 'https://mail.google.com/'

    use_google_gmail_service = fields.Boolean('Gmail Authentication')
    google_gmail_authorization_code = fields.Char(string='Authorization Code', groups='base.group_system', copy=False)
    google_gmail_refresh_token = fields.Char(string='Refresh Token', groups='base.group_system', copy=False)
    google_gmail_access_token = fields.Char(string='Access Token', groups='base.group_system', copy=False)
    google_gmail_access_token_expiration = fields.Integer(string='Access Token Expiration Timestamp', groups='base.group_system', copy=False)
    google_gmail_uri = fields.Char(compute='_compute_gmail_uri', string='URI', help='The URL to generate the authorization code from Google', groups='base.group_system')

    @api.depends('google_gmail_authorization_code')
    def _compute_gmail_uri(self):
        Config = self.env['ir.config_parameter'].sudo()
        google_gmail_client_id = Config.get_param('google_gmail_client_id')
        google_gmail_client_secret = Config.get_param('google_gmail_client_secret')

        if not google_gmail_client_id or not google_gmail_client_secret:
            self.google_gmail_uri = False
        else:
            google_gmail_uri = self.env['google.service']._get_google_token_uri('gmail', scope=self._SERVICE_SCOPE)
            self.google_gmail_uri = google_gmail_uri

    @api.model
    def create(self, values):
        if values.get('google_gmail_authorization_code'):
            # Generate the refresh token
            values['google_gmail_refresh_token'] = self.env['google.service'].generate_refresh_token(
                'gmail', values['google_gmail_authorization_code'])
            values['google_gmail_access_token'] = False
            values['google_gmail_access_token_expiration'] = False

        return super(GoogleGmailMixin, self).create(values)

    def write(self, values):
        authorization_code = values.get('google_gmail_authorization_code')
        if (
            authorization_code
            and not all(authorization_code == code for code in self.mapped('google_gmail_authorization_code'))
        ):
            # Update the refresh token
            values['google_gmail_refresh_token'] = self.env['google.service'].generate_refresh_token(
                'gmail', authorization_code)
            values['google_gmail_access_token'] = False
            values['google_gmail_access_token_expiration'] = False

        return super(GoogleGmailMixin, self).write(values)

    def _generate_oauth2_string(self, user, refresh_token):
        """Generate a OAuth2 string which can be used for authentication.

        :param user: Email address of the Gmail account to authenticate
        :param refresh_token: Refresh token for the given Gmail account

        :return: The SASL argument for the OAuth2 mechanism.
        """
        self.ensure_one()
        now_timestamp = int(time.time())
        if not self.google_gmail_access_token \
           or not self.google_gmail_access_token_expiration \
           or self.google_gmail_access_token_expiration < now_timestamp:
            self.google_gmail_access_token, expires_in = self.env['google.service']._get_access_token(
                refresh_token, 'gmail', self._SERVICE_SCOPE)
            self.google_gmail_access_token_expiration = now_timestamp + expires_in

            _logger.info('Google Gmail: fetch new access token. Expire in %i minutes', expires_in // 60)
        else:
            _logger.info(
                'Google Gmail: reuse existing access token. Expire in %i minutes',
                (self.google_gmail_access_token_expiration - now_timestamp) // 60)

        return 'user=%s\1auth=Bearer %s\1\1' % (user, self.google_gmail_access_token)
