from odoo import api, fields, models


class StockLot(models.Model):
    _inherit = "stock.lot"

    asset_id = fields.Many2one(
        comodel_name="resource.asset",
        compute="_compute_asset_id",
        store=True,
        index="btree_not_null",
        copy=False,
        readonly=False,
    )

    _asset_uniq = models.UniqueIndex(
        "(asset_id) WHERE asset_id IS NOT NULL", "A lot is one asset at most."
    )

    @api.depends("product_id.asset_kind_id")
    def _compute_asset_id(self):
        for lot in self:
            lot.asset_id = lot.asset_id

    @api.model_create_multi
    def create(self, vals_list):
        lots = super().create(vals_list)
        lots.filtered(
            lambda lot: lot.product_id.asset_kind_id and not lot.asset_id
        )._create_asset()
        return lots

    def _prepare_asset_vals(self):
        self.check_singleton()
        return {
            "name": f"{self.product_id.name} {self.name}",
            "product_id": self.product_id.id,
            "kind_id": self.product_id.asset_kind_id.id,
            "company_id": self.company_id.id,
            "lot_id": self.id,
        }

    def _create_asset(self):
        """The asset is a consequence of the serial, not an act of the user who
        receives it: a stock user with no asset rights still gets one."""
        if not self:
            return self.env["resource.asset"]
        assets = (
            self.env["resource.asset"]
            .sudo()
            .create([lot._prepare_asset_vals() for lot in self])
        )
        for lot, asset in zip(self, assets, strict=True):
            lot.sudo().asset_id = asset
        return assets.with_env(self.env)

    def action_view_asset(self):
        self.check_singleton()
        return {
            "type": "ir.actions.act_window",
            "res_model": "resource.asset",
            "res_id": self.asset_id.id,
            "view_mode": "form",
            "target": "current",
        }
