# -*- coding: utf-8 -*-
import re

from datetime import datetime, timedelta

from odoo import http, _
from odoo.exceptions import UserError
from odoo.http import request
from odoo.http.session import finalize, touch
from odoo.addons.web.controllers import home as web_home
from odoo.addons.auth_totp.models.totp import generate_secret

TRUSTED_DEVICE_COOKIE = 'td_id'


class Home(web_home.Home):
    @http.route(
        '/web/login/totp',
        type='http', auth='public', methods=['GET', 'POST'], sitemap=False,
        website=True, multilang=False # website breaks the login layout...
    )
    def web_totp(self, redirect=None, **kwargs):
        if request.session.uid:
            return request.redirect(self._login_redirect(request.session.uid, redirect=redirect))

        if not request.session.get('pre_uid'):
            return request.redirect('/web/login')

        error = None

        user = request.env['res.users'].browse(request.session['pre_uid'])
        mfa_type = user._mfa_type()
        setup = None
        if not mfa_type:
            if not user._mfa_required():
                return request.redirect('/web/login')
            # show the same secret until its code is entered
            setup_uid, secret = request.session.get('pre_totp_setup', (None, None))
            if setup_uid != user.id:
                secret = generate_secret()
                request.session['pre_totp_setup'] = (user.id, secret)
            setup = request.env['auth_totp.wizard'].sudo().new({'user_id': user.id, 'secret': secret})

        if user and request.httprequest.method == 'GET':
            cookies = request.cookies
            key = cookies.get(TRUSTED_DEVICE_COOKIE)
            if key:
                user_match = request.env['auth_totp.device']._check_credentials_for_uid(
                    scope="browser", key=key, uid=user.id)
                if user_match:
                    finalize(request.session, request.env)
                    request.update_env(user=request.session.uid)
                    request.update_context(**request.session.context)
                    return request.redirect(self._login_redirect(request.session.uid, redirect=redirect))

        elif user and request.httprequest.method == 'POST' and kwargs.get('totp_token'):
            code = re.sub(r'\s', '', kwargs['totp_token'])
            try:
                with user._assert_can_auth(user=user.id):
                    if setup:
                        user.with_user(user)._totp_enable(setup.secret, int(code))
                    else:
                        user._check_credentials({'type': mfa_type, 'token': int(code)}, {'interactive': True})
            except UserError as e:
                error = str(e)
            except ValueError:
                error = _("Invalid authentication code format.")
            else:
                request.session.pop('pre_totp_setup', None)
                finalize(request.session, request.env)
                request.update_env(user=request.session.uid)
                request.update_context(**request.session.context)
                response = request.redirect(self._login_redirect(request.session.uid, redirect=redirect))
                if kwargs.get('remember'):
                    name = _("%(browser)s on %(platform)s",
                        browser=request.httprequest.user_agent.browser.capitalize(),
                        platform=request.httprequest.user_agent.platform.capitalize(),
                    )

                    if request.geoip.city.name:
                        name += f" ({request.geoip.city.name}, {request.geoip.country_name})"

                    trusted_device_age = request.env['auth_totp.device']._get_trusted_device_age()
                    key = request.env['auth_totp.device'].sudo()._generate(
                        "browser",
                        name,
                        datetime.now() + timedelta(seconds=trusted_device_age)
                    )
                    response.set_cookie(
                        key=TRUSTED_DEVICE_COOKIE,
                        value=key,
                        max_age=trusted_device_age,
                        httponly=True,
                        samesite='Lax'
                    )
                # Crapy workaround for unupdatable Odoo Mobile App iOS (Thanks Apple :@)
                touch(request.session)
                return response

        # Crapy workaround for unupdatable Odoo Mobile App iOS (Thanks Apple :@)
        touch(request.session)
        response = request.render('auth_totp.auth_totp_form', {
            'user': user,
            'setup': setup,
            'error': error,
            'redirect': redirect,
        })
        response.headers['Cache-Control'] = 'no-store'
        return response
