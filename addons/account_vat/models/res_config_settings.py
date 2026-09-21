from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    vat_check_vies = fields.Boolean(
        related="company_id.account_config_id.vat_check_vies",
        string="Verify VAT Numbers",
        readonly=False,
    )
