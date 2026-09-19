from odoo import models

from odoo.addons.resource_asset.fields import AssetIdentifier


class ResourceAssetTelecom(models.Model):
    _name = "resource.asset.telecom"
    _description = "Telecom"
    _inherit = ["resource.asset"]
    _table = "resource_asset_telecom"

    serial_number = AssetIdentifier(
        identifier_code="serial",
        string="Serial Number",
    )
    imei = AssetIdentifier(
        identifier_code="imei",
        string="IMEI",
        help="International Mobile Equipment Identity of a cellular-capable asset.",
    )
