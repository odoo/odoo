from odoo import fields, models


class L10nBrConfig(models.Model):
    _name = "l10n_br.config"
    _description = "A company's l10n br configuration"
    _inherit = ["mixin.company.config"]

    l10n_br_nire_code = fields.Char(
        string="NIRE",
        help="State Commercial Identification Number. Should contain 11 digits.",
    )
