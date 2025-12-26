from odoo import models, fields


class AccountTax(models.Model):
    _inherit = 'account.tax'

    l10n_hr_vat_expence_category_id = fields.Many2one('l10n.hr.vat.expence.category', string="VAT Expense Category")


class l10nHrVatExpenceCategory(models.Model):
    _name = 'l10n.hr.vat.expence.category'
    _description = 'Croatian VAT expence categories'

    name = fields.Char("Name/Mark", required=True)
    code_untdid = fields.Char("UNTDID code")
    code_hr = fields.Char("HR tax category code")
    code_tax_scheme = fields.Char("UNTDID tax scheme code")
    category_name = fields.Char("Categody code name")
    description = fields.Char("Description")
