# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class GoogleGmailMixin(models.AbstractModel):

    _name = 'google.gmail.mixin'
    _description = 'Google Gmail Mixin'

    _service_scope = 'https://mail.google.com/'

    google_gmail_authorization_code = fields.Char(string='Authorization Code', groups='base.group_system')
    google_gmail_refresh_token = fields.Char(string='Refresh Token', groups='base.group_system')
    google_gmail_uri = fields.Char(compute='_compute_gmail_uri', string='URI',
        help='The URL to generate the authorization code from Google')

    @api.depends('google_gmail_authorization_code')
    def _compute_gmail_uri(self):
        Config = self.env['ir.config_parameter'].sudo()
        google_gmail_client_id = Config.get_param('google_gmail_client_id')
        google_gmail_client_secret = Config.get_param('google_gmail_client_secret')

        if not google_gmail_client_id or not google_gmail_client_secret:
            self.google_gmail_uri = False
        else:
            self.google_gmail_uri = self.env['google.service']._get_google_token_uri(
                'gmail',
                scope=self._service_scope,
            )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('google_gmail_authorization_code'):
                # Generate the refresh token
                vals['google_gmail_refresh_token'] = self.env['google.service'].generate_refresh_token(
                    'gmail', vals['google_gmail_authorization_code'])

        return super(GoogleGmailMixin, self).create(vals_list)

    def write(self, values):
        authorization_code = values.get('google_gmail_authorization_code')
        if (
            authorization_code
            and not all(authorization_code == code for code in self.mapped('google_gmail_authorization_code'))
        ):
            # Update the refresh token
            values['google_gmail_refresh_token'] = self.env['google.service'].generate_refresh_token(
                'gmail', authorization_code)

        return super(GoogleGmailMixin, self).write(values)

    def _generate_oauth2_string(self, user, refresh_token):
        """Generate a OAuth2 string which can be used for authentication.

        :param user: Email address of the Gmail account to authenticate
        :param refresh_token: Refresh token for the given Gmail account

        :return: The SASL argument for the OAuth2 mechanism.
        """
        access_token = self.env['google.service']._get_access_token(refresh_token, 'gmail', self._service_scope)
        return f'user={user}\1auth=Bearer {access_token}\1\1'
