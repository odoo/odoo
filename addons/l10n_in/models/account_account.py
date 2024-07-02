from odoo import fields, models


class AccountAccount(models.Model):
    _inherit = 'account.account'

    fiscal_country_code = fields.Char(related="company_id.account_fiscal_country_id.code")
    l10n_in_tds_tcs_section = fields.Many2one('account.tax.group', string="TCS/TDS Section", domain="[('l10n_in_tax_source_type', 'in', ['tcs', 'tds'])]")
