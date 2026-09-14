import odoo.release
from odoo import http
from odoo.http import Forbidden, request
from odoo.http.openapi import prepare_openapi_from_map

from ..tools import debug_log as dbg


class OpenAPI(http.Controller):
    @http.route(
        "/web/openapi.json", type="http", auth="user", methods=["GET"], readonly=True
    )
    def openapi_json(self):
        dbg.lifecycle.debug("[openapi] document: %s", dbg.req())
        if not request.env.user.has_group("base.group_system"):
            dbg.logic.debug("[openapi] document: not system, refused")
            raise Forbidden("Only system administrators may read the API document.")
        with dbg.timer(request.env, "[openapi] routing_map + document"):
            document = prepare_openapi_from_map(
                request.env["ir.http"].routing_map(),
                title="Odoo HTTP API",
                version=odoo.release.major_version,
                servers=[{"url": request.httprequest.url_root.rstrip("/")}],
                typed_only=True,
            )
        dbg.performance.debug(
            "[openapi] document: %d paths, %d schemas",
            len(document.get("paths", ())),
            len(document.get("components", {}).get("schemas", ())),
        )
        return request.prepare_json_response(document)
