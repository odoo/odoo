from odoo import http, _
from odoo.addons.auth_signup.controllers.main import AuthSignupHome
from odoo.http import request
from odoo.exceptions import UserError


class SignupCaptcha(AuthSignupHome):
    @http.route()
    def web_auth_signup(self, *args, **kw):
        if request.httprequest.method == 'POST' and not request.env['ir.http']._verify_request_recaptcha_token('signup'):
            raise UserError(_("Suspicious activity detected by Google reCaptcha."))
        return super().web_auth_signup(*args, **kw)

    @http.route()
    def web_auth_reset_password(self, *args, **kw):
        if request.httprequest.method == 'POST' and not request.env['ir.http']._verify_request_recaptcha_token('password_reset'):
            raise UserError(_("Suspicious activity detected by Google reCaptcha."))
        return super().web_auth_reset_password(*args, **kw)
