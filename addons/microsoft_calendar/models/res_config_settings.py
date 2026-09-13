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
        compute="_compute_cal_microsoft_client_secret",
        inverse="_inverse_cal_microsoft_client_secret",
    )

    def _compute_cal_microsoft_client_secret(self):
        secret = self.env["credential.credential"]._get_system_secret(
            "microsoft_calendar_client_secret"
        )
        for settings in self:
            settings.cal_microsoft_client_secret = secret

    def _inverse_cal_microsoft_client_secret(self):
        for settings in self:
            self.env["credential.credential"]._set_system_secret(
                "microsoft_calendar_client_secret", settings.cal_microsoft_client_secret
            )

    cal_microsoft_sync_paused = fields.Boolean(
        string="Microsoft Synchronization Paused",
        config_parameter="microsoft_calendar_sync_paused",
        help="Indicates if synchronization with Outlook Calendar is paused or not.",
    )
