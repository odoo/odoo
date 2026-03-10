from odoo import fields, models


class AccountAccount(models.Model):
    _inherit = 'account.account'

    withholding_tax_section_id = fields.Many2one(
        comodel_name='account.withholding.tax.section',
        string='Tax Section',
        check_company=True,
    )
