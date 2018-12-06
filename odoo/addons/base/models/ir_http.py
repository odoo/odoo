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

import werkzeug
import werkzeug.exceptions
import werkzeug.routing
import werkzeug.urls
import werkzeug.utils

import odoo
from odoo import api, http, models, tools, SUPERUSER_ID
from odoo.exceptions import AccessDenied, AccessError
from odoo.http import request, STATIC_CACHE, content_disposition
from odoo.tools import pycompat, consteq
from odoo.tools.mimetypes import guess_mimetype
from odoo.modules.module import get_resource_path, get_module_path

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
    def _serve_attachment(cls):
        env = api.Environment(request.cr, SUPERUSER_ID, request.context)
        attach = env['ir.attachment'].get_serve_attachment(request.httprequest.path, extra_fields=['name', 'checksum'])
        if attach:
            wdate = attach[0]['__last_update']
            datas = attach[0]['datas'] or b''
            name = attach[0]['name']
            checksum = attach[0]['checksum'] or hashlib.sha1(datas).hexdigest()

            if (not datas and name != request.httprequest.path and
                    name.startswith(('http://', 'https://', '/'))):
                return werkzeug.utils.redirect(name, 301)

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
        # If handle_exception returns something different than None, it will be used as a response

        # This is done first as the attachment path may
        # not match any HTTP controller
        if isinstance(exception, werkzeug.exceptions.HTTPException) and exception.code == 404:
            serve = cls._serve_fallback(exception)
            if serve:
                return serve

        # Don't handle exception but use werkzeug debugger if server in --dev mode
        if 'werkzeug' in tools.config['dev_mode'] and not isinstance(exception, werkzeug.exceptions.NotFound):
            raise exception

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
        except werkzeug.exceptions.NotFound as e:
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
        except Exception as e:
            return cls._handle_exception(e)

        return result

    @classmethod
    def _postprocess_args(cls, arguments, rule):
        """ post process arg to set uid on browse records """
        for key, val in list(arguments.items()):
            # Replace uid placeholder by the current request.uid
            if isinstance(val, models.BaseModel) and isinstance(val._uid, RequestUID):
                arguments[key] = val.sudo(request.uid)
                if not val.exists():
                    return cls._handle_exception(werkzeug.exceptions.NotFound())

    @classmethod
    def routing_map(cls):
        if not hasattr(cls, '_routing_map'):
            _logger.info("Generating routing map")
            installed = request.registry._init_modules - {'web'}
            if tools.config['test_enable'] and odoo.modules.module.current_test:
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
        if not record or not record.exists() or field not in record:
            return None, 404

        # access token grant access
        if model == 'ir.attachment' and access_token:
            record = record.sudo()
            if not consteq(record.access_token or '', access_token):
                return None, 403

        # check read access
        try:
            last_update = record['__last_update']
        except AccessError:
            return None, 403

        return record, 200

    @classmethod
    def _binary_ir_attachment_redirect_content(cls, record, default_mimetype='application/octet-stream'):
        # mainly used for theme images attachemnts
        status = content = filename = mimetype = filehash = None
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
            else:
                status = 301
                content = record.url



        return status, content, filename, mimetype, filehash

    def _binary_record_content(
            self, record, field='datas', filename=None,
            filename_field='datas_fname', default_mimetype='application/octet-stream'):

        model = record._name
        mimetype = 'mimetype' in record and record.mimetype or False
        content = None
        filehash = 'checksum' in record and record['checksum'] or False

        field_def = record._fields[field]
        if field_def.type == 'binary' and field_def.attachment:
            field_attachment = self.env['ir.attachment'].search_read(domain=[('res_model', '=', model), ('res_id', '=', record.id), ('res_field', '=', field)], fields=['datas', 'mimetype', 'checksum'], limit=1)
            if field_attachment:
                mimetype = field_attachment[0]['mimetype']
                content = field_attachment[0]['datas']
                filehash = field_attachment[0]['checksum']

        if not content:
            content = record[field] or ''

        # filename
        if not filename:
            if filename_field in record:
                filename = record[filename_field]
            else:
                filename = "%s-%s-%s" % (record._name, record.id, field)

        if not mimetype:
            mimetype = guess_mimetype(base64.b64decode(content), default=default_mimetype)

        if not filehash:
            filehash = '"%s"' % hashlib.md5(pycompat.to_text(content).encode('utf-8')).hexdigest()

        status = 200 if content else 404
        return status, content, filename, mimetype, filehash

    def _binary_set_headers(self, status, content, filename, mimetype, unique, filehash=None, download=False):
        headers = [('Content-Type', mimetype), ('X-Content-Type-Options', 'nosniff')]
        # cache
        etag = bool(request) and request.httprequest.headers.get('If-None-Match')
        status = status or (304 if filehash and etag == filehash else 200)
        if filehash:
            headers.append(('ETag', filehash))
        headers.append(('Cache-Control', 'max-age=%s' % (STATIC_CACHE if unique else 0)))
        # content-disposition default name
        if download:
            headers.append(('Content-Disposition', content_disposition(filename)))

        return (status, headers, content)

    def binary_content(self, xmlid=None, model='ir.attachment', id=None, field='datas',
                       unique=False, filename=None, filename_field='datas_fname', download=False,
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
            status, content, filename, mimetype, filehash = self._binary_ir_attachment_redirect_content(record, default_mimetype=default_mimetype)
        if not content:
            status, content, filename, mimetype, filehash = self._binary_record_content(
                record, field=field, filename=None, filename_field=filename_field,
                default_mimetype='application/octet-stream')

        status, headers, content = self._binary_set_headers(
            status, content, filename, mimetype, unique, filehash=False, download=download)

        return status, headers, content

    def _response_by_status(self, status, headers, content):
        if status == 304:
            return werkzeug.wrappers.Response(status=status, headers=headers)
        elif status == 301:
            return werkzeug.utils.redirect(content, code=301)
        elif status != 200:
            return request.not_found()
