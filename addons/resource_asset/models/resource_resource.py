from odoo import fields, models
from odoo.fields import Domain


class ResourceResource(models.Model):
    _inherit = "resource.resource"

    asset_id = fields.Many2one(
        comodel_name="resource.asset",
        compute="_compute_asset_id",
        search="_search_asset_id",
    )

    def _search_asset_id(self, operator, value):
        if operator not in ("in", "any"):
            return NotImplemented
        assets = (
            self.env["resource.asset"]
            .with_context(active_test=False)
            ._search(Domain("id", operator, value))
        )
        return Domain("id", "in", assets.subselect("resource_id"))

    def _compute_asset_id(self):
        assets = self.env["resource.asset"].search([("resource_id", "in", self.ids)])
        by_resource = {asset.resource_id.id: asset for asset in assets}
        for resource in self:
            resource.asset_id = by_resource.get(resource.id)
