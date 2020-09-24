# -*- coding: utf-8 -*-
import re

import odoo.addons.web.controllers.main
from odoo import http, _
from odoo.exceptions import AccessDenied
from odoo.http import request


class Home(odoo.addons.web.controllers.main.Home):
    @http.route(
        '/web/login/totp',
        type='http', auth='public', methods=['GET', 'POST'], sitemap=False,
        website=True, # website breaks the login layout...
    )
    def web_totp(self, redirect=None, **kwargs):
        if request.session.uid:
            return http.redirect_with_hash(self._login_redirect(request.session.uid, redirect=redirect))

        if not request.session.pre_uid:
            return http.redirect_with_hash('/web/login')

        error = None
        if request.httprequest.method == 'POST':
            user = request.env['res.users'].browse(request.session.pre_uid)
            try:
                with user._assert_can_auth():
                    user._totp_check(int(re.sub(r'\s', '', kwargs['totp_token'])))
            except AccessDenied:
                error = _("Verification failed, please double-check the 6-digit code")
            except ValueError:
                error = _("Invalid authentication code format.")
            else:
                request.session.finalize()
                return http.redirect_with_hash(self._login_redirect(request.session.uid, redirect=redirect))

        return request.render('auth_totp.auth_totp_form', {
            'error': error,
            'redirect': redirect,
        })
