from odoo import models

from odoo.addons.resource_asset.fields import AssetIdentifier


class ResourceAssetProperty(models.Model):
    _name = "resource.asset.property"
    _description = "Property"
    _inherit = ["resource.asset"]
    _table = "resource_asset_property"

    cadastral_id = AssetIdentifier(
        identifier_code="cadastral",
        string="Cadastral ID",
        help="Government-assigned parcel identifier for real estate assets.",
    )
