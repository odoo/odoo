import logging

import werkzeug.urls

import openerp.modules.registry
from openerp.addons.web.controllers.main import login_and_redirect
import openerp.addons.web.common.http as openerpweb

_logger = logging.getLogger(__name__)

class OpenIDController(openerpweb.Controller):
    _cp_path = '/auth_signup'

    @openerpweb.httprequest
    def signup(self, req, dbname, name, login, password):
        registry = openerp.modules.registry.RegistryManager.get(dbname)
        cr = registry.db.cursor()
        url = '/'
        try:
            try:
                Users = registry.get('res.users')
                credentials = Users.auth_signup(cr, 1, name, login, password)
                cr.commit()
                return login_and_redirect(req, *credentials)
            except AttributeError:
                # auth_signup is not installed
                _logger.exception('attribute error when signup')
                url = "/#action=auth_signup&error=NA"   # Not Available
            except Exception:
                # signup error
                _logger.exception('error when signup')
                url = "/#action=auth_signup&error=UE"   # Unexcpected Error
        finally:
            cr.close()
        return werkzeug.utils.redirect(url)

# vim:expandtab:tabstop=4:softtabstop=4:shiftwidth=4:
