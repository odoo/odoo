from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_ge_withholding_gross_account_id = fields.Many2one(
        comodel_name='account.account',
        string="Gross Withholding Cost",
        help="Expense account of the gross withholding taxes the company bears on its payments.",
    )
