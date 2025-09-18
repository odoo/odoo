import logging
from contextlib import ExitStack
from typing import Any
from urllib.parse import urlencode

import odoo
import odoo.modules.registry
from odoo import http
from odoo.exceptions import AccessError
from odoo.http import Response, request
from odoo.libs.json import dumps as json_dumps
from odoo.tools.translate import _

from .utils import _is_local_url

_logger = logging.getLogger(__name__)


class Session(http.Controller):
    @http.route(
        "/web/session/get_session_info",
        type="jsonrpc",
        auth="user",
        readonly=True,
    )
    def get_session_info(self) -> dict[str, Any]:
        # Crappy workaround for unupdatable Odoo Mobile App iOS (Thanks Apple :@)
        request.session.touch()
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
        if not http.db_filter([db]):
            msg = "Database not found."  # pylint: disable=missing-gettext
            raise AccessError(msg)

        with ExitStack() as stack:
            if not request.db or request.db != db:
                # Use a new env only when no db on the request, which means the env was not set on in through `_serve_db`
                # or the db is different than the request db
                cr = stack.enter_context(odoo.modules.registry.Registry(db).cursor())
                env = odoo.api.Environment(cr, None, {})
            else:
                env = request.env

            credential = {
                "login": login,
                "password": password,
                "type": "password",
            }
            auth_info = request.session.authenticate(env, credential)
            if auth_info["uid"] != request.session.uid:
                # Crappy workaround for unupdatable Odoo Mobile App iOS (Thanks Apple :@) and Android
                # Correct behavior should be to raise AccessError("Renewing an expired session for user that has multi-factor-authentication is not supported. Please use /web/login instead.")
                return {"uid": None}

            request.session.db = db
            request._save_session(env)

            return env["ir.http"].with_user(request.session.uid).session_info()

    @http.route("/web/session/get_lang_list", type="jsonrpc", auth="none")
    def get_lang_list(self) -> list[list[str]] | dict[str, str]:
        try:
            return http.dispatch_rpc("db", "list_lang", []) or []
        except Exception as e:
            _logger.exception("Failed to fetch language list")
            return {"error": str(e), "title": _("Languages")}

    @http.route("/web/session/modules", type="jsonrpc", auth="user", readonly=True)
    def modules(self) -> list[str]:
        # return all installed modules. Web client is smart enough to not load a module twice
        return list(request.env.registry._init_modules)

    @http.route("/web/session/check", type="jsonrpc", auth="user", readonly=True)
    def check(self) -> None:
        return  # ir.http@_authenticate does the job

    @http.route("/web/session/account", type="jsonrpc", auth="user", readonly=True)
    def account(self) -> str:
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
        request.session.logout()

    @http.route("/web/session/logout", type="http", auth="none", readonly=True)
    def logout(self, redirect: str = "/odoo") -> Response:
        request.session.logout(keep_db=True)
        if not _is_local_url(redirect):
            redirect = "/odoo"
        return request.redirect(redirect, 303)
