from odoo import fields, models


class MaintenancePlan(models.Model):
    _inherit = "maintenance.plan"

    asset_id = fields.Many2one(
        comodel_name="resource.asset",
        index="btree_not_null",
        ondelete="restrict",
        check_company=True,
        tracking=True,
    )
    block_asset = fields.Boolean(
        default=True,
        help="Each request of this plan blocks the asset's time while it is scheduled.",
    )

    def _prepare_request_vals(self, occurrence, previous=None):
        vals = super()._prepare_request_vals(occurrence, previous)
        if self.asset_id:
            vals["asset_id"] = self.asset_id.id
            vals["block_asset"] = self.block_asset
        return vals
