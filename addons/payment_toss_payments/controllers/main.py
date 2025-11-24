import hmac
import pprint

from werkzeug.exceptions import Forbidden

from odoo import http
from odoo.exceptions import ValidationError
from odoo.http import request

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.logging import get_payment_logger
from odoo.addons.payment_toss_payments import const

_logger = get_payment_logger(__name__, const.SENSITIVE_KEYS)


class TossPaymentsController(http.Controller):
    @http.route(const.PAYMENT_SUCCESS_RETURN_ROUTE, type='http', auth='public', methods=['GET'])
    def _toss_payments_success_return(self, **data):
        """Process the payment data after redirection from successful payment.

        :param dict data: The payment data. Expected keys: orderId, paymentKey, amount.
        """
        _logger.info("Handling redirection from Toss Payments with data:\n%s", pprint.pformat(data))
        tx_sudo = (
            request.env['payment.transaction'].sudo()._search_by_reference('toss_payments', data)
        )
        if not tx_sudo:
            return request.redirect('/payment/status')

        # Prevent tampering the amount from the client by validating it before sending the payment
        # confirmation request. The payment data uses `totalAmount` to follow the format of the
        # webhook data.
        tx_sudo._validate_amount({'totalAmount': data.get('amount')})
        if tx_sudo.state != 'error':  # The amount validation succeeded.
            try:
                payment_data = tx_sudo._send_api_request('POST', '/v1/payments/confirm', json=data)
            except ValidationError as e:
                tx_sudo._set_error(str(e))
            else:
                tx_sudo._process('toss_payments', payment_data)

        return request.redirect('/payment/status')

    @http.route(const.PAYMENT_FAILURE_RETURN_ROUTE, type='http', auth='public', methods=['GET'])
    def _toss_payments_failure_return(self, **data):
        """Process the payment data after redirection from failed payment.

        Note: The access token is used to verify the request is coming from Toss Payments since we
        don't have paymentKey in the failure return URL to verify the request via API call.

        :param dict data: The payment data. Expected keys: access_token, code, message, orderId.
        """
        _logger.info("Handling redirection from Toss Payments with data:\n%s", pprint.pformat(data))
        tx_sudo = (
            request.env['payment.transaction'].sudo()._search_by_reference('toss_payments', data)
        )
        if not tx_sudo:
            return request.redirect('/payment/status')

        access_token = data.get('access_token')
        if not access_token or not payment_utils.check_access_token(
            access_token, tx_sudo.reference
        ):
            return request.redirect('/payment/status')

        tx_sudo._set_error(f"{data['message']} ({data['code']})")

        return request.redirect('/payment/status')

    @http.route(const.WEBHOOK_ROUTE, type='http', auth='public', methods=['POST'], csrf=False)
    def _toss_payments_webhook(self):
        """Process the event data sent to the webhook.

        See https://docs.tosspayments.com/reference/using-api/webhook-events#%EC%9D%B4%EB%B2%A4%ED%8A%B8-%EB%B3%B8%EB%AC%B8
        for the event message schema.

        :return: An empty string to acknowledge the notification.
        :rtype: str
        """
        event_data = request.get_json_data()
        _logger.info(
            "Webhook event received from Toss Payments with data:\n%s", pprint.pformat(event_data)
        )
        event_type = event_data.get('eventType')
        if event_type in const.HANDLED_WEBHOOK_EVENTS:
            payment_data = event_data.get('data')
            tx_sudo = (
                request.env['payment.transaction']
                .sudo()
                ._search_by_reference('toss_payments', payment_data)
            )
            if tx_sudo:
                self._verify_signature(payment_data, tx_sudo)
                tx_sudo._process('toss_payments', payment_data)
        return request.make_json_response('')

    @staticmethod
    def _verify_signature(payment_data, tx_sudo):
        """Check that the received payment data's secret key matches the transaction's secret key.

        :param dict payment_data: The payment data.
        :param payment.transaction tx_sudo: The sudoed transaction referenced by the payment data.
        :rtype: None
        :raise Forbidden: If the secret keys don't match.
        """
        # Expired events might not have a secret if we never initiated the payment flow. Also
        # aborted events have a secret, but our implementation would not capture the secret in the
        # case of API call validation error (see `_toss_payments_success_return`). In these two
        # cases, we skip the verification.
        if payment_data.get('status') in const.VERIFICATION_EXEMPT_STATUSES:
            return

        received_signature = payment_data.get('secret')
        if not received_signature:
            _logger.warning("Received notification with missing signature.")
            raise Forbidden

        expected_signature = tx_sudo.toss_payments_payment_secret or ''
        if not hmac.compare_digest(received_signature, expected_signature):
            _logger.warning("Received notification with invalid signature.")
            raise Forbidden
