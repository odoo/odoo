# Part of Odoo. See LICENSE file for full copyright and licensing details.
import hmac
import logging
import pprint

from werkzeug.exceptions import Forbidden

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class PaywayController(http.Controller):
    _webhook_url = '/payment/payway/webhook'

    @http.route(_webhook_url, type='jsonrpc', auth='public', methods=['POST'])
    def payway_webhook(self):
        """Process the notification data sent by PayWay to the webhook."""
        data = request.get_json_data()
        _logger.info("Notification received from PayWay with data:\n%s", pprint.pformat(data))
        tx_sudo = request.env['payment.transaction'].sudo()._search_by_reference('aba_payway', data)
        if tx_sudo and tx_sudo.state != 'done':
            self._verify_signature(request.httprequest.headers.get('x-payway-hmac-sha512'), data, tx_sudo)
            enriched_data = self._enrich_payment_data(tx_sudo, data)
            if enriched_data:
                tx_sudo._process('aba_payway', enriched_data)
            else:
                raise Forbidden()

    @staticmethod
    def _verify_signature(received_signature, payment_data, tx_sudo):
        """Check that the received signature matches the expected one.

        :param dict received_signature: The received signature
        :param payment_data: Webhook notification data received from PayWay.
        :param recordset tx_sudo: The sudoed transaction referenced by the notification data, as a
                                  `payment.transaction` record
        :return: None
        :raise: :class:`werkzeug.exceptions.Forbidden` if the signatures don't match
        """
        if not received_signature:
            _logger.warning("Received notification with missing signature.")
            raise Forbidden()

        expected_signature = tx_sudo.provider_id._payway_calculate_signature(payment_data, sorted(payment_data.keys()))
        if (
                expected_signature is None
                or not hmac.compare_digest(received_signature, expected_signature)
        ):
            _logger.warning("Received notification with invalid signature.")
            raise Forbidden()

    @staticmethod
    def _enrich_payment_data(tx_sudo, payment_data):
        """ ABA PayWay only includes a status, Odoo transaction ID (tran_id) and their reference (apv).
        To substitute signature verification and facilitate amount/currency verification, the expectation is to
        call the "Check Transaction" API with the current tran_id and verify that the payment went through successfully.

        :param tx_sudo: Current transaction object.
        :param payment_data: Webhook notification data received from PayWay.
        :return: Enriched payment data.
        """
        response = tx_sudo.provider_id._payway_api_check_transaction(payment_data['tran_id'])
        status_code = int(response['status']['code'])
        status_msg = response['status']['message']

        if status_code != 0:
            _logger.warning("Checking transaction failed %r: %s", status_code, status_msg)
            return None

        payment_data['data'] = response['data']
        return payment_data
