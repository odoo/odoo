import logging
import urllib2

import werkzeug.urls
import werkzeug.utils

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
                # tmp = openerp.addons.web.controllers.main.login_and_redirect(req, cr, *r)
                # req.session.authenticate(db, login, key, {})
                # redirect = werkzeug.utils.redirect("http://localhost:8069/", 303)
                # redirect.autocorrect_location_header = False
                # cookie_val = urllib2.quote(simplejson.dumps(req.session_id))
                # redirect.set_cookie('instance0|session_id', cookie_val)
                print r
                return openerp.addons.web.controllers.main.login_and_redirect(req, *r)
            except AttributeError:
                # auth_signup is not installed
                url = "/#action=auth_signup&error=1"
            except Exception,e:
                # signup error
                url = "/#action=auth_signup&error=2"
        finally:
            cr.close()
        return werkzeug.utils.redirect("https://localhost")

# vim:expandtab:tabstop=4:softtabstop=4:shiftwidth=4:
