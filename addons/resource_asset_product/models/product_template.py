from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    asset_kind_id = fields.Many2one(
        comodel_name="resource.asset.kind",
        change_default=True,
        help="Set when each unit of this product is an asset in its own right: a vehicle, a machine, a phone. Empty for consumables and parts.",
    )
    asset_kind_code = fields.Char(related="asset_kind_id.code")
    asset_count = fields.Integer(compute="_compute_asset_count")

    def _compute_asset_count(self):
        counts = dict(
            self.env["resource.asset"]._read_group(
                [("product_tmpl_id", "in", self.ids)],
                ["product_tmpl_id"],
                ["__count"],
            )
        )
        for template in self:
            template.asset_count = counts.get(template, 0)

    def action_view_assets(self):
        self.check_singleton()
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "resource_asset.action_resource_asset"
        )
        action["domain"] = [("product_tmpl_id", "=", self.id)]
        action["context"] = {
            "default_product_id": self.product_variant_id.id,
            "default_kind_id": self.asset_kind_id.id,
        }
        return action
