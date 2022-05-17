# -*- coding: utf-8 -*-
#----------------------------------------------------------
# ir_http modular http routing
#----------------------------------------------------------
import base64
import hashlib
import logging
import mimetypes
import os
import re
import sys
import traceback

import werkzeug
import werkzeug.exceptions
import werkzeug.routing
import werkzeug.utils

import odoo
from odoo import api, http, models, tools, SUPERUSER_ID
from odoo.exceptions import AccessDenied, AccessError, MissingError
from odoo.http import request, content_disposition, Response
from odoo.tools import consteq, pycompat
from odoo.tools.mimetypes import get_extension, guess_mimetype
from odoo.modules.module import get_resource_path, get_module_path

from odoo.http import ALLOWED_DEBUG_MODES
from odoo.tools.misc import str2bool

_logger = logging.getLogger(__name__)


class RequestUID(object):
    def __init__(self, **kw):
        self.__dict__.update(kw)


class ModelConverter(werkzeug.routing.BaseConverter):

    def __init__(self, url_map, model=False):
        super(ModelConverter, self).__init__(url_map)
        self.model = model
        self.regex = r'([0-9]+)'

    def to_python(self, value):
        _uid = RequestUID(value=value, converter=self)
        env = api.Environment(request.cr, _uid, request.context)
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
        _uid = RequestUID(value=value, converter=self)
        env = api.Environment(request.cr, _uid, request.context)
        return env[self.model].browse(int(v) for v in value.split(','))

    def to_url(self, value):
        return ",".join(value.ids)


class SignedIntConverter(werkzeug.routing.NumberConverter):
    regex = r'-?\d+'
    num_convert = int


