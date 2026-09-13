from odoo import fields, models


class ResourceAsset(models.Model):
    _inherit = "resource.asset"

    lot_id = fields.Many2one(
        comodel_name="stock.lot",
        string="Serial",
        help="The inventory identity of this unit, when it entered through a receipt or a manufacturing order.",
        index="btree_not_null",
        copy=False,
    )
    location_id = fields.Many2one(
        related="lot_id.location_id",
        string="Stock Location",
    )
