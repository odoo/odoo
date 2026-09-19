from odoo import models

from odoo.addons.resource_asset.fields import AssetIdentifier


class ResourceAssetEquipment(models.Model):
    _name = "resource.asset.equipment"
    _description = "Equipment"
    _inherit = ["resource.asset"]
    _table = "resource_asset_equipment"

    serial_number = AssetIdentifier(
        identifier_code="serial",
        string="Serial Number",
    )
