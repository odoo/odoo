#----------------------------------------------------------
# ir_http modular http routing
#----------------------------------------------------------
import logging

import werkzeug.exceptions
import werkzeug.routing

import openerp
from openerp import http
from openerp.http import request
from openerp.osv import osv

_logger = logging.getLogger(__name__)

class ir_http(osv.osv):
    _name = 'ir.http'
    _description = "HTTP routing"

    def __init__(self, registry, cr):
        osv.osv.__init__(self, registry, cr)

    def _find_handler(self):
        # TODO move to __init__(self, registry, cr)
        if not hasattr(self, 'routing_map'):
            _logger.info("Generating routing map")
            cr = request.cr
            m = request.registry.get('ir.module.module')
            ids = m.search(cr, openerp.SUPERUSER_ID, [('state', '=', 'installed'), ('name', '!=', 'web')])
            installed = set(x['name'] for x in m.read(cr, 1, ids, ['name']))
            mods = ['', "web"] + sorted(installed)
            self.routing_map = http.routing_map(mods, False)

        # fallback to non-db handlers
        path = request.httprequest.path
        urls = self.routing_map.bind_to_environ(request.httprequest.environ)

        return urls.match(path)

    def _auth_method_user(self):
        request.uid = request.session.uid
        if not request.uid:
            raise SessionExpiredException("Session expired")

    def _auth_method_admin(self):
        if not request.db:
            raise SessionExpiredException("No valid database for request %s" % request.httprequest)
        request.uid = openerp.SUPERUSER_ID

    def _auth_method_none(self):
        request.disable_db = True
        request.uid = None

    def _authenticate(self, func, arguments):
        auth_method = getattr(func, "auth", "user")
        if request.session.uid:
            try:
                request.session.check_security()
            except SessionExpiredException, e:
                request.session.logout()
                raise SessionExpiredException("Session expired for request %s" % request.httprequest)
        getattr(self, "_auth_method_%s" % auth_method)()
        return auth_method

    def _handle_404(self, exception):
        raise exception

    def _handle_403(self, exception):
        raise exception

    def _handle_500(self, exception):
        raise exception

    def _dispatch(self):
        # locate the controller method
        try:
            func, arguments = self._find_handler()
        except werkzeug.exceptions.NotFound, e:
            return self._handle_404(e)

        # check authentication level
        try:
            auth_method = self._authenticate(func, arguments)
        except werkzeug.exceptions.NotFound, e:
            return self._handle_403(e)

        # set and execute handler
        try:
            request.set_handler(func, arguments, auth_method)
            result = request.dispatch()
        except Exception, e:
            return  self._handle_500(e)
        return result

# vim:et:
