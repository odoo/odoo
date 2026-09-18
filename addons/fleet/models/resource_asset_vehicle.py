from odoo import models


class ResourceAssetVehicle(models.Model):
    """A vehicle is an asset whose rows live in their own table.

    Everything a vehicle is remains declared on `resource.asset`, so a
    reference held as `resource.asset` still reads and writes it: PostgreSQL's
    SELECT, UPDATE and DELETE on a parent reach the children unless told ONLY.
    What this model buys is a place to put what only vehicles have -- access
    rights, record rules, views, actions and, later, columns no other kind
    carries.
    """

    _name = "resource.asset.vehicle"
    _description = "Vehicle"
    _inherit = ["resource.asset"]
    _table = "resource_asset_vehicle"
