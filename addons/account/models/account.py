from collections.abc import Set as AbstractSet

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.libs.debug_log import DebugLog
from odoo.tools import SQL, html2plaintext

from odoo.addons.account.models.account_audit_account_status import (
    STATUS_SELECTION,
)

_debug = DebugLog(__name__)


class AccountAccount(models.Model):
    _inherit = "account.account"

    exclude_provision_currency_ids = fields.Many2many(
        comodel_name="res.currency",
        relation="account_account_exclude_res_currency_provision",
        help="Whether or not we have to make provisions for the selected foreign currencies.",
    )
    budget_item_ids = fields.One2many(
        comodel_name="account.report.budget.item",
        inverse_name="account_id",
    )  # To use it in the domain when adding accounts from the report

    audit_debit = fields.Monetary(
        string="Debit",
        currency_field="company_currency_id",
        compute="_compute_audit_period",
        search="_search_audit_debit",
    )
    audit_credit = fields.Monetary(
        string="Credit",
        currency_field="company_currency_id",
        compute="_compute_audit_period",
        search="_search_audit_credit",
    )
    audit_balance = fields.Monetary(
        string="Balance",
        currency_field="company_currency_id",
        compute="_compute_audit_period",
        search="_search_audit_balance",
    )
    audit_balance_show_warning = fields.Boolean(
        compute="_compute_audit_balance_show_warning"
    )
    audit_previous_balance = fields.Monetary(
        string="Balance N-1",
        currency_field="company_currency_id",
        compute="_compute_audit_period",
        search="_search_audit_previous_balance",
    )
    audit_previous_balance_show_warning = fields.Boolean(
        compute="_compute_audit_previous_balance_show_warning"
    )
    audit_var_n_1 = fields.Monetary(
        string="Var N-1",
        currency_field="company_currency_id",
        compute="_compute_audit_variation",
        search="_search_audit_var_n_1",
    )
    audit_var_percentage = fields.Float(
        string="Var %",
        compute="_compute_audit_variation",
        search="_search_audit_var_percentage",
        default=False,
    )
    audit_status = fields.Selection(
        selection=STATUS_SELECTION,
        string="Status",
        compute="_compute_audit_status",
        inverse="_inverse_audit_status",
    )

    account_status = fields.One2many(
        comodel_name="account.audit.account.status",
        inverse_name="account_id",
    )
    last_message = fields.Char(compute="_compute_last_message")

    def _get_domain_audit_field(
        self, field_name: str, operator: str, value, previous=False
    ):
        if isinstance(value, AbstractSet):
            value = tuple(value)
        query = self._search([])
        query.add_where(
            self._fields[field_name]._condition_to_sql(
                field_name,
                operator,
                value,
                self,
                query.table,
                query,
            )
        )

        result = self.env.execute_query_dict(query.select())
        return [("id", "in", [row["id"] for row in result])]

    @_debug.perf.timed
    def _search_audit_debit(self, operator, value):
        return self._get_domain_audit_field("audit_debit", operator, value)

    @_debug.perf.timed
    def _search_audit_credit(self, operator, value):
        return self._get_domain_audit_field("audit_credit", operator, value)

    @_debug.perf.timed
    def _search_audit_balance(self, operator, value):
        return self._get_domain_audit_field("audit_balance", operator, value)

    @_debug.perf.timed
    def _search_audit_previous_balance(self, operator, value):
        return self._get_domain_audit_field("audit_previous_balance", operator, value)

    @_debug.perf.timed
    def _search_audit_var_n_1(self, operator, value):
        return self._get_domain_audit_field("audit_var_n_1", operator, value)

    @_debug.perf.timed
    def _search_audit_var_percentage(self, operator, value):
        return self._get_domain_audit_field("audit_var_percentage", operator, value)

    @api.depends_context("working_file_id")
    @_debug.perf.timed
    def _compute_audit_period(self):
        working_file = self.env["account.return"].browse(
            self.env.context.get("working_file_id")
        )
        found_ids = set()

        if working_file and self.ids:
            query = self._as_query(ordered=False)
            for (
                account_id,
                debit,
                credit,
                balance,
                previous_balance,
            ) in self.env.execute_query(
                query.select(
                    *(
                        self._field_to_sql(query.table, field_name, query)
                        for field_name in (
                            "id",
                            "audit_debit",
                            "audit_credit",
                            "audit_balance",
                            "audit_previous_balance",
                        )
                    )
                )
            ):
                account = self.browse(account_id)
                account.audit_debit = debit
                account.audit_credit = credit
                account.audit_balance = balance
                account.audit_previous_balance = previous_balance
                found_ids.add(account_id)
            _debug.perf.count("audit_rows_fetched", rows=len(found_ids))

        _debug.pipeline(
            "audit_balances_fetched",
            working_file=working_file,
            accounts=len(self),
            found=len(found_ids),
        )
        remaining = self - self.browse(found_ids)
        remaining.audit_debit = remaining.audit_credit = remaining.audit_balance = (
            remaining.audit_previous_balance
        ) = 0

    @api.depends("audit_balance", "audit_previous_balance")
    def _compute_audit_variation(self):
        for account in self:
            account.audit_var_n_1 = (
                account.audit_balance - account.audit_previous_balance
            )

            if self.env.company.currency_id.is_zero(account.audit_previous_balance):
                account.audit_var_percentage = False
            else:
                account.audit_var_percentage = (
                    account.audit_balance - account.audit_previous_balance
                ) / account.audit_previous_balance

    @api.depends_context("working_file_id")
    @_debug.perf.timed
    def _compute_audit_status(self):
        working_file = self.env["account.return"].browse(
            self.env.context.get("working_file_id")
        )

        self.audit_status = "todo"

        if working_file:
            create_vals = []
            account_status_by_account = {
                status.account_id: status
                for status in working_file.audit_account_status_ids
            }
            for account in self:
                if account in account_status_by_account:
                    account.audit_status = account_status_by_account[account].status
                else:
                    create_vals.append(
                        {
                            "account_id": account.id,
                            "audit_id": working_file.id,
                        }
                    )
            if create_vals:
                self.env["account.audit.account.status"].create(create_vals)
            _debug.pipeline(
                "audit_statuses_missing",
                working_file=working_file,
                accounts=self,
                created=len(create_vals),
            )

    def _inverse_audit_status(self):
        working_file = self.env["account.return"].browse(
            self.env.context.get("working_file_id")
        )

        if working_file:
            account_status_by_account = {
                status.account_id: status
                for status in working_file.audit_account_status_ids
            }
            for account in self:
                if account in account_status_by_account:
                    account_status_by_account[account].status = account.audit_status

    @_debug.perf.timed
    def _compute_balance_warning(self, balance_field_name, warning_field_name):
        for account in self:
            if account.internal_group == "asset":
                account[warning_field_name] = (
                    account.company_currency_id.compare_amounts(
                        account[balance_field_name], 0
                    )
                    == -1
                )
            elif account.internal_group == "liability":
                account[warning_field_name] = (
                    account.company_currency_id.compare_amounts(
                        account[balance_field_name], 0
                    )
                    == 1
                )
            else:
                account[warning_field_name] = False

    @api.depends("audit_balance")
    def _compute_audit_balance_show_warning(self):
        self._compute_balance_warning("audit_balance", "audit_balance_show_warning")

    @api.depends("audit_previous_balance")
    def _compute_audit_previous_balance_show_warning(self):
        self._compute_balance_warning(
            "audit_previous_balance", "audit_previous_balance_show_warning"
        )

    @api.depends_context("working_file_id")
    @_debug.perf.timed
    def _compute_last_message(self):
        working_file = self.env["account.return"].browse(
            self.env.context.get("working_file_id")
        )
        if not working_file:
            for account in self:
                account.last_message = False
            return

        self.env["mail.message"].flush_model(["model", "res_id", "body"])
        self.env["account.report.annotation"].flush_model(["message_id"])

        self.env.cr.execute(
            """
            SELECT DISTINCT ON (message.res_id) message.res_id, message.body
            FROM mail_message message
            JOIN account_report_annotation annotation ON annotation.message_id = message.id
            WHERE message.model = 'account.account' AND message.res_id = ANY(%s) AND annotation.date >= %s AND annotation.date <= %s
            ORDER BY message.res_id, message.create_date DESC
        """,
            (list(self.ids), working_file.date_from, working_file.date_to),
        )
        last_message_by_account = {
            row[0]: html2plaintext(row[1]) for row in self.env.cr.fetchall()
        }
        _debug.perf.count("last_messages_fetched", rows=len(last_message_by_account))

        for account in self:
            account.last_message = last_message_by_account.get(account.id, False)

    @_debug.perf.timed
    def _field_to_sql(self, alias, field_expr, query=None) -> SQL:
        def add_aml_join(join_alias, date_from, date_to, company_ids):
            _debug.pipeline(
                "audit_aml_join_requested",
                join_alias=join_alias,
                date_from=date_from,
                date_to=date_to,
                companies=len(company_ids),
            )
            self.env["account.move.line"].flush_model()
            query.add_join(
                "LEFT JOIN",
                join_alias,
                SQL(
                    """
                    (SELECT SUM(COALESCE(debit, 0.0)) AS debit,
                            SUM(COALESCE(credit, 0.0)) AS credit,
                            SUM(COALESCE(balance, 0.0)) AS balance,
                            account_id
                       FROM (
                                SELECT aml.debit, aml.credit, aml.balance, aml.account_id
                                  FROM account_move_line aml
                                  JOIN account_account aml_account ON aml_account.id = aml.account_id
                                 WHERE aml.date <= %(date_to)s
                                   AND NOT aml_account.account_type ILIKE ANY(ARRAY['income%%', 'expense%%', 'equity_unaffected'])
                                   AND aml.company_id = ANY(%(company_ids)s)
                                   AND aml.parent_state = 'posted'

                                UNION ALL

                                SELECT aml.debit, aml.credit, aml.balance, aml.account_id
                                  FROM account_move_line aml
                                  JOIN account_account aml_account ON aml_account.id = aml.account_id
                                 WHERE aml.date <= %(date_to)s
                                   AND aml.date >= %(date_from)s
                                   AND aml_account.account_type ILIKE ANY(ARRAY['income%%', 'expense%%', 'equity_unaffected'])
                                   AND aml.company_id = ANY(%(company_ids)s)
                                   AND aml.parent_state = 'posted'
                            ) aml
                   GROUP BY account_id)
                    """,
                    date_from=date_from,
                    date_to=date_to,
                    company_ids=company_ids,
                ),
                SQL(
                    "%s = %s",
                    SQL.identifier(join_alias, "account_id"),
                    self._field_to_sql(alias, "id", query),
                ),
            )

        if field_expr not in (
            "audit_debit",
            "audit_credit",
            "audit_balance",
            "audit_previous_balance",
            "audit_status",
            "audit_var_n_1",
            "audit_var_percentage",
        ):
            return super()._field_to_sql(alias, field_expr, query)

        if field_expr == "audit_status":
            query.add_join(
                "LEFT JOIN",
                "account_audit_account_status",
                "account_audit_account_status",
                SQL(
                    "account_audit_account_status.audit_id = %s AND account_audit_account_status.account_id = %s",
                    self.env.context.get("working_file_id"),
                    self._field_to_sql(alias, "id", query),
                ),
            )
            return SQL("account_audit_account_status.status")

        working_file = self.env["account.return"].browse(
            self.env.context.get("working_file_id")
        )
        _debug.logic(
            "audit_field_sql_resolved",
            field=field_expr,
            working_file=working_file,
            skipped=not working_file,
        )
        if not working_file:
            return SQL()

        if field_expr in ("audit_debit", "audit_credit", "audit_balance"):
            field_name = field_expr.replace("audit_", "")
            add_aml_join(
                "current_account_move_lines",
                working_file.date_from,
                working_file.date_to,
                working_file.company_ids.ids,
            )
            return SQL(
                "COALESCE(%s, 0.0)",
                SQL.identifier("current_account_move_lines", field_name),
            )

        if field_expr == "audit_previous_balance":
            previous_period_start, previous_period_end = (
                working_file.type_id._get_period_boundaries(
                    working_file.company_id,
                    (working_file.date_from or fields.Date.today())
                    - relativedelta(days=1),
                )
            )
            add_aml_join(
                "prev_account_move_line",
                previous_period_start,
                previous_period_end,
                working_file.company_ids.ids,
            )
            return SQL("COALESCE(prev_account_move_line.balance, 0.0)")

        if field_expr in ("audit_var_n_1", "audit_var_percentage"):
            previous_period_start, previous_period_end = (
                working_file.type_id._get_period_boundaries(
                    working_file.company_id,
                    (working_file.date_from or fields.Date.today())
                    - relativedelta(days=1),
                )
            )
            add_aml_join(
                "current_account_move_lines",
                working_file.date_from,
                working_file.date_to,
                working_file.company_ids.ids,
            )
            add_aml_join(
                "prev_account_move_line",
                previous_period_start,
                previous_period_end,
                working_file.company_ids.ids,
            )
            if field_expr == "audit_var_n_1":
                return SQL(
                    "(COALESCE(current_account_move_lines.balance, 0) - COALESCE(prev_account_move_line.balance, 0))"
                )
            else:
                return SQL("""
                    CASE WHEN prev_account_move_line.balance IS NULL THEN NULL
                         ELSE (COALESCE(current_account_move_lines.balance, 0) - COALESCE(prev_account_move_line.balance, 0)) / COALESCE(NULLIF(prev_account_move_line.balance, 0), 1) * 100
                    END
                """)
        return None

    @_debug.perf.timed
    def action_audit_account(self):
        _debug.lifecycle("action_audit_account", records=self)
        domain = [("account_id", "in", self.ids)]
        working_file = self.env["account.return"].browse(
            self.env.context.get("working_file_id")
        )
        if working_file:
            domain += [
                ("date", ">=", working_file.date_from),
                ("date", "<=", working_file.date_to),
            ]
        return {
            **self.env["ir.actions.act_window"]._get_action_dict_by_xml_id(
                "account.action_account_moves_all"
            ),
            "domain": domain,
        }
