import calendar
from itertools import chain

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Command
from odoo.libs.debug_log import DebugLog
from odoo.tools import float_compare

_debug = DebugLog(__name__)

DEFERRED_DATE_MIN = "1900-01-01"
DEFERRED_DATE_MAX = "9999-12-31"


class AccountMove(models.Model):
    _inherit = "account.move"

    deferred_move_ids = fields.Many2many(
        comodel_name="account.move",
        relation="account_move_deferred_rel",
        column1="original_move_id",
        column2="deferred_move_id",
        string="Deferred Entries",
        copy=False,
        help="The deferred entries created by this invoice",
    )
    deferred_original_move_ids = fields.Many2many(
        comodel_name="account.move",
        relation="account_move_deferred_rel",
        column1="deferred_move_id",
        column2="original_move_id",
        string="Original Invoices",
        copy=False,
        help="The original invoices that created the deferred entries",
    )
    deferred_entry_type = fields.Selection(
        selection=[
            ("expense", "Deferred Expense"),
            ("revenue", "Deferred Revenue"),
            ("misc", "Deferred Miscellaneous"),
        ],
        compute="_compute_deferred_entry_type",
        copy=False,
    )

    @_debug.perf.timed
    def _post_entries(self):
        _debug.lifecycle("_post_entries", records=self)
        posted = super()._post_entries()
        for move in self:
            if move._get_deferred_entries_method() == "on_validation" and any(
                move.line_ids.mapped("deferred_start_date")
            ):
                _debug.pipeline("deferral_validation_generating_entries", move=move)
                move._create_deferred_entries()
        return posted

    @_debug.perf.timed
    def action_draft(self):
        _debug.lifecycle("action_draft", records=self)
        if any(
            len(deferral_move.deferred_original_move_ids) > 1
            for deferral_move in self.deferred_move_ids
        ):
            raise UserError(
                _(
                    "You cannot reset to draft an invoice that is grouped in deferral entry. You can create a credit note instead."
                )
            )
        reversed_moves = self.deferred_move_ids._unlink_or_reverse()
        _debug.logic(
            "action_draft_deferral_moves_reversed",
            deferred_move_ids=self.deferred_move_ids,
            reversed_moves=reversed_moves,
        )
        if reversed_moves:
            for move in reversed_moves:
                move.with_context(skip_readonly_check=True).write(
                    {
                        "date": move._get_accounting_date(
                            move.date, move._affect_tax_report()
                        ),
                    }
                )
            self.deferred_move_ids |= reversed_moves
        return super().action_draft()

    @_debug.perf.timed
    def unlink(self):
        _debug.lifecycle("unlink", unlink=self)
        deferral_moves = self.filtered(
            lambda move: (
                move._is_protected_by_audit_trail() and move.deferred_original_move_ids
            )
        )
        deferral_moves.deferred_original_move_ids.deferred_move_ids = False
        deferral_moves._reverse_moves()
        return super(AccountMove, self - deferral_moves).unlink()

    def _get_deferred_entries_method(self):
        self.check_singleton()
        if self.is_entry():
            move_types = set(
                self.line_ids.filtered("deferred_start_date").account_id.mapped(
                    "internal_group"
                )
            )
            if (
                "expense" in move_types
                and "income" in move_types
                and self.company_id.generate_deferred_expense_entries_method
                != self.company_id.generate_deferred_revenue_entries_method
            ):
                _debug.logic(
                    "deferred_methods_conflict",
                    move=self,
                    groups=move_types,
                    reason="expense_and_revenue_methods_differ",
                )
                raise UserError(
                    self.env._(
                        "Having different deferred entries generation methods for expenses and revenues is not supported on "
                        "journal entries involving both expense and revenue accounts. You can split this entry into two entries instead."
                    )
                )
            _debug.logic(
                "deferred_method_side",
                move=self,
                source="entry",
                expense="expense" in move_types,
            )
            if "expense" in move_types:
                return self.company_id.generate_deferred_expense_entries_method
            else:
                return self.company_id.generate_deferred_revenue_entries_method
        if self.is_purchase_document():
            _debug.logic(
                "deferred_method_side",
                move=self,
                source="purchase_document",
                expense=True,
            )
            return self.company_id.generate_deferred_expense_entries_method
        return self.company_id.generate_deferred_revenue_entries_method

    @api.depends("deferred_original_move_ids")
    def _compute_deferred_entry_type(self):
        for move in self:
            if move.deferred_original_move_ids:
                move_types = set(move.deferred_original_move_ids.mapped("move_type"))
                if len(move_types) > 1 or move.deferred_original_move_ids[0].is_entry():
                    move.deferred_entry_type = "misc"
                elif move.deferred_original_move_ids[0].is_purchase_document():
                    move.deferred_entry_type = "expense"
                else:
                    move.deferred_entry_type = "revenue"
            else:
                move.deferred_entry_type = False

    @api.model
    def _get_deferred_diff_dates(self, start, end):
        if start > end:
            start, end = end, start
        nb_months = end.month - start.month + 12 * (end.year - start.year)
        start_day, end_day = start.day, end.day
        if start_day == calendar.monthrange(start.year, start.month)[1]:
            start_day = 30
        if end_day == calendar.monthrange(end.year, end.month)[1]:
            end_day = 30
        nb_days = end_day - start_day
        return (nb_months * 30 + nb_days) / 30

    @api.model
    def _get_deferred_period_amount(
        self, method, period_start, period_end, line_start, line_end, balance
    ):
        if period_end <= line_start or period_end <= period_start:
            return 0
        if method == "day":
            amount_per_day = balance / (line_end - line_start).days
            return (period_end - period_start).days * amount_per_day
        elif method in ("month", "full_months"):
            if method == "full_months":
                reset_day_1 = relativedelta(day=1)
                line_start, line_end = line_start + reset_day_1, line_end + reset_day_1
                period_start, period_end = (
                    period_start + reset_day_1,
                    period_end + reset_day_1,
                )
            line_diff = self._get_deferred_diff_dates(line_end, line_start)
            period_diff = self._get_deferred_diff_dates(period_end, period_start)
            return period_diff / line_diff * balance if line_diff else balance
        return None

    @api.model
    @_debug.perf.timed
    def _get_deferred_amounts_by_line(
        self, lines, periods, deferred_type, company=None
    ):
        company = company or self.company_id[:1] or self.env.company
        method = (
            company.deferred_expense_amount_computation_method
            if deferred_type == "expense"
            else company.deferred_revenue_amount_computation_method
        )
        _debug.pipeline(
            "deferred_amounts_computing",
            company=company,
            deferred_type=deferred_type,
            method=method,
            lines=len(lines),
            periods=len(periods),
        )
        values = []
        for line in lines:
            line_start = fields.Date.to_date(line["deferred_start_date"])
            line_end = fields.Date.to_date(line["deferred_end_date"])
            line_end = max(line_end, line_start)

            columns = {}
            for period in periods:
                if period[2] == "not_started" and line_start <= period[0]:
                    columns[period] = 0.0
                    continue
                period_start = max(period[0], line_start)
                period_end = min(period[1], line_end) + relativedelta(days=1)

                columns[period] = self._get_deferred_period_amount(
                    method,
                    period_start,
                    period_end,
                    line_start,
                    line_end + relativedelta(days=1),
                    line["balance"],
                )

            values.append(
                {
                    **self.env[
                        "account.move.line"
                    ]._prepare_deferred_amounts_by_line_values(line),
                    **columns,
                }
            )
        return values

    def _get_deferred_settings(self, deferred_type):
        self.check_singleton()
        company = self.company_id
        is_expense = deferred_type == "expense"
        deferred_account = (
            company.deferred_expense_account_id
            if is_expense
            else company.deferred_revenue_account_id
        )
        deferred_journal = (
            company.deferred_expense_journal_id
            if is_expense
            else company.deferred_revenue_journal_id
        )
        deferred_method = (
            company.deferred_expense_amount_computation_method
            if is_expense
            else company.deferred_revenue_amount_computation_method
        )
        if not deferred_journal:
            _debug.logic(
                "deferred_settings_missing",
                move=self,
                deferred_type=deferred_type,
                missing="journal",
            )
            raise UserError(
                _("Please set the deferred journal in the accounting settings.")
            )
        if not deferred_account:
            _debug.logic(
                "deferred_settings_missing",
                move=self,
                deferred_type=deferred_type,
                missing="account",
            )
            raise UserError(
                _("Please set the deferred accounts in the accounting settings.")
            )
        return deferred_account, deferred_journal, deferred_method

    def _get_deferrable_lines(self, deferred_type):
        self.check_singleton()
        internal_group = "expense" if deferred_type == "expense" else "income"
        return self.line_ids.filtered(
            lambda line: (
                line.account_id.internal_group == internal_group
                and line.deferred_start_date
                and line.deferred_end_date
            )
        )

    def _is_deferral_worth_generating(self, line, deferred_method):
        start_date = line.deferred_start_date
        end_date = line.deferred_end_date
        if deferred_method == "full_months" and (
            self._get_deferred_diff_dates(
                start_date.replace(day=1), end_date + relativedelta(days=1)
            )
            < 2
        ):
            end_date += relativedelta(months=-1)
        return not (
            start_date.replace(day=1)
            == end_date.replace(day=1)
            == line.date.replace(day=1)
        )

    @_debug.perf.timed
    def _prepare_deferral_move_vals(self, line, deferred_journal, ref):
        self.check_singleton()
        return {
            "move_type": "entry",
            "deferred_original_move_ids": [Command.set(line.move_id.ids)],
            "journal_id": deferred_journal.id,
            "company_id": self.company_id.id,
            "partner_id": line.partner_id.id,
            "auto_post": "at_date",
            "ref": ref,
            "name": False,
            "date": line.move_id.date,
        }

    @_debug.perf.timed
    def _create_deferral_moves(self, moves_vals, lines_vals):
        moves = self.create(moves_vals)
        for move, move_lines_vals in zip(moves, lines_vals, strict=True):
            for line_vals in move_lines_vals:
                line_vals["move_id"] = move.id
        self.env["account.move.line"].create(list(chain(*lines_vals)))
        return moves

    @_debug.perf.timed
    def _prepare_period_deferral_vals(
        self, line, periods, move_vals, deferred_type, deferred_account
    ):
        self.check_singleton()
        moves_vals, lines_vals = [], []
        remaining_balance = line.balance
        for period_index, period in enumerate(periods):
            force_balance = (
                remaining_balance if period_index == len(periods) - 1 else None
            )
            deferred_amounts = self._get_deferred_amounts_by_line(
                line, [period], deferred_type, company=self.company_id
            )[0]
            balance = (
                deferred_amounts[period] if force_balance is None else force_balance
            )
            remaining_balance -= line.currency_id.round(balance)
            moves_vals.append({**move_vals, "date": period[1]})
            lines_vals.append(
                [
                    {
                        **self.env["account.move.line"]._prepare_deferred_lines_values(
                            account.id,
                            coeff * balance,
                            move_vals["ref"],
                            line.analytic_distribution,
                            line,
                        ),
                        "partner_id": line.partner_id.id,
                        "product_id": line.product_id.id,
                    }
                    for (account, coeff) in [
                        (deferred_amounts["account_id"], 1),
                        (deferred_account, -1),
                    ]
                ]
            )
        _debug.pipeline(
            "period_deferral_vals_prepared",
            move=self,
            line=line,
            deferred_type=deferred_type,
            periods=len(periods),
            remaining_balance=remaining_balance,
        )
        return moves_vals, lines_vals

    @_debug.perf.timed
    def _create_deferred_entries(self):
        self.check_singleton()
        if self.state != "posted":
            return

        for deferred_type in ("expense", "revenue"):
            lines = self._get_deferrable_lines(deferred_type)
            if not lines:
                continue

            deferred_account, deferred_journal, deferred_method = (
                self._get_deferred_settings(deferred_type)
            )

            moves_vals_to_create = []
            lines_vals_to_create = []
            lines_periods = []
            for line in lines:
                periods = line._get_deferred_periods()
                if not periods or not self._is_deferral_worth_generating(
                    line, deferred_method
                ):
                    _debug.logic(
                        "deferral_not_worth_generating",
                        move=self,
                        line=line,
                        count=len(periods or ()),
                    )
                    continue

                ref = _("Deferral of %s", line.move_id.name or "")
                moves_vals_to_create.append(
                    self._prepare_deferral_move_vals(line, deferred_journal, ref)
                )
                lines_vals_to_create.append(
                    [
                        {
                            **self.env["account.move.line"]._prepare_deferred_lines_values(
                                account.id,
                                coeff * line.balance,
                                ref,
                                line.analytic_distribution,
                                line,
                            ),
                            "partner_id": line.partner_id.id,
                        }
                        for (account, coeff) in [
                            (line.account_id, -1),
                            (deferred_account, 1),
                        ]
                    ]
                )
                lines_periods.append((line, periods))

            moves_fully_deferred = self._create_deferral_moves(
                moves_vals_to_create, lines_vals_to_create
            )

            deferral_moves_vals = []
            deferral_moves_line_vals = []
            for (line, periods), move_vals in zip(
                lines_periods, moves_vals_to_create, strict=True
            ):
                period_moves, period_lines = self._prepare_period_deferral_vals(
                    line, periods, move_vals, deferred_type, deferred_account
                )
                deferral_moves_vals += period_moves
                deferral_moves_line_vals += period_lines

            deferral_moves = self._create_deferral_moves(
                deferral_moves_vals, deferral_moves_line_vals
            )

            to_unlink = deferral_moves.filtered(
                lambda move: move.currency_id.is_zero(move.amount_total)
            )
            _debug.pipeline(
                "deferred_zero",
                move=self,
                deferred_type=deferred_type,
                lines_periods_count=len(lines_periods),
                full=moves_fully_deferred,
                periodic=deferral_moves,
                dropped=to_unlink,
                method=deferred_method,
            )
            to_unlink.unlink()

            (moves_fully_deferred + deferral_moves - to_unlink)._post(soft=True)

    @_debug.perf.timed
    def open_deferred_entries(self):
        _debug.lifecycle("open_deferred_entries", records=self)
        self.check_singleton()
        return {
            "type": "ir.actions.act_window",
            "name": _("Deferred Entries"),
            "res_model": "account.move.line",
            "domain": [("id", "in", self.deferred_move_ids.line_ids.ids)],
            "views": [
                (
                    self.env.ref("account.view_deferred_entries_tree").id,
                    "list",
                )
            ],
            "context": {
                "search_default_group_by_move": True,
                "expand": True,
            },
        }

    @_debug.perf.timed
    def open_deferred_original_entry(self):
        _debug.lifecycle("open_deferred_original_entry", records=self)
        self.check_singleton()
        action = {
            "type": "ir.actions.act_window",
            "name": _("Original Deferred Entries"),
            "res_model": "account.move.line",
            "domain": [("id", "in", self.deferred_original_move_ids.line_ids.ids)],
            "views": [(False, "list"), (False, "form")],
            "context": {
                "search_default_group_by_move": True,
                "expand": True,
            },
        }
        if len(self.deferred_original_move_ids) == 1:
            action.update(
                {
                    "res_model": "account.move",
                    "res_id": self.deferred_original_move_ids[0].id,
                    "views": [(False, "form")],
                }
            )
        return action


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    deferred_start_date = fields.Date(
        string="Start Date",
        compute="_compute_deferred_start_date",
        store=True,
        index="btree_not_null",
        copy=False,
        readonly=False,
        help="Date at which the deferred expense/revenue starts",
    )
    deferred_end_date = fields.Date(
        string="End Date",
        index="btree_not_null",
        copy=False,
        help="Date at which the deferred expense/revenue ends",
    )
    has_deferred_moves = fields.Boolean(
        compute="_compute_has_deferred_moves",
        exportable=False,
    )
    has_abnormal_deferred_dates = fields.Boolean(
        compute="_compute_has_abnormal_deferred_dates",
        exportable=False,
    )

    @_debug.perf.timed
    def copy_data(self, default=None):
        _debug.lifecycle("copy_data", records=self)
        data_list = super().copy_data(default=default)
        for line, values in zip(self, data_list, strict=True):
            if "move_reverse_cancel" in self.env.context:
                values["deferred_start_date"] = line.deferred_start_date
                values["deferred_end_date"] = line.deferred_end_date
        return data_list

    @_debug.perf.timed
    def write(self, vals):
        _debug.lifecycle("write", records=self, fields=sorted(vals))
        if "account_id" in vals:
            for line in self:
                if (
                    line.has_deferred_moves
                    and line.deferred_start_date
                    and line.deferred_end_date
                    and vals["account_id"] != line.account_id.id
                ):
                    _debug.logic(
                        "deferred_account_change_blocked",
                        line=line,
                        account_id=vals.get("account_id"),
                    )
                    raise UserError(
                        _(
                            "You cannot change the account for a deferred line in %(move_name)s if it has already been deferred.",
                            move_name=line.move_id.display_name,
                        )
                    )
        return super().write(vals)

    @api.depends("move_id.deferred_move_ids")
    def _compute_has_deferred_moves(self):
        for line in self:
            line.has_deferred_moves = bool(line.move_id.deferred_move_ids)

    @api.depends("deferred_start_date", "deferred_end_date")
    @_debug.perf.timed
    def _compute_has_abnormal_deferred_dates(self):
        for line in self:
            line.has_abnormal_deferred_dates = (
                line.deferred_start_date
                and line.deferred_end_date
                and line.deferred_start_date != line.deferred_end_date
                and float_compare(
                    self.env["account.move"]._get_deferred_diff_dates(
                        line.deferred_start_date,
                        line.deferred_end_date + relativedelta(days=1),
                    )
                    % 1,
                    1 / 30,
                    precision_digits=2,
                )
                == 0
            )

    def _has_deferred_compatible_account(self):
        self.check_singleton()
        return (
            (
                self.move_id.is_purchase_document(include_receipts=True)
                and self.account_id.internal_group == "expense"
            )
            or (
                self.move_id.is_sale_document(include_receipts=True)
                and self.account_id.internal_group == "income"
            )
            or (
                self.move_id.is_entry()
                and self.account_id.internal_group in ("expense", "income")
            )
        )

    @api.onchange("deferred_start_date", "account_id")
    def _onchange_deferred_start_date(self):
        if not self._has_deferred_compatible_account():
            self.deferred_start_date = False
        if self.deferred_start_date and not self.deferred_end_date:
            self.deferred_end_date = self.deferred_start_date

    @api.onchange("deferred_end_date", "account_id")
    def _onchange_deferred_end_date(self):
        if not self._has_deferred_compatible_account():
            self.deferred_end_date = False
        if self.deferred_end_date and not self.deferred_start_date:
            self.deferred_start_date = self.deferred_end_date

    @api.depends("deferred_end_date", "move_id.invoice_date", "move_id.state")
    def _compute_deferred_start_date(self):
        for line in self:
            if (
                not line.deferred_start_date
                and line.move_id.invoice_date
                and line.deferred_end_date
            ):
                line.deferred_start_date = line.move_id.invoice_date

    @api.constrains("deferred_start_date", "deferred_end_date", "account_id")
    @_debug.perf.timed
    def _check_deferred_dates(self):
        for line in self:
            if line.deferred_start_date and not line.deferred_end_date:
                _debug.logic(
                    "deferred_dates_invalid", line=line, reason="start_without_end"
                )
                raise UserError(
                    _(
                        "You cannot create a deferred entry with a start date but no end date."
                    )
                )
            if (
                line.deferred_start_date
                and line.deferred_end_date
                and line.deferred_start_date > line.deferred_end_date
            ):
                _debug.logic(
                    "deferred_dates_invalid", line=line, reason="start_after_end"
                )
                raise UserError(
                    _(
                        "You cannot create a deferred entry with a start date later than the end date."
                    )
                )

    @api.model
    def _get_deferred_ends_of_month(self, start_date, end_date):
        dates = []
        while start_date <= end_date:
            start_date += relativedelta(day=31)
            dates.append(start_date)
            start_date += relativedelta(days=1)
        return dates

    def _get_deferred_periods(self):
        self.check_singleton()
        periods = [
            (
                max(self.deferred_start_date, date.replace(day=1)),
                min(date, self.deferred_end_date),
                "current",
            )
            for date in self._get_deferred_ends_of_month(
                self.deferred_start_date, self.deferred_end_date
            )
        ]
        if not periods or (
            len(periods) == 1
            and periods[0][0].replace(day=1) == self.date.replace(day=1)
        ):
            return []
        else:
            return periods

    @api.model
    def _prepare_deferred_amounts_by_line_values(self, line):
        return {
            "account_id": line["account_id"],
            "product_id": line["product_id"]
            if isinstance(line, dict)
            else line["product_id"].id,
            "product_category_id": line["product_category_id"]
            if isinstance(line, dict)
            else line["product_category_id"].id,
            "balance": line["balance"],
            "move_id": line["move_id"],
        }

    @api.model
    def _prepare_deferred_lines_values(
        self, account_id, balance, ref, analytic_distribution, line=None
    ):
        return {
            "account_id": account_id,
            "product_id": line["product_id"]
            if isinstance(line, dict)
            else line["product_id"].id,
            "product_category_id": line["product_category_id"]
            if isinstance(line, dict)
            else line["product_category_id"].id,
            "balance": balance,
            "name": ref,
            "analytic_distribution": analytic_distribution,
        }

    def _get_computed_taxes(self):
        if self.move_id.deferred_original_move_ids:
            return self.tax_ids
        return super()._get_computed_taxes()
