# Part of Odoo. See LICENSE file for full copyright and licensing details.
#----------------------------------------------------------
# ir_http modular http routing
#----------------------------------------------------------
import hashlib
import json
import logging
import os
import re
import threading
import unicodedata

import werkzeug
import werkzeug.exceptions
import werkzeug.routing
import werkzeug.utils
from werkzeug.datastructures import WWWAuthenticate
from werkzeug.exceptions import Unauthorized

try:
    from werkzeug.routing import NumberConverter
except ImportError:
    from werkzeug.routing.converters import NumberConverter  # moved in werkzeug 2.2.2

# optional python-slugify import (https://github.com/un33k/python-slugify)
try:
    import slugify as slugify_lib
except ImportError:
    slugify_lib = None

import odoo
from odoo import api, http, models, tools
from odoo.api import SUPERUSER_ID
from odoo.exceptions import AccessDenied
from odoo.http import ROUTING_KEYS, SAFE_HTTP_METHODS, Response, request
from odoo.modules.registry import Registry
from odoo.service import security
from odoo.tools.json import json_default
from odoo.tools.misc import get_lang, submap
from odoo.tools.translate import code_translations

_logger = logging.getLogger(__name__)

# see also mimetypes module: https://docs.python.org/3/library/mimetypes.html and odoo.tools.mimetypes
EXTENSION_TO_WEB_MIMETYPES = {
    '.css': 'text/css',
    '.less': 'text/less',
    '.scss': 'text/scss',
    '.js': 'text/javascript',
    '.xml': 'text/xml',
    '.csv': 'text/csv',
    '.html': 'text/html',
}


class RequestUID(object):
    def __init__(self, **kw):
        self.__dict__.update(kw)


class ModelConverter(werkzeug.routing.BaseConverter):
    regex = r'[0-9]+'

    def __init__(self, url_map, model=False):
        super().__init__(url_map)
        self.model = model

        IrHttp = Registry(threading.current_thread().dbname)['ir.http']
        self.slug = IrHttp._slug
        self.unslug = IrHttp._unslug

    def to_python(self, value: str) -> models.BaseModel:
        _uid = RequestUID(value=value, converter=self)
        env = api.Environment(request.env.cr, _uid, request.env.context)
        return env[self.model].browse(self.unslug(value)[1])

    def to_url(self, value: models.BaseModel) -> str:
        return self.slug(value)


class ModelsConverter(werkzeug.routing.BaseConverter):
    regex = r'[0-9,]+'

    def __init__(self, url_map, model=False):
        super().__init__(url_map)
        self.model = model

    def to_python(self, value: str) -> models.BaseModel:
        _uid = RequestUID(value=value, converter=self)
        env = api.Environment(request.env.cr, _uid, request.env.context)
        return env[self.model].browse(int(v) for v in value.split(','))

    def to_url(self, value: models.BaseModel) -> str:
        return ",".join(value.ids)


class SignedIntConverter(NumberConverter):
    regex = r'-?\d+'
    num_convert = int


class LazyCompiledBuilder:
    def __init__(self, rule, _compile_builder, append_unknown):
        self.rule = rule
        self._callable = None
        self._compile_builder = _compile_builder
        self._append_unknown = append_unknown

    def __get__(self, *args):
        # Rule.compile will actually call
        #
        #   self._build = self._compile_builder(False).__get__(self, None)
        #   self._build_unknown = self._compile_builder(True).__get__(self, None)
        #
        # meaning the _build and _build unkown will contain _compile_builder().__get__(self, None).
        # This is why this override of __get__ is needed.
        return self

    def __call__(self, *args, **kwargs):
        if self._callable is None:
            self._callable = self._compile_builder(self._append_unknown).__get__(self.rule, None)
            del self.rule
            del self._compile_builder
            del self._append_unknown
        return self._callable(*args, **kwargs)


class FasterRule(werkzeug.routing.Rule):
    """
    _compile_builder is a major part of the routing map generation and rules
    are actually not build so often.
    This classe makes calls to _compile_builder lazy
    """
    def _compile_builder(self, append_unknown=True):
        return LazyCompiledBuilder(self, super()._compile_builder, append_unknown)


