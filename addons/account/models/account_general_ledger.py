import csv
import io
import json
from collections import defaultdict
from itertools import groupby
from textwrap import shorten

from odoo import _, fields, models
from odoo.exceptions import UserError
from odoo.libs.debug_log import DebugLog
from odoo.tools import SQL, float_repr

_debug = DebugLog(__name__)


class AccountGeneralLedgerReportHandler(models.AbstractModel):
    _name = "account.general.ledger.report.handler"
    _inherit = ["report.formula.custom.handler"]
    _description = "General Ledger Custom Handler"

    @_debug.perf.timed
    def _custom_options_initializer(self, report, options, previous_options):
        options["buttons"].append(
            {
                "name": _("CSV"),
                "sequence": 50,
                "action": "export_file",
                "action_param": "generate_csv_export",
                "file_export_type": _("CSV"),
            }
        )

        super()._custom_options_initializer(
            report, options, previous_options=previous_options
        )
        # Remove multi-currency columns if needed
        if self.env.user.has_group("base.group_multi_currency"):
            options["multi_currency"] = True
        else:
            options["columns"] = [
                column
                for column in options["columns"]
                if column["expression_label"] != "amount_currency"
            ]

        # Automatically unfold the report when printing it, unless some specific lines have been unfolded
        options["unfold_all"] = (
            options["export_mode"] == "print" and not options.get("unfolded_lines")
        ) or options["unfold_all"]

        if options.get("force_not_unfold_all"):
            options["unfold_all"] = False
        _debug.logic(
            "gl_options_resolved",
            report=report,
            multi_currency=options.get("multi_currency", False),
            export_mode=options["export_mode"],
            unfold_all=options["unfold_all"],
            force_not_unfold_all=bool(options.get("force_not_unfold_all")),
            unfolded_lines=len(options.get("unfolded_lines") or ()),
        )

        options["custom_display_config"] = {
            "templates": {
                "AccountReportLineName": "account.GeneralLedgerLineName",
            },
        }

    def _caret_options_initializer(self):
        default_caret = self.env["report.formula"]._caret_options_initializer_default()

        return {
            **default_caret,
            "id_with_accumulated_balance_caret": [
                {
                    "name": _("View Journal Entry"),
                    "action": "caret_option_open_record_form_custom_id_groupby",
                    "action_param": "move_id",
                },
            ],
            "undistributed_profits_losses": [
                {
                    "name": _("Journal Items"),
                    "action": "open_unallocated_items_journal_items",
                },
            ],
        }

    @_debug.perf.timed
    def open_unallocated_items_journal_items(self, options, params):
        _debug.lifecycle("open_unallocated_items_journal_items", records=self)
        report = self.env["report.formula"].browse(options["report_id"])
        return report.open_unallocated_items_journal_items(options, params)

    def caret_option_open_record_form_custom_id_groupby(self, options, params):
        report = self.env["report.formula"].browse(options["report_id"])
        _model, aml_key = report._get_model_info_from_id(params["line_id"])
        record_id = json.loads(aml_key)[1]

        record = self.env["account.move.line"].browse(record_id)
        target_record = (
            record[params["action_param"]] if "action_param" in params else record
        )

        view_id = report._resolve_caret_option_view(target_record)

        action = {
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "views": [
                (view_id, "form")
            ],  # view_id will be False in case the default view is needed
            "res_model": target_record._name,
            "res_id": target_record.id,
            "context": self.env.context,
        }

        if view_id is not None:
            action["view_id"] = view_id

        return action

    @_debug.perf.timed
    def _get_custom_groupby_map(self):
        def custom_label_builder(grouping_keys):
            """Batch label builder for the accumulated-balance groupby: labels journal item rows with their move line name, and balance rows with "Initial Balance"."""
            keys_names_in_sequence = {}

            ids_to_browse = []
            aml_keys = []
            for grouping_key in grouping_keys:
                if "balance_line" in grouping_key:
                    keys_names_in_sequence[grouping_key] = _("Initial Balance")
                else:
                    combined_key = json.loads(grouping_key)
                    ids_to_browse.append(combined_key[1])
                    aml_keys.append(grouping_key)

            records_unsorted = self.env["account.move.line"].browse(ids_to_browse)
            records_unsorted.fetch(["display_name"])
            for record, aml_key in zip(records_unsorted, aml_keys, strict=False):
                keys_names_in_sequence[aml_key] = shorten(
                    record.display_name, width=200
                )

            _debug.pipeline(
                "accumulated_labels_built",
                labels=len(keys_names_in_sequence),
                aml_rows=len(aml_keys),
                balance_rows=len(keys_names_in_sequence) - len(aml_keys),
            )
            return keys_names_in_sequence

        def domain_builder(grouping_key):
            if "balance_line" in grouping_key:
                return []
            grouping_key_array = json.loads(grouping_key)
            return [
                ("id", "=", grouping_key_array[1]),
                ("date", "=", grouping_key_array[0]),
            ]

        return {
            "id_with_accumulated_balance": {
                "model": None,
                "domain_builder": domain_builder,
                "caret_builder": lambda grouping_key: (
                    None
                    if "balance_line" in grouping_key
                    else "id_with_accumulated_balance_caret"
                ),
                "label_builder": custom_label_builder,
            },
        }

    @_debug.perf.timed
    def _report_custom_engine_general_ledger(
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
        def get_grouping_key(row, groupby):
            if groupby == "id_with_accumulated_balance":
                if not row["id"]:
                    return f"balance_line_{row['account_id']}"
                else:
                    return json.dumps([fields.Date.to_string(row["date"]), row["id"]])
            return row[groupby] if groupby else None

        query = self._get_query(options, current_groupby, offset=offset, limit=limit)

        rows_by_key = defaultdict(
            lambda: {
                "date": None,
                "partner_name": None,
                "amount_currency": None,
                "currency_id": self.env.company.currency_id.id,
                "debit": 0,
                "credit": 0,
                "balance": 0,
                "has_sublines": True,
            }
        )

        for row in self.env.execute_query_dict(query):
            aml_key = get_grouping_key(row, current_groupby)

            if aml_key not in rows_by_key:
                rows_by_key[aml_key].update(
                    {
                        "debit": row["debit"],
                        "credit": row["credit"],
                        "balance": row["balance"],
                    }
                )

                if current_groupby == "id_with_accumulated_balance":
                    rows_by_key[aml_key]["has_sublines"] = False
                    rows_by_key[aml_key]["account_id"] = row[
                        "account_id"
                    ]  # Needed for batching

                    if "balance_line" not in aml_key:
                        rows_by_key[aml_key]["date"] = row["date"]
                        rows_by_key[aml_key]["partner_name"] = row["partner_name"]
                        rows_by_key[aml_key]["line_name"] = row["line_name"]
                        rows_by_key[aml_key]["account_code"] = row["account_code"]
                        rows_by_key[aml_key]["account_name"] = row["account_name"]
                        rows_by_key[aml_key]["move_name"] = row["move_name"]
                    if row["currency_id"] != self.env.company.currency_id.id:
                        rows_by_key[aml_key]["amount_currency"] = row["amount_currency"]
                        rows_by_key[aml_key]["currency_id"] = row["currency_id"]
                elif current_groupby == "account_id":
                    rows_by_key[aml_key]["has_sublines"] = True
                    if row.get("currency_id"):
                        rows_by_key[aml_key]["amount_currency"] = row["amount_currency"]
                        rows_by_key[aml_key]["currency_id"] = row["currency_id"]
            else:
                rows_by_key[aml_key]["debit"] += row["debit"]
                rows_by_key[aml_key]["credit"] += row["credit"]
                rows_by_key[aml_key]["balance"] += row["balance"]
                if row.get("currency_id"):
                    rows_by_key[aml_key]["currency_id"] += row["currency_id"]

        _debug.pipeline(
            "gl_engine_rows_grouped",
            report=options.get("report_id"),
            groupby=current_groupby,
            next_groupby=next_groupby,
            keys=len(rows_by_key),
            offset=offset,
            limit=limit,
            aggregated=not current_groupby,
        )
        if not current_groupby:
            return rows_by_key[
                None
            ]  # None is the key for total line as there is no groupby

        return [(key, entry) for key, entry in rows_by_key.items()]

    @_debug.perf.timed
    def _get_query(
        self, options, current_groupby, order_by_account=False, offset=0, limit=None
    ):
        report = self.env["report.formula"].browse(options["report_id"])
        options_date_from = fields.Date.from_string(options["date"]["date_from"])
        current_fiscalyear_date_from = self.env.company.compute_fiscalyear_dates(
            options_date_from
        )["date_from"]

        # We want to exclude move lines from expense and income accounts before the fiscal year for every groupby under account_id
        additional_domain = [
            "|",
            ("account_id.include_initial_balance", "=", True),
            ("date", ">=", current_fiscalyear_date_from),
        ]

        report_query = report._get_report_query(
            options, "from_beginning", additional_domain
        )

        if (
            options.get("export_mode") == "print"
            and options.get("filter_search_bar")
            and current_groupby not in ("id_with_accumulated_balance", "id")
        ):
            search_bar_sql = SQL(
                """
                AND account_move_line.account_id = ANY(%(search_bar_account_query)s)
                """,
                search_bar_account_query=self.env["account.account"]
                ._search(
                    [
                        ("display_name", "ilike", options.get("filter_search_bar")),
                        *self.env["account.account"]._check_company_domain(
                            self.env["report.formula"].get_report_company_ids(options)
                        ),
                    ]
                )
                .select(SQL.identifier("id")),
            )
        else:
            search_bar_sql = SQL()

        additional_select = SQL("")
        groupby = []
        if current_groupby == "id_with_accumulated_balance":
            account_code_select = self.env["account.account"]._field_to_sql(
                "account_move_line__account_id", "code", report_query
            )
            account_name_select = self.env["account.account"]._field_to_sql(
                "account_move_line__account_id", "name"
            )
            additional_select = SQL(
                """
                CASE
                    WHEN account_move_line.date >= %(date)s THEN account_move_line.id
                    ELSE NULL
                END AS id,
                CASE
                    WHEN account_move_line.date >= %(date)s THEN account_move_line.date
                    ELSE NULL
                END AS date,
                MIN(move.name) AS move_name,

                SUM(account_move_line.amount_currency) AS amount_currency,
                MIN(partner.name) AS partner_name,
                MIN(account_move_line.currency_id) AS currency_id,
                MIN(account_move_line__account_id.id) AS account_id,

                MIN(account_move_line.name) AS line_name,
                MIN(%(account_name_select)s) AS account_name,
                MIN(%(account_code_select)s) AS account_code,
                """,
                date=fields.Date.from_string(options["date"]["date_from"]),
                account_name_select=account_name_select,
                account_code_select=account_code_select,
            )
            groupby = [SQL("1"), SQL("2"), SQL("account_move_line.account_id")]
        elif current_groupby == "account_id":
            additional_select = SQL("""
                account_move_line__account_id.id AS account_id,
                account_move_line__account_id.account_type AS account_type,
                SUM(account_move_line.amount_currency) AS amount_currency,
                account_move_line__account_id.currency_id AS currency_id,
            """)
            groupby = [
                SQL("account_move_line__account_id.id"),
                SQL("account_move_line__account_id.currency_id"),
            ]
        elif current_groupby:
            groupby_field_sql = self.env["account.move.line"]._field_to_sql(
                "account_move_line", current_groupby, report_query
            )
            additional_select = SQL(
                "%s AS %s,", groupby_field_sql, SQL.identifier(current_groupby)
            )
            groupby = [groupby_field_sql]

        report_query.left_join(
            "account_move_line", "account_id", "account_account", "id", "account_id"
        )
        if current_groupby == "account_id" or order_by_account:
            # psycopg3 renumbers the params of a reused SQL object across GROUP BY
            # and ORDER BY, so the same account-order expression is not recognized
            # as identical and PG rejects it (GroupingError). Emit it once, only in
            # ORDER BY, wrapped in ANY_VALUE(): accounts are grouped by their PK so
            # the ordering value is deterministic per group. Same idiom as the ORM's
            # _read_group_orderby.
            report_query._any_value_orderby = True
            try:
                order_clause = [
                    self.env["account.account"]._order_to_sql(
                        self.env["account.account"]._order,
                        report_query,
                        "account_move_line__account_id",
                    )
                ]
            finally:
                report_query._any_value_orderby = False
        else:
            order_clause = []
        if current_groupby == "id_with_accumulated_balance":
            order_clause.append(SQL("2 NULLS FIRST, move_name, 1 NULLS FIRST"))
        _debug.logic(
            "gl_query_built",
            report=report,
            groupby=current_groupby,
            groupby_columns=len(groupby),
            order_by_account=order_by_account,
            order_clauses=len(order_clause),
            search_bar_restricted=options.get("export_mode") == "print"
            and bool(options.get("filter_search_bar"))
            and current_groupby not in ("id_with_accumulated_balance", "id"),
            fiscalyear_date_from=current_fiscalyear_date_from,
            offset=offset,
            limit=limit,
        )

        return SQL(
            """
            SELECT
                %(additional_select)s
                COALESCE(SUM(%(select_debit)s), 0.0) AS debit,
                COALESCE(SUM(%(select_credit)s), 0.0) AS credit,
                COALESCE(SUM(%(select_balance)s), 0.0) AS balance
            FROM %(from_clause)s

            LEFT JOIN res_partner partner ON partner.id = account_move_line.partner_id
            JOIN account_move move ON move.id = account_move_line.move_id
            %(currency_table_join)s

            WHERE %(where_clause)s
            %(search_bar_sql)s

            %(additional_groupby)s
            %(orderby_clause)s

            %(offset_clause)s
            LIMIT %(limit)s
            """,
            additional_select=additional_select,
            select_balance=report._currency_table_apply_rate(
                SQL("account_move_line.balance")
            ),
            select_debit=report._currency_table_apply_rate(
                SQL("account_move_line.debit")
            ),
            select_credit=report._currency_table_apply_rate(
                SQL("account_move_line.credit")
            ),
            from_clause=report_query.from_clause,
            currency_table_join=report._currency_table_aml_join(options),
            where_clause=report_query.where_clause,
            search_bar_sql=search_bar_sql,
            additional_groupby=SQL("GROUP BY %s", SQL(",").join(groupby))
            if groupby
            else SQL(),
            orderby_clause=SQL("ORDER BY %s", SQL(",").join(order_clause))
            if order_clause
            else SQL(),
            offset_clause=SQL("OFFSET %s", offset) if offset else SQL(),
            limit=limit,
        )

    @_debug.perf.timed
    def _report_expand_unfoldable_line_with_groupby(
        self,
        line_dict_id,
        groupby,
        options,
        progress,
        offset,
        unfold_all_batch_data=None,
    ):
        """Shadow report.formula's expansion to use progress when computing the accumulated balance, so the
        'id_with_accumulated_balance' groupby supports partial expand.
        """
        report = self.env["report.formula"].browse(options["report_id"])
        result = report._report_expand_unfoldable_line_with_groupby(
            line_dict_id, groupby, options, progress, offset, unfold_all_batch_data
        )
        _debug.logic(
            "expand_accumulated_balance",
            report=report,
            groupby=groupby,
            accumulate=groupby == "id_with_accumulated_balance",
            offset=offset,
            batched=unfold_all_batch_data is not None,
        )
        if groupby != "id_with_accumulated_balance":
            return result

        colname_to_idx = defaultdict(dict)
        for idx, col in enumerate(options.get("columns", [])):
            colname_to_idx[col["column_group_key"]][col["expression_label"]] = idx

        if options["export_mode"] is None:
            limit_to_load = report.load_more_limit or None
        else:
            limit_to_load = None
            offset = 0

        processed_lines = result["lines"]

        has_balance_line = False
        col_group_keys = options["column_groups"]
        accumulated_balance_by_colgroup = progress.get(
            "accumulated_balance_by_colgroup", dict.fromkeys(col_group_keys, 0.0)
        )
        for col_group_key in col_group_keys:
            if "balance" not in colname_to_idx[col_group_key]:
                continue
            for line in processed_lines:
                line_balance = line["columns"][
                    colname_to_idx[col_group_key]["balance"]
                ]["no_format"]
                accumulated_balance_by_colgroup[col_group_key] += line_balance
                if line["name"] == "balance_line":
                    has_balance_line = True
                    line["name"] = _("Initial Balance")
                else:
                    line["columns"][colname_to_idx[col_group_key]["balance"]] = (
                        report._prepare_column_dict(
                            accumulated_balance_by_colgroup[col_group_key],
                            line["columns"][colname_to_idx[col_group_key]["balance"]],
                            options,
                        )
                    )

        _debug.pipeline(
            "accumulated_balance_applied",
            report=report,
            lines=len(processed_lines),
            has_balance_line=has_balance_line,
            limit_to_load=limit_to_load,
            export_mode=options["export_mode"],
            column_groups=len(col_group_keys),
        )
        return {
            **result,
            "lines": processed_lines,
            "offset_increment": limit_to_load - 1
            if has_balance_line and limit_to_load
            else len(processed_lines),
            "progress": {
                **progress,
                "accumulated_balance_by_colgroup": accumulated_balance_by_colgroup,
            },
        }

    def _get_fiscalyear_start_date(self, options):
        options_date_from = fields.Date.to_date(options["date"]["date_from"])
        return self.env.company.compute_fiscalyear_dates(options_date_from)["date_from"]

    def _adjust_total_with_unaffected_earnings(
        self, total_line_columns, unaffected_earning_values
    ):
        for col in total_line_columns:
            if col and col["expression_label"] in unaffected_earning_values:
                col["no_format"] += unaffected_earning_values[col["expression_label"]]
                col["is_zero"] = not bool(col["no_format"])
        return total_line_columns

    @_debug.perf.timed
    def _custom_line_postprocessor(self, report, options, lines):
        """Append the unallocated earnings lines, attach the chatter to journal item lines and move the total
        line to the bottom, as it must always be last in the general ledger.
        """
        general_ledger_custom_engine_line = self.env.ref(
            "account.general_ledger_custom_engine_line"
        )
        processed_lines = []
        main_line_dict = None
        account_move_lines = []
        unaffected_earning_values = defaultdict(float)

        # Get the unaffected earning lines if the whole report has been generated
        # (e.g., not when loading more lines in a group)
        if report._parse_line_id(lines[0]["id"])[-1] == (
            "",
            "report.formula.line",
            report.line_ids[0].id,
        ):
            unaffected_earning_lines = report._get_unallocated_earnings_lines(
                options, "from_beginning"
            )
        else:
            unaffected_earning_lines = []
        _debug.logic(
            "unallocated_earnings_resolved",
            report=report,
            lines=len(lines),
            unaffected_earning_lines=len(unaffected_earning_lines),
        )

        for line in lines + unaffected_earning_lines:
            markup, model, res_id = report._parse_line_id(line["id"])[-1]
            if (
                model == "report.formula.line"
                and res_id == general_ledger_custom_engine_line.id
            ):
                main_line_dict = line
            elif markup == "undistributed_profits_losses":
                for column in line["columns"]:
                    # Swap no_format from 0.0 to None for unaffected lines, to match the other lines
                    if (
                        column["expression_label"] == "amount_currency"
                        and column["is_zero"]
                    ):
                        column["no_format"] = None
                    elif column["figure_type"] == "monetary":
                        unaffected_earning_values[column["expression_label"]] += column[
                            "no_format"
                        ]
            else:
                processed_lines.append(line)

            if (
                model is None
                and markup == {"groupby": "id_with_accumulated_balance"}
                and not res_id.startswith("balance_line_")
                and options.get("export_mode") != "file"
            ):
                line["chatter"] = {"id": json.loads(res_id)[1]}
                account_move_lines.append(line)

        _debug.pipeline(
            "gl_lines_classified",
            report=report,
            processed_lines=len(processed_lines),
            main_line=main_line_dict is not None,
            chatter_lines=len(account_move_lines),
        )
        if account_move_lines:
            line_ids = (line["chatter"]["id"] for line in account_move_lines)
            # load=False keeps move_id a bare id -- same reasoning as the
            # chatter map in account_report_ledger.py.
            account_moves = {
                line["id"]: line["move_id"]
                for line in self.env["account.move.line"]
                .browse(line_ids)
                .read(["id", "move_id"], load=False)
            }
            for line in account_move_lines:
                line["chatter"]["id"] = account_moves[line["chatter"]["id"]]
                line["chatter"]["model"] = "account.move"

        if self.env.company.account_config_id.totals_below_sections and not options.get(
            "ignore_totals_below_sections"
        ):
            _debug.logic(
                "totals_below_sections_kept",
                report=report,
                unaffected_earning_lines=len(unaffected_earning_lines),
            )
            if unaffected_earning_lines:
                total_line = processed_lines.pop(-1)
                total_line["columns"] = self._adjust_total_with_unaffected_earnings(
                    total_line["columns"], unaffected_earning_values
                )
                processed_lines.extend(unaffected_earning_lines)
                processed_lines.append(total_line)
            return processed_lines

        processed_lines.extend(unaffected_earning_lines)
        _debug.logic(
            "total_line_appended",
            report=report,
            main_line=main_line_dict is not None,
        )
        if main_line_dict:
            processed_lines.append(
                {
                    "id": report._get_generic_line_id(None, None, "total"),
                    "name": _("Total General Ledger"),
                    "columns": self._adjust_total_with_unaffected_earnings(
                        main_line_dict["columns"], unaffected_earning_values
                    ),
                    "level": 1,
                }
            )

        return processed_lines

    @_debug.perf.timed
    def _custom_unfold_all_batch_data_generator(
        self, report, options, lines_to_expand_by_function
    ):
        """Generate the custom engine's results for each full-sub-groupby-key that
        would be created when doing an unfold-all on the report.
        """

        results = {}  # In the form {full_sub_groupby_key: all_column_group_expression_totals for this groupby computation}

        for line_to_expand in lines_to_expand_by_function.get(
            "_report_expand_unfoldable_line_with_groupby", []
        ):
            report_line_id = report._get_res_id_from_line_id(
                line_to_expand["id"], "report.formula.line"
            )
            report_line = self.env["report.formula.line"].browse(report_line_id)

            expressions = report_line.expression_ids.filtered(
                lambda x: (
                    x.engine == "custom"
                    and x.formula == "_report_custom_engine_general_ledger"
                )
            )
            if not expressions:
                _debug.logic(
                    "unfold_batch_skipped",
                    report=report,
                    reason="no_gl_custom_expressions",
                    report_line=report_line_id,
                )
                continue

            for (
                column_group_key,
                column_group_options,
            ) in report._split_options_per_column_group(options).items():
                for date_scope, expressions_by_date_scope in groupby(
                    expressions, lambda e: e.date_scope
                ):
                    expressions_by_date_scope = list(expressions_by_date_scope)
                    # Get the custom engine results for the given groupby level.
                    engine_account_lines = self._report_custom_engine_general_ledger(
                        expressions_by_date_scope,
                        column_group_options,
                        date_scope,
                        "account_id",
                        "id_with_accumulated_balance",
                    )
                    account_expression_totals = results.setdefault(
                        f"[{report_line_id}]=>account_id", {}
                    ).setdefault(
                        column_group_key,
                        {
                            expression: {"value": [], "sublines_info": set()}
                            for expression in expressions_by_date_scope
                        },
                    )
                    for account_id, engine_account_result_dict in engine_account_lines:
                        for expression in expressions_by_date_scope:
                            account_expression_totals[expression]["value"].append(
                                (
                                    account_id,
                                    engine_account_result_dict[expression.subformula],
                                )
                            )
                            if engine_account_result_dict["has_sublines"]:
                                account_expression_totals[expression][
                                    "sublines_info"
                                ].add(account_id)

                    engine_aml_lines = self._report_custom_engine_general_ledger(
                        expressions_by_date_scope,
                        column_group_options,
                        date_scope,
                        "id_with_accumulated_balance",
                        None,
                    )
                    aml_data_by_account = {}
                    for grouping_key, engine_result_dict in engine_aml_lines:
                        engine_result_dict["grouping_key"] = grouping_key
                        aml_data_by_account.setdefault(
                            engine_result_dict["account_id"], []
                        ).append(engine_result_dict)

                    _debug.pipeline(
                        "unfold_batch_engine_results",
                        report=report,
                        report_line=report_line_id,
                        column_group=column_group_key,
                        date_scope=date_scope,
                        account_rows=len(engine_account_lines),
                        aml_rows=len(engine_aml_lines),
                        accounts_with_amls=len(aml_data_by_account),
                    )
                    for account_id, engine_result_list in aml_data_by_account.items():
                        account_aml_expression_totals = results.setdefault(
                            f"[{report_line_id}]account_id:{account_id}=>id_with_accumulated_balance",
                            {},
                        ).setdefault(
                            column_group_key,
                            {
                                expression: {"value": [], "sublines_info": set()}
                                for expression in expressions_by_date_scope
                            },
                        )
                        for engine_result_dict in engine_result_list:
                            for expression in expressions_by_date_scope:
                                account_aml_expression_totals[expression][
                                    "value"
                                ].append(
                                    (
                                        engine_result_dict["grouping_key"],
                                        engine_result_dict[expression.subformula],
                                    )
                                )

        _debug.pipeline(
            "unfold_batch_generated",
            report=report,
            lines_to_expand=len(
                lines_to_expand_by_function.get(
                    "_report_expand_unfoldable_line_with_groupby", []
                )
            ),
            groupby_keys=len(results),
        )
        return results

    def generate_csv_export(self, options):
        if len(options["column_groups"]) > 1:
            raise UserError(_("CSV export only works with one column group"))

        report = self.env["report.formula"].browse(options["report_id"])
        return {
            "file_content": self._generate_csv_lazy_export(options),
            "file_type": "csv",
            "file_name": report.get_default_report_filename(options, "csv"),
        }

    def _generate_csv_lazy_export(self, options):
        with self.pool.cursor() as new_cr:
            self.env.flush_all()
            handler = self.with_env(self.env(cr=new_cr))
            cur_data = {
                currency.id: {
                    "name": currency.name,
                    "decimal_places": currency.decimal_places,
                }
                for currency in handler.env["res.currency"]
                .with_context(active_test=False)
                .search([])
            }
            company_currency_id = handler.env.company.currency_id.id

            def csv_format_account_line(account_line, has_code=True):
                if has_code:
                    cells = list(
                        handler.env["account.account"]._split_code_name(
                            account_line["name"]
                        )
                    )
                else:
                    cells = ["/", account_line["name"]]

                for col in account_line["columns"]:
                    cell = col["name"]
                    currency_id = (
                        col["currency"].id
                        if col.get("currency")
                        else company_currency_id
                    )

                    if col["figure_type"] == "monetary" and isinstance(cell, float):
                        cell = float_repr(cell, cur_data[currency_id]["decimal_places"])

                    if col["expression_label"] == "amount_currency":
                        cells.append(cell)
                        cell = (
                            cur_data[currency_id]["name"]
                            if currency_id != company_currency_id
                            else ""
                        )

                    cells.append(cell)

                return csv_format(cells)

            def csv_format_aml_res(aml_res):
                cells = ["", aml_res.get("move_name", "")]
                for col in options["columns"]:
                    cell = aml_res.get(col["expression_label"], "")

                    if col["figure_type"] == "monetary" and isinstance(cell, float):
                        if col["expression_label"] == "amount_currency":
                            currency_id = aml_res["currency_id"]
                            amount_cur_cell = (
                                float_repr(
                                    cell, cur_data[currency_id]["decimal_places"]
                                )
                                if currency_id != company_currency_id
                                else ""
                            )
                            cells.append(amount_cur_cell)
                            cell = (
                                cur_data[currency_id]["name"]
                                if currency_id != company_currency_id
                                else ""
                            )
                        else:
                            cell = float_repr(
                                cell, cur_data[company_currency_id]["decimal_places"]
                            )
                    cells.append(cell)

                return csv_format(cells)

            def csv_format(cells):
                with io.StringIO() as buf:
                    writer = csv.writer(buf, delimiter=",", lineterminator="\n")
                    writer.writerow(cells)
                    return buf.getvalue().encode()

            col_names = [col["name"] for col in options["columns"]]
            currency_idx = next(
                (
                    i
                    for i, col in enumerate(options["columns"])
                    if col.get("expression_label") == "amount_currency"
                ),
                None,
            )
            header = [_("Code"), _("Name")]

            if currency_idx is not None:
                header += [
                    *col_names[:currency_idx],
                    _("Amount Currency"),
                    _("Currency"),
                    *col_names[currency_idx + 1 :],
                ]
            else:
                header += col_names
            _debug.logic(
                "csv_header_built",
                report=options.get("report_id"),
                columns=len(col_names),
                amount_currency_column=currency_idx is not None,
                currencies=len(cur_data),
            )

            yield csv_format(header)

            report = handler.env["report.formula"].browse(options["report_id"])
            agg_lines_options = report.get_options(
                previous_options={
                    **options,
                    "unfolded_lines": [],
                    "force_not_unfold_all": True,
                }
            )
            agg_lines = report.with_context(no_format=True)._get_lines(
                agg_lines_options
            )

            # Exclude total lines
            account_lines = []
            accounts = []
            for agg_line in agg_lines:
                line_id = agg_line["id"]
                markup, model, res_id = report._parse_line_id(line_id)[-1]
                if markup != "total":
                    if model == "account.account":
                        accounts.append(res_id)
                    account_lines.append(agg_line)

            _debug.pipeline(
                "csv_account_lines_collected",
                report=report,
                agg_lines=len(agg_lines),
                account_lines=len(account_lines),
                accounts=len(accounts),
                skipped=not account_lines,
            )
            if not account_lines:
                return

            accounts_with_codes = {
                account.id
                for account in handler.env["account.account"].browse(accounts)
                if account.code
            }

            account_lines_iter = iter(account_lines)
            account_line = next(account_lines_iter)
            _model, account_id = report._get_model_info_from_id(account_line["id"])
            yield csv_format_account_line(
                account_line, has_code=account_id in accounts_with_codes
            )

            aml_query = handler._get_query(
                options, "id_with_accumulated_balance", order_by_account=True
            )
            _debug.pipeline(
                "csv_aml_stream_started",
                report=report,
                accounts_with_codes=len(accounts_with_codes),
            )

            handler.env.cr.execute(SQL("%s", aml_query))
            _debug.perf.count("csv_aml_rows_fetched", rows=handler.env.cr.rowcount)
            progress = 0
            while aml_line := handler.env.cr.dictfetchone():
                while account_id != aml_line["account_id"]:
                    account_line = next(account_lines_iter)
                    _model, account_id = report._get_model_info_from_id(
                        account_line["id"]
                    )
                    yield csv_format_account_line(
                        account_line, has_code=account_id in accounts_with_codes
                    )
                    progress = 0

                if aml_line["id"] is None:
                    aml_line["move_name"] = _("Initial Balance")
                    aml_line["partner_name"] = ""

                progress = aml_line["balance"] = progress + aml_line["balance"]
                yield csv_format_aml_res(aml_line)

            # These are the "Result Brought Forward" lines
            for account_line in account_lines_iter:
                yield csv_format_account_line(account_line, has_code=False)

            total_line = agg_lines[-1]
            yield csv_format_account_line(total_line)
