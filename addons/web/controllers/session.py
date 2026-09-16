from contextlib import ExitStack
from typing import Any
from urllib.parse import urlencode

import odoo
import odoo.modules.registry
from odoo import http
from odoo.exceptions import AccessError
from odoo.http import Response, request
from odoo.libs.json import dumps as json_dumps

from ..tools import debug_log as dbg
from .utils import _is_local_url


class Session(http.Controller):
    @http.route(
        "/web/session/get_session_info",
        type="jsonrpc",
        auth="user",
        readonly=True,
    )
    def get_session_info(self) -> dict[str, Any]:
        dbg.lifecycle.debug("[session] get_session_info: %s (marks dirty)", dbg.req())
        request.session.mark_dirty()
        with dbg.timer(request.env, "[session] session_info"):
            return request.env["ir.http"].session_info()

    @http.route(
        "/web/session/authenticate", type="jsonrpc", auth="none", readonly=False
    )
    def authenticate(
        self,
        db: str,
        login: str,
        password: str,
        base_location: str | None = None,
    ) -> dict[str, Any]:
        dbg.lifecycle.debug(
            "[session] authenticate: %s db=%s login=%s has_password=%s",
            dbg.req(),
            db,
            login,
            bool(password),
        )
        if not request.app.filter_dbs_served([db]):
            dbg.logic.debug("[session] authenticate: db %s not served", db)
            msg = "Database not found."  # pylint: disable=missing-gettext
            raise AccessError(msg)

        with ExitStack() as stack:
            if request.db != db:
                dbg.logic.debug(
                    "[session] authenticate: request db %s != %s, own cursor",
                    request.db,
                    db,
                )
                cr = stack.enter_context(odoo.modules.registry.Registry(db).cursor())
                env = odoo.api.Environment(cr, None, {})
            else:
                env = request.env

            credential = {
                "login": login,
                "password": password,
                "type": "password",
            }
            with dbg.timer(env, "[session] authenticate %s", login):
                auth_info = request.session.authenticate(env, credential)
            if auth_info["uid"] != request.session.uid:
                dbg.logic.debug(
                    "[session] authenticate: uid %s != session uid %s (mfa pending?)",
                    auth_info["uid"],
                    request.session.uid,
                )
                return {"uid": None}

            request.session.db = db
            request._save_session(env)
            dbg.pipeline.debug(
                "[session] authenticate: uid=%s db=%s -> session_info",
                request.session.uid,
                db,
            )

            with dbg.timer(env, "[session] session_info uid=%s", request.session.uid):
                return env["ir.http"].with_user(request.session.uid).session_info()

    @http.route("/web/session/modules", type="jsonrpc", auth="user", readonly=True)
    def modules(self) -> list[str]:
        loaded = list(request.env.registry.loaded_modules)
        dbg.lifecycle.debug("[session] modules: %s -> %d", dbg.req(), len(loaded))
        return loaded

    @http.route("/web/session/check", type="jsonrpc", auth="user", readonly=True)
    def check(self) -> None:
        dbg.lifecycle.debug("[session] check: %s", dbg.req())

    @http.route("/web/session/account", type="jsonrpc", auth="user", readonly=True)
    def account(self) -> str:
        dbg.lifecycle.debug("[session] account: %s", dbg.req())
        ICP = request.env["ir.config_parameter"].sudo()
        params = {
            "response_type": "token",
            "client_id": ICP.get_param("database.uuid") or "",
            "state": json_dumps({"d": request.db, "u": ICP.get_param("web.base.url")}),
            "scope": "userinfo",
        }
        return "https://accounts.odoo.com/oauth2/auth?" + urlencode(params)

    @http.route("/web/session/destroy", type="jsonrpc", auth="user", readonly=True)
    def destroy(self) -> None:
        dbg.lifecycle.debug("[session] destroy: %s", dbg.req())
        request.session.logout()

    @http.route("/web/session/logout", type="http", auth="none", readonly=True)
    def logout(self, redirect: str = "/odoo") -> Response:
        dbg.lifecycle.debug("[session] logout: %s redirect=%r", dbg.req(), redirect)
        request.session.logout(keep_db=True)
        if not _is_local_url(redirect):
            dbg.logic.debug(
                "[session] logout: non-local redirect %r -> /odoo", redirect
            )
            redirect = "/odoo"
        return request.redirect(redirect, 303)