class IrHttp(models.AbstractModel):
    _name = 'ir.http'
    _description = "HTTP Routing"

    #------------------------------------------------------
    # Routing map
    #------------------------------------------------------

    @classmethod
    def _get_converters(cls):
        return {'model': ModelConverter, 'models': ModelsConverter, 'int': SignedIntConverter}

    @classmethod
    def _match(cls, path_info, key=None):
        return cls.routing_map().bind_to_environ(request.httprequest.environ).match(path_info=path_info, return_rule=True)

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
    def _authenticate(cls, endpoint):
        auth_method = endpoint.routing["auth"]
        if request._is_cors_preflight(endpoint):
            auth_method = 'none'
        try:
            if request.session.uid:
                try:
                    request.session.check_security()
                    # what if error in security.check()
                    #   -> res_users.check()
                    #   -> res_users._check_credentials()
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
    def _handle_debug(cls):
        # Store URL debug mode (might be empty) into session
        if 'debug' in request.httprequest.args:
            debug_mode = []
            for debug in request.httprequest.args['debug'].split(','):
                if debug not in ALLOWED_DEBUG_MODES:
                    debug = '1' if str2bool(debug, debug) else ''
                debug_mode.append(debug)
            debug_mode = ','.join(debug_mode)

            # Write on session only when needed
            if debug_mode != request.session.debug:
                request.session.debug = debug_mode

    @classmethod
    def _serve_attachment(cls):
        env = api.Environment(request.cr, SUPERUSER_ID, request.context)
        attach = env['ir.attachment'].get_serve_attachment(request.httprequest.path, extra_fields=['name', 'checksum'])
        if attach:
            wdate = attach[0]['__last_update']
            datas = attach[0]['datas'] or b''
            name = attach[0]['name']
            checksum = attach[0]['checksum'] or hashlib.sha512(datas).hexdigest()[:64]  # sha512/256

            if (not datas and name != request.httprequest.path and
                    name.startswith(('http://', 'https://', '/'))):
                return request.redirect(name, 301, local=False)

            response = werkzeug.wrappers.Response()
            response.last_modified = wdate

            response.set_etag(checksum)
            response.make_conditional(request.httprequest)

            if response.status_code == 304:
                return response

            response.mimetype = attach[0]['mimetype'] or 'application/octet-stream'
            response.data = base64.b64decode(datas)
            return response

    @classmethod
    def _serve_fallback(cls, exception):
        # serve attachment
        attach = cls._serve_attachment()
        if attach:
            return attach
        return False

    @classmethod
    def _handle_exception(cls, exception):
        # in case of Exception, e.g. 404, we don't step into _dispatch
        cls._handle_debug()

        # If handle_exception returns something different than None, it will be used as a response

        # This is done first as the attachment path may
        # not match any HTTP controller
        if (isinstance(exception, werkzeug.exceptions.HTTPException) and exception.code == 404) or \
           (isinstance(exception, odoo.exceptions.AccessError)):
            serve = cls._serve_fallback(exception)
            if serve:
                return serve

        # Don't handle exception but use werkzeug debugger if server in --dev mode
        # Don't intercept JSON request to respect the JSON Spec and return exception as JSON
        # "The Response is expressed as a single JSON Object, with the following members:
        #   jsonrpc, result, error, id"
        if ('werkzeug' in tools.config['dev_mode']
                and not isinstance(exception, werkzeug.exceptions.NotFound)
                and request._request_type != 'json'):
            raise exception

        try:
            return request._handle_exception(exception)
        except AccessDenied:
            return werkzeug.exceptions.Forbidden()

    @classmethod
    def _dispatch(cls):
        cls._handle_debug()

        # locate the controller method
        try:
            rule, arguments = cls._match(request.httprequest.path)
            func = rule.endpoint
        except werkzeug.exceptions.NotFound as e:
            return cls._handle_exception(e)

        # check authentication level
        try:
            auth_method = cls._authenticate(func)
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
        except Exception as e:
            return cls._handle_exception(e)

        return result

    @classmethod
    def _redirect(cls, location, code=303):
        return werkzeug.utils.redirect(location, code=code, Response=Response)

    @classmethod
    def _postprocess_args(cls, arguments, rule):
        """ post process arg to set uid on browse records """
        for key, val in list(arguments.items()):
            # Replace uid placeholder by the current request.uid
            if isinstance(val, models.BaseModel) and isinstance(val._uid, RequestUID):
                arguments[key] = val.with_user(request.uid)

    @classmethod
    def _generate_routing_rules(cls, modules, converters):
        return http._generate_routing_rules(modules, False, converters)

    @classmethod
    def routing_map(cls, key=None):

        if not hasattr(cls, '_routing_map'):
            cls._routing_map = {}
            cls._rewrite_len = {}

        if key not in cls._routing_map:
            _logger.info("Generating routing map for key %s" % str(key))
            installed = request.registry._init_modules | set(odoo.conf.server_wide_modules)
            if tools.config['test_enable'] and odoo.modules.module.current_test:
                installed.add(odoo.modules.module.current_test)
            mods = sorted(installed)
            # Note : when routing map is generated, we put it on the class `cls`
            # to make it available for all instance. Since `env` create an new instance
            # of the model, each instance will regenared its own routing map and thus
            # regenerate its EndPoint. The routing map should be static.
            routing_map = werkzeug.routing.Map(strict_slashes=False, converters=cls._get_converters())
            for url, endpoint, routing in cls._generate_routing_rules(mods, converters=cls._get_converters()):
                xtra_keys = 'defaults subdomain build_only strict_slashes redirect_to alias host'.split()
                kw = {k: routing[k] for k in xtra_keys if k in routing}
                rule = werkzeug.routing.Rule(url, endpoint=endpoint, methods=routing['methods'], **kw)
                rule.merge_slashes = False
                routing_map.add(rule)
            cls._routing_map[key] = routing_map
        return cls._routing_map[key]

    @classmethod
    def _clear_routing_map(cls):
        if hasattr(cls, '_routing_map'):
            cls._routing_map = {}
            _logger.debug("Clear routing map")

    #------------------------------------------------------
    # Binary server
    #------------------------------------------------------

    @classmethod
    def _xmlid_to_obj(cls, env, xmlid):
        return env.ref(xmlid, False)

    def _get_record_and_check(self, xmlid=None, model=None, id=None, field='datas', access_token=None):
        # get object and content
        record = None
        if xmlid:
            record = self._xmlid_to_obj(self.env, xmlid)
        elif id and model in self.env:
            record = self.env[model].browse(int(id))

        # obj exists
        if not record or field not in record:
            return None, 404

        try:
            if model == 'ir.attachment':
                record_sudo = record.sudo()
                if access_token and not consteq(record_sudo.access_token or '', access_token):
                    return None, 403
                elif (access_token and consteq(record_sudo.access_token or '', access_token)):
                    record = record_sudo
                elif record_sudo.public:
                    record = record_sudo
                elif self.env.user.has_group('base.group_portal'):
                    # Check the read access on the record linked to the attachment
                    # eg: Allow to download an attachment on a task from /my/task/task_id
                    record.check('read')
                    record = record_sudo

            # check read access
            try:
                # We have prefetched some fields of record, among which the field
                # 'write_date' used by '__last_update' below. In order to check
                # access on record, we have to invalidate its cache first.
                if not record.env.su:
                    record._cache.clear()
                record['__last_update']
            except AccessError:
                return None, 403

            return record, 200
        except MissingError:
            return None, 404

    @classmethod
    def _binary_ir_attachment_redirect_content(cls, record, default_mimetype='application/octet-stream'):
        # mainly used for theme images attachemnts
        status = content = filename = filehash = None
        mimetype = getattr(record, 'mimetype', False)
        if record.type == 'url' and record.url:
            # if url in in the form /somehint server locally
            url_match = re.match("^/(\w+)/(.+)$", record.url)
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
                        status = 200
                        filename = os.path.basename(module_resource_path)
                        mimetype = guess_mimetype(base64.b64decode(content), default=default_mimetype)
                        filehash = '"%s"' % hashlib.md5(pycompat.to_text(content).encode('utf-8')).hexdigest()

            if not content:
                status = 301
                content = record.url

        return status, content, filename, mimetype, filehash

    def _binary_record_content(
            self, record, field='datas', filename=None,
            filename_field='name', default_mimetype='application/octet-stream'):

        model = record._name
        mimetype = 'mimetype' in record and record.mimetype or False
        content = None
        filehash = 'checksum' in record and record['checksum'] or False

        field_def = record._fields[field]
        if field_def.type == 'binary' and field_def.attachment and not field_def.related:
            if model != 'ir.attachment':
                field_attachment = self.env['ir.attachment'].sudo().search_read(domain=[('res_model', '=', model), ('res_id', '=', record.id), ('res_field', '=', field)], fields=['datas', 'mimetype', 'checksum'], limit=1)
                if field_attachment:
                    mimetype = field_attachment[0]['mimetype']
                    content = field_attachment[0]['datas']
                    filehash = field_attachment[0]['checksum']
            else:
                mimetype = record['mimetype']
                content = record['datas']
                filehash = record['checksum']

        if not content:
            content = record[field] or ''

        # filename
        if not filename:
            if filename_field in record:
                filename = record[filename_field]
            if not filename:
                filename = "%s-%s-%s" % (record._name, record.id, field)

        if not mimetype:
            try:
                decoded_content = base64.b64decode(content)
            except base64.binascii.Error:  # if we could not decode it, no need to pass it down: it would crash elsewhere...
                return (404, [], None)
            mimetype = guess_mimetype(decoded_content, default=default_mimetype)

        # extension
        has_extension = get_extension(filename) or mimetypes.guess_type(filename)[0]
        if not has_extension:
            extension = mimetypes.guess_extension(mimetype)
            if extension:
                filename = "%s%s" % (filename, extension)

        if not filehash:
            filehash = '"%s"' % hashlib.md5(pycompat.to_text(content).encode('utf-8')).hexdigest()

        status = 200 if content else 404
        return status, content, filename, mimetype, filehash

    def _binary_set_headers(self, status, content, filename, mimetype, unique, filehash=None, download=False):
        headers = [('Content-Type', mimetype), ('X-Content-Type-Options', 'nosniff'), ('Content-Security-Policy', "default-src 'none'")]
        # cache
        etag = bool(request) and request.httprequest.headers.get('If-None-Match')
        status = status or 200
        if filehash:
            headers.append(('ETag', filehash))
            if etag == filehash and status == 200:
                status = 304
        headers.append(('Cache-Control', 'max-age=%s' % (http.STATIC_CACHE_LONG if unique else 0)))
        # content-disposition default name
        if download:
            headers.append(('Content-Disposition', content_disposition(filename)))

        return (status, headers, content)

    def binary_content(self, xmlid=None, model='ir.attachment', id=None, field='datas',
                       unique=False, filename=None, filename_field='name', download=False,
                       mimetype=None, default_mimetype='application/octet-stream',
                       access_token=None):
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
        :param str access_token: optional token for unauthenticated access
                                 only available  for ir.attachment
        :returns: (status, headers, content)
        """
        record, status = self._get_record_and_check(xmlid=xmlid, model=model, id=id, field=field, access_token=access_token)

        if not record:
            return (status or 404, [], None)

        content, headers, status = None, [], None

        if record._name == 'ir.attachment':
            status, content, default_filename, mimetype, filehash = self._binary_ir_attachment_redirect_content(record, default_mimetype=default_mimetype)
            filename = filename or default_filename
        if not content:
            status, content, filename, mimetype, filehash = self._binary_record_content(
                record, field=field, filename=filename, filename_field=filename_field,
                default_mimetype='application/octet-stream')

        status, headers, content = self._binary_set_headers(
            status, content, filename, mimetype, unique, filehash=filehash, download=download)

        return status, headers, content

    def _response_by_status(self, status, headers, content):
        if status == 304:
            return werkzeug.wrappers.Response(status=status, headers=headers)
        elif status == 301:
            return request.redirect(content, code=301, local=False)
        elif status != 200:
            return request.not_found()
