from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    cal_client_id = fields.Char(
        string="Client_id",
        default="",
        config_parameter="google_calendar_client_id",
    )
    cal_client_secret = fields.Char(
        string="Client_key",
        secret_parameter="google_calendar_client_secret",
    )

    cal_sync_paused = fields.Boolean(
        string="Google Synchronization Paused",
        config_parameter="google_calendar_sync_paused",
        help="Indicates if synchronization with Google Calendar is paused or not.",
    )
