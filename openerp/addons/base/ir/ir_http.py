#----------------------------------------------------------
# ir_http modular http routing
#----------------------------------------------------------
import datetime
import hashlib
import logging
import mimetypes
import re
import sys

import werkzeug
import werkzeug.exceptions
import werkzeug.routing
import werkzeug.urls
import werkzeug.utils

import openerp
import openerp.exceptions
import openerp.models
from openerp import http
from openerp.http import request
from openerp.osv import osv, orm

_logger = logging.getLogger(__name__)

UID_PLACEHOLDER = object()

class ModelConverter(werkzeug.routing.BaseConverter):

    def __init__(self, url_map, model=False):
        super(ModelConverter, self).__init__(url_map)
        self.model = model
        self.regex = '([0-9]+)'

    def to_python(self, value):
        m = re.match(self.regex, value)
        return request.registry[self.model].browse(
            request.cr, UID_PLACEHOLDER, int(m.group(1)), context=request.context)

    def to_url(self, value):
        return value.id

class ModelsConverter(werkzeug.routing.BaseConverter):

    def __init__(self, url_map, model=False):
        super(ModelsConverter, self).__init__(url_map)
        self.model = model
        # TODO add support for slug in the form [A-Za-z0-9-] bla-bla-89 -> id 89
        self.regex = '([0-9,]+)'

    def to_python(self, value):
        return request.registry[self.model].browse(request.cr, UID_PLACEHOLDER, [int(i) for i in value.split(',')], context=request.context)

    def to_url(self, value):
        return ",".join(i.id for i in value)

class ir_http(osv.AbstractModel):
    _name = 'ir.http'
    _description = "HTTP routing"

    def _get_converters(self):
        return {'model': ModelConverter, 'models': ModelsConverter}

    def _find_handler(self, return_rule=False):
        return self.routing_map().bind_to_environ(request.httprequest.environ).match(return_rule=return_rule)

    def _auth_method_user(self):
        request.uid = request.session.uid
        if not request.uid:
            raise http.SessionExpiredException("Session expired")

    def _auth_method_none(self):
        request.uid = None

    def _auth_method_public(self):
        if not request.session.uid:
            dummy, request.uid = self.pool['ir.model.data'].get_object_reference(request.cr, openerp.SUPERUSER_ID, 'base', 'public_user')
        else:
            request.uid = request.session.uid

    def _authenticate(self, auth_method='user'):
        try:
            if request.session.uid:
                try:
                    request.session.check_security()
                    # what if error in security.check()
                    #   -> res_users.check()
                    #   -> res_users.check_credentials()
                except (openerp.exceptions.AccessDenied, openerp.http.SessionExpiredException):
                    # All other exceptions mean undetermined status (e.g. connection pool full),
                    # let them bubble up
                    request.session.logout(keep_db=True)
            getattr(self, "_auth_method_%s" % auth_method)()
        except (openerp.exceptions.AccessDenied, openerp.http.SessionExpiredException, werkzeug.exceptions.HTTPException):
            raise
        except Exception:
            _logger.exception("Exception during request Authentication.")
            raise openerp.exceptions.AccessDenied()
        return auth_method

    def _serve_attachment(self):
        domain = [('type', '=', 'binary'), ('url', '=', request.httprequest.path)]
        attach = self.pool['ir.attachment'].search_read(
            request.cr, openerp.SUPERUSER_ID, domain,
            ['__last_update', 'datas', 'datas_fname', 'name'],
            context=request.context)
        if attach:
            wdate = attach[0]['__last_update']
            datas = attach[0]['datas'] or ''
            name = attach[0]['name']

            if (not datas and name != request.httprequest.path and
                    name.startswith(('http://', 'https://', '/'))):
                return werkzeug.utils.redirect(name, 301)

            response = werkzeug.wrappers.Response()
            server_format = openerp.tools.misc.DEFAULT_SERVER_DATETIME_FORMAT
            try:
                response.last_modified = datetime.datetime.strptime(wdate, server_format + '.%f')
            except ValueError:
                # just in case we have a timestamp without microseconds
                response.last_modified = datetime.datetime.strptime(wdate, server_format)

            response.set_etag(hashlib.sha1(datas).hexdigest())
            response.make_conditional(request.httprequest)

            if response.status_code == 304:
                return response

            response.mimetype = (mimetypes.guess_type(attach[0]['datas_fname'] or '')[0] or
                                 'application/octet-stream')
            response.data = datas.decode('base64')
            return response

    def _handle_exception(self, exception):
        # This is done first as the attachment path may
        # not match any HTTP controller.
        if isinstance(exception, werkzeug.exceptions.HTTPException) and exception.code == 404:
            attach = self._serve_attachment()
            if attach:
                return attach

        # If handle_exception returns something different than None, it will be used as a response
        try:
            return request._handle_exception(exception)
        except openerp.exceptions.AccessDenied:
            return werkzeug.exceptions.Forbidden()

    def _dispatch(self):
        # locate the controller method
        try:
            rule, arguments = self._find_handler(return_rule=True)
            func = rule.endpoint
        except werkzeug.exceptions.NotFound, e:
            return self._handle_exception(e)

        # check authentication level
        try:
            auth_method = self._authenticate(func.routing["auth"])
        except Exception as e:
            return self._handle_exception(e)

        processing = self._postprocess_args(arguments, rule)
        if processing:
            return processing


        # set and execute handler
        try:
            request.set_handler(func, arguments, auth_method)
            result = request.dispatch()
            if isinstance(result, Exception):
                raise result
        except Exception, e:
            return self._handle_exception(e)

        return result

    def _postprocess_args(self, arguments, rule):
        """ post process arg to set uid on browse records """
        for name, arg in arguments.items():
            if isinstance(arg, orm.browse_record) and arg._uid is UID_PLACEHOLDER:
                arguments[name] = arg.sudo(request.uid)
                try:
                    arg.exists()
                except openerp.models.MissingError:
                    return self._handle_exception(werkzeug.exceptions.NotFound())

    def routing_map(self):
        if not hasattr(self, '_routing_map'):
            _logger.info("Generating routing map")
            cr = request.cr
            m = request.registry.get('ir.module.module')
            ids = m.search(cr, openerp.SUPERUSER_ID, [('state', '=', 'installed'), ('name', '!=', 'web')], context=request.context)
            installed = set(x['name'] for x in m.read(cr, 1, ids, ['name'], context=request.context))
            if openerp.tools.config['test_enable']:
                installed.add(openerp.modules.module.current_test)
            mods = [''] + openerp.conf.server_wide_modules + sorted(installed)
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
