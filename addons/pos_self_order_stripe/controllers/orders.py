# -*- coding: utf-8 -*-
from odoo import http, fields
from odoo.http import request
from odoo.tools import float_is_zero
from odoo.addons.pos_self_order.controllers.orders import PosSelfOrderController
from werkzeug.exceptions import Unauthorized

class PosSelfOrderControllerStripe(PosSelfOrderController):
    @http.route("/pos-self-order/stripe-connection-token/", auth="public", type="jsonrpc", website=True)
    def get_stripe_creditentials(self, access_token, payment_method_id):
        # stripe_connection_token
        pos_config, _ = self._verify_authorization(access_token, "", {})
        payment_method = pos_config.payment_method_ids.filtered(lambda p: p.id == payment_method_id)
        return payment_method.stripe_connection_token()

    @http.route("/pos-self-order/stripe-capture-payment/", auth="public", type="jsonrpc", website=True)
    def stripe_capture_payment(self, access_token, order_access_token, payment_intent_id, payment_method_id):
        pos_config, _ = self._verify_authorization(access_token, "", {})
        stripe_confirmation = pos_config.env['pos.payment.method'].stripe_capture_payment(payment_intent_id)
        order = pos_config.env['pos.order'].search([('access_token', '=', order_access_token), ('config_id', '=', pos_config.id)])

        if not order:
            raise Unauthorized()

        payment_method = pos_config.payment_method_ids.filtered(lambda p: p.id == payment_method_id)
        stripe_order_amount = payment_method._stripe_calculate_amount(order.amount_total)

        if float_is_zero(stripe_order_amount - stripe_confirmation['amount'], precision_rounding=pos_config.currency_id.rounding) and stripe_confirmation['status'] == 'succeeded':
            transaction_id = stripe_confirmation['id']
            payment_result = stripe_confirmation['status']

            order.add_payment({
                'amount': order.amount_total,
                'payment_date': fields.Datetime.now(),
                'payment_method_id': payment_method.id,
                'card_type': False,
                'cardholder_name': '',
                'transaction_id': transaction_id,
                'payment_status': payment_result,
                'ticket': '',
                'pos_order_id': order.id
            })

            order.action_pos_order_paid()

            if order.config_id.self_ordering_mode == 'kiosk':
                order._send_payment_result('Success')
        else:
            order._send_payment_result('fail')
