# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.addons.web.controllers.home import Home as WebHome
from odoo.addons.web.controllers.utils import is_user_internal
from odoo.http import request


class Home(WebHome):

    @http.route()
    def index(self, *args, **kw):
        if request.session.uid and not is_user_internal(request.session.uid):
            return request.redirect_query('/my', query=request.params)
        return super().index(*args, **kw)

    def _login_redirect(self, uid, redirect=None):
        if redirect == '/my' or (not redirect or redirect == '/odoo?') and not is_user_internal(uid):
            lang = request.env(user=uid)['res.users'].browse(uid).lang
            if self.env['res.lang']._get_frontend()[lang]:
                redirect = f'/{lang}/my'
            else:
                redirect = f'/my'
        return super()._login_redirect(uid, redirect=redirect)

    @http.route()
    def web_client(self, s_action=None, **kw):
        uid = request.session.uid
        if uid and not is_user_internal(uid):
            lang = request.env(user=uid)['res.users'].browse(uid).lang
            if self.env['res.lang']._get_frontend()[lang]:
                redirect = f'/{lang}/my'
            else:
                redirect = f'/my'
            return request.redirect_query(redirect, query=request.params)
        return super().web_client(s_action, **kw)
