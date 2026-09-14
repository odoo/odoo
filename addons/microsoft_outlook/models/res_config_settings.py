from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    microsoft_outlook_client_identifier = fields.Char(
        string="Outlook Client Id",
        config_parameter="microsoft_outlook_client_id",
    )
    microsoft_outlook_client_secret = fields.Char(
        string="Outlook Client Secret",
        secret_parameter="microsoft_outlook_client_secret",
    )
