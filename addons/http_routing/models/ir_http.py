# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import re
import traceback
import typing
import werkzeug.exceptions
import werkzeug.routing
import werkzeug.urls
import urllib.parse
from werkzeug.exceptions import HTTPException, NotFound

import odoo
from odoo import api, models, exceptions, tools, http
from odoo.addons.base.models import ir_http
from odoo.addons.base.models.ir_http import RequestUID
from odoo.addons.base.models.ir_qweb import keep_query, QWebException
from odoo.addons.base.models.res_lang import LangData
from odoo.exceptions import AccessError, MissingError
from odoo.http import request, Response
from odoo.osv import expression

_logger = logging.getLogger(__name__)

# NOTE: the second pattern is used for the ModelConverter, do not use nor flags nor groups
_UNSLUG_RE = re.compile(r'(?:(\w{1,2}|\w[A-Za-z0-9-_]+?\w)-)?(-?\d+)(?=$|\/|#|\?)')
_UNSLUG_ROUTE_PATTERN = r'(?:(?:\w{1,2}|\w[A-Za-z0-9-_]+?\w)-)?(?:-?\d+)(?=$|\/|#|\?)'


class ModelConverter(ir_http.ModelConverter):

    def __init__(self, url_map, model=False, domain='[]'):
        super(ModelConverter, self).__init__(url_map, model)
        self.domain = domain
        self.regex = _UNSLUG_ROUTE_PATTERN

    def to_python(self, value) -> models.BaseModel:
        record = super().to_python(value)
        if record.id < 0 and not record.browse(record.id).exists():
            # limited support for negative IDs due to our slug pattern, assume abs() if not found
            record = record.browse(abs(record.id))
        return record.with_context(_converter_value=value)


