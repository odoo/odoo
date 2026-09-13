from odoo import fields, models


class ResourceAsset(models.Model):
    _inherit = "resource.asset"

    workcenter_id = fields.Many2one(
        comodel_name="mrp.workcenter",
        string="Work Center",
        compute="_compute_workcenter_id",
    )

    def _compute_workcenter_id(self):
        workcenters = self.env["mrp.workcenter"].search([("asset_id", "in", self.ids)])
        by_asset = {wc.asset_id.id: wc for wc in workcenters}
        for asset in self:
            asset.workcenter_id = by_asset.get(asset.id)
