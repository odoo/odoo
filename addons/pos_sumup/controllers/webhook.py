import json
import logging

from odoo import http
from odoo.http import request
from odoo.tools import verify_hash_signed

_logger = logging.getLogger(__name__)


class PosSumupController(http.Controller):
    @http.route(
        "/pos_sumup/notification",
        type="http",
        methods=["POST"],
        auth="public",
        csrf=False,
        save_session=False,
    )
    def notification(self, token: str):
        data = json.loads(request.httprequest.get_data(as_text=True))
        payload = data.get("payload") or {}

        payment_method_sudo = request.env["pos.payment.method"].sudo()
        try:
            decoded_token = token and verify_hash_signed(
                payment_method_sudo.env,
                "pos_sumup",
                token,
            )
        except ValueError:
            decoded_token = None
        if not decoded_token:
            _logger.warning("Received an unexpected SumUp notification: %s", data)
            return

        payment_method_sudo = payment_method_sudo.browse(
            decoded_token["payment_method_id"],
        ).exists()
        if not payment_method_sudo or payment_method_sudo.payment_provider != "sumup":
            _logger.warning(
                "Received a SumUp notification for an unknown payment method: %s",
                payload.get("client_transaction_id"),
            )
            return

        payment_method_sudo.config_ids._notify("SUMUP_LATEST_RESPONSE", payload)
