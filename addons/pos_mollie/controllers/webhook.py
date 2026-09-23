import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class PosMollie(http.Controller):
    # csrf=False: auth="receiver" admits the caller through its inbound gate
    @http.route(
        "/pos_mollie/webhook",
        methods=["POST"],
        auth="receiver",
        receiver="pos.payment.method:_receiver_for_mollie_terminal",
        receiver_event="mollie_terminal",
        type="http",
        save_session=False,
        csrf=False,
        typed=True,
    )
    def mollie_webhook(self, id: str, payload: str):
        _logger.info("Received webhook from Mollie for payment '%s'", id)
        payment_method_sudo = request.admission.subject
        pos_session_id = request.admission.extra["payload"]["pos_session_id"]
        pos_session_sudo = (
            request.env["pos.session"].sudo().browse(pos_session_id).exists()
        )
        if not pos_session_sudo:
            _logger.warning("No POS session found matching Mollie webhook, ignoring")
            return "OK"

        payment_info = payment_method_sudo._mollie_get_payment(id)
        payment_details = payment_info["details"]

        message = {
            "session_id": int(pos_session_id),
            "payment_id": id,
            "status": payment_info["status"],
        }
        if message["status"] == "paid":
            message |= {
                "card_type": payment_details.get("cardFunding"),
                "card_no": payment_details.get("cardNumber"),
                "card_brand": payment_details.get("cardLabel"),
            }
        elif message["status"] in ["expired", "failed", "canceled"]:
            message |= {
                "status_reason": payment_info.get("statusReason"),
            }
        pos_session_sudo.config_id._notify("MOLLIE_PAYMENT_STATUS", message)

        return "OK"
