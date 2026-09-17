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
        """Stored, because everything asks a resource what it is: the slot
        engine, the room kiosk and the record rules of both. Derived from the
        other table on read, it costs one query per record, and the engine reads
        it one record at a time."""
        for resource in self.with_context(active_test=False):
            resource.asset_id = resource.asset_ids[:1]
