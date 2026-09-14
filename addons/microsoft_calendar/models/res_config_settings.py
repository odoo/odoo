from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    cal_microsoft_client_id = fields.Char(
        string="Microsoft Client_id",
        default="",
        config_parameter="microsoft_calendar_client_id",
    )
    cal_microsoft_client_secret = fields.Char(
        string="Microsoft Client_key",
        secret_parameter="microsoft_calendar_client_secret",
    )

    cal_microsoft_sync_paused = fields.Boolean(
        string="Microsoft Synchronization Paused",
        config_parameter="microsoft_calendar_sync_paused",
        help="Indicates if synchronization with Outlook Calendar is paused or not.",
    )
