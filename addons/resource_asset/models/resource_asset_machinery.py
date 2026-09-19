from odoo import models

from odoo.addons.resource_asset.fields import AssetIdentifier


class ResourceAssetMachinery(models.Model):
    _name = "resource.asset.machinery"
    _description = "Machinery"
    _inherit = ["resource.asset"]
    _table = "resource_asset_machinery"

    serial_number = AssetIdentifier(
        identifier_code="serial",
        string="Serial Number",
    )
