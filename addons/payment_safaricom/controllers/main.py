# Part of Odoo. See LICENSE file for full copyright and licensing details.
import pprint

from werkzeug.exceptions import Forbidden

from odoo import http
from odoo.exceptions import ValidationError
from odoo.http import request
from odoo.tools import verify_hash_signed

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.logging import get_payment_logger
from odoo.addons.payment_safaricom import const

_logger = get_payment_logger(__name__, const.SENSITIVE_KEYS)


class SafaricomController(http.Controller):
    @http.route(const.PAYMENT_URL, type="jsonrpc", auth="public")
    def safaricom_stk_push(self, reference, phone, access_token, **_kwargs):
        """Catch the form submission, call the STK Push API, and redirect to the status page."""
        tx_sudo = (
            self.env["payment.transaction"].sudo().search([("reference", "=", reference)], limit=1)
        )
        if not tx_sudo or tx_sudo.provider_code != "safaricom":
            raise Forbidden(self.env._("Invalid Transaction Reference"))
        if not payment_utils.check_access_token(access_token, reference):
            raise ValidationError(
                self.env._("The access token doesn't match the transaction reference.")
            )
        if tx_sudo.state != "draft":
            raise ValidationError(self.env._("The transaction has already been processed."))

        tx_sudo._safaricom_send_stk_push(phone)
        return {}

    @http.route(const.WEBHOOK_URL, type="http", auth="public", methods=["POST"], csrf=False)
    def safaricom_webhook(self, reference, **_kwargs):
        """Receive the STK Push callback from Safaricom."""
        try:
            data = request.get_json_data()
            _logger.info("Notification received from Safaricom M-PESA:\n%s", pprint.pformat(data))

            try:
                verified = verify_hash_signed(self.env(su=True), "payment_safaricom", reference)
            except ValueError:  # Malformed token; also covers binascii.Error & UnicodeDecodeError
                verified = None
            if not verified:
                _logger.warning("Invalid reference received from Safaricom.")
                raise Forbidden

            data["reference"] = verified["reference"]
            tx_sudo = self.env["payment.transaction"].sudo()._search_by_reference("safaricom", data)
            if tx_sudo:
                tx_sudo._record(data)

            # Daraja API requires a successful HTTP response to acknowledge receipt
            return request.make_json_response({"ResultCode": "0", "ResultDesc": "Accepted"})
        except ValidationError as e:
            _logger.error("Error processing Safaricom webhook: %s", e)
            return request.make_json_response({"ResultCode": "1", "ResultDesc": "Error"})
