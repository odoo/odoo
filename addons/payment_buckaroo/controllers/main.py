# Part of Odoo. See LICENSE file for full copyright and licensing details.

import hmac
import pprint

from werkzeug.exceptions import Forbidden

from odoo import http
from odoo.http import request

from odoo.addons.payment.logging import get_payment_logger


_logger = get_payment_logger(__name__)


class BuckarooController(http.Controller):
    _return_url = '/payment/buckaroo/return'
    _webhook_url = '/payment/buckaroo/webhook'

    @http.route(
        _return_url, type='http', auth='public', methods=['POST'], csrf=False, save_session=False
    )
    def buckaroo_return_from_checkout(self, **raw_data):
        """Process the payment data sent by Buckaroo after redirection from checkout.

        The route is flagged with `save_session=False` to prevent Odoo from assigning a new session
        to the user if they are redirected to this route with a POST request. Indeed, as the session
        cookie is created without a `SameSite` attribute, some browsers that don't implement the
        recommended default `SameSite=Lax` behavior will not include the cookie in the redirection
        request from the payment provider to Odoo. As the redirection to the '/payment/status' page
        will satisfy any specification of the `SameSite` attribute, the session of the user will be
        retrieved and with it the transaction which will be immediately post-processed.

        :param dict raw_data: The un-formatted payment data
        """
        _logger.info("handling redirection from Buckaroo with data:\n%s", pprint.pformat(raw_data))
        data = self._normalize_data_keys(raw_data)

        received_signature = data.get('brq_signature')
        tx_sudo = request.env['payment.transaction'].sudo()._search_by_reference(
            'buckaroo', data
        )
        if tx_sudo:
            self._verify_signature(raw_data, received_signature, tx_sudo)
            tx_sudo._process('buckaroo', data)
        return request.redirect('/payment/status')

    @http.route(_webhook_url, type='http', auth='public', methods=['POST'], csrf=False)
    def buckaroo_webhook(self, **raw_data):
        """Process the payment data sent by Buckaroo to the webhook.

        See https://www.pronamic.nl/wp-content/uploads/2013/04/BPE-3.0-Gateway-HTML.1.02.pdf.

        :param dict raw_data: The un-formatted payment data
        :return: An empty string to acknowledge the notification
        :rtype: str
        """
        _logger.info("notification received from Buckaroo with data:\n%s", pprint.pformat(raw_data))
        data = self._normalize_data_keys(raw_data)
        received_signature = data.get('brq_signature')
        tx_sudo = request.env['payment.transaction'].sudo()._search_by_reference(
            'buckaroo', data
        )
        if tx_sudo:
            # Check the integrity of the payment data
            self._verify_signature(raw_data, received_signature, tx_sudo)
            tx_sudo._process('buckaroo', data)
        return ''

    @staticmethod
    def _normalize_data_keys(data):
        """ Set all keys of a dictionary to lower-case.

        As Buckaroo parameters names are case insensitive, we can convert everything to lower-case
        to easily detected the presence of a parameter by checking the lower-case key only.

        :param dict data: The dictionary whose keys must be set to lower-case
        :return: A copy of the original data with all keys set to lower-case
        :rtype: dict
        """
        return {key.lower(): val for key, val in data.items()}

    @staticmethod
    def _verify_signature(payment_data, received_signature, tx_sudo):
        """Check that the received signature matches the expected one.

        :param dict payment_data: The payment data.
        :param str received_signature: The signature received with the payment data.
        :param payment.transaction tx_sudo: The sudoed transaction referenced by the payment data.
        :return: None
        :raise Forbidden: If the signatures don't match.
        """
        # Check for the received signature
        if not received_signature:
            _logger.warning("Received payment data with missing signature")
            raise Forbidden()

        # Compare the received signature with the expected signature computed from the data
        expected_signature = tx_sudo.provider_id._buckaroo_generate_digital_sign(
            payment_data, incoming=True
        )
        if not hmac.compare_digest(received_signature, expected_signature):
            _logger.warning("Received payment data with invalid signature")
            raise Forbidden()
