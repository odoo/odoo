from odoo import fields, models


class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    l10n_us_bank_account_type = fields.Selection(
        selection=[
            ('checking', 'Checking'),
            ('savings', 'Savings'),
        ],
        string='Bank Account Type',
        default='checking',
        required=True
    )
