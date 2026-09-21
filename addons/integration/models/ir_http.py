import logging

from werkzeug.exceptions import NotFound

from odoo import models
from odoo.http import request

from ..tools.admission import Refused

_logger = logging.getLogger(__name__)


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    @classmethod
    def _auth_routing_keys(cls) -> dict[str, tuple[str, ...]]:
        return {**super()._auth_routing_keys(), "receiver": ("receiver",)}

    @classmethod
    def _auth_method_receiver(cls, receiver: str | None = None) -> None:
        cls._auth_method_public()
        if not receiver:
            _logger.error(
                "%s %s declares auth='receiver' without a receiver= resolver",
                request.httprequest.method,
                request.httprequest.path,
            )
            raise NotFound
        gate_model = request.env["mixin.inbound.gate"]
        subject, gate, extra = gate_model._resolve_route_receiver(
            receiver, request.path_args
        )
        if not gate:
            model_name = receiver.partition(":")[0]
            request.env["inbound.access.log"]._record_unknown_caller(
                model_name,
                ", ".join(f"{k}={str(v)[:16]}" for k, v in request.path_args.items()),
                request.httprequest.remote_addr,
                user_agent=request.httprequest.headers.get("User-Agent"),
            )
            raise Refused(404, "Endpoint not found or inactive", "endpoint_not_found")
        request.admission = gate.admit(subject=subject)
        request.admission.extra = extra
