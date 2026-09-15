import json
from collections import defaultdict

from markupsafe import Markup, escape

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.libs.debug_log import DebugLog
from odoo.libs.numbers import float_repr
from odoo.tools import frozendict, groupby
from odoo.tools.misc import format_date, formatLang

_debug = DebugLog(__name__)


class AccountAutomaticEntryWizard(models.TransientModel):
    _name = "account.automatic.entry.wizard"
    _description = "Create Automatic Entries"
    _check_company_auto = True

    action = fields.Selection(
        selection=[
            ("change_period", "Change Period"),
            ("change_account", "Change Account"),
        ],
        required=True,
    )
    move_data = fields.Text(compute="_compute_move_data")
    preview_move_data = fields.Text(compute="_compute_preview_move_data")
    move_line_ids = fields.Many2many(comodel_name="account.move.line")
    date = fields.Date(
        default=fields.Date.context_today,
        required=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        readonly=True,
        required=True,
    )
    company_currency_id = fields.Many2one(
        comodel_name="res.currency",
        related="company_id.currency_id",
    )
    percentage = fields.Float(
        compute="_compute_percentage",
        store=True,
        readonly=False,
        help="Percentage of each line to execute the action on.",
    )
    total_amount = fields.Monetary(
        currency_field="company_currency_id",
        compute="_compute_total_amount",
        store=True,
        readonly=False,
        help="Total amount impacted by the automatic entry.",
    )
    journal_id = fields.Many2one(
        comodel_name="account.journal",
        compute="_compute_journal_id",
        inverse="_inverse_journal_id",
        readonly=False,
        required=True,
        domain="[('type', '=', 'general')]",
        check_company=True,
        help="Journal where to create the entry.",
    )

    account_type = fields.Selection(
        selection=[("income", "Revenue"), ("expense", "Expense")],
        compute="_compute_account_type",
        store=True,
    )
    expense_accrual_account = fields.Many2one(
        comodel_name="account.account",
        compute="_compute_expense_accrual_account",
        inverse="_inverse_expense_accrual_account",
        readonly=False,
        domain="[('account_type', 'not in', ('asset_receivable', 'liability_payable', 'off_balance'))]",
        check_company=True,
    )
    revenue_accrual_account = fields.Many2one(
        comodel_name="account.account",
        compute="_compute_revenue_accrual_account",
        inverse="_inverse_revenue_accrual_account",
        readonly=False,
        domain="[('account_type', 'not in', ('asset_receivable', 'liability_payable', 'off_balance'))]",
        check_company=True,
    )
    lock_date_message = fields.Char(compute="_compute_lock_date_message")

    destination_account_id = fields.Many2one(
        comodel_name="account.account",
        string="To",
        check_company=True,
        help="Account to transfer to.",
    )
    display_currency_helper = fields.Boolean(
        string="Currency Conversion Helper",
        compute="_compute_display_currency_helper",
    )

    @api.depends("company_id")
    def _compute_expense_accrual_account(self):
        for record in self:
            record.expense_accrual_account = (
                record.company_id.expense_accrual_account_id
            )

    def _inverse_expense_accrual_account(self):
        for record in self:
            if record.env.user.has_group("account.group_account_manager"):
                record.company_id.sudo().expense_accrual_account_id = (
                    record.expense_accrual_account
                )

    @api.depends("company_id")
    def _compute_revenue_accrual_account(self):
        for record in self:
            record.revenue_accrual_account = (
                record.company_id.revenue_accrual_account_id
            )

    def _inverse_revenue_accrual_account(self):
        for record in self:
            if record.env.user.has_group("account.group_account_manager"):
                record.company_id.sudo().revenue_accrual_account_id = (
                    record.revenue_accrual_account
                )

    @api.depends("company_id")
    def _compute_journal_id(self):
        for record in self:
            record.journal_id = record.company_id.automatic_entry_default_journal_id

    def _inverse_journal_id(self):
        for record in self:
            if record.env.user.has_group("account.group_account_manager"):
                record.company_id.sudo().automatic_entry_default_journal_id = (
                    record.journal_id
                )

    @api.constrains("percentage", "action")
    @_debug.perf.timed
    def _check_percentage(self):
        for record in self:
            if (
                not (0.0 < record.percentage <= 100.0)
                and record.action == "change_period"
            ):
                raise ValidationError(_("Percentage must be between 0 and 100"))

    @api.depends("percentage", "move_line_ids")
    def _compute_total_amount(self):
        for record in self:
            record.total_amount = (
                (record.percentage or 100)
                * sum(record.move_line_ids.mapped("balance"))
                / 100
            )

    @api.depends("total_amount", "move_line_ids")
    def _compute_percentage(self):
        for record in self:
            balance_total = sum(record.move_line_ids.mapped("balance"))
            if balance_total:
                record.percentage = min(
                    (record.total_amount / balance_total) * 100, 100
                )
            else:
                record.percentage = 100

    @api.depends("move_line_ids")
    def _compute_account_type(self):
        for record in self:
            record.account_type = (
                "income"
                if sum(record.move_line_ids.mapped("balance")) < 0
                else "expense"
            )

    @api.depends("action", "move_line_ids")
    def _compute_lock_date_message(self):
        for record in self:
            record.lock_date_message = False
            if record.action == "change_period":
                for aml in record.move_line_ids:
                    lock_date_message = aml.move_id._get_lock_date_message(
                        aml.date, False
                    )
                    if lock_date_message:
                        record.lock_date_message = lock_date_message
                        break

    @api.depends("destination_account_id")
    def _compute_display_currency_helper(self):
        for record in self:
            record.display_currency_helper = bool(
                record.destination_account_id.currency_id
            )

    @api.constrains("date", "move_line_ids")
    @_debug.perf.timed
    def _check_date(self):
        for wizard in self:
            for move in wizard.move_line_ids.move_id:
                violated_lock_dates = move._get_violated_lock_dates(wizard.date, False)
                if violated_lock_dates:
                    raise ValidationError(
                        _(
                            "The date selected is protected by: %(lock_date_info)s.",
                            lock_date_info=self.env["res.company"]._format_lock_dates(
                                violated_lock_dates
                            ),
                        )
                    )

    @api.model
    @_debug.perf.timed
    def default_get(self, fields_list):
        _debug.lifecycle("default_get", records=self)
        res = super().default_get(fields_list)
        if not set(fields_list) & {"move_line_ids", "company_id"}:
            return res

        if self.env.context.get(
            "active_model"
        ) != "account.move.line" or not self.env.context.get("active_ids"):
            raise UserError(_("This can only be used on journal items"))
        move_line_ids = self.env["account.move.line"].browse(
            self.env.context["active_ids"]
        )
        res["move_line_ids"] = [(6, 0, move_line_ids.ids)]

        if any(move.state != "posted" for move in move_line_ids.mapped("move_id")):
            raise UserError(
                _(
                    "Oops! You can only change the period or account for posted entries! Other ones aren't up for an adventure like that!"
                )
            )
        if any(move_line.reconciled for move_line in move_line_ids):
            raise UserError(
                _(
                    "Oops! You can only change the period or account for items that are not yet reconciled! Other ones aren't up for an adventure like that!"
                )
            )
        if any(
            line.company_id.root_id != move_line_ids[0].company_id.root_id
            for line in move_line_ids
        ):
            raise UserError(
                _(
                    "You cannot use this wizard on journal entries belonging to different companies."
                )
            )
        res["company_id"] = move_line_ids[0].company_id.root_id.id

        allowed_actions = set(dict(self._fields["action"].selection))
        if self.env.context.get("default_action"):
            allowed_actions = {self.env.context["default_action"]}
        if any(
            line.account_id.account_type != move_line_ids[0].account_id.account_type
            for line in move_line_ids
        ):
            allowed_actions.discard("change_period")
        if _debug.logic.enabled:
            _debug.logic(
                "allowed_actions_resolved",
                lines=len(move_line_ids),
                default_action=self.env.context.get("default_action"),
                allowed=sorted(allowed_actions),
            )
        if not allowed_actions:
            raise UserError(_("No possible action found with the selected lines."))
        res["action"] = allowed_actions.pop()
        return res

    def _get_cut_off_label_format(self):
        self.check_singleton()
        return (
            _("Cut-off {label}")
            if self.percentage == 100
            else _("Cut-off {label} {percent}%")
        )

    @_debug.perf.timed
    def _get_change_account_groupings(self):
        counterpart_balances = defaultdict(lambda: defaultdict(lambda: 0))
        counterpart_distribution_amount = defaultdict(lambda: defaultdict(dict))
        grouped_source_lines = defaultdict(lambda: self.env["account.move.line"])

        for line in self.move_line_ids.filtered(
            lambda x: x.account_id != self.destination_account_id
        ):
            counterpart_currency = line.currency_id
            counterpart_amount_currency = line.amount_currency

            if (
                self.destination_account_id.currency_id
                and self.destination_account_id.currency_id
                != self.company_id.currency_id
            ):
                counterpart_currency = self.destination_account_id.currency_id
                counterpart_amount_currency = self.company_id.currency_id._convert(
                    line.balance,
                    self.destination_account_id.currency_id,
                    self.company_id,
                    line.date,
                )

            grouping_key = (line.partner_id, counterpart_currency)

            counterpart_balances[grouping_key]["amount_currency"] += (
                counterpart_amount_currency
            )
            counterpart_balances[grouping_key]["balance"] += line.balance
            if line.analytic_distribution:
                for account_id, distribution in line.analytic_distribution.items():
                    distribution_values = counterpart_distribution_amount[grouping_key]
                    distribution_values[account_id] = (
                        line.balance * distribution
                        + distribution_values.get(account_id, 0) * 100
                    ) / 100
            counterpart_balances[grouping_key]["analytic_distribution"] = (
                counterpart_distribution_amount[grouping_key] or {}
            )
            grouped_source_lines[
                (
                    line.partner_id,
                    line.currency_id,
                    line.account_id,
                    line.analytic_distribution
                    and frozendict(line.analytic_distribution),
                )
            ] += line
        if _debug.pipeline.enabled:
            _debug.pipeline(
                "change_account_groups_built",
                autoentry=self,
                destination_account=self.destination_account_id,
                destination_currency_forced=bool(
                    self.destination_account_id.currency_id
                    and self.destination_account_id.currency_id
                    != self.company_id.currency_id
                ),
                counterpart_groups=len(counterpart_balances),
                source_groups=len(grouped_source_lines),
            )
        return counterpart_balances, grouped_source_lines

    @_debug.perf.timed
    def _prepare_change_account_counterpart_line_vals(self, counterpart_balances):
        line_vals = []
        for (
            counterpart_partner,
            counterpart_currency,
        ), counterpart_vals in counterpart_balances.items():
            source_accounts = self.move_line_ids.mapped("account_id")
            counterpart_label = (
                len(source_accounts) == 1
                and _("Transfer from %s", source_accounts.display_name)
            ) or _("Transfer counterpart")

            analytic_distribution = {
                account_id: (
                    100
                    if counterpart_currency.is_zero(counterpart_vals["balance"])
                    else 100 * distribution_amount / counterpart_vals["balance"]
                )
                for account_id, distribution_amount in counterpart_vals[
                    "analytic_distribution"
                ].items()
            }

            if not counterpart_currency.is_zero(
                counterpart_vals["amount_currency"]
            ) or not self.company_id.currency_id.is_zero(counterpart_vals["balance"]):
                line_vals.append(
                    {
                        "name": counterpart_label,
                        "debit": (
                            counterpart_vals["balance"] > 0
                            and self.company_id.currency_id.round(
                                counterpart_vals["balance"]
                            )
                        )
                        or 0,
                        "credit": (
                            counterpart_vals["balance"] < 0
                            and self.company_id.currency_id.round(
                                -counterpart_vals["balance"]
                            )
                        )
                        or 0,
                        "account_id": self.destination_account_id.id,
                        "partner_id": counterpart_partner.id or None,
                        "amount_currency": counterpart_currency.round(
                            ((counterpart_vals["balance"] < 0 and -1) or 1)
                            * abs(counterpart_vals["amount_currency"])
                        )
                        or 0,
                        "currency_id": counterpart_currency.id,
                        "analytic_distribution": analytic_distribution,
                    }
                )
        _debug.pipeline(
            "counterpart_lines_built",
            autoentry=self,
            groups=len(counterpart_balances),
            lines=len(line_vals),
        )
        return line_vals

    @_debug.perf.timed
    def _prepare_change_account_source_line_vals(self, grouped_source_lines):
        line_vals = []
        for (
            partner,
            currency,
            account,
            analytic_distribution,
        ), lines in grouped_source_lines.items():
            account_balance = sum(line.balance for line in lines)
            if not self.company_id.currency_id.is_zero(account_balance):
                account_amount_currency = currency.round(
                    sum(line.amount_currency for line in lines)
                )
                line_vals.append(
                    {
                        "name": _(
                            "Transfer to %s",
                            self.destination_account_id.display_name or _("[Not set]"),
                        ),
                        "debit": (
                            account_balance < 0
                            and self.company_id.currency_id.round(-account_balance)
                        )
                        or 0,
                        "credit": (
                            account_balance > 0
                            and self.company_id.currency_id.round(account_balance)
                        )
                        or 0,
                        "account_id": account.id,
                        "partner_id": partner.id or None,
                        "currency_id": currency.id,
                        "amount_currency": ((account_balance > 0 and -1) or 1)
                        * abs(account_amount_currency),
                        "analytic_distribution": analytic_distribution,
                    }
                )
        _debug.pipeline(
            "source_lines_built",
            autoentry=self,
            groups=len(grouped_source_lines),
            lines=len(line_vals),
        )
        return line_vals

    @_debug.perf.timed
    def _get_move_dict_vals_change_account(self):
        counterpart_balances, grouped_source_lines = (
            self._get_change_account_groupings()
        )
        line_vals = self._prepare_change_account_counterpart_line_vals(
            counterpart_balances
        )
        line_vals += self._prepare_change_account_source_line_vals(grouped_source_lines)

        accounts = self.env["account.account"].browse(
            [line["account_id"] for line in line_vals]
        )
        companies = (
            accounts.company_ids.filtered(lambda c: self.env.company in c.parent_ids)
            | self.env.company
        )
        lowest_child_company = max(
            companies, key=lambda company: len(company.parent_ids)
        )

        _debug.pipeline(
            "change_account_move_vals_built",
            autoentry=self,
            lines=len(line_vals),
            company=lowest_child_company,
            candidate_companies=companies,
        )
        return [
            {
                "currency_id": self.journal_id.currency_id.id
                or self.journal_id.company_id.currency_id.id,
                "move_type": "entry",
                "name": "/",
                "journal_id": self.journal_id.id,
                "company_id": lowest_child_company.id,
                "date": fields.Date.to_string(self.date),
                "ref": self.destination_account_id.display_name
                and _(
                    "Transfer entry to %s",
                    self.destination_account_id.display_name or "",
                ),
                "line_ids": [(0, 0, line) for line in line_vals],
            }
        ]

    @_debug.perf.timed
    def _get_move_line_dict_vals_change_period(self, aml, date):
        accrual_account = (
            self.revenue_accrual_account
            if self.account_type == "income"
            else self.expense_accrual_account
        )
        reported_debit = aml.company_id.currency_id.round(
            (self.percentage / 100) * aml.debit
        )
        reported_credit = aml.company_id.currency_id.round(
            (self.percentage / 100) * aml.credit
        )
        reported_amount_currency = aml.currency_id.round(
            (self.percentage / 100) * aml.amount_currency
        )
        name = self._format_strings(self._get_cut_off_label_format(), aml.move_id)

        if date == "new_date":
            return [
                (
                    0,
                    0,
                    {
                        "name": name,
                        "debit": reported_debit,
                        "credit": reported_credit,
                        "amount_currency": reported_amount_currency,
                        "currency_id": aml.currency_id.id,
                        "account_id": aml.account_id.id,
                        "partner_id": aml.partner_id.id,
                        "analytic_distribution": aml.analytic_distribution,
                    },
                ),
                (
                    0,
                    0,
                    {
                        "name": name,
                        "debit": reported_credit,
                        "credit": reported_debit,
                        "amount_currency": -reported_amount_currency,
                        "currency_id": aml.currency_id.id,
                        "account_id": accrual_account.id,
                        "partner_id": aml.partner_id.id,
                        "analytic_distribution": aml.analytic_distribution,
                    },
                ),
            ]
        return [
            (
                0,
                0,
                {
                    "name": name,
                    "debit": reported_credit,
                    "credit": reported_debit,
                    "amount_currency": -reported_amount_currency,
                    "currency_id": aml.currency_id.id,
                    "account_id": aml.account_id.id,
                    "partner_id": aml.partner_id.id,
                    "analytic_distribution": aml.analytic_distribution,
                },
            ),
            (
                0,
                0,
                {
                    "name": name,
                    "debit": reported_debit,
                    "credit": reported_credit,
                    "amount_currency": reported_amount_currency,
                    "currency_id": aml.currency_id.id,
                    "account_id": accrual_account.id,
                    "partner_id": aml.partner_id.id,
                    "analytic_distribution": aml.analytic_distribution,
                },
            ),
        ]

    def _get_lock_safe_date(self, date):
        reference_move = self.env["account.move"].new(
            {
                "journal_id": self.journal_id.id,
                "move_type": "entry",
                "invoice_date": date,
            }
        )
        return reference_move._get_accounting_date(date, False)

    @_debug.perf.timed
    def _get_move_dict_vals_change_period(self):
        lock_safe_dates = {
            date: self._get_lock_safe_date(date)
            for date in set(self.move_line_ids.mapped("date"))
        }

        def get_lock_safe_date(aml):
            return lock_safe_dates[aml.date]

        ref_format = self._get_cut_off_label_format()
        move_data = {
            "new_date": {
                "currency_id": self.journal_id.currency_id.id
                or self.journal_id.company_id.currency_id.id,
                "move_type": "entry",
                "line_ids": [],
                "ref": self._format_strings(ref_format, self.move_line_ids[0].move_id),
                "date": fields.Date.to_string(self.date),
                "journal_id": self.journal_id.id,
                "adjusting_entry_origin_move_ids": self.move_line_ids.move_id.ids,
            }
        }
        for date, grouped_lines in groupby(self.move_line_ids, get_lock_safe_date):
            grouped_lines = list(grouped_lines)
            amount = sum(l.balance for l in grouped_lines)
            move_data[date] = {
                "currency_id": self.journal_id.currency_id.id
                or self.journal_id.company_id.currency_id.id,
                "move_type": "entry",
                "line_ids": [],
                "ref": self._format_strings(
                    ref_format, grouped_lines[0].move_id, amount
                ),
                "date": fields.Date.to_string(date),
                "journal_id": self.journal_id.id,
                "adjusting_entry_origin_move_ids": self.move_line_ids.move_id.ids,
            }

        for aml in self.move_line_ids:
            for date in ("new_date", get_lock_safe_date(aml)):
                move_data[date]["line_ids"] += (
                    self._get_move_line_dict_vals_change_period(aml, date)
                )

        if _debug.pipeline.enabled:
            _debug.pipeline(
                "change_period_move_vals_built",
                autoentry=self,
                moves=len(move_data),
                source_dates=len(lock_safe_dates),
                lock_shifted_dates=sum(
                    1 for date, safe in lock_safe_dates.items() if date != safe
                ),
                lines=len(self.move_line_ids),
            )
        return list(move_data.values())

    @api.depends(
        "move_line_ids",
        "journal_id",
        "revenue_accrual_account",
        "expense_accrual_account",
        "percentage",
        "date",
        "account_type",
        "action",
        "destination_account_id",
    )
    @_debug.perf.timed
    def _compute_move_data(self):
        for record in self:
            if record.action == "change_period":
                if any(
                    line.account_id.account_type
                    != record.move_line_ids[0].account_id.account_type
                    for line in record.move_line_ids
                ):
                    _debug.logic(
                        "move_data_rejected",
                        autoentry=record,
                        reason="mixed_account_types",
                    )
                    raise UserError(
                        _("All accounts on the lines must be of the same type.")
                    )
                record.move_data = json.dumps(
                    record._get_move_dict_vals_change_period()
                )
            elif record.action == "change_account":
                record.move_data = json.dumps(
                    record._get_move_dict_vals_change_account()
                )

    @api.depends("move_data")
    @_debug.perf.timed
    def _compute_preview_move_data(self):
        for record in self:
            preview_columns = [
                {"field": "account_id", "label": _("Account")},
                {"field": "name", "label": _("Label")},
                {
                    "field": "debit",
                    "label": _("Debit"),
                    "class": "text-end text-nowrap",
                },
                {
                    "field": "credit",
                    "label": _("Credit"),
                    "class": "text-end text-nowrap",
                },
            ]
            if record.action == "change_account":
                preview_columns[2:2] = [{"field": "partner_id", "label": _("Partner")}]

            move_vals = json.loads(record.move_data)
            preview_vals = []
            for move in move_vals[:4]:
                preview_vals += [
                    self.env["account.move"]._move_dict_to_preview_vals(
                        move, record.company_id.currency_id
                    )
                ]
            preview_discarded = max(0, len(move_vals) - len(preview_vals))
            _debug.pipeline(
                "preview_built",
                autoentry=record,
                action=record.action,
                moves=len(move_vals),
                discarded=preview_discarded,
            )

            record.preview_move_data = json.dumps(
                {
                    "groups_vals": preview_vals,
                    "options": {
                        "discarded_number": _("%d moves", preview_discarded)
                        if preview_discarded
                        else False,
                        "columns": preview_columns,
                    },
                }
            )

    def do_action(self):
        move_vals = json.loads(self.move_data)
        if _debug.pipeline.enabled:
            _debug.pipeline(
                "do_action_create",
                autoentry=self,
                action=self.action,
                move_line_ids_count=len(self.move_line_ids),
                move_vals_count=len(move_vals),
            )
        self = self.with_context(skip_computed_taxes=True)
        if self.action == "change_period":
            return self._do_action_change_period(move_vals)
        elif self.action == "change_account":
            return self._do_action_change_account(move_vals)
        return None

    @_debug.perf.timed
    def _reconcile_accrual_lines(
        self,
        accrual_account,
        accrual_move,
        destination_move,
        destination_move_offset,
        accrual_move_offsets,
    ):
        destination_move_lines = destination_move.mapped("line_ids").filtered(
            lambda line: line.account_id == accrual_account
        )[destination_move_offset : destination_move_offset + 2]
        offset = accrual_move_offsets[accrual_move]
        accrual_move_lines = accrual_move.mapped("line_ids").filtered(
            lambda line: line.account_id == accrual_account
        )[offset : offset + 2]
        accrual_move_offsets[accrual_move] += 2
        (accrual_move_lines + destination_move_lines).filtered(
            lambda line: not line.currency_id.is_zero(line.balance)
        ).reconcile()

    @_debug.perf.timed
    def _post_accrual_messages(self, move, accrual_move, destination_move, amount):
        _debug.lifecycle("_post_accrual_messages", records=self)
        body = Markup(
            "%(title)s<ul><li>%(link1)s %(second)s</li><li>%(link2)s %(third)s</li></ul>"
        ) % {
            "title": _("Adjusting Entries have been created for this invoice:"),
            "link1": self._format_move_link(accrual_move),
            "second": self._format_strings(
                _("cancelling {percent}%% of {amount}"), move, amount
            ),
            "link2": self._format_move_link(destination_move),
            "third": self._format_strings(
                _("postponing it to {new_date}"), move, amount
            ),
        }
        move.message_post(body=body)
        return (
            self._format_strings(
                escape(
                    _(
                        "Adjusting Entry {link} {percent}%% of {amount} recognized from {date}"
                    )
                ),
                move,
                amount,
            ),
            self._format_strings(
                escape(
                    _(
                        "Adjusting Entry {link} {percent}%% of {amount} recognized on {new_date}"
                    )
                ),
                move,
                amount,
            ),
        )

    def _get_generated_entries_action(self, created_moves):
        action = {
            "name": _("Generated Entries"),
            "domain": [("id", "in", created_moves.ids)],
            "res_model": "account.move",
            "view_mode": "list,form",
            "type": "ir.actions.act_window",
            "views": [
                (self.env.ref("account.view_move_tree").id, "list"),
                (False, "form"),
            ],
        }
        if len(created_moves) == 1:
            action.update({"view_mode": "form", "res_id": created_moves.id})
        return action

    @_debug.perf.timed
    def _do_action_change_period(self, move_vals):
        accrual_account = (
            self.revenue_accrual_account
            if self.account_type == "income"
            else self.expense_accrual_account
        )

        created_moves = self.env["account.move"].create(move_vals)
        created_moves._post()
        _debug.pipeline(
            "change_period_created",
            autoentry=self,
            created_moves=created_moves,
            accrual_account=accrual_account,
        )

        destination_move = created_moves[0]
        destination_move_offset = 0
        destination_messages = []
        accrual_move_messages = defaultdict(list)
        accrual_move_offsets = defaultdict(int)
        for move in self.move_line_ids.move_id:
            amount = sum((self.move_line_ids._origin & move.line_ids).mapped("balance"))
            lock_safe_date = self._get_lock_safe_date(move.date)
            accrual_move = created_moves[1:].filtered(
                lambda m, lock_safe_date=lock_safe_date: m.date == lock_safe_date
            )

            if (
                accrual_account.reconcile
                and accrual_move.state == "posted"
                and destination_move.state == "posted"
            ):
                _debug.logic(
                    "reconciling_accrual_destination",
                    autoentry=self,
                    accrual_move=accrual_move,
                    destination_move=destination_move,
                )
                self._reconcile_accrual_lines(
                    accrual_account,
                    accrual_move,
                    destination_move,
                    destination_move_offset,
                    accrual_move_offsets,
                )
                destination_move_offset += 2
            destination_message, accrual_message = self._post_accrual_messages(
                move, accrual_move, destination_move, amount
            )
            destination_messages.append(destination_message)
            accrual_move_messages[accrual_move].append(accrual_message)

        destination_move.message_post(body=Markup("<br/>\n").join(destination_messages))
        for accrual_move, messages in accrual_move_messages.items():
            accrual_move.message_post(body=Markup("<br/>\n").join(messages))

        return self._get_generated_entries_action(created_moves)

    @_debug.perf.timed
    def _do_action_change_account(self, move_vals):
        new_move = self.env["account.move"].create(move_vals)
        new_move._post()

        grouped_lines = defaultdict(lambda: self.env["account.move.line"])
        destination_lines = self.move_line_ids.filtered(
            lambda x: x.account_id == self.destination_account_id
        )
        for line in self.move_line_ids - destination_lines:
            grouped_lines[(line.partner_id, line.currency_id, line.account_id)] += line

        if _debug.logic.enabled:
            _debug.logic(
                "change_account_reconcile_plan",
                autoentry=self,
                move=new_move,
                groups=len(grouped_lines),
                reconcilable_groups=sum(
                    1 for (_p, _c, account) in grouped_lines if account.reconcile
                ),
                destination_lines=len(destination_lines),
                destination_reconcilable=self.destination_account_id.reconcile,
            )
        for (partner, currency, account), lines in grouped_lines.items():
            if account.reconcile:
                to_reconcile = lines + new_move.line_ids.filtered(
                    lambda x, account=account, partner=partner, currency=currency: (
                        x.account_id == account
                        and x.partner_id == partner
                        and x.currency_id == currency
                    )
                )
                to_reconcile.reconcile()

        if destination_lines and self.destination_account_id.reconcile:
            for partner, currency in {
                (partner, currency) for partner, currency, __ in grouped_lines
            }:
                to_reconcile = destination_lines + new_move.line_ids.filtered(
                    lambda x, partner=partner, currency=currency: (
                        x.account_id == self.destination_account_id
                        and x.partner_id == partner
                        and x.currency_id == currency
                    )
                )
                to_reconcile.reconcile()

        acc_transfer_per_move = defaultdict(lambda: defaultdict(lambda: 0))
        for line in self.move_line_ids:
            acc_transfer_per_move[line.move_id][line.account_id] += line.balance

        for move, balances_per_account in acc_transfer_per_move.items():
            message_to_log = self._format_transfer_source_log(
                balances_per_account, new_move
            )
            if message_to_log:
                move.message_post(body=message_to_log)

        new_move.message_post(
            body=self._format_new_transfer_move_log(acc_transfer_per_move)
        )

        return {
            "name": _("Transfer"),
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "res_model": "account.move",
            "res_id": new_move.id,
        }

    def _format_new_transfer_move_log(self, acc_transfer_per_move):
        transfer_format = Markup(
            "<li>%s, <strong>%%(account_source_name)s</strong></li>"
        ) % _("{amount} ({debit_credit}) from {link}")
        return _(
            "This entry transfers the following amounts to %(destination)s",
            destination=Markup("<strong>%s</strong>")
            % self.destination_account_id.display_name,
        ) + Markup("<ul>%(transfer_logs)s</ul>") % {
            "transfer_logs": Markup().join(
                [
                    self._format_strings(
                        transfer_format % {"account_source_name": account.display_name},
                        move,
                        balance,
                    )
                    for move, balances_per_account in acc_transfer_per_move.items()
                    for account, balance in balances_per_account.items()
                    if account != self.destination_account_id
                ],
            ),
        }

    def _format_transfer_source_log(self, balances_per_account, transfer_move):
        if not balances_per_account:
            return None

        transfer_format = Markup(
            _(
                "{amount} ({debit_credit}) from <strong>{account_source_name}</strong> were transferred to <strong>{account_target_name}</strong> by {link}"
            )
        )

        return Markup("<ul>%s</ul>") % Markup().join(
            [
                Markup("<li>%s</li>")
                % self._format_strings(
                    transfer_format, transfer_move, balance, account.display_name
                )
                for account, balance in balances_per_account.items()
                if account != self.destination_account_id
            ]
        )

    def _format_move_link(self, move):
        return move._get_html_link()

    def _format_strings(self, string, move, amount=None, account_source_name=""):
        return string.format(
            label=move.name or _("Adjusting Entry"),
            percent=float_repr(self.percentage, 2),
            name=move.name,
            id=move.id,
            amount=formatLang(
                self.env, abs(amount), currency_obj=self.company_id.currency_id
            )
            if amount
            else "",
            debit_credit=(amount < 0 and _("C")) or _("D") if amount else None,
            link=self._format_move_link(move),
            date=format_date(self.env, move.date),
            new_date=(self.date and format_date(self.env, self.date)) or _("[Not set]"),
            account_source_name=account_source_name,
            account_target_name=self.destination_account_id.display_name,
        )
