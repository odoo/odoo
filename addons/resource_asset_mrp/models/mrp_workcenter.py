from odoo import api, fields, models
from odoo.exceptions import ValidationError


class MrpWorkcenter(models.Model):
    _inherit = "mrp.workcenter"

    asset_id = fields.Many2one(
        comodel_name="resource.asset",
        string="Machine",
        index="unique",
        copy=False,
        check_company=True,
        help="The asset this work centre runs on. Both then share one resource: the machine's downtime, custody and bookings are the work centre's.",
    )

    def _check_asset_available(self, claims):
        """`claims` pairs a work centre (or its name, before it exists) with
        the asset it wants. Refused before the flush, so the unique index on
        `asset_id` never has to: the clash is named with its work centre. The
        batch is folded in as well: two work centres given one asset in one
        create clash with each other, and neither is in the database yet for
        the other to find."""
        wanted = [asset_id for _claimant, asset_id in claims if asset_id]
        if not wanted:
            return
        holders = self.with_context(active_test=False).search(
            [("asset_id", "in", wanted)]
        )
        taken = {holder.asset_id.id: holder.display_name for holder in holders}
        claimed = {holder.id for holder in holders}
        for claimant, asset_id in claims:
            if not asset_id:
                continue
            name = claimant if isinstance(claimant, str) else claimant.display_name
            is_own = not isinstance(claimant, str) and claimant.id in claimed
            if asset_id in taken and not (is_own and taken[asset_id] == name):
                raise ValidationError(
                    self.env._(
                        "%(asset)s already runs %(workcenter)s.",
                        asset=self.env["resource.asset"].browse(asset_id).display_name,
                        workcenter=taken[asset_id],
                    )
                )
            taken[asset_id] = name

    @api.model_create_multi
    def create(self, vals_list):
        assets = self.env["resource.asset"].browse(
            [vals["asset_id"] for vals in vals_list if vals.get("asset_id")]
        )
        by_id = {asset.id: asset for asset in assets}
        self._check_asset_available(
            [(vals.get("name", ""), vals.get("asset_id")) for vals in vals_list]
        )
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
        self._check_asset_available([(workcenter, asset.id) for workcenter in self])
        res = super().write(vals)
        left = self.env["resource.resource"]
        for workcenter in self:
            target = asset.resource_id if asset else workcenter._provision_resource()
            if workcenter.resource_id == target:
                continue
            left |= workcenter.resource_id
            super(MrpWorkcenter, workcenter).write({"resource_id": target.id})
        self._release_resources(left)
        return res

    def _provision_resource(self):
        self.check_singleton()
        return self.env["resource.resource"].create(
            self._prepare_resource_values(
                {"name": self.name, "company_id": self.company_id.id}, self.tz
            )
        )

    @api.model
    def _release_resources(self, resources):
        """A resource nobody is, that no work centre uses any more, is archived;
        a machine's or a person's resource is theirs to keep."""
        if not resources:
            return
        owned = resources._get_owners()
        bare = resources.filtered(lambda resource: resource.id not in owned)
        still_used = self.search([("resource_id", "in", bare.ids)]).resource_id
        (bare - still_used).action_archive()
