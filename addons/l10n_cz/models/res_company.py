from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    trade_registry = fields.Char()
    l10n_cz_tax_office_id = fields.Many2one(
        comodel_name="l10n_cz.tax_office",
        string="Tax Office (CZ)",
    )


class BaseDocumentLayout(models.TransientModel):
    _inherit = "base.document.layout"

    account_fiscal_country_id = fields.Many2one(
        related="company_id.account_fiscal_country_id"
    )
    company_registry = fields.Char(related="company_id.company_registry")
