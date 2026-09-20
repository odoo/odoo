from odoo import models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)

KIND_DEFAULTS = ("technician_user_id", "maintenance_team_id")


class ResourceAsset(models.Model):
    _name = "resource.asset"
    _inherit = ["resource.asset", "mixin.maintenance.target"]

    def _on_kind_changed(self, vals):
        super()._on_kind_changed(vals)
        for asset in self:
            asset._take_kind_defaults(vals)

    def _take_kind_defaults(self, given):
        self.check_singleton()
        kind = self.kind_id
        vals = {
            fname: kind[fname].id
            for fname in KIND_DEFAULTS
            if not given.get(fname) and kind[fname]
        }
        if vals:
            _debug.lifecycle("kind_defaults_taken", asset=self, fields=sorted(vals))
            self.sudo().write(vals)

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
        _debug.pipeline("state_synced", assets=self, orders=in_progress, busy=len(busy))
        assets = self.sudo()
        assets.filtered(
            lambda asset: asset.resource_id in busy and asset.state == "in_service"
        )._transition("maintenance")
        assets.filtered(
            lambda asset: asset.resource_id not in busy and asset.state == "maintenance"
        )._transition("in_service")
