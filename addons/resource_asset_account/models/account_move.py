from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    # FIELDS
    asset_part_flagged_count = fields.Integer(
        string="Flagged Parts",
        compute="_compute_asset_part_flagged_count",
    )
    asset_part_hold = fields.Boolean(
        string="Held for Flagged Parts",
        copy=False,
        readonly=True,
        help="Payment is blocked because a part this bill charges was flagged.",
    )

    # COMPUTE METHODS
    @api.depends("line_ids.asset_part_ids.review_state")
    def _compute_asset_part_flagged_count(self):
        for move in self:
            move.asset_part_flagged_count = len(move._get_flagged_asset_parts())

    # ACTION METHODS
    def action_toggle_block_payment(self):
        if self.payment_state == "blocked" and self._get_flagged_asset_parts():
            raise UserError(
                self.env._(
                    "%(bill)s charges flagged parts: an asset manager clears them before it is paid.",
                    bill=self.display_name,
                )
            )
        if self.payment_state == "blocked":
            self.asset_part_hold = False
        return super().action_toggle_block_payment()

    def action_view_flagged_asset_parts(self):
        self.check_singleton()
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "resource_asset_product.action_resource_asset_part"
        )
        action["domain"] = [("account_move_line_id.move_id", "=", self.id)]
        action["context"] = {"create": False, "search_default_flagged": 1}
        return action

    # POSTING METHODS
    def _post(self, soft=True):
        bills = self.filtered(
            lambda move: (
                move.move_type == "in_invoice" and move.invoice_line_ids.asset_id
            )
        )
        if bills:
            _debug.pipeline("bill_parts_hold_check", bills=bills)
            bills._hold_flagged_asset_parts()
        return super()._post(soft=soft)

    def _hold_flagged_asset_parts(self):
        # sudo: binding a bill line to the parts it charges follows from posting it.
        parts = (
            self.env["resource.asset.part"]
            .sudo()
            .search(
                [
                    ("asset_id", "in", self.invoice_line_ids.asset_id.ids),
                    ("account_move_line_id", "=", False),
                    ("vendor_id", "!=", False),
                    ("state", "in", ("installed", "removed")),
                ]
            )
        )
        self.sudo().invoice_line_ids._bind_asset_parts(parts)
        for bill in self:
            flagged = bill._get_flagged_asset_parts()
            if flagged:
                _debug.logic(
                    "bill_post_refused_flagged_parts", bill=bill, parts=flagged
                )
                raise UserError(
                    self.env._(
                        "%(bill)s cannot be posted: it charges flagged parts (%(parts)s). An asset manager reviews and clears them first.",
                        bill=bill.display_name,
                        parts=", ".join(flagged.mapped("display_name")),
                    )
                )

    def _sync_asset_part_hold(self):
        for move in self.filtered(lambda move: move.state == "posted"):
            flagged = move._get_flagged_asset_parts()
            _debug.logic(
                "bill_parts_hold_sync",
                bill=move,
                flagged=flagged,
                payment_state=move.payment_state,
                held=move.asset_part_hold,
            )
            if flagged and move.payment_state not in (
                "blocked",
                "paid",
                "in_payment",
                "reversed",
            ):
                move.write({"payment_state": "blocked", "asset_part_hold": True})
                move.message_post(
                    body=self.env._(
                        "Payment blocked: this bill charges flagged parts (%(parts)s).",
                        parts=", ".join(flagged.mapped("display_name")),
                    )
                )
            elif not flagged and move.asset_part_hold:
                move.asset_part_hold = False
                if move.payment_state == "blocked":
                    move.payment_state = "not_paid"
                    self.env.add_to_compute(move._fields["payment_state"], move)
                    move.message_post(
                        body=self.env._(
                            "Payment released: its flagged parts were cleared."
                        )
                    )

    # HELPER METHODS
    def _get_flagged_asset_parts(self):
        self.check_singleton()
        # sudo: an accountant sees that a bill is held without rights on the asset.
        return self.sudo().line_ids.asset_part_ids.filtered(
            lambda part: part.review_state == "flagged"
        )
