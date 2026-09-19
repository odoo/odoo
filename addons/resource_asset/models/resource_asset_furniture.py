from odoo import models

from odoo.addons.resource_asset.fields import AssetIdentifier


class ResourceAssetFurniture(models.Model):
    _name = "resource.asset.furniture"
    _description = "Furniture"
    _inherit = ["resource.asset"]
    _table = "resource_asset_furniture"

    inventory_tag = AssetIdentifier(
        identifier_code="inventory",
        string="Inventory Tag",
    )
