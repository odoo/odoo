# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    geoloc_provider_id = fields.Many2one(
        'base.geo_provider',
        string='API',
        config_parameter='base_geolocalize.geo_provider',
        default=lambda x: x.env['base.geocoder']._get_provider()
    )
    geoloc_provider_techname = fields.Char(related='geoloc_provider_id.tech_name', readonly=True)
    geoloc_provider_googlemap_key = fields.Char(
        string='Google Map API Key',
        config_parameter='base_geolocalize.google_map_api_key',
        help="Visit https://developers.google.com/maps/documentation/geocoding/get-api-key for more information."
    )
