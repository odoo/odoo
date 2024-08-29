from odoo import models, fields
from odoo.addons import base


class ResConfigSettings(models.TransientModel, base.ResConfigSettings):

    google_places_api_key = fields.Char(
        string='Google Places API Key',
        related='website_id.google_places_api_key',
        readonly=False)
