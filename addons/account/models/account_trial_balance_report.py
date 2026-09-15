import datetime
from collections import defaultdict

from odoo import _, api, fields, models
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog
from odoo.tools import SQL, frozendict, groupby

_debug = DebugLog(__name__)


class AccountTrialBalanceReportHandler(models.AbstractModel):
    _name = "account.trial.balance.report.handler"
    _inherit = ["account.report.custom.handler"]
    _description = "Trial Balance Custom Handler"

    def _custom_options_initializer(self, report, options, previous_options):
        super()._custom_options_initializer(
            report, options, previous_options=previous_options
        )

        if options.get("comparison"):
            options["comparison"]["period_order"] = (
                "ascending"  # Make comparisons ascending (always)
            )
            options["comparison"]["hide_period_order_filter"] = True

        # Modify column headers and group structure
        column_headers, column_groups, columns = self._prepare_trial_balance_columns(
            report, options
        )

        options["column_headers"][0] = column_headers
        options["column_groups"].update(column_groups)
        options["columns"] = columns
        _debug.pipeline(
            "trial_balance_columns_built",
            report=report,
            comparison=bool(options.get("comparison")),
            column_groups=len(column_groups),
            columns=len(columns),
        )

        # CTA
        for group_vals in options["column_groups"].values():
            group_vals["forced_options"]["date"]["currency_table_period_key"] = (
                "_trial_balance_middle_periods"
            )
            if group_vals["forced_options"]["trial_balance_column_type"] in (
                "initial_balance",
                "end_balance",
            ):
                group_vals["forced_options"]["no_impact_on_currency_table"] = True

    @_debug.perf.timed
    def _prepare_trial_balance_columns(self, report, options):
        """Generate the column headers, column groups and columns of the trial balance report.

        :return: a (headers, groups, columns) tuple
        :rtype: tuple
        """
        headers = []
        groups = {}
        columns = []

        original_headers = options["column_headers"][0]
        original_columns = options["columns"]

        initial_date_from = fields.Date.to_date(
            options["column_groups"][original_columns[0]["column_group_key"]][
                "forced_options"
            ]["date"]["date_from"]
        )
        previous_fiscal_year = self.env.company.compute_fiscalyear_dates(
            initial_date_from
        )
        block_id = 0

        # Add initial balance column
        initial_date_to = initial_date_from - datetime.timedelta(days=1)
        headers, groups, columns = self._add_initial_column(
            report,
            options,
            headers,
            groups,
            columns,
            initial_date_to,
            block_id,
            previous_fiscal_year["date_from"],
        )

        last_column = {}
        nb_columns_per_header = len(original_columns) / len(original_headers)
        fiscal_year = {}

        for col_number_in_block, column in enumerate(original_columns, start=1):
            column_group_values = options["column_groups"][column["column_group_key"]]
            fiscal_year = self.env.company.compute_fiscalyear_dates(
                fields.Date.to_date(
                    column_group_values["forced_options"]["date"]["date_from"]
                )
            )

            # Check for fiscal year change
            if fiscal_year != previous_fiscal_year:
                _debug.logic(
                    "fiscal_year_block_split",
                    report=report,
                    block_id=block_id,
                    column_group=column["column_group_key"],
                    fiscal_year_start=fiscal_year["date_from"],
                )
                headers, groups, columns = self._add_end_column(
                    report,
                    options,
                    headers,
                    groups,
                    columns,
                    last_column,
                    block_id,
                    previous_fiscal_year,
                )

                block_id += 1
                initial_date_to = fields.Date.to_date(
                    column_group_values["forced_options"]["date"]["date_from"]
                ) - datetime.timedelta(days=1)
                headers, groups, columns = self._add_initial_column(
                    report,
                    options,
                    headers,
                    groups,
                    columns,
                    initial_date_to,
                    block_id,
                    fiscal_year["date_from"],
                )
                previous_fiscal_year = fiscal_year

            # Update column group
            if column["column_group_key"] != last_column.get("column_group_key"):
                column_group_values["forced_options"].update(
                    {
                        "trial_balance_column_block_id": str(block_id),
                        "trial_balance_column_type": "period",
                        "trial_balance_block_fiscalyear_start": fields.Date.to_string(
                            fiscal_year["date_from"]
                        ),
                    }
                )

            # Handle column headers
            if col_number_in_block % nb_columns_per_header == 0:
                headers.append(original_headers.pop(0))

            columns.append(column)
            last_column = column

        headers, groups, columns = self._add_end_column(
            report,
            options,
            headers,
            groups,
            columns,
            last_column,
            block_id,
            fiscal_year,
        )

        _debug.pipeline(
            "trial_balance_columns_built",
            report=report,
            original_columns=len(original_columns),
            blocks=block_id + 1,
            headers=len(headers),
            column_groups=len(groups),
            columns=len(columns),
        )
        return headers, groups, columns

    def _add_initial_column(
        self,
        report,
        options,
        headers,
        groups,
        columns,
        date_to,
        block_id,
        fiscal_year_start,
    ):
        initial_dates = report._get_dates_period(
            date_from=None, date_to=date_to, mode="single"
        )
        header, group, col = self._create_column(
            report,
            options,
            _("Initial Balance"),
            initial_dates,
            block_id,
            fiscal_year_start,
            "initial_balance",
        )
        headers.append(header)
        groups.update(group)
        columns.extend(col)
        return headers, groups, columns

    @_debug.perf.timed
    def _add_end_column(
        self,
        report,
        options,
        headers,
        groups,
        columns,
        last_column,
        block_id,
        fiscal_year,
    ):
        last_group = options["column_groups"][last_column["column_group_key"]]
        end_dates = report._get_dates_period(
            date_from=fields.Date.to_date(
                last_group["forced_options"]["date"]["date_from"]
            ),
            date_to=fields.Date.to_date(
                last_group["forced_options"]["date"]["date_to"]
            ),
            mode="range",
        )
        header, group, col = self._create_column(
            report,
            options,
            _("End Balance"),
            end_dates,
            block_id,
            fiscal_year["date_from"],
            "end_balance",
        )
        _debug.pipeline(
            "end_column_added",
            report=report,
            block_id=block_id,
            fiscal_year_start=fiscal_year["date_from"],
            new_columns=len(col),
        )
        headers.append(header)
        groups.update(group)
        columns.extend(col)
        return headers, groups, columns

    @_debug.perf.timed
    def _create_column(
        self,
        report,
        options,
        header_name,
        period_dates,
        block_id,
        fiscal_year_start,
        column_type,
    ):
        header, group, cols = self._generate_column_group(
            report,
            options,
            new_header_name=header_name,
            new_values={
                "forced_options": {
                    "date": period_dates,
                    "trial_balance_column_block_id": str(block_id),
                    "trial_balance_column_type": column_type,
                    "trial_balance_block_fiscalyear_start": fields.Date.to_string(
                        fiscal_year_start
                    ),
                },
            },
            create_single_column=self._display_single_column_for_initial_and_end_sections(
                options
            ),
        )
        return header, group, cols

    @api.model
    def _display_single_column_for_initial_and_end_sections(self, options):
        return len(options["column_headers"]) == 1

    @_debug.perf.timed
    def _generate_column_group(
        self, report, options, new_header_name, new_values, create_single_column=True
    ):
        """Generate column header, column group and columns values for a new column group.

        :param bool create_single_column: create a single 'Balance' column instead of one
                                          column per report column
        :return: a (column_header_element, column_groups, columns) tuple
        :rtype: tuple
        """
        # Used to insert the Initial Balance and End Balance columns before / after the period columns.
        default_group_vals = {
            "horizontal_groupby_element": {},
            "forced_options": {},
            **new_values,
        }

        new_column_header_element = {
            "name": new_header_name,
            "forced_options": {},
            **new_values,
        }

        if create_single_column:
            new_column_header_element["colspan"] = 1

        column_headers = [
            [new_column_header_element],
            *options["column_headers"][1:],
        ]
        new_column_group_vals = report._generate_columns_group_vals_recursively(
            column_headers, default_group_vals
        )
        new_columns, new_column_groups = report._prepare_columns_from_column_group_vals(
            new_values["forced_options"], new_column_group_vals
        )
        _debug.logic(
            "column_group_shape",
            report=report,
            column_type=new_values["forced_options"].get("trial_balance_column_type"),
            single_balance_column=create_single_column,
            generated_columns=len(new_columns),
            column_groups=len(new_column_groups),
        )

        if create_single_column:
            column_name = _("Balance")
            new_columns = [
                {
                    **new_column,
                    "name": column_name,
                    "expression_label": "balance",
                }
                for new_column in new_columns
                if new_column["expression_label"] == "debit"
            ]

        return new_column_header_element, new_column_groups, new_columns

    def _caret_options_initializer(self):
        return {
            "account.account": [
                {
                    "name": _("General Ledger"),
                    "action": "caret_option_open_general_ledger",
                },
                {"name": _("Journal Items"), "action": "open_journal_items"},
            ],
            "undistributed_profits_losses": [
                {
                    "name": _("General Ledger"),
                    "action": "caret_option_open_general_ledger",
                },
                {
                    "name": _("Journal Items"),
                    "action": "open_unallocated_items_journal_items",
                },
            ],
        }

    @_debug.perf.timed
    def open_unallocated_items_journal_items(self, options, params):
        _debug.lifecycle("open_unallocated_items_journal_items", records=self)
        report = self.env["account.report"].browse(options["report_id"])
        return report.open_unallocated_items_journal_items(options, params)

    @_debug.perf.timed
    def _report_custom_engine_trial_balance(
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

        current_groupbys = (
            [current_groupby]
            if current_groupby and not isinstance(current_groupby, list)
            else current_groupby or []
        )
        report._check_groupby_fields(current_groupbys)

        _debug.logic(
            "trial_balance_engine_mode",
            report=report,
            column_type=options["trial_balance_column_type"],
            groupbys=current_groupbys,
            next_groupby=next_groupby,
            skipped_initial_balance_amls="id" in current_groupbys
            and options["trial_balance_column_type"] == "initial_balance",
        )
        if (
            "id" in current_groupbys
            and options["trial_balance_column_type"] == "initial_balance"
        ):
            return []

        extra_domain = []
        if fiscalyear_start := options.get("trial_balance_block_fiscalyear_start"):
            extra_domain = [
                "|",
                ("account_id.include_initial_balance", "=", True),
                ("date", ">=", fiscalyear_start),
            ]

        if options.get("export_mode") == "print" and options.get("filter_search_bar"):
            if options.get("hierarchy"):
                extra_domain += [
                    "|",
                    ("account_id", "ilike", options["filter_search_bar"]),
                    (
                        "account_id",
                        "in",
                        SQL(
                            """
                        /*
                        JOIN clause: Check if the account_group include the account_account
                        A group from 10 to 10 include every account with code that begin with 10.
                        If there is an account with a length of 6, it should be included if it's in the range from 100 000 to 109 999 included

                        Where clause: Check if the account_group matches the filter
                        */
                        (SELECT distinct account_account.id
                        FROM account_account
                        LEFT JOIN account_group ON
                            (
                                LEFT(account_account.code_store->>%(company_id)s, LENGTH(code_prefix_start)) BETWEEN
                                    code_prefix_start
                                AND code_prefix_end
                            )
                        WHERE ( account_group.name->> %(lang)s  ILIKE %(filter_search_bar)s
                            OR  account_group.code_prefix_start ILIKE %(filter_search_bar)s)
                        )""",
                            lang=self.env.lang,
                            company_id=str(self.env.company.root_id.id),
                            filter_search_bar="%" + options["filter_search_bar"] + "%",
                        ),
                    ),
                ]
            else:
                extra_domain.append(
                    ("account_id", "ilike", options["filter_search_bar"])
                )

        next_groupbys = next_groupby.split(",") if next_groupby else []
        _debug.logic(
            "trial_balance_extra_domain",
            report=report,
            fiscalyear_start=fiscalyear_start,
            print_search_bar=options.get("export_mode") == "print"
            and bool(options.get("filter_search_bar")),
            hierarchy=bool(options.get("hierarchy")),
            extra_domain_leaves=len(extra_domain),
        )
        query = report._get_report_query(options, date_scope, domain=extra_domain)

        if current_groupbys:
            select_groupby_key_components = SQL("\n").join(
                SQL(
                    "%s AS %s,",
                    self.env["account.move.line"]._field_to_sql(
                        "account_move_line", groupby_key, query
                    ),
                    SQL.identifier(f"groupby_key_{groupby_key}"),
                )
                for groupby_key in current_groupbys
            )
            query.groupby = SQL(",").join(
                SQL.identifier(f"groupby_key_{groupby_key}")
                for groupby_key in current_groupbys
            )

        sql_query = SQL(
            """
            SELECT
                %(select_groupby_key_components)s
                COALESCE(SUM(%(select_balance)s), 0.0) AS balance,
                COALESCE(SUM(%(select_debit)s), 0.0) AS debit,
                COALESCE(SUM(%(select_credit)s), 0.0) AS credit
            FROM %(table_references)s
            %(currency_table_join)s
            WHERE %(search_condition)s
            %(groupby_clause)s
            """,
            select_groupby_key_components=select_groupby_key_components
            if current_groupbys
            else SQL(""),
            select_balance=report._currency_table_apply_rate(
                SQL("account_move_line.balance")
            ),
            select_debit=report._currency_table_apply_rate(
                SQL("account_move_line.debit")
            ),
            select_credit=report._currency_table_apply_rate(
                SQL("account_move_line.credit")
            ),
            table_references=query.from_clause,
            currency_table_join=report._currency_table_aml_join(options),
            search_condition=query.where_clause,
            groupby_clause=SQL("GROUP BY %s", query.groupby)
            if query.groupby
            else SQL(),
        )

        self.env.cr.execute(sql_query)
        query_results = self.env.cr.dictfetchall()
        _debug.perf.count("trial_balance_sums_fetched", rows=len(query_results))

        disable_expand = bool(
            (not next_groupby or next_groupbys[0] == "id")
            and options["trial_balance_column_type"] == "initial_balance"
        )
        _debug.pipeline(
            "trial_balance_rows_fetched",
            report=report,
            column_type=options["trial_balance_column_type"],
            groupbys=current_groupbys,
            date_scope=date_scope,
            rows=len(query_results),
            disable_expand=disable_expand,
        )

        if not current_groupbys:
            if not query_results:
                return {
                    "balance": 0.0,
                    "debit": 0.0,
                    "credit": 0.0,
                    "has_sublines": False,
                }

            query_result = query_results[0]
            query_result["has_sublines"] = True
            return query_result

        return [
            (
                (
                    query_result[f"groupby_key_{current_groupbys[0]}"]
                    if len(current_groupbys) == 1
                    else tuple(
                        query_result[f"groupby_key_{groupby}"]
                        for groupby in current_groupbys
                    )
                ),
                {**query_result, "has_sublines": not disable_expand},
            )
            for query_result in query_results
        ]

    @_debug.perf.timed
    def _custom_line_postprocessor(self, report, options, lines):
        """Compute the end balance of each column block and horizontal group from the initial
        balance and the period debits and credits of that same block and group.

        Any value already present in the end_balance column is ignored.
        """

        def get_block_and_group_key(column):
            column_group = options["column_groups"][column["column_group_key"]]
            block_id = column_group["forced_options"].get(
                "trial_balance_column_block_id"
            )
            horizontal_group = frozendict(
                column_group.get("horizontal_groupby_element", {})
            )
            analytic_group = tuple(
                column_group["forced_options"].get("analytic_accounts_list", [])
            )
            return block_id, horizontal_group, analytic_group

        # Unaffected Earnings lines
        if report._parse_line_id(lines[0]["id"])[-1] == (
            "",
            "account.report.line",
            report.line_ids[0].id,
        ):
            unaffected_earning_lines = report._get_unallocated_earnings_lines(
                options, "strict_range", auditable=True
            )
        else:
            unaffected_earning_lines = []

        if self.env.company.totals_below_sections:
            total_line_id = lines[-1]["id"]
        else:
            total_line_id = lines[0]["id"]
        _debug.logic(
            "trial_balance_total_line_located",
            report=report,
            lines=len(lines),
            unaffected_earning_lines=len(unaffected_earning_lines),
            totals_below_sections=self.env.company.totals_below_sections,
        )

        unaffected_earning_values = defaultdict(
            lambda: {
                "initial_balance": {"debit": 0, "credit": 0, "balance": 0},
                "period": {"debit": 0, "credit": 0, "balance": 0},
            }
        )

        for line in unaffected_earning_lines + lines:
            unaffected_earning_line = (
                report._get_markup(line["id"]) == "undistributed_profits_losses"
            )
            # Group by column block ID and horizontal groupby element to sum up end balance
            grouped_by_block = groupby(line["columns"], key=get_block_and_group_key)

            for _grouping_key, columns_in_block in grouped_by_block:
                columns_grouped_by_type = dict(
                    groupby(
                        columns_in_block,
                        lambda column: options["column_groups"][
                            column["column_group_key"]
                        ]["forced_options"].get("trial_balance_column_type"),
                    )
                )

                # We do a separate sum for debits and credits since we need to handle both the case where
                # there is a single Balance column (if there is no horizontal groupby) or separate Debit and
                # Credit columns in the initial balance and end balance (if there is a horizontal groupby)
                sum_debit = sum_credit = 0.0
                for col_type, cols in columns_grouped_by_type.items():
                    if col_type in ("initial_balance", "period"):
                        for col in cols:
                            if line["id"] == total_line_id:
                                col["no_format"] += unaffected_earning_values[
                                    _grouping_key
                                ][col_type][col["expression_label"]]
                                col["is_zero"] = not bool(col["no_format"])
                            if not col["is_zero"]:
                                if col["expression_label"] == "debit" or (
                                    col["expression_label"] == "balance"
                                    and col
                                    in columns_grouped_by_type["initial_balance"]
                                ):
                                    sum_debit += col["no_format"]
                                elif col["expression_label"] == "credit":
                                    sum_credit += col["no_format"]
                                if unaffected_earning_line:
                                    unaffected_earning_values[_grouping_key][col_type][
                                        col["expression_label"]
                                    ] += col["no_format"]

                for end_balance_col in columns_grouped_by_type.get("end_balance", []):
                    match end_balance_col["expression_label"]:
                        case "debit":
                            end_balance_col["no_format"] = sum_debit
                            end_balance_col["is_zero"] = not bool(sum_debit)
                        case "credit":
                            end_balance_col["no_format"] = sum_credit
                            end_balance_col["is_zero"] = not bool(sum_credit)
                        case "balance":
                            balance = sum_debit - sum_credit
                            end_balance_col["no_format"] = balance
                            end_balance_col["is_zero"] = not bool(balance)

        _debug.logic(
            "trial_balance_total_line_reordered",
            report=report,
            reordered=bool(lines) and not lines[0].get("parent_id"),
        )
        # Total line
        if lines and not lines[0].get(
            "parent_id"
        ):  # should not affect when unfolding lines
            # The same behavior is expected with or without totals_below_sections activated
            # Only the total line should be displayed at the bottom, in bold
            if self.env.company.totals_below_sections:  # total line already exists
                lines.pop(0)
                if unaffected_earning_lines:
                    total_line = lines.pop(-1)
                    lines.extend(unaffected_earning_lines)
                    lines.append(total_line)
            else:
                lines.extend(unaffected_earning_lines)
                lines.append(lines.pop(0))
                # To make the style as if totals_below_sections was activated
                lines[-1]["id"] = report._prepare_subline_id(
                    lines[-1]["id"], report._prepare_line_id([("total", None, None)])
                )
            # To make totals line not blank
            for col in lines[-1]["columns"]:
                col["blank_if_zero"] = False
            lines[-1]["name"] = _("Total")

        return lines

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
        """Override the 'account.report' method to hide move lines outside the selected period."""
        report = self.env["account.report"].browse(options["report_id"])
        _debug.logic(
            "initial_balance_amls_hidden",
            report=report,
            groupby=groupby,
            hidden=groupby == "id",
        )
        if groupby != "id":
            return report._report_expand_unfoldable_line_with_groupby(
                line_dict_id, groupby, options, progress, offset, unfold_all_batch_data
            )

        for col_group_vals in options["column_groups"].values():
            if (
                col_group_vals["forced_options"]["trial_balance_column_type"]
                == "initial_balance"
            ):
                col_group_vals["forced_domain"].append(("id", "=", False))

        return report._report_expand_unfoldable_line_with_groupby(
            line_dict_id, groupby, options, progress, offset, unfold_all_batch_data
        )

    def _get_account_ids_type_map(self, report, options):
        company_ids = report.get_report_company_ids(options)
        accounts = self.env["account.account"].search_fetch(
            [("company_ids", "in", company_ids)], ["account_type"]
        )
        return {account.id: account.account_type for account in accounts}

    def _get_fiscalyear_start_date(self, options):
        return options.get("trial_balance_block_fiscalyear_start")

    @_debug.perf.timed
    def _custom_unfold_all_batch_data_generator(
        self, report, options, lines_to_expand_by_function
    ):
        """Generate the custom engine's results for each full-sub-groupby-key that
        would be created when doing an unfold-all on the report.
        """

        def get_sub_groupby_key(report_line_id, groupbys, grouping_key):
            previous_groupbys, current_groupby = groupbys[:-1], groupbys[-1]

            sub_groupby_key = f"[{report_line_id}]"
            sub_groupby_key += ",".join(
                f"{field_name}:{value or None}"
                for (field_name, value) in zip(
                    previous_groupbys, grouping_key, strict=False
                )
            )
            sub_groupby_key += f"=>{current_groupby}"
            return sub_groupby_key

        results = {}  # In the form {full_sub_groupby_key: all_column_group_expression_totals for this groupby computation}

        for line_to_expand in lines_to_expand_by_function.get(
            "_report_expand_unfoldable_line_with_groupby", []
        ):
            report_line_id = report._get_res_id_from_line_id(
                line_to_expand["id"], "account.report.line"
            )
            report_line = self.env["account.report.line"].browse(report_line_id)

            expressions = report_line.expression_ids.filtered(
                lambda x: (
                    x.engine == "custom"
                    and x.formula == "_report_custom_engine_trial_balance"
                )
            )
            if len(expressions) != len(report_line.expression_ids):
                _debug.logic(
                    "unfold_batch_skipped",
                    report=report,
                    reason="mixed_engine_expressions",
                    report_line=report_line_id,
                )
                continue

            groupby_str = report_line._get_groupby(options)
            groupbys = groupby_str.replace(" ", "").split(",")
            next_groupby = "id"

            # Execute the query once for each groupby level. While we could optimize this further
            # (execute the query once at the deepest groupby level, and then aggregate the results in Python),
            # this ensures that the results match exactly what we would get by expanding each line.
            # But we could change that if there is a performance need.
            while groupbys:
                for (
                    column_group_key,
                    column_group_options,
                ) in report._split_options_per_column_group(options).items():
                    for date_scope, expressions_by_date_scope in groupby(
                        expressions, lambda e: e.date_scope
                    ):
                        # Get the custom engine results for the given groupby level.
                        engine_lines = self._report_custom_engine_trial_balance(
                            expressions,
                            column_group_options,
                            date_scope,
                            current_groupby=groupbys,
                            next_groupby=next_groupby,
                        )

                        # Transform the groupby key of each line into a list
                        engine_lines = [
                            (
                                grouping_key
                                if isinstance(grouping_key, tuple)
                                else (grouping_key,),
                                line_values,
                            )
                            for grouping_key, line_values in engine_lines
                        ]
                        for (
                            parent_line_grouping_key,
                            engine_lines_grouped_by_parent_line,
                        ) in groupby(engine_lines, lambda l: tuple(l[0][:-1])):
                            full_sub_groupby_key = get_sub_groupby_key(
                                report_line_id, groupbys, parent_line_grouping_key
                            )
                            results.setdefault(full_sub_groupby_key, {})
                            results[full_sub_groupby_key][column_group_key] = {
                                expression: {
                                    "value": [
                                        (
                                            grouping_key[-1],
                                            line_values[expression.subformula],
                                        )
                                        for grouping_key, line_values in engine_lines_grouped_by_parent_line
                                    ],
                                    "sublines_info": {
                                        grouping_key[-1]
                                        for grouping_key, line_values in engine_lines_grouped_by_parent_line
                                        if line_values["has_sublines"]
                                    },
                                }
                                for expression in expressions_by_date_scope
                            }
                _debug.pipeline(
                    "unfold_batch_level_computed",
                    report=report,
                    report_line=report_line_id,
                    groupby_depth=len(groupbys),
                    groupby_keys=len(results),
                )
                next_groupby = groupbys.pop()
        _debug.pipeline(
            "unfold_batch_generated",
            report=report,
            groupby_keys=len(results),
        )
        return results

    @_debug.perf.timed
    def action_audit_cell(self, options, params):
        _debug.lifecycle("action_audit_cell", records=self)
        report = self.env["account.report"].browse(options["report_id"])
        column_group_forced_options = options["column_groups"][
            params["column_group_key"]
        ]["forced_options"]

        # When generating the end balance column, we didn't specify a date in the forced_options,
        # to avoid a separate call to the custom engine (instead, the end balance is computed in
        # the custom lines postprocessor.)
        # But when auditing an end balance line, we need to retrieve moves from the beginning of time,
        # so we modify the options here just for the call to report.action_audit_cell.
        if column_group_forced_options["trial_balance_column_type"] == "end_balance":
            column_group_forced_options["date"].update(
                {
                    "mode": "single",
                    "date_from": None,
                }
            )

        action = report.action_audit_cell(options, params)

        account_id = report._get_res_id_from_line_id(
            params["calling_line_dict_id"], "account.account"
        )
        account = self.env["account.account"].browse(account_id)

        modified_domain = []
        if _debug.logic.enabled:
            _debug.logic(
                "trial_balance_audit_mode",
                report=report,
                column_type=column_group_forced_options["trial_balance_column_type"],
                account=account,
                mode="unallocated_earnings"
                if not account
                else "fiscal_year_bounded"
                if column_group_forced_options["trial_balance_column_type"]
                in ("initial_balance", "end_balance")
                and (
                    account.internal_group in ("income", "expense")
                    or account.account_type == "equity_unaffected"
                )
                else "default",
            )
        if not account:
            # list(...): this domain goes back to the client inside an
            # ir.actions.act_window, and a Domain is not JSON serialisable.
            action["domain"] = list(
                Domain(action["domain"])
                & Domain(
                    report._get_domain_unallocated_earnings_lines(
                        column_group_forced_options[
                            "trial_balance_block_fiscalyear_start"
                        ],
                        report._get_res_id_from_line_id(
                            params["calling_line_dict_id"], "res.company"
                        ),
                    )
                )
            )

        elif column_group_forced_options["trial_balance_column_type"] in (
            "initial_balance",
            "end_balance",
        ) and (
            account.internal_group in ("income", "expense")
            or account.account_type == "equity_unaffected"
        ):
            for condition in action["domain"]:
                match condition:
                    case ["account_id", "=", account_id]:
                        modified_domain.extend(
                            [
                                ("account_id", "=", account_id),
                                (
                                    "date",
                                    ">=",
                                    column_group_forced_options[
                                        "trial_balance_block_fiscalyear_start"
                                    ],
                                ),
                            ]
                        )
                    case _:
                        modified_domain.append(condition)

            action["domain"] = modified_domain
        return action
