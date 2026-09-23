import re
from datetime import datetime, timedelta

from odoo import http
from odoo.exceptions import AccessDenied
from odoo.http import request

from odoo.addons.web.controllers import home as web_home

TRUSTED_DEVICE_COOKIE = "td_id"
TRUSTED_DEVICE_AGE_DAYS = 90


class Home(web_home.Home):
    @http.route(
        "/web/login/totp",
        type="http",
        auth="public",
        methods=["GET", "POST"],
        sitemap=False,
        website=True,
        multilang=False,  # website breaks the login layout...
    )
    def web_totp(self, redirect=None, **kwargs):
        if request.session.uid:
            return request.redirect(
                self._login_redirect(request.session.uid, redirect=redirect)
            )

        if not request.session.get("pre_uid"):
            return request.redirect("/web/login")

        error = None

        user = request.env["res.users"].sudo().browse(request.session["pre_uid"])
        if user and request.httprequest.method == "GET":
            cookies = request.cookies
            key = cookies.get(TRUSTED_DEVICE_COOKIE)
            if key:
                user_match = request.env["auth_totp.device"]._check_credentials_for_uid(
                    scope="browser", key=key, uid=user.id
                )
                if user_match:
                    request.session.finalize_login(request.env)
                    request.update_env(user=request.session.uid)
                    request.update_context(**request.session.context)
                    return request.redirect(
                        self._login_redirect(request.session.uid, redirect=redirect)
                    )

        elif user and request.httprequest.method == "POST" and kwargs.get("totp_token"):
            try:
                with user._assert_can_auth(user=user.id):
                    credentials = {
                        "type": user._get_mfa_type(),
                        "token": int(re.sub(r"\s", "", kwargs["totp_token"])),
                    }
                    user._check_credentials(credentials, {"interactive": True})
            except AccessDenied as e:
                error = str(e)
            except ValueError:
                error = request.env._("Invalid authentication code format.")
            else:
                request.session.finalize_login(request.env)
                request.update_env(user=request.session.uid)
                request.update_context(**request.session.context)
                response = request.redirect(
                    self._login_redirect(request.session.uid, redirect=redirect)
                )
                if kwargs.get("remember"):
                    # Both attributes are None for any User-Agent the parser in
                    # odoo/libs/_vendor/useragents.py does not classify, and
                    # calling .capitalize() on that turned "remember this
                    # device" into an HTTP 500 -- after the session was already
                    # finalized. The Odoo mobile app is one such client
                    # (`Odoo/x CFNetwork/y Darwin/z` parses a platform but no
                    # browser), which is the same client the two workarounds
                    # further down this method exist for.
                    user_agent = request.httprequest.user_agent
                    name = request.env._(
                        "%(browser)s on %(platform)s",
                        browser=(
                            user_agent.browser.capitalize()
                            if user_agent.browser
                            else request.env._("Unknown browser")
                        ),
                        platform=(
                            user_agent.platform.capitalize()
                            if user_agent.platform
                            else request.env._("Unknown platform")
                        ),
                    )

                    if request.geoip.city.name:
                        name += f" ({request.geoip.city.name}, {request.geoip.country_name})"

                    trusted_device_age = request.env[
                        "auth_totp.device"
                    ]._get_trusted_device_age()
                    key = (
                        request.env["auth_totp.device"]
                        .sudo()
                        ._generate(
                            "browser",
                            name,
                            datetime.now() + timedelta(seconds=trusted_device_age),
                        )
                    )
                    response.set_cookie(
                        key=TRUSTED_DEVICE_COOKIE,
                        value=key,
                        max_age=trusted_device_age,
                        httponly=True,
                        samesite="Lax",
                    )
                # Crapy workaround for unupdatable Odoo Mobile App iOS (Thanks Apple :@)
                request.session.mark_dirty()
                return response

        # Crapy workaround for unupdatable Odoo Mobile App iOS (Thanks Apple :@)
        request.session.mark_dirty()
        return request.render(
            "auth_totp.auth_totp_form",
            {
                "user": user,
                "error": error,
                "redirect": redirect,
            },
        )
