import contextlib
import logging
import re
import threading
import traceback
import typing
import urllib.parse

import werkzeug.exceptions
import werkzeug.routing
from werkzeug.exceptions import HTTPException, NotFound

from odoo import api, exceptions, http, models, tools
from odoo.exceptions import AccessError, MissingError
from odoo.fields import Domain
from odoo.http import Response, request
from odoo.libs.debug_log import DebugLog
from odoo.tools.urls import keep_query

from odoo.addons.base.models import ir_http
from odoo.addons.base.models.ir_http import RequestUID
from odoo.addons.base.models.res_lang import LangData

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)

_SLUG_NAME = r"\w{1,2}|\w[\w-]+?\w"
_SLUG_ID = r"-?\d+"
_SLUG_END = r"(?=$|\/|#|\?)"
_UNSLUG_RE = re.compile(rf"(?:({_SLUG_NAME})-)?({_SLUG_ID}){_SLUG_END}")
_UNSLUG_ROUTE_PATTERN = rf"(?:(?:{_SLUG_NAME})-)?(?:{_SLUG_ID}){_SLUG_END}"

FRONTEND_TRANSLATIONS_ROUTE = "/website/translations"

_REDIRECTABLE_METHODS = ("GET", "HEAD")


def _lang_base(lang_code: str) -> str:
    return lang_code.partition("_")[0].partition("@")[0]


