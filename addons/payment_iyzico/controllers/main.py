# Part of Odoo. See LICENSE file for full copyright and licensing details.

import hmac
import logging
import pprint

from werkzeug.exceptions import Forbidden

from odoo import http
from odoo.exceptions import ValidationError
from odoo.http import request

_logger = logging.getLogger(__name__)


class IyzicoController(http.Controller):
    _return_url = '/payment/iyzico/return'

    @http.route(_return_url, type='http', auth='public', methods=['POST'], csrf=False)
    def iyzico_return_from_checkout(self, **data):
        """ Process the notification data sent by Iyzico after redirection from checkout.

        :param dict data: The notification data.
        """
        _logger.info("Notification received from Iyzico with data:\n%s", pprint.pformat(data))
        self._verify_and_handle_notification_data(data)

        return request.redirect('/payment/status')

    @staticmethod
    def _verify_and_handle_notification_data(data):
        """ Verify and process the notification data sent by Iyzico.

        :param dict data: The notification data.
        :return: None
        """
        try:
            tx_sudo = request.env['payment.transaction'].sudo()._get_tx_from_notification_data(
                'iyzico', data
            )
            cf_response = tx_sudo.provider_id._iyzico_make_request(
                '/payment/iyzipos/checkoutform/auth/ecom/detail',
                payload={
                    'conversationId': tx_sudo.reference,
                    'locale': request.env.lang == 'tr_TR' and 'tr' or 'en',
                    'token': data.get('token'),
                },
            )
            _logger.info(
                "Response of Iyzico Checkout form Retrive request:\n%s",
                pprint.pformat(cf_response)
            )

            if cf_response.get('paymentStatus') != 'FAILURE':
                # Check the integrity of the notification
                IyzicoController._verify_notification_signature(cf_response, tx_sudo)

                # Handle the notification data.
                tx_sudo._handle_notification_data('iyzico', cf_response)
            else:
                pass  # Don't try to process this case because the response does not contains enough
                # data to verify signature.
        except ValidationError:
            _logger.exception("Unable to handle notification data; skipping to acknowledge.")

    @staticmethod
    def _verify_notification_signature(notification_data, tx_sudo):
        """ Check that the received signature matches the expected one.

        :param dict notification_data: The notification data
        :param recordset tx_sudo: The sudoed transaction referenced by the notification data, as a
                                  `payment.transaction` record
        :return: None
        :raise: :class:`werkzeug.exceptions.Forbidden` if the signatures don't match
        """
        received_signature = notification_data.get('signature')
        if not received_signature:
            _logger.warning("received notification with missing signature")
            raise Forbidden()

        # Compare the received signature with the expected signature computed from the data.
        expected_signature = tx_sudo.provider_id._iyzico_calculate_signature(notification_data)
        if not hmac.compare_digest(received_signature, expected_signature):
            _logger.warning("received notification with invalid signature")
            raise Forbidden()
