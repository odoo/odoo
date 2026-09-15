from odoo import api, fields, models


class ResourceAsset(models.Model):
    _inherit = "resource.asset"

    lot_id = fields.Many2one(
        comodel_name="stock.lot",
        string="Serial",
        index="btree_not_null",
        copy=False,
        help="The inventory identity of this unit, when it entered through a receipt or a manufacturing order.",
    )
    location_id = fields.Many2one(
        comodel_name="stock.location",
        string="Stock Location",
        compute="_compute_location_id",
        store=True,
        index="btree_not_null",
        readonly=False,
        domain="[('usage', '=', 'internal')]",
        help="Where the asset is kept: its serial's location when it has one, set by hand otherwise.",
    )

    @api.depends("lot_id.location_id")
    def _compute_location_id(self):
        for asset in self:
            if asset.lot_id:
                asset.location_id = asset.lot_id.location_id
            else:
                asset.location_id = asset.location_id
