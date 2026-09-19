from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"
    _inherits_sudo_fields = ("l10n_ca_pst",)


class BaseDocumentLayout(models.TransientModel):
    _inherit = "base.document.layout"

    l10n_ca_pst = fields.Char(
        related="company_id.l10n_ca_pst",
        readonly=True,
    )
    account_fiscal_country_id = fields.Many2one(
        related="company_id.account_config_id.account_fiscal_country_id",
        readonly=True,
    )
