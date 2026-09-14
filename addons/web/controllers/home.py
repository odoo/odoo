import hashlib
import logging
import os
from typing import Any

import psycopg

import odoo.api
import odoo.db
import odoo.exceptions
from odoo import http
from odoo.exceptions import AccessError
from odoo.http import Response, request
from odoo.libs.json import dumps as json_dumps
from odoo.service import security
from odoo.service.metrics import CONTENT_TYPE as METRICS_CONTENT_TYPE
from odoo.service.metrics import get_metrics_token, render_prometheus_exposition
from odoo.tools import config, str2bool
from odoo.tools.json import orjson_default
from odoo.tools.misc import consteq, hmac
from odoo.tools.translate import LazyTranslate, _

from ..tools import debug_log as dbg
from .utils import (
    _get_login_redirect_url,
    _is_local_url,
    is_user_internal,
    select_db,
)

_lt = LazyTranslate(__name__)
_logger = logging.getLogger(__name__)


SIGN_UP_REQUEST_PARAMS = {
    "db",
    "login",
    "debug",
    "token",
    "message",
    "error",
    "scope",
    "mode",
    "redirect",
    "redirect_hostname",
    "email",
    "name",
    "partner_id",
    "password",
    "confirm_password",
    "city",
    "country_id",
    "lang",
    "signup_email",
}
LOGIN_SUCCESSFUL_PARAMS = set()
CREDENTIAL_PARAMS = ["login", "password", "type"]


def _is_db_server_reachable(probe: str) -> bool:
    try:
        with (
            dbg.timer(None, "[%s] postgres probe", probe),
            odoo.db.db_connect("postgres").cursor(),
        ):
            return True
    except psycopg.Error as exc:
        dbg.logic.debug("[%s] postgres probe failed (%s)", probe, type(exc).__name__)
        return False


