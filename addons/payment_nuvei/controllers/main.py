# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import pprint

from werkzeug.exceptions import Forbidden

from odoo import http
from odoo.exceptions import ValidationError
from odoo.http import request
from odoo.tools import consteq

from odoo.addons.payment import utils as payment_utils

_logger = logging.getLogger(__name__)


class NuveiController(http.Controller):
    _return_url = '/payment/nuvei/return'
    _webhook_url = '/payment/nuvei/webhook'
    _cancel_url = '/payment/nuvei/cancel'

    @http.route(_return_url, type='http', auth='public', methods=['GET'])
    def nuvei_return_from_checkout(self, **data):
        """ Process the notification data sent by Nuvei after redirection.

        :param dict data: The notification data.
        """
        _logger.info("Handling redirection from Nuvei with data:\n%s", pprint.pformat(data))

        if data:
            # Check the integrity of the notification.
            tx_sudo = request.env['payment.transaction'].sudo()._get_tx_from_notification_data(
                'nuvei', data
            )
            self._verify_notification_signature(data, tx_sudo)

            # Handle the notification data.
            tx_sudo._handle_notification_data('nuvei', data)
        else:
            pass
        return request.redirect('/payment/status')

    @http.route(_webhook_url, type='http', auth='public', methods=['POST'], csrf=False)
    def nuvei_webhook(self, **data):
        """ Process the notification data sent by Nuvei to the webhook.

        See https://docs.nuvei.com/documentation/accept-payment/payment-page/output-parameters.

        :param dict data: The notification data.
        :return: The 'OK' string to acknowledge the notification.
        :rtype: str
        """
        _logger.info("Notification received from Nuvei with data:\n%s", pprint.pformat(data))
        try:
            # Check the integrity of the notification.
            tx_sudo = request.env['payment.transaction'].sudo()._get_tx_from_notification_data(
                'nuvei', data
            )
            self._verify_notification_signature(data, tx_sudo)

            # Handle the notification data.
            tx_sudo._handle_notification_data('nuvei', data)
        except ValidationError:  # Acknowledge the notification to avoid getting spammed.
            _logger.exception("Unable to handle the notification data; skipping to acknowledge.")

        return 'OK'  # Acknowledge the notification.

    @http.route(
        _cancel_url, type='http', auth='public', methods=['GET'], csrf=False, save_session=False
    )
    def nuvei_return_from_canceled_checkout(self, tx_ref, return_access_tkn):
        """ Process the transaction after the customer has canceled the payment.

        :param str tx_ref: The reference of the transaction having been canceled.
        :param str return_access_tkn: The access token to verify the authenticity of the request.
        """
        _logger.info(
            "Handling redirection from Nuvei for cancellation of transaction with reference %s",
            tx_ref,
        )

        tx_sudo = request.env['payment.transaction'].sudo()._get_tx_from_notification_data(
            'nuvei', {'invoice_id': tx_ref}
        )
        if not payment_utils.check_access_token(return_access_tkn, tx_ref):
            raise Forbidden()
        tx_sudo._handle_notification_data('nuvei', {})

        return request.redirect('/payment/status')

    @staticmethod
    def _verify_notification_signature(notification_data, tx_sudo):
        """ Check that the received signature matches the expected one.

        :param dict notification_data: The notification data
        :param recordset tx_sudo: The sudoed transaction referenced by the notification data, as a
                                  `payment.transaction` record
        :return: None
        :raise: :class:`werkzeug.exceptions.Forbidden` if the signatures don't match
        """
        received_signature = notification_data.get('advanceResponseChecksum')
        if not received_signature:
            _logger.warning("received notification with missing signature")
            raise Forbidden()

        # Compare the received signature with the expected signature computed from the data.
        expected_signature = tx_sudo.provider_id._nuvei_calculate_signature(
            notification_data, incoming=True,
        )
        if not consteq(received_signature, expected_signature):
            _logger.warning("received notification with invalid signature")
            raise Forbidden()
