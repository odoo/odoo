import ast
import json
import random
from collections import Counter, defaultdict
from datetime import timedelta
from typing import NamedTuple

from babel.dates import format_date, format_datetime

from odoo import _, api, fields, models
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog
from odoo.release import version_info
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF
from odoo.tools import SQL
from odoo.tools.misc import get_lang

_debug = DebugLog(__name__)

BANK_CASH_TYPES = ("bank", "cash", "credit")
SALE_PURCHASE_TYPES = ("sale", "purchase")


class BankPosition(NamedTuple):
    last_statement_id: int | None
    has_statement_lines: bool
    running_balance: float


def group_by_journal(vals_list):
    res = defaultdict(list)
    for vals in vals_list:
        res[vals["journal_id"]].append(vals)
    return res


class AccountJournal(models.Model):
    _inherit = "account.journal"

    kanban_dashboard = fields.Text(compute="_compute_kanban_dashboard")
    kanban_dashboard_graph = fields.Text(compute="_compute_kanban_dashboard_graph")
    show_on_dashboard = fields.Boolean(
        string="Show journal on dashboard",
        default=True,
        help="Whether this journal should be displayed on the dashboard or not",
    )
    color = fields.Integer(
        string="Color Index",
        default=0,
    )
    current_statement_balance = fields.Monetary(compute="_compute_bank_running_balance")
    has_statement_lines = fields.Boolean(compute="_compute_bank_running_balance")
    has_posted_entries = fields.Boolean(compute="_compute_entry_presence")
    has_entries = fields.Boolean(compute="_compute_entry_presence")
    has_sequence_holes = fields.Boolean(compute="_compute_has_sequence_holes")
    has_unhashed_entries = fields.Boolean(
        string="Unhashed Entries",
        compute="_compute_has_unhashed_entries",
    )
    last_statement_id = fields.Many2one(
        comodel_name="account.bank.statement",
        compute="_compute_last_statement_id",
    )

    def _dashboard_currency(self):
        self.check_singleton()
        return self.currency_id or self.env["res.currency"].browse(
            self.company_id.sudo().currency_id.id
        )

    @api.depends_context("allowed_company_ids")
    def _compute_bank_running_balance(self):
        bank_cash_journals = self.filtered(
            lambda journal: journal.type in BANK_CASH_TYPES
        )
        other_journals = self - bank_cash_journals
        other_journals.has_statement_lines = False
        other_journals.current_statement_balance = 0.0
        positions = bank_cash_journals._get_bank_positions()
        for journal in bank_cash_journals:
            position = positions[journal.id]
            journal.has_statement_lines = position.has_statement_lines
            journal.current_statement_balance = position.running_balance

    @api.depends_context("allowed_company_ids")
    def _compute_last_statement_id(self):
        bank_cash_journals = self.filtered(
            lambda journal: journal.type in BANK_CASH_TYPES
        )
        (self - bank_cash_journals).last_statement_id = False
        positions = bank_cash_journals._get_bank_positions()
        Statement = self.env["account.bank.statement"]
        for journal in bank_cash_journals:
            journal.last_statement_id = Statement.browse(
                positions[journal.id].last_statement_id
            )

    @api.depends_context("allowed_company_ids", "company")
    def _compute_kanban_dashboard(self):
        dashboard_data = self._get_journal_dashboard_data_batched()
        for journal in self:
            journal.kanban_dashboard = json.dumps(dashboard_data[journal.id])

    @api.depends("current_statement_balance")
    @_debug.perf.timed
    def _compute_kanban_dashboard_graph(self):
        bank_cash_journals = self.filtered(
            lambda journal: journal.type in BANK_CASH_TYPES
        )
        bank_cash_graph_datas = bank_cash_journals._prepare_bank_cash_graph_data()
        for journal in bank_cash_journals:
            journal.kanban_dashboard_graph = json.dumps(
                bank_cash_graph_datas[journal.id]
            )

        sale_purchase_journals = self.filtered(
            lambda journal: journal.type in SALE_PURCHASE_TYPES
        )
        sale_purchase_graph_datas = (
            sale_purchase_journals._prepare_sale_purchase_graph_data()
        )
        for journal in sale_purchase_journals:
            journal.kanban_dashboard_graph = json.dumps(
                sale_purchase_graph_datas[journal.id]
            )

        (
            self - bank_cash_journals - sale_purchase_journals
        ).kanban_dashboard_graph = False

    @_debug.perf.timed
    def _query_has_sequence_holes(self):
        self.env["account.move"].flush_model(
            ["journal_id", "date", "sequence_prefix", "made_sequence_gap"]
        )
        to_check = self.grouped(
            lambda j: j.company_id._get_user_fiscal_lock_date(j, ignore_exceptions=True)
        )
        descendants = (
            self.env["res.company"]
            .sudo()
            .search([("id", "child_of", self.company_id.ids)])
        )
        queries = []
        for lock_date, journals in to_check.items():
            journal_companies = journals.company_id
            companies = descendants.filtered(
                lambda company, journal_companies=journal_companies: (
                    journal_companies & company.parent_ids
                )
            )
            queries.append(
                SQL(
                    """
                    SELECT move.journal_id,
                           move.sequence_prefix
                      FROM account_move move
                     WHERE move.journal_id = ANY(%(journal_ids)s)
                       AND move.company_id = ANY(%(company_ids)s)
                       AND move.made_sequence_gap IS TRUE
                       AND move.date > %(lock_date)s
                  GROUP BY move.journal_id, move.sequence_prefix
                    """,
                    journal_ids=journals.ids,
                    company_ids=companies.ids,
                    lock_date=lock_date,
                )
            )
        _debug.pipeline(
            "sequence_hole_queries",
            journals=self,
            lock_dates=len(to_check),
            queries=len(queries),
            companies=descendants,
        )
        if not queries:
            return []
        self.env.cr.execute(SQL(" UNION ALL ".join(["%s"] * len(queries)), *queries))
        return self.env.cr.fetchall()

    def _get_unhashed_candidate_moves(self):
        if not self:
            return self.env["account.move"]
        by_lock_date = self.grouped(
            lambda journal: journal.company_id._get_user_fiscal_lock_date(journal)
        )
        return self.env["account.move"].search(
            Domain("restrict_mode_hash_table", "=", True)
            & Domain("inalterable_hash", "=", False)
            & Domain.OR(
                Domain("journal_id", "in", journals.ids)
                & Domain("date", ">", lock_date)
                for lock_date, journals in by_lock_date.items()
            )
        )

    def _chains_to_hash(self, moves, include_pre_last_hash, early_stop):
        return moves._get_chains_to_hash(
            force_hash=True,
            raise_if_gap=False,
            raise_if_no_document=False,
            raise_if_unreconciled=False,
            early_stop=early_stop,
            include_pre_last_hash=include_pre_last_hash,
        )

    def _get_moves_to_hash(self, include_pre_last_hash, early_stop):
        return self._chains_to_hash(
            self._get_unhashed_candidate_moves(), include_pre_last_hash, early_stop
        )

    @api.depends_context("allowed_company_ids", "uid")
    def _compute_has_sequence_holes(self):
        has_sequence_holes = {
            journal_id for journal_id, _prefix in self._query_has_sequence_holes()
        }
        for journal in self:
            journal.has_sequence_holes = journal.id in has_sequence_holes

    @api.depends_context("allowed_company_ids", "uid")
    def _compute_has_unhashed_entries(self):
        hashing_journals = self.filtered("restrict_mode_hash_table")
        (self - hashing_journals).has_unhashed_entries = False
        candidates = hashing_journals._get_unhashed_candidate_moves().grouped(
            "journal_id"
        )
        no_move = self.env["account.move"]
        for journal in hashing_journals:
            journal.has_unhashed_entries = bool(
                journal._chains_to_hash(
                    candidates.get(journal, no_move),
                    include_pre_last_hash=False,
                    early_stop=True,
                )
            )

    @api.depends_context("allowed_company_ids")
    @_debug.perf.timed
    def _compute_entry_presence(self):
        if not self.ids:
            _debug.logic("entry_presence_skipped", reason="no_ids", journals=self)
            self.has_posted_entries = False
            self.has_entries = False
            return
        sql_query = SQL(
            """
            SELECT
                j.id,
                posted.val,
                any_entry.val
            FROM
              account_journal j
            LEFT JOIN LATERAL (
                SELECT TRUE AS val
                FROM account_move m
                WHERE m.journal_id = j.id
                    AND m.state = 'posted'
                LIMIT 1
                              ) AS posted ON TRUE
            LEFT JOIN LATERAL (
                SELECT TRUE AS val
                FROM account_move m
                WHERE m.journal_id = j.id
                LIMIT 1
                              ) AS any_entry ON TRUE
            WHERE j.id = ANY(%(journal_ids)s)
            """,
            journal_ids=self.ids,
        )
        self.env.cr.execute(sql_query)
        presence = {
            journal_id: (bool(has_posted), bool(has_any))
            for journal_id, has_posted, has_any in self.env.cr.fetchall()
        }
        _debug.perf.count("entry_presence_rows", rows=len(presence))
        for journal in self:
            journal.has_posted_entries, journal.has_entries = presence.get(
                journal.id, (False, False)
            )

    def _graph_title_and_key(self):
        if self.type in ["sale", "purchase"]:
            return ["", _("Residual amount")]
        elif self.type == "cash":
            return ["", _("Cash: Balance")]
        elif self.type == "bank":
            return ["", _("Bank: Balance")]
        elif self.type == "credit":
            return ["", _("Credit Card: Balance")]
        return ["", ""]

    @_debug.perf.timed
    def _prepare_bank_cash_graph_data(self):
        def prepare_graph_point(date, amount, currency):
            name = format_date(date, "d LLLL Y", locale=locale)
            short_name = format_date(date, "d MMM", locale=locale)
            return {"x": short_name, "y": currency.round(amount), "name": name}

        today = fields.Date.context_today(self)
        last_month = today + timedelta(days=-30)
        locale = get_lang(self.env).code

        query = """
            SELECT move.journal_id,
                   move.date,
                   SUM(st_line.amount) AS amount
              FROM account_bank_statement_line st_line
              JOIN account_move move ON move.id = st_line.move_id
             WHERE move.journal_id = ANY(%s)
               AND move.date > %s
               AND move.company_id = ANY(%s)
          GROUP BY move.date, move.journal_id
          ORDER BY move.date DESC
        """
        self.env.cr.execute(query, (self.ids, last_month, self.env.companies.ids))
        query_result = group_by_journal(self.env.cr.dictfetchall())
        _debug.pipeline(
            "bank_cash_graph_rows",
            journals=self,
            journals_with_rows=len(query_result),
            since=last_month,
        )

        color = "#875A7B" if version_info[-1] == "e" else "#7c7bad"
        result = {}
        for journal in self:
            graph_title, graph_key = journal._graph_title_and_key()
            currency = journal._dashboard_currency()
            journal_result = query_result[journal.id]

            is_sample_data = not journal_result and not journal.has_statement_lines

            data = []
            if is_sample_data:
                graph_key = _("Sample data")
                sample = random.Random(journal.id)
                for i in range(30, 0, -5):
                    current_date = today + timedelta(days=-i)
                    data.append(
                        prepare_graph_point(
                            current_date, sample.randint(-5, 15), currency
                        )
                    )
            else:
                last_balance = journal.current_statement_balance
                if not journal_result or journal_result[0]["date"] < today:
                    data.append(prepare_graph_point(today, last_balance, currency))
                date = today
                amount = last_balance
                for val in journal_result:
                    date = val["date"]
                    data[:0] = [prepare_graph_point(date, amount, currency)]
                    amount -= val["amount"]

                if date.strftime(DF) != last_month.strftime(DF):
                    data[:0] = [prepare_graph_point(last_month, amount, currency)]

            _debug.logic(
                "bank_cash_graph_mode",
                journal=journal,
                sample=is_sample_data,
                points=len(data),
            )
            result[journal.id] = [
                {
                    "values": data,
                    "title": graph_title,
                    "key": graph_key,
                    "area": True,
                    "color": color,
                    "is_sample_data": is_sample_data,
                }
            ]
        return result

    @_debug.perf.timed
    def _prepare_sale_purchase_graph_data(self):
        today = fields.Date.context_today(self)
        lang_code = get_lang(self.env).code
        day_of_week = int(format_datetime(today, "e", locale=lang_code))
        first_day_of_week = today + timedelta(days=-day_of_week + 1)

        def format_month(d):
            return format_date(d, "MMM", locale=lang_code)

        self.env.cr.execute(
            """
            SELECT move.journal_id,
                   COALESCE(SUM(move.amount_residual_signed) FILTER (WHERE invoice_date_due < %(start_week1)s), 0) AS total_before,
                   COALESCE(SUM(move.amount_residual_signed) FILTER (WHERE invoice_date_due >= %(start_week1)s AND invoice_date_due < %(start_week2)s), 0) AS total_week1,
                   COALESCE(SUM(move.amount_residual_signed) FILTER (WHERE invoice_date_due >= %(start_week2)s AND invoice_date_due < %(start_week3)s), 0) AS total_week2,
                   COALESCE(SUM(move.amount_residual_signed) FILTER (WHERE invoice_date_due >= %(start_week3)s AND invoice_date_due < %(start_week4)s), 0) AS total_week3,
                   COALESCE(SUM(move.amount_residual_signed) FILTER (WHERE invoice_date_due >= %(start_week4)s AND invoice_date_due < %(start_week5)s), 0) AS total_week4,
                   COALESCE(SUM(move.amount_residual_signed) FILTER (WHERE invoice_date_due >= %(start_week5)s), 0) AS total_after
              FROM account_move move
             WHERE move.journal_id = ANY(%(journal_ids)s)
               AND move.state = 'posted'
               AND move.payment_state in ('not_paid', 'partial')
               AND move.move_type = ANY(%(invoice_types)s)
               AND move.company_id = ANY(%(company_ids)s)
          GROUP BY move.journal_id
            """,
            {
                "invoice_types": list(self.env["account.move"].get_invoice_types(True)),
                "journal_ids": self.ids,
                "company_ids": self.env.companies.ids,
                "start_week1": first_day_of_week + timedelta(days=-7),
                "start_week2": first_day_of_week + timedelta(days=0),
                "start_week3": first_day_of_week + timedelta(days=7),
                "start_week4": first_day_of_week + timedelta(days=14),
                "start_week5": first_day_of_week + timedelta(days=21),
            },
        )
        query_results = {r["journal_id"]: r for r in self.env.cr.dictfetchall()}
        _debug.pipeline(
            "sale_purchase_graph_rows",
            journals=self,
            journals_with_rows=len(query_results),
            week_start=first_day_of_week,
        )
        result = {}
        for journal in self:
            currency = journal._dashboard_currency()
            graph_title, graph_key = journal._graph_title_and_key()
            sign = 1 if journal.type == "sale" else -1
            journal_data = query_results.get(journal.id)
            data = self._get_due_week_buckets(first_day_of_week, format_month)

            is_sample_data = not journal_data
            if not is_sample_data:
                data[0]["value"] = currency.round(sign * journal_data["total_before"])
                data[1]["value"] = currency.round(sign * journal_data["total_week1"])
                data[2]["value"] = currency.round(sign * journal_data["total_week2"])
                data[3]["value"] = currency.round(sign * journal_data["total_week3"])
                data[4]["value"] = currency.round(sign * journal_data["total_week4"])
                data[5]["value"] = currency.round(sign * journal_data["total_after"])
            else:
                graph_key = _("Sample data")
                sample = random.Random(journal.id)
                for index in range(6):
                    data[index]["type"] = "o_sample_data"
                    data[index]["value"] = sample.randint(0, 20)

            _debug.logic(
                "sale_purchase_graph_mode",
                journal=journal,
                sample=is_sample_data,
            )
            result[journal.id] = [
                {
                    "values": data,
                    "title": graph_title,
                    "key": graph_key,
                    "is_sample_data": is_sample_data,
                }
            ]
        return result

    def _get_due_week_buckets(self, first_day_of_week, format_month):
        buckets = [{"label": _("Due"), "type": "past"}]
        for offset in range(-1, 3):
            if offset == 0:
                label = _("This Week")
            else:
                start = first_day_of_week + timedelta(days=offset * 7)
                end = start + timedelta(days=6)
                if start.month == end.month:
                    label = f"{start.day} - {end.day} {format_month(end)}"
                else:
                    label = (
                        f"{start.day} {format_month(start)}"
                        f" - {end.day} {format_month(end)}"
                    )
            buckets.append({"label": label, "type": "past" if offset < 0 else "future"})
        buckets.append({"label": _("Not Due"), "type": "future"})
        return buckets

    def _get_journal_dashboard_data_batched(self):
        self.env["account.move"].flush_model()
        self.env["account.move.line"].flush_model()
        self.env["account.payment"].flush_model()
        dashboard_data = {}
        for journal in self:
            dashboard_data[journal.id] = {
                "currency_id": journal._dashboard_currency().id,
                "show_company": len(self.env.companies) > 1
                or journal.company_id.id != self.env.company.id,
                "company_name": journal.company_id.sudo().name,
            }
        if _debug.pipeline.enabled:
            _debug.pipeline(
                "dashboard_batch", over=self, types=dict(Counter(self.mapped("type")))
            )
        with _debug.perf("dashboard_bank_cash", cr=self.env.cr):
            self._update_bank_cash_dashboard_data(dashboard_data)
        with _debug.perf("dashboard_sale_purchase", cr=self.env.cr):
            self._update_sale_purchase_dashboard_data(dashboard_data)
        with _debug.perf("dashboard_general", cr=self.env.cr):
            self._update_general_dashboard_data(dashboard_data)
        with _debug.perf("dashboard_onboarding", cr=self.env.cr):
            self._update_onboarding_data(dashboard_data)
        return dashboard_data

    def _update_dashboard_data_count(self, dashboard_data, model, name, domain):
        res = {
            journal.id: count
            for journal, count in self.env[model]._read_group(
                domain=Domain.AND(
                    (
                        self.env[model]._check_company_domain(self.env.companies),
                        Domain("journal_id", "in", self.ids),
                        domain,
                    )
                ),
                groupby=["journal_id"],
                aggregates=["__count"],
            )
        }
        for journal in self:
            dashboard_data[journal.id][name] = res.get(journal.id, 0)

    def _get_statement_lines_to_reconcile(self):
        self.env.cr.execute(
            """
            SELECT st_line.journal_id,
                   COUNT(st_line.id)
              FROM account_bank_statement_line st_line
              JOIN account_move st_line_move ON st_line_move.id = st_line.move_id
             WHERE st_line.journal_id = ANY(%s)
               AND st_line.company_id = ANY(%s)
               AND st_line.is_reconciled IS NOT TRUE
               AND st_line_move.checked IS TRUE
               AND st_line_move.state = 'posted'
          GROUP BY st_line.journal_id
            """,
            [list(self.ids), list(self.env.companies.ids)],
        )
        return dict(self.env.cr.fetchall())

    def _get_misc_operations_date_limits(self):
        return {
            journal.id: journal.last_statement_id.date
            or journal.company_id.fiscalyear_lock_date
            for journal in self
        }

    def _get_misc_operations_totals(self, date_limits):
        base_domain = Domain(
            [
                *self.env["account.move.line"]._check_company_domain(
                    self.env.companies
                ),
                ("statement_line_id", "=", False),
                ("parent_state", "=", "posted"),
                ("payment_id", "=", False),
            ]
        )
        accounts_by_date_limit = defaultdict(set)
        for journal in self:
            accounts_by_date_limit[date_limits[journal.id]].add(
                journal.default_account_id.id
            )
        totals = {}
        for date_limit, account_ids in accounts_by_date_limit.items():
            totals.update(
                self._get_account_totals_after_date(
                    base_domain, date_limit, account_ids
                )
            )
        return totals

    def _get_account_totals_after_date(self, base_domain, date_limit, account_ids):
        domain = base_domain & Domain("account_id", "in", list(account_ids))
        if date_limit:
            domain &= Domain("date", ">", date_limit)
        return {
            (account.id, date_limit): (balance, count_lines, currencies)
            for account, balance, count_lines, currencies in self.env[
                "account.move.line"
            ]._read_group(
                domain=domain,
                aggregates=["amount_currency:sum", "id:count", "currency_id:recordset"],
                groupby=["account_id"],
            )
        }

    def _get_statement_lines_to_check(self):
        return {
            journal: (amount, count)
            for journal, amount, count in self.env[
                "account.bank.statement.line"
            ]._read_group(
                domain=[
                    ("journal_id", "in", self.ids),
                    ("move_id.company_id", "in", self.env.companies.ids),
                    ("move_id.checked", "=", False),
                    ("move_id.state", "=", "posted"),
                ],
                groupby=["journal_id"],
                aggregates=["amount:sum", "__count"],
            )
        }

    @_debug.perf.timed
    def _update_bank_cash_dashboard_data(self, dashboard_data):
        bank_cash_journals = self.filtered(
            lambda journal: journal.type in BANK_CASH_TYPES
        )
        _debug.logic(
            "bank_cash_scope",
            journals=bank_cash_journals,
            skipped=not bank_cash_journals,
        )
        if not bank_cash_journals:
            return

        number_to_reconcile = bank_cash_journals._get_statement_lines_to_reconcile()
        outstanding_pay_account_balances = (
            bank_cash_journals._get_journal_dashboard_outstanding_payments()
        )
        direct_payment_balances = bank_cash_journals._get_direct_bank_payments()
        journal_misc_date_limit = bank_cash_journals._get_misc_operations_date_limits()
        misc_totals = bank_cash_journals._get_misc_operations_totals(
            journal_misc_date_limit
        )
        to_check = bank_cash_journals._get_statement_lines_to_check()
        _debug.pipeline(
            "bank_cash_inputs_ready",
            journals=bank_cash_journals,
            to_reconcile=len(number_to_reconcile),
            outstanding=len(outstanding_pay_account_balances),
            direct_payments=len(direct_payment_balances),
            misc_totals=len(misc_totals),
            to_check=len(to_check),
        )

        for journal in bank_cash_journals:
            currency = journal._dashboard_currency()
            nb_outstanding_payments, outstanding_pay_account_balance = (
                outstanding_pay_account_balances[journal.id]
            )
            to_check_balance, number_to_check = to_check.get(journal, (0, 0))
            misc_balance, number_misc, misc_currencies = misc_totals.get(
                (journal.default_account_id.id, journal_misc_date_limit[journal.id]),
                (0, 0, currency),
            )
            currency_consistent = misc_currencies == currency
            accessible = (
                journal.company_id.id
                in journal.company_id._get_accessible_branches().ids
            )
            nb_direct_payments, direct_payments_balance = direct_payment_balances[
                journal.id
            ]
            drag_drop_settings = {
                "image": "/account/static/src/img/bank.svg"
                if journal.type in ("bank", "credit")
                else "/web/static/img/rfq.svg",
                "text": _("Drop to import transactions"),
            }
            last_statement_visible = not journal.company_id.fiscalyear_lock_date or (
                journal.last_statement_id.date
                and journal.company_id.fiscalyear_lock_date
                < journal.last_statement_id.date
            )
            _debug.logic(
                "bank_cash_card_flags",
                journal=journal,
                currency_consistent=currency_consistent,
                accessible=accessible,
                last_statement_visible=last_statement_visible,
                number_misc=number_misc,
                number_to_check=number_to_check,
            )

            dashboard_data[journal.id].update(
                {
                    "number_to_check": number_to_check,
                    "to_check_balance": currency.format(to_check_balance),
                    "number_to_reconcile": number_to_reconcile.get(journal.id, 0),
                    "account_balance": currency.format(
                        journal.current_statement_balance + direct_payments_balance
                    ),
                    "has_at_least_one_statement": bool(journal.last_statement_id),
                    "nb_lines_bank_account_balance": (
                        bool(journal.has_statement_lines) or bool(nb_direct_payments)
                    )
                    and accessible,
                    "outstanding_pay_account_balance": currency.format(
                        outstanding_pay_account_balance
                    ),
                    "nb_lines_outstanding_pay_account_balance": nb_outstanding_payments,
                    "last_balance": currency.format(
                        journal.last_statement_id.balance_end_real
                    ),
                    "last_statement_id": journal.last_statement_id.id,
                    "last_statement_visible": last_statement_visible,
                    "has_invalid_statements": journal.has_invalid_statements,
                    "bank_statements_source": journal.bank_statements_source,
                    "nb_misc_operations": number_misc,
                    "misc_class": "text-warning" if not currency_consistent else "",
                    "misc_operations_balance": currency.format(misc_balance)
                    if currency_consistent
                    else None,
                    "drag_drop_settings": drag_drop_settings,
                }
            )

    def _get_draft_sales_purchases_rows(self):
        select = [
            "account_move.journal_id",
            (
                "(CASE WHEN account_move.move_type IN ('out_refund', 'in_refund')"
                " THEN -1 ELSE 1 END) * account_move.amount_total AS amount_total"
            ),
            (
                "(CASE WHEN account_move.move_type IN ('in_invoice', 'in_refund',"
                " 'in_receipt') THEN -1 ELSE 1 END) * account_move.amount_total_signed"
                " AS amount_total_company"
            ),
            "account_move.currency_id AS currency",
            "account_move.move_type",
            "account_move.invoice_date",
            "account_move.company_id",
        ]
        return group_by_journal(
            self.env.execute_query_dict(
                self._get_draft_sales_purchases_query().select(*select)
            )
        )

    def _get_open_sale_purchase_rows(self):
        to_pay = {}
        late = {}
        by_type = self.grouped("type")
        for journal_type in SALE_PURCHASE_TYPES:
            journals = by_type.get(journal_type)
            if not journals:
                continue
            query, selects = journals._get_open_sale_purchase_query(journal_type)
            rows = journals._grouped_move_aggregation(query, selects)
            for journal in journals:
                to_pay[journal.id] = [r for r in rows[journal.id] if r["to_pay"]]
                late[journal.id] = [r for r in rows[journal.id] if r["late"]]
        return to_pay, late

    @_debug.perf.timed
    def _update_sale_purchase_dashboard_data(self, dashboard_data):
        sale_purchase_journals = self.filtered(
            lambda journal: journal.type in SALE_PURCHASE_TYPES
        )
        _debug.logic(
            "sale_purchase_scope",
            journals=sale_purchase_journals,
            skipped=not sale_purchase_journals,
        )
        if not sale_purchase_journals:
            return
        query_results_drafts = sale_purchase_journals._get_draft_sales_purchases_rows()
        query_results_to_pay, late_query_results = (
            sale_purchase_journals._get_open_sale_purchase_rows()
        )
        query, selects = sale_purchase_journals._get_to_check_payment_query()
        to_check_vals = sale_purchase_journals._grouped_move_aggregation(query, selects)
        _debug.pipeline(
            "sale_purchase_inputs_ready",
            journals=sale_purchase_journals,
            drafts=len(query_results_drafts),
            to_pay=len(query_results_to_pay),
            late=len(late_query_results),
            to_check=len(to_check_vals),
        )

        for journal in sale_purchase_journals:
            currency = journal._dashboard_currency()
            (number_waiting, sum_waiting) = self._count_results_and_sum_amounts(
                query_results_to_pay[journal.id], currency
            )
            (number_draft, sum_draft) = self._count_results_and_sum_amounts(
                query_results_drafts[journal.id], currency
            )
            (number_late, sum_late) = self._count_results_and_sum_amounts(
                late_query_results[journal.id], currency
            )
            (number_to_check, sum_to_check) = self._count_results_and_sum_amounts(
                to_check_vals[journal.id], currency
            )
            _debug.logic(
                "sale_purchase_card_counts",
                journal=journal,
                draft=number_draft,
                waiting=number_waiting,
                late=number_late,
                to_check=number_to_check,
            )

            if journal.type == "purchase":
                title_has_sequence_holes = _(
                    "Irregularities due to draft, cancelled or deleted bills with a sequence number since last lock date."
                )
                drag_drop_settings = {
                    "image": "/account/static/src/img/bill.svg",
                    "text": _("Drop and let the AI process your bills automatically."),
                }
            else:
                title_has_sequence_holes = _(
                    "Irregularities due to draft, cancelled or deleted invoices with a sequence number since last lock date."
                )
                drag_drop_settings = {
                    "image": "/web/static/img/quotation.svg",
                    "text": _("Drop to import your invoices."),
                }

            dashboard_data[journal.id].update(
                {
                    "number_to_check": number_to_check,
                    "to_check_balance": currency.format(sum_to_check),
                    "title": _("Bills to pay")
                    if journal.type == "purchase"
                    else _("Invoices owed to you"),
                    "number_draft": number_draft,
                    "number_waiting": number_waiting,
                    "number_late": number_late,
                    "sum_draft": currency.format(sum_draft),
                    "sum_waiting": currency.format(
                        sum_waiting * (1 if journal.type == "sale" else -1)
                    ),
                    "sum_late": currency.format(
                        sum_late * (1 if journal.type == "sale" else -1)
                    ),
                    "has_sequence_holes": journal.has_sequence_holes,
                    "title_has_sequence_holes": title_has_sequence_holes,
                    "has_unhashed_entries": journal.has_unhashed_entries,
                    "drag_drop_settings": drag_drop_settings,
                }
            )

    def _update_general_dashboard_data(self, dashboard_data):
        general_journals = self.filtered(lambda journal: journal.type == "general")
        if not general_journals:
            return
        general_journals._update_dashboard_data_count(
            dashboard_data,
            "account.move",
            "number_draft",
            Domain("state", "=", "draft") & Domain("auto_post", "=", "no"),
        )
        for journal in general_journals:
            drag_drop_settings = {
                "image": "/web/static/img/folder.svg",
                "text": _("Drop to create journal entries with attachments."),
                "group": "account.group_account_user",
            }

            dashboard_data[journal.id]["drag_drop_settings"] = drag_drop_settings

    @_debug.perf.timed
    def _update_onboarding_data(self, dashboard_data):
        journal_onboarding_map = {
            "sale": "account_invoice",
            "general": "account_dashboard",
        }
        onboarding_data = defaultdict(dict)
        onboarding_progresses = (
            self.env["onboarding.progress"]
            .sudo()
            .search(
                [
                    (
                        "onboarding_id.route_name",
                        "in",
                        [*journal_onboarding_map.values()],
                    ),
                    ("company_id", "in", self.company_id.ids),
                ]
            )
        )
        for progress in onboarding_progresses:
            ob = progress.onboarding_id
            ob_vals = ob.with_company(progress.company_id)._prepare_rendering_values()
            onboarding_data[progress.company_id][ob.route_name] = ob_vals
            onboarding_data[progress.company_id][ob.route_name][
                "current_onboarding_state"
            ] = ob.current_onboarding_state
            onboarding_data[progress.company_id][ob.route_name]["steps"] = [
                {
                    "id": step.id,
                    "title": step.title,
                    "description": step.description,
                    "state": ob_vals["state"][step.id],
                    "action": step.panel_step_open_action_name,
                }
                for step in ob_vals["steps"]
            ]
        _debug.pipeline(
            "onboarding_resolved",
            journals=self,
            progresses=onboarding_progresses,
            companies=len(onboarding_data),
        )
        for journal in self:
            dashboard_data[journal.id]["onboarding"] = onboarding_data[
                journal.company_id
            ].get(journal_onboarding_map.get(journal.type))

    def _get_draft_sales_purchases_query(self):
        return self.env["account.move"]._search(
            [
                *self.env["account.move"]._check_company_domain(self.env.companies),
                ("journal_id", "in", self.ids),
                ("state", "=", "draft"),
                (
                    "move_type",
                    "in",
                    self.env["account.move"].get_invoice_types(include_receipts=True),
                ),
            ],
            bypass_access=True,
        )

    def _get_to_pay_select(self):
        return SQL("TRUE AS to_pay")

    def _get_sale_purchase_aggregation_selects(self, to_pay_select):
        return [
            SQL("journal_id"),
            SQL("company_id"),
            SQL("currency_id AS currency"),
            SQL("invoice_date_due < %s AS late", fields.Date.context_today(self)),
            SQL("SUM(amount_residual_signed) AS amount_total_company"),
            SQL(
                "SUM((CASE WHEN move_type = ANY(%s) THEN -1 ELSE 1 END)"
                " * amount_residual) AS amount_total",
                self.env["account.move"].get_outbound_types(),
            ),
            SQL("COUNT(*)"),
            to_pay_select,
        ]

    def _get_to_check_aggregation_selects(self):
        return [
            SQL("journal_id"),
            SQL("company_id"),
            SQL("currency_id AS currency"),
            SQL("invoice_date_due < %s AS late", fields.Date.context_today(self)),
            SQL("SUM(amount_total_signed) AS amount_total_company"),
            SQL(
                "SUM((CASE WHEN move_type = ANY(%s) THEN -1 ELSE 1 END)"
                " * amount_total) AS amount_total",
                self.env["account.move"].get_outbound_types(),
            ),
            SQL("COUNT(*)"),
            SQL("TRUE AS to_pay"),
        ]

    def _grouped_move_aggregation(self, query, selects):
        sql = SQL(
            "%s GROUP BY account_move.company_id, account_move.journal_id,"
            " account_move.currency_id, late, to_pay",
            query.select(*selects),
        )
        self.env.cr.execute(sql)
        return group_by_journal(self.env.cr.dictfetchall())

    def _get_open_sale_purchase_query(self, journal_type):
        assert journal_type in ("sale", "purchase")
        query = self.env["account.move"]._search(
            [
                *self.env["account.move"]._check_company_domain(self.env.companies),
                ("journal_id", "in", self.ids),
                ("payment_state", "in", ("not_paid", "partial")),
                (
                    "move_type",
                    "in",
                    ("out_invoice", "out_refund", "out_receipt")
                    if journal_type == "sale"
                    else ("in_invoice", "in_refund", "in_receipt"),
                ),
                ("state", "=", "posted"),
            ],
            bypass_access=True,
        )
        return query, self._get_sale_purchase_aggregation_selects(
            self._get_to_pay_select()
        )

    def _get_to_check_payment_query(self):
        query = self.env["account.move"]._search(
            [
                *self.env["account.move"]._check_company_domain(self.env.companies),
                ("journal_id", "in", self.ids),
                ("checked", "=", False),
                ("state", "=", "posted"),
            ],
            bypass_access=True,
        )
        return query, self._get_to_check_aggregation_selects()

    def _count_results_and_sum_amounts(self, rows, target_currency):
        if not rows:
            return 0, 0

        total_amount = 0
        count = 0
        company = self.env.company
        today = fields.Date.context_today(self)
        ResCurrency = self.env["res.currency"]
        ResCompany = self.env["res.company"]
        for result in rows:
            document_currency = ResCurrency.browse(result.get("currency"))
            document_company = ResCompany.browse(result.get("company_id")) or company
            date = result.get("invoice_date") or today
            count += result.get("count", 1)

            if document_company.currency_id == target_currency:
                total_amount += result.get("amount_total_company") or 0
            else:
                total_amount += document_currency._convert(
                    result.get("amount_total"), target_currency, document_company, date
                )
        _debug.logic(
            "dashboard_amounts_summed",
            rows=len(rows),
            count=count,
            currency=target_currency,
        )
        return count, target_currency.round(total_amount)

    @_debug.perf.timed
    def _get_bank_positions(self):
        if _debug.logic.enabled and not self:
            _debug.logic("bank_positions_skipped", reason="no_journals")
        if not self:
            return {}
        _debug.pipeline("bank_positions_query", journals=self)
        self.env["account.bank.statement.line"].flush_model()
        self.env["account.bank.statement"].flush_model()
        self.env.cr.execute(
            """
            SELECT journal.id AS journal_id,
                   statement.id AS statement_id,
                   COALESCE(statement.balance_end_real, 0) AS balance_end_real,
                   without_statement.amount AS unlinked_amount,
                   without_statement.count AS unlinked_count
              FROM account_journal journal
         LEFT JOIN LATERAL (  -- the statement whose lines run highest: the sum below
                             -- is of the unlinked lines above THIS statement, so any
                             -- other ranking drops the lines in between
                           SELECT id,
                                  first_line_index,
                                  balance_end_real
                             FROM account_bank_statement
                            WHERE journal_id = journal.id
                              AND company_id = ANY(%s)
                              AND first_line_index IS NOT NULL
                         ORDER BY first_line_index DESC, id DESC
                            LIMIT 1
                   ) statement ON TRUE
         LEFT JOIN LATERAL (  -- sum all the lines not linked to a statement with a higher index than the last line of the statement
                           SELECT COALESCE(SUM(stl.amount), 0.0) AS amount,
                                  COUNT(*)
                             FROM account_bank_statement_line stl
                             JOIN account_move move ON move.id = stl.move_id
                            WHERE stl.statement_id IS NULL
                              AND move.state != 'cancel'
                              AND stl.journal_id = journal.id
                              AND stl.company_id = ANY(%s)
                              AND stl.internal_index >= COALESCE(statement.first_line_index, '')
                            LIMIT 1
                   ) without_statement ON TRUE
             WHERE journal.id = ANY(%s)
        """,
            [self.env.companies.ids, self.env.companies.ids, self.ids],
        )
        return {
            row["journal_id"]: BankPosition(
                last_statement_id=row["statement_id"],
                has_statement_lines=bool(row["statement_id"] or row["unlinked_count"]),
                running_balance=row["balance_end_real"] + row["unlinked_amount"],
            )
            for row in self.env.cr.dictfetchall()
        }

    def _get_direct_bank_payments(self):
        self.env.cr.execute(
            """
            SELECT move.journal_id AS journal_id,
                   move.company_id AS company_id,
                   move.currency_id AS currency,
                   COUNT(*) AS count,
                   SUM(CASE
                       WHEN payment.payment_type = 'outbound' THEN -payment.amount
                       ELSE payment.amount
                   END) AS amount_total,
                   SUM(amount_company_currency_signed) AS amount_total_company
              FROM account_payment payment
              JOIN account_move move ON move.id = payment.move_id
              JOIN account_journal journal ON move.journal_id = journal.id
             WHERE payment.is_bank_matched IS TRUE
               AND move.state = 'posted'
               AND payment.journal_id = ANY(%s)
               AND payment.company_id = ANY(%s)
               AND payment.outstanding_account_id = journal.default_account_id
          GROUP BY move.company_id, move.journal_id, move.currency_id
        """,
            [self.ids, self.env.companies.ids],
        )
        return self._summarize_payment_balances(
            group_by_journal(self.env.cr.dictfetchall())
        )

    def _summarize_payment_balances(self, query_result):
        return {
            journal.id: self._count_results_and_sum_amounts(
                query_result[journal.id], journal._dashboard_currency()
            )
            for journal in self
        }

    def _get_journal_dashboard_outstanding_payments(self):
        self.env.cr.execute(
            """
            SELECT payment.journal_id AS journal_id,
                   payment.company_id AS company_id,
                   payment.currency_id AS currency,
                   COUNT(*) AS count,
                   SUM(CASE
                       WHEN payment.payment_type = 'outbound' THEN -payment.amount
                       ELSE payment.amount
                   END) AS amount_total,
                   SUM(amount_company_currency_signed) AS amount_total_company
              FROM account_payment payment
              JOIN account_move move ON move.id = payment.move_id
             WHERE payment.is_bank_matched IS NOT TRUE
               AND move.state = 'posted'
               AND payment.journal_id = ANY(%s)
               AND payment.company_id = ANY(%s)
          GROUP BY payment.company_id, payment.journal_id, payment.currency_id
        """,
            [self.ids, self.env.companies.ids],
        )
        return self._summarize_payment_balances(
            group_by_journal(self.env.cr.dictfetchall())
        )

    def _prepare_move_action_context(self):
        ctx = self.env.context.copy()
        journal = self
        if not ctx.get("default_journal_id"):
            ctx["default_journal_id"] = journal.id
        elif not journal:
            journal = self.browse(ctx["default_journal_id"])
        if journal.type == "sale":
            ctx["default_move_type"] = (
                "out_refund" if ctx.get("refund") else "out_invoice"
            )
        elif journal.type == "purchase":
            ctx["default_move_type"] = (
                "in_refund" if ctx.get("refund") else "in_invoice"
            )
        else:
            ctx["default_move_type"] = "entry"
            ctx["view_no_maturity"] = True
        _debug.logic(
            "move_action_context",
            journal=journal,
            move_type=ctx.get("default_move_type"),
            refund=bool(ctx.get("refund")),
        )
        return ctx

    @_debug.perf.timed
    def action_create_new(self):
        _debug.lifecycle("action_create_new", records=self)
        return {
            "name": _("Create invoice/bill"),
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "res_model": "account.move",
            "view_id": self.env.ref("account.view_move_form").id,
            "context": self._prepare_move_action_context(),
        }

    def _select_action_to_open(self):
        self.check_singleton()
        if self.env.context.get("action_name"):
            return self.env.context.get("action_name")
        elif self.type == "bank":
            return "action_bank_statement_tree"
        elif self.type == "credit":
            return "action_credit_statement_tree"
        elif self.type == "cash":
            return "action_view_bank_statement_tree"
        elif self.type == "sale":
            return "action_move_out_invoice_type"
        elif self.type == "purchase":
            return "action_move_in_invoice_type"
        else:
            return "action_move_journal_line"

    @_debug.perf.timed
    def open_action(self):
        _debug.lifecycle("open_action", records=self)
        self.check_singleton()
        action_name = self._select_action_to_open()

        if not action_name.startswith("account."):
            action_name = "account.%s" % action_name
        _debug.logic(
            "action_selected",
            journal=self,
            action=action_name,
            context_override=bool(self.env.context.get("action_name")),
        )

        action = self.env["ir.actions.act_window"]._get_action_dict_by_xml_id(
            action_name
        )

        if "context" in action and isinstance(action["context"], str):
            action_context = self.env["ir.actions.actions"]._eval_action_context(
                action["context"]
            )
        else:
            action_context = action.get("context", {})
        action["context"] = {
            **action_context,
            **self.env.context,
            "default_journal_id": self.id,
        }
        domain_type_field = (
            "move_id.move_type"
            if action["res_model"] == "account.move.line"
            else "move_type"
        )

        if action.get("domain") and isinstance(action["domain"], str):
            action["domain"] = ast.literal_eval(action["domain"] or "[]")
        if not self.env.context.get("action_name"):
            if self.type == "sale":
                action["domain"] = [
                    (
                        domain_type_field,
                        "in",
                        ("out_invoice", "out_refund", "out_receipt", "entry"),
                    )
                ]
            elif self.type == "purchase":
                action["domain"] = [
                    (
                        domain_type_field,
                        "in",
                        ("in_invoice", "in_refund", "in_receipt", "entry"),
                    )
                ]

        action["domain"] = (action["domain"] or []) + [("journal_id", "=", self.id)]
        _debug.logic(
            "action_domain_built",
            journal=self,
            res_model=action["res_model"],
            domain_terms=len(action["domain"]),
        )
        return action

    @_debug.perf.timed
    def open_payments_action(self, payment_type=False, mode="list"):
        _debug.lifecycle("open_payments_action", records=self)
        if payment_type == "outbound":
            action_ref = "account.action_account_payments_payable"
        elif payment_type == "transfer":
            action_ref = "account.action_account_payments_transfer"
        elif payment_type == "inbound":
            action_ref = "account.action_account_payments"
        else:
            action_ref = "account.action_account_all_payments"
        _debug.logic(
            "payments_action_chosen",
            journal=self,
            payment_type=payment_type,
            action=action_ref,
            mode=mode,
        )
        action = self.env["ir.actions.act_window"]._get_action_dict_by_xml_id(
            action_ref
        )
        action["context"] = dict(
            self.env["ir.actions.actions"]._eval_action_context(action.get("context")),
            default_journal_id=self.id,
            search_default_journal_id=self.id,
        )
        if payment_type == "transfer":
            action["context"].update(
                {
                    "default_partner_id": self.company_id.partner_id.id,
                    "default_is_internal_transfer": True,
                }
            )
        if mode == "form":
            action["views"] = [[False, "form"]]
        return action

    @_debug.perf.timed
    def action_post_all_entries(self):
        _debug.lifecycle("action_post_all_entries", records=self)
        ctx = dict(self.env.context, active_model="account.journal", active_id=self.id)
        moves_to_validate = self.env["account.move"].search(
            [("journal_id", "=", self.id)]
        )
        return moves_to_validate.with_context(ctx).action_post_moves_with_confirmation()

    @_debug.perf.timed
    def open_action_with_context(self):
        _debug.lifecycle("open_action_with_context", records=self)
        action_name = self.env.context.get("action_name", False)
        if not action_name:
            _debug.logic(
                "context_action_skipped", reason="no_action_name", journal=self
            )
            return False
        ctx = dict(self.env.context, default_journal_id=self.id)
        if ctx.get("search_default_journal"):
            ctx.update(search_default_journal_id=self.id)
            ctx["search_default_journal"] = False
        ctx.pop("group_by", None)
        action = self.env["ir.actions.act_window"]._get_action_dict_by_xml_id(
            f"account.{action_name}"
        )
        action["context"] = ctx
        if ctx.get("use_domain"):
            action["domain"] = (
                ctx["use_domain"]
                if isinstance(ctx["use_domain"], list)
                else ["|", ("journal_id", "=", self.id), ("journal_id", "=", False)]
            )
            action["name"] = _(
                "%(action)s for journal %(journal)s",
                action=action["name"],
                journal=self.name,
            )
        _debug.logic(
            "context_action_built",
            journal=self,
            action=action_name,
            use_domain=bool(ctx.get("use_domain")),
        )
        return action

    @_debug.perf.timed
    def open_bank_difference_action(self):
        _debug.lifecycle("open_bank_difference_action", records=self)
        self.check_singleton()
        action = self.env["ir.actions.act_window"]._get_action_dict_by_xml_id(
            "account.action_account_moves_all_a"
        )
        action["context"] = {
            "search_default_account_id": self.default_account_id.id,
            "search_default_group_by_move": False,
            "search_default_no_st_line_id": True,
            "search_default_posted": False,
        }
        date_from = self.last_statement_id.date or self.company_id.fiscalyear_lock_date
        if date_from:
            action["context"] |= {
                "date_from": date_from,
                "date_to": fields.Date.context_today(self),
                "search_default_date_between": True,
            }
        return action

    @_debug.perf.timed
    def open_invalid_statements_action(self):
        _debug.lifecycle("open_invalid_statements_action", records=self)
        self.check_singleton()
        return self.env["ir.actions.act_window"]._get_action_dict_by_xml_id(
            "account.action_bank_statement_tree"
        )

    def _show_sequence_holes(self, domain):
        return {
            "type": "ir.actions.act_window",
            "name": _("Journal Entries"),
            "res_model": "account.move",
            "search_view_id": (
                self.env.ref(
                    "account.view_account_move_with_gaps_in_sequence_filter"
                ).id,
                "search",
            ),
            "view_mode": "list,form",
            "domain": domain,
            "context": {
                "search_default_group_by_sequence_prefix": 1,
                "search_default_irregular_sequences": 1,
                "expand": 1,
            },
        }

    def show_sequence_holes(self):
        has_sequence_holes = self._query_has_sequence_holes()
        domain = Domain(
            self.env["account.move"]._check_company_domain(self.env.companies)
        )
        domain &= Domain.OR(
            Domain("journal_id", "=", journal_id)
            & Domain("sequence_prefix", "=", prefix)
            for journal_id, prefix in has_sequence_holes
        )
        action = self._show_sequence_holes(domain)
        action["context"] = {**self._prepare_move_action_context(), **action["context"]}
        return action

    def show_unhashed_entries(self):
        self.check_singleton()
        chains_to_hash = self._get_moves_to_hash(
            include_pre_last_hash=True, early_stop=False
        )
        moves = self.env["account.move"].concat(
            *[chain_moves["moves"] for chain_moves in chains_to_hash]
        )
        action = {
            "type": "ir.actions.act_window",
            "name": _("Journal Entries to Hash"),
            "res_model": "account.move",
            "domain": [("id", "in", moves.ids)],
            "views": [(False, "list"), (False, "form")],
        }
        if len(moves.ids) == 1:
            action.update(
                {
                    "res_id": moves[0].id,
                    "views": [(False, "form")],
                }
            )
        return action

    def create_bank_statement(self):
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "account.action_bank_statement_tree"
        )
        action.update(
            {
                "views": [[False, "form"]],
                "context": {"default_journal_id": self.id},
            }
        )
        return action

    def create_customer_payment(self):
        return self.open_payments_action("inbound", mode="form")

    def create_supplier_payment(self):
        return self.open_payments_action("outbound", mode="form")
