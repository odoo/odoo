from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    microsoft_outlook_client_identifier = fields.Char(
        string="Outlook Client Id",
        config_parameter="microsoft_outlook_client_id",
    )
    microsoft_outlook_client_secret = fields.Char(
        string="Outlook Client Secret",
        compute="_compute_microsoft_outlook_client_secret",
        inverse="_inverse_microsoft_outlook_client_secret",
    )

    def _compute_microsoft_outlook_client_secret(self):
        secret = self.env["credential.credential"]._get_system_secret(
            "microsoft_outlook_client_secret"
        )
        for settings in self:
            settings.microsoft_outlook_client_secret = secret

    def _inverse_microsoft_outlook_client_secret(self):
        for settings in self:
            self.env["credential.credential"]._set_system_secret(
                "microsoft_outlook_client_secret",
                settings.microsoft_outlook_client_secret,
            )
