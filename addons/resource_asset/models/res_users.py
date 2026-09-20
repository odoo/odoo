from odoo import models


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
        return [
            kind.id
            for kind in kinds
            if not kind.group_id or self.has_any_group_id([kind.group_id.id])
        ]

    def _get_hidden_asset_kinds(self):
        self.check_singleton()
        if self.has_group("resource_asset.group_asset_manager"):
            return []
        return [
            kind.id
            for kind in self._get_asset_kinds_gated()
            if not self.has_any_group_id([kind.group_id.id])
        ]
