# Part of Odoo. See LICENSE file for full copyright and licensing details.

import contextlib
import logging
import os
import re
import traceback
import threading
import unicodedata
import werkzeug.exceptions
import werkzeug.routing
import werkzeug.urls
from werkzeug.exceptions import HTTPException, NotFound

# optional python-slugify import (https://github.com/un33k/python-slugify)
try:
    import slugify as slugify_lib
except ImportError:
    slugify_lib = None

import odoo
from odoo import api, models, exceptions, tools, http
from odoo.addons.base.models import ir_http
from odoo.addons.base.models.ir_http import RequestUID
from odoo.addons.base.models.ir_qweb import QWebException
from odoo.http import request
from odoo.osv import expression
from odoo.tools import config, ustr, pycompat

_logger = logging.getLogger(__name__)

# global resolver (GeoIP API is thread-safe, for multithreaded workers)
# This avoids blowing up open files limit
odoo._geoip_resolver = None

# ------------------------------------------------------------
# Slug API
# ------------------------------------------------------------

def _guess_mimetype(ext=False, default='text/html'):
    exts = {
        '.css': 'text/css',
        '.less': 'text/less',
        '.scss': 'text/scss',
        '.js': 'text/javascript',
        '.xml': 'text/xml',
        '.csv': 'text/csv',
        '.html': 'text/html',
    }
    return ext is not False and exts.get(ext, default) or exts


def slugify_one(s, max_length=0):
    """ Transform a string to a slug that can be used in a url path.
        This method will first try to do the job with python-slugify if present.
        Otherwise it will process string by stripping leading and ending spaces,
        converting unicode chars to ascii, lowering all chars and replacing spaces
        and underscore with hyphen "-".
        :param s: str
        :param max_length: int
        :rtype: str
    """
    s = ustr(s)
    if slugify_lib:
        # There are 2 different libraries only python-slugify is supported
        try:
            return slugify_lib.slugify(s, max_length=max_length)
        except TypeError:
            pass
    uni = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode('ascii')
    slug_str = re.sub(r'[\W_]', ' ', uni).strip().lower()
    slug_str = re.sub(r'[-\s]+', '-', slug_str)
    return slug_str[:max_length] if max_length > 0 else slug_str


def slugify(s, max_length=0, path=False):
    if not path:
        return slugify_one(s, max_length=max_length)
    else:
        res = []
        for u in s.split('/'):
            if slugify_one(u, max_length=max_length) != '':
                res.append(slugify_one(u, max_length=max_length))
        # check if supported extension
        path_no_ext, ext = os.path.splitext(s)
        if ext and ext in _guess_mimetype():
            res[-1] = slugify_one(path_no_ext) + ext
        return '/'.join(res)


def slug(value):
    try:
        if not value.id:
            raise ValueError("Cannot slug non-existent record %s" % value)
        # [(id, name)] = value.name_get()
        identifier, name = value.id, getattr(value, 'seo_name', False) or value.display_name
    except AttributeError:
        # assume name_search result tuple
        identifier, name = value
    slugname = slugify(name or '').strip().strip('-')
    if not slugname:
        return str(identifier)
    return f"{slugname}-{identifier}"


# NOTE: as the pattern is used as it for the ModelConverter (ir_http.py), do not use any flags
_UNSLUG_RE = re.compile(r'(?:(\w{1,2}|\w[A-Za-z0-9-_]+?\w)-)?(-?\d+)(?=$|/)')


def unslug(s):
    """Extract slug and id from a string.
        Always return un 2-tuple (str|None, int|None)
    """
    m = _UNSLUG_RE.match(s)
    if not m:
        return None, None
    return m.group(1), int(m.group(2))


def unslug_url(s):
    """ From /blog/my-super-blog-1" to "blog/1" """
    parts = s.split('/')
    if parts:
        unslug_val = unslug(parts[-1])
        if unslug_val[1]:
            parts[-1] = str(unslug_val[1])
            return '/'.join(parts)
    return s


