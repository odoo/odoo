from odoo import api, fields, models


class PosPaymentProvider(models.Model):
    _inherit = "pos.payment.provider"

    adyen_merchant_account = fields.Char(help='The POS merchant account code used in Adyen', copy=False)

    @api.model
    def _load_pos_data_fields(self, config_id):
        params = super()._load_pos_data_fields(config_id)
        params += ['adyen_merchant_account']
        return params
