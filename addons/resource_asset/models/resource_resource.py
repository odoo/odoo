from odoo import api, fields, models


class ResourceResource(models.Model):
    _inherit = "resource.resource"

    asset_ids = fields.One2many(
        comodel_name="resource.asset",
        inverse_name="resource_id",
        string="Assets",
    )
    asset_id = fields.Many2one(
        comodel_name="resource.asset",
        compute="_compute_asset_id",
        store=True,
        index="btree_not_null",
    )

    @api.depends("asset_ids")
    def _compute_asset_id(self):
        for resource in self.with_context(active_test=False):
            resource.asset_id = resource.asset_ids[:1]

    def _on_custody_changed(self, role, changes, planned=False):
        super()._on_custody_changed(role, changes, planned=planned)
        self.with_context(active_test=False).asset_id._on_custody_changed(
            role, changes, planned=planned
        )
