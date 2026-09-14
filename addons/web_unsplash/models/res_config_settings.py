from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    unsplash_access_key = fields.Char(
        string="Access Key",
        secret_parameter="unsplash.access_key",
    )
    unsplash_app_id = fields.Char(
        string="Application ID",
        config_parameter="unsplash.app_id",
    )
