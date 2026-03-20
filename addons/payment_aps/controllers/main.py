# Part of Odoo. See LICENSE file for full copyright and licensing details.

import hmac
import pprint

from werkzeug.exceptions import Forbidden

from odoo import http
from odoo.http import request

from odoo.addons.payment.logging import get_payment_logger


_logger = get_payment_logger(__name__)


class APSController(http.Controller):
    _return_url = '/payment/aps/return'
    _webhook_url = '/payment/aps/webhook'

    @http.route(
        _return_url, type='http', auth='public', methods=['POST'], csrf=False, save_session=False
    )
    def aps_return_from_checkout(self, **data):
        """Process the payment data sent by APS after redirection.

        The route is flagged with `save_session=False` to prevent Odoo from assigning a new session
        to the user if they are redirected to this route with a POST request. Indeed, as the session
        cookie is created without a `SameSite` attribute, some browsers that don't implement the
        recommended default `SameSite=Lax` behavior will not include the cookie in the redirection
        request from the payment provider to Odoo. As the redirection to the '/payment/status' page
        will satisfy any specification of the `SameSite` attribute, the session of the user will be
        retrieved and with it the transaction which will be immediately post-processed.

        :param dict data: The payment data.
        """
        _logger.info("Handling redirection from APS with data:\n%s", pprint.pformat(data))

        tx_sudo = request.env['payment.transaction'].sudo()._search_by_reference('aps', data)
        if tx_sudo:
            self._verify_signature(data, tx_sudo)
            tx_sudo._process('aps', data)
        return request.redirect('/payment/status')

    @http.route(_webhook_url, type='http', auth='public', methods=['POST'], csrf=False)
    def aps_webhook(self, **data):
        """Process the payment data sent by APS to the webhook.

        See https://paymentservices-reference.payfort.com/docs/api/build/index.html#transaction-feedback.

        :param dict data: The payment data.
        :return: The 'SUCCESS' string to acknowledge the notification
        :rtype: str
        """
        _logger.info("Notification received from APS with data:\n%s", pprint.pformat(data))
        tx_sudo = request.env['payment.transaction'].sudo()._search_by_reference('aps', data)
        if tx_sudo:
            self._verify_signature(data, tx_sudo)
            tx_sudo._process('aps', data)
        return ''  # Acknowledge the notification.

    @staticmethod
    def _verify_signature(payment_data, tx_sudo):
        """Check that the received signature matches the expected one.

        :param dict payment_data: The payment data.
        :param payment.transaction tx_sudo: The sudoed transaction referenced by the payment data.
        :return: None
        :raise Forbidden: If the signatures don't match.
        """
        received_signature = payment_data.get('signature')
        if not received_signature:
            _logger.warning("Received payment data with missing signature.")
            raise Forbidden()

        # Compare the received signature with the expected signature computed from the data.
        expected_signature = tx_sudo.provider_id._aps_calculate_signature(
            payment_data, incoming=True
        )
        if not hmac.compare_digest(received_signature, expected_signature):
            _logger.warning("Received payment data with invalid signature.")
            raise Forbidden()
