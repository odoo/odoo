# Part of Odoo. See LICENSE file for full copyright and licensing details.

import pprint

from odoo import http
from odoo.http import request

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.logging import get_payment_logger
from odoo.addons.payment_ecpay import const

_logger = get_payment_logger(__name__)


class EcpayController(http.Controller):
    @http.route(
        const.PAYMENT_RETURN_ROUTE,
        type="http",
        auth="public",
        # In CVS/Barcode flows, ECPay can redirect users here with a plain GET when they click
        # "Return to merchant store". That request has no payload and does not indicate that the
        # payment failed.
        methods=["GET", "POST"],
        csrf=False,
        save_session=False,
    )
    def ecpay_return_from_checkout(self, **data):
        """Process the notification data (if included) sent by ECPay after redirection.

        The route is flagged with `save_session=False` to prevent Odoo from assigning a new session
        to the user if they are redirected to this route with a POST request. Indeed, as the session
        cookie is created without a `SameSite` attribute, some browsers that don't implement the
        recommended default `SameSite=Lax` behavior will not include the cookie in the redirection
        request from the payment provider to Odoo. As the redirection to the '/payment/status' page
        will satisfy any specification of the `SameSite` attribute, the session of the user will be
        retrieved and with it the transaction which will be immediately post-processed.

        :param dict data: The payment data.
        """
        if request.httprequest.method == "POST" and data:
            _logger.info("Handling redirection from ECPay with data:\n%s", pprint.pformat(data))
            tx_sudo = request.env["payment.transaction"].sudo()._search_by_reference("ecpay", data)
            if tx_sudo:
                received_signature = data.pop("CheckMacValue", None)
                expected_signature = tx_sudo.provider_id._ecpay_calculate_signature(data)
                payment_utils.verify_signature(received_signature, expected_signature)
                tx_sudo._record(data)
        return request.redirect("/payment/status")

    @http.route(
        const.WEBHOOK_ROUTE,
        type="http",
        auth="public",
        methods=["POST"],
        csrf=False,
        save_session=False,
    )
    def ecpay_webhook(self, **data):
        """Process the payment data sent by ECPay to the webhook.

        The route is flagged with `save_session=False` to prevent Odoo from assigning a new session
        to the user.

        :param dict data: The payment data.
        :return: The '1|OK' string to acknowledge the notification.
        :rtype: str
        """
        _logger.info("Notification received from ECPay with data:\n%s", pprint.pformat(data))
        if data and data.get("SimulatePaid") == "0":
            tx_sudo = request.env["payment.transaction"].sudo()._search_by_reference("ecpay", data)
            if tx_sudo:
                received_signature = data.pop("CheckMacValue", None)
                expected_signature = tx_sudo.provider_id._ecpay_calculate_signature(data)
                payment_utils.verify_signature(received_signature, expected_signature)
                tx_sudo._record(data)
        else:
            _logger.info(
                "Received payment simulation notification from ECPay, skipping processing of the"
                " data."
            )
        return "1|OK"
