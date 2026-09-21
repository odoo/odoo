from odoo import fields, models


class L10nCzConfig(models.Model):
    _name = "l10n_cz.config"
    _description = "A company's l10n cz configuration"
    _inherit = ["mixin.company.config"]

    trade_registry = fields.Char()
    l10n_cz_tax_office_id = fields.Many2one(
        comodel_name="l10n_cz.tax_office",
        string="Tax Office (CZ)",
    )
