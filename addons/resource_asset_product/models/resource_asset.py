from odoo import api, fields, models


class ResourceAsset(models.Model):
    _inherit = "resource.asset"

    product_id = fields.Many2one(
        comodel_name="product.product",
        string="Model",
        index="btree_not_null",
        domain="[('asset_kind_id', '!=', False)]",
        help="The model this unit is an instance of. Its template carries the spec sheet.",
    )
    product_tmpl_id = fields.Many2one(
        related="product_id.product_tmpl_id",
        store=True,
    )
    log_ids = fields.One2many(
        comodel_name="resource.asset.log",
        inverse_name="asset_id",
    )
    part_ids = fields.One2many(
        comodel_name="resource.asset.part",
        inverse_name="asset_id",
        string="Parts",
        domain=[("state", "in", ("installed", "removed"))],
    )
    part_flagged_count = fields.Integer(
        string="Flagged Parts",
        compute="_compute_part_flagged_count",
    )
    kind_id = fields.Many2one(
        compute="_compute_kind_id",
        precompute=True,
        store=True,
        readonly=False,
    )

    @api.depends("product_id.asset_kind_id")
    def _compute_kind_id(self):
        for asset in self:
            if asset.product_id.asset_kind_id:
                asset.kind_id = asset.product_id.asset_kind_id

    def _compute_part_flagged_count(self):
        counts = dict(
            self.env["resource.asset.part"]._read_group(
                [("asset_id", "in", self.ids), ("review_state", "=", "flagged")],
                ["asset_id"],
                ["__count"],
            )
        )
        for asset in self:
            asset.part_flagged_count = counts.get(asset, 0)

    def action_view_parts(self):
        return self._get_parts_action({"search_default_current": 1})

    def action_view_flagged_parts(self):
        return self._get_parts_action({"search_default_flagged": 1})

    def _get_parts_action(self, context):
        self.check_singleton()
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "resource_asset_product.action_resource_asset_part"
        )
        action["domain"] = [("asset_id", "=", self.id)]
        action["context"] = {"default_asset_id": self.id, **context}
        return action

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("product_id") and not vals.get("kind_id"):
                product = self.env["product.product"].browse(vals["product_id"])
                if product.asset_kind_id:
                    vals["kind_id"] = product.asset_kind_id.id
        return super().create(vals_list)
