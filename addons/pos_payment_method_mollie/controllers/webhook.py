import logging

from odoo import http
from odoo.http import request
from odoo.tools import verify_hash_signed

_logger = logging.getLogger(__name__)


class PosMollieController(http.Controller):
    @http.route('/pos_mollie/webhook', methods=['POST'], auth='public', type='http', save_session=False, csrf=False, replica=True)
    def mollie_webhook(self, id, payload):
        _logger.info("Received webhook from Mollie for payment '%s'", id)

        payment_method_sudo = request.env["pos.electronic.payment"].sudo()
        try:
            decoded_payload = verify_hash_signed(payment_method_sudo.env, "pos_mollie", payload)
        except ValueError:
            decoded_payload = None
        if not decoded_payload:
            _logger.warning("Invalid payload received in Mollie webhook, ignoring")
            return "OK"

        payment_method_id = decoded_payload["payment_method_id"]
        payment_method_sudo = payment_method_sudo.browse(payment_method_id).exists()
        if not payment_method_sudo:
            _logger.warning("No payment method found matching Mollie webhook, ignoring")
            return "OK"

        transaction = payment_method_sudo.get_transaction_status(id)
        if "transaction_id" in transaction:
            payment_method_sudo._notify(id, transaction)

        return "OK"
