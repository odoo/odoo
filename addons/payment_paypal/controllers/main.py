# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import logging
import pprint

from werkzeug.exceptions import Forbidden

from odoo import _, http
from odoo.exceptions import ValidationError
from odoo.http import request

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment_paypal import const


_logger = logging.getLogger(__name__)


class PaypalController(http.Controller):
    _complete_url = '/payment/paypal/complete_order'
    _webhook_url = '/payment/paypal/webhook/'

    @http.route(_complete_url, type='json', auth='public', methods=['POST'])
    def paypal_complete_order(self, provider_id, order_id, reference=None):
        """ Make a capture request and handle the notification data.

        :param int provider_id: The provider handling the transaction, as a `payment.provider` id.
        :param string order_id: The order id provided by PayPal to identify the order.
        :param str reference: The reference of the transaction used to generate idempotency key.
        :return: None
        """
        provider_sudo = request.env['payment.provider'].browse(provider_id).sudo()
        idempotency_key = None
        if reference:
            tx_sudo = request.env['payment.transaction'].sudo()._get_tx_from_notification_data(
                'paypal', {'reference_id': reference}
            )
            idempotency_key = payment_utils.generate_idempotency_key(
                tx_sudo, scope='payment_request_controller'
            )
        response = provider_sudo._paypal_make_request(
            f'/v2/checkout/orders/{order_id}/capture', idempotency_key=idempotency_key
        )
        normalized_response = self._normalize_paypal_data(response)
        tx_sudo = request.env['payment.transaction'].sudo()._get_tx_from_notification_data(
            'paypal', normalized_response
        )
        tx_sudo._handle_notification_data('paypal', normalized_response)

    @http.route(_webhook_url, type='http', auth='public', methods=['POST'], csrf=False)
    def paypal_webhook(self):
        """ Process the notification data sent by PayPal to the webhook.

        See https://developer.paypal.com/docs/api/webhooks/v1/.

        :return: An empty string to acknowledge the notification.
        :rtype: str
        """
        data = request.get_json_data()
        if data.get('event_type') in const.HANDLED_WEBHOOK_EVENTS:
            normalized_data = self._normalize_paypal_data(
                data.get('resource'), from_webhook=True
            )
            _logger.info("Notification received from PayPal with data:\n%s", pprint.pformat(data))
            try:
                # Check the origin and integrity of the notification.
                tx_sudo = request.env['payment.transaction'].sudo()._get_tx_from_notification_data(
                    'paypal', normalized_data
                )
                self._verify_notification_origin(data, tx_sudo)

                # Handle the notification data.
                tx_sudo._handle_notification_data('paypal', normalized_data)
            except ValidationError:  # Acknowledge the notification to avoid getting spammed.
                _logger.warning(
                    "Unable to handle the notification data; skipping to acknowledge.",
                    exc_info=True,
                )
        return request.make_json_response('')

    def _normalize_paypal_data(self, data, from_webhook=False):
        """ Normalize the payment data received from PayPal.

        The payment data received from PayPal has a different format depending on whether the data
        come from the payment request response, or from the webhook.

        :param dict data: The data to normalize.
        :param bool from_webhook: Whether the data come from the webhook.
        :return: The normalized data.
        :rtype: dict
        """
        purchase_unit = data['purchase_units'][0]
        result = {
            'payment_source': data['payment_source'].keys(),
            'reference_id': purchase_unit.get('reference_id')
        }
        if from_webhook:
            result.update({
                **purchase_unit,
                'txn_type': data.get('intent'),
                'id': data.get('id'),
                'status': data.get('status'),
            })
        else:
            if captured := purchase_unit.get('payments', {}).get('captures'):
                result.update({
                    **captured[0],
                    'txn_type': 'CAPTURE',
                })
            else:
                raise ValidationError("PayPal: " + _("Invalid response format, can't normalize."))
        return result

    def _verify_notification_origin(self, notification_data, tx_sudo):
        """ Check that the notification was sent by PayPal.

        See https://developer.paypal.com/docs/api/webhooks/v1/#verify-webhook-signature_post.

        :param dict notification_data: The notification data
        :param recordset tx_sudo: The sudoed transaction referenced in the notification data, as a
                                  `payment.transaction` record
        :return: None
        :raise Forbidden: If the notification origin can't be verified.
        """
        headers = request.httprequest.headers
        data = json.dumps({
            'transmission_id': headers.get('PAYPAL-TRANSMISSION-ID'),
            'transmission_time': headers.get('PAYPAL-TRANSMISSION-TIME'),
            'cert_url': headers.get('PAYPAL-CERT-URL'),
            'auth_algo': headers.get('PAYPAL-AUTH-ALGO'),
            'transmission_sig': headers.get('PAYPAL-TRANSMISSION-SIG'),
            'webhook_id': tx_sudo.provider_id.paypal_webhook_id,
            'webhook_event': notification_data,
        })
        verification = tx_sudo.provider_id._paypal_make_request(
            '/v1/notifications/verify-webhook-signature', data=data
        )
        if verification.get('verification_status') != 'SUCCESS':
            _logger.warning("Received notification that was not verified by PayPal.")
            raise Forbidden()
