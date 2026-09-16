from typing import Any

from odoo import api, fields, models
from odoo.exceptions import UserError


class ResourceAssetLog(models.Model):
    _inherit = "resource.asset.log"

    source = fields.Selection(
        selection_add=[("bill", "Vendor Bill")],
        ondelete={"bill": "set default"},
    )

    account_move_line_id = fields.Many2one(
        comodel_name="account.move.line",
        string="Accounting Entry",
        help="Link to the vendor bill line that created this log entry. "
        "When set, the amount and asset are synchronized from the bill",
    )
    account_move_state = fields.Selection(
        related="account_move_line_id.parent_state",
        string="Bill State",
        help="Current state of the related vendor bill (draft, posted, cancelled)",
    )
    asset_id = fields.Many2one(
        comodel_name="resource.asset",
        compute="_compute_asset_id",
        store=True,
        readonly=False,
        help="Asset this log entry is for. Auto-filled from the related bill line",
    )
    amount = fields.Monetary(
        compute="_compute_amount",
        inverse="_inverse_amount",
        store=True,
        readonly=False,
        help="Cost amount. Auto-computed from bill line if linked to accounting. "
        "Signed on the cost convention: positive for expenses, negative for "
        "credits, so a rebate line reduces the asset's recorded spend",
    )
    state = fields.Selection(
        compute="_compute_state",
        default=None,
        store=True,
        readonly=False,
        help="Auto-synced from the related bill: posted → done, cancel → cancelled, "
        "draft → new. Manual logs (no bill) remain user-controlled.",
    )
    date = fields.Date(
        compute="_compute_date",
        default=None,
        store=True,
        readonly=False,
    )
    vendor_id = fields.Many2one(
        compute="_compute_vendor_id",
        store=True,
        readonly=False,
    )
    product_id = fields.Many2one(
        compute="_compute_product_id",
        store=True,
        readonly=False,
    )

    _account_move_line_id_uniq = models.Constraint(
        "unique(account_move_line_id)",
        "Only one asset log can be linked to a given accounting line.",
    )

    @api.ondelete(at_uninstall=False)
    def _unlink_if_no_linked_bill(self) -> None:
        if self.env.context.get("ignore_linked_bill_constraint"):
            return
        if any(log.account_move_line_id for log in self):
            raise UserError(
                self.env._(
                    "You cannot delete log services records because one or more of them "
                    "were created from a bill. Delete the bill line instead."
                ),
            )

    @api.depends("account_move_line_id", "account_move_line_id.asset_id")
    def _compute_asset_id(self) -> None:
        for log in self:
            if not log.account_move_line_id:
                continue
            log.asset_id = log.account_move_line_id.asset_id

    @api.depends("account_move_line_id", "account_move_line_id.parent_state")
    def _compute_state(self) -> None:
        bill_to_log = {
            "posted": "done",
            "cancel": "cancelled",
            "draft": "new",
        }
        for log in self:
            if not log.account_move_line_id:
                log.state = log.state or "new"
                continue
            log.state = bill_to_log.get(
                log.account_move_line_id.parent_state,
                "new",
            )

    @api.depends(
        "account_move_line_id",
        "account_move_line_id.invoice_date",
        "account_move_line_id.date",
    )
    def _compute_date(self) -> None:
        for log in self:
            line = log.account_move_line_id
            if not line:
                log.date = log.date or fields.Date.context_today(log)
                continue
            log.date = line.invoice_date or line.date

    @api.depends("account_move_line_id", "account_move_line_id.partner_id")
    def _compute_vendor_id(self) -> None:
        for log in self:
            if not log.account_move_line_id:
                continue
            log.vendor_id = log.account_move_line_id.partner_id

    @api.depends("account_move_line_id", "account_move_line_id.product_id")
    def _compute_product_id(self) -> None:
        for log in self:
            if not log.account_move_line_id:
                continue
            log.product_id = log.account_move_line_id.product_id

    @api.depends(
        "product_category_id",
        "account_move_line_id",
        "account_move_line_id.product_id",
        "account_move_line_id.account_id.asset_log_type",
    )
    def _compute_log_type(self) -> None:
        super()._compute_log_type()
        for log in self:
            line = log.account_move_line_id
            if not line:
                continue
            # Same rule the parent applies to the category: re-derive while the
            # bill line is the source of truth, but never un-type a log that the
            # line no longer types.
            log.log_type = line._get_asset_log_type() or log.log_type

    @api.depends("account_move_line_id.balance")
    def _compute_amount(self) -> None:
        for log in self:
            if not log.account_move_line_id:
                continue
            log.amount = log.account_move_line_id.balance

    def _inverse_amount(self) -> None:
        if any(service.account_move_line_id for service in self):
            raise UserError(
                self.env._(
                    "You cannot modify the amount of services linked to an accounting entry. "
                    "Please modify the related vendor bill instead."
                ),
            )

    @api.model
    def _reclassify_untyped_from_account(self) -> int:
        untyped = self.search(
            [
                ("log_type", "=", False),
                ("account_move_line_id", "!=", False),
                ("account_move_line_id.account_id.asset_log_type", "!=", False),
            ],
        )
        for log in untyped:
            log.log_type = log.account_move_line_id.account_id.asset_log_type
        return len(untyped)

    def action_view_account_move(self) -> dict[str, Any]:
        self.check_singleton()
        return {
            "name": self.env._("Vendor Bill"),
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "view_mode": "form",
            "target": "current",
            "res_id": self.account_move_line_id.move_id.id,
        }
