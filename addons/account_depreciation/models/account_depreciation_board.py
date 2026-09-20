import datetime
from contextlib import contextmanager
from math import copysign
from typing import NamedTuple

import psycopg.errors
from dateutil.relativedelta import relativedelta
from markupsafe import Markup

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.libs.debug_log import DebugLog
from odoo.tools import float_compare, float_is_zero, formatLang
from odoo.tools.date_utils import end_of
from odoo.tools.misc import clean_context

_debug = DebugLog(__name__)

DAYS_PER_MONTH = 30
DAYS_PER_YEAR = DAYS_PER_MONTH * 12


class LinearRecompute(NamedTuple):
    start_date: datetime.date
    residual: float
    lifetime_left: float


RUNNING_BOARD = ("open", "paused")


class AccountDepreciationBoard(models.Model):
    """The depreciation of one asset: a facet of `resource.asset`, reached from the
    asset through `board_id`. The board reads and writes the asset's own facts
    (name, company, value, dates) through delegation, and owns everything the
    accounting knows about depreciating it."""

    _name = "account.depreciation.board"
    _description = "Depreciation Board"
    _inherit = ["mixin.mail.thread", "mixin.mail.activity"]
    _inherits = {"resource.asset": "asset_id"}
    _check_company_auto = True

    asset_id = fields.Many2one(
        comodel_name="resource.asset",
        string="Asset",
        index="unique",
        required=True,
        ondelete="cascade",
    )
    created_asset = fields.Boolean(
        help="The asset was created for this board, by a bill or a gross increase, so "
        "it goes with the board when the board is undone."
    )
    count_depreciation_posted = fields.Integer(
        string="# Posted Depreciation Entries",
        compute="_compute_depreciation_entries_count",
        groups="account.group_account_readonly,account.group_account_invoice",
    )
    count_increase = fields.Count(
        count_of="increase_ids",
        string="# Gross Increases",
        groups="account.group_account_readonly,account.group_account_invoice",
        help="Number of assets made to increase the value of the asset",
    )
    count_depreciation = fields.Count(
        count_of="depreciation_move_ids",
        string="# Depreciation Entries",
        groups="account.group_account_readonly,account.group_account_invoice",
        help="Number of depreciation entries (posted or not)",
    )

    country_code = fields.Char(
        related="company_id.account_config_id.account_fiscal_country_id.code",
        groups="account.group_account_readonly,account.group_account_invoice",
    )
    depreciation_state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("open", "Running"),
            ("paused", "On Hold"),
            ("close", "Closed"),
            ("cancelled", "Cancelled"),
        ],
        string="Depreciation Status",
        default="draft",
        copy=False,
        readonly=True,
        required=True,
        help="When an asset is created, the status is 'Draft'.\n"
        "If the asset is confirmed, the status goes in 'Running' and the depreciation lines can be posted in the accounting.\n"
        "The 'On Hold' status can be set manually when you want to pause the depreciation of an asset for some time.\n"
        "You can manually close an asset when the depreciation is over.\n"
        "By cancelling an asset, all depreciation entries will be reversed",
    )

    depreciation_method = fields.Selection(
        selection=[
            ("linear", "Straight Line"),
            ("degressive", "Declining"),
            ("degressive_then_linear", "Declining then Straight Line"),
        ],
        default="linear",
        groups="account.group_account_readonly,account.group_account_invoice",
        help="Choose the method to use to compute the amount of depreciation lines.\n"
        "  * Straight Line: Calculated on basis of: Gross Value / Duration\n"
        "  * Declining: Calculated on basis of: Residual Value * Declining Factor, with a minimum depreciation value equal to the straight line value once that exceeds the declining amount.\n"
        "  * Declining then Straight Line: Like Declining but with a minimum depreciation value equal to the straight line value.",
    )
    depreciation_duration = fields.Integer(
        string="Duration",
        default=5,
        groups="account.group_account_readonly,account.group_account_invoice",
        help="The number of depreciations needed to depreciate your asset",
    )
    depreciation_period = fields.Selection(
        selection=[("1", "Months"), ("12", "Years")],
        string="Number of Months in a Period",
        default="12",
        groups="account.group_account_readonly,account.group_account_invoice",
        help="The amount of time between two depreciations",
    )
    depreciation_factor = fields.Float(
        string="Declining Factor",
        default=0.3,
        groups="account.group_account_readonly,account.group_account_invoice",
    )
    depreciation_prorata = fields.Selection(
        selection=[
            ("none", "No Prorata"),
            ("constant_periods", "Constant Periods"),
            ("daily_computation", "Based on days per period"),
        ],
        string="Computation",
        default="constant_periods",
        required=True,
        groups="account.group_account_readonly,account.group_account_invoice",
    )
    date_prorata = fields.Date(
        compute="_compute_prorata_date",
        precompute=True,
        store=True,
        copy=True,
        readonly=False,
        groups="account.group_account_readonly,account.group_account_invoice",
        help="Starting date of the period used in the prorata calculation of the first depreciation",
    )
    date_prorata_paused = fields.Date(
        compute="_compute_paused_prorata_date",
        groups="account.group_account_readonly,account.group_account_invoice",
    )
    account_asset_id = fields.Many2one(
        comodel_name="account.account",
        string="Fixed Asset Account",
        compute="_compute_account_asset_id",
        store=True,
        readonly=False,
        domain="[('account_type', '!=', 'off_balance')]",
        check_company=True,
        groups="account.group_account_readonly,account.group_account_invoice",
        help="Account used to record the purchase of the asset at its original price.",
    )
    asset_group_id = fields.Many2one(
        comodel_name="account.asset.group",
        index=True,
        check_company=True,
        tracking=True,
        groups="account.group_account_readonly,account.group_account_invoice",
    )
    account_depreciation_id = fields.Many2one(
        comodel_name="account.account",
        string="Depreciation Account",
        domain="[('account_type', 'not in', ('asset_receivable', 'liability_payable', 'asset_cash', 'liability_credit_card', 'off_balance'))]",
        check_company=True,
        groups="account.group_account_readonly,account.group_account_invoice",
        help="Account used in the depreciation entries, to decrease the asset value.",
    )
    account_depreciation_expense_id = fields.Many2one(
        comodel_name="account.account",
        string="Expense Account",
        domain="[('account_type', 'not in', ('asset_receivable', 'liability_payable', 'asset_cash', 'liability_credit_card', 'off_balance'))]",
        check_company=True,
        groups="account.group_account_readonly,account.group_account_invoice",
        help="Account used in the periodical entries, to record a part of the asset as expense.",
    )

    depreciation_journal_id = fields.Many2one(
        comodel_name="account.journal",
        compute="_compute_depreciation_journal_id",
        store=True,
        readonly=False,
        domain="[('type', '=', 'general')]",
        check_company=True,
        groups="account.group_account_readonly,account.group_account_invoice",
    )

    value_book = fields.Monetary(
        compute="_compute_book_value",
        recursive=True,
        store=True,
        readonly=True,
        groups="account.group_account_readonly,account.group_account_invoice",
        help="Sum of the depreciable value, the salvage value and the book value of all value increase items",
    )
    value_depreciable_residual = fields.Monetary(
        string="Depreciable Value",
        compute="_compute_value_depreciable_residual",
        groups="account.group_account_readonly,account.group_account_invoice",
    )
    value_salvage = fields.Monetary(
        string="Not Depreciable Value",
        compute="_compute_salvage_value",
        store=True,
        readonly=False,
        groups="account.group_account_readonly,account.group_account_invoice",
        help="It is the amount you plan to have that you cannot depreciate.",
    )
    value_depreciable = fields.Monetary(
        compute="_compute_total_depreciable_value",
        groups="account.group_account_readonly,account.group_account_invoice",
    )
    value_increase = fields.Monetary(
        compute="_compute_gross_increase_value",
        compute_sudo=True,
        groups="account.group_account_readonly,account.group_account_invoice",
    )
    value_non_deductible_tax = fields.Monetary(
        compute="_compute_value_non_deductible_tax",
        store=True,
        readonly=True,
        groups="account.group_account_readonly,account.group_account_invoice",
    )
    value_purchase = fields.Monetary(
        compute="_compute_related_purchase_value",
        groups="account.group_account_readonly,account.group_account_invoice",
    )

    depreciation_move_ids = fields.One2many(
        comodel_name="account.move",
        inverse_name="depreciation_board_id",
        string="Depreciation Lines",
    )
    original_move_line_ids = fields.Many2many(
        comodel_name="account.move.line",
        relation="depreciation_board_move_line_rel",
        column1="board_id",
        column2="line_id",
        string="Journal Items",
        copy=False,
    )

    depreciation_profile_id = fields.Many2one(
        comodel_name="account.depreciation.profile",
        string="Depreciation Profile",
        change_default=True,
        index="btree_not_null",
        check_company=True,
        groups="account.group_account_readonly,account.group_account_invoice",
    )
    account_type = fields.Selection(
        related="account_asset_id.account_type",
        string="Type of the account",
        groups="account.group_account_readonly,account.group_account_invoice",
    )
    display_account_asset_id = fields.Boolean(
        compute="_compute_display_account_asset_id",
        groups="account.group_account_readonly,account.group_account_invoice",
    )

    increased_board_id = fields.Many2one(
        comodel_name="account.depreciation.board",
        string="Increases",
        index="btree_not_null",
        help="The board whose value this one increases, and whose life caps its depreciation",
    )
    increased_asset_id = fields.Many2one(
        related="increased_board_id.asset_id",
        store=True,
    )
    increase_ids = fields.One2many(
        comodel_name="account.depreciation.board",
        inverse_name="increased_board_id",
        string="Gross Increases",
        context={"active_test": False},
    )

    value_depreciated_import = fields.Monetary(
        groups="account.group_account_readonly,account.group_account_invoice",
        help="In case of an import from another software, you might need to use this field to have the right "
        "depreciation table report. This is the value that was already depreciated with entries not computed from this model",
    )

    depreciation_lifetime_days = fields.Float(
        compute="_compute_lifetime_days",
        recursive=True,
        groups="account.group_account_readonly,account.group_account_invoice",
    )
    depreciation_paused_days = fields.Float(
        copy=False,
        groups="account.group_account_readonly,account.group_account_invoice",
    )

    value_gain_on_sale = fields.Monetary(
        string="Net gain on sale",
        copy=False,
        groups="account.group_account_readonly,account.group_account_invoice",
        help="Net value of gain or loss on sale of an asset",
    )

    linked_assets_ids = fields.Many2many(
        comodel_name="account.depreciation.board",
        compute="_compute_linked_assets",
        groups="account.group_account_readonly,account.group_account_invoice",
    )
    count_linked_asset = fields.Count(
        count_of="linked_assets_ids",
        groups="account.group_account_readonly,account.group_account_invoice",
    )
    warning_count_assets = fields.Boolean(
        compute="_compute_linked_assets",
        groups="account.group_account_readonly,account.group_account_invoice",
    )

    PROPAGATED_TO_MOVES = frozenset(
        {
            "analytic_distribution",
            "account_depreciation_id",
            "account_depreciation_expense_id",
            "depreciation_journal_id",
        }
    )

    FISCALYEAR_MEMO_KEY = "account_depreciation.fiscalyear_dates"

    CREATION_TRACKED_FNAMES = (
        "depreciation_method",
        "depreciation_duration",
        "depreciation_period",
        "depreciation_factor",
        "value_salvage",
        "original_move_line_ids",
    )

    @api.constrains("depreciation_move_ids")
    def _check_depreciations(self):
        for asset in self:
            if (
                asset.depreciation_state == "open"
                and asset.depreciation_move_ids
                and not asset.currency_id.is_zero(
                    asset.depreciation_move_ids._sorted_by_date()[
                        -1
                    ].asset_remaining_value
                )
            ):
                _debug.logic("board.refused", reason="remaining_value", board=asset)
                raise UserError(
                    _("The remaining value on the last depreciation line must be 0")
                )

    @api.constrains("depreciation_state", "company_id", "date_prorata")
    def _check_board_has_company_and_start(self):
        for asset in self.filtered("depreciation_state"):
            if not asset.company_id:
                _debug.logic("board.refused", reason="no_company", board=asset)
                raise ValidationError(
                    _("%(asset)s depreciates, so it needs a company.", asset=asset.name)
                )
            if not asset.date_prorata:
                _debug.logic("board.refused", reason="no_prorata_date", board=asset)
                raise ValidationError(
                    _(
                        "%(asset)s depreciates, so it needs a prorata date.",
                        asset=asset.name,
                    )
                )

    @api.constrains("original_move_line_ids")
    def _check_single_source_account(self):
        for asset in self:
            if len(asset.original_move_line_ids.account_id) > 1:
                _debug.logic("bills.refused", reason="several_accounts", board=asset)
                raise ValidationError(
                    _("All the lines should be from the same account")
                )

    @api.constrains("original_move_line_ids")
    def _check_related_purchase(self):
        for asset in self:
            if asset.original_move_line_ids and asset.value_purchase == 0:
                _debug.logic("bills.refused", reason="null_purchase_value", board=asset)
                raise UserError(
                    _(
                        "You cannot create an asset from lines containing credit and debit on the account or with a null amount"
                    )
                )
            if asset.depreciation_state not in (False, "draft"):
                _debug.logic(
                    "bills.refused",
                    reason="board_running",
                    board=asset,
                    state=asset.depreciation_state,
                )
                raise UserError(
                    _(
                        "You cannot add or remove bills when the asset is already running or closed."
                    )
                )

    @api.model_create_multi
    def create(self, vals_list):
        vals_list = [dict(vals) for vals in vals_list]
        fallback_kind = None
        for vals in vals_list:
            state = vals.get("depreciation_state")
            if state and state != "draft":
                _debug.logic("create.refused", reason="state_given", state=state)
                raise UserError(
                    _(
                        "An asset is created in draft and confirmed afterwards; it cannot "
                        "be created directly in the %(state)s state.",
                        state=state,
                    )
                )
            vals["depreciation_state"] = "draft"
            if vals.get("asset_id"):
                continue
            if not vals.get("name"):
                vals["name"] = self._get_name_from_lines(vals)
            if not vals.get("name"):
                _debug.logic("create.refused", reason="no_name")
                raise UserError(_("An asset needs a name."))
            if not vals.get("kind_id"):
                profile = self.env["account.depreciation.profile"].browse(
                    vals.get("depreciation_profile_id")
                )
                if not profile.kind_id and fallback_kind is None:
                    fallback_kind = self.env.ref(
                        "account_depreciation.kind_fixed_asset"
                    )
                vals["kind_id"] = (profile.kind_id or fallback_kind).id
        boards = super(
            AccountDepreciationBoard, self.with_context(mail_create_nolog=True)
        ).create(vals_list)
        _debug.lifecycle(
            "create",
            boards=boards,
            on_existing_assets=sum(1 for vals in vals_list if vals.get("asset_id")),
        )
        for board, vals in zip(boards, vals_list, strict=True):
            requested = vals.get("value_original")
            if requested is not None and board.currency_id.compare_amounts(
                board.value_original, requested
            ):
                board.value_original = requested
        return boards

    def copy_data(self, default=None):
        # The asset copies itself (its resource, its identifiers); the board
        # copies its own fields and points at that copy.
        default = dict(default or {})
        asset_default = {
            name: default.pop(name)
            for name in list(default)
            if self._fields[name].inherited
        }
        vals_list = super().copy_data(default)
        inherited = [name for name, field in self._fields.items() if field.inherited]
        _debug.lifecycle("copy_data", boards=self, asset_defaults=sorted(asset_default))
        for board, vals in zip(self, vals_list, strict=True):
            for name in inherited:
                vals.pop(name, None)
            vals["asset_id"] = board.asset_id.copy(
                {
                    "name": _("%s (copy)", board.name),
                    "value_original": board.value_original,
                    **asset_default,
                }
            ).id
            vals["account_asset_id"] = board.account_asset_id.id
        return vals_list

    def unlink(self):
        bodies = {}
        orphaned_moves = self.env["account.move"]
        for asset in self:
            for line in asset.original_move_line_ids:
                if line.name:
                    body = _(
                        "A document linked to %(move_line_name)s has been deleted: %(link)s",
                        move_line_name=line.name,
                        link=asset._get_html_link(),
                    )
                else:
                    body = _(
                        "A document linked to this move has been deleted: %s",
                        asset._get_html_link(),
                    )
                bodies[line.move_id.id] = (
                    bodies[line.move_id.id] + Markup("<br>") + body
                    if line.move_id.id in bodies
                    else body
                )
                if not (line.move_id.capitalised_board_ids - self):
                    orphaned_moves |= line.move_id
        if bodies:
            self.env["account.move"].browse(bodies)._message_log_batch(bodies=bodies)
        orphaned_moves.asset_move_type = False
        _debug.lifecycle(
            "unlink", boards=self, bills_noted=len(bodies), orphaned=orphaned_moves
        )
        return super().unlink()

    @api.ondelete(at_uninstall=True)
    def _unlink_if_model_or_draft(self):
        for asset in self:
            if asset.depreciation_state in ["open", "paused", "close"]:
                _debug.logic(
                    "unlink.refused",
                    reason="state",
                    board=asset,
                    state=asset.depreciation_state,
                )
                raise UserError(
                    _(
                        "You cannot delete a document that is in %s state.",
                        dict(
                            self._fields["depreciation_state"]._description_selection(
                                self.env
                            )
                        ).get(asset.depreciation_state),
                    )
                )

            posted_amount = len(
                asset.depreciation_move_ids.filtered(lambda x: x.state == "posted")
            )
            if posted_amount > 0:
                _debug.logic("unlink.refused", reason="posted_entries", board=asset)
                raise UserError(
                    _(
                        "You cannot delete an asset linked to posted entries."
                        "\nYou should either confirm the asset, then, sell or dispose of it,"
                        " or cancel the linked journal entries."
                    )
                )

    @api.depends("company_id")
    def _compute_depreciation_journal_id(self):
        AccountJournal = self.env["account.journal"]
        needs_default = self.filtered(
            lambda asset: (
                asset.depreciation_state
                and asset.depreciation_journal_id.company_id != asset.company_id
            )
        )
        default_per_company = {}
        for company in needs_default.company_id:
            default_per_company[company] = AccountJournal.search(  # noqa: E8507  one search per distinct company, not per asset
                [
                    *AccountJournal._check_company_domain(company),
                    ("type", "=", "general"),
                ],
                limit=1,
            )
        for asset in needs_default:
            asset.depreciation_journal_id = default_per_company[asset.company_id]

    @api.depends("value_salvage", "value_original")
    def _compute_total_depreciable_value(self):
        for asset in self:
            asset.value_depreciable = asset.value_original - asset.value_salvage

    @api.depends("value_original", "depreciation_profile_id")
    def _compute_salvage_value(self):
        for asset in self:
            pct = asset.depreciation_profile_id.value_salvage_pct
            if not float_is_zero(pct, precision_digits=6):
                asset.value_salvage = asset.value_original * pct

    @api.depends("original_move_line_ids")
    def _compute_display_account_asset_id(self):
        for record in self:
            record.display_account_asset_id = not record.original_move_line_ids

    @api.depends(
        "account_depreciation_id",
        "account_depreciation_expense_id",
        "original_move_line_ids",
    )
    def _compute_account_asset_id(self):
        for record in self:
            if record.original_move_line_ids:
                record.account_asset_id = record.original_move_line_ids.account_id[:1]
            elif not record.account_asset_id:
                record.account_asset_id = record.account_depreciation_id

    @api.depends(
        "depreciation_duration",
        "depreciation_period",
        "depreciation_prorata",
        "date_prorata",
        "increased_board_id",
        "increased_board_id.depreciation_lifetime_days",
        "increased_board_id.date_prorata_paused",
    )
    @_debug.perf.timed
    def _compute_lifetime_days(self):
        for asset in self:
            if not asset.depreciation_state or not asset.date_prorata:
                asset.depreciation_lifetime_days = 0.0
            elif not asset.increased_board_id:
                if asset.depreciation_prorata == "daily_computation":
                    asset.depreciation_lifetime_days = (
                        asset.date_prorata
                        + relativedelta(
                            months=int(asset.depreciation_period)
                            * asset.depreciation_duration
                        )
                        - asset.date_prorata
                    ).days
                else:
                    asset.depreciation_lifetime_days = (
                        int(asset.depreciation_period)
                        * asset.depreciation_duration
                        * DAYS_PER_MONTH
                    )
            else:
                if asset.depreciation_prorata == "daily_computation":
                    parent_end_date = (
                        asset.increased_board_id.date_prorata_paused
                        + relativedelta(
                            days=int(
                                asset.increased_board_id.depreciation_lifetime_days - 1
                            )
                        )
                    )
                else:
                    parent_end_date = (
                        asset.increased_board_id.date_prorata_paused
                        + relativedelta(
                            months=int(
                                asset.increased_board_id.depreciation_lifetime_days
                                / DAYS_PER_MONTH
                            ),
                            days=int(
                                asset.increased_board_id.depreciation_lifetime_days
                                % DAYS_PER_MONTH
                            )
                            - 1,
                        )
                    )
                asset.depreciation_lifetime_days = asset._get_delta_days(
                    asset.date_prorata, parent_end_date
                )

    @api.depends("date_acquisition", "company_id", "depreciation_prorata")
    def _compute_prorata_date(self):
        for asset in self:
            if not asset.depreciation_state:
                asset.date_prorata = asset.date_prorata
            elif asset.depreciation_prorata == "none" and asset.date_acquisition:
                fiscalyear_date = asset._get_fiscalyear_dates(
                    asset.date_acquisition
                ).get("date_from")
                asset.date_prorata = fiscalyear_date
            else:
                asset.date_prorata = asset.date_acquisition

    @api.depends("date_prorata", "depreciation_prorata", "depreciation_paused_days")
    def _compute_paused_prorata_date(self):
        for asset in self:
            if not asset.date_prorata:
                asset.date_prorata_paused = False
            elif asset.depreciation_prorata == "daily_computation":
                asset.date_prorata_paused = asset.date_prorata + relativedelta(
                    days=asset.depreciation_paused_days
                )
            else:
                asset.date_prorata_paused = asset.date_prorata + relativedelta(
                    months=int(asset.depreciation_paused_days / DAYS_PER_MONTH),
                    days=asset.depreciation_paused_days % DAYS_PER_MONTH,
                )

    @api.depends(
        "original_move_line_ids",
        "original_move_line_ids.balance",
        "original_move_line_ids.deductible_amount",
        "original_move_line_ids.quantity",
    )
    def _compute_related_purchase_value(self):
        for asset in self:
            value_purchase = sum(
                line.balance * line.deductible_amount / 100
                for line in asset.original_move_line_ids
            )
            if (
                asset.account_asset_id.multiple_assets_per_line
                and len(asset.original_move_line_ids) == 1
            ):
                value_purchase /= max(1, int(asset.original_move_line_ids.quantity))
            asset.value_purchase = value_purchase

    @api.depends(
        "value_original",
        "value_salvage",
        "value_depreciated_import",
        "depreciation_move_ids.state",
        "depreciation_move_ids.depreciation_value",
        "depreciation_move_ids.reversal_move_ids",
    )
    @_debug.perf.timed
    def _compute_value_depreciable_residual(self):
        grouped_moves = self.env["account.move"]._read_group(
            domain=[
                ("depreciation_board_id", "in", self.ids),
                ("state", "=", "posted"),
            ],
            groupby=["depreciation_board_id"],
            aggregates=["depreciation_value:sum"],
        )
        depreciation_sum_by_asset = {asset.id: total for asset, total in grouped_moves}
        _debug.perf.count(
            "posted_depreciation_summed", boards=self, groups=len(grouped_moves)
        )
        for record in self:
            asset_depreciation = depreciation_sum_by_asset.get(record.id, 0.0)
            record.value_depreciable_residual = (
                record.value_original
                - record.value_salvage
                - record.value_depreciated_import
                - asset_depreciation
            )

    @api.depends(
        "value_depreciable_residual",
        "value_salvage",
        "increase_ids.value_book",
        "depreciation_state",
        "depreciation_move_ids.state",
    )
    @_debug.perf.timed
    def _compute_book_value(self):
        for record in self:
            record.value_book = (
                record.value_depreciable_residual
                + record.value_salvage
                + sum(record.increase_ids.mapped("value_book"))
            )
            if record.depreciation_state == "close" and all(
                move.state == "posted" for move in record.depreciation_move_ids
            ):
                record.value_book -= record.value_salvage

    @api.depends("increase_ids.value_original")
    def _compute_gross_increase_value(self):
        for record in self:
            record.value_increase = sum(record.increase_ids.mapped("value_original"))

    @api.depends(
        "original_move_line_ids",
        "original_move_line_ids.non_deductible_tax_value",
        "original_move_line_ids.deductible_amount",
        "original_move_line_ids.quantity",
    )
    @_debug.perf.timed
    def _compute_value_non_deductible_tax(self):
        for record in self:
            record.value_non_deductible_tax = 0.0
            for line in record.original_move_line_ids:
                if line.non_deductible_tax_value:
                    account = line.account_id
                    auto_create_multi = (
                        account.create_asset != "no"
                        and account.multiple_assets_per_line
                    )
                    quantity = line.quantity if auto_create_multi else 1
                    converted_non_deductible_tax_value = line.currency_id._convert(
                        line.non_deductible_tax_value / quantity,
                        record.currency_id,
                        record.company_id,
                        line.date,
                    )
                    converted_non_deductible_tax_value *= line.deductible_amount / 100
                    record.value_non_deductible_tax += record.currency_id.round(
                        converted_non_deductible_tax_value
                    )

    @api.depends("depreciation_move_ids.state")
    def _compute_depreciation_entries_count(self):
        depreciation_per_asset = {
            group.id: count
            for group, count in self.env["account.move"]._read_group(
                domain=[
                    ("depreciation_board_id", "in", self.ids),
                    ("state", "=", "posted"),
                ],
                groupby=["depreciation_board_id"],
                aggregates=["__count"],
            )
        }
        for asset in self:
            asset.count_depreciation_posted = depreciation_per_asset.get(asset.id, 0)

    @api.depends("original_move_line_ids.capitalised_board_ids")
    def _compute_linked_assets(self):
        for asset in self:
            asset.linked_assets_ids = (
                asset.original_move_line_ids.capitalised_board_ids - asset
            )
            confirmed_assets = asset.linked_assets_ids.filtered(
                lambda x: x.depreciation_state == "open"
            )
            asset.warning_count_assets = len(confirmed_assets) > 0

    @api.onchange("value_original", "original_move_line_ids")
    def _display_original_value_warning(self):
        if self.original_move_line_ids:
            computed_original_value = (
                self.value_purchase + self.value_non_deductible_tax
            )
            if self.value_original != computed_original_value:
                warning = {
                    "title": _("Warning for the Original Value of %s", self.name),
                    "message": _(
                        "The amount you have entered (%(entered_amount)s) does not match the Related Purchase's value (%(purchase_value)s). "
                        "Please make sure this is what you want.",
                        entered_amount=formatLang(
                            self.env, self.value_original, currency_obj=self.currency_id
                        ),
                        purchase_value=formatLang(
                            self.env,
                            computed_original_value,
                            currency_obj=self.currency_id,
                        ),
                    ),
                }
                return {"warning": warning}
        return None

    @api.onchange("original_move_line_ids")
    def _onchange_original_move_line_ids(self):
        if self.original_move_line_ids:
            self.date_acquisition = min(
                [(aml.invoice_date or aml.date) for aml in self.original_move_line_ids]
                + [fields.Date.today()]
            )
        if not self.name and self.original_move_line_ids:
            self.name = self.original_move_line_ids[0].name

    @api.onchange("account_asset_id")
    def _onchange_account_asset_id(self):
        self.account_depreciation_id = (
            self.account_depreciation_id or self.account_asset_id
        )

    @api.onchange("depreciation_profile_id")
    def _onchange_depreciation_profile_id(self):
        if self.depreciation_profile_id:
            defaults = self.depreciation_profile_id._get_asset_defaults()
            defaults.pop("analytic_distribution", None)
            self.update(defaults)
            self.analytic_distribution = (
                self.depreciation_profile_id.analytic_distribution
                or self.analytic_distribution
            )

    @api.onchange(
        "value_original",
        "value_salvage",
        "date_acquisition",
        "depreciation_method",
        "depreciation_factor",
        "depreciation_period",
        "depreciation_duration",
        "depreciation_prorata",
        "value_depreciated_import",
        "date_prorata",
    )
    def _onchange_consistent_board(self):
        self.write({"depreciation_move_ids": [Command.set([])]})

    def action_view_linked_assets(self):
        return self.linked_assets_ids.open_board(["list", "form"])

    def action_asset_modify(self):
        self.check_singleton()
        new_wizard = self.env["asset.modify"].create(
            {
                "asset_id": self.id,
                "modify_action": "resume"
                if self.env.context.get("resume_after_pause")
                else "dispose",
            }
        )
        return {
            "name": _("Modify Asset"),
            "view_mode": "form",
            "res_model": "asset.modify",
            "type": "ir.actions.act_window",
            "target": "new",
            "res_id": new_wizard.id,
            "context": self.env.context,
        }

    def action_save_profile(self):
        self.check_singleton()
        profile = self.env["account.depreciation.profile"].create(
            self._get_profile_values()
        )
        self.depreciation_profile_id = profile
        return {
            "name": _("Depreciation Profile"),
            "type": "ir.actions.act_window",
            "res_model": "account.depreciation.profile",
            "res_id": profile.id,
            "views": [(False, "form")],
        }

    def action_dispose(self):
        return self.asset_id.action_dispose()

    def _dispose(self, date=None):
        return self.asset_id._dispose(date)

    def action_compute_depreciation(self):
        return self._create_depreciation_entries()

    def action_confirm(self):
        if not self:
            return
        self.write({"depreciation_state": "open"})
        self.asset_id.filtered(lambda asset: asset.state == "draft")._transition(
            "in_service"
        )
        _debug.lifecycle("confirm", boards=self)
        self._log_asset_created()
        try:
            with self.env.cr.savepoint():
                boardless = self.filtered(lambda asset: not asset.depreciation_move_ids)
                if boardless:
                    boardless._create_depreciation_entries()
                self._check_depreciations()
                unposted = self.depreciation_move_ids.filtered(
                    lambda move: move.state != "posted"
                )
                if unposted:
                    unposted._post()
        except psycopg.errors.CheckViolation:
            _debug.logic("confirm.refused", reason="check_violation", boards=self)
            raise ValidationError(
                _(
                    "At least one asset (%s) couldn't be set as running because it lacks any required information",
                    ", ".join(self.mapped("name")),
                )
            ) from None

        for asset in self.filtered(
            lambda asset: asset.account_asset_id.create_asset == "no"
        ):
            asset._post_non_deductible_tax_value()

    def action_cancel(self):
        for asset in self:
            posted_moves = asset.depreciation_move_ids.filtered(
                lambda m: m._is_effective_depreciation()
            )
            if posted_moves:
                depreciation_change = sum(
                    posted_moves.line_ids.mapped(
                        lambda l: (
                            l.debit
                            if l.account_id == asset.account_depreciation_expense_id  # noqa: B023  the lambda runs inside this iteration
                            else 0.0
                        )
                    )
                )
                acc_depreciation_change = sum(
                    posted_moves.line_ids.mapped(
                        lambda l: (
                            l.credit
                            if l.account_id == asset.account_depreciation_id  # noqa: B023  the lambda runs inside this iteration
                            else 0.0
                        )
                    )
                )
                entries = Markup("<br>").join(
                    posted_moves._sorted_by_date().mapped(
                        lambda m: (
                            f"{m.ref} - {m.date} - "
                            f"{formatLang(self.env, m.depreciation_value, currency_obj=m.currency_id)} - "
                            f"{m.name}"
                        )
                    )
                )
                asset._cancel_future_moves(datetime.date.min)
                msg = (
                    _("Asset Cancelled")
                    + Markup("<br>")
                    + _(
                        "The account %(exp_acc)s has been credited by %(exp_delta)s, "
                        "while the account %(dep_acc)s has been debited by %(dep_delta)s. "
                        "This corresponds to %(move_count)s cancelled %(word)s:",
                        exp_acc=asset.account_depreciation_expense_id.display_name,
                        exp_delta=formatLang(
                            self.env,
                            depreciation_change,
                            currency_obj=asset.currency_id,
                        ),
                        dep_acc=asset.account_depreciation_id.display_name,
                        dep_delta=formatLang(
                            self.env,
                            acc_depreciation_change,
                            currency_obj=asset.currency_id,
                        ),
                        move_count=len(posted_moves),
                        word=_("entries") if len(posted_moves) > 1 else _("entry"),
                    )
                    + Markup("<br>")
                    + entries
                )
                asset._message_log(body=msg)
            else:
                asset._message_log(body=_("Asset Cancelled"))
            asset.depreciation_move_ids.filtered(
                lambda m: m.state == "draft"
            ).with_context(force_delete=True).unlink()
            asset.depreciation_paused_days = 0
            asset.write({"depreciation_state": "cancelled"})
            _debug.lifecycle("cancel", board=asset, reversed_entries=len(posted_moves))

    def action_reset_to_draft(self):
        self.write({"depreciation_state": "draft"})

    def action_reopen(self):
        self.check_singleton()
        if self.depreciation_move_ids and not self.currency_id.is_zero(
            self.depreciation_move_ids._sorted_by_date()[-1].asset_remaining_value
        ):
            self.env["asset.modify"].create(
                {"asset_id": self.id, "name": _("Reset to running")}
            ).action_modify()
        self.write({"depreciation_state": "open", "value_gain_on_sale": 0})
        if self.state == "disposed":
            self.asset_id.with_context(board_lifecycle=True).write(
                {"state": "in_service", "date_disposal": False, "active": True}
            )

    def action_resume(self):
        self.check_singleton()
        return self.with_context(resume_after_pause=True).action_asset_modify()

    def _create_depreciation_entries(self, date=False):
        self.depreciation_move_ids.filtered(
            lambda mv: mv.state == "draft" and (mv.date >= date if date else True)
        ).unlink()

        new_depreciation_moves_data = []
        with self._shared_fiscalyear_dates():
            for asset in self:
                new_depreciation_moves_data.extend(asset._recompute_board(date))

        new_depreciation_moves = self.env["account.move"].create(
            new_depreciation_moves_data
        )
        new_depreciation_moves_to_post = new_depreciation_moves.filtered(
            lambda move: move.depreciation_board_id.depreciation_state == "open"
        )
        new_depreciation_moves_to_post._post()
        _debug.pipeline(
            "entries_created",
            boards=self,
            entries=new_depreciation_moves,
            posted=len(new_depreciation_moves_to_post),
            from_date=date or None,
        )

    @contextmanager
    def _shared_fiscalyear_dates(self):
        cache = self.env.cr.cache
        if self.FISCALYEAR_MEMO_KEY in cache:
            yield
            return
        cache[self.FISCALYEAR_MEMO_KEY] = {}
        try:
            yield
        finally:
            cache.pop(self.FISCALYEAR_MEMO_KEY, None)

    def _add_depreciation_line(
        self, amount, beginning_depreciation_date, depreciation_date, days_depreciated
    ):
        self.check_singleton()
        AccountMove = self.env["account.move"]

        return AccountMove.create(
            AccountMove._prepare_move_for_asset_depreciation(
                {
                    "amount": amount,
                    "asset_id": self,
                    "depreciation_beginning_date": beginning_depreciation_date,
                    "date": depreciation_date,
                    "asset_number_days": days_depreciated,
                }
            )
        )

    @api.model
    def _create_from_plans(self, plans):
        # A plan's board lands on the asset the bill line names, on a component of
        # it, or on a new asset; every further board of the same line is a
        # component of the one that landed first.
        Board = self.with_context(clean_context(self.env.context))
        landed = {}
        boards = self.browse()
        for plan in plans:
            named = plan["named_asset"]
            vals = dict(plan["vals"])
            root = landed.get(plan["unit"])
            if plan["component_of_unit"] and root:
                vals["parent_id"] = root.asset_id.id
                vals["name"] = self._component_name(root, plan["profile"])
                board = Board.create({**vals, "created_asset": True})
            elif named and not named.board_id:
                board = Board.create({**vals, "asset_id": named.id})
            elif named:
                vals["parent_id"] = named.id
                vals["name"] = self._component_name(named, plan["profile"])
                board = Board.create({**vals, "created_asset": True})
            else:
                board = Board.create({**vals, "created_asset": True})
            landed.setdefault(plan["unit"], board)
            boards |= board
            plan["board"] = board
        to_validate = self.browse()
        for plan in plans:
            board = plan["board"]
            if plan["profile"] and plan["validate"]:
                to_validate |= board
            if plan["move"]:
                board.message_post(
                    body=_(
                        "Asset created from invoice: %s", plan["move"]._get_html_link()
                    )
                )
                board._post_non_deductible_tax_value()
        to_validate.action_confirm()
        _debug.pipeline(
            "plans_landed",
            plans=len(plans),
            boards=boards,
            confirmed=len(to_validate),
            landed_units=len(landed),
        )
        return boards

    def _create_move_before_date(self, date):
        all_move_dates_before_date = self.depreciation_move_ids.filtered(
            lambda x: x.date <= date and x._is_effective_depreciation()
        ).mapped("date")

        beginning_fiscal_year = (
            self._get_fiscalyear_dates(date).get("date_from")
            if self.depreciation_method != "linear"
            else False
        )
        if beginning_fiscal_year:
            beginning_fiscal_year = max(beginning_fiscal_year, self.date_prorata_paused)
        first_fiscalyear_move = self.env["account.move"]
        if all_move_dates_before_date:
            last_move_date_not_reversed = max(all_move_dates_before_date)
            future_moves_beginning_date = self.depreciation_move_ids.filtered(
                lambda m: (
                    m.date > last_move_date_not_reversed
                    and (m._is_effective_depreciation() or m.state == "draft")
                )
            ).mapped("asset_depreciation_beginning_date")
            beginning_depreciation_date = (
                min(future_moves_beginning_date)
                if future_moves_beginning_date
                else self.date_prorata_paused
            )

            if self.depreciation_method != "linear":
                first_moves = self.depreciation_move_ids.filtered(
                    lambda m: (
                        m.asset_depreciation_beginning_date >= beginning_fiscal_year
                        and (m._is_effective_depreciation() or m.state == "draft")
                    )
                ).sorted(lambda m: (m.asset_depreciation_beginning_date, m.id))
                first_fiscalyear_move = next(iter(first_moves), first_fiscalyear_move)
        else:
            beginning_depreciation_date = self.date_prorata_paused

        residual_declining = (
            first_fiscalyear_move.asset_remaining_value
            + first_fiscalyear_move.depreciation_value
        )
        self._cancel_future_moves(date)

        imported_amount = (
            self.value_depreciated_import if not all_move_dates_before_date else 0
        )
        value_depreciable_residual = (
            self.value_depreciable_residual + self.value_depreciated_import
            if not all_move_dates_before_date
            else self.value_depreciable_residual
        )
        residual_declining = residual_declining or value_depreciable_residual

        last_day_asset = self._get_last_day_asset()
        lifetime_left = self._get_delta_days(
            beginning_depreciation_date, last_day_asset
        )
        days_depreciated, amount = self._get_board_amount(
            self.value_depreciable_residual,
            beginning_depreciation_date,
            date,
            lifetime_left,
            residual_declining,
            beginning_fiscal_year,
            LinearRecompute(
                start_date=beginning_depreciation_date,
                residual=value_depreciable_residual,
                lifetime_left=lifetime_left,
            ),
        )

        if abs(imported_amount) <= abs(amount):
            amount -= imported_amount
        _debug.pipeline(
            "entry_before_date",
            board=self,
            date=date,
            days=days_depreciated,
            amount=amount,
            imported=imported_amount,
        )
        if not float_is_zero(amount, precision_rounding=self.currency_id.rounding):
            new_line = self._add_depreciation_line(
                amount, beginning_depreciation_date, date, days_depreciated
            )
            new_line._post()

    def _cancel_future_moves(self, date):
        for asset in self:
            obsolete_moves = asset.depreciation_move_ids.filtered(
                lambda m: (
                    m.state == "draft"
                    or (m._is_effective_depreciation() and m.date > date)
                )
            )
            _debug.lifecycle(
                "future_entries_cancelled", board=asset, entries=obsolete_moves
            )
            obsolete_moves._unlink_or_reverse()

    @api.model
    def _component_name(self, parent, profile):
        if not profile:
            return parent.name
        return f"{parent.name} — {profile.name}"

    def _clamp_to_original_sign(self, value):
        self.check_singleton()
        if self.currency_id.compare_amounts(self.value_original, 0) > 0:
            return max(value, 0)
        return min(value, 0)

    def _close(self, invoice_line_ids, date=None, message=None):
        self.check_singleton()
        date_disposal = date or fields.Date.today()
        if date_disposal <= self.company_id._get_user_fiscal_lock_date(
            self.depreciation_journal_id
        ):
            _debug.logic(
                "close.refused",
                reason="before_lock_date",
                board=self,
                date=date_disposal,
            )
            raise UserError(_("You cannot dispose of an asset before the lock date."))
        if invoice_line_ids and self.increase_ids.filtered(
            lambda a: (
                a.depreciation_state in ("draft", "open")
                or a.value_depreciable_residual > 0
            )
        ):
            _debug.logic("close.refused", reason="running_increase", board=self)
            raise UserError(
                _(
                    "You cannot automate the journal entry for an asset that has a running gross increase. Please use 'Dispose' on the increase(s)."
                )
            )
        full_asset = (self + self.increase_ids).filtered(
            lambda asset: asset.depreciation_state not in ("close", "cancelled")
        )
        full_asset.depreciation_state = "close"
        _debug.pipeline(
            "close",
            board=self,
            increases=len(full_asset) - 1,
            sold=bool(invoice_line_ids),
            date=date_disposal,
        )
        move_ids = full_asset._get_disposal_moves(
            [
                invoice_line_ids if asset == self else self.env["account.move.line"]
                for asset in full_asset
            ],
            date_disposal,
        )
        if invoice_line_ids:
            invoice_moves = invoice_line_ids.move_id
            invoice_links = Markup(", ").join(
                move._get_html_link() for move in invoice_moves
            )
            asset_body = self.env._(
                "Asset sold. %(message)s See %(invoice_links)s",
                message=message or "",
                invoice_links=invoice_links,
            )
            invoice_body = self.env._("Asset sold: %s", self._get_html_link())
            invoice_moves._message_log_batch(
                bodies={invoice.id: invoice_body for invoice in invoice_moves}
            )
        else:
            asset_body = self.env._(
                "Asset disposed. %(message)s",
                message=message or "",
            )

        full_asset._message_log_batch(
            bodies={asset.id: asset_body for asset in full_asset}
        )
        # The asset's lifecycle is written on the asset, in one write, so its
        # disposal constraint sees the date beside the state.
        full_asset.asset_id.with_context(board_lifecycle=True).write(
            {"state": "disposed", "active": False, "date_disposal": date_disposal}
        )

        selling_price = abs(
            sum(invoice_line.balance for invoice_line in invoice_line_ids)
        )
        self.value_gain_on_sale = self.currency_id.round(
            selling_price - self.value_book
        )

        if move_ids:
            name = _("Disposal Move")
            view_mode = "form"
            if len(move_ids) > 1:
                name = _("Disposal Moves")
                view_mode = "list,form"
            return {
                "name": name,
                "view_mode": view_mode,
                "res_model": "account.move",
                "type": "ir.actions.act_window",
                "target": "current",
                "res_id": move_ids[0],
                "domain": [("id", "in", move_ids)],
            }
        return None

    def _log_asset_created(self):
        tracked_fnames = list(self.CREATION_TRACKED_FNAMES)
        ref_tracked_fields = self.fields_get(tracked_fnames)
        for asset in self:
            tracked_fields = ref_tracked_fields.copy()
            if asset.depreciation_method == "linear":
                del tracked_fields["depreciation_factor"]
            _dummy, tracking_value_ids = asset._mail_track(
                tracked_fields, dict.fromkeys(tracked_fnames)
            )
            asset.message_post(
                body=_("Asset created"), tracking_value_ids=tracking_value_ids
            )
            move_body = _("An asset has been created for this move: %s") % (
                asset._get_html_link()
            )
            for move_id in asset.original_move_line_ids.mapped("move_id"):
                move_id.message_post(body=move_body)

    def open_board(self, view_mode):
        if len(self) == 1:
            view_mode = ["form"]
        views = [v for v in self._get_depreciation_views() if v[1] in view_mode]
        ctx = dict(self.env.context)
        ctx.pop("default_move_type", None)
        return {
            "name": _("Asset"),
            "view_mode": ",".join(view_mode),
            "type": "ir.actions.act_window",
            "res_id": self.id if len(self) == 1 else False,
            "res_model": "account.depreciation.board",
            "views": views,
            "domain": [("id", "in", self.ids)],
            "context": ctx,
        }

    def open_entries(self):
        return {
            "name": _("Journal Entries"),
            "view_mode": "list,form",
            "res_model": "account.move",
            "search_view_id": [
                self.env.ref("account.view_account_move_filter").id,
                "search",
            ],
            "views": [
                (self.env.ref("account.view_move_tree").id, "list"),
                (False, "form"),
            ],
            "type": "ir.actions.act_window",
            "domain": [("id", "in", self.depreciation_move_ids.ids)],
            "context": dict(self.env.context, create=False),
        }

    def open_related_entries(self):
        return {
            "name": _("Journal Items"),
            "view_mode": "list,form",
            "res_model": "account.move.line",
            "view_id": False,
            "type": "ir.actions.act_window",
            "domain": [("id", "in", self.original_move_line_ids.ids)],
        }

    def open_increase(self):
        result = {
            "name": _("Gross Increase"),
            "view_mode": "list,form",
            "res_model": "account.depreciation.board",
            "context": {**self.env.context, "create": False},
            "view_id": False,
            "type": "ir.actions.act_window",
            "domain": [("id", "in", self.increase_ids.ids)],
            "views": self._get_depreciation_views(),
        }
        if len(self.increase_ids) == 1:
            result["views"] = self._get_depreciation_views()[1:]
            result["res_id"] = self.increase_ids.id
        return result

    def open_increased_asset(self):
        return {
            "name": _("Parent Asset"),
            "view_mode": "form",
            "res_model": "account.depreciation.board",
            "type": "ir.actions.act_window",
            "res_id": self.increased_board_id.id,
            "views": self._get_depreciation_views()[1:],
        }

    def _pause(self, date, message=None):
        self.check_singleton()
        self._create_move_before_date(date)
        self.write({"depreciation_state": "paused"})
        _debug.lifecycle("pause", board=self, date=date)
        self.message_post(body=_("Asset paused. %s", message or ""))

    def _recompute_board(self, start_depreciation_date=False):
        self.check_singleton()
        posted_depreciation_move_ids = self.depreciation_move_ids.filtered(
            lambda mv: mv.state == "posted" and not mv.asset_value_change
        )._sorted_by_date()

        imported_amount = self.value_depreciated_import
        residual_amount = self.value_depreciable_residual - sum(
            self.depreciation_move_ids.filtered(lambda mv: mv.state == "draft").mapped(
                "depreciation_value"
            )
        )
        if not posted_depreciation_move_ids:
            residual_amount += imported_amount
        residual_declining = residual_amount
        start_depreciation_date = start_yearly_period = (
            start_depreciation_date or self.date_prorata_paused
        )

        last_day_asset = self._get_last_day_asset()
        final_depreciation_date = self._get_end_period_date(last_day_asset)
        linear_recompute = LinearRecompute(
            start_date=start_depreciation_date,
            residual=residual_amount,
            lifetime_left=self._get_delta_days(start_depreciation_date, last_day_asset),
        )

        depreciation_move_values = []
        if not float_is_zero(
            self.value_depreciable_residual,
            precision_rounding=self.currency_id.rounding,
        ):
            while (
                not self.currency_id.is_zero(residual_amount)
                and start_depreciation_date < final_depreciation_date
            ):
                period_end_depreciation_date = self._get_end_period_date(
                    start_depreciation_date
                )
                period_end_fiscalyear_date = self._get_fiscalyear_dates(
                    period_end_depreciation_date
                ).get("date_to")
                lifetime_left = self._get_delta_days(
                    start_depreciation_date, last_day_asset
                )

                days, amount = self._get_board_amount(
                    residual_amount,
                    start_depreciation_date,
                    period_end_depreciation_date,
                    lifetime_left,
                    residual_declining,
                    start_yearly_period,
                    linear_recompute,
                )
                residual_amount -= amount

                if not posted_depreciation_move_ids:
                    if abs(imported_amount) <= abs(amount):
                        amount -= imported_amount
                        imported_amount = 0
                    else:
                        imported_amount -= amount
                        amount = 0

                if (
                    self.depreciation_method == "degressive_then_linear"
                    and final_depreciation_date < period_end_depreciation_date
                ):
                    period_end_depreciation_date = final_depreciation_date

                if not float_is_zero(
                    amount, precision_rounding=self.currency_id.rounding
                ):
                    depreciation_move_values.append(
                        self.env["account.move"]._prepare_move_for_asset_depreciation(
                            {
                                "amount": amount,
                                "asset_id": self,
                                "depreciation_beginning_date": start_depreciation_date,
                                "date": period_end_depreciation_date,
                                "asset_number_days": days,
                            }
                        )
                    )

                if period_end_depreciation_date == period_end_fiscalyear_date:
                    start_yearly_period = self._get_fiscalyear_dates(
                        period_end_depreciation_date + relativedelta(days=1)
                    ).get("date_from")
                    residual_declining = residual_amount

                start_depreciation_date = period_end_depreciation_date + relativedelta(
                    days=1
                )

        _debug.pipeline(
            "board_recomputed",
            board=self,
            method=self.depreciation_method,
            lines=len(depreciation_move_values),
            posted_kept=len(posted_depreciation_move_ids),
            residual=residual_amount,
        )
        return depreciation_move_values

    @api.model
    def _get_depreciation_views(self):
        return [
            (self.env.ref("account_depreciation.view_account_asset_tree").id, "list"),
            (self.env.ref("account_depreciation.view_account_asset_form").id, "form"),
        ]

    def _get_fiscalyear_dates(self, date):
        self.check_singleton()
        memo = self.env.cr.cache.get(self.FISCALYEAR_MEMO_KEY)
        if memo is None:
            return self.company_id.compute_fiscalyear_dates(date)
        key = (self.company_id.id, date)
        if key not in memo:
            memo[key] = self.company_id.compute_fiscalyear_dates(date)
        return dict(memo[key])

    def _get_end_period_date(self, start_depreciation_date):
        self.check_singleton()
        fiscalyear_date = self._get_fiscalyear_dates(start_depreciation_date).get(
            "date_to"
        )
        period_end_depreciation_date = (
            fiscalyear_date
            if start_depreciation_date <= fiscalyear_date
            else fiscalyear_date + relativedelta(years=1)
        )

        if self.depreciation_period == "1":
            max_day_in_month = end_of(
                datetime.date(
                    start_depreciation_date.year, start_depreciation_date.month, 1
                ),
                "month",
            ).day
            period_end_depreciation_date = min(
                start_depreciation_date.replace(day=max_day_in_month),
                period_end_depreciation_date,
            )
        return period_end_depreciation_date

    def _get_delta_days(self, start_date, end_date):
        self.check_singleton()
        if self.depreciation_prorata == "daily_computation":
            return (end_date - start_date).days + 1
        else:
            start_date_days_month = end_of(start_date, "month").day
            start_prorata = (
                start_date_days_month - start_date.day + 1
            ) / start_date_days_month
            end_prorata = end_date.day / end_of(end_date, "month").day
            return sum(
                (
                    start_prorata * DAYS_PER_MONTH,
                    end_prorata * DAYS_PER_MONTH,
                    (end_date.year - start_date.year) * DAYS_PER_YEAR,
                    (end_date.month - start_date.month - 1) * DAYS_PER_MONTH,
                )
            )

    def _get_last_day_asset(self):
        this = self.increased_board_id or self
        return this.date_prorata_paused + relativedelta(
            months=int(this.depreciation_period) * this.depreciation_duration, days=-1
        )

    def _get_profile_values(self):
        self.check_singleton()
        return {
            "name": self.name,
            "company_id": self.company_id.id,
            "depreciation_method": self.depreciation_method,
            "depreciation_duration": self.depreciation_duration,
            "depreciation_period": self.depreciation_period,
            "depreciation_factor": self.depreciation_factor,
            "depreciation_prorata": self.depreciation_prorata,
            "analytic_distribution": self.analytic_distribution,
            "account_asset_id": self.account_asset_id.id,
            "account_depreciation_id": self.account_depreciation_id.id,
            "account_depreciation_expense_id": self.account_depreciation_expense_id.id,
            "depreciation_journal_id": self.depreciation_journal_id.id,
        }

    @api.model
    def _get_name_from_lines(self, vals):
        line_ids = []
        for command in vals.get("original_move_line_ids") or []:
            if command[0] == Command.SET:
                line_ids.extend(command[2])
            elif command[0] == Command.LINK:
                line_ids.append(command[1])
        lines = self.env["account.move.line"].browse(line_ids)
        return lines[:1].name or ""

    def _get_linear_amount(
        self, days_before_period, days_until_period_end, value_depreciable
    ):

        amount_expected_previous_period = (
            value_depreciable * days_before_period / self.depreciation_lifetime_days
        )
        amount_after_expected = (
            value_depreciable * days_until_period_end / self.depreciation_lifetime_days
        )
        number_days_for_period = days_until_period_end - days_before_period
        amount_of_decrease_spread_over_period = [
            number_days_for_period
            * mv.depreciation_value
            / (
                self.depreciation_lifetime_days
                - self._get_delta_days(
                    self.date_prorata_paused, mv.asset_depreciation_beginning_date
                )
            )
            for mv in self.depreciation_move_ids.filtered(
                lambda mv: mv.asset_value_change
            )
        ]
        return self.currency_id.round(
            amount_after_expected
            - self.currency_id.round(amount_expected_previous_period)
            - sum(amount_of_decrease_spread_over_period)
        )

    def _get_board_amount(
        self,
        residual_amount,
        period_start_date,
        period_end_date,
        days_left_to_depreciated,
        residual_declining,
        start_yearly_period=None,
        linear_recompute=None,
    ):

        def _get_max_between_linear_and_degressive(linear_amount):
            fiscalyear_dates = self._get_fiscalyear_dates(period_end_date)
            days_in_fiscalyear = self._get_delta_days(
                fiscalyear_dates["date_from"], fiscalyear_dates["date_to"]
            )

            degressive_total_value = residual_declining * (
                1
                - self.depreciation_factor
                * self._get_delta_days(start_yearly_period, period_end_date)
                / days_in_fiscalyear
            )
            degressive_amount = residual_amount - degressive_total_value
            return self._degressive_linear_amount(
                residual_amount, degressive_amount, linear_amount
            )

        if float_is_zero(self.depreciation_lifetime_days, 2) or float_is_zero(
            residual_amount, 2
        ):
            return 0, 0

        days_until_period_end = self._get_delta_days(
            self.date_prorata_paused, period_end_date
        )
        days_before_period = self._get_delta_days(
            self.date_prorata_paused, period_start_date + relativedelta(days=-1)
        )
        days_before_period = max(days_before_period, 0)
        number_days = days_until_period_end - days_before_period

        if self.depreciation_method == "linear":
            if (
                linear_recompute
                and float_compare(linear_recompute.lifetime_left, 0, 2) > 0
            ):
                computed_linear_amount = residual_amount - linear_recompute.residual * (
                    1
                    - self._get_delta_days(linear_recompute.start_date, period_end_date)
                    / linear_recompute.lifetime_left
                )
            else:
                computed_linear_amount = self._get_linear_amount(
                    days_before_period,
                    days_until_period_end,
                    self.value_depreciable,
                )
            amount = min(computed_linear_amount, residual_amount, key=abs)
        elif self.depreciation_method == "degressive":
            days_left_from_beginning_of_year = (
                self._get_delta_days(
                    start_yearly_period, period_start_date - relativedelta(days=1)
                )
                + days_left_to_depreciated
            )
            expected_remaining_value_with_linear = (
                residual_declining
                - residual_declining
                * self._get_delta_days(start_yearly_period, period_end_date)
                / days_left_from_beginning_of_year
            )
            linear_amount = residual_amount - expected_remaining_value_with_linear

            amount = _get_max_between_linear_and_degressive(linear_amount)
        elif self.depreciation_method == "degressive_then_linear":
            if not self.increased_board_id:
                linear_amount = self._get_linear_amount(
                    days_before_period,
                    days_until_period_end,
                    self.value_depreciable,
                )
            else:
                parent_moves = self.increased_board_id.depreciation_move_ids.filtered(
                    lambda mv: mv.date <= self.date_prorata
                )._sorted_by_date()
                parent_cumulative_depreciation = (
                    parent_moves[-1].asset_depreciated_value
                    if parent_moves
                    else self.increased_board_id.value_depreciated_import
                )
                parent_depreciable_value = (
                    parent_moves[-1].asset_remaining_value
                    if parent_moves
                    else self.increased_board_id.value_depreciable
                )
                if self.currency_id.is_zero(parent_depreciable_value):
                    linear_amount = self._get_linear_amount(
                        days_before_period,
                        days_until_period_end,
                        self.value_depreciable,
                    )
                else:
                    depreciable_value = self.value_depreciable * (
                        1 + parent_cumulative_depreciation / parent_depreciable_value
                    )
                    linear_amount = (
                        self._get_linear_amount(
                            days_before_period, days_until_period_end, depreciable_value
                        )
                        * self.depreciation_lifetime_days
                        / self.increased_board_id.depreciation_lifetime_days
                    )

            amount = _get_max_between_linear_and_degressive(linear_amount)
        else:
            _debug.logic(
                "board.refused",
                reason="unknown_method",
                board=self,
                method=self.depreciation_method,
            )
            raise UserError(
                _(
                    "The depreciation method %s has no board computation.",
                    self.depreciation_method,
                )
            )

        amount = (
            max(amount, 0)
            if self.currency_id.compare_amounts(residual_amount, 0) > 0
            else min(amount, 0)
        )
        amount = self._get_depreciation_amount_end_of_lifetime(
            residual_amount, amount, days_until_period_end
        )

        return number_days, self.currency_id.round(amount)

    def _get_disposal_moves(self, invoice_lines_list, date_disposal):

        def get_line(name, asset, amount, account, is_sale):
            return (
                0,
                0,
                {
                    "name": name,
                    "account_id": account.id,
                    "balance": -amount,
                    "analytic_distribution": analytic_distribution,
                    "currency_id": asset.currency_id.id,
                    "amount_currency": -asset.company_id.currency_id._convert(
                        from_amount=amount,
                        to_currency=asset.currency_id,
                        company=asset.company_id,
                        date=date_disposal,
                    ),
                    "is_storno": asset.company_id.account_config_id.account_storno
                    and is_sale
                    and (
                        account
                        not in (
                            asset.company_id.gain_account_id,
                            asset.company_id.loss_account_id,
                        )
                    ),
                },
            )

        move_ids = []
        for asset, invoice_line_ids in zip(self, invoice_lines_list, strict=True):
            asset._create_move_before_date(date_disposal)

            analytic_distribution = asset.analytic_distribution

            dict_invoice = {}
            invoice_amount = 0

            initial_amount = asset.value_original
            initial_account = (
                asset.original_move_line_ids.account_id
                if len(asset.original_move_line_ids.account_id) == 1
                else asset.account_asset_id
            )

            all_lines_before_disposal = asset.depreciation_move_ids.filtered(
                lambda x: x.date <= date_disposal
            )
            depreciated_amount = asset.currency_id.round(
                copysign(
                    sum(all_lines_before_disposal.mapped("depreciation_value"))
                    + asset.value_depreciated_import,
                    -initial_amount,
                )
            )
            depreciation_account = asset.account_depreciation_id
            for invoice_line in invoice_line_ids:
                dict_invoice[invoice_line.account_id] = copysign(
                    invoice_line.balance, -initial_amount
                ) + dict_invoice.get(invoice_line.account_id, 0)
                invoice_amount += copysign(invoice_line.balance, -initial_amount)
            list_accounts = [
                (amount, account) for account, amount in dict_invoice.items()
            ]
            difference = -initial_amount - depreciated_amount - invoice_amount
            difference_account = (
                asset.company_id.gain_account_id
                if difference > 0
                else asset.company_id.loss_account_id
            )
            line_datas = (
                [
                    (initial_amount, initial_account),
                    (depreciated_amount, depreciation_account),
                ]
                + list_accounts
                + [(difference, difference_account)]
            )
            name = (
                _("%(asset)s: Disposal", asset=asset.name)
                if not invoice_line_ids
                else _("%(asset)s: Sale", asset=asset.name)
            )
            vals = {
                "depreciation_board_id": asset.id,
                "ref": name,
                "asset_depreciation_beginning_date": date_disposal,
                "date": date_disposal,
                "journal_id": asset.depreciation_journal_id.id,
                "move_type": "entry",
                "asset_move_type": "disposal" if not invoice_line_ids else "sale",
                "line_ids": [
                    get_line(name, asset, amount, account, invoice_line_ids)
                    for amount, account in line_datas
                    if account
                ],
            }
            move_ids += self.env["account.move"].create(vals).ids
            _debug.pipeline(
                "disposal_move_prepared",
                board=asset,
                sale=bool(invoice_line_ids),
                lines=len(line_datas),
                difference=difference,
            )

        return move_ids

    def _degressive_linear_amount(
        self, residual_amount, degressive_amount, linear_amount
    ):
        if self.currency_id.compare_amounts(residual_amount, 0) > 0:
            return max(degressive_amount, linear_amount)
        else:
            return min(degressive_amount, linear_amount)

    def _get_depreciation_amount_end_of_lifetime(
        self, residual_amount, amount, days_until_period_end
    ):
        if (
            abs(residual_amount) < abs(amount)
            or days_until_period_end >= self.depreciation_lifetime_days
        ):
            amount = residual_amount
        return amount

    def _get_own_book_value(self, date=None):
        self.check_singleton()
        return (
            self._get_residual_value_at_date(date)
            if date
            else self.value_depreciable_residual
        ) + self.value_salvage

    def _get_residual_value_at_date(self, date):
        current_and_previous_depreciation = self.depreciation_move_ids.filtered(
            lambda mv: (
                mv.asset_depreciation_beginning_date < date and not mv.reversed_entry_id
            )
        ).sorted("asset_depreciation_beginning_date", reverse=True)
        undepreciated_value = (
            self.value_original - self.value_salvage - self.value_depreciated_import
        )
        if not current_and_previous_depreciation:
            return self._clamp_to_original_sign(undepreciated_value)

        if len(current_and_previous_depreciation) > 1:
            previous_value_residual = current_and_previous_depreciation[
                1
            ].asset_remaining_value
        else:
            previous_value_residual = undepreciated_value

        cur_depr_end_date = self._get_end_period_date(date)
        current_depreciation = current_and_previous_depreciation[0]
        cur_depr_beg_date = current_depreciation.asset_depreciation_beginning_date

        rate = self._get_delta_days(cur_depr_beg_date, date) / self._get_delta_days(
            cur_depr_beg_date, cur_depr_end_date
        )
        lost_value_at_date = (
            previous_value_residual - current_depreciation.asset_remaining_value
        ) * rate
        residual_value_at_date = self.currency_id.round(
            previous_value_residual - lost_value_at_date
        )
        return self._clamp_to_original_sign(residual_value_at_date)

    def _post_non_deductible_tax_value(self):
        if self.value_non_deductible_tax:
            currency = self.env.company.currency_id
            msg = _(
                "A non deductible tax value of %(tax_value)s was added to %(name)s's initial value of %(purchase_value)s",
                tax_value=formatLang(
                    self.env, self.value_non_deductible_tax, currency_obj=currency
                ),
                name=self.name,
                purchase_value=formatLang(
                    self.env, self.value_purchase, currency_obj=currency
                ),
            )
            self.message_post(body=msg)

    def write(self, vals):
        propagated = self.PROPAGATED_TO_MOVES & vals.keys()
        if not propagated:
            return super().write(vals)
        previous_accounts = {
            asset.id: (
                asset.account_depreciation_id,
                asset.account_depreciation_expense_id,
            )
            for asset in self
        }
        result = super().write(vals)

        AccountMoveLine = self.env["account.move.line"]
        analytic_lines = AccountMoveLine
        depreciation_lines = AccountMoveLine
        expense_lines = AccountMoveLine
        rejournaled_moves = self.env["account.move"]
        for asset in self:
            lock_date = asset.company_id._get_user_fiscal_lock_date(
                asset.depreciation_journal_id
            )
            depreciation_account, expense_account = previous_accounts[asset.id]
            for move in asset.depreciation_move_ids:
                if move.state == "draft" and "analytic_distribution" in propagated:
                    analytic_lines |= move.line_ids
                if move.date <= lock_date:
                    continue
                if "account_depreciation_id" in propagated:
                    depreciation_lines |= move.line_ids.filtered(
                        lambda line: line.account_id == depreciation_account  # noqa: B023  the lambda runs inside this iteration
                    )
                if "account_depreciation_expense_id" in propagated:
                    expense_lines |= move.line_ids.filtered(
                        lambda line: line.account_id == expense_account  # noqa: B023  the lambda runs inside this iteration
                    )
                if "depreciation_journal_id" in propagated:
                    rejournaled_moves |= move

        if analytic_lines:
            analytic_lines.analytic_distribution = vals["analytic_distribution"]
        if depreciation_lines:
            depreciation_lines.account_id = vals["account_depreciation_id"]
        if expense_lines:
            expense_lines.account_id = vals["account_depreciation_expense_id"]
        if rejournaled_moves:
            rejournaled_moves.journal_id = vals["depreciation_journal_id"]
        _debug.lifecycle(
            "write.propagated_to_moves",
            boards=self,
            fields=sorted(propagated),
            analytic_lines=len(analytic_lines),
            depreciation_lines=len(depreciation_lines),
            expense_lines=len(expense_lines),
            rejournaled=len(rejournaled_moves),
        )
        return result

    def _check_disposal_accounts(self):
        company = self.company_id.sudo()
        if not (company.gain_account_id and company.loss_account_id):
            _debug.logic("disposal.refused", reason="no_gain_loss_account", board=self)
            raise UserError(
                _(
                    "%(asset)s depreciates, so disposing of it books an entry. Set the gain and loss accounts of %(company)s first.",
                    asset=self.display_name,
                    company=self.company_id.display_name,
                )
            )
