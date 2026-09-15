from odoo import fields, models


class ResourceAsset(models.Model):
    _name = "resource.asset"
    _inherit = ["resource.asset", "mixin.maintenance"]

    maintenance_ids = fields.One2many(
        comodel_name="maintenance.order",
        inverse_name="asset_id",
    )
    maintenance_plan_ids = fields.One2many(
        comodel_name="maintenance.plan",
        inverse_name="asset_id",
    )
    maintenance_plan_count = fields.Count(count_of="maintenance_plan_ids")

    def action_view_maintenance(self):
        self.check_singleton()
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "maintenance.maintenance_order_action"
        )
        action["domain"] = [("asset_id", "=", self.id)]
        action["context"] = {
            "default_asset_id": self.id,
            "default_company_id": self.company_id.id,
        }
        return action

    def action_view_maintenance_plans(self):
        self.check_singleton()
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "maintenance.maintenance_plan_action"
        )
        action["domain"] = [("asset_id", "=", self.id)]
        action["context"] = {
            "default_asset_id": self.id,
            "default_company_id": self.company_id.id,
        }
        return action

    def _sync_state_from_maintenance(self):
        if not self:
            return
        in_progress = (
            self.env["maintenance.order"]
            .sudo()
            .search([("asset_id", "in", self.ids), ("state", "=", "in_progress")])
        )
        busy_ids = set(in_progress.asset_id.ids)
        assets = self.sudo()
        assets.filtered(
            lambda asset: asset.id in busy_ids and asset.state == "in_service"
        ).write({"state": "maintenance"})
        assets.filtered(
            lambda asset: asset.id not in busy_ids and asset.state == "maintenance"
        ).write({"state": "in_service"})
