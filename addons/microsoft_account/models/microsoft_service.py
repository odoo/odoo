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
DEFAULT_MICROSOFT_GRAPH_ENDPOINT = 'https://graph.microsoft.com'

RESOURCE_NOT_FOUND_STATUSES = (204, 404)


def _get_microsoft_client_secret(ICP_sudo, service):
    """ Return the client_secret for a specific service.

    Note: This method serves as a hook for modules that would like share their own keys.
        This method should never be callable from a method that return it in clear, it
        should only be used directly in a request.

    :param ICP_sudo: the model ir.config_parameters in sudo
    :param service: the service that we need the secret key
    :return: The ICP value
    :rtype: str
    """
    return ICP_sudo.get_param('microsoft_%s_client_secret' % service)

class MicrosoftService(models.AbstractModel):
    _name = 'microsoft.service'
    _description = 'Microsoft Service'

    def _get_microsoft_client_id(self, service):
        # client id is not a secret, and can be leaked without risk. e.g. in clear in authorize uri.
        ICP = self.env['ir.config_parameter'].sudo()
        return ICP.get_param('microsoft_%s_client_id' % service)

    def _get_calendar_scope(self):
        return 'offline_access openid Calendars.ReadWrite'

    @api.model
    def _get_auth_endpoint(self):
        return self.env["ir.config_parameter"].sudo().get_param('microsoft_account.auth_endpoint', DEFAULT_MICROSOFT_AUTH_ENDPOINT)

    @api.model
    def _get_token_endpoint(self):
        return self.env["ir.config_parameter"].sudo().get_param('microsoft_account.token_endpoint', DEFAULT_MICROSOFT_TOKEN_ENDPOINT)

    @api.model
    def generate_refresh_token(self, service, authorization_code):
        """ Call Microsoft API to refresh the token, with the given authorization code
            :param service : the name of the microsoft service to actualize
            :param authorization_code : the code to exchange against the new refresh token
            :returns the new refresh token
        """
        ICP_sudo = self.env['ir.config_parameter'].sudo()
        scope = self._get_calendar_scope()

        # Get the Refresh Token From Microsoft And store it in ir.config_parameter
        headers = {"Content-type": "application/x-www-form-urlencoded"}
        data = {
            'client_id': self._get_microsoft_client_id(service),
            'redirect_uri': ICP_sudo.get_param('microsoft_redirect_uri'),
            'client_secret': _get_microsoft_client_secret(ICP_sudo, service),
            'scope': scope,
            'grant_type': "refresh_token"
        }
        try:
            req = requests.post(self._get_token_endpoint(), data=data, headers=headers, timeout=TIMEOUT)
            req.raise_for_status()
            content = req.json()
        except requests.exceptions.RequestException as exc:
            error_msg = _("Something went wrong during your token generation. Maybe your Authorization Code is invalid or already expired")
            raise self.env['res.config.settings'].get_config_warning(error_msg) from exc

        return content.get('refresh_token')

    @api.model
    def _get_authorize_uri(self, from_url, service, scope, redirect_uri):
        """ This method return the url needed to allow this instance of Odoo to access to the scope
            of gmail specified as parameters
        """
        state = {
            'd': self.env.cr.dbname,
            's': service,
            'f': from_url,
            'u': self.env['ir.config_parameter'].sudo().get_param('database.uuid'),
        }

        get_param = self.env['ir.config_parameter'].sudo().get_param

        encoded_params = urls.url_encode({
            'response_type': 'code',
            'client_id': self._get_microsoft_client_id(service),
            'state': json.dumps(state),
            'scope': scope,
            'redirect_uri': redirect_uri,
            'access_type': 'offline'
        })
        return "%s?%s" % (self._get_auth_endpoint(), encoded_params)

    @api.model
    def _get_microsoft_tokens(self, authorize_code, service, redirect_uri):
        """ Call Microsoft API to exchange authorization code against token, with POST request, to
            not be redirected.
        """
        ICP_sudo = self.env['ir.config_parameter'].sudo()
        scope = self._get_calendar_scope()

        headers = {"content-type": "application/x-www-form-urlencoded"}
        data = {
            'code': authorize_code,
            'client_id': self._get_microsoft_client_id(service),
            'client_secret': _get_microsoft_client_secret(ICP_sudo, service),
            'grant_type': 'authorization_code',
            'scope': scope,
            'redirect_uri': redirect_uri
        }
        try:
            dummy, response, dummy = self._do_request(self._get_token_endpoint(), params=data, headers=headers, method='POST', preuri='')
            access_token = response.get('access_token')
            refresh_token = response.get('refresh_token')
            ttl = response.get('expires_in')
            return access_token, refresh_token, ttl
        except requests.HTTPError:
            error_msg = _("Something went wrong during your token generation. Maybe your Authorization Code is invalid")
            raise self.env['res.config.settings'].get_config_warning(error_msg)

    @api.model
    def _do_request(self, uri, params=None, headers=None, method='POST', preuri=DEFAULT_MICROSOFT_GRAPH_ENDPOINT, timeout=TIMEOUT):
        """ Execute the request to Microsoft API. Return a tuple ('HTTP_CODE', 'HTTP_RESPONSE')
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
            urls.url_parse(url).host for url in (DEFAULT_MICROSOFT_TOKEN_ENDPOINT, DEFAULT_MICROSOFT_GRAPH_ENDPOINT)
        ]

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

            if int(status) in RESOURCE_NOT_FOUND_STATUSES:
                response = {}
            else:
                # Some answers return empty content
                response = res.content and res.json() or {}

            try:
                ask_time = datetime.strptime(res.headers.get('date'), "%a, %d %b %Y %H:%M:%S %Z")
            except:
                pass
        except requests.HTTPError as error:
            if error.response.status_code in RESOURCE_NOT_FOUND_STATUSES:
                status = error.response.status_code
                response = {}
            else:
                _logger.exception("Bad microsoft request: %s!", error.response.content)
                raise error
        return (status, response, ask_time)
