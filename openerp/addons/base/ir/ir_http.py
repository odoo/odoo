#----------------------------------------------------------
# ir_http modular http routing
#----------------------------------------------------------
import logging
import re
import sys

import werkzeug.exceptions
import werkzeug.routing

import openerp
from openerp import http
from openerp.http import request
from openerp.osv import osv, orm

_logger = logging.getLogger(__name__)


# FIXME: replace by proxy on request.uid?
_uid = object()

class ModelConverter(werkzeug.routing.BaseConverter):

    def __init__(self, url_map, model=False):
        super(ModelConverter, self).__init__(url_map)
        self.model = model
        self.regex = '([0-9]+)'

    def to_python(self, value):
        m = re.match(self.regex, value)
        return request.registry[self.model].browse(
            request.cr, _uid, int(m.group(1)), context=request.context)

    def to_url(self, value):
        return value.id

class ModelsConverter(werkzeug.routing.BaseConverter):

    def __init__(self, url_map, model=False):
        super(ModelsConverter, self).__init__(url_map)
        self.model = model
        # TODO add support for slug in the form [A-Za-z0-9-] bla-bla-89 -> id 89
        self.regex = '([0-9,]+)'

    def to_python(self, value):
        # TODO:
        # - raise routing.ValidationError() if no browse record can be createdm
        # - support slug
        return request.registry[self.model].browse(request.cr, _uid, [int(i) for i in value.split(',')], context=request.context)

    def to_url(self, value):
        return ",".join(i.id for i in value)

class ir_http(osv.AbstractModel):
    _name = 'ir.http'
    _description = "HTTP routing"

    def _get_converters(self):
        return {'model': ModelConverter, 'models': ModelsConverter}

    def _find_handler(self):
        return self.routing_map().bind_to_environ(request.httprequest.environ).match()

    def _auth_method_user(self):
        request.uid = request.session.uid
        if not request.uid:
            raise http.SessionExpiredException("Session expired")

    def _auth_method_admin(self):
        if not request.db:
            raise http.SessionExpiredException("No valid database for request %s" % request.httprequest)
        request.uid = openerp.SUPERUSER_ID

    def _auth_method_none(self):
        request.disable_db = True
        request.uid = None

    def _authenticate(self, auth_method='user'):
        if request.session.uid:
            try:
                request.session.check_security()
                # what if error in security.check()
                #   -> res_users.check()
                #   -> res_users.check_credentials()
            except Exception:
                request.session.logout()
        getattr(self, "_auth_method_%s" % auth_method)()
        return auth_method

    def _handle_exception(self, exception):
        if isinstance(exception, openerp.exceptions.AccessError):
            code = 403
        else:
            code = getattr(exception, 'code', 500)

        fn = getattr(self, '_handle_%d' % code, self._handle_unknown_exception)
        return fn(exception)

    def _handle_unknown_exception(self, exception):
        raise exception

    def _dispatch(self):
        # locate the controller method
        try:
            func, arguments = self._find_handler()
        except werkzeug.exceptions.NotFound, e:
            return self._handle_exception(e)

        # check authentication level
        try:
            auth_method = self._authenticate(getattr(func, "auth", None))
        except Exception:
            # force a Forbidden exception with the original traceback
            return self._handle_exception(
                convert_exception_to(
                    werkzeug.exceptions.Forbidden))

        # post process arg to set uid on browse records
        for arg in arguments.itervalues():
            if isinstance(arg, orm.browse_record) and arg._uid is _uid:
                arg._uid = request.uid

        # set and execute handler
        try:
            request.set_handler(func, arguments, auth_method)
            result = request.dispatch()
            if isinstance(result, Exception):
                raise result
        except Exception, e:
            return self._handle_exception(e)

        return result

    def routing_map(self):
        if not hasattr(self, '_routing_map'):
            _logger.info("Generating routing map")
            cr = request.cr
            m = request.registry.get('ir.module.module')
            ids = m.search(cr, openerp.SUPERUSER_ID, [('state', '=', 'installed'), ('name', '!=', 'web')], context=request.context)
            installed = set(x['name'] for x in m.read(cr, 1, ids, ['name'], context=request.context))
            mods = ['', "web"] + sorted(installed)
            self._routing_map = http.routing_map(mods, False, converters=self._get_converters())

        return self._routing_map

def convert_exception_to(to_type, with_message=False):
    """ Should only be called from an exception handler. Fetches the current
    exception data from sys.exc_info() and creates a new exception of type
    ``to_type`` with the original traceback.

    If ``with_message`` is ``True``, sets the new exception's message to be
    the stringification of the original exception. If ``False``, does not
    set the new exception's message. Otherwise, uses ``with_message`` as the
    new exception's message.

    :type with_message: str|bool
    """
    etype, original, tb = sys.exc_info()
    try:
        if with_message is False:
            message = None
        elif with_message is True:
            message = str(original)
        else:
            message = str(with_message)

        raise to_type, message, tb
    except to_type, e:
        return e

# vim:et:
