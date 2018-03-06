# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import os
import re
import traceback

import werkzeug
import werkzeug.routing
import werkzeug.utils

import odoo
from odoo import api, models
from odoo import SUPERUSER_ID
from odoo.http import request
from odoo.tools import config
from odoo.exceptions import QWebException
from odoo.tools.safe_eval import safe_eval

from odoo.addons.base import ir
from odoo.addons.website.models.website import slug, url_for, _UNSLUG_RE


logger = logging.getLogger(__name__)

# global resolver (GeoIP API is thread-safe, for multithreaded workers)
# This avoids blowing up open files limit
odoo._geoip_resolver = None


class RequestUID(object):
    def __init__(self, **kw):
        self.__dict__.update(kw)


class Http(models.AbstractModel):
    _inherit = 'ir.http'

    rerouting_limit = 10
    _geoip_resolver = None  # backwards-compatibility

    @classmethod
    def _get_converters(cls):
        """ Get the converters list for custom url pattern werkzeug need to
            match Rule. This override adds the website ones.
        """
        return dict(
            super(Http, cls)._get_converters(),
            model=ModelConverter,
            page=PageConverter,
        )

    @classmethod
    def _auth_method_public(cls):
        """ If no user logged, set the public user of current website, or default
            public user as request uid.
            After this method `request.env` can be called, since the `request.uid` is
            set. The `env` lazy property of `request` will be correct.
        """
        if not request.session.uid:
            env = api.Environment(request.cr, SUPERUSER_ID, request.context)
            website = env['website'].get_current_website()
            if website and website.user_id:
                request.uid = website.user_id.id
            else:
                request.uid = env.ref('base.public_user').id
        else:
            request.uid = request.session.uid

    bots = "bot|crawl|slurp|spider|curl|wget|facebookexternalhit".split("|")

    @classmethod
    def is_a_bot(cls):
        # We don't use regexp and ustr voluntarily
        # timeit has been done to check the optimum method
        user_agent = request.httprequest.environ.get('HTTP_USER_AGENT', '').lower()
        try:
            return any(bot in user_agent for bot in cls.bots)
        except UnicodeDecodeError:
            return any(bot in user_agent.encode('ascii', 'ignore') for bot in cls.bots)

    @classmethod
    def get_nearest_lang(cls, lang):
        # Try to find a similar lang. Eg: fr_BE and fr_FR
        short = lang.partition('_')[0]
        short_match = False
        for code, dummy in request.website.get_languages():
            if code == lang:
                return lang
            if not short_match and code.startswith(short):
                short_match = code
        return short_match

    @classmethod
    def _geoip_setup_resolver(cls):
        # Lazy init of GeoIP resolver
        if cls._geoip_resolver is not None:
            return
        if odoo._geoip_resolver is not None:
            cls._geoip_resolver = odoo._geoip_resolver
            return
        try:
            import GeoIP
            # updated database can be downloaded on MaxMind website
            # http://dev.maxmind.com/geoip/legacy/install/city/
            geofile = config.get('geoip_database')
            if os.path.exists(geofile):
                odoo._geoip_resolver = GeoIP.open(geofile, GeoIP.GEOIP_STANDARD)
            else:
                odoo._geoip_resolver = False
                logger.warning('GeoIP database file %r does not exists, apt-get install geoip-database-contrib or download it from http://dev.maxmind.com/geoip/legacy/install/city/', geofile)
        except ImportError:
            odoo._geoip_resolver = False

    @classmethod
    def _geoip_resolve(cls):
        if 'geoip' not in request.session:
            record = {}
            if odoo._geoip_resolver and request.httprequest.remote_addr:
                record = odoo._geoip_resolver.record_by_addr(request.httprequest.remote_addr) or {}
            request.session['geoip'] = record

    @classmethod
    def get_page_key(cls):
        return (cls._name, "cache", request.uid, request.lang, request.httprequest.full_path)

    @classmethod
    def _dispatch(cls):
        """ Before executing the endpoint method, add website params on request, such as
                - current website (record)
                - multilang support (set on cookies)
                - geoip dict data are added in the session
            Then follow the parent dispatching.
            Reminder :  Do not use `request.env` before authentication phase, otherwise the env
                        set on request will be created with uid=None (and it is a lazy property)
        """
        first_pass = not hasattr(request, 'website')
        request.website = None
        func = None
        try:
            if request.httprequest.method == 'GET' and '//' in request.httprequest.path:
                new_url = request.httprequest.path.replace('//', '/') + '?' + request.httprequest.query_string
                return werkzeug.utils.redirect(new_url, 301)
            func, arguments = cls._find_handler()
            request.website_enabled = func.routing.get('website', False)
        except werkzeug.exceptions.NotFound:
            # either we have a language prefixed route, either a real 404
            # in all cases, website processes them
            request.website_enabled = True

        request.website_multilang = (
            request.website_enabled and
            func and func.routing.get('multilang', func.routing['type'] == 'http')
        )

        cls._geoip_setup_resolver()
        cls._geoip_resolve()

        # For website routes (only), add website params on `request`
        cook_lang = request.httprequest.cookies.get('website_lang')
        if request.website_enabled:
            try:
                if func:
                    cls._authenticate(func.routing['auth'])
                elif request.uid is None:
                    cls._auth_method_public()
            except Exception as e:
                return cls._handle_exception(e)

            request.redirect = lambda url, code=302: werkzeug.utils.redirect(url_for(url), code)
            request.website = request.env['website'].get_current_website()  # can use `request.env` since auth methods are called
            context = dict(request.context)
            context['website_id'] = request.website.id
            langs = [lg[0] for lg in request.website.get_languages()]
            path = request.httprequest.path.split('/')
            if first_pass:
                is_a_bot = cls.is_a_bot()
                nearest_lang = not func and cls.get_nearest_lang(path[1])
                url_lang = nearest_lang and path[1]
                preferred_lang = ((cook_lang if cook_lang in langs else False)
                                  or (not is_a_bot and cls.get_nearest_lang(request.lang))
                                  or request.website.default_lang_code)

                request.lang = context['lang'] = nearest_lang or preferred_lang
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
                    request.context = context
                    redirect = request.redirect(path + '?' + request.httprequest.query_string)
                    redirect.set_cookie('website_lang', request.lang)
                    return redirect
                elif url_lang:
                    request.uid = None
                    path.pop(1)
                    request.context = context
                    return cls.reroute('/'.join(path) or '/')
            if request.lang == request.website.default_lang_code:
                context['edit_translations'] = False
            if not context.get('tz'):
                context['tz'] = request.session.get('geoip', {}).get('time_zone')
            # bind modified context
            request.context = context
            request.website = request.website.with_context(context)

        # removed cache for auth public
        request.cache_save = False
        resp = super(Http, cls)._dispatch()

        if request.website_enabled and cook_lang != request.lang and hasattr(resp, 'set_cookie'):
            resp.set_cookie('website_lang', request.lang)
        return resp

    @classmethod
    def reroute(cls, path):
        if not hasattr(request, 'rerouting'):
            request.rerouting = [request.httprequest.path]
        if path in request.rerouting:
            raise Exception("Rerouting loop is forbidden")
        request.rerouting.append(path)
        if len(request.rerouting) > cls.rerouting_limit:
            raise Exception("Rerouting limit exceeded")
        request.httprequest.environ['PATH_INFO'] = path
        # void werkzeug cached_property. TODO: find a proper way to do this
        for key in ('path', 'full_path', 'url', 'base_url'):
            request.httprequest.__dict__.pop(key, None)

        return cls._dispatch()

    @classmethod
    def _postprocess_args(cls, arguments, rule):
        super(Http, cls)._postprocess_args(arguments, rule)

        for key, val in arguments.items():
            # Replace uid placeholder by the current request.uid
            if isinstance(val, models.BaseModel) and isinstance(val._uid, RequestUID):
                arguments[key] = val.sudo(request.uid)

        try:
            _, path = rule.build(arguments)
            assert path is not None
        except Exception, e:
            return cls._handle_exception(e, code=404)

        if getattr(request, 'website_multilang', False) and request.httprequest.method in ('GET', 'HEAD'):
            generated_path = werkzeug.url_unquote_plus(path)
            current_path = werkzeug.url_unquote_plus(request.httprequest.path)
            if generated_path != current_path:
                if request.lang != request.website.default_lang_code:
                    path = '/' + request.lang + path
                if request.httprequest.query_string:
                    path += '?' + request.httprequest.query_string
                return werkzeug.utils.redirect(path, code=301)

    @classmethod
    def _handle_exception(cls, exception, code=500):
        is_website_request = bool(getattr(request, 'website_enabled', False) and request.website)
        if not is_website_request:
            # Don't touch non website requests exception handling
            return super(Http, cls)._handle_exception(exception)
        else:
            try:
                response = super(Http, cls)._handle_exception(exception)
                if isinstance(response, Exception):
                    exception = response
                else:
                    # if parent excplicitely returns a plain response, then we don't touch it
                    return response
            except Exception, e:
                if 'werkzeug' in config['dev_mode'] and (not isinstance(exception, QWebException) or not exception.qweb.get('cause')):
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

            if isinstance(exception, odoo.exceptions.AccessError):
                code = 403

            if isinstance(exception, QWebException):
                values.update(qweb_exception=exception)
                if isinstance(exception.qweb.get('cause'), odoo.exceptions.AccessError):
                    code = 403

            if code == 500:
                logger.error("500 Internal Server Error:\n\n%s", values['traceback'])
                if 'qweb_exception' in values:
                    view = request.env["ir.ui.view"]
                    views = view._views_get(exception.qweb['template'])
                    to_reset = views.filtered(lambda view: view.model_data_id.noupdate is True and not view.page)
                    values['views'] = to_reset
            elif code == 403:
                logger.warn("403 Forbidden:\n\n%s", values['traceback'])

            values.update(
                status_message=werkzeug.http.HTTP_STATUS_CODES[code],
                status_code=code,
            )

            if not request.uid:
                cls._auth_method_public()

            try:
                html = request.env['ir.ui.view'].render_template('website.%s' % code, values)
            except Exception:
                html = request.env['ir.ui.view'].render_template('website.http_error', values)
            return werkzeug.wrappers.Response(html, status=code, content_type='text/html;charset=utf-8')

    @classmethod
    def binary_content(cls, xmlid=None, model='ir.attachment', id=None, field='datas', unique=False, filename=None, filename_field='datas_fname', download=False, mimetype=None, default_mimetype='application/octet-stream', env=None):
        env = env or request.env
        obj = None
        if xmlid:
            obj = env.ref(xmlid, False)
        elif id and model in env:
            obj = env[model].browse(int(id))
        if obj and 'website_published' in obj._fields:
            if env[obj._name].sudo().search([('id', '=', obj.id), ('website_published', '=', True)]):
                env = env(user=SUPERUSER_ID)
        return super(Http, cls).binary_content(xmlid=xmlid, model=model, id=id, field=field, unique=unique, filename=filename, filename_field=filename_field, download=download, mimetype=mimetype, default_mimetype=default_mimetype, env=env)