class IrHttp(models.AbstractModel):
    _inherit = ['ir.http']

    rerouting_limit = 10

    # ------------------------------------------------------------
    # Slug tools
    # ------------------------------------------------------------

    @classmethod
    def _slug(cls, value: models.BaseModel | tuple[int, str]) -> str:
        try:
            identifier, name = value.id, value.display_name
        except AttributeError:
            # assume name_search result tuple
            identifier, name = value
        if not identifier:
            raise ValueError("Cannot slug non-existent record %s" % value)
        slugname = cls._slugify(name or '')
        if not slugname:
            return str(identifier)
        return f"{slugname}-{identifier}"

    @classmethod
    def _unslug(cls, value: str) -> tuple[str | None, int] | tuple[None, None]:
        """ Extract slug and id from a string.
            Always return a 2-tuple (str|None, int|None)
        """
        m = _UNSLUG_RE.match(value)
        if not m:
            return None, None
        return m.group(1), int(m.group(2))

    @classmethod
    def _unslug_url(cls, value: str) -> str:
        """ From /blog/my-super-blog-1" to "blog/1" """
        parts = value.split('/')
        if parts:
            unslug_val = cls._unslug(parts[-1])
            if unslug_val[1]:
                parts[-1] = str(unslug_val[1])
                return '/'.join(parts)
        return value

    @classmethod
    def _get_converters(cls) -> dict[str, type]:
        """ Get the converters list for custom url pattern werkzeug need to
            match Rule. This override adds the website ones.
        """
        return dict(
            super(IrHttp, cls)._get_converters(),
            model=ModelConverter,
        )

    # ------------------------------------------------------------
    # Language tools
    # ------------------------------------------------------------

    @classmethod
    def _url_localized(cls,
            url: str | None = None,
            lang_code: str | None = None,
            canonical_domain: str | tuple[str, str, str, str, str] | None = None,
            prefetch_langs: bool = False, force_default_lang: bool = False) -> str:
        """ Returns the given URL adapted for the given lang, meaning that:
        1. It will have the lang suffixed to it
        2. The model converter parts will be translated

        If it is not possible to rebuild a path, use the current one instead.
        `url_quote_plus` is applied on the returned path.

        It will also force the canonical domain is requested.
        Eg:
        - `_get_url_localized(lang_fr, '/shop/my-phone-14')` will return
            `/fr/shop/mon-telephone-14`
        - `_get_url_localized(lang_fr, '/shop/my-phone-14', True)` will return
            `<base_url>/fr/shop/mon-telephone-14`
        """
        if not lang_code:
            lang = request.lang
        else:
            lang = request.env['res.lang']._get_data(code=lang_code)

        if not url:
            qs = keep_query()
            url = request.httprequest.path + ('?%s' % qs if qs else '')

        # '/shop/furn-0269-chaise-de-bureau-noire-17?' to
        # '/shop/furn-0269-chaise-de-bureau-noire-17', otherwise -> 404
        url, sep, qs = url.partition('?')

        try:
            # Re-match the controller where the request path routes.
            rule, args = request.env['ir.http']._match(url)
            for key, val in list(args.items()):
                if isinstance(val, models.BaseModel):
                    if isinstance(val._uid, RequestUID):
                        args[key] = val = val.with_user(request.uid)
                    if val.env.context.get('lang') != lang.code:
                        args[key] = val = val.with_context(lang=lang.code)
                    if prefetch_langs:
                        args[key] = val = val.with_context(prefetch_langs=True)
            router = http.root.get_db_router(request.db).bind('')
            path = router.build(rule.endpoint, args)
        except (NotFound, AccessError, MissingError):
            # The build method returns a quoted URL so convert in this case for consistency.
            path = werkzeug.urls.url_quote_plus(url, safe='/')
        if force_default_lang or lang != request.env['ir.http']._get_default_lang():
            path = f'/{lang.url_code}{path if path != "/" else ""}'

        if canonical_domain:
            # canonical URLs should not have qs
            return werkzeug.urls.url_join(canonical_domain, path)

        return path + sep + qs

    @classmethod
    def _url_lang(cls, path_or_uri: str, lang_code: str | None = None) -> str:
        ''' Given a relative URL, make it absolute and add the required lang or
            remove useless lang.
            Nothing will be done for absolute or invalid URL.
            If there is only one language installed, the lang will not be handled
            unless forced with `lang` parameter.

            :param lang_code: Must be the lang `code`. It could also be something
                              else, such as `'[lang]'` (used for url_return).
        '''
        Lang = request.env['res.lang']
        location = path_or_uri.strip()
        force_lang = lang_code is not None
        try:
            url = urllib.parse.urlparse(location)
        except ValueError:
            # e.g. Invalid IPv6 URL, `urllib.parse.urlparse('http://]')`
            url = False
        # relative URL with either a path or a force_lang
        if url and not url.netloc and not url.scheme and (url.path or force_lang):
            location = werkzeug.urls.url_join(request.httprequest.path, location)
            lang_url_codes = [info.url_code for info in Lang._get_frontend().values()]
            lang_code = lang_code or request.context['lang']
            lang_url_code = Lang._get_data(code=lang_code).url_code
            lang_url_code = lang_url_code if lang_url_code in lang_url_codes else lang_code
            if (len(lang_url_codes) > 1 or force_lang) and cls._is_multilang_url(location, lang_url_codes):
                loc, sep, qs = location.partition('?')
                ps = loc.split('/')
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
                    # Remove the last empty string to avoid trailing / after joining
                    if not ps[-1]:
                        ps.pop(-1)

                location = '/'.join(ps) + sep + qs
        return location

    @classmethod
    def _url_for(cls, url_from: str, lang_code: str | None = None) -> str:
        ''' Return the url with the rewriting applied.
            Nothing will be done for absolute URL, invalid URL, or short URL from 1 char.

            :param url_from: The URL to convert.
            :param lang_code: Must be the lang `code`. It could also be something
                              else, such as `'[lang]'` (used for url_return).
        '''
        return cls._url_lang(url_from, lang_code=lang_code)

    @classmethod
    def _is_multilang_url(cls, local_url: str, lang_url_codes: list[str] | None = None) -> bool:
        ''' Check if the given URL content is supposed to be translated.
            To be considered as translatable, the URL should either:
            1. Match a POST (non-GET actually) controller that is `website=True` and
            either `multilang` specified to True or if not specified, with `type='http'`.
            2. If not matching 1., everything not under /static/ or /web/ will be translatable
        '''
        if not lang_url_codes:
            lang_url_codes = [lg.url_code for lg in request.env['res.lang']._get_frontend().values()]
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
        except Exception as exception:  # noqa: BLE001
            _logger.warning(exception)
            return False

    @classmethod
    def _get_default_lang(cls) -> LangData:
        lang_code = request.env['ir.default'].sudo()._get('res.partner', 'lang')
        if lang_code:
            return request.env['res.lang']._get_data(code=lang_code)
        return next(iter(request.env['res.lang']._get_active_by('code').values()))

    @api.model
    def get_frontend_session_info(self) -> dict:
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
    def get_translation_frontend_modules(self) -> list[str]:
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
    def _get_translation_frontend_modules_domain(cls) -> list[tuple[str, str, typing.Any]]:
        """ Return a domain to list the domain adding web-translations and
            dynamic resources that may be used frontend views
        """
        return []

    @classmethod
    def _get_translation_frontend_modules_name(cls) -> list[str]:
        """ Return a list of module name where web-translations and
            dynamic resources may be used in frontend views
        """
        return ['web']

    @api.model
    def get_nearest_lang(self, lang_code: str) -> str:
        """ Try to find a similar lang. Eg: fr_BE and fr_FR
            :param lang_code: the lang `code` (en_US)
        """
        if not lang_code:
            return None

        frontend_langs = self.env['res.lang']._get_frontend()
        if lang_code in frontend_langs:
            return lang_code

        short = lang_code.partition('_')[0]
        if not short:
            return None
        return next((code for code in frontend_langs if code.startswith(short)), None)

    # ------------------------------------------------------------
    # Routing and diplatch
    # ------------------------------------------------------------

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

        # Some URLs in website are concatenated, first url ends with /,
        # second url starts with /, resulting url contains two following
        # slashes that must be merged.
        if allow_redirect and '//' in path:
            new_url = path.replace('//', '/')
            werkzeug.exceptions.abort(request.redirect(new_url, code=301, local=True))

        # There is no user on the environment yet but the following code
        # requires one to set the lang on the request. Temporary grant
        # the public user. Don't try it at home!
        real_env = request.env
        try:
            request.registry['ir.http']._auth_method_public()  # it calls update_env
            nearest_url_lang = request.env['ir.http'].get_nearest_lang(request.env['res.lang']._get_data(url_code=url_lang_str).code or url_lang_str)
            cookie_lang = request.env['ir.http'].get_nearest_lang(request.cookies.get('frontend_lang'))
            context_lang = request.env['ir.http'].get_nearest_lang(real_env.context.get('lang'))
            default_lang = cls._get_default_lang()
            request.lang = request.env['res.lang']._get_data(code=(
                nearest_url_lang or cookie_lang or context_lang or default_lang.code
            ))
            request_url_code = request.lang.url_code
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
            redirect.set_cookie('frontend_lang', request.lang.code)
            werkzeug.exceptions.abort(redirect)

        # See /6, default lang in url, /en/home -> /home
        elif url_lang_str == default_lang.url_code and allow_redirect:
            _logger.debug("%r (lang: %r) default lang in url, redirect", path, request_url_code)
            redirect = request.redirect_query(path_no_lang, request.httprequest.args)
            redirect.set_cookie('frontend_lang', default_lang.code)
            werkzeug.exceptions.abort(redirect)

        # See /7, lang alias in url, /fr_FR/home -> /fr/home
        elif url_lang_str != request_url_code and allow_redirect:
            _logger.debug("%r (lang: %r) lang alias in url, redirect", path, request_url_code)
            redirect = request.redirect_query(f'/{request_url_code}{path_no_lang}', request.httprequest.args, code=301)
            redirect.set_cookie('frontend_lang', request.lang.code)
            werkzeug.exceptions.abort(redirect)

        # See /8, homepage with trailing slash. /fr_BE/ -> /fr_BE
        elif path == f'/{url_lang_str}/' and allow_redirect:
            _logger.debug("%r (lang: %r) homepage with trailing slash, redirect", path, request_url_code)
            redirect = request.redirect_query(path[:-1], request.httprequest.args, code=301)
            redirect.set_cookie('frontend_lang', default_lang.code)
            werkzeug.exceptions.abort(redirect)

        # See /9, valid lang in url
        elif url_lang_str == request_url_code:
            # Rewrite the URL to remove the lang
            _logger.debug("%r (lang: %r) valid lang in url, rewrite url and continue", path, request_url_code)
            request.reroute(path_no_lang)
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
                except odoo.exceptions.MissingError as exc:
                    raise werkzeug.exceptions.NotFound() from exc
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
        request.update_context(lang=request.lang.code)
        if request.cookies.get('frontend_lang') != request.lang.code:
            request.future_response.set_cookie('frontend_lang', request.lang.code)

    # ------------------------------------------------------------
    # Exception
    # ------------------------------------------------------------

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
        if code in (404, 403):
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

        response = Response(html, status=code, content_type='text/html;charset=utf-8')
        cls._post_dispatch(response)
        return response

    # ------------------------------------------------------------
    # Rewrite
    # ------------------------------------------------------------

    @api.model
    @tools.ormcache('path', 'query_args', cache='routing.rewrites')
    def url_rewrite(self, path, query_args=None):
        new_url = False
        router = http.root.get_db_router(request.db).bind('')
        endpoint = False
        try:
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
