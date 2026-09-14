from odoo import fields, models


class ResourceAsset(models.Model):
    _name = "resource.asset"
    _inherit = ["resource.asset", "mixin.maintenance"]

    maintenance_ids = fields.One2many(
        comodel_name="maintenance.request",
        inverse_name="asset_id",
    )

    def action_view_maintenance(self):
        self.check_singleton()
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "maintenance.hr_equipment_request_action"
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
        first_stage = self.env["maintenance.stage"].sudo().search([], limit=1)
        in_progress = (
            self.env["maintenance.request"]
            .sudo()
            .search(
                [
                    ("asset_id", "in", self.ids),
                    ("archive", "=", False),
                    ("stage_id.done", "=", False),
                    ("stage_id", "!=", first_stage.id),
                ]
            )
        )
        busy_ids = set(in_progress.asset_id.ids)
        assets = self.sudo()
        assets.filtered(
            lambda asset: asset.id in busy_ids and asset.state == "in_service"
        ).write({"state": "maintenance"})
        assets.filtered(
            lambda asset: asset.id not in busy_ids and asset.state == "maintenance"
        ).write({"state": "in_service"})
