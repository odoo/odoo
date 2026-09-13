from odoo import fields, models


class AccountTax(models.Model):
    _inherit = "account.tax"

    l10n_hr_tax_category_id = fields.Many2one(
        comodel_name="l10n.hr.tax.category",
        string="Croatian Tax Expence Category",
    )


class l10nHrTaxCategory(models.Model):
    _name = "l10n.hr.tax.category"
    _description = "Croatian tax expence categories"

    name = fields.Char(
        string="Name/Mark",
        required=True,
    )
    code_untdid = fields.Char(string="UNTDID code")
    code_hr = fields.Char(string="HR tax category code")
    code_tax_scheme = fields.Char(string="UNTDID tax scheme code")
    category_name = fields.Char(string="Categody code name")
    description = fields.Char()
