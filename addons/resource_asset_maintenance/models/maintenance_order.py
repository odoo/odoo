from odoo import api, fields, models

from odoo.addons.maintenance.models.maintenance_order import BOOKING_STATES


class MaintenanceOrder(models.Model):
    _name = "maintenance.order"
    _inherit = ["maintenance.order", "mixin.resource.scheduling"]
    # Booked by hand: the window is the order's schedule when it blocks the
    # asset, and nothing otherwise. A sibling module may book the same order
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
        for order in self:
            team = order.asset_id.maintenance_team_id
            if team and (not team.company_id or team.company_id == order.company_id):
                order.maintenance_team_id = team

    @api.depends("asset_id.technician_user_id")
    def _compute_user_id(self):
        super()._compute_user_id()
        for order in self:
            technician = order.asset_id.technician_user_id
            if technician and order.company_id in technician.company_ids:
                order.user_id = technician

    def _is_new_activity_required(self, vals):
        return super()._is_new_activity_required(vals) or vals.get("asset_id")

    def _get_activity_note(self):
        self.check_singleton()
        if self.asset_id and not self.equipment_id:
            return self.env._("Order planned for %s", self.asset_id._get_html_link())
        return super()._get_activity_note()

    def _get_fields_reservation_date(self):
        return ("schedule_date", "schedule_end")

    def _asset_reservation_vals(self):
        self.check_singleton()
        resource = self.asset_id.resource_id
        if (
            not resource
            or not self.block_asset
            or self.state not in BOOKING_STATES
            or not self.schedule_date
            or not self.schedule_end
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
        """Whether another booking path of this order already claims ``resource``
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
        for order in self:
            existing = order.sudo().with_context(active_test=False).reservation_ids
            existing = existing.filtered(lambda r: r.booking_key == "asset")
            reservation_model._sync_reservation(
                order, order._asset_reservation_vals(), existing=existing
            )
        self.invalidate_recordset(["reservation_ids", "schedule_overlap_count"])

    @api.model_create_multi
    def create(self, vals_list):
        orders = super().create(vals_list)
        orders.filtered("asset_id")._sync_asset_reservations()
        orders.asset_id._sync_state_from_maintenance()
        return orders

    def write(self, vals):
        before = {order.id: order.asset_id for order in self}
        res = super().write(vals)
        if vals.keys() & {
            "asset_id",
            "block_asset",
            "schedule_date",
            "schedule_end",
            "state",
        }:
            touched = self.filtered(lambda r: r.asset_id or before[r.id])
            touched._sync_asset_reservations()
        if vals.keys() & {"asset_id", "state"}:
            previous = self.env["resource.asset"].union(*before.values())
            (self.asset_id | previous)._sync_state_from_maintenance()
        return res

    def unlink(self):
        assets = self.asset_id
        res = super().unlink()
        assets.exists()._sync_state_from_maintenance()
        return res
