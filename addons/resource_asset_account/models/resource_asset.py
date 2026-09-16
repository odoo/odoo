from typing import Any

from odoo import api, fields, models


class ResourceAsset(models.Model):
    _inherit = "resource.asset"

    account_move_ids = fields.Many2many(
        comodel_name="account.move",
        string="Bills",
        compute="_compute_move_ids",
        help="Vendor bills containing line items related to this asset",
    )
    count_bill = fields.Integer(
        string="Bills Count",
        compute="_compute_move_ids",
        help="Number of vendor bills referencing this asset",
    )
    account_move_line_ids = fields.One2many(
        comodel_name="account.move.line",
        inverse_name="asset_id",
        string="Bill Lines",
        export_string_translation=False,
    )

    @api.depends("account_move_line_ids.parent_state", "account_move_line_ids.move_id")
    @api.depends_context("uid")
    def _compute_move_ids(self) -> None:
        account_move = self.env["account.move"]
        empty_moves = account_move.browse()

        if not self.env.user.has_group("account.group_account_readonly"):
            move_field = self._fields["account_move_ids"]
            for asset in self:
                asset.count_bill = 0
                move_field._update_cache(asset, ())
            return

        moves_by_asset = self.env["account.move.line"]._read_group(
            domain=[
                ("asset_id", "in", self.ids),
                ("parent_state", "!=", "cancel"),
                ("move_id.move_type", "in", account_move.get_purchase_types()),
            ],
            groupby=["asset_id"],
            aggregates=["move_id:array_agg"],
        )
        asset_move_mapping = {
            asset.id: account_move.browse(set(move_ids))
            for asset, move_ids in moves_by_asset
        }
        for asset in self:
            moves = asset_move_mapping.get(asset.id, empty_moves)
            asset.account_move_ids = moves
            asset.count_bill = len(moves)

    def action_view_bills(self) -> dict[str, Any]:
        self.check_singleton()
        action = self.env["ir.actions.act_window"]._get_action_dict_by_xml_id(
            "account.action_move_in_invoice_type"
        )
        action["domain"] = [("id", "in", self.account_move_ids.ids)]
        return action
