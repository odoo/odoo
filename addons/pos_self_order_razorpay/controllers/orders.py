from odoo import http
from odoo.tools import consteq
from odoo.addons.pos_self_order.controllers.orders import PosSelfOrderController
from werkzeug.exceptions import Unauthorized


class PosSelfOrderControllerRazorpay(PosSelfOrderController):
    @http.route("/pos-self-order/razorpay-fetch-payment-status/", auth="public", type="jsonrpc", website=True)
    def razorpay_payment_status(self, access_token, order_id, payment_data, payment_method_id):
        pos_config = self._verify_pos_config(access_token)
        order = pos_config.env['pos.order'].search([
            ('id', '=', order_id), ('config_id', '=', pos_config.id), ('access_token', '=', payment_data.get('order_token'))
        ], limit=1)

        if not order:
            raise Unauthorized()

        payment_method = pos_config.env['pos.payment.method'].browse(payment_method_id)
        reference_id = payment_method._razorpay_get_reference_id(order)
        p2p_request_id = str(payment_data.get('p2pRequestId') or '')
        expected_signature = payment_method._razorpay_sign_transaction(p2p_request_id, reference_id)
        if not p2p_request_id or not consteq(str(payment_data.get('razorpay_signature') or ''), expected_signature):
            raise Unauthorized()
        razorpay_status_response = payment_method.razorpay_fetch_payment_status(payment_data)
        payment_status = razorpay_status_response.get('status')
        if payment_status == "AUTHORIZED":
            if not consteq(razorpay_status_response.get('externalRefNumber'), reference_id):
                raise Unauthorized()
            order.add_payment({
                'amount': order.amount_total,
                'payment_method_id': payment_method.id,
                'card_type': razorpay_status_response.get('paymentCardType'),
                'cardholder_name': razorpay_status_response.get('nameOnCard'),
                'transaction_id': razorpay_status_response.get('txnId'),
                'payment_status': razorpay_status_response.get('status'),
                'pos_order_id': order.id,
                'payment_method_authcode': razorpay_status_response.get('authCode'),
                'card_brand': razorpay_status_response.get('paymentCardBrand'),
                'payment_method_issuer_bank': razorpay_status_response.get('acquirerCode'),
                'card_no': razorpay_status_response.get('cardLastFourDigit'),
                'payment_method_payment_mode': razorpay_status_response.get('paymentMode'),
                'payment_ref_no': razorpay_status_response.get('externalRefNumber'),
                'razorpay_reverse_ref_no': razorpay_status_response.get('reverseReferenceNumber'),
            })

            order.action_pos_order_paid()

            if order.config_id.self_ordering_mode == 'kiosk':
                self.call_bus_service(order, payment_result='Success')
        elif payment_status == "FAILED" or not payment_status:
            self.call_bus_service(order, payment_result='fail')
        return razorpay_status_response

    @http.route("/pos-self-order/razorpay-cancel-transaction/", auth="public", type="jsonrpc", website=True)
    def razorpay_cancel_status(self, access_token, order_id, payment_data, payment_method_id):
        pos_config = self._verify_pos_config(access_token)
        order = pos_config.env['pos.order'].search([
            ('id', '=', order_id), ('config_id', '=', pos_config.id), ('access_token', '=', payment_data.get('order_token'))
        ], limit=1)

        if not order:
            raise Unauthorized()

        payment_method = pos_config.env['pos.payment.method'].browse(payment_method_id)
        razorpay_cancel_response = payment_method.razorpay_cancel_payment_request(payment_data)
        cancel_status = razorpay_cancel_response.get('status')
        if cancel_status:
            self.call_bus_service(order, payment_result='fail')
        return razorpay_cancel_response

    def call_bus_service(self, order, payment_result):
        order._send_payment_result(payment_result)
