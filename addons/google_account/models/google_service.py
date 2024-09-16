# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
import logging

import json
import requests
from werkzeug import urls

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)

TIMEOUT = 20

GOOGLE_AUTH_ENDPOINT = 'https://accounts.google.com/o/oauth2/auth'
GOOGLE_TOKEN_ENDPOINT = 'https://accounts.google.com/o/oauth2/token'
GOOGLE_API_BASE_URL = 'https://www.googleapis.com'


class GoogleService(models.AbstractModel):
    _name = 'google.service'
    _description = 'Google Service'

    def _get_client_id(self, service):
        """ Returns the Client ID for a specific Google service.

        :param service: The Google service for which to retrieve the Client ID
        :return: The Client ID for the specified Google service
        :rtype: str
        """
        return self.env['ir.config_parameter'].sudo().get_param(
            'google_%s_client_id' % (service),
            default=False
        )

    def _get_client_secret(self, service):
        """ Returns the Client Secret for a specific Google service.

        :param service: The Google service for which to retrieve the Client Secret
        :return: The Client Secret for the specified Google service
        :rtype: str
        """
        return self.env['ir.config_parameter'].sudo().get_param(
            'google_%s_client_secret' % (service),
            default=False
        )

    def _has_setup_credentials(self):
        """ Checks if both Client ID and Client Secret are defined in the database.

        :return: True if both Client ID and Client Secret are defined, False otherwise
        :rtype: bool
        """
        sudo_get_param = self.env['ir.config_parameter'].sudo().get_param
        client_id = sudo_get_param('google_calendar_client_id')
        client_secret = sudo_get_param('google_calendar_client_secret')
        return client_id and client_secret

    def _has_external_credentials_provider(self):
        """ Overridable method that indicates if external credentials are being used for the synchronization.

        :return: True if external credentials are being used, False otherwise
        :rtype: bool
        """
        return False

    def _get_base_url(self):
        """ Returns the base URL for Google API requests.

        :return: The base URL for Google API requests
        :rtype: str
        """
        return self._context.get('base_url') or self.env.user.get_base_url()

    def _get_redirect_uri(self):
        """ Returns the redirect URI for Google API requests.

        :return: The redirect URI for Google API requests
        :rtype: str
        """
        return self._get_base_url() + '/google_account/authentication'

    @api.model
    def _get_authorize_uri(self, service, scope, redirect_uri, state=None, approval_prompt=None, access_type=None):
        """ This method return the url needed to allow this instance of Odoo to access to the scope
            of gmail specified as parameters
        """
        params = {
            'response_type': 'code',
            'client_id': self._get_client_id(service),
            'scope': scope,
            'redirect_uri': redirect_uri,
        }

        if state:
            params['state'] = state

        if approval_prompt:
            params['approval_prompt'] = approval_prompt

        if access_type:
            params['access_type'] = access_type


        encoded_params = urls.url_encode(params)
        return "%s?%s" % (GOOGLE_AUTH_ENDPOINT, encoded_params)

    @api.model
    def _get_google_tokens(self, authorize_code, service):
        """ Call Google API to exchange authorization code against token, with POST request, to
            not be redirected.
        """
        ICP = self.env['ir.config_parameter'].sudo()

        headers = {"content-type": "application/x-www-form-urlencoded"}
        data = {
            'code': authorize_code,
            'client_id': self._get_client_id(service),
            'client_secret': self._get_client_secret(service),
            'grant_type': 'authorization_code',
            'redirect_uri': self._get_redirect_uri(),
        }
        try:
            dummy, response, dummy = self._do_request(GOOGLE_TOKEN_ENDPOINT, params=data, headers=headers, method='POST', preuri='')
            return response.get('access_token'), response.get('refresh_token'), response.get('expires_in')
        except requests.HTTPError as e:
            _logger.error(e)
            error_msg = _("Something went wrong during your token generation. Maybe your Authorization Code is invalid or already expired")
            raise self.env['res.config.settings'].get_config_warning(error_msg)

    @api.model
    def _do_request(self, uri, params=None, headers=None, method='POST', preuri=GOOGLE_API_BASE_URL, timeout=TIMEOUT):
        """ Execute the request to Google API. Return a tuple ('HTTP_CODE', 'HTTP_RESPONSE')
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

        assert urls.url_parse(preuri + uri).host in [
            urls.url_parse(url).host for url in (GOOGLE_TOKEN_ENDPOINT, GOOGLE_API_BASE_URL)
        ]

        # Remove client_secret key from logs
        if isinstance(params, str):
            _log_params = json.loads(params) or {}
        else:
            _log_params = (params or {}).copy()
        if _log_params.get('client_secret'):
            _log_params['client_secret'] = _log_params['client_secret'][0:4] + 'x' * 12

        _logger.debug("Uri: %s - Type : %s - Headers: %s - Params : %s!", uri, method, headers, _log_params)

        ask_time = fields.Datetime.now()
        try:
            if method.upper() in ('GET', 'DELETE'):
                res = requests.request(method.lower(), preuri + uri, params=params, timeout=timeout)
            elif method.upper() in ('POST', 'PATCH', 'PUT'):
                res = requests.request(method.lower(), preuri + uri, data=params, headers=headers, timeout=timeout)
            else:
                raise Exception(_('Method not supported [%s] not in [GET, POST, PUT, PATCH or DELETE]!', method))
            res.raise_for_status()
            status = res.status_code

            if int(status) == 204:  # Page not found, no response
                response = False
            else:
                response = res.json()

            try:
                ask_time = datetime.strptime(res.headers.get('date', ''), "%a, %d %b %Y %H:%M:%S %Z")
            except ValueError:
                pass
        except requests.HTTPError as error:
            if error.response.status_code in (204, 404):
                status = error.response.status_code
                response = ""
            else:
                _logger.exception("Bad google request : %s!", error.response.content)
                raise error
        return (status, response, ask_time)
