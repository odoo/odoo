import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class PosMercadoPagoWebhook(http.Controller):
    # csrf=False: auth="receiver" admits the caller through its inbound gate
    @http.route(
        "/pos_mercado_pago/notification",
        methods=["POST"],
        type="http",
        auth="receiver",
        receiver="pos.payment.method:_receiver_for_mercado_pago_terminal",
        receiver_event="mercado_pago_terminal",
        csrf=False,
        typed=True,
    )
    def notification(self):
        """Process the notification sent by Mercado Pago (always JSON)."""
        extra = request.admission.extra
        _logger.debug("Webhook authenticated, POST message: %s", extra["data"])
        # Notify the frontend that we received a message from Mercado Pago
        pos_session_sudo = extra["session"]
        pos_session_sudo.config_id._notify(
            "MERCADO_PAGO_LATEST_MESSAGE", {"config_id": pos_session_sudo.config_id.id}
        )
        # Acknowledge Mercado Pago message
        return http.Response("OK", status=200)
