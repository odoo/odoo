from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    google_gmail_client_identifier = fields.Char(
        string="Gmail Client Id",
        config_parameter="google_gmail_client_id",
    )
    google_gmail_client_secret = fields.Char(
        string="Gmail Client Secret",
        compute="_compute_google_gmail_client_secret",
        inverse="_inverse_google_gmail_client_secret",
    )

    def _compute_google_gmail_client_secret(self):
        secret = self.env["credential.credential"]._get_system_secret(
            "google_gmail_client_secret"
        )
        for settings in self:
            settings.google_gmail_client_secret = secret

    def _inverse_google_gmail_client_secret(self):
        for settings in self:
            self.env["credential.credential"]._set_system_secret(
                "google_gmail_client_secret", settings.google_gmail_client_secret
            )
