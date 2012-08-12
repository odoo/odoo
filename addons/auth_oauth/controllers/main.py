import logging

import werkzeug.urls

import openerp.modules.registry
import openerp.addons.web.controllers.main
import openerp.addons.web.common.http as openerpweb

_logger = logging.getLogger(__name__)

class OAuthController(openerpweb.Controller):
    _cp_path = '/auth_oauth'

    @openerpweb.httprequest
    def signin(self, req, **kw):
        dbname = kw.get("state")
        registry = openerp.modules.registry.RegistryManager.get(dbname)
        cr = registry.db.cursor()
        try:
            try:
                u = registry.get('res.users')
                r = u.auth_oauth(cr, 1, kw)
                cr.commit()
                return openerp.addons.web.controllers.main.login_and_redirect(req, *r)
                # or
                req.authenticate(*r)
                url = "/"
            except AttributeError:
                # auth_signup is not installed
                url = "/#action=auth_signup&error=1"
            except Exception,e:
                # signup error
                url = "/#action=auth_signup&error=2"
        finally:
            cr.close()
        return ""
        return werkzeug.utils.redirect(url)

# vim:expandtab:tabstop=4:softtabstop=4:shiftwidth=4:
