from odoo import models

from odoo.addons.resource_asset.fields import AssetIdentifier


class ResourceAssetIt(models.Model):
    _name = "resource.asset.it"
    _description = "IT Equipment"
    _inherit = ["resource.asset"]
    _table = "resource_asset_it"

    serial_number = AssetIdentifier(
        identifier_code="serial",
        string="Serial Number",
    )
