from collections import defaultdict

from odoo import _, api, models
from odoo.exceptions import UserError
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog
from odoo.tools import SQL

_debug = DebugLog(__name__)


class AccountTaxReportHandler(models.AbstractModel):
    _name = "account.tax.report.handler"
    _inherit = ["account.report.custom.handler"]
    _description = "Account Report Handler for Tax Reports"

    @_debug.perf.timed
    def _customize_warnings(
        self, report, options, all_column_groups_expression_totals, warnings
    ):
        if "account.common_warning_draft_in_period" in warnings:
            # Recompute the warning 'common_warning_draft_in_period' to not include tax closing entries in the banner of unposted moves
            if not self.env["account.move"].search_count(
                [
                    ("state", "=", "draft"),
                    ("date", "<=", options["date"]["date_to"]),
                    ("closing_return_id", "=", False),
                ],
                limit=1,
            ):
                warnings.pop("account.common_warning_draft_in_period")

        # Chek the use of inactive tags in the period
        query = report._get_report_query(options, "strict_range")
        rows = self.env.execute_query(
            SQL(
                """
            SELECT 1
            FROM %s
            JOIN account_account_tag_account_move_line_rel aml_tag
                ON account_move_line.id = aml_tag.account_move_line_id
            JOIN account_account_tag tag
                ON aml_tag.account_account_tag_id = tag.id
            WHERE %s
            AND NOT tag.active
            LIMIT 1
        """,
                query.from_clause,
                query.where_clause,
            )
        )
        if rows:
            warnings["account.tax_report_warning_inactive_tags"] = {}
        _debug.logic(
            "tax_warnings_resolved",
            report=report,
            draft_in_period="account.common_warning_draft_in_period" in warnings,
            inactive_tags=bool(rows),
        )

    def _get_domain_amls_with_archived_tags(self, options):
        domain = [
            ("tax_tag_ids.active", "=", False),
            ("parent_state", "=", "posted"),
            ("date", ">=", options["date"]["date_from"]),
        ]
        if options["date"]["mode"] == "single":
            domain.append(("date", "<=", options["date"]["date_to"]))
        return domain

    @_debug.perf.timed
    def action_view_amls_with_archived_tags(self, options, params=None):
        _debug.lifecycle("action_view_amls_with_archived_tags", records=self)
        return {
            "name": _("Journal items with archived tax tags"),
            "type": "ir.actions.act_window",
            "res_model": "account.move.line",
            "domain": self._get_domain_amls_with_archived_tags(options),
            "context": {"active_test": False},
            "views": [(self.env.ref("account.view_archived_tag_move_tree").id, "list")],
        }


