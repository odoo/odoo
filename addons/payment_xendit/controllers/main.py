# Part of Odoo. See LICENSE file for full copyright and licensing details.

import pprint

from odoo import http
from odoo.http import request
from odoo.tools import str2bool

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.logging import get_payment_logger

_logger = get_payment_logger(__name__)


class XenditController(http.Controller):
    _webhook_url = "/payment/xendit/webhook"
    _return_url = "/payment/xendit/return"

    @http.route("/payment/xendit/payment", type="jsonrpc", auth="public")
    def xendit_payment(self, reference, token_ref, access_token, auth_id=None):
        """Kept for backward compatibility; no longer used, as card payments now go through the
        Xendit-hosted payment link instead of the inline form.

        :param str reference: The reference of the transaction.
        :param str token_ref: The reference of the Xendit token to use to make the payment.
        :param str access_token: The access token used to verify the provided values
        :param str auth_id: The authentication id to use to make the payment.
        :return: None
        """

    @http.route(_webhook_url, type="http", methods=["POST"], auth="public", csrf=False)
    def xendit_webhook(self):
        """Process the payment data sent by Xendit to the webhook.

        :return: The 'accepted' string to acknowledge the notification.
        """
        data = request.get_json_data()
        _logger.info("Notification received from Xendit with data:\n%s", pprint.pformat(data))

        # Real webhooks are wrapped in an envelope; unwrap before processing.
        event = None
        if "event" in data and "data" in data:
            event = data["event"]
            data = data["data"]

        tx_sudo = self.env["payment.transaction"].sudo()._search_by_reference("xendit", data)
        if tx_sudo:
            received_token = request.httprequest.headers.get("x-callback-token")
            expected_token = tx_sudo.provider_id.xendit_webhook_token
            payment_utils.verify_signature(received_token, expected_token)
            if event == "payment_token.activation":
                # Recorded in its envelope to be told apart from payment data upon processing.
                tx_sudo._record({"event": event, "data": data})
            else:
                tx_sudo._record(data)

        return request.make_json_response(["accepted"], status=200)

    @http.route(_return_url, type="http", methods=["GET"], auth="public")
    def xendit_return(self, tx_ref=None, success=False, access_token=None, **_data):
        """Check the transaction status with Xendit after returning from checkout, falling back
        to pending if the webhook notification hasn't come in yet."""
        if access_token and str2bool(success, default=False):
            # A checkout redirect leaves the transaction in `draft` until this return or the
            # webhook processes it, but a token charge requiring 3DS authentication is already
            # `pending` by the time the customer comes back from the challenge.
            tx_sudo = (
                self
                .env["payment.transaction"]
                .sudo()
                .search(
                    [
                        ("provider_code", "=", "xendit"),
                        ("reference", "=", tx_ref),
                        ("state", "in", ("draft", "pending")),
                    ],
                    limit=1,
                )
            )
            if tx_sudo and payment_utils.check_access_token(access_token, tx_ref, tx_sudo.amount):
                if not tx_sudo._xendit_sync_from_provider() and tx_sudo.state == "draft":
                    tx_sudo._record({"status": "PENDING"})
        return request.redirect("/payment/status")
