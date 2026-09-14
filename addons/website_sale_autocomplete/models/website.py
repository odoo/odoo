from odoo import fields, models


class Website(models.Model):
    _inherit = "website"
    _CREDENTIAL_FIELDS = {"google_places_api_key": "google_places_api_key"}

    google_places_api_key = fields.Char(
        string="Google Places API Key",
        compute="_compute_credential_doors",
        inverse="_inverse_credential_doors",
        copy=True,
        groups="base.group_system",
    )

    def has_google_places_api_key(self):
        return bool(self.sudo().google_places_api_key)
