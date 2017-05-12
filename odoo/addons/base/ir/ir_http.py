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

import odoo
from odoo import api, http, models, tools, SUPERUSER_ID
from odoo.exceptions import AccessDenied, AccessError
from odoo.http import request, STATIC_CACHE, content_disposition
from odoo.tools.mimetypes import guess_mimetype
from odoo.modules.module import get_resource_path, get_module_path

_logger = logging.getLogger(__name__)

UID_PLACEHOLDER = object()


class ModelConverter(werkzeug.routing.BaseConverter):

    def __init__(self, url_map, model=False):
        super(ModelConverter, self).__init__(url_map)
        self.model = model
        self.regex = r'([0-9]+)'

    def to_python(self, value):
        env = api.Environment(request.cr, UID_PLACEHOLDER, request.context)
        return env[self.model].browse(int(value))

    def to_url(self, value):
        return value.id


class ModelsConverter(werkzeug.routing.BaseConverter):

    def __init__(self, url_map, model=False):
        super(ModelsConverter, self).__init__(url_map)
        self.model = model
        # TODO add support for slug in the form [A-Za-z0-9-] bla-bla-89 -> id 89
        self.regex = r'([0-9,]+)'

    def to_python(self, value):
        env = api.Environment(request.cr, UID_PLACEHOLDER, request.context)
        return env[self.model].browse(map(int, value.split(',')))

    def to_url(self, value):
        return ",".join(value.ids)


class SignedIntConverter(werkzeug.routing.NumberConverter):
    regex = r'-?\d+'
    num_convert = int


