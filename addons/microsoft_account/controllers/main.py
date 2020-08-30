# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
from werkzeug.utils import redirect

from odoo import http, registry
from odoo.http import request


class MicrosoftAuth(http.Controller):

    @http.route('/microsoft_account/authentication', type='http', auth="public")
    def oauth2callback(self, **kw):
        """ This route/function is called by Microsoft when user Accept/Refuse the consent of Microsoft """
        state = json.loads(kw['state'])
        dbname = state.get('d')
        service = state.get('s')
        url_return = state.get('f')

        with registry(dbname).cursor() as cr:
            if kw.get('code'):
                access_token, refresh_token, ttl = request.env['microsoft.service']._get_microsoft_tokens(kw['code'], service)
                request.env.user._set_microsoft_auth_tokens(access_token, refresh_token, ttl)
                return redirect(url_return)
            elif kw.get('error'):
                return redirect("%s%s%s" % (url_return, "?error=", kw['error']))
            else:
                return redirect("%s%s" % (url_return, "?error=Unknown_error"))
