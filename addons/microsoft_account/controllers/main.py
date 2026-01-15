# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import logging
import requests
from werkzeug.exceptions import BadRequest

from odoo import http
from odoo.http import request
from odoo.addons.microsoft_account.models.microsoft_service import TIMEOUT

_logger = logging.getLogger(__name__)


class MicrosoftAuth(http.Controller):

    @http.route('/microsoft_account/authentication', type='http', auth="public")
    def oauth2callback(self, **kw):
        """ This route/function is called by Microsoft when user Accept/Refuse the consent of Microsoft """
        state = json.loads(kw.get('state', '{}'))
        service = state.get('s')
        url_return = state.get('f')
        if (not service or (kw.get('code') and not url_return)):
            raise BadRequest()

        if kw.get('code'):
            base_url = request.httprequest.url_root.strip('/') or request.env.user.get_base_url()
            access_token, refresh_token, ttl = request.env['microsoft.service']._get_microsoft_tokens(
                kw['code'],
                service,
                redirect_uri=f'{base_url}/microsoft_account/authentication'
            )
            request.env.user._set_microsoft_auth_tokens(access_token, refresh_token, ttl)
            request.env.user.restart_microsoft_synchronization(reset_records=False)
            self._set_outlook_email(token=access_token)
            return request.redirect(url_return)
        elif kw.get('error'):
            return request.redirect("%s%s%s" % (url_return, "?error=", kw['error']))
        else:
            return request.redirect("%s%s" % (url_return, "?error=Unknown_error"))

    def _set_outlook_email(self, token=None, timeout=TIMEOUT):
        url = '/v1.0/me'
        headers = {'Content-type': 'application/json', 'Authorization': 'Bearer %s' % token}
        try:
            status, user_info, _ = self.env["microsoft.service"]._do_request(url, {}, headers, method='GET', timeout=timeout)
            if status == 200:
                # 'mail' can be None for some accounts, fall back to userPrincipalName
                email = user_info.get('mail') or user_info.get('userPrincipalName')
                if email:
                    self.env.user.sudo()._set_microsoft_email(email)
        except requests.exceptions.RequestException as e:
            _logger.error('Error setting outlook email: %s', e)
