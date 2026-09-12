# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
from werkzeug import urls
from werkzeug.exceptions import BadRequest

from odoo import http
from odoo.http import request


class GoogleAuth(http.Controller):

    @http.route('/google_account/authentication', type='http', auth="public")
    def oauth2callback(self, **kw):
        """ This route/function is called by Google when user Accept/Refuse the consent of Google """
        state = json.loads(kw.get('state', '{}'))
        service = state.get('s')
        url_return = state.get('f')
        if (not service or (kw.get('code') and not url_return)):
            raise BadRequest()

        def _build_url_w_params(url_string, query_params, remove_duplicates=True):
            """ Rebuild a string url based on url_string and correctly compute query parameters
            using those present in the url and those given by query_params. Having duplicates in
            the final url is optional. For example:

             * url_string = '/my?foo=bar&error=pay'
             * query_params = {'foo': 'bar2', 'alice': 'bob'}
             * if remove duplicates: result = '/my?foo=bar2&error=pay&alice=bob'
             * else: result = '/my?foo=bar&foo=bar2&error=pay&alice=bob'
            """
            # Method copied from portal.py, consider moving to web module
            url = urls.url_parse(url_string)
            url_params = url.decode_query()
            if remove_duplicates:  # convert to standard dict instead of werkzeug multidict to remove duplicates automatically
                url_params = url_params.to_dict()
            url_params.update(query_params)
            return url.replace(query=urls.url_encode(url_params)).to_url()

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
            return request.redirect(_build_url_w_params(url_return, {"auth_success": "True"}))
        elif kw.get('error'):
            return request.redirect(_build_url_w_params(url_return, {"error": kw['error']}))
        else:
            return request.redirect(_build_url_w_params(url_return, {"error": "Unknown_error"}))
