from odoo import fields, models


class L10nRsEdiConfig(models.Model):
    _name = "l10n_rs_edi.config"
    _description = "A company's l10n rs edi configuration"
    _inherit = ["mixin.company.config"]

    l10n_rs_edi_demo_env = fields.Boolean(
        string="Use Demo Environment",
        default=True,
    )
