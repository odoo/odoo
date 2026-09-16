import logging
from datetime import date

from odoo import _, fields, models
from odoo.exceptions import UserError
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog
from odoo.tools import SQL

_logger = logging.getLogger(__name__)

_debug = DebugLog(__name__)


class AccountBankReconciliationReportHandler(models.AbstractModel):
    _name = "account.bank.reconciliation.report.handler"
    _inherit = ["account.report.custom.handler"]
    _description = "Bank Reconciliation Report Custom Handler"

    ######################
    # Options
    ######################
    @_debug.perf.timed
    def _custom_options_initializer(self, report, options, previous_options):
        super()._custom_options_initializer(
            report, options, previous_options=previous_options
        )

        # Options is needed otherwise some elements added in the post processor go on the total line
        options["ignore_totals_below_sections"] = True
        options["no_xlsx_currency_code_columns"] = True
        if (
            "active_id" in self.env.context
            and self.env.context.get("active_model") == "account.journal"
        ):
            options["bank_reconciliation_report_journal_id"] = self.env.context[
                "active_id"
            ]
        elif "bank_reconciliation_report_journal_id" in previous_options:
            options["bank_reconciliation_report_journal_id"] = previous_options[
                "bank_reconciliation_report_journal_id"
            ]
        else:
            # This should never happen except in some test cases
            options["bank_reconciliation_report_journal_id"] = (
                self.env["account.journal"].search([("type", "=", "bank")], limit=1).id
            )

        # Remove multi-currency columns if needed
        is_multi_currency = self.env.user.has_group(
            "base.group_multi_currency"
        ) and self.env.user.has_group("base.group_no_one")
        if _debug.logic.enabled:
            _debug.logic(
                "bank_reco_journal_resolved",
                report=report,
                journal=options["bank_reconciliation_report_journal_id"],
                source="context"
                if "active_id" in self.env.context
                and self.env.context.get("active_model") == "account.journal"
                else "previous_options"
                if "bank_reconciliation_report_journal_id" in previous_options
                else "first_bank_journal",
                multi_currency=is_multi_currency,
            )
        if not is_multi_currency:
            options["columns"] = [
                column
                for column in options["columns"]
                if column["expression_label"] not in ("amount_currency", "currency")
            ]

    ######################
    # Getter
    ######################
    def _get_bank_journal_and_currencies(self, options):
        journal = self.env["account.journal"].browse(
            options.get("bank_reconciliation_report_journal_id")
        )
        company_currency = journal.company_id.currency_id
        journal_currency = journal.currency_id or company_currency
        return journal, journal_currency, company_currency

    ######################
    # Return function
    ######################
    @_debug.perf.timed
    def _prepare_custom_engine_result(
        self,
        date=None,
        label=None,
        amount_currency=None,
        amount_currency_currency_id=None,
        currency=None,
        amount=0,
        amount_currency_id=None,
        has_sublines=False,
    ):
        return {
            "date": date,
            "label": label,
            "amount_currency": amount_currency,
            "amount_currency_currency_id": amount_currency_currency_id,
            "currency": currency,
            "amount": amount,
            "amount_currency_id": amount_currency_id,
            "has_sublines": has_sublines,
        }

    ######################
    # Engine
    ######################
    @_debug.perf.timed
    def _report_custom_engine_forced_currency_amount(
        self,
        expressions,
        options,
        date_scope,
        current_groupby,
        next_groupby,
        offset=0,
        limit=None,
        warnings=None,
    ):
        _journal, journal_currency, _company_currency = (
            self._get_bank_journal_and_currencies(options)
        )
        return self._prepare_custom_engine_result(
            amount_currency_id=journal_currency.id
        )

    @_debug.perf.timed
    def _report_custom_engine_unreconciled_last_statement_receipts(
        self,
        expressions,
        options,
        date_scope,
        current_groupby,
        next_groupby,
        offset=0,
        limit=None,
        warnings=None,
    ):
        return self._bank_reconciliation_report_custom_engine_common(
            options, "receipts", current_groupby, True
        )

    @_debug.perf.timed
    def _report_custom_engine_unreconciled_last_statement_payments(
        self,
        expressions,
        options,
        date_scope,
        current_groupby,
        next_groupby,
        offset=0,
        limit=None,
        warnings=None,
    ):
        return self._bank_reconciliation_report_custom_engine_common(
            options, "payments", current_groupby, True
        )

    @_debug.perf.timed
    def _report_custom_engine_unreconciled_receipts(
        self,
        expressions,
        options,
        date_scope,
        current_groupby,
        next_groupby,
        offset=0,
        limit=None,
        warnings=None,
    ):
        return self._bank_reconciliation_report_custom_engine_common(
            options, "receipts", current_groupby, False
        )

    @_debug.perf.timed
    def _report_custom_engine_unreconciled_payments(
        self,
        expressions,
        options,
        date_scope,
        current_groupby,
        next_groupby,
        offset=0,
        limit=None,
        warnings=None,
    ):
        return self._bank_reconciliation_report_custom_engine_common(
            options, "payments", current_groupby, False
        )

    @_debug.perf.timed
    def _report_custom_engine_outstanding_receipts(
        self,
        expressions,
        options,
        date_scope,
        current_groupby,
        next_groupby,
        offset=0,
        limit=None,
        warnings=None,
    ):
        return self._bank_reconciliation_report_custom_engine_outstanding_common(
            options, "receipts", current_groupby
        )

    @_debug.perf.timed
    def _report_custom_engine_outstanding_payments(
        self,
        expressions,
        options,
        date_scope,
        current_groupby,
        next_groupby,
        offset=0,
        limit=None,
        warnings=None,
    ):
        return self._bank_reconciliation_report_custom_engine_outstanding_common(
            options, "payments", current_groupby
        )

    @_debug.perf.timed
    def _report_custom_engine_misc_operations(
        self,
        expressions,
        options,
        date_scope,
        current_groupby,
        next_groupby,
        offset=0,
        limit=None,
        warnings=None,
    ):
        report = self.env["account.report"].browse(options["report_id"])
        report._check_groupby_fields([current_groupby] if current_groupby else [])

        journal, journal_currency, _company_currency = (
            self._get_bank_journal_and_currencies(options)
        )
        exchange_journal = journal.company_id.currency_exchange_journal_id

        bank_miscellaneous_domain = self._get_domain_bank_miscellaneous_move_lines(
            options, journal
        )
        bank_miscellaneous_domain = Domain.AND(
            [bank_miscellaneous_domain, [("journal_id", "!=", exchange_journal.id)]]
        )

        base_query = report._get_report_query(
            options, "strict_range", domain=bank_miscellaneous_domain or []
        )

        groupby_field_sql = (
            self.env["account.move.line"]._field_to_sql(
                "account_move_line", current_groupby, base_query
            )
            if current_groupby
            else None
        )
        query_sql = SQL(
            """
            SELECT
                %(select_from_groupby)s,
                COALESCE(SUM(COALESCE(NULLIF(account_move_line.amount_currency, 0), account_move_line.balance)), 0)
            FROM %(table_references)s
            WHERE %(search_condition)s
            %(groupby_sql)s
            """,
            select_from_groupby=groupby_field_sql,
            table_references=base_query.from_clause,
            search_condition=base_query.where_clause,
            groupby_sql=SQL("GROUP BY %s", groupby_field_sql)
            if groupby_field_sql
            else SQL(),
        )

        self.env.cr.execute(query_sql)
        query_res_lines = self.env.cr.fetchall()
        _debug.pipeline(
            "misc_operations_fetched",
            report=report,
            journal=journal,
            exchange_journal=exchange_journal,
            groupby=current_groupby,
            rows=len(query_res_lines),
        )

        if not current_groupby:
            return self._prepare_custom_engine_result(
                amount=query_res_lines[-1][1], amount_currency_id=journal_currency.id
            )
        else:
            return [
                (
                    grouping_key,
                    self._prepare_custom_engine_result(
                        amount=amount, amount_currency_id=journal_currency.id
                    ),
                )
                for grouping_key, amount in query_res_lines
            ]

    @_debug.perf.timed
    def _report_custom_engine_last_statement_balance_amount(
        self,
        expressions,
        options,
        date_scope,
        current_groupby,
        next_groupby,
        offset=0,
        limit=None,
        warnings=None,
    ):
        if current_groupby:
            raise UserError(
                _(
                    "Custom engine _report_custom_engine_last_statement_balance_amount does not support groupby"
                )
            )

        journal, journal_currency, _company_currency = (
            self._get_bank_journal_and_currencies(options)
        )
        last_statement = self._get_last_bank_statement(journal, options)

        return self._prepare_custom_engine_result(
            amount=last_statement.balance_end_real,
            amount_currency_id=journal_currency.id,
        )

    @_debug.perf.timed
    def _report_custom_engine_transaction_without_statement_amount(
        self,
        expressions,
        options,
        date_scope,
        current_groupby,
        next_groupby,
        offset=0,
        limit=None,
        warnings=None,
    ):
        return self._bank_reconciliation_report_custom_engine_common(
            options, "all", current_groupby, False, unreconciled=False
        )

    @_debug.perf.timed
    def _bank_reconciliation_report_custom_engine_common(
        self,
        options,
        internal_type,
        current_groupby,
        from_last_statement,
        unreconciled=True,
    ):
        """Retrieve the bank statement lines feeding a section of the report.

        :param dict options: the report options.
        :param str internal_type: 'receipts' keeps positive amounts, 'payments' negative ones, any other
            value ('all') keeps both.
        :param str current_groupby: the current grouping criteria.
        :param bool from_last_statement: if True, query the lines of the last statement, otherwise the
            lines not attached to any statement.
        :param bool unreconciled: if True, query the unreconciled entries only.
        """
        journal, journal_currency, _company_currency = (
            self._get_bank_journal_and_currencies(options)
        )
        _debug.logic(
            "statement_lines_engine_mode",
            report=options.get("report_id"),
            journal=journal,
            internal_type=internal_type,
            groupby=current_groupby,
            from_last_statement=from_last_statement,
            unreconciled=unreconciled,
            skipped=not journal,
        )
        if not journal:
            return self._prepare_custom_engine_result()

        report = self.env["account.report"].browse(options["report_id"])
        report._check_groupby_fields([current_groupby] if current_groupby else [])

        def prepare_result_dict(query_res_lines):
            # The query should find exactly one account move line per bank statement line
            if current_groupby == "id":
                res = query_res_lines[0]
                foreign_currency = self.env["res.currency"].browse(
                    res["foreign_currency_id"]
                )
                rate = 1  # journal_currency / foreign_currency
                if foreign_currency:
                    rate = (
                        (res["amount"] / res["amount_currency"])
                        if res["amount_currency"]
                        else 0
                    )

                return self._prepare_custom_engine_result(
                    date=res["date"] or None,
                    label=res["payment_ref"] or res["ref"] or "/",
                    amount_currency=-res["amount_residual"]
                    if res["foreign_currency_id"]
                    else None,
                    amount_currency_currency_id=foreign_currency.id
                    if res["foreign_currency_id"]
                    else None,
                    currency=foreign_currency.display_name
                    if res["foreign_currency_id"]
                    else None,
                    amount=-res["amount_residual"] * rate
                    if res["amount_residual"]
                    else None,
                    amount_currency_id=journal_currency.id,
                    has_sublines=True,
                )
            else:
                amount = 0
                for res in query_res_lines:
                    rate = 1  # journal_currency / foreign_currency
                    if res["foreign_currency_id"]:
                        rate = (
                            (res["amount"] / res["amount_currency"])
                            if res["amount_currency"]
                            else 0
                        )
                    amount += (
                        -res.get("amount_residual", 0) * rate
                        if unreconciled
                        else res.get("amount", 0)
                    )

                return self._prepare_custom_engine_result(
                    amount=amount,
                    amount_currency_id=journal_currency.id,
                    has_sublines=bool(len(query_res_lines)),
                )

        query = report._get_report_query(
            options,
            "strict_range",
            domain=[
                ("journal_id", "=", journal.id),
                (
                    "account_id",
                    "=",
                    journal.default_account_id.id,
                ),  # There should be only 1 line per move with that account
            ],
        )

        if from_last_statement:
            last_statement_id = self._get_last_bank_statement(journal, options).id
            _debug.logic(
                "last_statement_resolved",
                report=report,
                journal=journal,
                last_statement=last_statement_id,
                empty_section=not last_statement_id,
            )
            if last_statement_id:
                last_statement_id_condition = SQL(
                    "st_line.statement_id = %s", last_statement_id
                )
            else:
                # If there is no last statement, the last statement section must be empty and the other must have all
                # transaction
                return self._get_grouped_result(
                    [], current_groupby, prepare_result_dict
                )
        else:
            last_statement_id_condition = SQL("st_line.statement_id IS NULL")

        if internal_type == "receipts":
            st_line_amount_condition = SQL("AND st_line.amount > 0")
        elif internal_type == "payments":
            st_line_amount_condition = SQL("AND st_line.amount < 0")
        else:
            # For the Transaction without statement, the internal type is 'all'
            st_line_amount_condition = SQL("")

        groupby_field_sql = (
            self.env["account.move.line"]._field_to_sql(
                "account_move_line", current_groupby, query
            )
            if current_groupby
            else SQL("NULL")
        )
        # Build query
        query = SQL(
            """
           SELECT %(select_from_groupby)s,
                  st_line.id,
                  move.name,
                  move.ref,
                  move.date,
                  st_line.payment_ref,
                  st_line.amount,
                  st_line.amount_residual,
                  st_line.amount_currency,
                  st_line.foreign_currency_id
             FROM %(table_references)s
             JOIN account_bank_statement_line st_line ON st_line.move_id = account_move_line.move_id
             JOIN account_move move ON move.id = st_line.move_id
            WHERE %(search_condition)s
                  %(is_unreconciled)s
                  %(st_line_amount_condition)s
              AND %(last_statement_id_condition)s
         GROUP BY %(group_by)s,
                  st_line.id,
                  move.id
            """,
            select_from_groupby=SQL("%s AS grouping_key", groupby_field_sql),
            table_references=query.from_clause,
            search_condition=query.where_clause,
            is_receipt=SQL("st_line.amount > 0")
            if internal_type == "receipts"
            else SQL("st_line.amount < 0"),
            is_unreconciled=SQL("AND st_line.is_reconciled IS NOT TRUE")
            if unreconciled
            else SQL(""),
            st_line_amount_condition=st_line_amount_condition,
            last_statement_id_condition=last_statement_id_condition,
            group_by=groupby_field_sql
            if current_groupby
            else SQL(
                "st_line.id"
            ),  # Same key in the groupby because we can't put a null key in a group by
        )

        self.env.cr.execute(query)
        query_res_lines = self.env.cr.dictfetchall()
        _debug.pipeline(
            "statement_lines_fetched",
            report=report,
            internal_type=internal_type,
            groupby=current_groupby,
            rows=len(query_res_lines),
        )

        return self._get_grouped_result(
            query_res_lines, current_groupby, prepare_result_dict
        )

    @_debug.perf.timed
    def _bank_reconciliation_report_custom_engine_outstanding_common(
        self, options, internal_type, current_groupby
    ):
        """Retrieve the recorded payments/receipts not yet matched with a bank statement line."""
        journal, journal_currency, company_currency = (
            self._get_bank_journal_and_currencies(options)
        )
        _debug.logic(
            "outstanding_engine_mode",
            report=options.get("report_id"),
            journal=journal,
            internal_type=internal_type,
            groupby=current_groupby,
            skipped=not journal,
        )
        if not journal:
            return self._prepare_custom_engine_result()

        report = self.env["account.report"].browse(options["report_id"])
        report._check_groupby_fields([current_groupby] if current_groupby else [])

        def prepare_result_dict(query_res_lines):
            if current_groupby == "id":
                res = query_res_lines[0]
                convert = not (
                    journal_currency and res["currency_id"] == journal_currency.id
                )
                amount_currency = (
                    res["amount_residual_currency"]
                    if res["is_account_reconcile"]
                    else res["amount_currency"]
                )
                balance = (
                    res["amount_residual"]
                    if res["is_account_reconcile"]
                    else res["balance"]
                )
                foreign_currency = self.env["res.currency"].browse(res["currency_id"])

                return self._prepare_custom_engine_result(
                    date=res["date"] or None,
                    label=res["ref"] or None,
                    amount_currency=amount_currency if convert else None,
                    amount_currency_currency_id=foreign_currency.id
                    if convert
                    else None,
                    currency=foreign_currency.display_name if convert else None,
                    amount=company_currency._convert(
                        balance,
                        journal_currency,
                        journal.company_id,
                        options["date"]["date_to"],
                    )
                    if convert
                    else amount_currency,
                    amount_currency_id=journal_currency.id,
                )
            else:
                amount = 0
                for res in query_res_lines:
                    convert = not (
                        journal_currency and res["currency_id"] == journal_currency.id
                    )
                    if convert:
                        balance = (
                            res["amount_residual"]
                            if res["is_account_reconcile"]
                            else res["balance"]
                        )
                        amount += company_currency._convert(
                            balance,
                            journal_currency,
                            journal.company_id,
                            options["date"]["date_to"],
                        )
                    else:
                        amount += (
                            res["amount_residual_currency"]
                            if res["is_account_reconcile"]
                            else res["amount_currency"]
                        )

                return self._prepare_custom_engine_result(
                    amount=amount,
                    amount_currency_id=journal_currency.id,
                    has_sublines=bool(len(query_res_lines)),
                )

        accounts = (
            journal._get_journal_inbound_outstanding_payment_accounts()
            + journal._get_journal_outbound_outstanding_payment_accounts()
        )

        query = report._get_report_query(
            options,
            "from_beginning",
            domain=[
                ("journal_id", "=", journal.id),
                ("account_id", "in", accounts.ids),
                ("full_reconcile_id", "=", False),
                ("amount_residual_currency", "!=", 0.0),
            ],
        )

        # Build query
        groupby_field_sql = (
            self.env["account.move.line"]._field_to_sql(
                "account_move_line", current_groupby, query
            )
            if current_groupby
            else SQL("NULL")
        )
        query = SQL(
            """
           SELECT %(select_from_groupby)s,
                  account_move_line.account_id,
                  account_move_line.payment_id,
                  account_move_line.move_id,
                  account_move_line.currency_id,
                  account_move_line.move_name AS name,
                  account_move_line.ref,
                  account_move_line.date,
                  account.reconcile AS is_account_reconcile,
                  SUM(account_move_line.amount_residual) AS amount_residual,
                  SUM(account_move_line.balance) AS balance,
                  SUM(account_move_line.amount_residual_currency) AS amount_residual_currency,
                  SUM(account_move_line.amount_currency) AS amount_currency
             FROM %(table_references)s
             JOIN account_account account ON account.id = account_move_line.account_id
            WHERE %(search_condition)s
              AND %(is_receipt)s
         GROUP BY %(group_by)s,
                  account_move_line.account_id,
                  account_move_line.payment_id,
                  account_move_line.move_id,
                  account_move_line.currency_id,
                  account_move_line.move_name,
                  account_move_line.ref,
                  account_move_line.date,
                  account.reconcile
           """,
            select_from_groupby=SQL("%s AS grouping_key", groupby_field_sql),
            table_references=query.from_clause,
            search_condition=query.where_clause,
            is_receipt=SQL("account_move_line.balance > 0")
            if internal_type == "receipts"
            else SQL("account_move_line.balance < 0"),
            group_by=groupby_field_sql
            if current_groupby
            else SQL(
                "account_move_line.account_id"
            ),  # Same key in the groupby because we can't put a null key in a group by
        )
        self.env.cr.execute(query)
        query_res_lines = self.env.cr.dictfetchall()
        _debug.pipeline(
            "outstanding_lines_fetched",
            report=report,
            internal_type=internal_type,
            groupby=current_groupby,
            outstanding_accounts=accounts,
            rows=len(query_res_lines),
        )

        return self._get_grouped_result(
            query_res_lines, current_groupby, prepare_result_dict
        )

    def _get_grouped_result(
        self, query_res_lines, current_groupby, prepare_result_dict
    ):
        if not current_groupby:
            return prepare_result_dict(query_res_lines)
        else:
            rslt = []

            all_res_per_grouping_key = {}
            for query_res in query_res_lines:
                grouping_key = query_res["grouping_key"]
                all_res_per_grouping_key.setdefault(grouping_key, []).append(query_res)

            for grouping_key, grouped_lines in all_res_per_grouping_key.items():
                rslt.append((grouping_key, prepare_result_dict(grouped_lines)))

            return rslt

    @_debug.perf.timed
    def _custom_line_postprocessor(self, report, options, lines):
        lines = super()._custom_line_postprocessor(report, options, lines)
        journal, _journal_currency, _company_currency = (
            self._get_bank_journal_and_currencies(options)
        )
        _debug.logic(
            "bank_reco_postprocess_skipped",
            report=report,
            journal=journal,
            skipped=not journal,
        )
        if not journal:
            return lines

        last_statement = self._get_last_bank_statement(journal, options)

        for line in lines:
            line_id = report._get_res_id_from_line_id(line["id"], "account.report.line")
            code = self.env["account.report.line"].browse(line_id).code

            if code == "balance_bank":
                line["name"] = _(
                    "Balance of '%s'", journal.default_account_id.display_name
                )

            if code == "last_statement_balance":
                line["class"] = "o_bold_tr"
                if last_statement:
                    line["columns"][1].update(
                        {
                            "name": last_statement.display_name,
                            "auditable": True,
                        }
                    )

            if code == "transaction_without_statement":
                line["class"] = "o_bold_tr"

            if code == "misc_operations":
                line["class"] = "o_bold_tr"

            # Check if it's a leaf node
            model, _model_id = report._get_model_info_from_id(line["id"])
            if model == "account.move.line":
                line_name = line["name"].split()
                line["name"] = line_name[
                    0
                ]  # This will give just the name without the ref or label

        _debug.pipeline(
            "bank_reco_lines_postprocessed",
            report=report,
            journal=journal,
            lines=len(lines),
            last_statement=last_statement,
        )
        return lines

    @_debug.perf.timed
    def _customize_warnings(
        self, report, options, all_column_groups_expression_totals, warnings
    ):
        journal, journal_currency, _company_currency = (
            self._get_bank_journal_and_currencies(options)
        )
        inconsistent_statement = self._get_inconsistent_statements(options, journal).ids
        bank_miscellaneous_domain = self._get_domain_bank_miscellaneous_move_lines(
            options, journal
        )
        has_bank_miscellaneous_move_lines = bank_miscellaneous_domain and bool(
            self.env["account.move.line"].search_count(
                bank_miscellaneous_domain, limit=1
            )
        )
        (
            last_statement,
            balance_gl,
            balance_end,
            unexplained_difference,
            general_ledger_not_matching,
        ) = self._get_journal_balances(report, options, journal, journal_currency)

        _debug.logic(
            "bank_reco_warnings_inputs",
            report=report,
            journal=journal,
            inconsistent_statements=len(inconsistent_statement),
            bank_miscellaneous_move_lines=bool(has_bank_miscellaneous_move_lines),
            last_statement=last_statement,
            general_ledger_not_matching=general_ledger_not_matching,
            collect_warnings=warnings is not None,
        )
        if warnings is not None:
            if last_statement and general_ledger_not_matching:
                warnings["account.journal_balance"] = {
                    "alert_type": "warning",
                    "general_ledger_amount": balance_gl,
                    "last_bank_statement_amount": balance_end,
                    "unexplained_difference": unexplained_difference,
                }
            if inconsistent_statement:
                warnings["account.inconsistent_statement_warning"] = {
                    "alert_type": "warning",
                    "args": inconsistent_statement,
                }
            if has_bank_miscellaneous_move_lines:
                warnings["account.has_bank_miscellaneous_move_lines"] = {
                    "alert_type": "warning",
                    "args": journal.default_account_id.display_name,
                }

    @_debug.perf.timed
    def _get_journal_balances(self, report, options, journal, journal_currency):
        """Compute the formatted balances used by the 'account.journal_balance' warning.

        :param report:           The bank reconciliation report.
        :param options:          The report options.
        :param journal:          The journal used.
        :param journal_currency: The currency of the journal.
        :return:                 (last_statement, balance_gl, balance_end, difference, general_ledger_not_matching),
                                 the three balances being formatted strings.
        :rtype: tuple
        """
        # Get domain and balances
        domain = report._get_domain_options(options, "from_beginning")
        balance_gl = journal._get_journal_bank_account_balance(domain=domain)[0]
        last_statement, balance_end, difference, general_ledger_not_matching = (
            self._get_balances(options, journal, balance_gl, journal_currency)
        )
        _debug.pipeline(
            "journal_balances_computed",
            report=report,
            journal=journal,
            last_statement=last_statement,
            balance_gl=balance_gl,
            balance_end=balance_end,
            difference=difference,
            general_ledger_not_matching=general_ledger_not_matching,
        )

        # Format values
        balance_gl = report.format_value(
            options,
            balance_gl,
            format_params={"currency_id": journal_currency.id},
            figure_type="monetary",
        )
        balance_end = report.format_value(
            options,
            balance_end,
            format_params={"currency_id": journal_currency.id},
            figure_type="monetary",
        )
        difference = report.format_value(
            options,
            difference,
            format_params={"currency_id": journal_currency.id},
            figure_type="monetary",
        )

        return (
            last_statement,
            balance_gl,
            balance_end,
            difference,
            general_ledger_not_matching,
        )

    @_debug.perf.timed
    def _get_balances(self, options, journal, balance_gl, report_currency):
        """Compute the balance of the last statement and the unexplained difference.

        :param options:         The report options.
        :param journal:         The journal used.
        :param balance_gl:      The balance of the general ledger.
        :param report_currency: The currency of the report.
        :return:                (last_statement, balance_end, difference, general_ledger_not_matching).
        :rtype: tuple
        """
        report_date = fields.Date.from_string(options["date"]["date_to"])
        last_statement = self._get_last_bank_statement(journal, options)
        balance_end = 0
        difference = 0
        general_ledger_not_matching = False

        if last_statement:
            lines_before_date_to = last_statement.line_ids.filtered(
                lambda line: line.date <= report_date
            )
            balance_end = last_statement.balance_start + sum(
                lines_before_date_to.mapped("amount")
            )
            difference = balance_gl - balance_end
            general_ledger_not_matching = not report_currency.is_zero(difference)

        return last_statement, balance_end, difference, general_ledger_not_matching

    def _get_last_bank_statement(self, journal, options):
        """Retrieve the last bank statement created using this journal.

        :param journal: The journal used.
        :param options: The report options, providing the upper bound date.
        :return:        An account.bank.statement record or an empty recordset.
        """
        report_date = fields.Date.from_string(options["date"]["date_to"])
        last_statement_domain = [
            ("journal_id", "=", journal.id),
            ("statement_id", "!=", False),
            ("date", "<=", report_date),
        ]
        last_st_line = self.env["account.bank.statement.line"].search(
            last_statement_domain, order="date desc, id desc", limit=1
        )
        return last_st_line.statement_id

    def _get_inconsistent_statements(self, options, journal):
        """Retrieve the statements up to the report date whose starting balance does not match the
        ending balance of the previous statement.

        :param options: The report options.
        :param journal: The account.journal from which this report has been opened.
        :return:        An account.bank.statement recordset.
        """
        return self.env["account.bank.statement"].search(
            [
                ("journal_id", "=", journal.id),
                ("date", "<=", options["date"]["date_to"]),
                ("is_valid", "=", False),
            ]
        )

    def _get_domain_bank_miscellaneous_move_lines(self, options, journal):
        """Get the domain retrieving the journal items affecting the bank account but not linked to a
        statement line.

        :param options: The report options.
        :param journal: The account.journal from which this report has been opened.
        :return:        A domain to search on the account.move.line model, or None if the journal has no
                        default account.
        """
        if not journal.default_account_id:
            _debug.logic(
                "misc_lines_skipped", journal=journal, reason="no_default_account"
            )
            return None

        report = self.env["account.report"].browse(options["report_id"])
        domain = [
            ("account_id", "=", journal.default_account_id.id),
            ("statement_line_id", "=", False),
            *report._get_domain_options(options, "from_beginning"),
        ]

        fiscal_lock_date = journal.company_id._get_user_fiscal_lock_date(journal)
        if fiscal_lock_date != date.min:
            domain.append(("date", ">", fiscal_lock_date))

        if journal.company_id.account_opening_move_id:
            domain.append(
                ("move_id", "!=", journal.company_id.account_opening_move_id.id)
            )
        _debug.logic(
            "misc_lines_domain_restricted",
            report=report,
            journal=journal,
            after_lock_date=fiscal_lock_date != date.min,
            opening_move_excluded=bool(journal.company_id.account_opening_move_id),
        )

        return domain

    ################
    # Audit
    ################
    @_debug.perf.timed
    def action_audit_cell(self, options, params):
        _debug.lifecycle("action_audit_cell", records=self)
        report_line = self.env["account.report.line"].browse(params["report_line_id"])
        if report_line.code == "balance_bank":
            return self.action_redirect_to_general_ledger(options)
        elif report_line.code == "misc_operations":
            return self.open_bank_miscellaneous_move_lines(options)
        elif report_line.code == "last_statement_balance":
            return self.action_redirect_to_bank_statement_widget(options)
        else:
            return report_line.report_id.action_audit_cell(options, params)

    ################
    # ACTIONS
    ################
    @_debug.perf.timed
    def action_redirect_to_general_ledger(self, options):
        """Redirect to the general ledger report.

        :param options: The report options.
        :return:        An ir.actions.actions dictionary opening the general ledger.
        """
        _debug.lifecycle("action_redirect_to_general_ledger", records=self)
        general_ledger_action = self.env[
            "ir.actions.actions"
        ]._get_action_dict_by_xml_id("account.action_account_report_general_ledger")
        general_ledger_action["params"] = {
            "options": options,
            "ignore_session": True,
        }

        return general_ledger_action

    @_debug.perf.timed
    def action_redirect_to_bank_statement_widget(self, options):
        """Redirect the user to the last bank statement, if empty displays all bank transactions of the journal.

        :param options: The report options.
        :return:        A dictionary representing an ir.actions.act_window.
        """
        _debug.lifecycle("action_redirect_to_bank_statement_widget", records=self)
        journal = self.env["account.journal"].browse(
            options.get("bank_reconciliation_report_journal_id")
        )
        last_statement = self._get_last_bank_statement(journal, options)
        return self.env[
            "account.bank.statement.line"
        ]._action_view_bank_reconciliation_widget(
            default_context={
                "create": False,
                "search_default_statement_id": last_statement.id,
            },
            name=last_statement.display_name,
        )

    @_debug.perf.timed
    def open_bank_miscellaneous_move_lines(self, options):
        """Open the account.move.line list view of the items affecting the bank account balance but not
        linked to a bank statement line.

        :param options: The report options.
        :return:        An action redirecting to the list view of journal items.
        """
        _debug.lifecycle("open_bank_miscellaneous_move_lines", records=self)
        journal = self.env["account.journal"].browse(
            options["bank_reconciliation_report_journal_id"]
        )

        return {
            "name": _("Journal Items"),
            "type": "ir.actions.act_window",
            "res_model": "account.move.line",
            "view_type": "list",
            "view_mode": "list",
            "target": "current",
            "views": [(self.env.ref("account.view_account_move_line_list").id, "list")],
            "domain": self.env[
                "account.bank.reconciliation.report.handler"
            ]._get_domain_bank_miscellaneous_move_lines(options, journal),
        }

    @_debug.perf.timed
    def bank_reconciliation_report_open_inconsistent_statements(
        self, options, params=None
    ):
        """Open the account.bank.statement view, in form when a single statement is passed, in list otherwise.

        :param options: The report options.
        :param params:  The action params, whose 'args' key holds the inconsistent statement ids.
        :return:        An action redirecting to a view of statements.
        """
        inconsistent_statement_ids = params["args"]
        _debug.logic(
            "inconsistent_statements_view",
            statements=len(inconsistent_statement_ids),
            single_form=len(inconsistent_statement_ids) == 1,
        )
        action = {
            "name": _("Inconsistent Statements"),
            "type": "ir.actions.act_window",
            "res_model": "account.bank.statement",
        }
        if len(inconsistent_statement_ids) == 1:
            action.update(
                {
                    "view_mode": "form",
                    "res_id": inconsistent_statement_ids[0],
                    "views": [(False, "form")],
                }
            )
        else:
            action.update(
                {
                    "view_mode": "list",
                    "domain": [("id", "in", inconsistent_statement_ids)],
                    "views": [(False, "list")],
                }
            )
        return action
