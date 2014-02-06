import openerp
from openerp import http
from openerp.http import request, LazyResponse

class AuthSignupWebsiteLogin(openerp.addons.web.controllers.main.Home):
    @http.route(website=True, auth="public", multilang=True)
    def web_auth_signup(self, *args, **kw):
        response = super(AuthSignupWebsiteLogin, self).web_auth_signup(*args, **kw)
        if isinstance(response, LazyResponse):
            response = request.website.render(response.params['template'], response.params['values'])
        return response

    @http.route(website=True, auth="public", multilang=True)
    def web_auth_reset_password(self, *args, **kw):
        response = super(AuthSignupWebsiteLogin, self).web_auth_reset_password(*args, **kw)
        if isinstance(response, LazyResponse):
            response = request.website.render(response.params['template'], response.params['values'])
        return response

# vim:expandtab:tabstop=4:softtabstop=4:shiftwidth=4:
