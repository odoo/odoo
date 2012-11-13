import logging

import simplejson
import werkzeug.urls
import werkzeug.utils

import openerp

_logger = logging.getLogger(__name__)

class OAuthController(openerp.addons.web.http.Controller):
    _cp_path = '/auth_oauth'

    @openerp.addons.web.http.jsonrequest
    def list_providers(self, req, dbname):
        try:
            registry = openerp.modules.registry.RegistryManager.get(dbname)
            with registry.cursor() as cr:
                providers = registry.get('auth.oauth.provider')
                l = providers.read(cr, openerp.SUPERUSER_ID, providers.search(cr, openerp.SUPERUSER_ID, [('enabled','=',True)]))
        except Exception:
            l = []
        return l

    @openerp.addons.web.http.httprequest
    def signin(self, req, **kw):
        state = simplejson.loads(kw['state'])
        dbname = state['d']
        provider = state['p']
        registry = openerp.modules.registry.RegistryManager.get(dbname)
        with registry.cursor() as cr:
            try:
                u = registry.get('res.users')
                credentials = u.auth_oauth(cr, openerp.SUPERUSER_ID, provider, kw)
                cr.commit()
                return openerp.addons.web.controllers.main.login_and_redirect(req, *credentials)
            except AttributeError:
                # auth_signup is not installed
                _logger.error("auth_signup not installed on database %s: oauth sign up cancelled."%dbname)
                url = "/#action=login&oauth_error=1"
            except Exception,e:
                # signup error
                _logger.exception("OAuth2: %s" % str(e))
                url = "/#action=login&oauth_error=2"
        return openerp.addons.web.controllers.main.set_cookie_and_redirect(req, url)


# vim:expandtab:tabstop=4:softtabstop=4:shiftwidth=4:
