from odoo import models

from odoo.addons.resource_asset.fields import AssetIdentifier


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

    # The root reads these through the identifier rows; the vehicle holds them.
    license_plate = AssetIdentifier(
        identifier_code="plate",
        store=True,
    )
    vin_sn = AssetIdentifier(
        identifier_code="vin",
        store=True,
    )
    engine_sn = AssetIdentifier(
        identifier_code="engine",
        store=True,
    )
