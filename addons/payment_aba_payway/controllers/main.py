# Part of Odoo. See LICENSE file for full copyright and licensing details.

import hmac
import pprint
from datetime import datetime

from werkzeug.exceptions import Forbidden

from odoo import http
from odoo.exceptions import ValidationError
from odoo.http import request

from odoo.addons.payment.logging import get_payment_logger
from odoo.addons.payment_aba_payway import const

_logger = get_payment_logger(__name__)


class PaywayController(http.Controller):
    @http.route(const.PAYMENT_WEBHOOK_ROUTE, type="jsonrpc", auth="public", methods=["POST"])
    def payway_webhook(self):
        """Process the notification data sent by PayWay to the webhook."""
        data = request.get_json_data()
        _logger.info("Notification received from PayWay with data:\n%s", pprint.pformat(data))
        tx_sudo = request.env["payment.transaction"].sudo()._search_by_reference("aba_payway", data)
        if tx_sudo and tx_sudo.state not in {"done", "error"}:
            self._verify_signature(request.httprequest.headers.get("x-payway-hmac-sha512"), data, tx_sudo)
            try:
                payload = {
                    "req_time": datetime.now().strftime("%Y%m%d%H%M%S"),
                    "merchant_id": tx_sudo.provider_id.payway_merchant_id,
                    "tran_id": data["tran_id"],
                }
                payload.update({"hash": tx_sudo.provider_id._payway_calculate_signature(payload)})
                payment_data = tx_sudo._send_api_request(
                    "POST", "/api/payment-gateway/v1/payments/check-transaction-2", json=payload,
                )
            except ValidationError as e:
                tx_sudo._set_error(str(e))
            else:
                tx_sudo._process("aba_payway", payment_data)

    @staticmethod
    def _verify_signature(received_signature, payment_data, tx_sudo):
        """Check that the received signature matches the expected one.

        :param str received_signature: The received signature
        :param payment_data: Webhook notification data received from PayWay.
        :param recordset tx_sudo: The sudoed transaction referenced by the notification data, as a
                                  `payment.transaction` record
        :return: None
        :raise: :class:`werkzeug.exceptions.Forbidden` if the signatures don't match
        """
        if not received_signature:
            _logger.warning("Received notification with missing signature.")
            raise Forbidden()

        expected_signature = tx_sudo.provider_id._payway_calculate_signature(payment_data, sorted(payment_data.keys()))
        if expected_signature is None or not hmac.compare_digest(received_signature, expected_signature):
            _logger.warning("Received notification with invalid signature.")
            raise Forbidden()
