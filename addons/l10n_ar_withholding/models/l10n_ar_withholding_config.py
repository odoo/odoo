from odoo import fields, models


class L10nArWithholdingConfig(models.Model):
    _name = "l10n_ar_withholding.config"
    _description = "A company's l10n ar withholding configuration"
    _inherit = ["mixin.company.config"]

    l10n_ar_tax_base_account_id = fields.Many2one(
        comodel_name="account.account",
        string="Tax Base Account",
        help="Account that will be set on lines created to represent the tax base amounts.",
    )
