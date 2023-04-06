# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import time
import requests

from odoo import _, api, fields, tools, models
from odoo.exceptions import UserError

from werkzeug.urls import url_join

_logger = logging.getLogger(__name__)


class MicrosoftOutlookToken(models.Model):
    """Represent an Outlook OAuth token.

    This model is useful to share token between the outgoing mail servers and the
    incoming mail servers. That way, the user can login only once to configure
    both servers.
    """

    _name = 'microsoft.outlook.token'
    _description = 'Microsoft Outlook Token'
    _rec_name = 'email'

    _SCOPES = (
        'https://outlook.office.com/SMTP.Send',
        'https://outlook.office.com/IMAP.AccessAsUser.All',
    )
    _OUTLOOK_ENDPOINT = 'https://login.microsoftonline.com/common/oauth2/v2.0/'

    email = fields.Char(string='Email', required=True, readonly=True)
    microsoft_outlook_refresh_token = fields.Char(
        string='Outlook Refresh Token', copy=False, required=True)
    microsoft_outlook_access_token = fields.Char(
        string='Outlook Access Token', copy=False)
    microsoft_outlook_access_token_expiration = fields.Integer(
        string='Outlook Access Token Expiration Timestamp', copy=False)

    _unique_email_outlook_token = models.Constraint('UNIQUE(email)', 'Only one token per account')

    def _search_or_create(self, email, values):
        # update existing token or create a new one
        email = tools.email_normalize(email)
        token = self.search([('email', '=', email)], limit=1)
        if token:
            token.write(values)
            return token

        return self.create({'email': email, **values})

    def _fetch_outlook_refresh_token(self, authorization_code):
        """Request the refresh token and the initial access token from the authorization code.

        :return:
            refresh_token, access_token, access_token_expiration
        """
        response = self._fetch_outlook_token('authorization_code', code=authorization_code)
        return (
            response['refresh_token'],
            response['access_token'],
            int(time.time()) + int(response['expires_in']),
        )

    def _fetch_outlook_access_token(self, refresh_token):
        """Refresh the access token thanks to the refresh token.

        :return:
            access_token, access_token_expiration
        """
        Config = self.env['ir.config_parameter'].sudo()
        microsoft_outlook_client_id = Config.get_param('microsoft_outlook_client_id')
        microsoft_outlook_client_secret = Config.get_param('microsoft_outlook_client_secret')
        if not microsoft_outlook_client_id or not microsoft_outlook_client_secret:
            return self._fetch_outlook_access_token_iap(refresh_token)

        response = self._fetch_outlook_token('refresh_token', refresh_token=refresh_token)
        return (
            response['refresh_token'],
            response['access_token'],
            int(time.time()) + int(response['expires_in']),
        )

    def _fetch_outlook_access_token_iap(self, refresh_token):
        """Fetch the access token using IAP.

        Make a HTTP request to IAP, that will make a HTTP request
        to the Outlook API and give us the result.

        :return:
            access_token, access_token_expiration
        """
        outlook_iap_endpoint = self.env['ir.config_parameter'].sudo().get_param(
            'mail.outlook_iap_endpoint',
            self.env['microsoft.outlook.mixin']._DEFAULT_OUTLOOK_IAP_ENDPOINT,
        )
        db_uuid = self.env['ir.config_parameter'].sudo().get_param('database.uuid')

        response = requests.get(
            url_join(outlook_iap_endpoint, '/iap/mail_oauth/outlook_access_token'),
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

    def _fetch_outlook_token(self, grant_type, **values):
        """Generic method to request an access token or a refresh token.

        Return the JSON response of the Outlook API and manage the errors which can occur.

        :param grant_type: Depends on the action we want to do (refresh_token or authorization_code)
        :param values: Additional parameters that will be given to the Outlook endpoint
        """
        Config = self.env['ir.config_parameter'].sudo()
        base_url = self.get_base_url()
        microsoft_outlook_client_id = Config.get_param('microsoft_outlook_client_id')
        microsoft_outlook_client_secret = Config.get_param('microsoft_outlook_client_secret')

        response = requests.post(
            url_join(self.env['microsoft.outlook.mixin']._get_microsoft_endpoint(), 'token'),
            data={
                'client_id': microsoft_outlook_client_id,
                'client_secret': microsoft_outlook_client_secret,
                'scope': f'offline_access {" ".join(self._SCOPES)}',
                'redirect_uri': url_join(base_url, '/microsoft_outlook/confirm'),
                'grant_type': grant_type,
                **values,
            },
            timeout=10,
        )

        if not response.ok:
            try:
                error_description = response.json()['error_description']
            except (requests.exceptions.JSONDecodeError, KeyError):
                error_description = _('Unknown error.')
            raise UserError(_('An error occurred when fetching the access token. %s', error_description))

        return response.json()

    def _generate_outlook_oauth2_string(self):
        """Generate a OAuth2 string which can be used for authentication.

        :return: The SASL argument for the OAuth2 mechanism.
        """
        self.ensure_one()
        now_timestamp = int(time.time())
        if not self.microsoft_outlook_access_token \
           or not self.microsoft_outlook_access_token_expiration \
           or self.microsoft_outlook_access_token_expiration < now_timestamp:
            if not self.microsoft_outlook_refresh_token:
                raise UserError(_('Please connect with your Outlook account before using it.'))
            (
                self.microsoft_outlook_refresh_token,
                self.microsoft_outlook_access_token,
                self.microsoft_outlook_access_token_expiration,
            ) = self._fetch_outlook_access_token(self.microsoft_outlook_refresh_token)
            _logger.info(
                'Microsoft Outlook: fetch new access token. It expires in %i minutes',
                (self.microsoft_outlook_access_token_expiration - now_timestamp) // 60)
        else:
            _logger.info(
                'Microsoft Outlook: reuse existing access token. It expires in %i minutes',
                (self.microsoft_outlook_access_token_expiration - now_timestamp) // 60)

        return f'user={self.email}\1auth=Bearer {self.microsoft_outlook_access_token}\1\1'

    @api.autovacuum
    def _gc_microsoft_outlook_token(self):
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
        tokens = self.env['microsoft.outlook.token'].search(
            [('email', 'not in', list(all_emails))])
        _logger.info('Remove %i unused Outlook tokens', len(tokens))
        tokens.unlink()

    @api.model
    def _get_microsoft_endpoint(self):
        return self.env['ir.config_parameter'].sudo().get_param(
            'microsoft_outlook.endpoint',
            'https://login.microsoftonline.com/common/oauth2/v2.0/',
        )
