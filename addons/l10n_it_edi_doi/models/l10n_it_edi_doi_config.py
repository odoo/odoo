from odoo import fields, models


class L10nItEdiDoiConfig(models.Model):
    _name = "l10n_it_edi_doi.config"
    _description = "A company's l10n it edi doi configuration"
    _inherit = ["mixin.company.config"]

    l10n_it_edi_doi_tax_id = fields.Many2one(
        comodel_name="account.tax",
        string="Declaration of Intent Tax",
    )
    l10n_it_edi_doi_fiscal_position_id = fields.Many2one(
        comodel_name="account.fiscal.position",
        string="Declaration of Intent Fiscal Position",
    )
