# Part of Odoo. See LICENSE file for full copyright and licensing details.

import hashlib
import hmac
import pprint

from odoo import _, http
from odoo.exceptions import ValidationError
from odoo.http import request

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.logging import get_payment_logger
from odoo.addons.payment_authorize import const

_logger = get_payment_logger(__name__)


class AuthorizeController(http.Controller):
    @http.route(const.PAYMENT_REQUEST_ROUTE, type="jsonrpc", auth="public")
    def authorize_payment(self, reference, partner_id, access_token, opaque_data):
        """Make a payment request and handle the response.

        :param str reference: The reference of the transaction
        :param int partner_id: The partner making the transaction, as a `res.partner` id
        :param str access_token: The access token used to verify the provided values
        :param dict opaque_data: The payment details obfuscated by Authorize.Net
        :return: None
        """
        # Check that the transaction details have not been altered
        if not payment_utils.check_access_token(access_token, reference, partner_id):
            raise ValidationError(_("Received tampered payment request data."))

        # Retrieve the transaction
        tx_sudo = request.env["payment.transaction"].sudo().search([("reference", "=", reference)])
        if not tx_sudo:
            raise ValidationError(_("Transaction not found."))

        # Lock the transaction row to prevent concurrent updates (e.g., from cron jobs)
        # This prevents sql concurrent updates, which stops ORM from automatically
        # retrying the route and consuming the single-use OTS token a second time.
        tx_sudo.env.cr.execute(
            "SELECT 1 FROM payment_transaction WHERE id = %s FOR NO KEY UPDATE", [tx_sudo.id]
        )

        # Send the payment request to Authorize.Net.
        response_content = tx_sudo._authorize_create_transaction_request(opaque_data)

        # Handle the payment request response
        _logger.info(
            "Payment request response for transaction %s:\n%s",
            reference,
            pprint.pformat(response_content),
        )
        tx_sudo._process("authorize", {"response": response_content})

    @http.route(const.WEBHOOK_ROUTE, type="http", auth="public", methods=["POST"], csrf=False)
    def authorize_webhook(self):
        """Process the payment data sent by Authorize.net to the webhook.

        See https://developer.authorize.net/api/reference/features/webhooks.html

        :return: An empty string to acknowledge the notification.
        :rtype: str
        """
        data = request.get_json_data()
        _logger.info(
            "Notification received from Authorize.net with data:\n%s", pprint.pformat(data)
        )
        event_type = data.get("eventType")
        if event_type in const.HANDLED_WEBHOOK_EVENTS:
            tx_sudo = (
                request.env["payment.transaction"].sudo()._search_by_reference("authorize", data)
            )
            if tx_sudo and data.get("webhookId") == tx_sudo.provider_id.authorize_webhook_id:
                # Check the integrity of the notification
                signature_header = request.httprequest.headers.get("X-ANET-Signature")
                received_signature = signature_header and signature_header.split("=", 1)[1].upper()
                signature_key = tx_sudo.provider_id.authorize_signature_key
                request_body = request.httprequest.get_data()
                expected_signature = (
                    hmac
                    .new(signature_key.encode(), request_body, hashlib.sha512)
                    .hexdigest()
                    .upper()
                )
                payment_utils.verify_signature(received_signature, expected_signature)

                # Process the payment data. The data are structured in the same format as the
                # transaction API's responses.
                payload = data.get("payload", {})
                payment_data = {
                    "response": {
                        "x_response_code": str(payload.get("responseCode")),
                        "x_trans_id": payload.get("id"),
                        "x_type": const.WEBHOOK_EVENT_TYPE_MAPPING[event_type],
                    }
                }
                tx_sudo._process("authorize", payment_data)
        return request.make_json_response("")
