from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    google_gmail_client_identifier = fields.Char(
        string="Gmail Client Id",
        config_parameter="google_gmail_client_id",
    )
    google_gmail_client_secret = fields.Char(
        string="Gmail Client Secret",
        secret_parameter="google_gmail_client_secret",
    )
