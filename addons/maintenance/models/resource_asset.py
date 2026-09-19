from odoo import fields, models

KIND_DEFAULTS = ("technician_user_id", "maintenance_team_id")


class ResourceAsset(models.Model):
    _inherit = "resource.asset"

    maintenance_ids = fields.Many2many(
        related="resource_id.maintenance_ids",
    )
    maintenance_count = fields.Integer(
        related="resource_id.maintenance_count",
    )
    maintenance_open_count = fields.Integer(
        related="resource_id.maintenance_open_count"
    )
    maintenance_plan_ids = fields.Many2many(related="resource_id.maintenance_plan_ids")
    maintenance_plan_count = fields.Integer(
        related="resource_id.maintenance_plan_count"
    )
    maintenance_team_id = fields.Many2one(
        related="resource_id.maintenance_team_id",
        readonly=False,
    )
    technician_user_id = fields.Many2one(
        related="resource_id.technician_user_id",
        readonly=False,
    )
    date_in_service = fields.Date(
        related="resource_id.date_in_service",
        readonly=False,
    )
    expected_mtbf = fields.Integer(
        related="resource_id.expected_mtbf",
        readonly=False,
    )
    mtbf = fields.Integer(related="resource_id.mtbf")
    mttr = fields.Integer(related="resource_id.mttr")
    date_next_failure = fields.Date(related="resource_id.date_next_failure")
    date_last_failure = fields.Date(related="resource_id.date_last_failure")

    def _on_kind_changed(self, vals):
        super()._on_kind_changed(vals)
        for asset in self:
            asset._take_kind_defaults(vals)

    def _take_kind_defaults(self, given):
        self.check_singleton()
        kind = self.kind_id
        resource_vals = {
            fname: kind[fname].id
            for fname in KIND_DEFAULTS
            if not given.get(fname) and kind[fname]
        }
        if resource_vals:
            self.resource_id.sudo().write(resource_vals)

    def _get_maintenance_action(self, xmlid):
        self.check_singleton()
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(xmlid)
        action["domain"] = [("resource_ids", "in", self.resource_id.ids)]
        action["context"] = {
            "default_resource_ids": self.resource_id.ids,
            "default_company_id": self.company_id.id,
        }
        return action

    def action_view_maintenance(self):
        return self._get_maintenance_action("maintenance.maintenance_order_action")

    def action_view_maintenance_plans(self):
        return self._get_maintenance_action("maintenance.maintenance_plan_action")

    def _sync_state_from_maintenance(self):
        if not self:
            return
        in_progress = (
            self.env["maintenance.order"]
            .sudo()
            .search(
                [
                    ("resource_ids", "in", self.resource_id.ids),
                    ("state", "=", "in_progress"),
                ]
            )
        )
        busy = in_progress.resource_ids
        assets = self.sudo()
        assets.filtered(
            lambda asset: asset.resource_id in busy and asset.state == "in_service"
        )._transition("maintenance")
        assets.filtered(
            lambda asset: asset.resource_id not in busy and asset.state == "maintenance"
        )._transition("in_service")
