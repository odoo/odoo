from odoo import fields, models


class ResourceResource(models.Model):
    _inherit = "resource.resource"

    asset_id = fields.One2one(
        comodel_name="resource.asset",
        inverse_name="resource_id",
        context={"active_test": False},
    )

    def _on_custody_changed(self, role, changes, planned=False):
        super()._on_custody_changed(role, changes, planned=planned)
        self.asset_id._on_custody_changed(role, changes, planned=planned)
