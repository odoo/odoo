# Part of Odoo. See LICENSE file for full copyright and licensing details.

import pprint

from werkzeug.exceptions import ServiceUnavailable

from odoo import http
from odoo.exceptions import ValidationError
from odoo.http import request

from odoo.addons.payment.logging import get_payment_logger

_logger = get_payment_logger(__name__)


class MollieController(http.Controller):
    _return_url = "/payment/mollie/return"
    _webhook_url = "/payment/mollie/webhook"

    @http.route(
        _return_url,
        type="http",
        auth="public",
        methods=["GET", "POST"],
        csrf=False,
        save_session=False,
    )
    def mollie_return_from_checkout(self, **data):
        """Process the payment data sent by Mollie after redirection from checkout.

        The route is flagged with `save_session=False` to prevent Odoo from assigning a new session
        to the user if they are redirected to this route with a POST request. Indeed, as the session
        cookie is created without a `SameSite` attribute, some browsers that don't implement the
        recommended default `SameSite=Lax` behavior will not include the cookie in the redirection
        request from the payment provider to Odoo. As the redirection to the '/payment/status' page
        will satisfy any specification of the `SameSite` attribute, the session of the user will be
        retrieved and with it the transaction which will be immediately post-processed.

        :param dict data: The payment data (only `id`) and the transaction reference (`ref`)
                          embedded in the return URL.
        """
        _logger.info("handling redirection from Mollie with data:\n%s", pprint.pformat(data))
<<<<<<< ecf3b5a244ace6730722212666499ce0b728c391
        self._verify_and_process(data)
        return request.redirect("/payment/status")
||||||| 18a960f0b4830e5b978ae5bc9de0577422db3fcf
        self._verify_and_process(data)
        return request.redirect('/payment/status')
=======
        try:
            self._verify_and_process(data)
        except ValidationError:
            _logger.error("Unable to process the payment data")
        return request.redirect('/payment/status')
>>>>>>> 418b24aabbe82b1bf0313f8c6b838de0eab5ab60

    @http.route(_webhook_url, type="http", auth="public", methods=["POST"], csrf=False)
    def mollie_webhook(self, **data):
        """Process the payment data sent by Mollie to the webhook.

        :param dict data: The payment data (only `id`) and the transaction reference (`ref`)
                          embedded in the return URL
        :return: An empty string to acknowledge the notification
        :rtype: str
        :raise ServiceUnavailable: If the payment data could not be fetched from Mollie
        """
        _logger.info("notification received from Mollie with data:\n%s", pprint.pformat(data))
<<<<<<< ecf3b5a244ace6730722212666499ce0b728c391
        self._verify_and_process(data)
        return ""  # Acknowledge the notification
||||||| 18a960f0b4830e5b978ae5bc9de0577422db3fcf
        self._verify_and_process(data)
        return ''  # Acknowledge the notification
=======
        try:
            self._verify_and_process(data)
        except ValidationError as error:
            _logger.error("Unable to process the payment data")
            raise ServiceUnavailable from error
        return ''  # Acknowledge the notification
>>>>>>> 418b24aabbe82b1bf0313f8c6b838de0eab5ab60

    @staticmethod
    def _verify_and_process(data):
        """Verify and process the payment data sent by Mollie.

        :param dict data: The payment data.
        :return: None
        :raise ValidationError: If the payment data could not be fetched from Mollie
        """
        tx_sudo = request.env["payment.transaction"].sudo()._search_by_reference("mollie", data)
        if not tx_sudo:
            return

<<<<<<< ecf3b5a244ace6730722212666499ce0b728c391
        try:
            verified_data = tx_sudo._send_api_request(
                "GET", f"/payments/{tx_sudo.provider_reference}"
            )
        except ValidationError:
            _logger.error("Unable to process the payment data")
        else:
            tx_sudo._process("mollie", verified_data)
||||||| 18a960f0b4830e5b978ae5bc9de0577422db3fcf
        try:
            verified_data = tx_sudo._send_api_request(
                'GET', f'/payments/{tx_sudo.provider_reference}'
            )
        except ValidationError:
            _logger.error("Unable to process the payment data")
        else:
            tx_sudo._process('mollie', verified_data)
=======
        verified_data = tx_sudo._send_api_request("GET", f"/payments/{tx_sudo.provider_reference}")
        tx_sudo._process("mollie", verified_data)
>>>>>>> 418b24aabbe82b1bf0313f8c6b838de0eab5ab60
