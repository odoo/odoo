from odoo import api, fields, models


class MaintenanceRequest(models.Model):
    _name = "maintenance.request"
    _inherit = ["maintenance.request", "mixin.resource.scheduling"]
    # Booked by hand: the window is the request's schedule when it blocks the
    # asset, and nothing otherwise. A sibling module may book the same request
    # on another resource with its own rules.
    _reservation_sync_manual = True

    asset_id = fields.Many2one(
        comodel_name="resource.asset",
        index="btree_not_null",
        ondelete="restrict",
        check_company=True,
    )
    block_asset = fields.Boolean(
        default=True,
        help="While scheduled, the asset is unavailable time for planning, work orders and every other reader of its calendar.",
    )

    @api.depends("asset_id.maintenance_team_id")
    def _compute_maintenance_team_id(self):
        super()._compute_maintenance_team_id()
        for request in self:
            team = request.asset_id.maintenance_team_id
            if team and (not team.company_id or team.company_id == request.company_id):
                request.maintenance_team_id = team

    @api.depends("asset_id.technician_user_id")
    def _compute_user_id(self):
        super()._compute_user_id()
        for request in self:
            technician = request.asset_id.technician_user_id
            if technician and request.company_id in technician.company_ids:
                request.user_id = technician

    def _is_new_activity_required(self, vals):
        return super()._is_new_activity_required(vals) or vals.get("asset_id")

    def _get_activity_note(self):
        self.check_singleton()
        if self.asset_id and not self.equipment_id:
            return self.env._("Request planned for %s", self.asset_id._get_html_link())
        return super()._get_activity_note()

    def _get_fields_reservation_date(self):
        return ("schedule_date", "schedule_end")

    def _asset_reservation_vals(self):
        self.check_singleton()
        resource = self.asset_id.resource_id
        if (
            not resource
            or not self.block_asset
            or self.archive
            or not self.schedule_date
            or not self.schedule_end
            or self.stage_id.done
            or self._asset_booked_by_sibling(resource)
        ):
            return []
        return [
            {
                "name": self.display_name,
                "resource_id": resource.id,
                "date_start": self.schedule_date,
                "date_end": self.schedule_end,
                "allocated_percentage": 100.0,
                "enforcement_mode": "hard",
                "booking_key": "asset",
            }
        ]

    def _asset_booked_by_sibling(self, resource):
        """Whether another booking path of this request already claims ``resource``
        (a work centre running on the asset shares its resource)."""
        if "workcenter_id" not in self._fields:
            return False
        return bool(
            self.workcenter_id
            and self.block_workcenter
            and self.workcenter_id.resource_id == resource
        )

    def _sync_asset_reservations(self):
        reservation_model = self.env["resource.reservation"].sudo()
        for request in self:
            existing = request.sudo().with_context(active_test=False).reservation_ids
            existing = existing.filtered(lambda r: r.booking_key == "asset")
            reservation_model._sync_reservation(
                request, request._asset_reservation_vals(), existing=existing
            )
        self.invalidate_recordset(["reservation_ids", "schedule_overlap_count"])

    @api.model_create_multi
    def create(self, vals_list):
        requests = super().create(vals_list)
        requests.filtered("asset_id")._sync_asset_reservations()
        return requests

    def write(self, vals):
        before = {request.id: request.asset_id for request in self}
        res = super().write(vals)
        if vals.keys() & {
            "asset_id",
            "block_asset",
            "schedule_date",
            "schedule_end",
            "stage_id",
            "archive",
        }:
            touched = self.filtered(lambda r: r.asset_id or before[r.id])
            touched._sync_asset_reservations()
        return res
