# Part of Odoo. See LICENSE file for full copyright and licensing details.

import hmac
import logging
import pprint

import requests
from werkzeug.exceptions import Forbidden

from odoo import http
from odoo.exceptions import ValidationError
from odoo.http import request

_logger = logging.getLogger(__name__)


class AlipayController(http.Controller):
    _return_url = '/payment/alipay/return'
    _webhook_url = '/payment/alipay/webhook'

    @http.route(_return_url, type='http', auth='public', methods=['GET'])
    def alipay_return_from_checkout(self, **data):
        """ Process the notification data sent by Alipay after redirection from checkout.

        See https://global.alipay.com/docs/ac/web/sync.

        :param dict data: The notification data
        """
        _logger.info("handling redirection from Alipay with data:\n%s", pprint.pformat(data))

        # Check the integrity of the notification
        tx_sudo = request.env['payment.transaction'].sudo()._get_tx_from_notification_data(
            'alipay', data
        )
        self._verify_notification_signature(data, tx_sudo)

        # Handle the notification data
        tx_sudo._handle_notification_data('alipay', data)
        return request.redirect('/payment/status')

    @http.route(_webhook_url, type='http', auth='public', methods=['POST'], csrf=False)
    def alipay_webhook(self, **data):
        """ Process the notification data sent by Alipay to the webhook.

        See https://global.alipay.com/docs/ac/web/async.

        :param dict data: The notification data
        :return: The 'SUCCESS' string to acknowledge the notification
        :rtype: str
        """
        _logger.info("notification received from Alipay with data:\n%s", pprint.pformat(data))
        try:
            # Check the origin and integrity of the notification
            tx_sudo = request.env['payment.transaction'].sudo()._get_tx_from_notification_data(
                'alipay', data
            )
            self._verify_notification_origin(data, tx_sudo)
            self._verify_notification_signature(data, tx_sudo)

            # Handle the notification data
            tx_sudo._handle_notification_data('alipay', data)
        except ValidationError:  # Acknowledge the notification to avoid getting spammed
            _logger.exception("unable to handle the notification data; skipping to acknowledge")

        return 'SUCCESS'  # Acknowledge the notification

    @staticmethod
    def _verify_notification_origin(notification_data, tx_sudo):
        """ Check that the notification was sent by Alipay.

        See https://global.alipay.com/docs/ac/web/async#9727f6bd.

        :param dict notification_data: The notification data
        :param recordset tx_sudo: The sudoed transaction referenced in the notification data, as a
                                        `payment.transaction` record
        :return: None
        :raise: :class:`werkzeug.exceptions.Forbidden` if the notification origin can't be verified
        """
        url = tx_sudo.provider_id._alipay_get_api_url()
        payload = {
            'service': 'notify_verify',
            'partner': tx_sudo.provider_id.alipay_merchant_partner_id,
            'notify_id': notification_data['notify_id'],
        }
        try:
            response = requests.post(url, data=payload, timeout=60)
            response.raise_for_status()
        except (requests.exceptions.ConnectionError, requests.exceptions.HTTPError) as error:
            _logger.exception(
                "could not verify notification origin at %(url)s with data: %(data)s:\n%(error)s",
                {'url': url, 'data': payload, 'error': pprint.pformat(error.response.text)},
            )
            raise Forbidden()
        else:
            response_content = response.text
            if response_content != 'true':
                _logger.warning(
                    "Alipay did not confirm the origin of the notification with data:\n%s", payload
                )
                raise Forbidden()

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
        received_signature = notification_data.get('sign')
        if not received_signature:
            _logger.warning("received notification with missing signature")
            raise Forbidden()

        # Compare the received signature with the expected signature computed from the data
        expected_signature = tx_sudo.provider_id._alipay_compute_signature(notification_data)
        if not hmac.compare_digest(received_signature, expected_signature):
            _logger.warning("received notification with invalid signature")
            raise Forbidden()
