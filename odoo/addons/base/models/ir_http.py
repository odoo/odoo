# Part of Odoo. See LICENSE file for full copyright and licensing details.
#----------------------------------------------------------
# ir_http modular http routing
#----------------------------------------------------------
import base64
import hashlib
import json
import logging
import mimetypes
import os
import re
import sys
import traceback
import threading

import werkzeug
import werkzeug.exceptions
import werkzeug.routing
import werkzeug.utils

try:
    from werkzeug.routing import NumberConverter
except ImportError:
    from werkzeug.routing.converters import NumberConverter  # moved in werkzeug 2.2.2

import odoo
from odoo import api, http, models, tools, SUPERUSER_ID
from odoo.exceptions import AccessDenied, AccessError, MissingError
from odoo.http import request, Response, ROUTING_KEYS, Stream
from odoo.modules.registry import Registry
from odoo.service import security
from odoo.tools import get_lang, submap
from odoo.tools.translate import code_translations

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

    #------------------------------------------------------
    # Routing map
    #------------------------------------------------------

    @classmethod
    def _get_converters(cls):
        return {'model': ModelConverter, 'models': ModelsConverter, 'int': SignedIntConverter}

    @classmethod
    def _match(cls, path_info):
        rule, args = request.env['ir.http'].routing_map().bind_to_environ(request.httprequest.environ).match(path_info=path_info, return_rule=True)
        return rule, args

    @classmethod
    def _get_public_users(cls):
        return [request.env['ir.model.data']._xmlid_to_res_model_res_id('base.public_user')[1]]

    @classmethod
    def _auth_method_user(cls):
        if request.env.uid in [None] + cls._get_public_users():
            raise http.SessionExpiredException("Session expired")

    @classmethod
    def _auth_method_none(cls):
        request.env = api.Environment(request.env.cr, None, request.env.context)

    @classmethod
    def _auth_method_public(cls):
        if request.env.uid is None:
            public_user = request.env.ref('base.public_user')
            request.update_env(user=public_user.id)

    @classmethod
    def _authenticate(cls, endpoint):
        auth = 'none' if http.is_cors_preflight(request, endpoint) else endpoint.routing['auth']

        try:
            if request.session.uid is not None:
                if not security.check_session(request.session, request.env):
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

        # Replace uid placeholder by the current request.env.uid
        for key, val in list(args.items()):
            if isinstance(val, models.BaseModel) and isinstance(val._uid, RequestUID):
                args[key] = val.with_user(request.env.uid)

        # verify the default language set in the context is valid,
        # otherwise fallback on the company lang, english or the first
        # lang installed
        env = request.env if request.env.uid else request.env['base'].with_user(SUPERUSER_ID).env
        request.update_context(lang=get_lang(env)._get_cached('code'))

        for key, val in list(args.items()):
            if not isinstance(val, models.BaseModel):
                continue

            try:
                # explicitly crash now, instead of crashing later
                args[key].check_access_rights('read')
                args[key].check_access_rule('read')
            except (odoo.exceptions.AccessError, odoo.exceptions.MissingError) as e:
                # custom behavior in case a record is not accessible / has been removed
                if handle_error := rule.endpoint.routing.get('handle_params_access_error'):
                    if response := handle_error(e):
                        werkzeug.exceptions.abort(response)
                if isinstance(e, odoo.exceptions.MissingError):
                    raise werkzeug.exceptions.NotFound() from e
                raise

    @classmethod
    def _dispatch(cls, endpoint):
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
            return Stream.from_attachment(attach).get_response()

    @classmethod
    def _redirect(cls, location, code=303):
        return werkzeug.utils.redirect(location, code=code, Response=Response)

    def _generate_routing_rules(self, modules, converters):
        return http._generate_routing_rules(modules, False, converters)

    @tools.ormcache('key', cache='routing')
    def routing_map(self, key=None):
        _logger.info("Generating routing map for key %s", str(key))
        registry = Registry(threading.current_thread().dbname)
        installed = registry._init_modules.union(odoo.conf.server_wide_modules)
        if tools.config['test_enable'] and odoo.modules.module.current_test:
            installed.add(odoo.modules.module.current_test)
        mods = sorted(installed)
        # Note : when routing map is generated, we put it on the class `cls`
        # to make it available for all instance. Since `env` create an new instance
        # of the model, each instance will regenared its own routing map and thus
        # regenerate its EndPoint. The routing map should be static.
        routing_map = werkzeug.routing.Map(strict_slashes=False, converters=self._get_converters())
        for url, endpoint in self._generate_routing_rules(mods, converters=self._get_converters()):
            routing = submap(endpoint.routing, ROUTING_KEYS)
            if routing['methods'] is not None and 'OPTIONS' not in routing['methods']:
                routing['methods'] = routing['methods'] + ['OPTIONS']
            rule = FasterRule(url, endpoint=endpoint, **routing)
            rule.merge_slashes = False
            routing_map.add(rule)
        return routing_map

    @api.autovacuum
    def _gc_sessions(self):
        if os.getenv("ODOO_SKIP_GC_SESSIONS"):
            return
        ICP = self.env["ir.config_parameter"]
        max_lifetime = int(ICP.get_param('sessions.max_inactivity_seconds', http.SESSION_LIFETIME))
        http.root.session_store.vacuum(max_lifetime=max_lifetime)

    @api.model
    def get_translations_for_webclient(self, modules, lang):
        if not modules:
            modules = self.pool._init_modules
        if not lang:
            lang = self._context.get("lang")
        langs = self.env['res.lang']._lang_get(lang)
        lang_params = None
        if langs:
            lang_params = {
                "name": langs.name,
                "direction": langs.direction,
                "date_format": langs.date_format,
                "time_format": langs.time_format,
                "grouping": langs.grouping,
                "decimal_point": langs.decimal_point,
                "thousands_sep": langs.thousands_sep,
                "week_start": langs.week_start,
            }
            lang_params['week_start'] = int(lang_params['week_start'])
            lang_params['code'] = lang

        # Regional languages (ll_CC) must inherit/override their parent lang (ll), but this is
        # done server-side when the language is loaded, so we only need to load the user's lang.
        translations_per_module = {}
        for module in modules:
            translations_per_module[module] = code_translations.get_web_translations(module, lang)

        return translations_per_module, lang_params

    @api.model
    @tools.ormcache('frozenset(modules)', 'lang')
    def get_web_translations_hash(self, modules, lang):
        translations, lang_params = self.get_translations_for_webclient(modules, lang)
        translation_cache = {
            'lang_parameters': lang_params,
            'modules': translations,
            'lang': lang,
            'multi_lang': len(self.env['res.lang'].sudo().get_installed()) > 1,
        }
        return hashlib.sha1(json.dumps(translation_cache, sort_keys=True).encode()).hexdigest()

    @classmethod
    def _is_allowed_cookie(cls, cookie_type):
        return True
