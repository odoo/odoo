# Part of Odoo. See LICENSE file for full copyright and licensing details.

import pprint

from werkzeug.exceptions import Forbidden

from odoo import http
from odoo.http import request
from odoo.tools import consteq

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.logging import get_payment_logger


_logger = get_payment_logger(__name__)


class NuveiController(http.Controller):
    _return_url = '/payment/nuvei/return'
    _webhook_url = '/payment/nuvei/webhook'

    @http.route(_return_url, type='http', auth='public', methods=['GET'])
    def nuvei_return_from_checkout(self, tx_ref=None, error_access_token=None, **data):
        """Process the payment data sent by Nuvei after redirection.

        :param str tx_ref: The optional reference of the transaction having been canceled/errored.
        :param str error_access_token: The optional access token to verify the authenticity of
                                       requests for errored payments.
        :param dict data: The payment data.
        """
        _logger.info("Handling redirection from Nuvei with data:\n%s", pprint.pformat(data))
        if tx_ref and error_access_token:
            _logger.warning("Nuvei errored on transaction: %s.", tx_ref)

        tx_data = data or {'invoice_id': tx_ref}
        tx_sudo = request.env['payment.transaction'].sudo()._search_by_reference('nuvei', tx_data)
        if tx_sudo:
            self._verify_signature(
                tx_sudo, data, error_access_token=error_access_token
            )
            tx_sudo._process('nuvei', data)
        return request.redirect('/payment/status')

    @http.route(_webhook_url, type='http', auth='public', methods=['POST'], csrf=False)
    def nuvei_webhook(self, **data):
        """Process the payment data sent by Nuvei to the webhook.

        See https://docs.nuvei.com/documentation/integration/webhooks/payment-dmns/.

        :param dict data: The payment data.
        :return: The 'OK' string to acknowledge the notification.
        :rtype: str
        """
        _logger.info("Notification received from Nuvei with data:\n%s", pprint.pformat(data))
        tx_sudo = request.env['payment.transaction'].sudo()._search_by_reference('nuvei', data)
        if tx_sudo:
            self._verify_signature(tx_sudo, data)
            tx_sudo._process('nuvei', data)

        return 'OK'  # Acknowledge the notification.

    @staticmethod
    def _verify_signature(tx_sudo, payment_data, error_access_token=None):
        """Check that the received signature matches the expected one.

        :param payment.transaction tx_sudo: The sudoed transaction referenced by the notification
                                            data.
        :param dict payment_data: The payment data.
        :param str error_access_token: The optional access token for verifying errored payments.
        :return: None
        :raise Forbidden: If the signatures don't match.
        """
        if error_access_token:  # The access token is not included when the payment goes through.
            # Verify the request based on the provided access token.
            ref = tx_sudo.reference
            if not payment_utils.check_access_token(error_access_token, ref):
                _logger.warning("Received cancel/error with invalid access token.")
                raise Forbidden()
        else:  # The payment went through.
            received_signature = payment_data.get('advanceResponseChecksum')
            if not received_signature:
                _logger.warning("Received payment data with missing signature")
                raise Forbidden()

            # Compare the received signature with the expected signature computed from the data.
            expected_signature = tx_sudo.provider_id._nuvei_calculate_signature(
                payment_data, incoming=True,
            )
            if not consteq(received_signature, expected_signature):
                _logger.warning("Received payment data with invalid signature")
                raise Forbidden()
