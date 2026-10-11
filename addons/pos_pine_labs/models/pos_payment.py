from odoo import api, fields, models


class PosPayment(models.Model):
    _inherit = 'pos.payment'

    pine_labs_plutus_transaction_ref = fields.Char(
        string='PineLabs Transaction ID',
        help='Required during the refund order process: https://developer.pinelabs.com/in/instore/cloud-integration#Example-JSON-request-for-Void-ICB-on-UPI-transaction')

    @api.model
    def _get_additional_payment_fields(self):
        return super()._get_additional_payment_fields() + ['pine_labs_plutus_transaction_ref']
