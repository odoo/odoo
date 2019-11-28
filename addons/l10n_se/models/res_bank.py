from odoo import fields, models

class ResBank(models.Model):
    _inherit = 'res.bank'

    clearing_number = fields.Char(string='Clearing Number', help='Swedish Bank Clearing Number, 4 digits.')
    account_digits = fields.Integer(string='Account Numbers', help='Swedish Bank Account numbers.', default=0)
    account_padding = fields.Boolean(string='Account Padding', help='Swedish Bank Account Padding with 0 in front of account number.', default=False)
