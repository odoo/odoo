# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
import json
import logging

import requests
from werkzeug import urls

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)

TIMEOUT = 20

DEFAULT_MICROSOFT_AUTH_ENDPOINT = 'https://login.microsoftonline.com/common/oauth2/v2.0/authorize'
DEFAULT_MICROSOFT_TOKEN_ENDPOINT = 'https://login.microsoftonline.com/common/oauth2/v2.0/token'


class MicrosoftService(models.AbstractModel):
    _name = 'microsoft.service'
    _description = 'Microsoft Service'

    @api.model
    def _get_scope(self):
        """
        Get the scope of the Microsoft API authentication.
        Note: at the moment, only calendar access is configured. 
        """
        return 'offline_access openid Calendars.ReadWrite'

    @api.model
    def _get_base_url(self):
        """
        Get the Odoo instance base URL.
        """
        return self.env['ir.config_parameter'].sudo().get_param(
            'web.base.url', default='http://www.odoo.com?NoBaseUrl'
        )

    @api.model
    def _get_credentials(self):
        """
        Get Microsoft API credentials from settings.
        """
        Config = self.env['ir.config_parameter'].sudo()
        client_id = Config.get_param('microsoft_api_client_id')
        secret_id = Config.get_param('microsoft_api_client_secret')

        return client_id, secret_id

    @api.model
    def has_credentials_configured(self):
        """
        Indicates if API credentials are correctly configured
        """
        client_id, secret_id = self._get_credentials()
        return client_id and secret_id

    @api.model
    def can_set_credentials(self, user):
        """
        Indicates if the user can set Microsoft API credentials.
        """
        return user.has_group('base.group_erp_manager')

    @api.model
    def is_user_authenticated(self, user):
        """
        Indicates if the user is already authenticated to the Microsoft API with
        credentials set in Odoo settings.
        """
        return bool(user.sudo().microsoft_calendar_rtoken)

    @api.model
    def get_calendar_auth_url(self, from_url):
        """
        Return the full Microsoft Calendar URL for the authentication.
        """
        return self._get_authorize_url(
            from_url,
            service='calendar',
            scope=self._get_scope()
        )

    @api.model
    def _get_auth_endpoint(self):
        return self.env["ir.config_parameter"].sudo().get_param(
            'microsoft_account.auth_endpoint',
            DEFAULT_MICROSOFT_AUTH_ENDPOINT
        )

    @api.model
    def _get_token_endpoint(self):
        return self.env["ir.config_parameter"].sudo().get_param(
            'microsoft_account.token_endpoint',
            DEFAULT_MICROSOFT_TOKEN_ENDPOINT
        )

    @api.model
    def _get_authorize_url(self, from_url, service, scope):
        """
        Returns the URL needed to allow this Odoo instance to access to the 
        Microsoft scope specified as parameter.
        """
        state = {
            'd': self.env.cr.dbname,
            's': service,
            'f': from_url
        }
        client_id, _ = self._get_credentials()
        encoded_params = urls.url_encode({
            'response_type': 'code',
            'client_id': client_id,
            'state': json.dumps(state),
            'scope': scope,
            'redirect_uri': self._get_base_url() + '/microsoft_account/authentication',
            'prompt': 'consent',
            'access_type': 'offline'
        })
        return "%s?%s" % (self._get_auth_endpoint(), encoded_params)

    @api.model
    def _get_microsoft_tokens(self, authorize_code, service):
        """
        Call Microsoft API to exchange authorization code against token, with POST request, to not be redirected.
        """
        client_id, client_secret = self._get_credentials()

        headers = {"content-type": "application/x-www-form-urlencoded"}
        data = {
            'code': authorize_code,
            'client_id': client_id,
            'client_secret': client_secret,
            'grant_type': 'authorization_code',
            'scope': self._get_scope(),
            'redirect_uri': self._get_base_url() + '/microsoft_account/authentication'
        }
        try:
            _, res, _ = self._do_request(
                self._get_token_endpoint(), params=data, headers=headers, method='POST', preuri=''
            )
            return res.get('access_token'), res.get('refresh_token'), res.get('expires_in')
        except requests.HTTPError:
            raise self.env['res.config.settings'].get_config_warning(
                _("Something went wrong during your token generation. Maybe your Authorization Code is invalid")
            )

    @api.model
    def _do_request(
        self, uri, params=None, headers=None, method='POST', preuri="https://graph.microsoft.com", timeout=TIMEOUT
    ):
        """
        Execute the request to Microsoft API. Return a tuple ('HTTP_CODE', 'HTTP_RESPONSE')
        :param uri : the url to contact
        :param params : dict or already encoded parameters for the request to make
        :param headers : headers of request
        :param method : the method to use to make the request
        :param preuri : pre url to prepend to param uri.
        """
        if params is None:
            params = {}
        if headers is None:
            headers = {}

        _logger.debug("Uri: %s - Type : %s - Headers: %s - Params : %s !" % (uri, method, headers, params))

        ask_time = fields.Datetime.now()
        try:
            if method.upper() in ('GET', 'DELETE'):
                res = requests.request(method.lower(), preuri + uri, headers=headers, params=params, timeout=timeout)
            elif method.upper() in ('POST', 'PATCH', 'PUT'):
                res = requests.request(method.lower(), preuri + uri, data=params, headers=headers, timeout=timeout)
            else:
                raise Exception(_('Method not supported [%s] not in [GET, POST, PUT, PATCH or DELETE]!', method))
            res.raise_for_status()
            status = res.status_code

            if int(status) in (204, 404):  # Page not found, no response
                response = False
            else:
                # Some answers return empty content
                response = res.content and res.json() or {}

            try:
                ask_time = datetime.strptime(res.headers.get('date'), "%a, %d %b %Y %H:%M:%S %Z")
            except:
                pass
        except requests.HTTPError as error:
            if error.response.status_code in (204, 404):
                status = error.response.status_code
                response = ""
            else:
                _logger.exception("Bad microsoft request : %s !", error.response.content)
                raise error
        return (status, response, ask_time)
