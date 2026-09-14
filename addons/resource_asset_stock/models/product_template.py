from odoo import api, models
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = "product.template"

    @api.constrains("asset_kind_id", "tracking", "is_storable")
    def _check_asset_kind_tracking(self):
        for template in self:
            if (
                template.asset_kind_id
                and template.is_storable
                and template.tracking != "serial"
            ):
                raise ValidationError(
                    self.env._(
                        "%(name)s: a storable product whose units are assets must be tracked by unique serial number, so that each unit is one asset.",
                        name=template.name,
                    )
                )

    def write(self, vals):
        untyped = (
            self.filtered(lambda template: not template.asset_kind_id)
            if "asset_kind_id" in vals
            else self.browse()
        )
        res = super().write(vals)
        untyped.filtered("asset_kind_id")._create_missing_assets()
        return res

    def _create_missing_assets(self):
        if not self:
            return self.env["resource.asset"]
        lots = (
            self.env["stock.lot"]
            .sudo()
            .search(
                [
                    ("product_id.product_tmpl_id", "in", self.ids),
                    ("asset_id", "=", False),
                ]
            )
        )
        return lots._create_asset().with_env(self.env)
