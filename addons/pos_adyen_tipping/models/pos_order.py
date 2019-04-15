# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _


class PosOrder(models.Model):
    _inherit = 'pos.order'

    def _set_tip_amount(self):
        res = super(PosOrder, self)._set_tip_amount()

        for order in self:
            payment = order.payment_ids.filtered(lambda payment: payment.payment_method_id.use_payment_terminal == 'adyen')[0]
            payment_method = payment.payment_method_id
            payment_method.proxy_adyen_request({
                'merchantAccount': payment_method.adyen_merchant_account,
                'originalReference': payment.transaction_id,
                'modificationAmount': {
                    'currency': payment.currency_id.name,
                    'value': round(order.amount_total * 100)  # tip will already be included by super
                }
            }, payment_method.adyen_test_mode, payment_method.adyen_api_key, test_endpoint='https://pal-test.adyen.com/pal/servlet/Payment/v46/capture', live_endpoint='https://pal-live.adyen.com/pal/servlet/Payment/v46/capture')

        return res
