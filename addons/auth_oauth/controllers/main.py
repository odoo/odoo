import logging

import werkzeug.urls
import werkzeug.utils

import openerp.modules.registry
import openerp.addons.web.controllers.main
import openerp.addons.web.common.http as openerpweb

_logger = logging.getLogger(__name__)

class OAuthController(openerpweb.Controller):
    _cp_path = '/auth_oauth'

    def list_providers(self, req, dbname):
        #dbname = kw.get("state")
        #registry = openerp.modules.registry.RegistryManager.get(dbname)
        #with registry.cursor() as cr:
        # dsfasdf
        pass

    @openerpweb.httprequest
    def signin(self, req, **kw):
        dbname = kw.get("state")
        registry = openerp.modules.registry.RegistryManager.get(dbname)
        with registry.cursor() as cr:
            try:
                u = registry.get('res.users')
                credentials = u.auth_oauth(cr, 1, kw)
                cr.commit()
                return openerp.addons.web.controllers.main.login_and_redirect(req, *credentials)
            except AttributeError:
                # auth_signup is not installed
                _logger.exception("attribute error")
                url = "/#action=auth_signup&error=1"
            except Exception,e:
                # signup error
                _logger.exception('oops')
                url = "/#action=auth_signup&error=2"
        return openerp.addons.web.controllers.main.set_cookie_and_redirect(req, "/")


# vim:expandtab:tabstop=4:softtabstop=4:shiftwidth=4:
