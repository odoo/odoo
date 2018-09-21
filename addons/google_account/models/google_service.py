# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
import json
import logging

import requests
from werkzeug import urls

from odoo import api, fields, models, registry, _
from odoo.exceptions import UserError
from odoo.http import request


_logger = logging.getLogger(__name__)

TIMEOUT = 20

GOOGLE_AUTH_ENDPOINT = 'https://accounts.google.com/o/oauth2/auth'
GOOGLE_TOKEN_ENDPOINT = 'https://accounts.google.com/o/oauth2/token'
GOOGLE_API_BASE_URL = 'https://www.googleapis.com'


# FIXME : this needs to become an AbstractModel, to be inhereted by google_calendar_service and google_drive_service
class GoogleService(models.TransientModel):
    _name = 'google.service'
    _description = 'Google Service'

    @api.model
    def generate_refresh_token(self, service, authorization_code):
        """ Call Google API to refresh the token, with the given authorization code
            :param service : the name of the google service to actualize
            :param authorization_code : the code to exchange against the new refresh token
            :returns the new refresh token
        """
        Parameters = self.env['ir.config_parameter'].sudo()
        client_id = Parameters.get_param('google_%s_client_id' % service)
        client_secret = Parameters.get_param('google_%s_client_secret' % service)
        redirect_uri = Parameters.get_param('google_redirect_uri')

        # Get the Refresh Token From Google And store it in ir.config_parameter
        headers = {"Content-type": "application/x-www-form-urlencoded"}
        data = {
            'code': authorization_code,
            'client_id': client_id,
            'client_secret': client_secret,
            'redirect_uri': redirect_uri,
            'grant_type': "authorization_code"
        }
        try:
            req = requests.post(GOOGLE_TOKEN_ENDPOINT, data=data, headers=headers, timeout=TIMEOUT)
            req.raise_for_status()
            content = req.json()
        except IOError:
            error_msg = _("Something went wrong during your token generation. Maybe your Authorization Code is invalid or already expired")
            raise self.env['res.config.settings'].get_config_warning(error_msg)

        return content.get('refresh_token')

    @api.model
    def _get_google_token_uri(self, service, scope):
        get_param = self.env['ir.config_parameter'].sudo().get_param
        encoded_params = urls.url_encode({
            'scope': scope,
            'redirect_uri': get_param('google_redirect_uri'),
            'client_id': get_param('google_%s_client_id' % service),
            'response_type': 'code',
        })
        return '%s?%s' % (GOOGLE_AUTH_ENDPOINT, encoded_params)

    @api.model
    def _get_authorize_uri(self, from_url, service, scope=False):
        """ This method return the url needed to allow this instance of Odoo to access to the scope
            of gmail specified as parameters
        """
        state = {
            'd': self.env.cr.dbname,
            's': service,
            'f': from_url
        }

        get_param = self.env['ir.config_parameter'].sudo().get_param
        base_url = get_param('web.base.url', default='http://www.odoo.com?NoBaseUrl')
        client_id = get_param('google_%s_client_id' % (service,), default=False)

        encoded_params = urls.url_encode({
            'response_type': 'code',
            'client_id': client_id,
            'state': json.dumps(state),
            'scope': scope or '%s/auth/%s' % (GOOGLE_API_BASE_URL, service),  # If no scope is passed, we use service by default to get a default scope
            'redirect_uri': base_url + '/google_account/authentication',
            'approval_prompt': 'force',
            'access_type': 'offline'
        })
        return "%s?%s" % (GOOGLE_AUTH_ENDPOINT, encoded_params)

    @api.model
    def _get_google_token_json(self, authorize_code, service):
        """ Call Google API to exchange authorization code against token, with POST request, to
            not be redirected.
        """
        get_param = self.env['ir.config_parameter'].sudo().get_param
        base_url = get_param('web.base.url', default='http://www.odoo.com?NoBaseUrl')
        client_id = get_param('google_%s_client_id' % (service,), default=False)
        client_secret = get_param('google_%s_client_secret' % (service,), default=False)

        headers = {"content-type": "application/x-www-form-urlencoded"}
        data = {
            'code': authorize_code,
            'client_id': client_id,
            'client_secret': client_secret,
            'grant_type': 'authorization_code',
            'redirect_uri': base_url + '/google_account/authentication'
        }
        try:
            dummy, response, dummy = self._do_request(GOOGLE_TOKEN_ENDPOINT, params=data, headers=headers, type='POST', preuri='')
            return response
        except requests.HTTPError:
            error_msg = _("Something went wrong during your token generation. Maybe your Authorization Code is invalid")
            raise self.env['res.config.settings'].get_config_warning(error_msg)

    # FIXME : this method update a field defined in google_calendar module. Since it is used only in that module, maybe it should be moved.
    @api.model
    def _refresh_google_token_json(self, refresh_token, service):  # exchange_AUTHORIZATION vs Token (service = calendar)
        get_param = self.env['ir.config_parameter'].sudo().get_param
        client_id = get_param('google_%s_client_id' % (service,), default=False)
        client_secret = get_param('google_%s_client_secret' % (service,), default=False)

        if not client_id or not client_secret:
            raise UserError(_("The account for the Google service '%s' is not configured.") % service)

        headers = {"content-type": "application/x-www-form-urlencoded"}
        data = {
            'refresh_token': refresh_token,
            'client_id': client_id,
            'client_secret': client_secret,
            'grant_type': 'refresh_token',
        }

        try:
            dummy, response, dummy = self._do_request(GOOGLE_TOKEN_ENDPOINT, params=data, headers=headers, type='POST', preuri='')
            return response
        except requests.HTTPError as error:
            if error.response.status_code == 400:  # invalid grant
                with registry(request.session.db).cursor() as cur:
                    self.env(cur)['res.users'].browse(self.env.uid).write({'google_%s_rtoken' % service: False})
            error_key = error.response.json().get("error", "nc")
            _logger.exception("Bad google request : %s !", error_key)
            error_msg = _("Something went wrong during your token generation. Maybe your Authorization Code is invalid or already expired [%s]") % error_key
            raise self.env['res.config.settings'].get_config_warning(error_msg)

    # TODO JEM : remove preuri param, and rename type into method
    @api.model
    def _do_request(self, uri, params={}, headers={}, type='POST', preuri="https://www.googleapis.com"):
        """ Execute the request to Google API. Return a tuple ('HTTP_CODE', 'HTTP_RESPONSE')
            :param uri : the url to contact
            :param params : dict or already encoded parameters for the request to make
            :param headers : headers of request
            :param type : the method to use to make the request
            :param preuri : pre url to prepend to param uri.
        """
        _logger.debug("Uri: %s - Type : %s - Headers: %s - Params : %s !", (uri, type, headers, params))

        ask_time = fields.Datetime.now()
        try:
            if type.upper() in ('GET', 'DELETE'):
                res = requests.request(type.lower(), preuri + uri, params=params, timeout=TIMEOUT)
            elif type.upper() in ('POST', 'PATCH', 'PUT'):
                res = requests.request(type.lower(), preuri + uri, data=params, headers=headers, timeout=TIMEOUT)
            else:
                raise Exception(_('Method not supported [%s] not in [GET, POST, PUT, PATCH or DELETE]!') % (type))
            res.raise_for_status()
            status = res.status_code

            if int(status) in (204, 404):  # Page not found, no response
                response = False
            else:
                response = res.json()

            try:
                ask_time = datetime.strptime(res.headers.get('date'), "%a, %d %b %Y %H:%M:%S %Z")
            except:
                pass
        except requests.HTTPError as error:
            if error.response.status_code in (204, 404):
                status = error.response.status_code
                response = ""
            else:
                _logger.exception("Bad google request : %s !", error.response.content)
                if error.response.status_code in (400, 401, 410):
                    raise error
                raise self.env['res.config.settings'].get_config_warning(_("Something went wrong with your request to google"))
        return (status, response, ask_time)

    # TODO : remove me, it is only used in google calendar. Make google_calendar use the constants
    @api.model
    def get_client_id(self, service):
        return self.env['ir.config_parameter'].sudo().get_param('google_%s_client_id' % (service,), default=False)
