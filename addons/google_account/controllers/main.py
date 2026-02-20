# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import logging
import requests
from werkzeug.exceptions import BadRequest

from odoo import http
from odoo.http import request
from odoo.addons.google_account.models.google_service import TIMEOUT

_logger = logging.getLogger(__name__)


class GoogleAuth(http.Controller):

    @http.route('/google_account/authentication', type='http', auth="public")
    def oauth2callback(self, **kw):
        """ This route/function is called by Google when user Accept/Refuse the consent of Google """
        state = json.loads(kw.get('state', '{}'))
        service = state.get('s')
        url_return = state.get('f')
        if (not service or (kw.get('code') and not url_return)):
            raise BadRequest()

        if kw.get('code'):
            base_url = request.httprequest.url_root.strip('/') or request.env.user.get_base_url()
            access_token, refresh_token, ttl = request.env['google.service']._get_google_tokens(
                kw['code'],
                service,
                redirect_uri=f'{base_url}/google_account/authentication'
            )
            service_field = 'res_users_settings_id'
            if service_field in request.env.user:
                request.env.user[service_field]._set_google_auth_tokens(access_token, refresh_token, ttl)
            else:
                raise Warning('No callback field for service <%s>' % service)

            request.env.user.restart_google_synchronization(reset_records=False)
            self._set_google_email(token=access_token)
            return request.redirect(url_return)
        elif kw.get('error'):
            return request.redirect("%s%s%s" % (url_return, "?error=", kw['error']))
        else:
            return request.redirect("%s%s" % (url_return, "?error=Unknown_error"))

    def _set_google_email(self, token=None, timeout=TIMEOUT):
        headers = {'Content-type': 'application/json'}
        params = {'access_token': token}
        url = '/oauth2/v2/userinfo'
        try:
            status, mail_info, _ = self.env['google.service']._do_request(url, params, headers, method='GET', timeout=timeout)
            if status == 200:
                self.env.user.sudo().res_users_settings_id._set_google_calendar_email(mail_info['email'])
        except requests.exceptions.RequestException as e:
            _logger.error('Error setting google email: %s', e)
