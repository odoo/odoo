# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    def _get_adyen_endpoints(self):
        return {
            **super(PosPaymentMethod, self)._get_adyen_endpoints(),
            'adjust': 'https://pal-%s.adyen.com/pal/servlet/Payment/v52/adjustAuthorisation',
            'capture': 'https://pal-%s.adyen.com/pal/servlet/Payment/v52/capture',
        }

    @api.model
    def _load_pos_data_fields(self, config_id):
        params = super()._load_pos_data_fields(config_id)
        params += ['terminal_merchant_key']
        return params
