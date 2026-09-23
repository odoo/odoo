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
    def xendit_payment(self, reference, token_ref, auth_id=None):
        """Make a payment by token request and handle the response.

        :param str reference: The reference of the transaction.
        :param str token_ref: The reference of the Xendit token to use to make the payment.
        :param str auth_id: The authentication id to use to make the payment.
        :return: None
        """
        tx_sudo = (
            request.env["payment.transaction"]
            .sudo()
            .search([("reference", "=", reference)])
        )
        tx_sudo._xendit_create_charge(token_ref, auth_id=auth_id)

    # csrf=False: auth="receiver" admits the caller through its inbound gate
    @http.route(
        _webhook_url,
        type="http",
        methods=["POST"],
        auth="receiver",
        receiver="payment.transaction:_receiver_for_xendit_webhook",
        csrf=False,
        typed=True,
    )
    def xendit_webhook(self):
        """Process the payment data sent by Xendit to the webhook.

        :return: The 'accepted' string to acknowledge the notification.
        """
        _logger.info(
            "Notification received from Xendit with data:\n%s",
            pprint.pformat(request.get_json_data()),
        )
        request.admission.subject._process("xendit", request.admission.extra["data"])
        return request.prepare_json_response(["accepted"], status=200)

    @http.route(_return_url, type="http", methods=["GET"], auth="public")
    def xendit_return(self, tx_ref=None, success=False, access_token=None, **data):
        """Set draft transaction to pending after successfully returning from Xendit."""
        if access_token and str2bool(success, default=False):
            tx_sudo = (
                request.env["payment.transaction"]
                .sudo()
                .search(
                    [
                        ("provider_code", "=", "xendit"),
                        ("reference", "=", tx_ref),
                        ("state", "=", "draft"),
                    ],
                    limit=1,
                )
            )
            if tx_sudo and payment_utils.is_access_token_valid(
                access_token, tx_ref, tx_sudo.amount
            ):
                tx_sudo._set_pending()
        return request.redirect("/payment/status")
