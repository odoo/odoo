# Part of Odoo. See LICENSE file for full copyright and licensing details.

import pprint

from werkzeug.exceptions import Forbidden

from odoo import _, http
from odoo.exceptions import ValidationError
from odoo.http import request

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.logging import get_payment_logger
from odoo.addons.payment_paypal import const


_logger = get_payment_logger(__name__)


class PaypalController(http.Controller):
    _complete_url = '/payment/paypal/complete_order'
    _webhook_url = '/payment/paypal/webhook/'

    @http.route(_complete_url, type='jsonrpc', auth='public', methods=['POST'])
    def paypal_complete_order(self, order_id, reference):
        """Make a capture request and process the payment data.

        :param string order_id: The order id provided by PayPal to identify the order.
        :param str reference: The reference of the transaction, used to generate the idempotency
                              key.
        :return: None
        """
        tx_sudo = request.env['payment.transaction'].sudo()._search_by_reference(
            'paypal', {'reference_id': reference}
        )
        if tx_sudo:
            idempotency_key = payment_utils.generate_idempotency_key(
                tx_sudo, scope='payment_request_controller'
            )
            response = tx_sudo._send_api_request(
                'POST', f'/v2/checkout/orders/{order_id}/capture', idempotency_key=idempotency_key
            )
            normalized_response = self._normalize_paypal_data(response)
            tx_sudo = request.env['payment.transaction'].sudo()._search_by_reference(
                'paypal', normalized_response
            )
            tx_sudo._process('paypal', normalized_response)

    @http.route(_webhook_url, type='http', auth='public', methods=['POST'], csrf=False)
    def paypal_webhook(self):
        """Process the payment data sent by PayPal to the webhook.

        See https://developer.paypal.com/docs/api/webhooks/v1/.

        :return: An empty string to acknowledge the notification.
        :rtype: str
        """
        data = request.get_json_data()
        if data.get('event_type') in const.HANDLED_WEBHOOK_EVENTS:
            _logger.info("Notification received from PayPal with data:\n%s", pprint.pformat(data))
            normalized_data = self._normalize_paypal_data(data.get('resource'), from_webhook=True)
            # Check the origin and integrity of the notification.
            tx_sudo = request.env['payment.transaction'].sudo()._search_by_reference(
                'paypal', normalized_data
            )
            if tx_sudo:
                self._verify_notification_origin(data, tx_sudo)
                tx_sudo._process('paypal', normalized_data)
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
                _logger.warning(_("Invalid response format, can't normalize."))
        return result

    def _verify_notification_origin(self, payment_data, tx_sudo):
        """ Check that the notification was sent by PayPal.

        See https://developer.paypal.com/docs/api/webhooks/v1/#verify-webhook-signature_post.

        :param dict payment_data: The payment data.
        :param payment.transaction tx_sudo: The sudoed transaction referenced in the payment data.
        :return: None
        :raise Forbidden: If the notification origin can't be verified.
        """
        headers = request.httprequest.headers
        data = {
            'transmission_id': headers.get('PAYPAL-TRANSMISSION-ID'),
            'transmission_time': headers.get('PAYPAL-TRANSMISSION-TIME'),
            'cert_url': headers.get('PAYPAL-CERT-URL'),
            'auth_algo': headers.get('PAYPAL-AUTH-ALGO'),
            'transmission_sig': headers.get('PAYPAL-TRANSMISSION-SIG'),
            'webhook_id': tx_sudo.provider_id.paypal_webhook_id,
            'webhook_event': payment_data,
        }
        try:
            verification = tx_sudo._send_api_request(
                'POST', '/v1/notifications/verify-webhook-signature', json=data
            )
        except ValidationError:
            tx_sudo._set_error(_("Unable to verify the payment data"))
            return

        if verification.get('verification_status') != 'SUCCESS':
            _logger.warning("Received payment data that was not verified by PayPal.")
            raise Forbidden()
