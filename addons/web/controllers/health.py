import logging
import os
from typing import Any

import psycopg

import odoo.db
from odoo import http
from odoo.http import Response, request
from odoo.libs.json import dumps as json_dumps
from odoo.service import server as service_server
from odoo.service.metrics import CONTENT_TYPE as METRICS_CONTENT_TYPE
from odoo.service.metrics import get_metrics_token, render_prometheus_exposition
from odoo.tools import config, str2bool
from odoo.tools.misc import consteq

from ..tools import debug_log as dbg

_logger = logging.getLogger(__name__)


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


class Health(http.Controller):
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
        # A request for a database still being preloaded waits on the
        # registry lock until the load ends; a balancer should not send one.
        if service_server.is_ready():
            checks["registries"] = "pass"
        else:
            dbg.logic.debug("[readyz] a registry preload is in progress")
            checks["registries"] = "loading"
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
