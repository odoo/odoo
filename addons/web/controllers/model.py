from odoo.http import Controller, Response, request, route
from odoo.libs.json import dumps, loads


class Model(Controller):
    @route(
        "/web/model/get_definitions",
        methods=["POST"],
        type="http",
        auth="user",
        readonly=True,
    )
    def get_model_definitions(self, model_names: str, **kwargs) -> Response:
        return request.make_response(
            dumps(
                request.env["ir.model"]._get_definitions(loads(model_names)),
            )
        )