# ------------------------------------------------------------
# Language tools
# ------------------------------------------------------------

def url_lang(path_or_uri, lang_code=None):
    ''' Given a relative URL, make it absolute and add the required lang or
        remove useless lang.
        Nothing will be done for absolute or invalid URL.
        If there is only one language installed, the lang will not be handled
        unless forced with `lang` parameter.

        :param lang_code: Must be the lang `code`. It could also be something
                          else, such as `'[lang]'` (used for url_return).
    '''
    Lang = request.env['res.lang']
    location = pycompat.to_text(path_or_uri).strip()
    force_lang = lang_code is not None
    try:
        url = werkzeug.urls.url_parse(location)
    except ValueError:
        # e.g. Invalid IPv6 URL, `werkzeug.urls.url_parse('http://]')`
        url = False
    # relative URL with either a path or a force_lang
    if url and not url.netloc and not url.scheme and (url.path or force_lang):
        location = werkzeug.urls.url_join(request.httprequest.path, location)
        lang_url_codes = [url_code for _, url_code, *_ in Lang.get_available()]
        lang_code = pycompat.to_text(lang_code or request.context['lang'])
        lang_url_code = Lang._lang_code_to_urlcode(lang_code)
        lang_url_code = lang_url_code if lang_url_code in lang_url_codes else lang_code
        if (len(lang_url_codes) > 1 or force_lang) and is_multilang_url(location, lang_url_codes):
            loc, sep, qs = location.partition('?')
            ps = loc.split(u'/')
            default_lg = request.env['ir.http']._get_default_lang()
            if ps[1] in lang_url_codes:
                # Replace the language only if we explicitly provide a language to url_for
                if force_lang:
                    ps[1] = lang_url_code
                # Remove the default language unless it's explicitly provided
                elif ps[1] == default_lg.url_code:
                    ps.pop(1)
            # Insert the context language or the provided language
            elif lang_url_code != default_lg.url_code or force_lang:
                ps.insert(1, lang_url_code)

            location = u'/'.join(ps) + sep + qs
    return location


def url_for(url_from, lang_code=None, no_rewrite=False):
    ''' Return the url with the rewriting applied.
        Nothing will be done for absolute URL, invalid URL, or short URL from 1 char.

        :param url_from: The URL to convert.
        :param lang_code: Must be the lang `code`. It could also be something
                          else, such as `'[lang]'` (used for url_return).
        :param no_rewrite: don't try to match route with website.rewrite.
    '''
    new_url = False

    # don't try to match route if we know that no rewrite has been loaded.
    routing = getattr(request, 'website_routing', None)  # not modular, but not overridable
    if not getattr(request.env['ir.http'], '_rewrite_len', {}).get(routing):
        no_rewrite = True

    path, _, qs = (url_from or '').partition('?')

    if (not no_rewrite and path and (
            len(path) > 1
            and path.startswith('/')
            and '/static/' not in path
            and not path.startswith('/web/')
    )):
        new_url, _ = request.env['ir.http'].url_rewrite(path)
        new_url = new_url if not qs else new_url + '?%s' % qs

    return url_lang(new_url or url_from, lang_code=lang_code)


def is_multilang_url(local_url, lang_url_codes=None):
    ''' Check if the given URL content is supposed to be translated.
        To be considered as translatable, the URL should either:
        1. Match a POST (non-GET actually) controller that is `website=True` and
           either `multilang` specified to True or if not specified, with `type='http'`.
        2. If not matching 1., everything not under /static/ or /web/ will be translatable
    '''
    if not lang_url_codes:
        lang_url_codes = [url_code for _, url_code, *_ in request.env['res.lang'].get_available()]
    spath = local_url.split('/')
    # if a language is already in the path, remove it
    if spath[1] in lang_url_codes:
        spath.pop(1)
        local_url = '/'.join(spath)

    url = local_url.partition('#')[0].split('?')
    path = url[0]

    # Consider /static/ and /web/ files as non-multilang
    if '/static/' in path or path.startswith('/web/'):
        return False

    query_string = url[1] if len(url) > 1 else None

    # Try to match an endpoint in werkzeug's routing table
    try:
        _, func = request.env['ir.http'].url_rewrite(path, query_args=query_string)

        # /page/xxx has no endpoint/func but is multilang
        return (not func or (
            func.routing.get('website', False)
            and func.routing.get('multilang', func.routing['type'] == 'http')
        ))
    except Exception as exception:
        _logger.warning(exception)
        return False


