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
        if request.httprequest.method == 'GET':
            user = request.env['res.users'].browse(request.session.pre_uid)
            cookies = request.httprequest.cookies
            if 'trusted_device' in cookies.keys():
                key = cookies['trusted_device']
                checked_credentials = request.env['res.users.apikeys']._check_credentials(scope='Trusted Device', key=key)
                if checked_credentials == user.id:
                    request.session.finalize()
                    return http.redirect_with_hash(self._login_redirect(request.session.uid, redirect=redirect))

        elif request.httprequest.method == 'POST':
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
                returning_session = http.redirect_with_hash(self._login_redirect(request.session.uid, redirect=redirect))
                if 'remember' in kwargs.keys() and kwargs['remember'] == 'on':
                    client_info = {
                        'browser': request.httprequest.user_agent.browser.capitalize(),
                        'platform': request.httprequest.user_agent.platform.capitalize(),
                        'location': request.httprequest.remote_addr,
                    }
                    name = '{browser}({platform}) - {location}'.format(**client_info)
                    key = request.env['res.users.apikeys']._generate('Trusted Device', name)
                    print(key)
                    returning_session.headers.add('Set-Cookie', f'trusted_device={key}; Path=/; Max-Age={90 * 60 * 60 * 24}; HttpOnly')  # Max-Age = 90 days;
                return returning_session

        return request.render('auth_totp.auth_totp_form', {
            'error': error,
            'redirect': redirect,
        })
