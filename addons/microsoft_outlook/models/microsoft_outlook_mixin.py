# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import hashlib
import hmac
import json
import logging
import time
import requests

from werkzeug.urls import url_encode, url_join

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError

_logger = logging.getLogger(__name__)


class MicrosoftOutlookMixin(models.AbstractModel):

    _name = 'microsoft.outlook.mixin'
    _description = 'Microsoft Outlook Mixin'

    _OUTLOOK_SCOPE = None
    _OUTLOOK_ENDPOINT = 'https://login.microsoftonline.com/common/oauth2/v2.0/'

    use_microsoft_outlook_service = fields.Boolean('Outlook Authentication')
    is_microsoft_outlook_configured = fields.Boolean('Is Outlook Credential Configured',
        compute='_compute_is_microsoft_outlook_configured')
    microsoft_outlook_refresh_token = fields.Char(string='Outlook Refresh Token',
        groups='base.group_system', copy=False)
    microsoft_outlook_access_token = fields.Char(string='Outlook Access Token',
        groups='base.group_system', copy=False)
    microsoft_outlook_access_token_expiration = fields.Integer(string='Outlook Access Token Expiration Timestamp',
        groups='base.group_system', copy=False)
    microsoft_outlook_uri = fields.Char(compute='_compute_outlook_uri', string='Authentication URI',
        help='The URL to generate the authorization code from Outlook', groups='base.group_system')

    @api.depends('use_microsoft_outlook_service')
    def _compute_is_microsoft_outlook_configured(self):
        Config = self.env['ir.config_parameter'].sudo()
        microsoft_outlook_client_id = Config.get_param('microsoft_outlook_client_id')
        microsoft_outlook_client_secret = Config.get_param('microsoft_outlook_client_secret')
        self.is_microsoft_outlook_configured = microsoft_outlook_client_id and microsoft_outlook_client_secret

    @api.depends('use_microsoft_outlook_service')
    def _compute_outlook_uri(self):
        Config = self.env['ir.config_parameter'].sudo()
        base_url = Config.get_param('web.base.url')
        microsoft_outlook_client_id = Config.get_param('microsoft_outlook_client_id')

        for record in self:
            if not record.id or not record.use_microsoft_outlook_service or not record.is_microsoft_outlook_configured:
                record.microsoft_outlook_uri = False
                continue

            record.microsoft_outlook_uri = url_join(self._OUTLOOK_ENDPOINT, 'authorize?%s' % url_encode({
                'client_id': microsoft_outlook_client_id,
                'response_type': 'code',
                'redirect_uri': url_join(base_url, '/microsoft_outlook/confirm'),
                'response_mode': 'query',
                # offline_access is needed to have the refresh_token
                'scope': 'offline_access %s' % self._OUTLOOK_SCOPE,
                'state': json.dumps({
                    'model': record._name,
                    'id': record.id,
                    'csrf_token': record._get_outlook_csrf_token(),
                })
            }))

    def open_microsoft_outlook_uri(self):
        """Open the URL to accept the Outlook permission.

        This is done with an action, so we can force the user the save the form.
        We need him to save the form so the current mail server record exist in DB, and
        we can include the record ID in the URL.
        """
        self.ensure_one()

        if not self.env.user.has_group('base.group_system'):
            raise AccessError(_('Only the administrator can link an Outlook mail server.'))

        if not self.use_microsoft_outlook_service or not self.is_microsoft_outlook_configured:
            raise UserError(_('Please configure your Outlook credentials.'))

        return {
            'type': 'ir.actions.act_url',
            'url': self.microsoft_outlook_uri,
        }

    def _fetch_outlook_refresh_token(self, authorization_code):
        """Request the refresh token and the initial access token from the authorization code.

        :return:
            refresh_token, access_token, access_token_expiration
        """
        response = self._fetch_outlook_token('authorization_code', code=authorization_code)
        return (
            response['refresh_token'],
            response['access_token'],
            int(time.time()) + response['expires_in'],
        )

    def _fetch_outlook_access_token(self, refresh_token):
        """Refresh the access token thanks to the refresh token.

        :return:
            access_token, access_token_expiration
        """
        response = self._fetch_outlook_token('refresh_token', refresh_token=refresh_token)
        return (
            response['access_token'],
            int(time.time()) + response['expires_in'],
        )

    def _fetch_outlook_token(self, grant_type, **values):
        """Generic method to request an access token or a refresh token.

        Return the JSON response of the Outlook API and manage the errors which can occur.

        :param grant_type: Depends the action we want to do (refresh_token or authorization_code)
        :param values: Additional parameters that will be given to the Outlook endpoint
        """
        Config = self.env['ir.config_parameter'].sudo()
        base_url = Config.get_param('web.base.url')
        microsoft_outlook_client_id = Config.get_param('microsoft_outlook_client_id')
        microsoft_outlook_client_secret = Config.get_param('microsoft_outlook_client_secret')

        response = requests.post(
            url_join(self._OUTLOOK_ENDPOINT, 'token'),
            data={
                'client_id': microsoft_outlook_client_id,
                'client_secret': microsoft_outlook_client_secret,
                'scope': 'offline_access %s' % self._OUTLOOK_SCOPE,
                'redirect_uri': url_join(base_url, '/microsoft_outlook/confirm'),
                'grant_type': grant_type,
                **values,
            },
            timeout=10,
        )

        if not response.ok:
            try:
                error_description = response.json()['error_description']
            except Exception:
                error_description = _('Unknown error.')
            raise UserError(_('An error occurred when fetching the access token. %s') % error_description)

        return response.json()

    def _generate_outlook_oauth2_string(self, login):
        """Generate a OAuth2 string which can be used for authentication.

        :param user: Email address of the Outlook account to authenticate
        :return: The SASL argument for the OAuth2 mechanism.
        """
        self.ensure_one()
        now_timestamp = int(time.time())
        if not self.microsoft_outlook_access_token \
           or not self.microsoft_outlook_access_token_expiration \
           or self.microsoft_outlook_access_token_expiration < now_timestamp:
            if not self.microsoft_outlook_refresh_token:
                raise UserError(_('Please login your Outlook mail server before using it.'))
            (
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

        return 'user=%s\1auth=Bearer %s\1\1' % (login, self.microsoft_outlook_access_token)

    def _get_outlook_csrf_token(self):
        """Generate a CSRF token that will be verified in `microsoft_outlook_callback`.

        This will prevent a malicious person to make an admin user disconnect the mail servers.
        """
        self.ensure_one()
        _logger.info('Microsoft Outlook: generate CSRF token for %s #%i', self._name, self.id)
        secret = self.env['ir.config_parameter'].sudo().get_param('database.secret')
        data = str((self.env.cr.dbname, 'microsoft_outlook_oauth', self._name, self.id))
        return hmac.new(secret.encode('utf-8'), data.encode('utf-8'), hashlib.sha256).hexdigest()
