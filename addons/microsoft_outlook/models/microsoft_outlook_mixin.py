# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import logging
import time
import requests

from werkzeug.urls import url_encode

from odoo import _, api, fields, models, release
from odoo.exceptions import AccessError, UserError
from odoo.tools import hmac, email_normalize
from odoo.tools.urls import urljoin as url_join
from odoo.addons.google_gmail.tools import get_iap_error_message

_logger = logging.getLogger(__name__)

OUTLOOK_TOKEN_REQUEST_TIMEOUT = 5
OUTLOOK_TOKEN_VALIDITY_THRESHOLD = OUTLOOK_TOKEN_REQUEST_TIMEOUT + 5


class MicrosoftOutlookMixin(models.AbstractModel):
    _name = 'microsoft.outlook.mixin'

    _description = 'Microsoft Outlook Mixin'

    _OUTLOOK_SCOPE = None
    _DEFAULT_OUTLOOK_IAP_ENDPOINT = 'https://outlook.api.odoo.com'

    active = fields.Boolean(default=True)

    microsoft_outlook_refresh_token = fields.Char(string='Outlook Refresh Token',
        groups='base.group_system', copy=False)
    microsoft_outlook_access_token = fields.Char(string='Outlook Access Token',
        groups='base.group_system', copy=False)
    microsoft_outlook_access_token_expiration = fields.Integer(string='Outlook Access Token Expiration Timestamp',
        groups='base.group_system', copy=False)
    microsoft_outlook_uri = fields.Char(compute='_compute_outlook_uri', string='Authentication URI',
        help='The URL to generate the authorization code from Outlook', groups='base.group_system')

    def _compute_outlook_uri(self):
        Config = self.env['ir.config_parameter'].sudo()
        base_url = self.get_base_url()
        microsoft_outlook_client_id = Config.get_param('microsoft_outlook_client_id')
        microsoft_outlook_client_secret = Config.get_param('microsoft_outlook_client_secret')
        is_configured = microsoft_outlook_client_id and microsoft_outlook_client_secret

        for record in self:
            if not is_configured:
                record.microsoft_outlook_uri = False
                continue

            record.microsoft_outlook_uri = url_join(self._get_microsoft_endpoint(), 'authorize?%s' % url_encode({
                'client_id': microsoft_outlook_client_id,
                'response_type': 'code',
                'redirect_uri': url_join(base_url, '/microsoft_outlook/confirm'),
                'response_mode': 'query',
                # offline_access is needed to have the refresh_token
                'scope': f'openid email offline_access https://outlook.office.com/User.read {self._OUTLOOK_SCOPE}',
                'state': json.dumps({
                    'model': record._name,
                    'id': record.id,
                    'csrf_token': record._get_outlook_csrf_token(),
                }),
            }))

    def open_microsoft_outlook_uri(self):
        """Open the URL to accept the Outlook permission.

        This is done with an action, so we can force the user the save the form.
        We need him to save the form so the current mail server record exist in DB and
        we can include the record ID in the URL.
        """
        self.ensure_one()

        if not self.env.is_admin():
            raise AccessError(_('Only the administrator can link an Outlook mail server.'))

        email_normalized = email_normalize(self[self._email_field])

        if not email_normalized:
            raise UserError(_('Please enter a valid email address.'))

        Config = self.env['ir.config_parameter'].sudo()
        microsoft_outlook_client_id = Config.get_param('microsoft_outlook_client_id')
        microsoft_outlook_client_secret = Config.get_param('microsoft_outlook_client_secret')
        is_configured = microsoft_outlook_client_id and microsoft_outlook_client_secret

        if not is_configured:  # use IAP (see '/microsoft_outlook/iap_confirm')
            if release.version_info[-1] != 'e':
                raise UserError(_('Please configure your Outlook credentials.'))

            outlook_iap_endpoint = self.env['ir.config_parameter'].sudo().get_param(
                'mail.server.outlook.iap.endpoint',
                self._DEFAULT_OUTLOOK_IAP_ENDPOINT,
            )
            db_uuid = self.env['ir.config_parameter'].sudo().get_param('database.uuid')

            # final callback URL that will receive the token from IAP
            callback_params = url_encode({
                'model': self._name,
                'rec_id': self.id,
                'csrf_token': self._get_outlook_csrf_token(),
            })
            callback_url = url_join(self.get_base_url(), f'/microsoft_outlook/iap_confirm?{callback_params}')

            try:
                response = requests.get(
                    url_join(outlook_iap_endpoint, '/api/mail_oauth/1/outlook'),
                    params={'db_uuid': db_uuid, 'callback_url': callback_url},
                    timeout=OUTLOOK_TOKEN_REQUEST_TIMEOUT)
                response.raise_for_status()
            except requests.exceptions.RequestException as e:
                _logger.error('Can not contact IAP: %s.', e)
                raise UserError(_('Oops, we could not authenticate you. Please try again later.'))

            response = response.json()
            if 'error' in response:
                self._raise_iap_error(response['error'])

            # URL on IAP that will redirect to Outlook login page
            microsoft_outlook_uri = response['url']

        else:
            microsoft_outlook_uri = self.microsoft_outlook_uri

        if not microsoft_outlook_uri:
            raise UserError(_('Please configure your Outlook credentials.'))

        return {
            'type': 'ir.actions.act_url',
            'url': microsoft_outlook_uri,
            'target': 'self',
        }

    def _fetch_outlook_refresh_token(self, authorization_code):
        """Request the refresh token and the initial access token from the authorization code.

        :return:
            refresh_token, access_token, id_token, access_token_expiration
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
            response['id_token'],
            int(time.time()) + int(response['expires_in']),
        )

    def _fetch_outlook_token(self, grant_type, **values):
        """Generic method to request an access token or a refresh token.

        Return the JSON response of the Outlook API and manage the errors which can occur.

        :param grant_type: Depends the action we want to do (refresh_token or authorization_code)
        :param values: Additional parameters that will be given to the Outlook endpoint
        """
        Config = self.env['ir.config_parameter'].sudo()
        base_url = self.get_base_url()
        microsoft_outlook_client_id = Config.get_param('microsoft_outlook_client_id')
        microsoft_outlook_client_secret = Config.get_param('microsoft_outlook_client_secret')

        response = requests.post(
            url_join(self._get_microsoft_endpoint(), 'token'),
            data={
                'client_id': microsoft_outlook_client_id,
                'client_secret': microsoft_outlook_client_secret,
                'scope': f'openid email offline_access https://outlook.office.com/User.read {self._OUTLOOK_SCOPE}',
                'redirect_uri': url_join(base_url, '/microsoft_outlook/confirm'),
                'grant_type': grant_type,
                **values,
            },
            timeout=OUTLOOK_TOKEN_REQUEST_TIMEOUT,
        )

        if not response.ok:
            try:
                error_description = response.json()['error_description']
            except Exception:
                error_description = _('Unknown error.')
            raise UserError(_('An error occurred when fetching the access token. %s', error_description))

        return response.json()

    def _fetch_outlook_access_token_iap(self, refresh_token):
        """Fetch the access token using IAP.

        Make a HTTP request to IAP, that will make a HTTP request
        to the Outlook API and give us the result.

        :return:
            access_token, access_token_expiration
        """
        outlook_iap_endpoint = self.env['ir.config_parameter'].sudo().get_param(
            'mail.server.outlook.iap.endpoint',
            self.env['microsoft.outlook.mixin']._DEFAULT_OUTLOOK_IAP_ENDPOINT,
        )
        db_uuid = self.env['ir.config_parameter'].sudo().get_param('database.uuid')

        response = requests.get(
            url_join(outlook_iap_endpoint, '/api/mail_oauth/1/outlook_access_token'),
            params={'refresh_token': refresh_token, 'db_uuid': db_uuid},
            timeout=OUTLOOK_TOKEN_REQUEST_TIMEOUT,
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

    def _generate_outlook_oauth2_string(self, login):
        """Generate a OAuth2 string which can be used for authentication.

        :param login: Email address of the Outlook account to authenticate
        :return: The SASL argument for the OAuth2 mechanism.
        """
        self.ensure_one()
        now_timestamp = int(time.time())
        if not self.microsoft_outlook_access_token \
           or not self.microsoft_outlook_access_token_expiration \
           or self.microsoft_outlook_access_token_expiration - OUTLOOK_TOKEN_VALIDITY_THRESHOLD < now_timestamp:
            if not self.microsoft_outlook_refresh_token:
                raise UserError(_('Please connect with your Outlook account before using it.'))
            (
                self.microsoft_outlook_refresh_token,
                self.microsoft_outlook_access_token,
                _id_token,
                self.microsoft_outlook_access_token_expiration,
            ) = self._fetch_outlook_access_token(self.microsoft_outlook_refresh_token)
            _logger.info(
                'Microsoft Outlook: fetch new access token. It expires in %i minutes',
                (self.microsoft_outlook_access_token_expiration - now_timestamp) // 60)
        else:
            _logger.info(
                'Microsoft Outlook: reuse existing access token. It expires in %i minutes',
                (self.microsoft_outlook_access_token_expiration - now_timestamp) // 60)

        return 'user=%s\1auth=Bearer %s\1\1' % (login, self.microsoft_outlook_access_token)

    def _get_outlook_csrf_token(self):
        """Generate a CSRF token that will be verified in `microsoft_outlook_callback`.

        This will prevent a malicious person to make an admin user disconnect the mail servers.
        """
        self.ensure_one()
        _logger.info('Microsoft Outlook: generate CSRF token for %s #%i', self._name, self.id)
        return hmac(
            env=self.env(su=True),
            scope='microsoft_outlook_oauth',
            message=(self._name, self.id),
        )

    @api.model
    def _get_microsoft_endpoint(self):
        return self.env["ir.config_parameter"].sudo().get_param(
            'microsoft_outlook.endpoint',
            'https://login.microsoftonline.com/common/oauth2/v2.0/',
        )