class IrHttp(models.AbstractModel):
    _name = 'ir.http'
    _description = "HTTP Routing"

    @classmethod
    def _slugify_one(cls, value: str, max_length: int = None) -> str:
        """ Transform a string to a slug that can be used in a url path.
            This method will first try to do the job with python-slugify if present.
            Otherwise it will process string by replacing spaces and underscores with
            dashes '-',removing every character that is not a word or a dash,
            collapsing multiple dashes like --- into a single dash, removing leading
            and trailing dashes and converting to lowercase.
            Example: ^h☺e$#!l(%l}o 你好& becomes hello-你好
        """
        if slugify_lib:
            # There are 2 different libraries only python-slugify is supported
            try:
                return slugify_lib.slugify(value, max_length=max_length)
            except TypeError:
                pass
        uni = unicodedata.normalize('NFKD', value)
        slugified_segments = []
        for slug in re.split('-|_| ', uni):
            slug = re.sub(r'([^\w-])+', '', slug)
            slug = re.sub(r'--+', '-', slug)
            slug = slug.strip('-')
            if slug:
                slugified_segments.append(slug.lower())
        slugified_str = '-'.join(slugified_segments)
        return slugified_str[:max_length]

    @classmethod
    def _slugify(cls, value: str, max_length: int = None, path: bool = False) -> str:
        if not path:
            return cls._slugify_one(value, max_length=max_length)
        else:
            res = []
            for u in value.split('/'):
                s = cls._slugify_one(u, max_length=max_length)
                if s:
                    res.append(s)
            # check if supported extension
            path_no_ext, ext = os.path.splitext(value)
            if ext in EXTENSION_TO_WEB_MIMETYPES:
                res[-1] = cls._slugify_one(path_no_ext) + ext
            return '/'.join(res)

    @classmethod
    def _slug(cls, value: models.BaseModel | tuple[int, str]) -> str:
        if isinstance(value, tuple):
            return str(value[0])
        return str(value.id)

    @classmethod
    def _unslug(cls, value: str) -> tuple[str | None, int] | tuple[None, None]:
        try:
            return None, int(value)
        except ValueError:
            return None, None

    #------------------------------------------------------
    # Routing map
    #------------------------------------------------------

    @classmethod
    def _get_converters(cls) -> dict[str, type]:
        return {'model': ModelConverter, 'models': ModelsConverter, 'int': SignedIntConverter}

    @classmethod
    def _match(cls, path_info):
        rule, args = request.env['ir.http'].routing_map().bind_to_environ(request.httprequest.environ).match(path_info=path_info, return_rule=True)
        return rule, args

    @classmethod
    def _get_public_users(cls):
        return [request.env['ir.model.data']._xmlid_to_res_model_res_id('base.public_user')[1]]

    @classmethod
    def _auth_method_bearer(cls):
        headers = request.httprequest.headers

        def get_http_authorization_bearer_token():
            # werkzeug<2.3 doesn't expose `authorization.token` (for bearer authentication)
            # check header directly
            header = headers.get("Authorization")
            if header and (m := re.match(r"^bearer\s+(.+)$", header, re.IGNORECASE)):
                return m.group(1)
            return None

        def check_sec_headers():
            """Protection against CSRF attacks.
            Modern browsers automatically add Sec- headers that we can check to protect against CSRF.
            https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Sec-Fetch-User
            """
            return (
                headers.get("Sec-Fetch-Dest") == "document"
                and headers.get("Sec-Fetch-Mode") == "navigate"
                and headers.get("Sec-Fetch-Site") in ('none', 'same-origin')
                and headers.get("Sec-Fetch-User") == "?1"
            )

        if token := get_http_authorization_bearer_token():
            # 'rpc' scope does not really exist, we basically require a global key (scope NULL)
            uid = request.env['res.users.apikeys']._check_credentials(scope='rpc', key=token)
            if not uid:
                e = "Invalid apikey"
                raise Unauthorized(e, www_authenticate=WWWAuthenticate('bearer'))
            if request.env.uid and request.env.uid != uid:
                e = "Session user does not match the used apikey."
                raise AccessDenied(e)
            request.update_env(user=uid)
            request.session.can_save = False  # stateless
        elif not request.env.uid:
            e = "User not authenticated, use an API Key with a Bearer Authorization header."
            raise Unauthorized(e, www_authenticate=WWWAuthenticate('bearer'))
        elif not check_sec_headers():
            e = 'Missing "Authorization" or Sec-headers for interactive usage.'
            raise werkzeug.exceptions.Unauthorized(e, www_authenticate=WWWAuthenticate('bearer'))
        cls._auth_method_user()

    @classmethod
    def _auth_method_user(cls):
        if request.env.uid in [None] + cls._get_public_users():
            raise http.SessionExpiredException("Session expired")

    @classmethod
    def _auth_method_none(cls):
        request.env = api.Environment(request.env.cr, None, request.env.context)
        request.env.transaction.default_env = request.env

    @classmethod
    def _auth_method_public(cls):
        if request.env.uid is None:
            public_user = request.env.ref('base.public_user')
            request.update_env(user=public_user.id)

    @classmethod
    def _authenticate(cls, endpoint):
        auth = 'none' if http.is_cors_preflight(request, endpoint) else endpoint.routing['auth']
        cls._authenticate_explicit(auth)

    @classmethod
    def _authenticate_explicit(cls, auth):
        try:
            if request.session.uid is not None:
                if not security.check_session(request.session, request.env, request):
                    request.session.logout(keep_db=True)
                    request.env = api.Environment(request.env.cr, None, request.session.context)
            getattr(cls, f'_auth_method_{auth}')()
        except (AccessDenied, http.SessionExpiredException, werkzeug.exceptions.HTTPException):
            raise
        except Exception:
            _logger.info("Exception during request Authentication.", exc_info=True)
            raise AccessDenied()

    @classmethod
    def _geoip_resolve(cls):
        return request._geoip_resolve()

    @classmethod
    def _sanitize_cookies(cls, cookies):
        pass

    @classmethod
    def _pre_dispatch(cls, rule, args):
        ICP = request.env['ir.config_parameter'].with_user(SUPERUSER_ID)

        # Change the default database-wide 128MiB upload limit on the
        # ICP value. Do it before calling http's generic pre_dispatch
        # so that the per-route limit @route(..., max_content_length=x)
        # takes over.
        try:
            key = 'web.max_file_upload_size'
            if (value := ICP.get_param(key, None)) is not None:
                request.httprequest.max_content_length = int(value)
        except ValueError:  # better not crash on ALL requests
            _logger.error("invalid %s: %r, using %s instead",
                key, value, request.httprequest.max_content_length,
            )

        request.dispatcher.pre_dispatch(rule, args)

        # verify the default language set in the context is valid,
        # otherwise fallback on the company lang, english or the first
        # lang installed
        env = request.env if request.env.uid else request.env['base'].with_user(SUPERUSER_ID).env
        request.update_context(lang=get_lang(env).code)

        # Replace uid and lang placeholder by the current request.env.uid and request.env.lang
        # before checking the access.
        for key, val in list(args.items()):
            if not isinstance(val, models.BaseModel):
                continue

            args[key] = val.with_env(request.env)

        for key, val in list(args.items()):
            if not isinstance(val, models.BaseModel):
                continue

            try:
                # explicitly crash now, instead of crashing later
                args[key].check_access('read')
            except (odoo.exceptions.AccessError, odoo.exceptions.MissingError) as e:
                # custom behavior in case a record is not accessible / has been removed
                if handle_error := rule.endpoint.routing.get('handle_params_access_error'):
                    if response := handle_error(e, **args):
                        werkzeug.exceptions.abort(response)
                if request.env.user.is_public or isinstance(e, odoo.exceptions.MissingError):
                    raise werkzeug.exceptions.NotFound() from e
                raise

    @classmethod
    def _dispatch(cls, endpoint):
        # Verify the captcha in case it was set on @http.route
        # https://httpwg.org/specs/rfc9110.html#safe.methods
        captcha = endpoint.routing.get('captcha')
        if captcha and request.httprequest.method not in SAFE_HTTP_METHODS:
            request.env['ir.http']._verify_request_recaptcha_token(captcha)
        result = endpoint(**request.params)
        if isinstance(result, Response) and result.is_qweb:
            result.flatten()
        return result

    @classmethod
    def _post_dispatch(cls, response):
        request.dispatcher.post_dispatch(response)

    @classmethod
    def _post_logout(cls):
        pass

    @classmethod
    def _handle_error(cls, exception):
        return request.dispatcher.handle_error(exception)

    @classmethod
    def _serve_fallback(cls):
        model = request.env['ir.attachment']
        attach = model.sudo()._get_serve_attachment(request.httprequest.path)
        if attach and (attach.store_fname or attach.db_datas):
            return attach._to_http_stream().get_response()

    @classmethod
    def _redirect(cls, location, code=303):
        return werkzeug.utils.redirect(location, code=code, Response=Response)

    def _generate_routing_rules(self, modules, converters):
        return http._generate_routing_rules(modules, False, converters)

    @tools.ormcache('key', cache='routing')
    def routing_map(self, key=None):
        _logger.info("Generating routing map for key %s", str(key))
        registry = Registry(threading.current_thread().dbname)
        installed = registry._init_modules.union(odoo.tools.config['server_wide_modules'])
        mods = sorted(installed)
        # Note : when routing map is generated, we put it on the class `cls`
        # to make it available for all instance. Since `env` create an new instance
        # of the model, each instance will regenared its own routing map and thus
        # regenerate its EndPoint. The routing map should be static.
        routing_map = werkzeug.routing.Map(strict_slashes=False, converters=self._get_converters())
        for url, endpoint in self._generate_routing_rules(mods, converters=self._get_converters()):
            routing = submap(endpoint.routing, ROUTING_KEYS)
            if routing['methods'] is not None and 'OPTIONS' not in routing['methods']:
                routing['methods'] = [*routing['methods'], 'OPTIONS']
            rule = FasterRule(url, endpoint=endpoint, **routing)
            rule.merge_slashes = False
            routing_map.add(rule)
        return routing_map

    @api.autovacuum
    def _gc_sessions(self):
        if os.getenv("ODOO_SKIP_GC_SESSIONS"):
            return
        http.root.session_store.vacuum(max_lifetime=http.get_session_max_inactivity(self.env))

    @api.model
    def _get_translations_for_webclient(self, modules, lang):
        if not lang:
            lang = self.env.context.get("lang")
        lang_data = self.env['res.lang']._get_data(code=lang)
        lang_params = {
            "name": lang_data.name,
            "code": lang_data.code,
            "direction": lang_data.direction,
            "date_format": lang_data.date_format,
            "time_format": lang_data.time_format,
            "grouping": lang_data.grouping,
            "decimal_point": lang_data.decimal_point,
            "thousands_sep": lang_data.thousands_sep,
            "week_start": int(lang_data.week_start),
        } if lang_data else None

        # Regional languages (ll_CC) must inherit/override their parent lang (ll), but this is
        # done server-side when the language is loaded, so we only need to load the user's lang.
        translations_per_module = {}
        for module in modules:
            translations_per_module[module] = code_translations.get_web_translations(module, lang)

        return translations_per_module, lang_params

    @api.model
    @tools.ormcache('frozenset(modules)', 'lang')
    def _get_web_translations_hash(self, modules, lang):
        translations, lang_params = self._get_translations_for_webclient(modules, lang)
        translation_cache = {
            'lang_parameters': lang_params,
            'modules': translations,
            'lang': lang,
            'multi_lang': len(self.env['res.lang'].sudo().get_installed()) > 1,
        }
        if self.env.context.get('cache_translation_data'):
            # put in the transactional cache
            self.env.cr.cache['translation_data'] = translation_cache
        return hashlib.sha1(json.dumps(translation_cache, sort_keys=True, default=json_default).encode()).hexdigest()

    @classmethod
    def _is_allowed_cookie(cls, cookie_type):
        return True if cookie_type == 'required' else bool(request.env.user)

    @api.model
    def _verify_request_recaptcha_token(self, action: str):
        return
