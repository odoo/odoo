import pprint

from odoo import http
from odoo.exceptions import ValidationError
from odoo.http import request

from odoo.addons.payment.logging import get_payment_logger
from odoo.addons.payment_iyzico import const

_logger = get_payment_logger(__name__)


class IyzicoController(http.Controller):
    # csrf=False: auth="receiver" admits the caller through its inbound gate
    @http.route(
        const.PAYMENT_RETURN_ROUTE,
        type="http",
        auth="receiver",
        receiver="payment.transaction:_receiver_for_iyzico_return",
        methods=["POST"],
        csrf=False,
        save_session=False,
        typed=True,
    )
    def iyzico_return_from_payment(self, tx_ref: str = "", **data):
        """Process the payment data sent by Iyzico after redirection from checkout.

        The route is flagged with `save_session=False` to prevent Odoo from assigning a new session
        to the user if they are redirected to this route with a POST request. Indeed, as the session
        cookie is created without a `SameSite` attribute, some browsers that don't implement the
        recommended default `SameSite=Lax` behavior will not include the cookie in the redirection
        request from the payment provider to Odoo. As the redirection to the '/payment/status' page
        will satisfy any specification of the `SameSite` attribute, the session of the user will be
        retrieved and with it the transaction which will be immediately post-processed.

        :param str tx_ref: The reference of the related transaction.
        :param dict data: The payment data.
        """
        _logger.info(
            "Handling redirection from Iyzico with data:\n%s", pprint.pformat(data)
        )
        self._check_and_process()
        return request.redirect("/payment/status")

    # csrf=False: auth="receiver" admits the caller through its inbound gate
    @http.route(
        const.WEBHOOK_ROUTE,
        type="http",
        auth="receiver",
        receiver="payment.transaction:_receiver_for_iyzico_webhook",
        methods=["POST"],
        csrf=False,
        typed=True,
    )
    def iyzico_webhook(self):
        """Process the payment data sent by Iyzico to the webhook.

        See https://docs.iyzico.com/en/advanced/webhook.

        :return: An empty response to acknowledge the notification.
        :rtype: odoo.http.Response
        """
        data = request.get_json_data()
        _logger.info(
            "Notification received from Iyzico with data:\n%s", pprint.pformat(data)
        )
        self._check_and_process()
        return request.prepare_json_response("")  # Acknowledge the notification.

    @staticmethod
    def _check_and_process():
        """Process the admitted transaction's payment, fetched back from Iyzico's API."""
        tx_sudo = request.admission.subject
        token = request.admission.extra["token"]
        try:
            verified_payment_data = tx_sudo._send_api_request(
                "POST",
                "payment/iyzipos/checkoutform/auth/ecom/detail",
                json={
                    "conversationId": tx_sudo.reference,
                    "locale": (request.env.lang == "tr_TR" and "tr") or "en",
                    "token": token,
                },
            )
            tx_sudo._process("iyzico", verified_payment_data)
        except ValidationError:
            _logger.error("Unable to process the payment data.")
