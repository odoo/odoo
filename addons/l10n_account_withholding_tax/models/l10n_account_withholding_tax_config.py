from odoo import fields, models


class L10nAccountWithholdingTaxConfig(models.Model):
    _name = "l10n_account_withholding_tax.config"
    _description = "A company's l10n account withholding tax configuration"
    _inherit = ["mixin.company.config"]

    withholding_tax_base_account_id = fields.Many2one(
        comodel_name="account.account",
        string="Withholding Tax Base",
        help="This account will be set on withholding tax base lines.",
    )
