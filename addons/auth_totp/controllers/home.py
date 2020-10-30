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
            error = self._process_totp(kwargs['totp_token'])
            if not error:
                return http.redirect_with_hash(self._login_redirect(request.session.uid, redirect=redirect))

        return request.render('auth_totp.auth_totp_form', {
            'error': error,
            'redirect': redirect,
        })

    @http.route(
        '/web/session/authenticate/totp',
        type='json', auth='public', methods=['POST']
    )
    def authenticate_totp(self, totp_token):
        if not request.session.pre_uid:
            return {'error': _("Session isn't authenticate")}
        error = self._process_totp(totp_token)
        if not error:
            return request.env['ir.http'].session_info()
        return {'error': error}

    def _process_totp(self, totp_token):
        """Apply the 2FA check for the user with the session uid stored inside the ``pre_uid`` value inside the session

        :param totp_token: the challenge code token
        :return: None if totp is a success or an error message if the 2FA checks fails
        """
        user = request.env['res.users'].browse(request.session.pre_uid)
        try:
            with user._assert_can_auth():
                user._totp_check(int(re.sub(r'\s', '', totp_token)))
        except AccessDenied:
            return _("Verification failed, please double-check the 6-digit code")
        except ValueError:
            return _("Invalid authentication code format.")
        else:
            request.session.finalize()
            return None
