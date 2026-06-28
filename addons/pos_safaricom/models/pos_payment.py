from odoo import fields, models


class PosPayment(models.Model):
    _inherit = 'pos.payment'

    safaricom_transaction_id = fields.Char(string="Safaricom transaction id", required=False)
