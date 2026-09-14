from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    google_places_api_key = fields.Char(
        string="Google Places API Key",
        readonly=False,
        secret_parameter="google_address_autocomplete.google_places_api_key",
    )
