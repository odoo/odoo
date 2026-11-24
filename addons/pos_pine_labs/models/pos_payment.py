from odoo import api, fields, models


class PosPayment(models.Model):
    _inherit = 'pos.payment'

    pine_labs_plutus_transaction_ref = fields.Char(
        string='PineLabs Transaction ID',
        help='Required during the refund order process: https://developer.pinelabs.com/in/instore/cloud-integration#Example-JSON-request-for-Void-ICB-on-UPI-transaction')
    pine_labs_signature = fields.Char(
        string='Pine Labs Signature',
        copy=False,
        help='Proves that the Pine Labs transaction was requested for this payment reference and amount')

    @api.model
    def _get_additional_payment_fields(self):
        return super()._get_additional_payment_fields() + ['pine_labs_plutus_transaction_ref', 'pine_labs_signature']
