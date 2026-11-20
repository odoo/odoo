from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    google_places_api_key = fields.Char(
        string='Google Places API Key',
        related='website_id.google_places_api_key',
        readonly=False)