class Home(http.Controller):
    @http.route("/", type="http", auth="none")
    def index(
        self, s_action: str | None = None, db: str | None = None, **kw: Any
    ) -> Response:
        dbg.lifecycle.debug("[index] %s", dbg.req())
        if (
            request.db
            and request.session.uid
            and not is_user_internal(request.session.uid)
        ):
            dbg.logic.debug("[index] external user -> /web/login_successful")
            return request.redirect_query("/web/login_successful", query=request.params)
        return request.redirect_query("/odoo", query=request.params)

    def _web_client_readonly(self, rule: Any, args: Any) -> bool:
        return False

    @http.route(
        ["/web", "/odoo", "/odoo/<path:subpath>", "/scoped_app/<path:subpath>"],
        type="http",
        auth="none",
        readonly=_web_client_readonly,
    )
    def web_client(self, s_action: str | None = None, **kw: Any) -> Response:
        dbg.lifecycle.debug("[webclient] %s kw=%s", dbg.req(), dbg.keys(kw))
        select_db()
        if not request.session.uid:
            dbg.pipeline.debug("[webclient] anonymous -> 303 /web/login")
            return request.redirect_query(
                "/web/login",
                query={"redirect": request.httprequest.full_path},
                code=303,
            )
        if kw.get("redirect") and _is_local_url(kw["redirect"]):
            dbg.pipeline.debug("[webclient] local redirect param -> %r", kw["redirect"])
            return request.redirect(kw["redirect"], 303)
        if not security.is_session_valid(request.session, request.env, request):
            dbg.logic.debug("[webclient] session token invalid -> expired")
            msg = "Session expired"
            raise http.SessionExpiredException(msg)
        if not is_user_internal(request.session.uid):
            dbg.pipeline.debug(
                "[webclient] external uid=%s -> 303", request.session.uid
            )
            return request.redirect("/web/login_successful", 303)

        request.update_env(user=request.session.uid)
        try:
            if request.env.user:
                with dbg.timer(request.env, "[webclient] on_webclient_bootstrap"):
                    request.env.user._on_webclient_bootstrap()
            with dbg.timer(request.env, "[webclient] rendering_context"):
                context = request.env["ir.http"].webclient_rendering_context()

            hmac_payload = request.env.user._get_session_token_values()
            session_info = context.get("session_info")
            session_info["browser_cache_secret"] = hmac(
                request.env(su=True), "browser_cache_key", hmac_payload
            )
            dbg.pipeline.debug(
                "[webclient] uid=%s context=%s session_info=%s -> render",
                request.session.uid,
                dbg.keys(context),
                dbg.count(session_info),
            )

            with dbg.timer(request.env, "[webclient] render bootstrap"):
                response = request.render("web.webclient_bootstrap", qcontext=context)
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["Cache-Control"] = "no-store"
            response.set_cookie(
                "content_density", request.env["ir.http"].content_density()
            )
            response.set_cookie("color_scheme", request.env["ir.http"].color_scheme())
            return response
        except AccessError:
            dbg.logic.debug("[webclient] AccessError during bootstrap -> login")
            return request.redirect("/web/login?error=access")

    @http.route(
        "/web/webclient/load_menus",
        type="http",
        auth="user",
        methods=["GET"],
        readonly=True,
    )
    def web_load_menus(
        self, lang: str | None = None, hash: str | None = None
    ) -> Response:
        dbg.lifecycle.debug(
            "[menus] load: %s lang=%s client_hash=%s debug=%r",
            dbg.req(),
            lang,
            (hash or "")[:12] or None,
            request.session.debug,
        )
        if lang:
            request.update_context(lang=lang)

        with dbg.timer(request.env, "[menus] load_web_menus"):
            menus = request.env["ir.ui.menu"].load_web_menus(request.session.debug)
        with dbg.timer(None, "[menus] dumps + sha256"):
            body = json_dumps(menus, default=orjson_default)
            current_hash = hashlib.sha256(body.encode()).hexdigest()
        headers = [
            ("Cache-Control", "no-store"),
            ("X-Menus-Hash", current_hash),
        ]
        if hash and hash == current_hash:
            dbg.logic.debug("[menus] load: hash match -> 304 (body still built)")
            return request.prepare_response("", headers, status=304)
        dbg.performance.debug(
            "[menus] load: %d menus, %d bytes, hash %s",
            len(menus),
            len(body),
            current_hash[:12],
        )
        headers.append(("Content-Type", "application/json; charset=utf-8"))
        return request.prepare_response(body, headers)

    def _login_redirect(self, uid: int, redirect: str | None = None) -> str:
        return _get_login_redirect_url(uid, redirect)

    @http.route(
        "/web/login",
        type="http",
        auth="none",
        readonly=False,
        list_as_website_content=_lt("Login"),
    )
    def web_login(self, redirect: str | None = None, **kw: Any) -> Response:
        dbg.lifecycle.debug(
            "[login] %s redirect=%r params=%s",
            dbg.req(),
            redirect,
            dbg.keys(request.params),
        )
        select_db()
        request.params["login_success"] = False
        if request.httprequest.method == "GET" and redirect and request.session.uid:
            if not _is_local_url(redirect):
                dbg.logic.debug("[login] non-local redirect %r -> /odoo", redirect)
                redirect = "/odoo"
            dbg.pipeline.debug(
                "[login] already authenticated uid=%s -> %r",
                request.session.uid,
                redirect,
            )
            return request.redirect(redirect)

        if request.env.uid is None:
            if request.session.uid is None:
                dbg.logic.debug("[login] env unbound, session anonymous -> public")
                request.env["ir.http"]._auth_method_public()
            else:
                dbg.logic.debug(
                    "[login] env unbound, session uid=%s -> bind", request.session.uid
                )
                request.update_env(user=request.session.uid)

        values = {
            k: v for k, v in request.params.items() if k in SIGN_UP_REQUEST_PARAMS
        }
        try:
            values["databases"] = http.get_dbs_served()
        except odoo.exceptions.AccessDenied:
            dbg.logic.debug("[login] db list denied (list_db off)")
            values["databases"] = None

        if request.httprequest.method == "POST":
            try:
                credential = {
                    key: value
                    for key, value in request.params.items()
                    if key in CREDENTIAL_PARAMS and value
                }
                credential.setdefault("type", "password")
                dbg.pipeline.debug(
                    "[login] POST login=%r type=%s has_password=%s",
                    credential.get("login"),
                    credential["type"],
                    bool(credential.get("password")),
                )
                if request.env["res.users"]._is_captcha_login_required(credential):
                    dbg.logic.debug("[login] captcha required for this credential")
                    request.env["ir.http"]._check_request_recaptcha_token("login")
                with dbg.timer(request.env, "[login] authenticate"):
                    auth_info = request.session.authenticate(request.env, credential)
                request.params["login_success"] = True
                dbg.pipeline.debug(
                    "[login] success uid=%s session_uid=%s -> redirect",
                    auth_info["uid"],
                    request.session.uid,
                )
                return request.redirect(
                    self._login_redirect(auth_info["uid"], redirect=redirect)
                )
            except odoo.exceptions.AccessDenied as e:
                if e.args == odoo.exceptions.AccessDenied().args:
                    dbg.logic.debug("[login] denied: wrong login/password")
                    values["error"] = _("Wrong login/password")
                else:
                    dbg.logic.debug("[login] denied with reason: %s", e.args[0])
                    values["error"] = e.args[0]
        elif "error" in request.params and request.params.get("error") == "access":
            dbg.logic.debug("[login] GET with error=access (non-employee)")
            values["error"] = _(
                "Only employees can access this database. Please contact the administrator."
            )

        if "login" not in values and request.session.get("auth_login"):
            dbg.logic.debug("[login] prefill login from session auth_login")
            values["login"] = request.session.get("auth_login")

        if not odoo.tools.config["list_db"]:
            values["disable_database_manager"] = True

        with dbg.timer(request.env, "[login] render"):
            response = request.render("web.login", values)
        response.headers["Cache-Control"] = "no-cache"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["Content-Security-Policy"] = "frame-ancestors 'self'"
        return response

    @http.route(
        "/web/login_successful",
        type="http",
        auth="user",
        website=True,
        sitemap=False,
    )
    def login_successful_external_user(self, **kwargs: Any) -> Response:
        valid_values = {k: v for k, v in kwargs.items() if k in LOGIN_SUCCESSFUL_PARAMS}
        dbg.lifecycle.debug(
            "[login_successful] %s kept=%s of %d",
            dbg.req(),
            dbg.keys(valid_values),
            len(kwargs),
        )
        return request.render("web.login_successful", valid_values)

    @http.route("/web/become", type="http", auth="user", sitemap=False, readonly=False)
    def switch_to_admin(self) -> Response:
        uid = request.env.user.id
        dbg.lifecycle.debug("[become] %s uid=%s", dbg.req(), uid)
        if request.env.user._is_system():
            uid = request.session.uid = odoo.SUPERUSER_ID
            request.env.registry.clear_cache()
            request.session.session_token = security.get_session_token(
                request.session, request.env
            )
            dbg.pipeline.debug(
                "[become] system user -> superuser, registry cache cleared, token rotated"
            )
        else:
            dbg.logic.debug("[become] uid=%s is not system, no switch", uid)

        return request.redirect(self._login_redirect(uid))

    @http.route("/web/health", type="http", auth="none", save_session=False)
    def health(self, db_server_status: bool | str = False) -> Response:
        health_info = {"status": "pass"}
        status = 200
        if str2bool(db_server_status, False):
            reachable = _is_db_server_reachable("health")
            health_info["db_server_status"] = reachable
            if not reachable:
                health_info["status"] = "fail"
                status = 500
        dbg.lifecycle.debug("[health] %s -> %d %s", dbg.req(), status, health_info)
        return self._get_health_response(health_info, status)

    @http.route("/web/healthz", type="http", auth="none", save_session=False)
    def healthz(self) -> Response:
        dbg.lifecycle.debug("[healthz] %s", dbg.req())
        return self._get_health_response({"status": "pass"}, 200)

    @http.route("/web/readyz", type="http", auth="none", save_session=False)
    def readyz(self) -> Response:
        checks: dict[str, str] = {}
        status = 200
        if _is_db_server_reachable("readyz"):
            checks["db"] = "pass"
        else:
            checks["db"] = "fail"
            status = 503
        if os.access(config["data_dir"], os.W_OK):
            checks["data_dir"] = "pass"
        else:
            dbg.logic.debug("[readyz] data_dir %s not writable", config["data_dir"])
            checks["data_dir"] = "fail"
            status = 503
        dbg.lifecycle.debug("[readyz] %s -> %d %s", dbg.req(), status, checks)
        return self._get_health_response(
            {"status": "pass" if status == 200 else "fail", "checks": checks},
            status,
        )

    @http.route("/web/metrics", type="http", auth="none", save_session=False)
    def metrics(self) -> Response:
        token = get_metrics_token()
        dbg.lifecycle.debug("[metrics] %s token_configured=%s", dbg.req(), bool(token))
        if not token:
            raise request.prepare_not_found_error()
        presented = request.httprequest.headers.get("Authorization", "")
        scheme, _, offered = presented.partition(" ")
        if scheme.lower() != "bearer" or not consteq(offered.strip(), token):
            dbg.logic.debug(
                "[metrics] rejected: scheme=%r token_presented=%s",
                scheme,
                bool(offered),
            )
            _logger.warning(
                "Rejected /web/metrics scrape from %s: bad or missing bearer token",
                request.httprequest.remote_addr,
            )
            return request.prepare_response(
                "", [("Cache-Control", "no-store")], status=401
            )
        with dbg.timer(None, "[metrics] render exposition"):
            exposition = render_prometheus_exposition()
        dbg.performance.debug("[metrics] exposition %d bytes", len(exposition))
        return request.prepare_response(
            exposition,
            [("Content-Type", METRICS_CONTENT_TYPE), ("Cache-Control", "no-store")],
            status=200,
        )

    def _get_health_response(self, payload: dict[str, Any], status: int) -> Response:
        return request.prepare_response(
            json_dumps(payload),
            [
                ("Content-Type", "application/json"),
                ("Cache-Control", "no-store"),
            ],
            status=status,
        )

    @http.route(["/robots.txt"], type="http", auth="none")
    def robots(self, **kwargs: Any) -> Response:
        allowed_routes = self._get_allowed_robots_routes()
        dbg.lifecycle.debug("[robots] %s allowed=%d", dbg.req(), len(allowed_routes))
        robots_content = ["User-agent: *", "Disallow: /"]
        robots_content.extend(f"Allow: {route}" for route in allowed_routes)

        return request.prepare_response(
            "\n".join(robots_content), [("Content-Type", "text/plain")]
        )

    def _get_allowed_robots_routes(self) -> list[str]:
        return []
