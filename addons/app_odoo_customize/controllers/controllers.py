# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import http
from odoo.addons.portal.controllers.web import Home
from odoo.http import request


class AppHome(Home):

    @http.route()
    def web_client(self, s_action=None, **kw):
        # todo: 当前只对 web，要调整为也对 website
        res = super(AppHome, self).web_client(s_action, **kw)

        if kw.get('debug', False):
            config_parameter = request.env['ir.config_parameter'].sudo()
            app_debug_only_admin = config_parameter.get_param('app_debug_only_admin')
            if request.session.uid and request.env.user.browse(request.session.uid)._is_admin():
                pass
            else:
                if app_debug_only_admin:
                    return request.redirect('/web/session/logout?debug=0')
        return res