class AccountGenericTaxReportHandler(models.AbstractModel):
    _name = "account.generic.tax.report.handler"
    _inherit = ["account.tax.report.handler"]
    _description = "Generic Tax Report Custom Handler"

    def _custom_options_initializer(self, report, options, previous_options):
        super()._custom_options_initializer(report, options, previous_options)

        options["custom_display_config"] = {
            "css_custom_class": "generic_tax_report",
            "templates": {
                "AccountReportLineName": "account.TaxReportLineName",
            },
        }

    def _dynamic_lines_generator(
        self, report, options, all_column_groups_expression_totals, warnings=None
    ):
        return self._get_dynamic_lines(report, options, "default", warnings)

    def _caret_options_initializer(self):
        return {
            "generic_tax_report": [
                {"name": _("Audit"), "action": "caret_option_audit_tax"},
            ]
        }

    @_debug.perf.timed
    def _get_dynamic_lines(self, report, options, grouping, warnings=None):
        """Compute the report lines for the generic tax report.

        :param report:      The account.report record being rendered.
        :param options:     The report options.
        :param str grouping: The requested grouping ('tax_account', 'account_tax' or none).
        :param warnings:    The warnings dictionary to fill, if any.
        :return:            A list of lines, each one being a python dictionary.
        :rtype:             list
        """
        options_by_column_group = report._split_options_per_column_group(options)

        # Compute tax_base_amount / tax_amount for each selected groupby.
        if grouping == "tax_account":
            groupby_fields = [
                ("src_tax", "type_tax_use"),
                ("src_tax", "id"),
                ("account", "id"),
            ]
            comodels = [None, "account.tax", "account.account"]
        elif grouping == "account_tax":
            groupby_fields = [
                ("src_tax", "type_tax_use"),
                ("account", "id"),
                ("src_tax", "id"),
            ]
            comodels = [None, "account.account", "account.tax"]
        else:
            groupby_fields = [("src_tax", "type_tax_use"), ("src_tax", "id")]
            comodels = [None, "account.tax"]
        _debug.logic(
            "tax_grouping_chosen",
            report=report,
            grouping=grouping,
            levels=len(groupby_fields),
            tax_details_engine=grouping in ("tax_account", "account_tax"),
            column_groups=len(options_by_column_group),
        )

        if grouping in ("tax_account", "account_tax"):
            tax_amount_hierarchy = self._read_generic_tax_report_amounts(
                report, options_by_column_group, groupby_fields
            )
        else:
            tax_amount_hierarchy = self._read_generic_tax_report_amounts_no_tax_details(
                report, options, options_by_column_group
            )

        # Fetch involved records in order to ensure all lines are sorted according the comodel order.
        # To do so, we compute 'sorting_map_list' allowing to retrieve each record by id and the order
        # to be used.
        record_ids_gb = [set() for dummy in groupby_fields]

        def update_record_ids_gb_recursively(node, level=0):
            for k, v in node.items():
                if k:
                    record_ids_gb[level].add(k)
                    if v.get("children"):
                        update_record_ids_gb_recursively(v["children"], level=level + 1)

        update_record_ids_gb_recursively(tax_amount_hierarchy)
        if _debug.pipeline.enabled:
            _debug.pipeline(
                "tax_hierarchy_read",
                report=report,
                grouping=grouping,
                records_per_level=[len(ids) for ids in record_ids_gb],
            )

        sorting_map_list = []
        for i, comodel in enumerate(comodels):
            if comodel:
                # Relational records.
                records = (
                    self.env[comodel]
                    .with_context(active_test=False)
                    .search([("id", "in", tuple(record_ids_gb[i]))])  # noqa: E8507  one search per comodel, and each iteration is a different model
                )
                sorting_map = {r.id: (r, j) for j, r in enumerate(records)}
                sorting_map_list.append(sorting_map)
            else:
                # src_tax_type_tax_use.
                selection = (
                    self.env["account.tax"]
                    ._fields["type_tax_use"]
                    ._description_selection(self.env)
                )
                sorting_map_list.append(
                    {
                        v[0]: (v, j)
                        for j, v in enumerate(selection)
                        if v[0] in record_ids_gb[i]
                    }
                )

        # Compute report lines.
        lines = []
        self._update_lines_recursively(
            report,
            options,
            lines,
            sorting_map_list,
            groupby_fields,
            tax_amount_hierarchy,
            warnings=warnings,
        )
        _debug.pipeline(
            "tax_dynamic_lines_built",
            report=report,
            grouping=grouping,
            lines=len(lines),
        )
        return lines

    # -------------------------------------------------------------------------
    # GENERIC TAX REPORT COMPUTATION (DYNAMIC LINES)
    # -------------------------------------------------------------------------

    @api.model
    @_debug.perf.timed
    def _read_generic_tax_report_amounts_no_tax_details(
        self, report, options, options_by_column_group
    ):
        # Fetch the group of taxes.
        # If all child taxes have a 'none' type_tax_use, all amounts are aggregated and only the group appears on the report.
        company_ids = report.get_report_company_ids(options)
        company_domain = self.env["account.tax"]._check_company_domain(company_ids)
        company_where_query = (
            self.env["account.tax"]
            .with_context(active_test=False)
            ._search(company_domain, bypass_access=True)
        )
        self.env.cr.execute(
            SQL(
                """
                SELECT
                    account_tax.id,
                    account_tax.type_tax_use,
                    ARRAY_AGG(child_tax.id ORDER BY child_tax.id) AS child_tax_ids,
                    ARRAY_AGG(child_tax.type_tax_use ORDER BY child_tax.id) AS child_types,
                    ARRAY_AGG(child_tax.tax_exigibility ORDER BY child_tax.id) as child_exigibility
                FROM account_tax_filiation_rel account_tax_rel
                JOIN account_tax ON account_tax.id = account_tax_rel.parent_tax
                JOIN account_tax child_tax ON child_tax.id = account_tax_rel.child_tax
                WHERE account_tax.amount_type = 'group'
                AND %s
                GROUP BY account_tax.id
            """,
                company_where_query.where_clause or SQL("TRUE"),
            )
        )
        group_of_taxes_info = {}
        child_to_group_of_taxes = {}
        for row in self.env.cr.dictfetchall():
            row["to_expand"] = set(row["child_types"]) != {"none"}
            group_of_taxes_info[row["id"]] = row
            for child_id in row["child_tax_ids"]:
                child_to_group_of_taxes[child_id] = row["id"]
        _debug.perf.count("groups_of_taxes_rows_fetched", rows=self.env.cr.rowcount)
        if _debug.pipeline.enabled:
            _debug.pipeline(
                "groups_of_taxes_fetched",
                report=report,
                groups=len(group_of_taxes_info),
                groups_to_expand=sum(
                    1 for info in group_of_taxes_info.values() if info["to_expand"]
                ),
                child_taxes=len(child_to_group_of_taxes),
            )

        results = defaultdict(
            lambda: {  # key: type_tax_use
                "base_amount": dict.fromkeys(options["column_groups"], 0.0),
                "tax_amount": dict.fromkeys(options["column_groups"], 0.0),
                "tax_non_deductible": dict.fromkeys(options["column_groups"], 0.0),
                "tax_deductible": dict.fromkeys(options["column_groups"], 0.0),
                "tax_due": dict.fromkeys(options["column_groups"], 0.0),
                "children": defaultdict(
                    lambda: {  # key: tax_id
                        "base_amount": dict.fromkeys(options["column_groups"], 0.0),
                        "tax_amount": dict.fromkeys(options["column_groups"], 0.0),
                        "tax_non_deductible": dict.fromkeys(
                            options["column_groups"], 0.0
                        ),
                        "tax_deductible": dict.fromkeys(options["column_groups"], 0.0),
                        "tax_due": dict.fromkeys(options["column_groups"], 0.0),
                    }
                ),
            }
        )

        for column_group_key, column_group_options in options_by_column_group.items():
            query = report._get_report_query(column_group_options, "strict_range")
            # make sure account_move is always joined
            if "account_move_line__move_id" not in query._joins:
                query.join(
                    "account_move_line", "move_id", "account_move", "id", "move_id"
                )

            # Fetch the base amounts.
            self.env.cr.execute(
                SQL(
                    """
                SELECT
                    tax.id AS tax_id,
                    tax.type_tax_use AS tax_type_tax_use,
                    src_group_tax.id AS src_group_tax_id,
                    src_group_tax.type_tax_use AS src_group_tax_type_tax_use,
                    src_tax.id AS src_tax_id,
                    src_tax.type_tax_use AS src_tax_type_tax_use,
                    SUM(account_move_line.balance) AS base_amount
                FROM %(table_references)s
                JOIN account_move_line_account_tax_rel tax_rel ON account_move_line.id = tax_rel.account_move_line_id
                JOIN account_tax tax ON tax.id = tax_rel.account_tax_id
                LEFT JOIN account_tax_repartition_line src_rep ON src_rep.id = account_move_line.tax_repartition_line_id
                LEFT JOIN account_tax src_tax ON src_tax.id = src_rep.tax_id
                LEFT JOIN account_tax src_group_tax ON src_group_tax.id = account_move_line.group_tax_id
                WHERE %(search_condition)s
                    AND (
                        /* CABA */
                        account_move_line__move_id.always_tax_exigible
                        OR account_move_line__move_id.tax_cash_basis_rec_id IS NOT NULL
                        OR tax.tax_exigibility != 'on_payment'
                    )
                    AND (
                        (
                            /* Tax lines affecting the base of others. */
                            src_tax.id IS NOT NULL
                            AND (
                                src_tax.type_tax_use IN ('sale', 'purchase')
                                OR src_group_tax.type_tax_use IN ('sale', 'purchase')
                            )
                        )
                        OR
                        (
                            /* For regular base lines. */
                            src_tax.id IS NULL
                            AND tax.type_tax_use IN ('sale', 'purchase')
                        )
                    )
                GROUP BY tax.id, src_group_tax.id, src_tax.id
                ORDER BY src_group_tax.sequence, src_group_tax.id, src_tax.sequence, src_tax.id, tax.sequence, tax.id
                """,
                    table_references=query.from_clause,
                    search_condition=query.where_clause,
                )
            )

            group_of_taxes_with_extra_base_amount = set()
            for row in self.env.cr.dictfetchall():
                is_tax_line = bool(row["src_tax_id"])
                if is_tax_line:
                    if (
                        row["src_group_tax_id"]
                        and not group_of_taxes_info[row["src_group_tax_id"]][
                            "to_expand"
                        ]
                        and row["tax_id"]
                        in group_of_taxes_info[row["src_group_tax_id"]]["child_tax_ids"]
                    ):
                        # Suppose a base of 1000 with a group of taxes 20% affect + 10%.
                        # The base of the group of taxes must be 1000, not 1200 because the group of taxes is not
                        # expanded. So the tax lines affecting the base of its own group of taxes are ignored.
                        pass
                    elif row[
                        "tax_type_tax_use"
                    ] == "none" and child_to_group_of_taxes.get(row["tax_id"]):
                        # The tax line is affecting the base of a 'none' tax belonging to a group of taxes.
                        # In that case, the amount is accounted as an extra base for that group. However, we need to
                        # account it only once.
                        # For example, suppose a tax 10% affect base of subsequent followed by a group of taxes
                        # 20% + 30%. On a base of 1000.0, the tax line for 10% will affect the base of 20% + 30%.
                        # However, this extra base must be accounted only once since the base of the group of taxes
                        # must be 1100.0 and not 1200.0.
                        group_tax_id = child_to_group_of_taxes[row["tax_id"]]
                        if group_tax_id not in group_of_taxes_with_extra_base_amount:
                            group_tax_info = group_of_taxes_info[group_tax_id]
                            results[group_tax_info["type_tax_use"]]["children"][
                                group_tax_id
                            ]["base_amount"][column_group_key] += row["base_amount"]
                            group_of_taxes_with_extra_base_amount.add(group_tax_id)
                    else:
                        tax_type_tax_use = (
                            row["src_group_tax_type_tax_use"]
                            or row["src_tax_type_tax_use"]
                        )
                        results[tax_type_tax_use]["children"][row["tax_id"]][
                            "base_amount"
                        ][column_group_key] += row["base_amount"]
                elif (
                    row["tax_id"] in group_of_taxes_info
                    and group_of_taxes_info[row["tax_id"]]["to_expand"]
                ):
                    # Expand the group of taxes since it contains at least one tax with a type != 'none'.
                    group_info = group_of_taxes_info[row["tax_id"]]
                    for child_tax_id, child_exigibility in zip(
                        group_info["child_tax_ids"],
                        group_info["child_exigibility"],
                        strict=False,
                    ):
                        if child_exigibility != "on_payment":
                            results[group_info["type_tax_use"]]["children"][
                                child_tax_id
                            ]["base_amount"][column_group_key] += row["base_amount"]
                else:
                    results[row["tax_type_tax_use"]]["children"][row["tax_id"]][
                        "base_amount"
                    ][column_group_key] += row["base_amount"]

            _debug.perf.count(
                "base_amount_rows_fetched",
                column_group=column_group_key,
                rows=self.env.cr.rowcount,
            )
            _debug.pipeline(
                "base_amounts_read",
                report=report,
                column_group=column_group_key,
                tax_types=len(results),
                groups_with_extra_base=len(group_of_taxes_with_extra_base_amount),
            )
            # Fetch the tax amounts.

            select_deductible = join_deductible = group_by_deductible = SQL()
            _debug.logic(
                "tax_deductibility_columns",
                report=report,
                column_group=column_group_key,
                enabled=bool(
                    column_group_options.get(
                        "account_journal_report_tax_deductibility_columns"
                    )
                ),
            )
            if column_group_options.get(
                "account_journal_report_tax_deductibility_columns"
            ):
                select_deductible = SQL(""", repartition.use_in_tax_closing AS trl_tax_closing
                                           , SIGN(repartition.factor_percent) AS trl_factor""")
                join_deductible = SQL("""JOIN account_tax_repartition_line repartition
                                           ON account_move_line.tax_repartition_line_id = repartition.id""")
                group_by_deductible = SQL(
                    ", repartition.use_in_tax_closing, SIGN(repartition.factor_percent)"
                )

            self.env.cr.execute(
                SQL(
                    """
                SELECT
                    tax.id AS tax_id,
                    tax.type_tax_use AS tax_type_tax_use,
                    group_tax.id AS group_tax_id,
                    group_tax.type_tax_use AS group_tax_type_tax_use,
                    SUM(account_move_line.balance) AS tax_amount
                    %(select_deductible)s
                FROM %(table_references)s
                JOIN account_tax_repartition_line tax_rep ON tax_rep.id = account_move_line.tax_repartition_line_id
                JOIN account_tax tax ON tax.id = tax_rep.tax_id
                %(join_deductible)s
                LEFT JOIN account_tax group_tax ON group_tax.id = account_move_line.group_tax_id
                WHERE %(search_condition)s
                    AND (
                        /* CABA */
                        account_move_line__move_id.always_tax_exigible
                        OR account_move_line__move_id.tax_cash_basis_rec_id IS NOT NULL
                        OR tax.tax_exigibility != 'on_payment'
                    )
                    AND (
                        (group_tax.id IS NULL AND tax.type_tax_use IN ('sale', 'purchase'))
                        OR
                        (group_tax.id IS NOT NULL AND group_tax.type_tax_use IN ('sale', 'purchase'))
                    )
                GROUP BY tax.id, group_tax.id %(group_by_deductible)s
                """,
                    select_deductible=select_deductible,
                    table_references=query.from_clause,
                    join_deductible=join_deductible,
                    search_condition=query.where_clause,
                    group_by_deductible=group_by_deductible,
                )
            )

            for row in self.env.cr.dictfetchall():
                # Manage group of taxes.
                # In case the group of taxes is mixing multiple taxes having a type_tax_use != 'none', consider
                # them instead of the group.
                tax_id = row["tax_id"]
                if row["group_tax_id"]:
                    tax_type_tax_use = row["group_tax_type_tax_use"]
                    if not group_of_taxes_info[row["group_tax_id"]]["to_expand"]:
                        tax_id = row["group_tax_id"]
                else:
                    tax_type_tax_use = (
                        row["group_tax_type_tax_use"] or row["tax_type_tax_use"]
                    )

                results[tax_type_tax_use]["tax_amount"][column_group_key] += row[
                    "tax_amount"
                ]
                results[tax_type_tax_use]["children"][tax_id]["tax_amount"][
                    column_group_key
                ] += row["tax_amount"]

                if column_group_options.get(
                    "account_journal_report_tax_deductibility_columns"
                ):
                    tax_detail_label = False
                    if row["trl_factor"] > 0 and tax_type_tax_use == "purchase":
                        tax_detail_label = (
                            "tax_deductible"
                            if row["trl_tax_closing"]
                            else "tax_non_deductible"
                        )
                    elif row["trl_tax_closing"] and (
                        row["trl_factor"] > 0,
                        tax_type_tax_use,
                    ) in ((False, "purchase"), (True, "sale")):
                        tax_detail_label = "tax_due"

                    if tax_detail_label:
                        results[tax_type_tax_use][tax_detail_label][
                            column_group_key
                        ] += row["tax_amount"] * row["trl_factor"]
                        results[tax_type_tax_use]["children"][tax_id][tax_detail_label][
                            column_group_key
                        ] += row["tax_amount"] * row["trl_factor"]

            _debug.perf.count(
                "tax_amount_rows_fetched",
                column_group=column_group_key,
                rows=self.env.cr.rowcount,
            )

        if _debug.pipeline.enabled:
            _debug.pipeline(
                "tax_amounts_read",
                report=report,
                tax_types=sorted(str(key) for key in results),
                taxes=sum(len(node["children"]) for node in results.values()),
            )
        return results

    @_debug.perf.timed
    def _read_generic_tax_report_amounts(
        self, report, options_by_column_group, groupby_fields
    ):
        """Read the tax details to compute the tax amounts.

        :param report:                  The account.report record being rendered.
        :param options_by_column_group: The report options, split per column group key.
        :param groupby_fields:          A list of tuple (alias, field) representing the way the amounts must be grouped.
        :return:                        A dictionary mapping each groupby key (e.g. a tax_id) to a sub dictionary containing:

            base_amount:    The tax base amount expressed in company's currency.
            tax_amount:     The tax amount expressed in company's currency.
            children:       The children nodes following the same pattern as the current dictionary.

        :rtype:                         dict
        """
        fetch_group_of_taxes = False

        select_clause_list = []
        groupby_query_list = []
        for alias, field in groupby_fields:
            select_clause_list.append(
                SQL(
                    "%s AS %s",
                    SQL.identifier(alias, field),
                    SQL.identifier(f"{alias}_{field}"),
                )
            )
            groupby_query_list.append(SQL.identifier(alias, field))

            # Fetch both info from the originator tax and the child tax to manage the group of taxes.
            if alias == "src_tax":
                select_clause_list.append(
                    SQL(
                        "%s AS %s",
                        SQL.identifier("tax", field),
                        SQL.identifier(f"tax_{field}"),
                    )
                )
                groupby_query_list.append(SQL.identifier("tax", field))
                fetch_group_of_taxes = True

        # Fetch the group of taxes.
        # If all children taxes are 'none', all amounts are aggregated and only the group will appear on the report.
        # If some children taxes are not 'none', the children are displayed.
        group_of_taxes_to_expand = set()
        if fetch_group_of_taxes:
            group_of_taxes = (
                self.env["account.tax"]
                .with_context(active_test=False)
                .search([("amount_type", "=", "group")])
            )
            for group in group_of_taxes:
                if set(group.children_tax_ids.mapped("type_tax_use")) != {"none"}:
                    group_of_taxes_to_expand.add(group.id)
        _debug.logic(
            "tax_details_groupby_resolved",
            report=report,
            groupby=groupby_fields,
            fetch_group_of_taxes=fetch_group_of_taxes,
            groups_to_expand=len(group_of_taxes_to_expand),
        )

        res = {}
        for column_group_key, options in options_by_column_group.items():
            query = report._get_report_query(options, "strict_range")
            tax_details_query = self.env["account.move.line"]._get_query_tax_details(
                query
            )

            # Avoid adding multiple times the same base amount sharing the same grouping_key.
            # It could happen when dealing with group of taxes for example.
            row_keys = set()

            self.env.cr.execute(
                SQL(
                    """
                SELECT
                    %(select_clause)s,
                    trl.document_type = 'refund' AS is_refund,
                    SUM(CASE WHEN tdr.display_type = 'rounding' THEN 0 ELSE tdr.base_amount END) AS base_amount,
                    SUM(tdr.tax_amount) AS tax_amount
                FROM (%(tax_details_query)s) AS tdr
                JOIN account_tax_repartition_line trl ON trl.id = tdr.tax_repartition_line_id
                JOIN account_tax tax ON tax.id = tdr.tax_id
                JOIN account_tax src_tax ON
                    src_tax.id = COALESCE(tdr.group_tax_id, tdr.tax_id)
                    AND src_tax.type_tax_use IN ('sale', 'purchase')
                JOIN account_account account ON account.id = tdr.base_account_id
                WHERE tdr.tax_exigible
                GROUP BY tdr.tax_repartition_line_id, trl.document_type, %(groupby_query)s
                ORDER BY src_tax.sequence, src_tax.id, tax.sequence, tax.id
                """,
                    select_clause=SQL(",").join(select_clause_list),
                    tax_details_query=tax_details_query,
                    groupby_query=SQL(",").join(groupby_query_list),
                )
            )

            for row in self.env.cr.dictfetchall():
                node = res

                # tuple of values used to prevent adding multiple times the same base amount.
                cumulated_row_key = [row["is_refund"]]

                for alias, field in groupby_fields:
                    grouping_key = f"{alias}_{field}"

                    # Manage group of taxes.
                    # In case the group of taxes is mixing multiple taxes having a type_tax_use != 'none', consider
                    # them instead of the group.
                    if (
                        grouping_key == "src_tax_id"
                        and row["src_tax_id"] in group_of_taxes_to_expand
                    ):
                        # Add the originator group to the grouping key, to make sure that its base amount is not
                        # treated twice, for hybrid cases where a tax is both used in a group and independently.
                        cumulated_row_key.append(row[grouping_key])

                        # Ensure the child tax is used instead of the group.
                        grouping_key = "tax_id"

                    row_key = row[grouping_key]
                    cumulated_row_key.append(row_key)
                    cumulated_row_key_tuple = tuple(cumulated_row_key)

                    node.setdefault(
                        row_key,
                        {
                            "base_amount": dict.fromkeys(options["column_groups"], 0.0),
                            "tax_amount": dict.fromkeys(options["column_groups"], 0.0),
                            "children": {},
                        },
                    )
                    sub_node = node[row_key]

                    # Add amounts.
                    if cumulated_row_key_tuple not in row_keys:
                        sub_node["base_amount"][column_group_key] += row["base_amount"]
                    sub_node["tax_amount"][column_group_key] += row["tax_amount"]

                    node = sub_node["children"]
                    row_keys.add(cumulated_row_key_tuple)

            _debug.perf.count(
                "tax_detail_rows_fetched",
                column_group=column_group_key,
                rows=self.env.cr.rowcount,
            )
            _debug.pipeline(
                "tax_details_rows_read",
                report=report,
                column_group=column_group_key,
                distinct_row_keys=len(row_keys),
                top_level_nodes=len(res),
            )

        return res

    @_debug.perf.timed
    def _update_lines_recursively(
        self,
        report,
        options,
        lines,
        sorting_map_list,
        groupby_fields,
        values_node,
        index=0,
        type_tax_use=None,
        parent_line_id=None,
        warnings=None,
    ):
        """Populate the list of report lines passed as parameter recursively. At this point, every amounts is already
        fetched for every periods and every groupby.

        :param options:             The report options.
        :param lines:               The list of report lines to populate.
        :param sorting_map_list:    A list of dictionary mapping each encountered key with a weight to sort the results.
        :param index:               The index of the current element to process (also equals to the level into the hierarchy).
        :param groupby_fields:      A list of tuple <alias, field> defining in which way tax amounts should be grouped.
        :param values_node:         The node containing the amounts and children into the hierarchy.
        :param type_tax_use:        The type_tax_use of the tax.
        :param parent_line_id:      The line id of the parent line (if any)
        :param warnings             The warnings dictionnary.
        """
        if index == len(groupby_fields):
            return

        alias, field = groupby_fields[index]
        groupby_key = f"{alias}_{field}"

        # Sort the keys in order to add the lines in the same order as the records.
        sorting_map = sorting_map_list[index]
        sorted_keys = sorted(values_node.keys(), key=lambda x: sorting_map[x][1])

        for key in sorted_keys:
            # Compute 'type_tax_use' with the first grouping since 'src_tax_type_tax_use' is always
            # the first one.
            if groupby_key == "src_tax_type_tax_use":
                type_tax_use = key
            sign = -1 if type_tax_use == "sale" else 1

            # Prepare columns.
            tax_amount_dict = values_node[key]
            columns = []
            tax_base_amounts = tax_amount_dict["base_amount"]
            tax_amounts = tax_amount_dict["tax_amount"]

            for column in options["columns"]:
                tax_base_amount = tax_base_amounts[column["column_group_key"]]
                tax_amount = tax_amounts[column["column_group_key"]]

                expr_label = column.get("expression_label")
                col_value = ""

                if expr_label == "net" and index == len(groupby_fields) - 1:
                    col_value = sign * tax_base_amount

                if expr_label == "tax":
                    col_value = sign * tax_amount

                columns.append(
                    report._prepare_column_dict(col_value, column, options=options)
                )

                # Add the non-deductible, deductible and due tax amounts.
                if expr_label == "tax" and options.get(
                    "account_journal_report_tax_deductibility_columns"
                ):
                    columns.extend(
                        report._prepare_column_dict(
                            col_value=sign
                            * tax_amount_dict[deduct_type][column["column_group_key"]],
                            col_data={
                                "figure_type": "monetary",
                                "column_group_key": column["column_group_key"],
                                "expression_label": deduct_type,
                            },
                            options=options,
                        )
                        for deduct_type in (
                            "tax_non_deductible",
                            "tax_deductible",
                            "tax_due",
                        )
                    )

            # Prepare line.
            default_vals = {
                "columns": columns,
                "level": index if index == 0 else index + 1,
                "unfoldable": False,
            }
            report_line = self._prepare_report_line(
                report,
                options,
                default_vals,
                groupby_key,
                sorting_map[key][0],
                parent_line_id,
                warnings,
            )

            if groupby_key == "src_tax_id":
                report_line["caret_options"] = "generic_tax_report"

            lines.append((0, report_line))

            # Process children recursively.
            self._update_lines_recursively(
                report,
                options,
                lines,
                sorting_map_list,
                groupby_fields,
                tax_amount_dict.get("children"),
                index=index + 1,
                type_tax_use=type_tax_use,
                parent_line_id=report_line["id"],
                warnings=warnings,
            )
        if _debug.pipeline.enabled and index == 0:
            _debug.pipeline(
                "tax_lines_populated",
                report=report,
                levels=len(groupby_fields),
                top_level_keys=len(sorted_keys),
                lines=len(lines),
            )

    @_debug.perf.timed
    def _prepare_report_line(
        self,
        report,
        options,
        default_vals,
        groupby_key,
        value,
        parent_line_id,
        warnings=None,
    ):
        """Build the report line accordingly to its type.

        :param report:          The account.report record being rendered.
        :param options:         The report options.
        :param default_vals:    The pre-computed report line values.
        :param str groupby_key: The groupby field name this line stands for
                                ('src_tax_type_tax_use', 'src_tax_id' or 'account_id').
        :param value:           The grouping value, a record or a tuple depending on `groupby_key`.
        :param parent_line_id:  The line id of the parent line (if any, can be None otherwise).
        :param warnings:        The warnings dictionary.
        :return:                A python dictionary.
        :rtype:                 dict
        """
        report_line = dict(default_vals)
        if parent_line_id is not None:
            report_line["parent_id"] = parent_line_id

        if groupby_key == "src_tax_type_tax_use":
            type_tax_use_option = value
            report_line["id"] = report._get_generic_line_id(
                None, None, markup=type_tax_use_option[0], parent_line_id=parent_line_id
            )
            report_line["name"] = type_tax_use_option[1]

        elif groupby_key == "src_tax_id":
            tax = value
            report_line["id"] = report._get_generic_line_id(
                tax._name, tax.id, parent_line_id=parent_line_id
            )

            if tax.amount_type == "percent":
                report_line["name"] = f"{tax.name} ({tax.amount}%)"

                if warnings is not None:
                    self._check_line_consistency(
                        report, options, report_line, tax, warnings
                    )
            elif tax.amount_type == "fixed":
                report_line["name"] = f"{tax.name} ({tax.amount})"
            else:
                report_line["name"] = tax.name

            if options.get("multi-company"):
                report_line["name"] = (
                    f"{report_line['name']} - {self.env.company.display_name}"
                )

        elif groupby_key == "account_id":
            account = value
            report_line["id"] = report._get_generic_line_id(
                account._name, account.id, parent_line_id=parent_line_id
            )

            if options.get("multi-company"):
                report_line["name"] = (
                    f"{account.display_name} - {account.company_id.display_name}"
                )
            else:
                report_line["name"] = account.display_name

        return report_line

    @_debug.perf.timed
    def _check_line_consistency(self, report, options, report_line, tax, warnings=None):
        tax_applied = (
            tax.amount
            * sum(
                tax.invoice_repartition_line_ids.filtered(
                    lambda tax_rep: tax_rep.repartition_type == "tax"
                ).mapped("factor")
            )
            / 100
        )

        for column_group_key in report._split_options_per_column_group(options):
            net_value = next(
                (
                    col["no_format"]
                    for col in report_line["columns"]
                    if col["column_group_key"] == column_group_key
                    and col["expression_label"] == "net"
                ),
                0,
            )
            tax_value = next(
                (
                    col["no_format"]
                    for col in report_line["columns"]
                    if col["column_group_key"] == column_group_key
                    and col["expression_label"] == "tax"
                ),
                0,
            )

            if net_value == "":
                continue

            currency = self.env.company.currency_id
            computed_tax_amount = float(net_value or 0) * tax_applied
            is_inconsistent = currency.compare_amounts(computed_tax_amount, tax_value)

            if is_inconsistent:
                error = abs(
                    (abs(tax_value) - abs(computed_tax_amount)) / float(net_value or 1)
                )

                # Error is bigger than 0.1%. We can not ignore it.
                if error > 0.001:
                    _debug.logic(
                        "tax_line_inconsistent",
                        report=report,
                        tax=tax,
                        column_group=column_group_key,
                        error=error,
                    )
                    report_line["alert"] = True
                    warnings["account.tax_report_warning_lines_consistency"] = {
                        "alert_type": "danger"
                    }

                    return

    # -------------------------------------------------------------------------
    # BUTTONS & CARET OPTIONS
    # -------------------------------------------------------------------------

    @_debug.perf.timed
    def caret_option_audit_tax(self, options, params):
        report = self.env["account.report"].browse(options["report_id"])
        model, tax_id = report._get_model_info_from_id(params["line_id"])

        if model != "account.tax":
            raise UserError(_("Cannot audit tax from another model than account.tax."))

        tax = self.env["account.tax"].browse(tax_id)

        if tax.amount_type == "group":
            tax_affecting_base_domain = [
                ("tax_ids", "in", tax.children_tax_ids.ids),
                ("tax_repartition_line_id", "!=", False),
            ]
        else:
            tax_affecting_base_domain = [
                ("tax_ids", "=", tax.id),
                ("tax_ids.type_tax_use", "=", tax.type_tax_use),
                ("tax_repartition_line_id", "!=", False),
            ]
        _debug.logic(
            "tax_audit_scope",
            report=report,
            tax=tax,
            group_of_taxes=tax.amount_type == "group",
        )

        domain = Domain(
            report._get_domain_options(options, "strict_range")
        ) & Domain.OR(
            (
                # Base lines
                [
                    ("tax_ids", "in", tax.ids),
                    ("tax_ids.type_tax_use", "=", tax.type_tax_use),
                    ("tax_repartition_line_id", "=", False),
                ],
                # Tax lines
                [
                    ("group_tax_id", "=", tax.id)
                    if tax.amount_type == "group"
                    else ("tax_line_id", "=", tax.id),
                ],
                # Tax lines acting as base lines
                tax_affecting_base_domain,
            )
        )

        ctx = self.env.context.copy()
        ctx.update({"search_default_group_by_account": 2, "expand": 1})

        return {
            "type": "ir.actions.act_window",
            "name": _("Journal Items for Tax Audit"),
            "res_model": "account.move.line",
            "views": [
                [self.env.ref("account.view_move_line_tax_audit_tree").id, "list"]
            ],
            "domain": domain,
            "context": ctx,
        }


class AccountGenericTaxReportHandlerAccountTax(models.AbstractModel):
    _name = "account.generic.tax.report.handler.account.tax"
    _inherit = ["account.generic.tax.report.handler"]
    _description = "Generic Tax Report Custom Handler (Account -> Tax)"

    def _dynamic_lines_generator(
        self, report, options, all_column_groups_expression_totals, warnings=None
    ):
        return super()._get_dynamic_lines(report, options, "account_tax", warnings)


class AccountGenericTaxReportHandlerTaxAccount(models.AbstractModel):
    _name = "account.generic.tax.report.handler.tax.account"
    _inherit = ["account.generic.tax.report.handler"]
    _description = "Generic Tax Report Custom Handler (Tax -> Account)"

    def _dynamic_lines_generator(
        self, report, options, all_column_groups_expression_totals, warnings=None
    ):
        return super()._get_dynamic_lines(report, options, "tax_account", warnings)
