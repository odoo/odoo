from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)

RUNNING_BOARD = ("open", "paused")


class ResourceAsset(models.Model):
    _inherit = ["resource.asset", "mixin.analytic"]

    board_id = fields.One2one(
        comodel_name="account.depreciation.board",
        inverse_name="asset_id",
        string="Depreciation Board",
    )
    depreciation_state = fields.Selection(
        related="board_id.depreciation_state",
        string="Depreciation Status",
    )
    value_book = fields.Monetary(
        related="board_id.value_book",
        groups="account.group_account_readonly,account.group_account_invoice",
    )
    value_original = fields.Monetary(
        compute="_compute_value",
        store=True,
        readonly=False,
    )
    date_acquisition = fields.Date(
        compute="_compute_acquisition_date",
        precompute=True,
        store=True,
        copy=True,
        readonly=False,
    )
    date_disposal = fields.Date(
        compute="_compute_disposal_date",
        store=True,
        readonly=False,
    )

    @api.constrains("active")
    def _check_active(self):
        for asset in self:
            state = asset.board_id.depreciation_state
            if not asset.active and state and state != "close":
                _debug.logic(
                    "archive.refused",
                    reason="board_not_closed",
                    asset=asset,
                    state=state,
                )
                raise UserError(_("You cannot archive a record that is not closed"))

    @api.depends("board_id.depreciation_move_ids.date", "board_id.depreciation_state")
    def _compute_disposal_date(self):
        for asset in self:
            board = asset.board_id
            if board.depreciation_state == "close":
                dates = board.depreciation_move_ids.filtered(
                    lambda m: m.date and m.state != "cancel"
                ).mapped("date")
                asset.date_disposal = (
                    max([*dates, asset.date_acquisition or dates[0]])
                    if dates
                    else asset.date_disposal
                    or asset.date_acquisition
                    or fields.Date.context_today(asset)
                )
            elif board:
                asset.date_disposal = False
            else:
                asset.date_disposal = asset.date_disposal

    @api.depends(
        "board_id.original_move_line_ids",
        "board_id.original_move_line_ids.account_id",
        "board_id.value_non_deductible_tax",
    )
    @_debug.perf.timed
    def _compute_value(self):
        for asset in self:
            board = asset.board_id
            if not board.original_move_line_ids:
                continue
            asset.value_original = board.value_purchase
            if board.value_non_deductible_tax:
                asset.value_original += board.value_non_deductible_tax

    @api.depends("board_id.original_move_line_ids")
    def _compute_analytic_distribution(self):
        for asset in self:
            lines = asset.board_id.original_move_line_ids
            distribution_asset = {}
            amount_total = sum(lines.mapped("balance"))
            if not asset.currency_id.is_zero(amount_total):
                for line in lines._origin:
                    if line.analytic_distribution:
                        for account, distribution in line.analytic_distribution.items():
                            distribution_asset[account] = (
                                distribution_asset.get(account, 0)
                                + distribution * line.balance
                            )
                for account, distribution_amount in distribution_asset.items():
                    distribution_asset[account] = distribution_amount / amount_total
            asset.analytic_distribution = (
                distribution_asset or asset.analytic_distribution
            )

    @api.depends("board_id.original_move_line_ids")
    def _compute_acquisition_date(self):
        for asset in self:
            board = asset.board_id
            if not board:
                asset.date_acquisition = asset.date_acquisition
                continue
            asset.date_acquisition = asset.date_acquisition or min(
                [(aml.invoice_date or aml.date) for aml in board.original_move_line_ids]
                + [fields.Date.today()]
            )

    def action_open_depreciation(self):
        self.check_singleton()
        return self.board_id.open_board(["form"])

    def action_dispose(self):
        running = self.filtered(
            lambda asset: asset.board_id.depreciation_state in RUNNING_BOARD
        )
        if not running:
            return super().action_dispose()
        if len(self) == 1:
            return self.board_id.action_asset_modify()
        _debug.logic("dispose.refused", reason="several_running_boards", assets=running)
        raise UserError(
            _(
                "%(assets)s: a running depreciation board is disposed one asset at a time, through its Dispose or Sell action.",
                assets=", ".join(running.mapped("display_name")),
            )
        )

    def _dispose(self, date=None):
        running = self.filtered(
            lambda asset: asset.board_id.depreciation_state in RUNNING_BOARD
        )
        _debug.pipeline("dispose", assets=self, through_board=len(running), date=date)
        for asset in running:
            asset.board_id._check_disposal_accounts()
            asset.board_id._close(self.env["account.move.line"], date)
        return super(ResourceAsset, self - running)._dispose(date)

    def _check_transition(self, state):
        super()._check_transition(state)
        if state == "disposed" and not self.env.context.get("board_lifecycle"):
            running = self.filtered(
                lambda asset: asset.board_id.depreciation_state in RUNNING_BOARD
            )
            if running:
                _debug.logic(
                    "transition.refused", reason="running_board", assets=running
                )
                raise UserError(
                    _(
                        "%(assets)s: a running depreciation board is disposed through its Dispose or Sell action, which books the disposal entry.",
                        assets=", ".join(running.mapped("display_name")),
                    )
                )

    def _check_reactivation(self):
        super()._check_reactivation()
        if not self.env.context.get("board_lifecycle"):
            closed = self.filtered(
                lambda asset: (
                    asset.state == "disposed"
                    and asset.board_id.depreciation_state == "close"
                )
            )
            if closed:
                _debug.logic(
                    "reactivation.refused", reason="board_closed", assets=closed
                )
                raise UserError(
                    _(
                        "%(assets)s: the depreciation board is closed, so the asset stays disposed. Set the board running again to restore it.",
                        assets=", ".join(closed.mapped("display_name")),
                    )
                )
