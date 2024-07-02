# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    google_places_api_key = fields.Char(
        string='Google Places API Key',
        readonly=False,
        config_parameter='google_address_autocomplete.google_places_api_key')
