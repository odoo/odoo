# -*- coding: utf-8 -*-
#----------------------------------------------------------
# ir_http modular http routing
#----------------------------------------------------------
import base64
import datetime
import hashlib
import logging
import mimetypes
import os
import re
import sys
import urllib2

import werkzeug
import werkzeug.exceptions
import werkzeug.routing
import werkzeug.urls
import werkzeug.utils

import openerp
import openerp.exceptions
import openerp.models
from openerp import http
from openerp.http import request, STATIC_CACHE
from openerp.modules.module import get_resource_path, get_module_path
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

class SignedIntConverter(werkzeug.routing.NumberConverter):
    regex = r'-?\d+'
    num_convert = int


class ir_http(osv.AbstractModel):
    _name = 'ir.http'
    _description = "HTTP routing"

    def _get_converters(self):
        return {'model': ModelConverter, 'models': ModelsConverter, 'int': SignedIntConverter}

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
            if request.uid is None:
                getattr(self, "_auth_method_%s" % auth_method)()
        except (openerp.exceptions.AccessDenied, openerp.http.SessionExpiredException, werkzeug.exceptions.HTTPException):
            raise
        except Exception:
            _logger.info("Exception during request Authentication.", exc_info=True)
            raise openerp.exceptions.AccessDenied()
        return auth_method

    def _serve_attachment(self):
        domain = [('type', '=', 'binary'), ('url', '=', request.httprequest.path)]
        attach = self.pool['ir.attachment'].search_read(request.cr, openerp.SUPERUSER_ID, domain, ['__last_update', 'datas', 'name', 'mimetype', 'checksum'], context=request.context)
        if attach:
            wdate = attach[0]['__last_update']
            datas = attach[0]['datas'] or ''
            name = attach[0]['name']
            checksum = attach[0]['checksum'] or hashlib.sha1(datas).hexdigest()

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

            response.set_etag(checksum)
            response.make_conditional(request.httprequest)

            if response.status_code == 304:
                return response

            response.mimetype = attach[0]['mimetype'] or 'application/octet-stream'
            response.data = datas.decode('base64')
            return response

    def _handle_exception(self, exception):
        # If handle_exception returns something different than None, it will be used as a response

        # This is done first as the attachment path may
        # not match any HTTP controller
        if isinstance(exception, werkzeug.exceptions.HTTPException) and exception.code == 404:
            attach = self._serve_attachment()
            if attach:
                return attach

        # Don't handle exception but use werkeug debugger if server in --dev mode
        if openerp.tools.config['dev_mode']:
            raise
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
            installed = request.registry._init_modules - {'web'}
            if openerp.tools.config['test_enable']:
                installed.add(openerp.modules.module.current_test)
            mods = [''] + openerp.conf.server_wide_modules + sorted(installed)
            self._routing_map = http.routing_map(mods, False, converters=self._get_converters())

        return self._routing_map

    def content_disposition(self, filename):
        filename = openerp.tools.ustr(filename)
        escaped = urllib2.quote(filename.encode('utf8'))
        browser = request.httprequest.user_agent.browser
        version = int((request.httprequest.user_agent.version or '0').split('.')[0])
        if browser == 'msie' and version < 9:
            return "attachment; filename=%s" % escaped
        elif browser == 'safari' and version < 537:
            return u"attachment; filename=%s" % filename.encode('ascii', 'replace')
        else:
            return "attachment; filename*=UTF-8''%s" % escaped

    def binary_content(self, xmlid=None, model='ir.attachment', id=None, field='datas', unique=False, filename=None, filename_field='datas_fname', download=False, mimetype=None, default_mimetype='application/octet-stream', env=None):
        """ Get file, attachment or downloadable content

        If the ``xmlid`` and ``id`` parameter is omitted, fetches the default value for the
        binary field (via ``default_get``), otherwise fetches the field for
        that precise record.

        :param str xmlid: xmlid of the record
        :param str model: name of the model to fetch the binary from
        :param int id: id of the record from which to fetch the binary
        :param str field: binary field
        :param bool unique: add a max-age for the cache control
        :param str filename: choose a filename
        :param str filename_field: if not create an filename with model-id-field
        :param bool download: apply headers to download the file
        :param str mimetype: mintype of the field (for headers)
        :param str default_mimetype: default mintype if no mintype found
        :param Environment env: by default use request.env
        :returns: (status, headers, content)
        """
        env = env or request.env
        # get object and content
        obj = None
        if xmlid:
            obj = env.ref(xmlid, False)
        elif id and model in env.registry:
            obj = env[model].browse(int(id))

        # obj exists
        if not obj or not obj.exists() or field not in obj:
            return (404, [], None)

        # check read access
        try:
            last_update = obj['__last_update']
        except openerp.exceptions.AccessError:
            return (403, [], None)

        status, headers, content = None, [], None

        # attachment by url check
        module_resource_path = None
        if model == 'ir.attachment' and obj.type == 'url' and obj.url:
            url_match = re.match("^/(\w+)/(.+)$", obj.url)
            if url_match:
                module = url_match.group(1)
                module_path = get_module_path(module)
                module_resource_path = get_resource_path(module, url_match.group(2))
                if module_path and module_resource_path:
                    module_path = os.path.join(os.path.normpath(module_path), '')  # join ensures the path ends with '/'
                    module_resource_path = os.path.normpath(module_resource_path)
                    if module_resource_path.startswith(module_path):
                        with open(module_resource_path, 'r') as f:
                            content = base64.b64encode(f.read())
                        last_update = str(os.path.getmtime(module_resource_path))

            if not module_resource_path:
                module_resource_path = obj.url

            if not content:
                status = 301
                content = module_resource_path
        else:
            content = obj[field] or ''

        # filename
        if not filename:
            if filename_field in obj:
                filename = obj[filename_field]
            elif module_resource_path:
                filename = os.path.basename(module_resource_path)
            else:
                filename = "%s-%s-%s" % (obj._model._name, obj.id, field)

        # mimetype
        if not mimetype:
            if 'mimetype' in obj and obj.mimetype and obj.mimetype != 'application/octet-stream':
                mimetype = obj.mimetype
            elif filename:
                mimetype = mimetypes.guess_type(filename)[0]
            elif getattr(env[model]._fields[field], 'attachment', False):
                # for binary fields, fetch the ir_attachement for mimetype check
                attach_mimetype = env['ir.attachment'].search_read(domain=[('res_model', '=', model), ('res_id', '=', id), ('res_field', '=', field)], fields=['mimetype'], limit=1)
                mimetype = attach_mimetype and attach_mimetype[0]['mimetype']
            if not mimetype:
                mimetype = default_mimetype
        headers.append(('Content-Type', mimetype))

        # cache
        etag = hasattr(request, 'httprequest') and request.httprequest.headers.get('If-None-Match')
        retag = hashlib.md5(last_update).hexdigest()
        status = status or (304 if etag == retag else 200)
        headers.append(('ETag', retag))
        headers.append(('Cache-Control', 'max-age=%s' % (STATIC_CACHE if unique else 0)))

        # content-disposition default name
        if download:
            headers.append(('Content-Disposition', self.content_disposition(filename)))

        return (status, headers, content)


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
