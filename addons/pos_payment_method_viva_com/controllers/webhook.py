import json
import logging

from werkzeug.exceptions import NotFound

from odoo import http
from odoo.http import request
from odoo.tools import consteq

_logger = logging.getLogger(__name__)


EVENT_TYPE_PAYMENT_CREATED = 1796


class PosVivaComController(http.Controller):
    def _get_payment_method(self, token: str):
        viva_payment_methods = request.env["pos.electronic.payment"].sudo().search([
            ("payment_provider", "=", "viva_com"),
        ])
        payment_method_sudo = next(
            (pm for pm in viva_payment_methods if consteq(pm.viva_com_webhook_verification_key, token)),
            None,
        )

        if not payment_method_sudo:
            _logger.error("Received webhook with an unknown token")
            raise NotFound

        return payment_method_sudo

    @http.route("/pos_viva_com/notification", type="http", auth="public", methods=["GET"], csrf=False, save_session=False, replica=True)
    def verify_webhook(self, token: str):
        _logger.info("Webhook verification request from Viva.com")

        payment_method_sudo = self._get_payment_method(token)
        return json.dumps({"Key": payment_method_sudo.viva_com_webhook_verification_key})

    @http.route("/pos_viva_com/notification", type="http", auth="public", methods=["POST"], csrf=False, save_session=False, replica=False)
    def notification(self, token: str):
        _logger.info("Notification received from Viva.com")

        payment_method_sudo = self._get_payment_method(token)

        data = request.get_json_data()
        terminal_id = str(data.get("EventData", {}).get("TerminalId"))
        event_type = data.get("EventTypeId")
        data_webhook = data.get("EventData", {})

        if event_type != EVENT_TYPE_PAYMENT_CREATED:
            _logger.warning("Received webhook with an unknown event type '%s'. See https://developer.viva.com/webhooks-for-payments/#webhook-events.", event_type)
            return

        if terminal_id != payment_method_sudo.viva_com_terminal_id:
            _logger.error("Webhook terminal ID '%s' does not match payment method '%s'", terminal_id, payment_method_sudo.viva_com_terminal_id)
            return

        transaction_id = data_webhook.get("MerchantTrns")
        if not transaction_id:
            return

        transaction = payment_method_sudo.get_transaction_status(transaction_id)
        if transaction.get("status") not in ["paid", "failed"]:
            return

        payment_method_sudo._notify(transaction_id, transaction)