class ModelConverter(ir_http.ModelConverter):
    def __init__(self, url_map, model=False, domain="[]"):
        super().__init__(url_map, model)
        self.domain = domain
        self.regex = _UNSLUG_ROUTE_PATTERN

    def to_python(self, value) -> models.BaseModel:
        record = super().to_python(value)
        if not record.id:
            raise werkzeug.routing.ValidationError
        if record.id < 0 and not record.exists():
            record = record.browse(abs(record.id))
        return record.with_context(_converter_value=value)


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    @classmethod
    def _slug(cls, value: models.BaseModel | tuple[int, str]) -> str:
        try:
            identifier, name = value.check_singleton().id, value.display_name
        except AttributeError:
            identifier, name = value
        if not identifier:
            _debug.logic("slug_refused", reason="no_id")
            raise ValueError("Cannot slug non-existent record %r" % (value,))
        slugname = cls._slugify(name or "")
        if not slugname:
            return str(identifier)
        return f"{slugname}-{identifier}"

    @classmethod
    def _unslug(cls, value: str) -> tuple[str | None, int] | tuple[None, None]:
        m = _UNSLUG_RE.match(value)
        if not m:
            return None, None
        return m.group(1), int(m.group(2))

    @classmethod
    def _unslug_url(cls, value: str) -> str:
        path, suffix = cls._url_split_suffix(value)
        slash = "/" if path.endswith("/") and path != "/" else ""
        if slash:
            path = path[:-1]
        parts = path.split("/")
        slug_id = cls._unslug(parts[-1])[1]
        if slug_id is None:
            return value
        parts[-1] = str(slug_id)
        return "/".join(parts) + slash + suffix

    @classmethod
    def _get_converters(cls) -> dict[str, type]:
        return dict(
            super()._get_converters(),
            model=ModelConverter,
        )

    @classmethod
    def _url_split_suffix(cls, url: str) -> tuple[str, str]:
        head, hash_, fragment = url.partition("#")
        path, qmark, query = head.partition("?")
        return path, qmark + query + hash_ + fragment

    @classmethod
    def _lang_url_prefix(cls, path: str, url_code: str) -> str:
        if not path.startswith("/"):
            _logger.warning("Lang-prefixing a non root-relative path %r", path)
            _debug.logic("lang_prefix_on_relative_path", path=path, lang=url_code)
            path = "/" + path
        return f"/{url_code}{path if path != '/' else ''}"

    @api.model
    def _frontend_url_codes(self) -> list[str]:
        return [info.url_code for info in self.env["res.lang"]._get_frontend().values()]

    @classmethod
    def _lang_url_split(
        cls, path: str, url_codes: list[str] | None = None
    ) -> tuple[str | None, str]:
        if url_codes is None:
            url_codes = request.env["ir.http"]._frontend_url_codes()
        segments = path.split("/")
        if len(segments) > 1 and segments[1] in url_codes:
            return segments[1], "/" + "/".join(segments[2:])
        return None, path

    @classmethod
    def _lang_url_unprefix(cls, path: str, url_codes: list[str] | None = None) -> str:
        return cls._lang_url_split(path, url_codes)[1]

    @classmethod
    def _url_localized(
        cls,
        url: str | None = None,
        lang_code: str | None = None,
        canonical_domain: str | None = None,
        prefetch_langs: bool = False,
        force_default_lang: bool = False,
    ) -> str:
        if url and (not url.startswith("/") or url.startswith("//")):
            return url

        if not lang_code:
            lang = request.lang
        else:
            lang = request.env["res.lang"]._get_data(code=lang_code)
            if not lang.url_code:
                lang = request.lang

        if not url:
            qs = keep_query()
            url = request.httprequest.path + ("?%s" % qs if qs else "")

        url, suffix = cls._url_split_suffix(url)

        url = cls._lang_url_unprefix(url)

        router = http.root.get_routing_map(request.db, env=request.env)
        try:
            rule, args = router.bind_to_environ(request.httprequest.environ).match(
                path_info=url, return_rule=True
            )
            for key, val in list(args.items()):
                if isinstance(val, models.BaseModel):
                    if isinstance(val.env.uid, RequestUID):
                        args[key] = val = val.with_user(request.env.uid)
                    if val.env.context.get("lang") != lang.code:
                        args[key] = val = val.with_context(lang=lang.code)
                    if prefetch_langs:
                        args[key] = val = val.with_context(prefetch_langs=True)
            path = router.bind("").build(rule.endpoint, args)
        except (
            HTTPException,
            AccessError,
            MissingError,
            werkzeug.routing.BuildError,
            ValueError,
        ):
            _debug.logic("url_localize", by="quote_unrouted", url=url, lang=lang.code)
            path = urllib.parse.quote(url, safe="/%")
        if force_default_lang or lang != request.env["ir.http"]._get_default_lang():
            path = cls._lang_url_prefix(path, lang.url_code)

        if canonical_domain:
            try:
                return tools.urls.urljoin(canonical_domain, path)
            except ValueError:
                # An URL the router could not rebuild is quoted as-is above, so
                # it may still carry '.'/'..' segments -- scanners probe with
                # them. urljoin refuses to build a domain-qualified URL out of
                # such a path, and rightly so: it is not canonical. Degrade to
                # the root-relative path, like the no-domain branch below, as
                # this runs while rendering the error page of that very request.
                return path

        return path + suffix

    @classmethod
    def _url_lang(cls, path_or_uri: str, lang_code: str | None = None) -> str:
        Lang = request.env["res.lang"]
        location = (path_or_uri or "").strip()
        force_lang = lang_code is not None
        try:
            url = urllib.parse.urlparse(location)
        except ValueError:
            url = False
        if url and not url.netloc and not url.scheme and (url.path or force_lang):
            location = urllib.parse.urljoin(request.httprequest.path, location)
            lang_url_codes = request.env["ir.http"]._frontend_url_codes()
            if not lang_code:
                lang_code = request.env.context.get("lang") or getattr(
                    getattr(request, "lang", None), "code", None
                )
            lang_url_code = (
                Lang._get_data(code=lang_code).url_code if lang_code else None
            )
            if lang_url_code not in lang_url_codes:
                lang_url_code = lang_code if isinstance(lang_code, str) else None
            default_url_code = request.env["ir.http"]._get_default_lang().url_code
            if lang_url_code is None:
                lang_url_code = default_url_code
            if (len(lang_url_codes) > 1 or force_lang) and request.env[
                "ir.http"
            ]._is_multilang_url(location, lang_url_codes):
                loc, suffix = cls._url_split_suffix(location)
                if loc.endswith("/") and loc != "/":
                    loc = loc[:-1]
                url_code, rest = cls._lang_url_split(loc, lang_url_codes)
                if url_code is not None:
                    if force_lang:
                        loc = cls._lang_url_prefix(rest, lang_url_code)
                    elif url_code == default_url_code:
                        loc = rest
                elif lang_url_code != default_url_code or force_lang:
                    loc = cls._lang_url_prefix(rest, lang_url_code)

                location = loc + suffix
        return location

    @classmethod
    def _url_for(cls, url_from: str, lang_code: str | None = None) -> str:
        return cls._url_lang(url_from, lang_code=lang_code)

    @api.model
    def _is_multilang_url(
        self, local_url: str, lang_url_codes: list[str] | None = None
    ) -> bool:
        if not lang_url_codes:
            lang_url_codes = self.env["ir.http"]._frontend_url_codes()
        path, _suffix = self._url_split_suffix(local_url)
        path = self._lang_url_unprefix(path, lang_url_codes)

        if "/static/" in path or path.startswith("/web/"):
            _debug.logic(
                "multilang_url", verdict=False, reason="asset_or_web", url=local_url
            )
            return False

        try:
            _, func = self.env["ir.http"].url_rewrite(path)

            return not func or (
                func.routing.get("website", False)
                and func.routing.get("multilang", func.routing["type"] == "http")
            )
        except Exception:
            _logger.warning(
                "Could not determine multilang status for %r, assuming False",
                local_url,
                exc_info=True,
            )
            _debug.logic(
                "multilang_url", verdict=False, reason="rewrite_failed", url=local_url
            )
            return False

    @api.model
    @tools.ormcache()
    def _get_default_lang_code(self) -> str | None:
        return self.env["ir.default"].sudo()._get("res.partner", "lang")

    @api.model
    def _get_default_lang(self) -> LangData:
        Lang = self.env["res.lang"]
        lang_code = self._get_default_lang_code()
        lang = Lang._get_data(code=lang_code) if lang_code else None
        if not lang:
            lang = next(iter(Lang._get_active_by_field("code").values()))
            _debug.logic("default_lang", by="first_active", lang=lang.code)
        return lang

    @api.model
    def get_frontend_session_info(self) -> dict:
        session_info = super().get_frontend_session_info()

        if getattr(request, "is_frontend", False):
            session_info["bundle_params"]["lang"] = request.lang.code
        session_info.update(
            {
                "translationURL": FRONTEND_TRANSLATIONS_ROUTE,
            }
        )
        return session_info

    @api.model
    def get_translation_frontend_modules(self) -> list[str]:
        Modules = self.env["ir.module.module"].sudo()
        extra_modules_name = list(self._get_translation_frontend_modules_name())
        extra_modules_domain = Domain(self._get_domain_translation_frontend_modules())
        if not extra_modules_domain.is_true():
            new = Modules.search(
                extra_modules_domain & Domain("state", "=", "installed")
            ).mapped("name")
            extra_modules_name += new
        return extra_modules_name

    @classmethod
    def _get_domain_translation_frontend_modules(
        cls,
    ) -> list[tuple[str, str, typing.Any]]:
        return []

    @classmethod
    def _get_translation_frontend_modules_name(cls) -> list[str]:
        return ["web"]

    @api.model
    def get_nearest_lang(self, lang_code: str | None) -> str | None:
        """Return the active frontend language code nearest to ``lang_code``.

        An exact match wins outright. Otherwise, among the active frontend
        languages that share ``lang_code``'s base (e.g. ``es_MX`` and
        ``es_419`` both base to ``"es"``), the first one in
        ``res.lang._get_frontend()``'s iteration order is returned — which is
        alphabetical by language display name, not by any linguistic or
        geographic notion of "nearest". When two or more variants of the same
        base are active, which one wins this tie-break is therefore
        arbitrary but deterministic.
        """
        if not lang_code:
            return None

        frontend_langs = self.env["res.lang"]._get_frontend()
        if lang_code in frontend_langs:
            return lang_code

        base = _lang_base(lang_code)
        if not base:
            return None
        _debug.logic("nearest_lang", wanted=lang_code, base=base)
        return next((code for code in frontend_langs if _lang_base(code) == base), None)

    @classmethod
    def _match(cls, path: str) -> tuple[werkzeug.routing.Rule, dict[str, typing.Any]]:
        if hasattr(request, "is_frontend"):
            return super()._match(path)

        # See /1, match a non website endpoint
        matched = None
        try:
            rule, args = cls._match_and_flag(path)
            if not request.is_frontend:
                return rule, args
            matched = (rule, args)
        except NotFound:
            _, url_lang_str, *rest = path.split("/", 2) + ["", ""]
            path_no_lang = "/" + rest[0]
        else:
            url_lang_str = ""
            path_no_lang = path

        allow_redirect = (
            request.httprequest.method in _REDIRECTABLE_METHODS
            and getattr(request, "is_frontend_multilang", True)
        )

        if allow_redirect and "//" in path:
            new_url = re.sub(r"/{2,}", "/", path)
            _debug.logic("path_collapsed", path=path, to=new_url)
            werkzeug.exceptions.abort(
                request.redirect_query(
                    new_url, request.httprequest.args, code=301, local=True
                )
            )

        default_lang, nearest_url_lang = cls._resolve_frontend_lang(url_lang_str)
        if not nearest_url_lang:
            url_lang_str = None

        path = cls._reroute_for_lang(
            path, path_no_lang, url_lang_str, default_lang, allow_redirect
        )

        if matched is not None:
            return matched

        try:
            return cls._match_and_flag(path)
        except NotFound:
            _debug.logic("frontend_not_found", path=path)
            request.is_frontend = True
            request.is_frontend_multilang = True
            raise

    @classmethod
    def _match_and_flag(
        cls, path: str
    ) -> tuple[werkzeug.routing.Rule, dict[str, typing.Any]]:
        rule, args = super()._match(path)
        routing = rule.endpoint.routing
        request.is_frontend = routing.get("website", False)
        request.is_frontend_multilang = request.is_frontend and routing.get(
            "multilang", routing["type"] == "http"
        )
        _debug.logic(
            "route_flagged",
            path=path,
            frontend=request.is_frontend,
            multilang=request.is_frontend_multilang,
        )
        return rule, args

    @classmethod
    def _resolve_frontend_lang(cls, url_lang_str: str) -> tuple[LangData, str | None]:
        with cls._borrowed_public_env() as real_env:
            IrHttp = request.env["ir.http"]
            Lang = request.env["res.lang"]
            nearest_url_lang = IrHttp.get_nearest_lang(
                Lang._get_data(url_code=url_lang_str).code or url_lang_str
            )
            cookie_lang = IrHttp.get_nearest_lang(request.cookies.get("frontend_lang"))
            context_lang = IrHttp.get_nearest_lang(real_env.context.get("lang"))
            default_lang = IrHttp._get_default_lang()
            request.lang = Lang._get_data(
                code=(
                    nearest_url_lang or cookie_lang or context_lang or default_lang.code
                )
            )
            _debug.logic(
                "frontend_lang",
                by=(
                    "url"
                    if nearest_url_lang
                    else "cookie"
                    if cookie_lang
                    else "context"
                    if context_lang
                    else "default"
                ),
                lang=request.lang.code,
                url_code=url_lang_str or None,
            )
        return default_lang, nearest_url_lang

    @classmethod
    @contextlib.contextmanager
    def _borrowed_public_env(cls) -> typing.Iterator[api.Environment]:
        real_env = request.env
        real_default_env = real_env.transaction.default_env
        real_uid = getattr(threading.current_thread(), "uid", None)
        try:
            request.registry["ir.http"]._auth_method_public()
            yield real_env
        finally:
            request.env = real_env
            real_env.transaction.default_env = real_default_env
            threading.current_thread().uid = real_uid

    @classmethod
    def _redirect_lang(cls, target: str, code: int = 303) -> typing.NoReturn:
        _debug.logic("lang_redirect", to=target, code=code, lang=request.lang.code)
        redirect = request.redirect_query(target, request.httprequest.args, code=code)
        redirect.set_cookie("frontend_lang", request.lang.code)
        werkzeug.exceptions.abort(redirect)

    @classmethod
    def _reroute_for_lang(
        cls,
        path: str,
        path_no_lang: str,
        url_lang_str: str | None,
        default_lang: LangData,
        allow_redirect: bool,
    ) -> str:
        request_url_code = request.lang.url_code

        # See /2, no lang in url and default website
        if not url_lang_str and request.lang == default_lang:
            _logger.debug(
                "%r (lang: %r) no lang in url and default website, continue",
                path,
                request_url_code,
            )

        # See /3, missing lang in url but user-agent is a bot
        elif not url_lang_str and request.env["ir.http"].is_a_bot():
            _logger.debug(
                "%r (lang: %r) missing lang in url but user-agent is a bot, continue",
                path,
                request_url_code,
            )
            _debug.logic("reroute_for_lang", by="bot", path=path)
            request.lang = default_lang

        # See /4, no lang in url and should not redirect (e.g. POST), continue
        elif not url_lang_str and not allow_redirect:
            _debug.logic("reroute_for_lang", by="no_lang_no_redirect", path=path)
            _logger.debug(
                "%r (lang: %r) no lang in url and should not redirect (e.g. POST), continue",
                path,
                request_url_code,
            )

        # See /5, missing lang in url, /home -> /fr/home
        elif not url_lang_str:
            _logger.debug(
                "%r (lang: %r) missing lang in url, redirect", path, request_url_code
            )
            _debug.logic("reroute_for_lang", by="missing_lang", path=path)
            cls._redirect_lang(cls._lang_url_prefix(path, request_url_code))

        else:
            return cls._reroute_for_prefixed_lang(
                path, path_no_lang, url_lang_str, default_lang, allow_redirect
            )

        return path

    @classmethod
    def _reroute_for_prefixed_lang(
        cls,
        path: str,
        path_no_lang: str,
        url_lang_str: str,
        default_lang: LangData,
        allow_redirect: bool,
    ) -> str:
        request_url_code = request.lang.url_code

        # See /6, default lang in url, /en/home -> /home
        if url_lang_str == default_lang.url_code and allow_redirect:
            _logger.debug(
                "%r (lang: %r) default lang in url, redirect", path, request_url_code
            )
            _debug.logic("reroute_for_lang", by="default_lang_in_url", path=path)
            cls._redirect_lang(path_no_lang)

        # See /7, lang alias in url, /fr_FR/home -> /fr/home
        elif url_lang_str != request_url_code and allow_redirect:
            _logger.debug(
                "%r (lang: %r) lang alias in url, redirect", path, request_url_code
            )
            _debug.logic("reroute_for_lang", by="lang_alias", path=path)
            cls._redirect_lang(
                cls._lang_url_prefix(path_no_lang, request_url_code), code=301
            )

        # See /8, homepage with trailing slash, /fr_BE/ -> /fr_BE
        elif path == f"/{url_lang_str}/" and allow_redirect:
            _logger.debug(
                "%r (lang: %r) homepage with trailing slash, redirect",
                path,
                request_url_code,
            )
            _debug.logic("reroute_for_lang", by="trailing_slash", path=path)
            cls._redirect_lang(path[:-1], code=301)

        # See /9, valid lang in url
        elif url_lang_str == request_url_code or not allow_redirect:
            _logger.debug(
                "%r (lang: %r) valid lang in url, rewrite url and continue",
                path,
                request_url_code,
            )
            _debug.logic("reroute_for_lang", by="valid_lang_rerouted", path=path)
            request.reroute(path_no_lang)
            path = path_no_lang

        else:
            _logger.warning(
                "%r (lang: %r) couldn't correctly route this frontend request, url used as-is.",
                path,
                request_url_code,
            )
            _debug.logic("reroute_for_lang", by="unrouted", path=path)

        return path

    @classmethod
    def _pre_dispatch(
        cls, rule: werkzeug.routing.Rule, args: dict[str, typing.Any]
    ) -> None:
        super()._pre_dispatch(rule, args)

        if request.is_frontend:
            cls._frontend_pre_dispatch()

            for key, val in list(args.items()):
                if isinstance(val, models.BaseModel):
                    args[key] = val.with_context(request.env.context)

        if request.is_frontend_multilang:
            if request.httprequest.method in _REDIRECTABLE_METHODS:
                try:
                    built, error = rule.build(args), None
                except (ValueError, TypeError, werkzeug.routing.ValidationError) as exc:
                    built, error = None, exc
                if not built:
                    _logger.warning(
                        "Cannot rebuild a canonical URL for rule %r (%s), "
                        "serving %r without the slug redirect",
                        rule.rule,
                        error or "a converter rejected the value",
                        request.httprequest.path,
                    )
                    return
                _, path = built
                generated_path = urllib.parse.unquote(path)
                current_path = request.httprequest.path
                if generated_path != current_path:
                    if request.lang != request.env["ir.http"]._get_default_lang():
                        path = cls._lang_url_prefix(path, request.lang.url_code)
                    redirect = request.redirect_query(
                        path, request.httprequest.args, code=301
                    )
                    werkzeug.exceptions.abort(redirect)

    @classmethod
    def _frontend_pre_dispatch(cls) -> None:
        request.update_context(lang=request.lang.code)
        if request.cookies.get("frontend_lang") != request.lang.code:
            request.future_response.set_cookie("frontend_lang", request.lang.code)

    @classmethod
    def _get_exception_code_values(
        cls, exception: Exception
    ) -> tuple[int, dict[str, typing.Any]]:
        code = 500
        values = {
            "exception": exception,
            "traceback": "".join(traceback.format_exception(exception)),
        }

        if isinstance(exception, exceptions.UserError):
            code = exception.http_status
            values["error_message"] = exception.args[0]
        elif isinstance(exception, werkzeug.exceptions.HTTPException):
            code = exception.code or 500
            values["error_message"] = exception.description

        if hasattr(exception, "qweb"):
            values.update(qweb_exception=exception.qweb)
            if code == 404 and exception.qweb.path:
                code = 500

        values.update(
            status_message=werkzeug.http.HTTP_STATUS_CODES.get(code, ""),
            status_code=code,
        )

        return (code, values)

    @classmethod
    def _get_values_500_error(cls, env, values, exception):
        values["view"] = env["ir.ui.view"]
        return values

    @classmethod
    def _get_error_template(cls, code: int, values: dict[str, typing.Any]) -> str:
        return "http_routing.%s" % code

    @classmethod
    def _get_error_html(
        cls, env, code: int, values: dict[str, typing.Any]
    ) -> tuple[int, typing.Any]:
        View = env["ir.ui.view"]
        try:
            return code, View._render_template(
                cls._get_error_template(code, values), values
            )
        except MissingError:
            if not isinstance(code, int):
                raise
            return code, View._render_template(
                "http_routing.4xx" if 400 <= code < 500 else "http_routing.http_error",
                values,
            )

    @classmethod
    def _handle_error(cls, exception):
        response = super()._handle_error(exception)

        is_frontend_request = bool(getattr(request, "is_frontend", False))
        if not is_frontend_request or not isinstance(response, HTTPException):
            return response

        if not request.env.uid:
            cls._auth_method_public()
        cls._handle_debug()
        if not getattr(request, "lang", None):
            request.lang = request.env["ir.http"]._get_default_lang()
        cls._frontend_pre_dispatch()
        request.params = request.get_http_params()

        code, values = cls._get_exception_code_values(exception)

        request.env.cr.rollback()
        if code in (404, 403):
            try:
                response = cls._serve_fallback()
                if response:
                    cls._post_dispatch(response)
                    return response
            except werkzeug.exceptions.Forbidden:
                pass
        elif code >= 500:
            values = cls._get_values_500_error(request.env, values, exception)
        try:
            code, html = cls._get_error_html(request.env, code, values)
        except Exception:
            _logger.exception("Couldn't render a template for http status %s", code)
            request.env.cr.rollback()
            code, html = (
                418,
                request.env["ir.ui.view"]._render_template(
                    "http_routing.http_error", values
                ),
            )

        response = Response(html, status=code, content_type="text/html;charset=utf-8")
        cls._post_dispatch(response)
        return response

    @api.model
    def _routing_map_key(self) -> int | str | None:
        return None

    @api.model
    @tools.ormcache("self._routing_map_key()", "path", cache="routing.rewrites")
    def url_rewrite(self, path: str) -> tuple[str, typing.Any]:
        return self._url_rewrite(path, frozenset())

    def _url_rewrite(
        self, path: str, _visited: frozenset[str]
    ) -> tuple[str, typing.Any]:
        router = http.root.get_routing_map(
            self.env.registry.db_name, env=self.env
        ).bind("")
        try:
            try:
                func, _args = router.match(path, method="POST")
            except werkzeug.exceptions.MethodNotAllowed:
                func, _args = router.match(path, method="GET")
        except werkzeug.routing.RequestRedirect as e:
            new_path = urllib.parse.urlsplit(e.new_url).path
            if new_path == path or new_path in _visited:
                _logger.warning(
                    "Redirect loop while rewriting %r (targets %r again)",
                    path,
                    new_path,
                )
                return path, False
            _, func = self._url_rewrite(new_path, _visited | {path})
            return new_path or path, func
        except HTTPException:
            return path, False
        return path, func
