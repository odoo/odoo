# -*- coding: utf-8 -*-
import datetime
import hashlib
import logging
import os
import re
import traceback

import werkzeug
import werkzeug.routing
import werkzeug.utils

import openerp
from openerp.addons.base import ir
from openerp.addons.base.ir import ir_qweb
from openerp.addons.website.models.website import slug, url_for, _UNSLUG_RE
from openerp.http import request
from openerp.tools import config
from openerp.osv import orm

logger = logging.getLogger(__name__)

class RequestUID(object):
    def __init__(self, **kw):
        self.__dict__.update(kw)

class ir_http(orm.AbstractModel):
    _inherit = 'ir.http'

    rerouting_limit = 10
    geo_ip_resolver = None

    def _get_converters(self):
        return dict(
            super(ir_http, self)._get_converters(),
            model=ModelConverter,
            page=PageConverter,
        )

    def _auth_method_public(self):
        # TODO: select user_id from matching website
        if not request.session.uid:
            request.uid = self.pool['ir.model.data'].xmlid_to_res_id(request.cr, openerp.SUPERUSER_ID, 'base.public_user')
        else:
            request.uid = request.session.uid

    def _dispatch(self):
        first_pass = not hasattr(request, 'website')
        request.website = None
        func = None
        try:
            func, arguments = self._find_handler()
            request.website_enabled = func.routing.get('website', False)
        except werkzeug.exceptions.NotFound:
            # either we have a language prefixed route, either a real 404
            # in all cases, website processes them
            request.website_enabled = True

        request.website_multilang = request.website_enabled and func and func.routing.get('multilang', True)

        if 'geoip' not in request.session:
            record = {}
            if self.geo_ip_resolver is None:
                try:
                    import GeoIP
                    # updated database can be downloaded on MaxMind website
                    # http://dev.maxmind.com/geoip/legacy/install/city/
                    geofile = config.get('geoip_database', '/usr/share/GeoIP/GeoLiteCity.dat')
                    if os.path.exists(geofile):
                        self.geo_ip_resolver = GeoIP.open(geofile, GeoIP.GEOIP_STANDARD)
                    else:
                        self.geo_ip_resolver = False
                        logger.warning('GeoIP database file %r does not exists', geofile)
                except ImportError:
                    self.geo_ip_resolver = False
            if self.geo_ip_resolver and request.httprequest.remote_addr:
                record = self.geo_ip_resolver.record_by_addr(request.httprequest.remote_addr) or {}
            request.session['geoip'] = record

        if request.website_enabled:
            if func:
                self._authenticate(func.routing['auth'])
            else:
                self._auth_method_public()
            request.redirect = lambda url: werkzeug.utils.redirect(url_for(url))
            request.website = request.registry['website'].get_current_website(request.cr, request.uid, context=request.context)
            if first_pass:
                request.lang = request.website.default_lang_code
            request.context['lang'] = request.lang
            if not func:
                path = request.httprequest.path.split('/')
                langs = [lg[0] for lg in request.website.get_languages()]
                if path[1] in langs:
                    request.lang = request.context['lang'] = path.pop(1)
                    path = '/'.join(path) or '/'
                    if request.lang == request.website.default_lang_code:
                        # If language is in the url and it is the default language, redirect
                        # to url without language so google doesn't see duplicate content
                        return request.redirect(path + '?' + request.httprequest.query_string)
                    return self.reroute(path)
        return super(ir_http, self)._dispatch()

    def reroute(self, path):
        if not hasattr(request, 'rerouting'):
            request.rerouting = [request.httprequest.path]
        if path in request.rerouting:
            raise Exception("Rerouting loop is forbidden")
        request.rerouting.append(path)
        if len(request.rerouting) > self.rerouting_limit:
            raise Exception("Rerouting limit exceeded")
        request.httprequest.environ['PATH_INFO'] = path
        # void werkzeug cached_property. TODO: find a proper way to do this
        for key in ('path', 'full_path', 'url', 'base_url'):
            request.httprequest.__dict__.pop(key, None)

        return self._dispatch()

    def _postprocess_args(self, arguments, rule):
        super(ir_http, self)._postprocess_args(arguments, rule)

        for key, val in arguments.items():
            # Replace uid placeholder by the current request.uid
            if isinstance(val, orm.BaseModel) and isinstance(val._uid, RequestUID):
                arguments[key] = val.sudo(request.uid)

        try:
            _, path = rule.build(arguments)
            assert path is not None
        except Exception, e:
            return self._handle_exception(e, code=404)

        if getattr(request, 'website_multilang', False) and request.httprequest.method in ('GET', 'HEAD'):
            generated_path = werkzeug.url_unquote_plus(path)
            current_path = werkzeug.url_unquote_plus(request.httprequest.path)
            if generated_path != current_path:
                if request.lang != request.website.default_lang_code:
                    path = '/' + request.lang + path
                if request.httprequest.query_string:
                    path += '?' + request.httprequest.query_string
                return werkzeug.utils.redirect(path)

    def _serve_attachment(self):
        domain = [('type', '=', 'binary'), ('url', '=', request.httprequest.path)]
        attach = self.pool['ir.attachment'].search_read(request.cr, openerp.SUPERUSER_ID, domain, ['__last_update', 'datas', 'mimetype'], context=request.context)
        if attach:
            wdate = attach[0]['__last_update']
            datas = attach[0]['datas']
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

            response.mimetype = attach[0]['mimetype'] or 'application/octet-stream'
            response.data = datas.decode('base64')
            return response

    def _handle_exception(self, exception, code=500):
        # This is done first as the attachment path may
        # not match any HTTP controller, so the request
        # may not be website-enabled.
        attach = self._serve_attachment()
        if attach:
            return attach

        is_website_request = bool(getattr(request, 'website_enabled', False) and request.website)
        if not is_website_request:
            # Don't touch non website requests exception handling
            return super(ir_http, self)._handle_exception(exception)
        else:
            try:
                response = super(ir_http, self)._handle_exception(exception)
                if isinstance(response, Exception):
                    exception = response
                else:
                    # if parent excplicitely returns a plain response, then we don't touch it
                    return response
            except Exception, e:
                exception = e

            values = dict(
                exception=exception,
                traceback=traceback.format_exc(exception),
            )
            code = getattr(exception, 'code', code)

            if isinstance(exception, openerp.exceptions.AccessError):
                code = 403

            if isinstance(exception, ir_qweb.QWebException):
                values.update(qweb_exception=exception)
                if isinstance(exception.qweb.get('cause'), openerp.exceptions.AccessError):
                    code = 403

            if isinstance(exception, werkzeug.exceptions.HTTPException) and code is None:
                # Hand-crafted HTTPException likely coming from abort(),
                # usually for a redirect response -> return it directly
                return exception

            if code == 500:
                logger.error("500 Internal Server Error:\n\n%s", values['traceback'])
                if 'qweb_exception' in values:
                    view = request.registry.get("ir.ui.view")
                    views = view._views_get(request.cr, request.uid, exception.qweb['template'], request.context)
                    to_reset = [v for v in views if v.model_data_id.noupdate is True]
                    values['views'] = to_reset
            elif code == 403:
                logger.warn("403 Forbidden:\n\n%s", values['traceback'])

            values.update(
                status_message=werkzeug.http.HTTP_STATUS_CODES[code],
                status_code=code,
            )

            if not request.uid:
                self._auth_method_public()

            try:
                html = request.website._render('website.%s' % code, values)
            except Exception:
                html = request.website._render('website.http_error', values)
            return werkzeug.wrappers.Response(html, status=code, content_type='text/html;charset=utf-8')

