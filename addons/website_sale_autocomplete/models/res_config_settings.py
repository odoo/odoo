from odoo import fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    website_google_places_api_key = fields.Char(
        string="Website's Google Places API Key",
        related='website_id.google_places_api_key',
        readonly=False)
