from collections import defaultdict

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class MrpWorkcenter(models.Model):
    _inherit = "mrp.workcenter"

    asset_id = fields.Many2one(
        comodel_name="resource.asset",
        string="Machine",
        index="btree_not_null",
        check_company=True,
        help="The asset this work centre runs on. Both then share one resource: the machine's downtime, custody and bookings are the work centre's.",
    )

    @api.constrains("asset_id")
    def _check_asset_unique(self):
        scoped = self.filtered("asset_id")
        if not scoped:
            return
        # One query for the whole batch. The batch is folded in as well: two
        # work centres given the same asset in one create clash with each
        # other, and neither is in the database yet for the other to find.
        holders = self.search([("asset_id", "in", scoped.asset_id.ids)]) | scoped
        by_asset = defaultdict(self.browse)
        for holder in holders:
            by_asset[holder.asset_id.id] |= holder
        for workcenter in scoped:
            other = by_asset[workcenter.asset_id.id] - workcenter
            if other:
                raise ValidationError(
                    self.env._(
                        "%(asset)s already runs %(workcenter)s.",
                        asset=workcenter.asset_id.display_name,
                        workcenter=other[0].display_name,
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
                vals.pop("resource_calendar_id", None)
        return super().create(vals_list)

    def write(self, vals):
        if "asset_id" not in vals:
            return super().write(vals)
        asset = self.env["resource.asset"].browse(vals["asset_id"])
        orphans = self.env["resource.resource"]
        for workcenter in self:
            if asset and workcenter.resource_id != asset.resource_id:
                if not workcenter.resource_id.asset_id:
                    orphans |= workcenter.resource_id
            elif not asset and workcenter.resource_id.asset_id:
                # Detaching: the work centre gets a resource of its own again.
                own = self.env["resource.resource"].create(
                    workcenter._prepare_resource_values(
                        {
                            "name": workcenter.name,
                            "company_id": workcenter.company_id.id,
                        },
                        workcenter.tz,
                    )
                )
                super(MrpWorkcenter, workcenter).write({"resource_id": own.id})
        res = super().write(vals)
        if asset:
            super().write({"resource_id": asset.resource_id.id})
            orphans.filtered(
                lambda r: not r.employee_id if "employee_id" in r._fields else True
            ).action_archive()
        return res
