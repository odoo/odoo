import logging

import werkzeug.urls
import werkzeug.utils

import openerp.modules.registry
import openerp.addons.web.controllers.main
import openerp.addons.web.common.http as openerpweb

_logger = logging.getLogger(__name__)

class OAuthController(openerpweb.Controller):
    _cp_path = '/auth_oauth'

    @openerpweb.jsonrequest
    def list_providers(self, req, dbname):
        registry = openerp.modules.registry.RegistryManager.get(dbname)
        with registry.cursor() as cr:
            providers = registry.get('auth.oauth.provider')
            l = providers.read(cr, 1, providers.search(cr, 1, []))
        return l

    @openerpweb.httprequest
    def signin(self, req, **kw):
        dbname = kw.get("state")
        registry = openerp.modules.registry.RegistryManager.get(dbname)
        with registry.cursor() as cr:
            try:
                u = registry.get('res.users')
                credentials = u.auth_oauth(cr, 1, {}, kw)
                cr.commit()
                return openerp.addons.web.controllers.main.login_and_redirect(req, *credentials)
            except AttributeError:
                # auth_signup is not installed
                _logger.error("auth_signup not installed on database %s: oauth sign up cancelled."%dbname)
                url = "/#action=login&oauth_error=1"
            except Exception,e:
                # signup error
                _logger.exception('oops')
                url = "/#action=login&oauth_error=2"
        return openerp.addons.web.controllers.main.set_cookie_and_redirect(req, url)


# vim:expandtab:tabstop=4:softtabstop=4:shiftwidth=4:
