from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    l10n_ar_tax_base_account_id = fields.Many2one(
        comodel_name="account.account",
        related="company_id.l10n_ar_tax_base_account_id",
        string="Tax Base Account",
        readonly=False,
        help="Account that will be set on lines created to represent the tax base amounts.",
    )
