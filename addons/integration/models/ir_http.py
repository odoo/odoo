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
        return {
            **super()._auth_routing_keys(),
            "receiver": ("receiver", "receiver_event", "receiver_refusal"),
        }

    @classmethod
    def _auth_method_receiver(
        cls,
        receiver: str | None = None,
        receiver_event: str | None = None,
        receiver_refusal: str | None = None,
    ) -> None:
        cls._auth_method_public()
        if receiver_refusal:
            model_name, _, method = receiver_refusal.partition(":")
            request.receiver_refusal = getattr(request.env[model_name], method)
        if not receiver:
            _logger.error(
                "%s %s declares auth='receiver' without a receiver= resolver",
                request.httprequest.method,
                request.httprequest.path,
            )
            raise NotFound
        gate_model = request.env["mixin.inbound.gate"]
        resolution = gate_model._resolve_route_receiver(
            receiver, request.path_args, event_type=receiver_event
        )
        subject, gate, extra = resolution.subject, resolution.gate, resolution.extra
        if not gate:
            model_name = receiver.partition(":")[0]
            request.env["inbound.access.log"]._record_unknown_caller(
                model_name,
                resolution.claimed
                or ", ".join(
                    f"{k}={str(v)[:16]}" for k, v in request.path_args.items()
                ),
                request.httprequest.remote_addr,
                user_agent=request.httprequest.headers.get("User-Agent"),
                status_code=404,
            )
            # Committed, so the row above is kept: nothing else ran.
            raise Refused(
                404, "Endpoint not found or inactive", "endpoint_not_found", commit=True
            )
        request.admission = gate.admit(
            subject=subject, event_type=receiver_event, verify=resolution.verify
        )
        request.admission.extra = extra
