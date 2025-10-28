from odoo import fields, models


class AccountAccount(models.Model):
    _inherit = 'account.account'

    withhold_tax_ids = fields.Many2many(
        comodel_name='account.tax',
        string='Withholding Taxes',
        domain=[('is_withholding_tax_on_payment', '=', True)],
    )
