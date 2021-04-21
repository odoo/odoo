# -*- coding: utf-8 -*-
import re

import odoo.addons.web.controllers.main
from odoo import http, _
from odoo.addons.auth_totp.models.res_users import TRUSTED_DEVICE_SCOPE
from odoo.exceptions import AccessDenied
from odoo.http import request

TRUSTED_DEVICE_COOKIE = 'td_id'
TRUSTED_DEVICE_AGE = 90*86400 # 90 days expiration


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
        user = request.env['res.users'].browse(request.session.pre_uid)
        if user and request.httprequest.method == 'GET':
            cookies = request.httprequest.cookies
            key = cookies.get(TRUSTED_DEVICE_COOKIE)
            if key:
                checked_credentials = request.env['res.users.apikeys']._check_credentials(scope=TRUSTED_DEVICE_SCOPE, key=key)
                if checked_credentials == user.id:
                    request.session.finalize()
                    return http.redirect_with_hash(self._login_redirect(request.session.uid, redirect=redirect))

        elif user and request.httprequest.method == 'POST':
            try:
                with user._assert_can_auth():
                    user._totp_check(int(re.sub(r'\s', '', kwargs['totp_token'])))
            except AccessDenied:
                error = _("Verification failed, please double-check the 6-digit code")
            except ValueError:
                error = _("Invalid authentication code format.")
            else:
                request.session.finalize()
                response = http.redirect_with_hash(self._login_redirect(request.session.uid, redirect=redirect))
                if kwargs.get('remember'):
                    name = _("%(browser)s on %(platform)s",
                        browser=request.httprequest.user_agent.browser.capitalize(),
                        platform=request.httprequest.user_agent.platform.capitalize(),
                    )
                    geoip = request.session.get('geoip')
                    if geoip:
                        name += " (%s, %s)" % (geoip['city'], geoip['country_name'])

                    key = request.env['res.users.apikeys']._generate(TRUSTED_DEVICE_SCOPE, name)
                    response.set_cookie(
                        key=TRUSTED_DEVICE_COOKIE,
                        value=key,
                        max_age=TRUSTED_DEVICE_AGE,
                        httponly=True,
                        samesite='Lax'
                    )
                return response

        return request.render('auth_totp.auth_totp_form', {
            'error': error,
            'redirect': redirect,
        })
