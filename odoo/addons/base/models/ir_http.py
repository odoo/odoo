import logging
import os
import re
import threading
import unicodedata
from pathlib import Path
from typing import Any

import werkzeug.routing
import werkzeug.utils
from werkzeug.datastructures import WWWAuthenticate
from werkzeug.routing.converters import NumberConverter

import odoo
from odoo import api, http, models, tools
from odoo.api import SUPERUSER_ID
from odoo.exceptions import AccessDenied
from odoo.http import (
    SAFE_HTTP_METHODS,
    HTTPException,
    NotFound,
    Response,
    Unauthorized,
    abort,
    prepare_routing_map,
    request,
)
from odoo.libs.debug_log import DebugLog
from odoo.libs.hashing import cache_hash
from odoo.libs.json import OPT_SORT_KEYS
from odoo.libs.json import dumps_bytes as json_dumps_bytes
from odoo.modules.registry import Registry
from odoo.service import security
from odoo.tools.assets.constants import EXTENSION_TO_WEB_MIMETYPES
from odoo.tools.json import json_default
from odoo.tools.misc import get_lang, str2bool
from odoo.tools.translate import code_translations

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)

_SLUG_SPLIT_RE = re.compile(r"[-_ ]")
_SLUG_NONWORD_RE = re.compile(r"[^\w]+")


class RequestUID:
    def __init__(self, **kw: Any) -> None:
        self.__dict__.update(kw)


class ModelConverter(werkzeug.routing.BaseConverter):
    regex = r"[0-9]+"

    def __init__(self, url_map: Any, model: str | bool = False) -> None:
        super().__init__(url_map)
        self.model = model

        IrHttp = Registry(threading.current_thread().dbname)["ir.http"]
        self.slug = IrHttp._slug
        self.unslug = IrHttp._unslug

    def to_python(self, value: str) -> models.BaseModel:
        _uid = RequestUID(value=value, converter=self)
        env = api.Environment(request.env.cr, _uid, request.env.context)
        record_id = self.unslug(value)[1]
        _debug.logic("route_model_converted", model=self.model, id=record_id)
        return env[self.model].browse(record_id)

    def to_url(self, value: models.BaseModel) -> str:
        return self.slug(value)


class ModelsConverter(werkzeug.routing.BaseConverter):
    regex = r"[0-9,]+"

    def __init__(self, url_map: Any, model: str | bool = False) -> None:
        super().__init__(url_map)
        self.model = model

    def to_python(self, value: str) -> models.BaseModel:
        _uid = RequestUID(value=value, converter=self)
        env = api.Environment(request.env.cr, _uid, request.env.context)
        ids = [int(v) for v in value.split(",") if v]
        _debug.logic("route_models_converted", model=self.model, count=len(ids))
        return env[self.model].browse(ids)

    def to_url(self, value: models.BaseModel) -> str:
        return ",".join(str(i) for i in value.ids)


class SignedIntConverter(NumberConverter):
    regex = r"-?\d+"
    num_convert = int


