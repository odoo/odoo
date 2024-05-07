import logging
from odoo.addons.pos_adyen.controllers.main import PosAdyenController
from odoo import fields
from odoo.http import request

_logger = logging.getLogger(__name__)


class PosSelfAdyenController(PosAdyenController):

    def _process_payment_response(self, data, adyen_pm_sudo):
        self_order_id = None
        try:
            self_order_id = PosAdyenController._get_additional_data_from_unparsed(data['SaleToPOIResponse']['PaymentResponse']['Response']['AdditionalResponse'], 'metadata.self_order_id')
        except KeyError:
            self_order_id = None

        if not self_order_id:
            return super()._process_payment_response(data, adyen_pm_sudo)

        order_sudo = request.env['pos.order'].sudo().search([('id', '=', self_order_id)], limit=1)
        if not order_sudo:
            _logger.warning('Received an Adyen event notification for the self order #%d that does not exist (anymore)', self_order_id)
            return request.make_json_response('[accepted]') # https://docs.adyen.com/point-of-sale/design-your-integration/choose-your-architecture/cloud/#guarantee

        order = order_sudo.sudo(False).with_user(order_sudo.session_id.config_id.self_ordering_default_user_id).with_company(order_sudo.session_id.config_id.company_id)

        payment_result = data['SaleToPOIResponse']['PaymentResponse']['Response']['Result']

        if payment_result == 'Success' and order.config_id.self_ordering_mode == 'kiosk':
            payment_amount = data['SaleToPOIResponse']['PaymentResponse']['PaymentResult']['AmountsResp']['AuthorizedAmount']
            card_type = data['SaleToPOIResponse']['PaymentResponse']['PaymentResult']['PaymentInstrumentData']['CardData']['PaymentBrand']
            transaction_id = data['SaleToPOIResponse']['PaymentResponse']['SaleData']['SaleTransactionID']['TransactionID']
            order.add_payment({
                'amount': payment_amount,
                'payment_date': fields.Datetime.now(),
                'payment_method_id': adyen_pm_sudo.id,
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
            order.config_id._notify('PAYMENT_STATUS', {
                'payment_result': payment_result,
                'data': {
                    'pos.order': order.read(order._load_pos_self_data_fields(order.config_id.id), load=False),
                    'pos.order.line': order.lines.read(order._load_pos_self_data_fields(order.config_id.id), load=False),
                }
            })
        return request.make_json_response('[accepted]') # https://docs.adyen.com/point-of-sale/design-your-integration/choose-your-architecture/cloud/#guarantee
