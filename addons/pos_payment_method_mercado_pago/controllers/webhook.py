import hashlib
import hmac
import logging
import re

from werkzeug.exceptions import BadRequest

from odoo import http
from odoo.http import request
from odoo.tools import consteq

_logger = logging.getLogger(__name__)


class PosMercadoPagoController(http.Controller):
    @http.route("/pos_mercado_pago/notification", methods=["POST"], auth="public", type="http", save_session=False, csrf=False, replica=True)
    def notification(self, **kwargs):
        """ Process the notification sent by Mercado Pago

        Notification format is always json
        """
        # Check for mandatory keys in header
        x_request_id = request.httprequest.headers.get("X-Request-Id")
        if not x_request_id:
            _logger.warning("POST message received with no X-Request-Id in header")
            raise BadRequest()

        x_signature = request.httprequest.headers.get("X-Signature")
        if not x_signature:
            _logger.warning("POST message received with no X-Signature in header")
            raise BadRequest()

        ts_m = re.search(r"ts=(\d+)", x_signature)
        v1_m = re.search(r"v1=([a-f0-9]+)", x_signature)
        ts = ts_m.group(1) if ts_m else None
        v1 = v1_m.group(1) if v1_m else None
        if not ts or not v1:
            _logger.warning("Webhook bad X-Signature, ts: %s, v1: %s", ts, v1)
            raise BadRequest()

        # Check for payload
        data = request.httprequest.get_json(silent=True)
        if not data or data.get("type") != "order":
            _logger.warning("POST message received with incorrect data")
            return "OK"

        external_reference = data.get("data", {}).get("external_reference")
        if not external_reference:
            _logger.warning("POST message received with no 'external_reference' key")
            return "OK"

        try:
            payment_method_id, _ = external_reference.split("_")
            payment_method_id = int(payment_method_id)
        except ValueError:
            _logger.warning("External reference is not in the correct format: %s", external_reference)
            return "OK"

        payment_method_sudo = request.env["pos.electronic.payment"].sudo().browse(int(payment_method_id))
        if not payment_method_sudo or payment_method_sudo.payment_provider != "mercado_pago":
            _logger.error("Payment method with ID %s not found or wrong provider", payment_method_id)
            return "OK"

        # We have to check if this comes from Mercado Pago with the secret key.
        # MP builds the signature from the `data.id` query param lowercased even
        # though it is sent uppercase.
        secret_key = payment_method_sudo.mp_webhook_secret_key
        data_id = kwargs.get("data.id", "")
        signed_template = f"id:{data_id.lower()};request-id:{x_request_id};ts:{ts};"
        cyphed_signature = hmac.new(secret_key.encode(), signed_template.encode(), hashlib.sha256).hexdigest()
        if not consteq(cyphed_signature, v1):
            _logger.error("Webhook authenticating failure, ts: %s, v1: %s", ts, v1)
            return "OK"

        _logger.debug("Webhook authenticated, POST message: %s", data)

        order_status = payment_method_sudo.get_transaction_status(data_id)
        payment_method_sudo._notify(data_id, order_status)

        return "OK"
