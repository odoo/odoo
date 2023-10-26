import json
from odoo.addons.pos_adyen.controllers.main import PosAdyenController
from odoo import http, fields
from odoo.http import request


class PosSelfAdyenController(PosAdyenController):
    @http.route()
    def notification(self):
        super().notification()

        data = json.loads(request.httprequest.data)
        if data.get('SaleToPOIResponse'):
            order_reference = data['SaleToPOIResponse']['PaymentResponse']['SaleData']['SaleTransactionID']['TransactionID']
            payment_result = data['SaleToPOIResponse']['PaymentResponse']['Response']['Result']
            order_sudo = request.env['pos.order'].sudo().search([('pos_reference', '=', order_reference)], limit=1)
            order = order_sudo.sudo(False).with_user(order_sudo.session_id.config_id.self_ordering_default_user_id).with_company(order_sudo.session_id.config_id.company_id)
            terminal_identifier = data['SaleToPOIResponse']['MessageHeader']['POIID']
            payment_method = request.env['pos.payment.method'].sudo().search([('adyen_terminal_identifier', '=', terminal_identifier)], limit=1)

            if payment_result == 'Success' and order.config_id.self_ordering_mode == 'kiosk':
                payment_amount = data['SaleToPOIResponse']['PaymentResponse']['PaymentResult']['AmountsResp']['AuthorizedAmount']
                card_type = data['SaleToPOIResponse']['PaymentResponse']['PaymentResult']['PaymentInstrumentData']['CardData']['PaymentBrand']
                transaction_id = data['SaleToPOIResponse']['PaymentResponse']['SaleData']['SaleTransactionID']['TransactionID']
                order.add_payment({
                    'amount': payment_amount,
                    'payment_date': fields.Datetime.now(),
                    'payment_method_id': payment_method.id,
                    'card_type': card_type,
                    'cardholder_name': '',
                    'transaction_id': transaction_id,
                    'payment_status': payment_result,
                    'ticket': '',
                    'pos_order_id': order.id
                })
                order.action_pos_order_paid()
                order._send_order()

            if order.config_id.self_ordering_mode == 'kiosk':
                order.env['bus.bus']._sendone(f'pos_config-{order.config_id.access_token}', 'PAYMENT_STATUS', {
                    'payment_result': payment_result,
                    'order': order._export_for_self_order(),
                })
