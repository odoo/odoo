import openerp
import werkzeug

from openerp.http import request

class OAuthSignupLogin(openerp.addons.web.controllers.main.Home):
    def list_providers(self):
        providers = super(OAuthSignupLogin, self).list_providers()
        if len(providers) == 1 and request.params.get('mode') == 'signup':
            werkzeug.exceptions.abort(werkzeug.utils.redirect(providers[0]['auth_link'], 303))
        return providers

    def get_state(self, provider):
        state = super(OAuthSignupLogin, self).get_state(provider)
        token = request.params.get('token')
        if token:
            state['t'] = token
        return state

# vim:expandtab:tabstop=4:softtabstop=4:shiftwidth=4:
