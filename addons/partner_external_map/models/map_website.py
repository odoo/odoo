# Copyright 2015 Akretion (Alexis de Lattre <alexis.delattre@akretion.com>)
# Copyright 2016 Akretion (Alexis de Lattre <alexis.delattre@akretion.com>)
# Copyright 2016 Pedro M. Baeza <pedro.baeza@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class MapWebsite(models.Model):
    _name = "map.website"
    _description = "Map Website"
    _order = "sequence, id"

    name = fields.Char(string="Map Website Name", required=True)
    address_url = fields.Char(
        string="URL that uses the address",
        help="In this URL, {ADDRESS} will be replaced by the address.",
    )
    lat_lon_url = fields.Char(
        string="URL that uses latitude and longitude",
        help="In this URL, {LATITUDE} and {LONGITUDE} will be replaced by "
        "the latitude and longitude (requires the module 'base_geolocalize')",
    )
    route_address_url = fields.Char(
        string="Route URL that uses the addresses",
        help="In this URL, {START_ADDRESS} and {DEST_ADDRESS} will be "
        "replaced by the start and destination addresses.",
    )
    route_lat_lon_url = fields.Char(
        string="Route URL that uses latitude and longitude",
        help="In this URL, {START_LATITUDE}, {START_LONGITUDE}, "
        "{DEST_LATITUDE} and {DEST_LONGITUDE} will be replaced by the "
        "latitude and longitude of the start and destination adresses "
        "(requires the module 'base_geolocalize').",
    )
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)
