# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _


class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    adyen_merchant_account = fields.Char(help='The POS merchant account code used in Adyen')

    @api.model
    def cancel_authorization(self, reference, test_mode, api_key, merchant_account):
        self.proxy_adyen_request({
            'merchantAccount': merchant_account,
            'originalReference': reference,
        }, test_mode, api_key, test_endpoint='https://pal-test.adyen.com/pal/servlet/Payment/v46/cancel', live_endpoint='https://pal-live.adyen.com/pal/servlet/Payment/v46/cancel')

        return True
