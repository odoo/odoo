# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import pprint

from werkzeug.exceptions import Forbidden

from odoo import http
from odoo.exceptions import ValidationError
from odoo.http import request
from odoo.tools import consteq

_logger = logging.getLogger(__name__)


class PayuLatamController(http.Controller):
    _return_url = '/payment/payulatam/return'
    _webhook_url = '/payment/payulatam/webhook'

    @http.route(_return_url, type='http', auth='public', methods=['GET'])
    def payulatam_return_from_checkout(self, **data):
        """ Process the notification data sent by PayU Latam after redirection from checkout.

        See http://developers.payulatam.com/latam/en/docs/integrations/webcheckout-integration/response-page.html.

        :param dict data: The notification data
        """
        _logger.info("handling redirection from PayU Latam with data:\n%s", pprint.pformat(data))

        # Check the integrity of the notification
        tx_sudo = request.env['payment.transaction'].sudo()._get_tx_from_notification_data(
            'payulatam', data
        )
        self._verify_notification_signature(data, tx_sudo)

        # Handle the notification data
        tx_sudo._handle_notification_data('payulatam', data)
        return request.redirect('/payment/status')

    @http.route(_webhook_url, type='http', auth='public', methods=['POST'], csrf=False)
    def payulatam_webhook(self, **raw_data):
        """ Process the notification data sent by PayU Latam to the webhook.

        See http://developers.payulatam.com/latam/en/docs/integrations/webcheckout-integration/confirmation-page.html.

        :param dict raw_data: The un-formatted notification data
        :return: An empty string to acknowledge the notification
        :rtype: str
        """
        _logger.info(
            "notification received from PayU Latam with data:\n%s", pprint.pformat(raw_data)
        )
        data = self._normalize_data_keys(raw_data)

        try:
            # Check the origin and integrity of the notification
            tx_sudo = request.env['payment.transaction'].sudo().with_context(
                payulatam_is_confirmation_page=True
            )._get_tx_from_notification_data('payulatam', data)
            self._verify_notification_signature(data, tx_sudo)  # Use the normalized data.

            # Handle the notification data
            tx_sudo._handle_notification_data('payulatam', data)
        except ValidationError:  # Acknowledge the notification to avoid getting spammed
            _logger.exception("unable to handle the notification data; skipping to acknowledge")

        return ''

    @staticmethod
    def _normalize_data_keys(webhook_notification_data):
        """ Reshape the webhook notification data to process them as redirect notification data.

        :param dict webhook_notification_data: The webhook notification data
        :return: The normalized notification data
        :rtype: dict
        """
        state_pol = webhook_notification_data.get('state_pol')
        if state_pol == '4':
            lap_transaction_state = 'APPROVED'
        elif state_pol == '6':
            lap_transaction_state = 'DECLINED'
        elif state_pol == '5':
            lap_transaction_state = 'EXPIRED'
        else:
            lap_transaction_state = f'INVALID state_pol {state_pol}'
        return {
            'lapTransactionState': lap_transaction_state,
            'transactionState': webhook_notification_data.get('state_pol'),
            'TX_VALUE': webhook_notification_data.get('value'),
            'currency': webhook_notification_data.get('currency'),
            'referenceCode': webhook_notification_data.get('reference_sale'),
            'transactionId': webhook_notification_data.get('transaction_id'),
            'message': webhook_notification_data.get('response_message_pol'),
            'signature': webhook_notification_data.get('sign'),
        }

    @staticmethod
    def _verify_notification_signature(notification_data, tx_sudo):
        """ Check that the received signature matches the expected one.

        :param dict notification_data: The notification data
        :param recordset tx_sudo: The sudoed transaction referenced by the notification data, as a
                                  `payment.transaction` record
        :return: None
        :raise: :class:`werkzeug.exceptions.Forbidden` if the signatures don't match
        """
        # Retrieve the received signature from the data
        received_signature = notification_data.get('signature')
        if not received_signature:
            _logger.warning("received notification with missing signature")
            raise Forbidden()

        # Compare the received signature with the expected signature computed from the data
        expected_signature = tx_sudo.provider_id._payulatam_generate_sign(notification_data)
        if not consteq(received_signature, expected_signature):
            _logger.warning("received notification with invalid signature")
            raise Forbidden()
