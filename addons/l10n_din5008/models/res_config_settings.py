from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    has_position_column = fields.Boolean(
        related="company_id.report_config_id.has_position_column",
        readonly=False,
    )
