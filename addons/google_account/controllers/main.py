# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
from werkzeug.utils import redirect

from odoo import http, registry
from odoo.http import request


class GoogleAuth(http.Controller):

    @http.route('/google_account/authentication', type='http', auth="none")
    def oauth2callback(self, **kw):
        """ This route/function is called by Google when user Accept/Refuse the consent of Google """
        state = json.loads(kw['state'])
        dbname = state.get('d')
        service = state.get('s')
        url_return = state.get('f')

        with registry(dbname).cursor() as cr:
            if kw.get('code'):
                request.env(cr, request.session.uid)['google.%s' % service].set_all_tokens(kw['code'])
                return redirect(url_return)
            elif kw.get('error'):
                return redirect("%s%s%s" % (url_return, "?error=", kw['error']))
            else:
                return redirect("%s%s" % (url_return, "?error=Unknown_error"))
