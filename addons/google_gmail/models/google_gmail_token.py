# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import time
import requests

from werkzeug.urls import url_join

from odoo import _, api, fields, models, tools
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class GoogleGmailToken(models.Model):
    """Represent a Gmail token.

    The token can be used for an outgoing mail server, for an incoming mail server or
    for both mail servers type at once. That way, the user can login only once
    and connect both incoming and outgoing mail server.
    """

    _name = 'google.gmail.token'
    _description = 'Google Gmail Token'
    _rec_name = 'email'

    email = fields.Char('Email', required=True, readonly=True)
    google_gmail_refresh_token = fields.Char(
        string='Refresh Token', groups='base.group_system', copy=False, required=True)
    google_gmail_access_token = fields.Char(
        string='Access Token', groups='base.group_system', copy=False)
    google_gmail_access_token_expiration = fields.Integer(
        string='Access Token Expiration Timestamp',
        groups='base.group_system',
        copy=False,
    )

    _unique_email_gmail_token = models.Constraint('UNIQUE(email)', 'Only one token per account')

    def _search_or_create(self, email, values):
        # update existing token or create a new one
        email = tools.email_normalize(email)
        token = self.search([('email', '=', email)], limit=1)
        if token:
            token.write(values)
            return token

        return self.create({'email': email, **values})

    def _fetch_gmail_refresh_token(self, authorization_code):
        """Request the refresh token and the initial access token from the authorization code.

        :return:
            refresh_token, access_token, access_token_expiration
        """
        response = self._fetch_gmail_token('authorization_code', code=authorization_code)

        return (
            response['refresh_token'],
            response['access_token'],
            int(time.time()) + response['expires_in'],
        )

    def _fetch_gmail_access_token(self, refresh_token):
        """Refresh the access token thanks to the refresh token.

        :return:
            access_token, access_token_expiration
        """
        Config = self.env['ir.config_parameter'].sudo()
        google_gmail_client_id = Config.get_param('google_gmail_client_id')
        google_gmail_client_secret = Config.get_param('google_gmail_client_secret')
        if not google_gmail_client_id or not google_gmail_client_secret:
            return self._fetch_gmail_access_token_iap(refresh_token)

        response = self._fetch_gmail_token('refresh_token', refresh_token=refresh_token)
        return (
            response['access_token'],
            int(time.time()) + response['expires_in'],
        )

    def _fetch_gmail_access_token_iap(self, refresh_token):
        """Fetch the access token using IAP.

        Make a HTTP request to IAP, that will make a HTTP request
        to the Gmail API and give us the result.

        :return:
            access_token, access_token_expiration
        """
        gmail_iap_endpoint = self.env['ir.config_parameter'].sudo().get_param(
            'mail.gmail_iap_endpoint',
            self.env['google.gmail.mixin']._DEFAULT_GMAIL_IAP_ENDPOINT,
        )
        db_uuid = self.env['ir.config_parameter'].sudo().get_param('database.uuid')

        response = requests.get(
            url_join(gmail_iap_endpoint, '/iap/mail_oauth/gmail_access_token'),
            params={'refresh_token': refresh_token, 'db_uuid': db_uuid},
            timeout=3,
        )

        if not response.ok:
            _logger.error('Can not contact IAP: %s.', response.text)
            raise UserError(_('Can not contact IAP.'))

        response = response.json()
        if 'error' in response:
            raise UserError(_('An error occurred: %s.', response['error']))

        return response

    def _fetch_gmail_token(self, grant_type, **values):
        """Generic method to request an access token or a refresh token.

        Return the JSON response of the GMail API and manage the errors which can occur.

        :param grant_type: Depends on the action we want to do (refresh_token or authorization_code)
        :param values: Additional parameters that will be given to the GMail endpoint
        """
        Config = self.env['ir.config_parameter'].sudo()
        google_gmail_client_id = Config.get_param('google_gmail_client_id')
        google_gmail_client_secret = Config.get_param('google_gmail_client_secret')
        base_url = self.get_base_url()
        redirect_uri = url_join(base_url, '/google_gmail/confirm')

        response = requests.post(
            'https://oauth2.googleapis.com/token',
            data={
                'client_id': google_gmail_client_id,
                'client_secret': google_gmail_client_secret,
                'grant_type': grant_type,
                'redirect_uri': redirect_uri,
                **values,
            },
            timeout=5,
        )

        if not response.ok:
            raise UserError(_('An error occurred when fetching the access token.'))

        return response.json()

    def _generate_oauth2_string(self):
        """Generate a OAuth2 string which can be used for authentication.

        :return: The SASL argument for the OAuth2 mechanism.
        """
        self.ensure_one()
        now_timestamp = int(time.time())
        if (
            not self.google_gmail_access_token
            or not self.google_gmail_access_token_expiration
            or self.google_gmail_access_token_expiration < now_timestamp
        ):
            access_token, expiration = self._fetch_gmail_access_token(self.google_gmail_refresh_token)

            self.write({
                'google_gmail_access_token': access_token,
                'google_gmail_access_token_expiration': expiration,
            })

            _logger.info(
                'Google Gmail: fetch new access token. Expires in %i minutes',
                (self.google_gmail_access_token_expiration - now_timestamp) // 60,
            )
        else:
            _logger.info(
                'Google Gmail: reuse existing access token. Expire in %i minutes',
                (self.google_gmail_access_token_expiration - now_timestamp) // 60,
            )

        return f'user={self.email}\1auth=Bearer {self.google_gmail_access_token}\1\1'

    @api.autovacuum
    def _gc_google_gmail_token(self):
        """Remove the old tokens if they are not used anymore.

        Because the tokens are shared across multiple models, when we change the token
        (because we changed the email address, the server type, etc), we need to check
        if the old token is still used by the others models, and if not we need to remove it.
        """
        MODELS = ('ir.mail_server', 'fetchmail.server')
        all_emails = set()
        for model in MODELS:
            email_field = self.env[model]._email_field
            values = self.env[model].search_read([(email_field, '!=', False)], [email_field])
            all_emails |= {tools.email_normalize(val[email_field]) for val in values}
        tokens = self.env['google.gmail.token'].search(
            [('email', 'not in', list(all_emails))])
        _logger.info('Remove %i unused Gmail tokens', len(tokens))
        tokens.unlink()
