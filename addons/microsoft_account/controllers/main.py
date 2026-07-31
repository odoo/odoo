# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
from urllib.parse import urlencode, urlsplit, urlunsplit, parse_qsl
from werkzeug.exceptions import BadRequest

from odoo import http
from odoo.http import request


class MicrosoftAuth(http.Controller):

    @http.route('/microsoft_account/authentication', type='http', auth="public")
    def oauth2callback(self, **kw):
        """ This route/function is called by Microsoft when user Accept/Refuse the consent of Microsoft """
        state = json.loads(kw.get('state', '{}'))
        service = state.get('s')
        url_return = state.get('f')
        if (not service or (kw.get('code') and not url_return)):
            raise BadRequest()

        def _add_query_params(url, params):
            """Merge params into url's query string, whether or not it already has one."""
            parts = urlsplit(url)
            query = dict(parse_qsl(parts.query, keep_blank_values=True))
            query.update(params)
            return urlunsplit(parts._replace(query=urlencode(query)))

        if kw.get('code'):
            base_url = request.httprequest.url_root.strip('/') or request.env.user.get_base_url()
            access_token, refresh_token, ttl = request.env['microsoft.service']._get_microsoft_tokens(
                kw['code'],
                service,
                redirect_uri=f'{base_url}/microsoft_account/authentication'
            )
            request.env.user._set_microsoft_auth_tokens(access_token, refresh_token, ttl)
            return request.redirect(_add_query_params(url_return, {"auth_success": "True"}))
        elif kw.get('error'):
            return request.redirect(_add_query_params(url_return, {"error": kw['error']}))
        else:
            return request.redirect(_add_query_params(url_return, {"error": "Unknown_error"}))
