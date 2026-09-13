from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    portal_allow_api_keys = fields.Boolean(
        string="Customer API Keys",
        config_parameter="portal.allow_api_keys",
    )
