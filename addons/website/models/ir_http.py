# -*- coding: utf-8 -*-
import logging
import os
import re
import time
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
from openerp.tools.safe_eval import safe_eval as eval

logger = logging.getLogger(__name__)

class RequestUID(object):
    def __init__(self, **kw):
        self.__dict__.update(kw)

class ir_http(orm.AbstractModel):
    _inherit = 'ir.http'

    rerouting_limit = 10
    _geoip_resolver = None

    def _get_converters(self):
        return dict(
            super(ir_http, self)._get_converters(),
            model=ModelConverter,
            page=PageConverter,
        )

    def _auth_method_public(self):
        if not request.session.uid:
            website = self.pool['website'].get_current_website(request.cr, openerp.SUPERUSER_ID, context=request.context)
            if website and website.user_id:
                request.uid = website.user_id.id
            else:
                request.uid = self.pool['ir.model.data'].xmlid_to_res_id(request.cr, openerp.SUPERUSER_ID, 'base', 'public_user')
        else:
            request.uid = request.session.uid

    bots = "bot|crawl|slurp|spider|curl|wget|facebookexternalhit".split("|")
    def is_a_bot(self):
        # We don't use regexp and ustr voluntarily
        # timeit has been done to check the optimum method
        ua = request.httprequest.environ.get('HTTP_USER_AGENT', '').lower()
        try:
            return any(bot in ua for bot in self.bots)
        except UnicodeDecodeError:
            return any(bot in ua.encode('ascii', 'ignore') for bot in self.bots)

    def get_nearest_lang(self, lang):
        # Try to find a similar lang. Eg: fr_BE and fr_FR
        short = lang.partition('_')[0]
        short_match = False
        for code, name in request.website.get_languages():
            if code == lang:
                return lang
            if not short_match and code.startswith(short):
                short_match = code
        return short_match

    def _geoip_setup_resolver(self):
        if self._geoip_resolver is None:
            try:
                import GeoIP
                # updated database can be downloaded on MaxMind website
                # http://dev.maxmind.com/geoip/legacy/install/city/
                geofile = config.get('geoip_database')
                if os.path.exists(geofile):
                    self._geoip_resolver = GeoIP.open(geofile, GeoIP.GEOIP_STANDARD)
                else:
                    self._geoip_resolver = False
                    logger.warning('GeoIP database file %r does not exists, apt-get install geoip-database-contrib or download it from http://dev.maxmind.com/geoip/legacy/install/city/', geofile)
            except ImportError:
                self._geoip_resolver = False

    def _geoip_resolve(self):
        if 'geoip' not in request.session:
            record = {}
            if self._geoip_resolver and request.httprequest.remote_addr:
                record = self._geoip_resolver.record_by_addr(request.httprequest.remote_addr) or {}
            request.session['geoip'] = record

    def get_page_key(self):
        return (self._name, "cache", request.uid, request.lang, request.httprequest.full_path)

    def _dispatch(self):
        first_pass = not hasattr(request, 'website')
        request.website = None
        func = None
        try:
            if request.httprequest.method == 'GET' and '//' in request.httprequest.path:
                new_url = request.httprequest.path.replace('//', '/') + '?' + request.httprequest.query_string
                return werkzeug.utils.redirect(new_url, 301)
            func, arguments = self._find_handler()
            request.website_enabled = func.routing.get('website', False)
        except werkzeug.exceptions.NotFound:
            # either we have a language prefixed route, either a real 404
            # in all cases, website processes them
            request.website_enabled = True

        request.website_multilang = (
            request.website_enabled and
            func and func.routing.get('multilang', func.routing['type'] == 'http')
        )

        self._geoip_setup_resolver()
        self._geoip_resolve()

        cook_lang = request.httprequest.cookies.get('website_lang')
        if request.website_enabled:
            try:
                if func:
                    self._authenticate(func.routing['auth'])
                elif request.uid is None:
                    self._auth_method_public()
            except Exception as e:
                return self._handle_exception(e)

            request.redirect = lambda url, code=302: werkzeug.utils.redirect(url_for(url), code)
            request.website = request.registry['website'].get_current_website(request.cr, request.uid, context=request.context)
            request.context['website_id'] = request.website.id
            langs = [lg[0] for lg in request.website.get_languages()]
            path = request.httprequest.path.split('/')
            if first_pass:
                is_a_bot = self.is_a_bot()
                nearest_lang = not func and self.get_nearest_lang(path[1])
                url_lang = nearest_lang and path[1]
                preferred_lang = ((cook_lang if cook_lang in langs else False)
                                  or (not is_a_bot and self.get_nearest_lang(request.lang))
                                  or request.website.default_lang_code)

                request.lang = request.context['lang'] = nearest_lang or preferred_lang
                # if lang in url but not the displayed or default language --> change or remove
                # or no lang in url, and lang to dispay not the default language --> add lang
                # and not a POST request
                # and not a bot or bot but default lang in url
                if ((url_lang and (url_lang != request.lang or url_lang == request.website.default_lang_code))
                        or (not url_lang and request.website_multilang and request.lang != request.website.default_lang_code)
                        and request.httprequest.method != 'POST') \
                        and (not is_a_bot or (url_lang and url_lang == request.website.default_lang_code)):
                    if url_lang:
                        path.pop(1)
                    if request.lang != request.website.default_lang_code:
                        path.insert(1, request.lang)
                    path = '/'.join(path) or '/'
                    redirect = request.redirect(path + '?' + request.httprequest.query_string)
                    redirect.set_cookie('website_lang', request.lang)
                    return redirect
                elif url_lang:
                    request.uid = None
                    path.pop(1)
                    return self.reroute('/'.join(path) or '/')
            if request.lang == request.website.default_lang_code:
                request.context['edit_translations'] = False
            if not request.context.get('tz'):
                request.context['tz'] = request.session.get('geoip', {}).get('time_zone')
            # bind modified context
            request.website = request.website.with_context(request.context)

        # cache for auth public
        cache_time = getattr(func, 'routing', {}).get('cache')
        cache_enable = cache_time and request.httprequest.method == "GET" and request.website.user_id.id == request.uid
        cache_response = None
        if cache_enable:
            key = self.get_page_key()
            try:
                r = self.pool.cache[key]
                if r['time'] + cache_time > time.time():
                    cache_response = openerp.http.Response(r['content'], mimetype=r['mimetype'])
                else:
                    del self.pool.cache[key]
            except KeyError:
                pass

        if cache_response:
            request.cache_save = False
            resp = cache_response
        else:
            request.cache_save = key if cache_enable else False
            resp = super(ir_http, self)._dispatch()

        if request.website_enabled and cook_lang != request.lang and hasattr(resp, 'set_cookie'):
            resp.set_cookie('website_lang', request.lang)
        return resp

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
                return werkzeug.utils.redirect(path, code=301)

    def _handle_exception(self, exception, code=500):
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
                if openerp.tools.config['dev_mode'] and (not isinstance(exception, ir_qweb.QWebException) or not exception.qweb.get('cause')):
                    raise
                exception = e

            values = dict(
                exception=exception,
                traceback=traceback.format_exc(exception),
            )

            if isinstance(exception, werkzeug.exceptions.HTTPException):
                if exception.code is None:
                    # Hand-crafted HTTPException likely coming from abort(),
                    # usually for a redirect response -> return it directly
                    return exception
                else:
                    code = exception.code

            if isinstance(exception, openerp.exceptions.AccessError):
                code = 403

            if isinstance(exception, ir_qweb.QWebException):
                values.update(qweb_exception=exception)
                if isinstance(exception.qweb.get('cause'), openerp.exceptions.AccessError):
                    code = 403

            if code == 500:
                logger.error("500 Internal Server Error:\n\n%s", values['traceback'])
                if 'qweb_exception' in values:
                    view = request.registry.get("ir.ui.view")
                    views = view._views_get(request.cr, request.uid, exception.qweb['template'],
                                            context=request.context)
                    to_reset = [v for v in views if v.model_data_id.noupdate is True and not v.page]
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

    def binary_content(self, xmlid=None, model='ir.attachment', id=None, field='datas', unique=False, filename=None, filename_field='datas_fname', download=False, mimetype=None, default_mimetype='application/octet-stream', env=None):
        env = env or request.env
        obj = None
        if xmlid:
            obj = env.ref(xmlid, False)
        elif id and model in self.pool:
            obj = env[model].browse(int(id))
        if obj and 'website_published' in obj._fields:
            if env[obj._name].sudo().search([('id', '=', obj.id), ('website_published', '=', True)]):
                env = env(user=openerp.SUPERUSER_ID)
        return super(ir_http, self).binary_content(xmlid=xmlid, model=model, id=id, field=field, unique=unique, filename=filename, filename_field=filename_field, download=download, mimetype=mimetype, default_mimetype=default_mimetype, env=env)

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
        record_id = int(m.group(2))
        if record_id < 0:
            # limited support for negative IDs due to our slug pattern, assume abs() if not found
            if not request.registry[self.model].exists(request.cr, _uid, [record_id]):
                record_id = abs(record_id)
        return request.registry[self.model].browse(
            request.cr, _uid, record_id, context=request.context)

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
        domain = [('page', '=', True)]
        query = query and query.startswith('website.') and query[8:] or query
        if query:
            domain += [('key', 'like', query)]
        website_id = request.context.get('website_id') or request.registry['website'].search(cr, uid, [], limit=1)[0]
        domain += ['|', ('website_id', '=', website_id), ('website_id', '=', False)]

        views = View.search_read(cr, uid, domain, fields=['key', 'priority', 'write_date'], order='name', context=context)
        for view in views:
            xid = view['key'].startswith('website.') and view['key'][8:] or view['key']
            # the 'page/homepage' url is indexed as '/', avoid aving the same page referenced twice
            # when we will have an url mapping mechanism, replace this by a rule: page/homepage --> /
            if xid=='homepage': continue
            record = {'loc': xid}
            if view['priority'] != 16:
                record['__priority'] = min(round(view['priority'] / 32.0,1), 1)
            if view['write_date']:
                record['__lastmod'] = view['write_date'][:10]
            yield record
