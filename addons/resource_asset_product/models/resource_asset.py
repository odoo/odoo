from odoo import api, fields, models


class ResourceAsset(models.Model):
    _inherit = "resource.asset"

    product_id = fields.Many2one(
        comodel_name="product.product",
        string="Model",
        help="The model this unit is an instance of. Its template carries the spec sheet.",
        index="btree_not_null",
        domain="[('asset_kind_id', '!=', False)]",
    )
    product_tmpl_id = fields.Many2one(
        related="product_id.product_tmpl_id",
        store=True,
    )
    kind_id = fields.Many2one(
        compute="_compute_kind_id",
        store=True,
        readonly=False,
    )

    @api.depends("product_id.asset_kind_id")
    def _compute_kind_id(self):
        for asset in self:
            if asset.product_id.asset_kind_id:
                asset.kind_id = asset.product_id.asset_kind_id

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("product_id") and not vals.get("kind_id"):
                product = self.env["product.product"].browse(vals["product_id"])
                if product.asset_kind_id:
                    vals["kind_id"] = product.asset_kind_id.id
        return super().create(vals_list)
