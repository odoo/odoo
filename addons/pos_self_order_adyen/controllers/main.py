from odoo.addons.pos_adyen.controllers.main import PosAdyenController
from odoo import fields
from odoo.http import request


class PosSelfAdyenController(PosAdyenController):

    def _process_payment_response(self, data, adyen_pm_sudo):
        self_order_id = None
        try:
            self_order_id = PosAdyenController._get_additional_data_from_unparsed(data['SaleToPOIResponse']['PaymentResponse']['Response']['AdditionalResponse'], 'metadata.self_order_id')
        except KeyError:
            self_order_id = None

        order_sudo = request.env['pos.order'].sudo().search([('id', '=', self_order_id)], limit=1) if self_order_id else None
        if not order_sudo:
            return super()._process_payment_response(data, adyen_pm_sudo)

        payment_result = data['SaleToPOIResponse']['PaymentResponse']['Response']['Result']

        if payment_result == 'Success' and order_sudo.config_id.self_ordering_mode == 'kiosk':
            payment_amount = data['SaleToPOIResponse']['PaymentResponse']['PaymentResult']['AmountsResp']['AuthorizedAmount']
            card_type = data['SaleToPOIResponse']['PaymentResponse']['PaymentResult']['PaymentInstrumentData']['CardData']['PaymentBrand']
            transaction_id = data['SaleToPOIResponse']['PaymentResponse']['SaleData']['SaleTransactionID']['TransactionID']
            order_sudo.add_payment({
                'amount': payment_amount,
                'payment_date': fields.Datetime.now(),
                'payment_method_id': adyen_pm_sudo.id,
                'card_type': card_type,
                'cardholder_name': '',
                'transaction_id': transaction_id,
                'payment_status': payment_result,
                'ticket': '',
                'pos_order_id': order_sudo.id
            })
            order_sudo.action_pos_order_paid()
            order_sudo._send_order()

        if order_sudo.config_id.self_ordering_mode == 'kiosk':
            request.env['bus.bus']._sendone(f'pos_config-{order_sudo.config_id.access_token}', 'PAYMENT_STATUS', {
                'payment_result': payment_result,
                'order': order_sudo._export_for_self_order(),
            })
        return request.make_json_response('[accepted]') # https://docs.adyen.com/point-of-sale/design-your-integration/choose-your-architecture/cloud/#guarantee
