from odoo import models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class ResUsers(models.Model):
    _inherit = "res.users"

    def _get_asset_kinds_gated(self):
        return (
            self.env["resource.asset.kind"].sudo().search([("group_id", "!=", False)])
        )

    def _get_enabled_asset_kinds(self):
        self.check_singleton()
        kinds = self.env["resource.asset.kind"].sudo().search([])
        if self.has_group("resource_asset.group_asset_manager"):
            return kinds.ids
        enabled = [
            kind.id
            for kind in kinds
            if not kind.group_id or self.has_any_group_id([kind.group_id.id])
        ]
        _debug.logic("kinds_enabled", user=self, kinds=len(kinds), enabled=len(enabled))
        return enabled

    def _get_hidden_asset_kinds(self):
        self.check_singleton()
        if self.has_group("resource_asset.group_asset_manager"):
            return []
        hidden = [
            kind.id
            for kind in self._get_asset_kinds_gated()
            if not self.has_any_group_id([kind.group_id.id])
        ]
        _debug.logic("kinds_hidden", user=self, hidden=len(hidden))
        return hidden
