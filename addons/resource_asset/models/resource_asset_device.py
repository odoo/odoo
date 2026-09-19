from odoo import models

from odoo.addons.resource_asset.fields import AssetIdentifier


class ResourceAssetDevice(models.Model):
    _name = "resource.asset.device"
    _description = "Device"
    _inherit = ["resource.asset"]
    _table = "resource_asset_device"

    imei = AssetIdentifier(
        identifier_code="imei",
        string="IMEI",
        help="International Mobile Equipment Identity of a cellular-capable asset.",
    )
