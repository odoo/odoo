from odoo import fields, models
from odoo.fields import Domain

BOOKABLE_STATES = ("in_service", "maintenance")


class ResourceAsset(models.Model):
    _inherit = "resource.asset"

    appointment_resource_id = fields.Many2one(
        comodel_name="appointment.resource",
        string="Booking Profile",
        compute="_compute_appointment_resource_id",
        inverse="_inverse_appointment_resource_id",
        search="_search_appointment_resource_id",
    )

    def _compute_appointment_resource_id(self):
        profiles = (
            self.env["appointment.resource"]
            .with_context(active_test=False)
            .search([("asset_id", "in", self.ids)])
        )
        by_asset = {profile.asset_id.id: profile for profile in profiles}
        for asset in self:
            asset.appointment_resource_id = by_asset.get(asset.id)

    def _search_appointment_resource_id(self, operator, value):
        if operator not in ("in", "any"):
            return NotImplemented
        profiles = (
            self.env["appointment.resource"]
            .with_context(active_test=False)
            ._search(Domain("id", operator, value) & Domain("asset_id", "!=", False))
        )
        return Domain("id", "in", profiles.subselect("asset_id"))

    def _inverse_appointment_resource_id(self):
        profiles = (
            self.env["appointment.resource"]
            .with_context(active_test=False)
            .search([("asset_id", "in", self.ids)])
        )
        by_asset = {profile.asset_id.id: profile for profile in profiles}
        for asset in self:
            current = by_asset.get(asset.id, profiles.browse())
            if current == asset.appointment_resource_id:
                continue
            current.asset_id = False
            asset.appointment_resource_id.asset_id = asset

    def _is_bookable(self):
        self.check_singleton()
        return self.state in BOOKABLE_STATES

    def _create_appointment_resources(self):
        missing = self.filtered(lambda asset: not asset.appointment_resource_id)
        profiles = self.env["appointment.resource"].create(
            [{"asset_id": asset.id} for asset in missing]
        )
        self.invalidate_recordset(["appointment_resource_id"])
        return profiles

    def action_make_bookable(self):
        self._create_appointment_resources()
        self.check_singleton()
        return {
            "type": "ir.actions.act_window",
            "res_model": "appointment.resource",
            "res_id": self.appointment_resource_id.id,
            "views": [(False, "form")],
            "target": "current",
        }
