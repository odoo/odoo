# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import logging
import time
import requests

from werkzeug.urls import url_encode

from odoo import _, fields, models, tools, release
from odoo.exceptions import AccessError, UserError
from odoo.tools.urls import urljoin as url_join
from odoo.addons.google_gmail.tools import get_iap_error_message

GMAIL_TOKEN_REQUEST_TIMEOUT = 5

# seconds removed from end-of-validity datetime to take into account the time
# needed to renew the token and open the new smtp session
GMAIL_TOKEN_VALIDITY_THRESHOLD = GMAIL_TOKEN_REQUEST_TIMEOUT + 5

_logger = logging.getLogger(__name__)


class GoogleGmailMixin(models.AbstractModel):
    _name = 'google.gmail.mixin'

    _description = 'Google Gmail Mixin'

    # The scope `https://mail.google.com/` is needed for SMTP and IMAP
    # https://developers.google.com/workspace/gmail/imap/xoauth2-protocol
    _SERVICE_SCOPE = 'https://mail.google.com/ https://www.googleapis.com/auth/userinfo.email'
    _DEFAULT_GMAIL_IAP_ENDPOINT = 'https://gmail.api.odoo.com'

    active = fields.Boolean(default=True)

    google_gmail_refresh_token = fields.Char(string='Refresh Token', groups='base.group_system', copy=False)
    google_gmail_access_token = fields.Char(string='Access Token', groups='base.group_system', copy=False)
    google_gmail_access_token_expiration = fields.Integer(string='Access Token Expiration Timestamp', groups='base.group_system', copy=False)
    google_gmail_uri = fields.Char(compute='_compute_gmail_uri', string='URI', help='The URL to generate the authorization code from Google', groups='base.group_system')

    def _compute_gmail_uri(self):
        Config = self.env['ir.config_parameter'].sudo()
        google_gmail_client_id = Config.get_param('google_gmail_client_id')
        google_gmail_client_secret = Config.get_param('google_gmail_client_secret')
        is_configured = google_gmail_client_id and google_gmail_client_secret
        base_url = self.get_base_url()

        if not is_configured:
            self.google_gmail_uri = False
        else:
            for record in self:
                google_gmail_uri = 'https://accounts.google.com/o/oauth2/v2/auth?%s' % url_encode({
                    'client_id': google_gmail_client_id,
                    'redirect_uri': url_join(base_url, '/google_gmail/confirm'),
                    'response_type': 'code',
                    'scope': self._SERVICE_SCOPE,
                    # access_type and prompt needed to get a refresh token
                    'access_type': 'offline',
                    'prompt': 'consent',
                    'state': json.dumps({
                        'model': record._name,
                        'id': record.id or False,
                        'csrf_token': record._get_gmail_csrf_token() if record.id else False,
                    })
                })
                record.google_gmail_uri = google_gmail_uri

    def open_google_gmail_uri(self):
        """Open the URL to accept the Gmail permission.

        This is done with an action, so we can force the user the save the form.
        We need him to save the form so the current mail server record exist in DB, and
        we can include the record ID in the URL.
        """
        self.ensure_one()

        if not self.env.is_admin():
            raise AccessError(_('Only the administrator can link a Gmail mail server.'))

        email_normalized = tools.email_normalize(self[self._email_field])
        if not email_normalized:
            raise UserError(_('Please enter a valid email address.'))

        Config = self.env['ir.config_parameter'].sudo()
        google_gmail_client_id = Config.get_param('google_gmail_client_id')
        google_gmail_client_secret = Config.get_param('google_gmail_client_secret')
        is_configured = google_gmail_client_id and google_gmail_client_secret

        if not is_configured:  # use IAP (see '/google_gmail/iap_confirm')
            if release.version_info[-1] != 'e':
                raise UserError(_('Please configure your Gmail credentials.'))

            gmail_iap_endpoint = self.env['ir.config_parameter'].sudo().get_param(
                'mail.server.gmail.iap.endpoint',
                self._DEFAULT_GMAIL_IAP_ENDPOINT,
            )
            db_uuid = self.env['ir.config_parameter'].sudo().get_param('database.uuid')

            # final callback URL that will receive the token from IAP
            callback_params = url_encode({
                'model': self._name,
                'rec_id': self.id,
                'csrf_token': self._get_gmail_csrf_token(),
            })
            callback_url = url_join(self.get_base_url(), f'/google_gmail/iap_confirm?{callback_params}')

            iap_url = url_join(gmail_iap_endpoint, '/api/mail_oauth/1/gmail')
            try:
                response = requests.get(
                    iap_url,
                    params={'db_uuid': db_uuid, 'callback_url': callback_url},
                    timeout=GMAIL_TOKEN_REQUEST_TIMEOUT)
                response.raise_for_status()
            except requests.exceptions.RequestException as e:
                _logger.error('Can not contact IAP: %s.', e)
                raise UserError(_('Oops, we could not authenticate you. Please try again later.'))

            response = response.json()
            if 'error' in response:
                self._raise_iap_error(response['error'])

            # URL on IAP that will redirect to Gmail login page
            google_gmail_uri = response['url']

        else:
            google_gmail_uri = self.google_gmail_uri

        if not google_gmail_uri:
            raise UserError(_('Please configure your Gmail credentials.'))

        return {
            'type': 'ir.actions.act_url',
            'url': google_gmail_uri,
            'target': 'self',
        }

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

    def _fetch_gmail_token(self, grant_type, **values):
        """Generic method to request an access token or a refresh token.

        Return the JSON response of the GMail API and manage the errors which can occur.

        :param grant_type: Depends the action we want to do (refresh_token or authorization_code)
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
            timeout=GMAIL_TOKEN_REQUEST_TIMEOUT,
        )

        if not response.ok:
            raise UserError(_('An error occurred when fetching the access token.'))

        return response.json()

    def _fetch_gmail_access_token_iap(self, refresh_token):
        """Fetch the access token using IAP.

        Make a HTTP request to IAP, that will make a HTTP request
        to the Gmail API and give us the result.

        :return:
            access_token, access_token_expiration
        """
        gmail_iap_endpoint = self.env['ir.config_parameter'].sudo().get_param(
            'mail.server.gmail.iap.endpoint',
            self.env['google.gmail.mixin']._DEFAULT_GMAIL_IAP_ENDPOINT,
        )
        db_uuid = self.env['ir.config_parameter'].sudo().get_param('database.uuid')

        response = requests.get(
            url_join(gmail_iap_endpoint, '/api/mail_oauth/1/gmail_access_token'),
            params={'refresh_token': refresh_token, 'db_uuid': db_uuid},
            timeout=GMAIL_TOKEN_REQUEST_TIMEOUT,
        )

        if not response.ok:
            _logger.error('Can not contact IAP: %s.', response.text)
            raise UserError(_('Oops, we could not authenticate you. Please try again later.'))

        response = response.json()
        if 'error' in response:
            self._raise_iap_error(response['error'])

        return response

    def _raise_iap_error(self, error):
        raise UserError(get_iap_error_message(self.env, error))

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
           or self.google_gmail_access_token_expiration - GMAIL_TOKEN_VALIDITY_THRESHOLD < now_timestamp:

            access_token, expiration = self._fetch_gmail_access_token(self.google_gmail_refresh_token)

            self.write({
                'google_gmail_access_token': access_token,
                'google_gmail_access_token_expiration': expiration,
            })

            _logger.info(
                'Google Gmail: fetch new access token. Expires in %i minutes',
                (self.google_gmail_access_token_expiration - now_timestamp) // 60)
        else:
            _logger.info(
                'Google Gmail: reuse existing access token. Expire in %i minutes',
                (self.google_gmail_access_token_expiration - now_timestamp) // 60)

        return 'user=%s\1auth=Bearer %s\1\1' % (user, self.google_gmail_access_token)

    def _get_gmail_csrf_token(self):
        """Generate a CSRF token that will be verified in `google_gmail_callback`.

        This will prevent a malicious person to make an admin user disconnect the mail servers.
        """
        self.ensure_one()
        _logger.info('Google Gmail: generate CSRF token for %s #%i', self._name, self.id)
        return tools.misc.hmac(
            env=self.env(su=True),
            scope='google_gmail_oauth',
            message=(self._name, self.id),
        )