class IrHttp(models.AbstractModel):
    _name = 'ir.http'
    _description = "HTTP routing"

    @classmethod
    def _get_converters(cls):
        return {'model': ModelConverter, 'models': ModelsConverter, 'int': SignedIntConverter}

    @classmethod
    def _find_handler(cls, return_rule=False):
        return cls.routing_map().bind_to_environ(request.httprequest.environ).match(return_rule=return_rule)

    @classmethod
    def _auth_method_user(cls):
        request.uid = request.session.uid
        if not request.uid:
            raise http.SessionExpiredException("Session expired")

    @classmethod
    def _auth_method_none(cls):
        request.uid = None

    @classmethod
    def _auth_method_public(cls):
        if not request.session.uid:
            request.uid = request.env.ref('base.public_user').id
        else:
            request.uid = request.session.uid

    @classmethod
    def _authenticate(cls, auth_method='user'):
        try:
            if request.session.uid:
                try:
                    request.session.check_security()
                    # what if error in security.check()
                    #   -> res_users.check()
                    #   -> res_users.check_credentials()
                except (AccessDenied, http.SessionExpiredException):
                    # All other exceptions mean undetermined status (e.g. connection pool full),
                    # let them bubble up
                    request.session.logout(keep_db=True)
            if request.uid is None:
                getattr(cls, "_auth_method_%s" % auth_method)()
        except (AccessDenied, http.SessionExpiredException, werkzeug.exceptions.HTTPException):
            raise
        except Exception:
            _logger.info("Exception during request Authentication.", exc_info=True)
            raise AccessDenied()
        return auth_method

    @classmethod
    def _serve_attachment(cls):
        env = api.Environment(request.cr, SUPERUSER_ID, request.context)
        domain = [('type', '=', 'binary'), ('url', '=', request.httprequest.path)]
        fields = ['__last_update', 'datas', 'name', 'mimetype', 'checksum']
        attach = env['ir.attachment'].search_read(domain, fields)
        if attach:
            wdate = attach[0]['__last_update']
            datas = attach[0]['datas'] or ''
            name = attach[0]['name']
            checksum = attach[0]['checksum'] or hashlib.sha1(datas).hexdigest()

            if (not datas and name != request.httprequest.path and
                    name.startswith(('http://', 'https://', '/'))):
                return werkzeug.utils.redirect(name, 301)

            response = werkzeug.wrappers.Response()
            server_format = tools.DEFAULT_SERVER_DATETIME_FORMAT
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

    @classmethod
    def _handle_exception(cls, exception):
        # If handle_exception returns something different than None, it will be used as a response

        # This is done first as the attachment path may
        # not match any HTTP controller
        if isinstance(exception, werkzeug.exceptions.HTTPException) and exception.code == 404:
            attach = cls._serve_attachment()
            if attach:
                return attach

        # Don't handle exception but use werkeug debugger if server in --dev mode
        if 'werkzeug' in tools.config['dev_mode']:
            raise
        try:
            return request._handle_exception(exception)
        except AccessDenied:
            return werkzeug.exceptions.Forbidden()

    @classmethod
    def _dispatch(cls):
        # locate the controller method
        try:
            rule, arguments = cls._find_handler(return_rule=True)
            func = rule.endpoint
        except werkzeug.exceptions.NotFound, e:
            return cls._handle_exception(e)

        # check authentication level
        try:
            auth_method = cls._authenticate(func.routing["auth"])
        except Exception as e:
            return cls._handle_exception(e)

        processing = cls._postprocess_args(arguments, rule)
        if processing:
            return processing

        # set and execute handler
        try:
            request.set_handler(func, arguments, auth_method)
            result = request.dispatch()
            if isinstance(result, Exception):
                raise result
        except Exception, e:
            return cls._handle_exception(e)

        return result

    @classmethod
    def _postprocess_args(cls, arguments, rule):
        """ post process arg to set uid on browse records """
        for name, arg in arguments.items():
            if isinstance(arg, models.BaseModel) and arg._uid is UID_PLACEHOLDER:
                arguments[name] = arg.sudo(request.uid)
                if not arg.exists():
                    return cls._handle_exception(werkzeug.exceptions.NotFound())

    @classmethod
    def routing_map(cls):
        if not hasattr(cls, '_routing_map'):
            _logger.info("Generating routing map")
            installed = request.registry._init_modules - {'web'}
            if tools.config['test_enable']:
                installed.add(odoo.modules.module.current_test)
            mods = [''] + odoo.conf.server_wide_modules + sorted(installed)
            # Note : when routing map is generated, we put it on the class `cls`
            # to make it available for all instance. Since `env` create an new instance
            # of the model, each instance will regenared its own routing map and thus
            # regenerate its EndPoint. The routing map should be static.
            cls._routing_map = http.routing_map(mods, False, converters=cls._get_converters())
        return cls._routing_map

    @classmethod
    def _clear_routing_map(cls):
        if hasattr(cls, '_routing_map'):
            del cls._routing_map

    @classmethod
    def content_disposition(cls, filename):
        return content_disposition(filename)

    @classmethod
    def binary_content(cls, xmlid=None, model='ir.attachment', id=None, field='datas', unique=False, filename=None, filename_field='datas_fname', download=False, mimetype=None, default_mimetype='application/octet-stream', env=None):
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
        except AccessError:
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
                        with open(module_resource_path, 'rb') as f:
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
                filename = "%s-%s-%s" % (obj._name, obj.id, field)

        # mimetype
        mimetype = 'mimetype' in obj and obj.mimetype or False
        if not mimetype:
            if filename:
                mimetype = mimetypes.guess_type(filename)[0]
            if not mimetype and getattr(env[model]._fields[field], 'attachment', False):
                # for binary fields, fetch the ir_attachement for mimetype check
                attach_mimetype = env['ir.attachment'].search_read(domain=[('res_model', '=', model), ('res_id', '=', id), ('res_field', '=', field)], fields=['mimetype'], limit=1)
                mimetype = attach_mimetype and attach_mimetype[0]['mimetype']
            if not mimetype:
                mimetype = guess_mimetype(base64.b64decode(content), default=default_mimetype)

        headers += [('Content-Type', mimetype), ('X-Content-Type-Options', 'nosniff')]

        # cache
        etag = hasattr(request, 'httprequest') and request.httprequest.headers.get('If-None-Match')
        retag = '"%s"' % hashlib.md5(last_update).hexdigest()
        status = status or (304 if etag == retag else 200)
        headers.append(('ETag', retag))
        headers.append(('Cache-Control', 'max-age=%s' % (STATIC_CACHE if unique else 0)))

        # content-disposition default name
        if download:
            headers.append(('Content-Disposition', cls.content_disposition(filename)))
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
    except to_type as e:
        return e
