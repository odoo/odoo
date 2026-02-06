from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    ram_google_places_api_key = fields.Char(
        string="Google Places API Key",
        config_parameter="ram_webiste.google_places_api_key",
    )
    ram_google_place_id = fields.Char(
        string="Google Place ID",
        config_parameter="ram_webiste.google_place_id",
    )
    ram_google_reviews_language = fields.Char(
        string="Google Reviews Language",
        default="en",
        config_parameter="ram_webiste.google_reviews_language",
        help="Language code for Google Reviews (e.g., en, ja).",
    )
    ram_google_reviews_max = fields.Integer(
        string="Max Reviews to Import",
        default=12,
        config_parameter="ram_webiste.google_reviews_max",
    )

    def action_ram_sync_google_reviews(self):
        return self.env["ram.website.review"].action_sync_google_reviews()

