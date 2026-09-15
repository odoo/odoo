from collections import defaultdict

from odoo import api, fields, models
from odoo.exceptions import ValidationError

SHARED_FROM_ASSET = ("tz", "resource_calendar_id", "company_id")


class AppointmentResource(models.Model):
    _inherit = "appointment.resource"

    asset_id = fields.Many2one(
        comodel_name="resource.asset",
        index="btree_not_null",
        ondelete="restrict",
        help="The asset this profile books. Both then share one resource, so the asset's maintenance and custody reservations block its bookings.",
    )

    @api.constrains("asset_id")
    def _check_asset_unique(self):
        scoped = self.filtered("asset_id")
        if not scoped:
            return
        holders = (
            self.with_context(active_test=False).search(
                [("asset_id", "in", scoped.asset_id.ids)]
            )
            | scoped
        )
        by_asset = defaultdict(self.browse)
        for holder in holders:
            by_asset[holder.asset_id.id] |= holder
        for profile in scoped:
            other = by_asset[profile.asset_id.id] - profile
            if other:
                raise ValidationError(
                    self.env._(
                        "%(asset)s is already booked through %(profile)s.",
                        asset=profile.asset_id.display_name,
                        profile=other[0].display_name,
                    )
                )

    @api.model_create_multi
    def create(self, vals_list):
        assets = self.env["resource.asset"].browse(
            [vals["asset_id"] for vals in vals_list if vals.get("asset_id")]
        )
        by_id = {asset.id: asset for asset in assets}
        for vals in vals_list:
            asset = by_id.get(vals.get("asset_id"))
            if asset:
                vals["resource_id"] = asset.resource_id.id
                vals["name"] = asset.name
                vals["active"] = asset.active
                for fname in SHARED_FROM_ASSET:
                    vals.pop(fname, None)
        return super().create(vals_list)

    def write(self, vals):
        if "asset_id" not in vals:
            return super().write(vals)
        asset = self.env["resource.asset"].browse(vals["asset_id"])
        orphans = self.env["resource.resource"]
        for profile in self:
            if asset and profile.resource_id != asset.resource_id:
                if not profile.resource_id.asset_id:
                    orphans |= profile.resource_id
            elif not asset and profile.asset_id:
                own = self.env["resource.resource"].create(
                    profile._prepare_resource_values(
                        {
                            "name": profile.name,
                            "company_id": profile.company_id.id,
                        },
                        profile.tz,
                    )
                )
                super(AppointmentResource, profile).write({"resource_id": own.id})
        res = super().write(vals)
        if asset:
            super().write({"resource_id": asset.resource_id.id})
            orphans.filtered(
                lambda r: not r.employee_id if "employee_id" in r._fields else True
            ).action_archive()
        return res
