from odoo import http
from odoo.exceptions import ValidationError
from odoo.http import request
from odoo.tools import verify_hash_signed
import logging

_logger = logging.getLogger(__name__)


class PosMollie(http.Controller):
    @http.route('/pos_mollie/webhook', methods=['POST'], auth='public', type='http', save_session=False, csrf=False)
    def mollie_webhook(self, id, payload):
        _logger.info("Received webhook from Mollie for payment '%s'", id)

        payment_method_sudo = request.env["pos.payment.method"].sudo()
        try:
            decoded_payload = verify_hash_signed(payment_method_sudo.env, "pos_mollie", payload)
        except ValueError:
            decoded_payload = None
        if not decoded_payload:
            _logger.warning("Invalid payload received in Mollie webhook, ignoring")
            return "OK"

        payment_method_id = decoded_payload["payment_method_id"]
        pos_session_id = decoded_payload["pos_session_id"]
        payment_method_sudo = payment_method_sudo.browse(payment_method_id).exists()
        if not payment_method_sudo:
            _logger.warning("No payment method found matching Mollie webhook, ignoring")
            return "OK"

        try:
            payment = payment_method_sudo.mollie_get_payment(id, pos_session_id, decoded_payload["payment_uuid"])
        except ValidationError as e:
            _logger.warning("Mollie payment '%s' rejected: %s, ignoring", id, e)
            return "OK"
        pos_session_sudo = request.env["pos.session"].sudo().browse(pos_session_id).exists()
        pos_session_sudo.config_id._notify('MOLLIE_PAYMENT_STATUS', payment)

        return "OK"
