from odoo.http import Controller, Response, request, route
from odoo.libs.json import dumps, loads

from ..tools import debug_log as dbg


class Model(Controller):
    @route(
        "/web/model/get_definitions",
        methods=["POST"],
        type="http",
        auth="user",
        readonly=True,
    )
    def get_model_definitions(self, model_names: str, **kwargs) -> Response:
        names = loads(model_names)
        dbg.lifecycle.debug(
            "[definitions] get: %s models=%d ignored=%s",
            dbg.req(),
            len(names),
            dbg.keys(kwargs),
        )
        with dbg.timer(request.env, "[definitions] get %d models", len(names)):
            definitions = request.env["ir.model"]._get_definitions(names)
        dbg.performance.debug(
            "[definitions] get: %d models -> %d definitions, %d fields",
            len(names),
            len(definitions),
            sum(len(d.get("fields", ())) for d in definitions.values()),
        )
        return request.prepare_response(
            dumps(definitions),
            headers=[("Content-Type", "application/json")],
        )
