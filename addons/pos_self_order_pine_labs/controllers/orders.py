# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.tools import consteq
from odoo.addons.pos_self_order.controllers.orders import PosSelfOrderController
from werkzeug.exceptions import NotFound, Unauthorized


class PosSelfOrderPineLabsController(PosSelfOrderController):
    @http.route('/pos-self-order/pine-labs-fetch-payment-status/', auth='public', type='jsonrpc')
    def pine_labs_fetch_payment_status(self, access_token, order_id, payment_data, payment_method_id):
        pos_config = self._verify_pos_config(access_token)
        order = pos_config.env['pos.order'].search([
            ('id', '=', order_id), ('config_id', '=', pos_config.id), ('access_token', '=', payment_data.get('order_token'))
        ], limit=1)
        payment_method = pos_config.env['pos.payment.method'].browse(payment_method_id).exists()

        if not order or not payment_method or payment_method_id not in pos_config.payment_method_ids.ids:
            raise NotFound()

        # Pine Labs approves any valid Plutus reference, whatever order it was issued for. The signature
        # proves the reference was issued for this order and its current amount, so a reference from
        # another order, or from this order before its amount changed, is rejected.
        transaction_number = payment_method._pine_labs_get_transaction_number(order)
        plutus_transaction_ref = str(payment_data.get('plutusTransactionReferenceID') or '')
        expected_signature = payment_method._pine_labs_sign_transaction(plutus_transaction_ref, transaction_number)
        if not plutus_transaction_ref or not consteq(str(payment_data.get('pine_labs_signature') or ''), expected_signature):
            raise Unauthorized()

        pine_labs_status_response = payment_method.pine_labs_fetch_payment_status({
            'plutusTransactionReferenceID': plutus_transaction_ref,
        })
        if pine_labs_status_response.get('status') == "TXN APPROVED":
            data = pine_labs_status_response.get('data')
            # Reject duplicate status checks when the transaction has already been processed for this Plutus reference ID.
            if pos_config.env['pos.payment'].search_count([
                ('payment_method_id', '=', payment_method_id),
                ('pine_labs_plutus_transaction_ref', '=', plutus_transaction_ref),
                ('transaction_id', '=', data.get('TransactionLogId'))
            ]):
                raise Unauthorized()

            order.add_payment({
                'amount': order.amount_total,
                'payment_method_id': payment_method.id,
                'cardholder_name': data.get('Card Holder Name'),
                'transaction_id': data.get('TransactionLogId'),
                'payment_status': 'done',
                'pos_order_id': order.id,
                'payment_method_authcode': data.get('ApprovalCode'),
                'card_brand': data.get('Card Type'),
                'payment_method_issuer_bank': data.get('Acquirer Name'),
                'card_no': data.get('Card Number') and data.get('Card Number')[-4:],
                'payment_method_payment_mode': data.get('PaymentMode'),
                'payment_ref_no': transaction_number,
                'pine_labs_plutus_transaction_ref': pine_labs_status_response.get('plutusTransactionReferenceID'),
            })
            order.action_pos_order_paid()
            order._send_payment_result('Success')
        return pine_labs_status_response

    @http.route("/pos-self-order/pine-labs-cancel-transaction/", auth="public", type="jsonrpc")
    def pine_labs_cancel_transaction(self, access_token, order_id, payment_data, payment_method_id):
        pos_config = self._verify_pos_config(access_token)
        order = pos_config.env['pos.order'].search([
            ('id', '=', order_id), ('config_id', '=', pos_config.id), ('access_token', '=', payment_data.get('order_token'))
        ], limit=1)
        payment_method = pos_config.env['pos.payment.method'].browse(payment_method_id).exists()

        if not order or not payment_method or payment_method_id not in pos_config.payment_method_ids.ids:
            raise NotFound()

        return payment_method.pine_labs_cancel_payment_request(payment_data)
