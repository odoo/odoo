from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    geoloc_provider_id = fields.Many2one(
        comodel_name="geocoder.provider",
        string="API",
        default=lambda x: x.env["geocoder"]._get_provider(),
        config_parameter="geocoding.geo_provider",
    )
    geoloc_provider_techname = fields.Char(
        related="geoloc_provider_id.tech_name",
        readonly=True,
    )
    geoloc_provider_googlemap_key = fields.Char(
        string="Google Map API Key",
        secret_parameter="geocoding.google_map_api_key",
        help="Visit https://developers.google.com/maps/documentation/geocoding/get-api-key for more information.",
    )