class ModelConverter(ir.ir_http.ModelConverter):
    def __init__(self, url_map, model=False, domain='[]'):
        super(ModelConverter, self).__init__(url_map, model)
        self.domain = domain
        self.regex = _UNSLUG_RE.pattern

    def to_url(self, value):
        return slug(value)

    def to_python(self, value):
        m = re.match(self.regex, value)
        _uid = RequestUID(value=value, match=m, converter=self)
        return request.registry[self.model].browse(
            request.cr, _uid, int(m.group(2)), context=request.context)

    def generate(self, cr, uid, query=None, args=None, context=None):
        obj = request.registry[self.model]
        domain = eval( self.domain, (args or {}).copy())
        if query:
            domain.append((obj._rec_name, 'ilike', '%'+query+'%'))
        for record in obj.search_read(cr, uid, domain=domain, fields=['write_date',obj._rec_name], context=context):
            if record.get(obj._rec_name, False):
                yield {'loc': (record['id'], record[obj._rec_name])}

class PageConverter(werkzeug.routing.PathConverter):
    """ Only point of this converter is to bundle pages enumeration logic """
    def generate(self, cr, uid, query=None, args={}, context=None):
        View = request.registry['ir.ui.view']
        views = View.search_read(cr, uid, [['page', '=', True]],
            fields=['xml_id','priority','write_date'], order='name', context=context)
        for view in views:
            xid = view['xml_id'].startswith('website.') and view['xml_id'][8:] or view['xml_id']
            # the 'page/homepage' url is indexed as '/', avoid aving the same page referenced twice
            # when we will have an url mapping mechanism, replace this by a rule: page/homepage --> /
            if xid=='homepage': continue
            if query and query.lower() not in xid.lower():
                continue
            record = {'loc': xid}
            if view['priority'] <> 16:
                record['__priority'] = min(round(view['priority'] / 32.0,1), 1)
            if view['write_date']:
                record['__lastmod'] = view['write_date'][:10]
            yield record
