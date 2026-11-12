import logging
import pprint

from odoo import http
from odoo.http import request
from odoo.tools import consteq

_logger = logging.getLogger(__name__)


class PosAdyenController(http.Controller):

    @http.route("/pos_adyen/notification", type="http", methods=["POST"], auth="public", csrf=False, save_session=False, replica=True)
    def notification(self):
        data = request.httprequest.json
        if not data.get("SaleToPOIResponse"):
            return

        _logger.info("Notification received from Adyen:\n%s", pprint.pformat(data))

        response = data["SaleToPOIResponse"]
        msg_header = response.get("MessageHeader")
        if not msg_header \
            or msg_header.get("ProtocolVersion") != "3.0" \
            or msg_header.get("MessageClass") != "Service" \
            or msg_header.get("MessageType") != "Response" \
            or msg_header.get("MessageCategory") not in ["Payment", "Reversal"] \
            or not msg_header.get("POIID"):
            _logger.warning("Adyen notification header is invalid")
            return

        terminal_identifier = msg_header["POIID"]
        service_id = msg_header["ServiceID"]
        response_name = "PaymentResponse" if msg_header.get("MessageCategory") == "Payment" else "ReversalResponse"
        transaction_response = response[response_name]["Response"]

        pos_electronic_payment = request.env["pos.electronic.payment"]
        additional_response = pos_electronic_payment._parse_adyen_additional_response(transaction_response)
        if "metadata.payment_method_id" not in additional_response or "metadata.pos_hmac" not in additional_response:
            _logger.warning("Adyen notification missing required metadata")
            return

        payment_method_id = int(additional_response["metadata.payment_method_id"])
        payment_method = pos_electronic_payment.sudo().browse(payment_method_id)
        if not payment_method.exists():
            _logger.warning("Adyen notification for non-existent payment method with ID=%s", payment_method_id)
            return

        if terminal_identifier != payment_method.adyen_terminal_identifier:
            _logger.warning("Adyen notification terminal ID '%s' does not match Odoo terminal ID '%s'", terminal_identifier, payment_method.adyen_terminal_identifier)

        received_hmac = additional_response["metadata.pos_hmac"]
        calculated_hmac = payment_method._generate_adyen_hmac(service_id)

        if not consteq(received_hmac, calculated_hmac):
            _logger.warning("Adyen notification has invalid HMAC")
            return

        odoo_transaction_id = f"Payment/{service_id}" if response_name == "PaymentResponse" else f"Reversal/{service_id}"
        payment_method._notify(odoo_transaction_id, payment_method._process_adyen_transaction_result(response))
        _logger.info("Adyen notification processed successfully")
