from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    # ------------------
    # Fields declaration
    # ------------------

    withholding_tax_base_account_id = fields.Many2one(
        related="company_id.l10n_account_withholding_tax_config_id.withholding_tax_base_account_id",
        readonly=False,
    )