class ModelConverter(ir.ir_http.ModelConverter):

    def __init__(self, url_map, model=False, domain='[]'):
        super(ModelConverter, self).__init__(url_map, model)
        self.domain = domain
        self.regex = _UNSLUG_RE.pattern

    def to_url(self, value):
        return slug(value)

    def to_python(self, value):
        matching = re.match(self.regex, value)
        _uid = RequestUID(value=value, match=matching, converter=self)
        record_id = int(matching.group(2))
        env = api.Environment(request.cr, _uid, request.context)
        if record_id < 0:
            # limited support for negative IDs due to our slug pattern, assume abs() if not found
            if not env[self.model].browse(record_id).exists():
                record_id = abs(record_id)
        return env[self.model].browse(record_id)

    def generate(self, query=None, args=None):
        Model = request.env[self.model]
        if request.context.get('use_public_user'):
            Model = Model.sudo(request.website.user_id.id)
        domain = safe_eval(self.domain, (args or {}).copy())
        if query:
            domain.append((Model._rec_name, 'ilike', '%' + query + '%'))
        for record in Model.search_read(domain=domain, fields=['write_date', Model._rec_name]):
            if record.get(Model._rec_name, False):
                yield {'loc': (record['id'], record[Model._rec_name])}


class PageConverter(werkzeug.routing.PathConverter):
    """ Only point of this converter is to bundle pages enumeration logic """

    def generate(self, query=None, args={}):
        View = request.env['ir.ui.view']
        domain = [('page', '=', True)]
        query = query and query.startswith('website.') and query[8:] or query
        if query:
            domain += [('key', 'like', query)]
        website_id = request.context.get('website_id') or request.env['website'].search([], limit=1).id
        domain += ['|', ('website_id', '=', website_id), ('website_id', '=', False)]

        views = View.search_read(domain, fields=['key', 'priority', 'write_date'], order='name')
        for view in views:
            xid = view['key'].startswith('website.') and view['key'][8:] or view['key']
            # the 'page/homepage' url is indexed as '/', avoid aving the same page referenced twice
            # when we will have an url mapping mechanism, replace this by a rule: page/homepage --> /
            if xid == 'homepage':
                continue
            record = {'loc': xid}
            if view['priority'] != 16:
                record['__priority'] = min(round(view['priority'] / 32.0, 1), 1)
            if view['write_date']:
                record['__lastmod'] = view['write_date'][:10]
            yield record
