import openerp
from openerp import http

class AuthSignupWebsiteLogin(openerp.addons.web.controllers.main.Home):
    @http.route(website=True, auth="public", multilang=True)
    def web_auth_signup(self, *args, **kw):
        return super(AuthSignupWebsiteLogin, self).web_auth_signup(*args, **kw)

    @http.route(website=True, auth="public", multilang=True)
    def web_auth_reset_password(self, *args, **kw):
        return super(AuthSignupWebsiteLogin, self).web_auth_reset_password(*args, **kw)

# vim:expandtab:tabstop=4:softtabstop=4:shiftwidth=4:
