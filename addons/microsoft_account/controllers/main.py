# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo import http
from odoo.http import request


class MicrosoftAuth(http.Controller):

    @http.route('/microsoft_account/authentication', type='http', auth="public")
    def oauth2callback(self, **kw):
        """
        This route is called by Microsoft API when user accepts/refuses to give
        his consent during the authentication process.
        """
        state = json.loads(kw['state'])
        dbname = state.get('d')
        service = state.get('s')
        url_return = state.get('f')

        if kw.get('code'):
            tokens = request.env['microsoft.service']._get_microsoft_tokens(kw['code'], service)
            request.env.user._set_microsoft_auth_tokens(*tokens)
            return request.redirect(url_return)
        elif kw.get('error'):
            return request.redirect("%s%s%s" % (url_return, "?error=", kw['error']))
        else:
            return request.redirect("%s%s" % (url_return, "?error=Unknown_error"))