class IrHttp(models.AbstractModel):
    _name = "ir.http"
    _description = "HTTP Routing"

    @classmethod
    def _slugify_one(cls, value: str, max_length: int | None = None) -> str:
        uni = unicodedata.normalize("NFKD", value)
        slugified_segments = []
        for slug in _SLUG_SPLIT_RE.split(uni):
            slug = _SLUG_NONWORD_RE.sub("", slug)
            if slug:
                slugified_segments.append(slug.lower())
        slugified_str = unicodedata.normalize("NFC", "-".join(slugified_segments))
        return slugified_str[:max_length]

    @classmethod
    def _slugify(
        cls, value: str, max_length: int | None = None, path: bool = False
    ) -> str:
        if not path:
            return cls._slugify_one(value, max_length=max_length)
        else:
            res = []
            for u in value.split("/"):
                s = cls._slugify_one(u, max_length=max_length)
                if s:
                    res.append(s)
            p = Path(value)
            ext = p.suffix
            if ext in EXTENSION_TO_WEB_MIMETYPES and res:
                res[-1] = cls._slugify_one(p.stem) + ext
                _debug.logic("slug_extension_kept", ext=ext, segments=len(res))
            return "/".join(res)

    @classmethod
    def _slug(cls, value: models.BaseModel | tuple[int, str]) -> str:
        if isinstance(value, tuple):
            return str(value[0])
        return str(value.id)

    @classmethod
    def _unslug(cls, value: str) -> tuple[None, int] | tuple[None, None]:
        try:
            return None, int(value)
        except ValueError:
            _debug.logic("unslug_failed", value=value)
            return None, None

    @api.model
    def _get_request_remote_addr(self) -> str | None:
        if not request or not hasattr(request, "httprequest"):
            return None
        return request.httprequest.remote_addr

    @classmethod
    def _get_converters(cls) -> dict[str, type]:
        return {
            "model": ModelConverter,
            "models": ModelsConverter,
            "int": SignedIntConverter,
        }

    @classmethod
    def _match(cls, path_info: str) -> tuple[werkzeug.routing.Rule, dict[str, Any]]:
        rule, args = (
            request.env["ir.http"]
            .routing_map()
            .bind_to_environ(request.httprequest.environ)
            .match(path_info=path_info, return_rule=True)
        )
        _debug.pipeline(
            "route_matched",
            path=path_info,
            rule=rule.rule,
            args=sorted(args),
        )
        return rule, args

    @classmethod
    def _get_public_users(cls) -> list[int]:
        return [
            request.env["ir.model.data"]._xmlid_to_res_model_res_id("base.public_user")[
                1
            ]
        ]

    @classmethod
    def _auth_method_bearer(cls) -> None:
        headers = request.httprequest.headers

        def get_http_authorization_bearer_token() -> str | None:
            header = headers.get("Authorization")
            if header and (m := re.match(r"^bearer\s+(.+)$", header, re.IGNORECASE)):
                return m.group(1).strip()
            return None

        def is_document_navigation() -> bool:
            return (
                headers.get("Sec-Fetch-Dest") == "document"
                and headers.get("Sec-Fetch-Mode") == "navigate"
                and headers.get("Sec-Fetch-Site") in ("none", "same-origin")
                and headers.get("Sec-Fetch-User") == "?1"
            )

        if token := get_http_authorization_bearer_token():
            uid = request.env["res.users.apikeys"]._check_credentials(
                scope="rpc", key=token
            )
            _debug.logic("bearer_auth", uid=uid, session_uid=request.env.uid)
            if not uid:
                _debug.logic("bearer_auth_refused", reason="invalid_apikey")
                e = "Invalid apikey"
                raise Unauthorized(e, www_authenticate=WWWAuthenticate("bearer"))
            if request.env.uid and request.env.uid != uid:
                _debug.logic(
                    "bearer_auth_refused",
                    reason="session_mismatch",
                    session_uid=request.env.uid,
                    key_uid=uid,
                )
                e = "Session user does not match the used apikey."
                raise AccessDenied(e)
            request.update_env(user=uid)
            request.session.can_save = False
        elif not request.env.uid:
            _debug.logic("bearer_auth", uid=None, reason="no_token_no_session")
            e = "User not authenticated, use an API Key with a Bearer Authorization header."
            raise Unauthorized(e, www_authenticate=WWWAuthenticate("bearer"))
        elif not is_document_navigation():
            _debug.logic("bearer_auth", uid=request.env.uid, reason="not_navigation")
            e = 'Missing "Authorization" or Sec-headers for interactive usage.'
            raise Unauthorized(e, www_authenticate=WWWAuthenticate("bearer"))
        cls._auth_method_user()

    @classmethod
    def _auth_method_user(cls) -> None:
        if request.env.uid in [None] + cls._get_public_users():
            _debug.logic("session_expired", uid=request.env.uid)
            msg = "Session expired"
            raise http.SessionExpiredException(msg)

    @classmethod
    def _auth_method_none(cls) -> None:
        _debug.logic("auth_none", previous_uid=request.env.uid)
        request.update_env(anonymous=True)

    @classmethod
    def _auth_method_public(cls) -> None:
        if request.env.uid is None:
            public_user = request.env.ref("base.public_user")
            _debug.logic("auth_public_assigned", public_uid=public_user.id)
            request.update_env(user=public_user.id)

    @classmethod
    def _authenticate(cls, endpoint: Any) -> None:
        preflight = http.is_cors_preflight(request, endpoint)
        auth = "none" if preflight else endpoint.routing["auth"]
        _debug.pipeline("authenticate", auth=auth, cors_preflight=preflight)
        cls._authenticate_explicit(auth)

    @classmethod
    def _authenticate_explicit(cls, auth: str) -> None:
        try:
            if request.session.uid is not None:
                if not security.is_session_valid(request.session, request.env, request):
                    _debug.logic("session_invalidated", uid=request.session.uid)
                    request.session.logout(keep_db=True)
                    request.update_env(anonymous=True, context=request.session.context)
            auth_method = getattr(cls, f"_auth_method_{auth}", None)
            if auth_method is None:
                _debug.logic("auth_method_unknown", auth=auth)
                msg = f"Unknown authentication method: {auth!r}"
                raise AccessDenied(msg)
            with _debug.perf("authenticate", auth=auth, uid=request.env.uid):
                auth_method()
        except (
            AccessDenied,
            http.SessionExpiredException,
            HTTPException,
        ):
            raise
        except Exception as exc:
            _debug.logic("auth_failed", auth=auth, error=type(exc).__name__)
            _logger.info("Exception during request Authentication.", exc_info=True)
            raise AccessDenied from exc

    @classmethod
    def _update_cookies(cls, cookies: Any) -> None:
        pass

    @classmethod
    def _apply_max_upload_size(cls) -> None:
        current = request.httprequest.max_content_length
        value = (
            request.env["ir.config_parameter"]
            .with_user(SUPERUSER_ID)
            .get_param_int("web.max_file_upload_size", current)
        )
        if value != current:
            request.httprequest.max_content_length = value
            _debug.logic("max_upload_size_applied", bytes=value)

    @classmethod
    def _pre_dispatch(cls, rule: werkzeug.routing.Rule, args: dict[str, Any]) -> None:
        cls._apply_max_upload_size()

        request.dispatcher.pre_dispatch(rule, args)

        env = (
            request.env
            if request.env.uid
            else request.env["base"].with_user(SUPERUSER_ID).env
        )
        request.update_context(lang=get_lang(env).code)

        model_params = 0
        for key, val in list(args.items()):
            if not isinstance(val, models.BaseModel):
                continue

            args[key] = val.with_env(request.env)
            model_params += 1
        _debug.pipeline(
            "pre_dispatch",
            rule=rule.rule,
            uid=request.env.uid,
            params=len(args),
            model_params=model_params,
        )

        for key, val in list(args.items()):
            if not isinstance(val, models.BaseModel):
                continue

            try:
                args[key].check_access("read")
            except (
                odoo.exceptions.AccessError,
                odoo.exceptions.MissingError,
            ) as e:
                _debug.logic(
                    "route_param_inaccessible",
                    param=key,
                    model=args[key]._name,
                    error=type(e).__name__,
                )
                if handle_error := rule.endpoint.routing.get(
                    "handle_params_access_error"
                ):
                    if response := handle_error(e, **args):
                        abort(response)
                if request.env.user.is_public or isinstance(
                    e, odoo.exceptions.MissingError
                ):
                    _debug.logic("route_param_hidden_as_404", param=key)
                    raise NotFound from e
                raise

    @classmethod
    def _dispatch(cls, endpoint: Any) -> Any:
        if (
            captcha := endpoint.routing.get("captcha")
        ) and request.httprequest.method not in SAFE_HTTP_METHODS:
            _debug.logic("captcha_checked", method=request.httprequest.method)
            request.env["ir.http"]._check_request_recaptcha_token(captcha)
        with _debug.perf(
            "dispatch",
            cr=request.env.cr,
            endpoint=endpoint.routing.get("routes", [""])[0],
            method=request.httprequest.method,
        ) as span:
            result = endpoint(**request.params)
            span.set(qweb=isinstance(result, Response) and result.is_qweb)
        if isinstance(result, Response) and result.is_qweb:
            result.flatten()
        return result

    @classmethod
    def _post_dispatch(cls, response: Response) -> None:
        request.dispatcher.post_dispatch(response)

    @classmethod
    def _post_logout(cls) -> None:
        pass

    @classmethod
    def _handle_error(cls, exception: Exception) -> Any:
        _debug.pipeline(
            "handle_error",
            error=type(exception).__name__,
            dispatcher=type(request.dispatcher).__name__,
        )
        return request.dispatcher.prepare_error_response(exception)

    @classmethod
    def _serve_fallback(cls) -> Response | None:
        model = request.env["ir.attachment"]
        attach = model.sudo()._get_serve_attachment(
            request.httprequest.path, extra_domain=[("public", "=", True)]
        )
        _debug.logic(
            "serve_fallback", path=request.httprequest.path, attachment=bool(attach)
        )
        if attach and (attach.store_fname or attach.db_datas):
            return attach._to_http_stream().prepare_response()
        if _debug.logic.enabled and attach:
            _debug.logic("serve_fallback_empty", attachment=attach.id)
        return None

    @classmethod
    def _redirect(cls, location: str, code: int = 303) -> Response:
        return werkzeug.utils.redirect(location, code=code, Response=Response)

    def _generate_routing_rules(self, modules: list[str]) -> Any:
        return http._generate_routing_rules(modules, False)

    @tools.ormcache("key", cache="routing")
    def routing_map(self, key: str | None = None) -> werkzeug.routing.Map:
        _logger.info("Generating routing map for key %s", key)
        installed = self.pool.loaded_modules.union(
            odoo.tools.config["server_wide_modules"]
        )
        mods = sorted(installed)
        with _debug.perf("routing_map", key=key, modules=len(mods)) as span:
            routing_map = prepare_routing_map(
                self._generate_routing_rules(mods),
                converters=self._get_converters(),
            )
            span.set(rules=sum(1 for _rule in routing_map.iter_rules()))
        return routing_map

    @api.autovacuum
    def _gc_sessions(self) -> None:
        if str2bool(os.getenv("ODOO_SKIP_GC_SESSIONS", ""), default=False):
            _debug.logic("gc_sessions_skipped", reason="env_flag")
            return
        max_lifetime = http.get_session_max_inactivity(self.env)
        with _debug.perf("gc_sessions", max_lifetime=max_lifetime):
            http.root.session_store.vacuum(max_lifetime=max_lifetime)

    @api.model
    def _get_translations_for_webclient(
        self, modules: list[str], lang: str | None
    ) -> tuple[dict[str, Any], dict[str, Any] | None]:
        if not lang:
            lang = self.env.context.get("lang")
        lang_data = self.env["res.lang"]._get_data(code=lang)
        if _debug.logic.enabled and not lang_data:
            _debug.logic("web_translations_lang_unknown", lang=lang)
        lang_params = (
            {
                "name": lang_data.name,
                "code": lang_data.code,
                "direction": lang_data.direction,
                "date_format": lang_data.date_format,
                "time_format": lang_data.time_format,
                "grouping": lang_data.grouping,
                "decimal_point": lang_data.decimal_point,
                "thousands_sep": lang_data.thousands_sep,
                "week_start": int(lang_data.week_start),
            }
            if lang_data
            else None
        )

        translations_per_module = {}
        with _debug.perf("web_translations", lang=lang, modules=len(modules)):
            for module in modules:
                translations_per_module[module] = (
                    code_translations.get_web_translations(module, lang)
                )

        return translations_per_module, lang_params

    @api.model
    @tools.ormcache("frozenset(modules)", "lang")
    def _get_web_translations_hash(self, modules: list[str], lang: str) -> str:
        translations, lang_params = self._get_translations_for_webclient(modules, lang)
        translation_cache = {
            "lang_parameters": lang_params,
            "modules": translations,
            "lang": lang,
            "multi_lang": len(self.env["res.lang"].sudo().get_installed()) > 1,
        }
        if self.env.context.get("cache_translation_data"):
            self.env.cr.cache["translation_data"] = translation_cache
        _debug.perf.count(
            "web_translations_hashed",
            lang=lang,
            modules=len(translations),
            multi_lang=translation_cache["multi_lang"],
        )
        return cache_hash(
            json_dumps_bytes(
                translation_cache, default=json_default, option=OPT_SORT_KEYS
            )
        )

    @classmethod
    def _is_allowed_cookie(cls, cookie_type: str) -> bool:
        return cookie_type == "required" or bool(request.env.user)

    @api.model
    def _check_request_recaptcha_token(self, action: str) -> None:
        return
