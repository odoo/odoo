import base64

from odoo import http
from odoo.http import request
from odoo.addons.payment.logging import get_payment_logger
from odoo.exceptions import ValidationError

_logger = get_payment_logger(__name__)


class TossPaymentController(http.Controller):
    @http.route('/payment/tosspayments/success', type='http', auth='public')
    def handleValidationSuccess(self, **payment_data):
        """ Process payment after validation from Toss SDK is successful.

        This controller endpoint should be accessed via Toss SDK's successUrl redirection. The
        method handles payment usingToss API.

        :param dict payment_data: The dict data of successUrl's query parameter.
        Expected keys = ["orderId", "paymentKey", "amount"]
        """
        tx_sudo = request.env['payment.transaction'].sudo() \
            ._search_by_reference('tosspayments', payment_data)

        if not tx_sudo:
            reference = base64.b64decode(payment_data['orderId'])
            _logger.error("Cannot find matching payment trasaction using reference: %s", reference)
            return request.redirect('/payment/status')

        try:
            # Need payment_data validation before sending payment confirmation request because the
            # amount data can be manipulated from the client side.
            tx_sudo._validate_amount({'totalAmount': payment_data.get("amount")})
        except ValidationError as e:
            _logger.error("Amount validation error: %s", e)
            # Method '_validate_amount' set tx state to 'error' already.
            return request.redirect('/payment/status')

        try:
            res = tx_sudo._send_api_request('POST', '/v1/payments/confirm', json=payment_data)
        except ValidationError as e:
            _logger.error("Error while sending payment confirmation request: %s", e)
            tx_sudo._set_error(e)
            return request.redirect('/payment/status')

        tx_sudo._process('tosspayments', res)
        return request.redirect('/payment/status')

    @http.route('/payment/tosspayments/fail', type='http', auth='public')
    def handleValidationFail(self, **error_data):
        """ Handle unsuccessful validation from Toss SDK.

        :param dict error_data: The dict data of successUrl's query parameter.
        Expected keys = ["code", "message", "orderId"]
        """
        tx_sudo = request.env['payment.transaction'].sudo() \
            ._search_by_reference('tosspayments', error_data)

        if not tx_sudo:
            reference = base64.b64decode(error_data['orderId'])
            _logger.error("Cannot find matching payment trasaction using reference: %s", reference)
            return request.redirect('/payment/status')

        _logger.error(
            "Unsuccessful payment validation. Error code: %s, Error message: %s, Order ID: %s",
            error_data.get('code'),
            error_data.get('message'),
            error_data.get('orderId')
        )
        tx_sudo._set_error(error_data.get('message'))

        return request.redirect('/payment/status')