class ModelConverter(ir_http.ModelConverter):

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
        return env[self.model].with_context(_converter_value=value).browse(record_id)


class IrHttp(models.AbstractModel):
    _inherit = ['ir.http']

    rerouting_limit = 10

    @classmethod
    def _get_converters(cls):
        """ Get the converters list for custom url pattern werkzeug need to
            match Rule. This override adds the website ones.
        """
        return dict(
            super(IrHttp, cls)._get_converters(),
            model=ModelConverter,
        )

    @classmethod
    def _get_default_lang(cls):
        lang_code = request.env['ir.default'].sudo().get('res.partner', 'lang')
        if lang_code:
            return request.env['res.lang']._lang_get(lang_code)
        return request.env['res.lang'].search([], limit=1)

    @api.model
    def get_frontend_session_info(self):
        session_info = super(IrHttp, self).get_frontend_session_info()

        IrHttpModel = request.env['ir.http'].sudo()
        modules = IrHttpModel.get_translation_frontend_modules()
        user_context = request.session.context if request.session.uid else {}
        lang = user_context.get('lang')
        translation_hash = request.env['ir.http'].get_web_translations_hash(modules, lang)

        session_info.update({
            'translationURL': '/website/translations',
            'cache_hashes': {
                'translations': translation_hash,
            },
        })
        return session_info

    @api.model
    def get_translation_frontend_modules(self):
        Modules = request.env['ir.module.module'].sudo()
        extra_modules_domain = self._get_translation_frontend_modules_domain()
        extra_modules_name = self._get_translation_frontend_modules_name()
        if extra_modules_domain:
            new = Modules.search(
                expression.AND([extra_modules_domain, [('state', '=', 'installed')]])
            ).mapped('name')
            extra_modules_name += new
        return extra_modules_name

    @classmethod
    def _get_translation_frontend_modules_domain(cls):
        """ Return a domain to list the domain adding web-translations and
            dynamic resources that may be used frontend views
        """
        return []

    @classmethod
    def _get_translation_frontend_modules_name(cls):
        """ Return a list of module name where web-translations and
            dynamic resources may be used in frontend views
        """
        return ['web']

    @classmethod
    def _get_frontend_langs(cls):
        return [code for code, _ in request.env['res.lang'].get_installed()]

    @classmethod
    def get_nearest_lang(cls, lang_code):
        """ Try to find a similar lang. Eg: fr_BE and fr_FR
            :param lang_code: the lang `code` (en_US)
        """
        if not lang_code:
            return None

        lang_codes = cls._get_frontend_langs()
        if lang_code in lang_codes:
            return lang_code

        short = lang_code.partition('_')[0]
        return next((code for code in lang_codes if code.startswith(short)), None)

    @classmethod
    def _match(cls, path):
        """
        Grant multilang support to URL matching by using http 3xx
        redirections and URL rewrite. This method also grants various
        attributes such as ``lang`` and ``is_frontend`` on the current
        ``request`` object.

        1/ Use the URL as-is when it matches a non-multilang compatible
           endpoint.

        2/ Use the URL as-is when the lang is not present in the URL and
           that the default lang has been requested.

        3/ Use the URL as-is saving the requested lang when the user is
           a bot and that the lang is missing from the URL.

        4) Use the url as-is when the lang is missing from the URL, that
           another lang than the default one has been requested but that
           it is forbidden to redirect (e.g. POST)

        5/ Redirect the browser when the lang is missing from the URL
           but another lang than the default one has been requested. The
           requested lang is injected before the original path.

        6/ Redirect the browser when the lang is present in the URL but
           it is the default lang. The lang is removed from the original
           URL.

        7/ Redirect the browser when the lang present in the URL is an
           alias of the preferred lang url code (e.g. fr_FR -> fr)

        8/ Redirect the browser when the requested page is the homepage
           but that there is a trailing slash.

        9/ Rewrite the URL when the lang is present in the URL, that it
           matches and that this lang is not the default one. The URL is
           rewritten to remove the lang.

        Note: The "requested lang" is (in order) either (1) the lang in
              the URL or (2) the lang in the ``frontend_lang`` request
              cookie or (3) the lang in the context or (4) the default
              lang of the website.
        """

        # The URL has been rewritten already
        if hasattr(request, 'is_frontend'):
            return super()._match(path)

        # See /1, match a non website endpoint
        try:
            rule, args = super()._match(path)
            routing = rule.endpoint.routing
            request.is_frontend = routing.get('website', False)
            request.is_frontend_multilang = request.is_frontend and routing.get('multilang', routing['type'] == 'http')
            if not request.is_frontend:
                return rule, args
        except NotFound:
            _, url_lang_str, *rest = path.split('/', 2)
            path_no_lang = '/' + (rest[0] if rest else '')
        else:
            url_lang_str = ''
            path_no_lang = path

        allow_redirect = (
            request.httprequest.method != 'POST'
            and getattr(request, 'is_frontend_multilang', True)
        )

        # There is no user on the environment yet but the following code
        # requires one to set the lang on the request. Temporary grant
        # the public user. Don't try it at home!
        real_env = request.env
        try:
            request.registry['ir.http']._auth_method_public()  # it calls update_env
            nearest_url_lang = cls.get_nearest_lang(request.env['res.lang']._lang_get_code(url_lang_str))
            cookie_lang = cls.get_nearest_lang(request.httprequest.cookies.get('frontend_lang'))
            context_lang = cls.get_nearest_lang(real_env.context.get('lang'))
            default_lang = cls._get_default_lang()
            request.lang = request.env['res.lang']._lang_get(
                nearest_url_lang or cookie_lang or context_lang or default_lang._get_cached('code')
            )
            request_url_code = request.lang._get_cached('url_code')
        finally:
            request.env = real_env

        if not nearest_url_lang:
            url_lang_str = None

        # See /2, no lang in url and default website
        if not url_lang_str and request.lang == default_lang:
            _logger.debug("%r (lang: %r) no lang in url and default website, continue", path, request_url_code)

        # See /3, missing lang in url but user-agent is a bot
        elif not url_lang_str and request.env['ir.http'].is_a_bot():
            _logger.debug("%r (lang: %r) missing lang in url but user-agent is a bot, continue", path, request_url_code)
            request.lang = default_lang

        # See /4, no lang in url and should not redirect (e.g. POST), continue
        elif not url_lang_str and not allow_redirect:
            _logger.debug("%r (lang: %r) no lang in url and should not redirect (e.g. POST), continue", path, request_url_code)

        # See /5, missing lang in url, /home -> /fr/home
        elif not url_lang_str:
            _logger.debug("%r (lang: %r) missing lang in url, redirect", path, request_url_code)
            redirect = request.redirect_query(f'/{request_url_code}{path}', request.httprequest.args)
            redirect.set_cookie('frontend_lang', request.lang._get_cached('code'))
            werkzeug.exceptions.abort(redirect)

        # See /6, default lang in url, /en/home -> /home
        elif url_lang_str == default_lang.url_code and allow_redirect:
            _logger.debug("%r (lang: %r) default lang in url, redirect", path, request_url_code)
            redirect = request.redirect_query(path_no_lang, request.httprequest.args)
            redirect.set_cookie('frontend_lang', default_lang._get_cached('code'))
            werkzeug.exceptions.abort(redirect)

        # See /7, lang alias in url, /fr_FR/home -> /fr/home
        elif url_lang_str != request_url_code and allow_redirect:
            _logger.debug("%r (lang: %r) lang alias in url, redirect", path, request_url_code)
            redirect = request.redirect_query(f'/{request_url_code}{path_no_lang}', request.httprequest.args, code=301)
            redirect.set_cookie('frontend_lang', request.lang._get_cached('code'))
            werkzeug.exceptions.abort(redirect)

        # See /8, homepage with trailing slash. /fr_BE/ -> /fr_BE
        elif path == f'/{url_lang_str}/' and allow_redirect:
            _logger.debug("%r (lang: %r) homepage with trailing slash, redirect", path, request_url_code)
            redirect = request.redirect_query(path[:-1], request.httprequest.args, code=301)
            redirect.set_cookie('frontend_lang', default_lang._get_cached('code'))
            werkzeug.exceptions.abort(redirect)

        # See /9, valid lang in url
        elif url_lang_str == request_url_code:
            # Rewrite the URL to remove the lang
            _logger.debug("%r (lang: %r) valid lang in url, rewrite url and continue", path, request_url_code)
            cls.reroute(path_no_lang)
            path = path_no_lang

        else:
            _logger.warning("%r (lang: %r) couldn't not correctly route this frontend request, url used as-is.", path, request_url_code)

        # Re-match using rewritten route and really raise for 404 errors
        try:
            rule, args = super()._match(path)
            routing = rule.endpoint.routing
            request.is_frontend = routing.get('website', False)
            request.is_frontend_multilang = request.is_frontend and routing.get('multilang', routing['type'] == 'http')
            return rule, args
        except NotFound:
            # Use website to render a nice 404 Not Found html page
            request.is_frontend = True
            request.is_frontend_multilang = True
            raise

    @classmethod
    def reroute(cls, path, query_string=None):
        """
        Rewrite the current request URL using the new path and query
        string. This act as a light redirection, it does not return a
        3xx responses to the browser but still change the current URL.
        """
        if query_string is None:
            query_string = request.httprequest.environ['QUERY_STRING']

        # Change the WSGI environment
        environ = request.httprequest.environ.copy()
        environ['PATH_INFO'] = path
        environ['QUERY_STRING'] = query_string
        environ['RAW_URI'] = f'{path}?{query_string}'
        # REQUEST_URI left as-is so it still contains the original URI

        # Create and expose a new request from the modified WSGI env
        httprequest = werkzeug.wrappers.Request(environ)
        httprequest.parameter_storage_class = (
            werkzeug.datastructures.ImmutableOrderedMultiDict)
        threading.current_thread().url = httprequest.url
        request.httprequest = httprequest

    @classmethod
    def _pre_dispatch(cls, rule, args):
        super()._pre_dispatch(rule, args)

        if request.is_frontend:
            cls._frontend_pre_dispatch()

        # update the context of "<model(...):...>" args
        for key, val in list(args.items()):
            if isinstance(val, models.BaseModel):
                args[key] = val.with_context(request.context)

        if request.is_frontend_multilang:
            # A product with id 1 and named 'egg' is accessible via a
            # frontend multilang enpoint 'foo' at the URL '/foo/1'.
            # The preferred URL to access the product (and to generate
            # URLs pointing it) should instead be the sluggified URL
            # '/foo/egg-1'. This code is responsible of redirecting the
            # browser from '/foo/1' to '/foo/egg-1', or '/fr/foo/1' to
            # '/fr/foo/oeuf-1'. While it is nice (for humans) to have a
            # pretty URL, the real reason of this redirection is SEO.
            if request.httprequest.method in ('GET', 'HEAD'):
                try:
                    _, path = rule.build(args)
                except odoo.exceptions.MissingError:
                    raise werkzeug.exceptions.NotFound()
                assert path is not None
                generated_path = werkzeug.urls.url_unquote_plus(path)
                current_path = werkzeug.urls.url_unquote_plus(request.httprequest.path)
                if generated_path != current_path:
                    if request.lang != cls._get_default_lang():
                        path = f'/{request.lang.url_code}{path}'
                    redirect = request.redirect_query(path, request.httprequest.args, code=301)
                    werkzeug.exceptions.abort(redirect)

    @classmethod
    def _frontend_pre_dispatch(cls):
        request.update_context(lang=request.lang._get_cached('code'))
        if request.httprequest.cookies.get('frontend_lang') != request.lang._get_cached('code'):
            request.future_response.set_cookie('frontend_lang', request.lang._get_cached('code'))

    @classmethod
    def _get_exception_code_values(cls, exception):
        """ Return a tuple with the error code following by the values matching the exception"""
        code = 500  # default code
        values = dict(
            exception=exception,
            traceback=traceback.format_exc(),
        )
        if isinstance(exception, exceptions.AccessDenied):
            code = 403
        elif isinstance(exception, exceptions.UserError):
            values['error_message'] = exception.args[0]
            code = 400
            if isinstance(exception, exceptions.AccessError):
                code = 403

        elif isinstance(exception, QWebException):
            values.update(qweb_exception=exception)

            if isinstance(exception.__context__, exceptions.UserError):
                code = 400
                values['error_message'] = exception.__context__.args[0]
                if isinstance(exception.__context__, exceptions.AccessError):
                    code = 403

        elif isinstance(exception, werkzeug.exceptions.HTTPException):
            code = exception.code

        values.update(
            status_message=werkzeug.http.HTTP_STATUS_CODES.get(code, ''),
            status_code=code,
        )

        return (code, values)

    @classmethod
    def _get_values_500_error(cls, env, values, exception):
        values['view'] = env["ir.ui.view"]
        return values

    @classmethod
    def _get_error_html(cls, env, code, values):
        return code, env['ir.ui.view']._render_template('http_routing.%s' % code, values)

    @classmethod
    def _handle_error(cls, exception):
        response = super()._handle_error(exception)

        is_frontend_request = bool(getattr(request, 'is_frontend', False))
        if not is_frontend_request or not isinstance(response, HTTPException):
            # neither handle backend requests nor plain responses
            return response

        # minimal setup to serve frontend pages
        if not request.uid:
            cls._auth_method_public()
        cls._handle_debug()
        cls._frontend_pre_dispatch()
        request.params = request.get_http_params()

        code, values = cls._get_exception_code_values(exception)

        request.cr.rollback()
        if code == 403:
            try:
                response = cls._serve_fallback()
                if response:
                    cls._post_dispatch(response)
                    return response
            except werkzeug.exceptions.Forbidden:
                # Rendering does raise a Forbidden if target is not visible.
                pass # Use default error page handling.
        elif code == 500:
            values = cls._get_values_500_error(request.env, values, exception)
        try:
            code, html = cls._get_error_html(request.env, code, values)
        except Exception:
            code, html = 418, request.env['ir.ui.view']._render_template('http_routing.http_error', values)

        response = werkzeug.wrappers.Response(html, status=code, content_type='text/html;charset=utf-8')
        cls._post_dispatch(response)
        return response

    @api.model
    @tools.ormcache('path', 'query_args')
    def url_rewrite(self, path, query_args=None):
        new_url = False
        router = http.root.get_db_router(request.db).bind('')
        endpoint = False
        try:
            endpoint = router.match(path, method='POST', query_args=query_args)
        except werkzeug.exceptions.MethodNotAllowed:
            endpoint = router.match(path, method='GET', query_args=query_args)
        except werkzeug.routing.RequestRedirect as e:
            new_url = e.new_url.split('?')[0][7:]  # remove scheme
            _, endpoint = self.url_rewrite(new_url, query_args)
            endpoint = endpoint and [endpoint]
        except werkzeug.exceptions.NotFound:
            new_url = path
        return new_url or path, endpoint and endpoint[0]
