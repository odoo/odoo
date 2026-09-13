from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    events_app_name = fields.Char(
        related="website_id.events_app_name",
        string="Events App Name",
        readonly=False,
    )
