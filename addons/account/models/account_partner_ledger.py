from collections import defaultdict
from copy import deepcopy
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog
from odoo.tools import SQL

_debug = DebugLog(__name__)


class AccountPartnerLedgerReportHandler(models.AbstractModel):
    _name = "account.partner.ledger.report.handler"
    _inherit = ["account.report.custom.handler"]
    _description = "Partner Ledger Custom Handler"

    def _dynamic_lines_generator(
        self, report, options, all_column_groups_expression_totals, warnings=None
    ):
        partner_lines, totals_by_column_group = self._prepare_partner_lines(
            report, options
        )
        lines = report._regroup_lines_by_name_prefix(
            options,
            partner_lines,
            "_report_expand_unfoldable_line_partner_ledger_prefix_group",
            0,
        )

        # Inject sequence on dynamic lines
        lines = [(0, line) for line in lines]

        # Report total line.
        lines.append((0, self._get_report_line_total(options, totals_by_column_group)))

        return lines

    @_debug.perf.timed
    def _prepare_partner_lines(self, report, options, level_shift=0):
        lines = []

        totals_by_column_group = {
            column_group_key: dict.fromkeys(
                ["debit", "credit", "amount", "balance"], 0.0
            )
            for column_group_key in options["column_groups"]
        }

        partners_results = self._query_partners(report, options)

        search_filter = options.get("filter_search_bar", "")
        accept_unknown_in_filter = (
            search_filter.lower() in self._get_no_partner_line_label().lower()
        )
        _debug.logic(
            "partner_search_filter",
            report=report,
            partners=len(partners_results),
            export_mode=options["export_mode"],
            search_filter=bool(search_filter),
            accept_unknown_in_filter=accept_unknown_in_filter,
            level_shift=level_shift,
        )
        for partner, results in partners_results:
            if (
                options["export_mode"] == "print"
                and search_filter
                and not partner
                and not accept_unknown_in_filter
            ):
                # When printing and searching for a specific partner, make it so we only show its lines, not the 'Unknown Partner' one, that would be
                # shown in case a misc entry with no partner was reconciled with one of the target partner's entries.
                continue

            partner_values = defaultdict(dict)
            for column_group_key in options["column_groups"]:
                partner_sum = results.get(column_group_key, {})

                partner_values[column_group_key]["debit"] = partner_sum.get(
                    "debit", 0.0
                )
                partner_values[column_group_key]["credit"] = partner_sum.get(
                    "credit", 0.0
                )
                partner_values[column_group_key]["amount"] = partner_sum.get(
                    "amount", 0.0
                )
                partner_values[column_group_key]["balance"] = partner_sum.get(
                    "balance", 0.0
                )
                partner_values[column_group_key]["amount_currency"] = partner_sum.get(
                    "amount_currency"
                )
                partner_values[column_group_key]["currency_id"] = partner_sum.get(
                    "currency_id"
                )

                totals_by_column_group[column_group_key]["debit"] += partner_values[
                    column_group_key
                ]["debit"]
                totals_by_column_group[column_group_key]["credit"] += partner_values[
                    column_group_key
                ]["credit"]
                totals_by_column_group[column_group_key]["amount"] += partner_values[
                    column_group_key
                ]["amount"]
                totals_by_column_group[column_group_key]["balance"] += partner_values[
                    column_group_key
                ]["balance"]

            lines.append(
                self._get_report_line_partners(
                    options, partner, partner_values, level_shift=level_shift
                )
            )

        _debug.pipeline(
            "partner_lines_prepared",
            report=report,
            partners=len(partners_results),
            lines=len(lines),
            filtered_out=len(partners_results) - len(lines),
        )
        return lines, totals_by_column_group

    @_debug.perf.timed
    def _report_expand_unfoldable_line_partner_ledger_prefix_group(
        self,
        line_dict_id,
        groupby,
        options,
        progress,
        offset,
        unfold_all_batch_data=None,
    ):
        report = self.env["account.report"].browse(options["report_id"])
        matched_prefix = report._get_prefix_groups_matched_prefix_from_line_id(
            line_dict_id
        )

        prefix_domain = Domain("partner_id.name", "=ilike", f"{matched_prefix}%")
        if self._get_no_partner_line_label().upper().startswith(matched_prefix):
            prefix_domain |= Domain("partner_id", "=", None)

        expand_options = {
            **options,
            # list(...): forced_domain travels inside options, which is
            # json.dumps'd, and a Domain is not serialisable.
            "forced_domain": list(
                Domain(options.get("forced_domain", [])) & prefix_domain
            ),
        }
        parent_level = len(matched_prefix) * 2
        partner_lines, _dummy = self._prepare_partner_lines(
            report, expand_options, level_shift=parent_level
        )

        for partner_line in partner_lines:
            partner_line["id"] = report._prepare_subline_id(
                line_dict_id, partner_line["id"]
            )
            partner_line["parent_id"] = line_dict_id

        lines = report._regroup_lines_by_name_prefix(
            options,
            partner_lines,
            "_report_expand_unfoldable_line_partner_ledger_prefix_group",
            parent_level,
            matched_prefix=matched_prefix,
            parent_line_dict_id=line_dict_id,
        )
        _debug.pipeline(
            "prefix_group_expanded",
            report=report,
            matched_prefix=matched_prefix,
            parent_level=parent_level,
            partner_lines=len(partner_lines),
            lines=len(lines),
        )

        return {
            "lines": lines,
            "offset_increment": len(lines),
            "has_more": False,
        }

    @_debug.perf.timed
    def _custom_options_initializer(self, report, options, previous_options):
        super()._custom_options_initializer(
            report, options, previous_options=previous_options
        )
        domain = []

        company_ids = report.get_report_company_ids(options)
        exch_code = (
            self.env["res.company"]
            .browse(company_ids)
            .mapped("currency_exchange_journal_id")
        )
        if exch_code:
            domain += [
                "!",
                "&",
                "&",
                "&",
                ("credit", "=", 0.0),
                ("debit", "=", 0.0),
                ("amount_currency", "!=", 0.0),
                ("journal_id", "in", exch_code.ids),
            ]

        if options["export_mode"] == "print" and options.get("filter_search_bar"):
            domain += [
                "|",
                (
                    "matched_debit_ids.debit_move_id.partner_id.name",
                    "ilike",
                    options["filter_search_bar"],
                ),
                "|",
                (
                    "matched_credit_ids.credit_move_id.partner_id.name",
                    "ilike",
                    options["filter_search_bar"],
                ),
                "|",
                ("partner_id.name", "ilike", options["filter_search_bar"]),
                ("partner_id", "=", False),
            ]

        options["forced_domain"] = options.get("forced_domain", []) + domain

        if self.env.user.has_group("base.group_multi_currency") and (
            options["export_mode"] != "print"
            or self._has_foreign_currency_lines(report, options)
        ):
            options["multi_currency"] = True
        else:
            options["columns"] = [
                col
                for col in options["columns"]
                if col["expression_label"] != "amount_currency"
            ]

        _debug.logic(
            "partner_ledger_options_resolved",
            report=report,
            exchange_journals=exch_code,
            forced_domain_leaves=len(domain),
            print_search_bar=options["export_mode"] == "print"
            and bool(options.get("filter_search_bar")),
            multi_currency=options.get("multi_currency", False),
            columns=len(options["columns"]),
        )
        options["custom_display_config"] = {
            "css_custom_class": "partner_ledger",
            "components": {
                "AccountReportLineCell": "PartnerLedgerLineCell",
            },
            "templates": {
                "AccountReportLineName": "account.PartnerLedgerLineName",
            },
        }

    def _has_foreign_currency_lines(self, report, options):
        # The Amount Currency column is only filled for lines whose currency differs
        # from the company's: _get_query_sums returns NULL as soon as they match. A
        # printed scope with none of them carries the column as blank width, which
        # on a landscape letter sheet pushes Balance past the printable area.
        domain = report._get_domain_options(options, "from_beginning") & Domain(
            "currency_id", "!=", self.env.company.currency_id.id
        )
        return bool(self.env["account.move.line"].search_count(domain, limit=1))

    @_debug.perf.timed
    def _custom_unfold_all_batch_data_generator(
        self, report, options, lines_to_expand_by_function
    ):
        partner_ids_to_expand = []

        # Regular case
        for line_dict in lines_to_expand_by_function.get(
            "_report_expand_unfoldable_line_partner_ledger", []
        ):
            markup, model, model_id = self.env["account.report"]._parse_line_id(
                line_dict["id"]
            )[-1]
            if model == "res.partner":
                partner_ids_to_expand.append(model_id)
            elif markup == "no_partner":
                partner_ids_to_expand.append(None)

        # In case prefix groups are used
        no_partner_line_label = self._get_no_partner_line_label().upper()
        partner_prefix_domains = []
        for line_dict in lines_to_expand_by_function.get(
            "_report_expand_unfoldable_line_partner_ledger_prefix_group", []
        ):
            prefix = report._get_prefix_groups_matched_prefix_from_line_id(
                line_dict["id"]
            )
            partner_prefix_domains.append([("name", "=ilike", f"{prefix}%")])

            # amls without partners are regrouped "Unknown Partner", which is also used to create prefix groups
            if no_partner_line_label.startswith(prefix):
                partner_ids_to_expand.append(None)

        if partner_prefix_domains:
            partner_ids_to_expand += (
                self.env["res.partner"]
                .with_context(active_test=False)
                .search(Domain.OR(partner_prefix_domains))
                .ids
            )
        _debug.pipeline(
            "unfold_batch_partners_collected",
            report=report,
            partner_lines=len(
                lines_to_expand_by_function.get(
                    "_report_expand_unfoldable_line_partner_ledger", []
                )
            ),
            prefix_groups=len(partner_prefix_domains),
            partners_to_expand=len(partner_ids_to_expand),
            skipped=not partner_ids_to_expand,
        )

        return {
            "initial_balances": self._prepare_initial_balance_values(
                partner_ids_to_expand, options
            )
            if partner_ids_to_expand
            else {},
            # load_more_limit cannot be passed to this call, otherwise it won't be applied per partner but on the whole result.
            # We gain perf from batching, but load every result, even if the limit restricts them later.
            "aml_values": self._prepare_aml_values(options, partner_ids_to_expand)
            if partner_ids_to_expand
            else {},
        }

    @api.model
    @_debug.perf.timed
    def action_view_partner(self, options, params):
        _debug.lifecycle("action_view_partner", records=self)
        _dummy, record_id = self.env["account.report"]._get_model_info_from_id(
            params["id"]
        )
        return {
            "type": "ir.actions.act_window",
            "res_model": "res.partner",
            "res_id": record_id,
            "views": [[False, "form"]],
            "view_mode": "form",
            "target": "current",
        }

    @api.model
    @_debug.perf.timed
    def action_toggle_no_followup(self, line_id, all_line_ids):
        """Toggle the `no_followup` field on the journal item corresponding to the given `line_id`.

        :param line_id: The report line ID.
        :param all_line_ids: A list containing all the report's line IDs.
        :return: None if the line is not a journal item, otherwise a dict containing:
            - `updated_value`: the updated `no_followup` value (`True` or `False`)
            - `updated_line_ids`: a list of the impacted report lines, so the report can be updated dynamically
        """
        _debug.lifecycle("action_toggle_no_followup", records=self)
        model, aml_id = self.env["account.report"]._get_model_info_from_id(line_id)
        _debug.logic(
            "no_followup_toggle_target",
            model=model,
            aml_id=aml_id,
            skipped=model != "account.move.line",
        )
        if model != "account.move.line":
            return None
        aml = self.env["account.move.line"].browse(aml_id)
        aml.no_followup = not aml.no_followup

        aml_id_to_line_id = {}
        for cur_line_id in all_line_ids:
            model, record_id = self.env["account.report"]._get_model_info_from_id(
                cur_line_id
            )
            if model == "account.move.line":
                aml_id_to_line_id[record_id] = cur_line_id

        res = {
            "updated_value": aml.no_followup,
            "updated_line_ids": [aml_id_to_line_id[aml.id]],
        }
        move = aml.move_id
        if move.is_invoice():
            # For invoices, the `no_followup` toggle will impact all its receivable/payable lines.
            res["updated_line_ids"] = move.line_ids.filtered(
                lambda line: (
                    line.account_type in ("asset_receivable", "liability_payable")
                ),
            ).mapped(lambda line: aml_id_to_line_id[line.id])
        _debug.pipeline(
            "no_followup_toggled",
            move=move,
            updated_value=res["updated_value"],
            report_lines=len(all_line_ids),
            updated_lines=len(res["updated_line_ids"]),
        )
        return res

    @_debug.perf.timed
    def _query_partners(self, report, options):
        """Executes the queries and performs all the computation.
        :return:        A list of tuple (partner, column_group_values) sorted by the table's model _order:
                        - partner is a res.partner record, or None for the 'Unknown Partner' entry.
                        - column_group_values is a dict(column_group_key, fetched_values), where
                            - column_group_key is a string identifying a column group, like in options['column_groups']
                            - fetched_values is a dictionary containing:
                                - debit, credit, amount, balance:  float, set directly on the dict (not nested)
        """

        def update_partner_sums(row):
            fields_to_assign = ["balance", "debit", "credit", "amount"]
            if any(
                not company_currency.is_zero(row[field]) for field in fields_to_assign
            ):
                groupby_partners.setdefault(
                    row["groupby"], defaultdict(lambda: defaultdict(float))
                )
                partner_vals = groupby_partners[row["groupby"]][row["column_group_key"]]
                for field in fields_to_assign:
                    partner_vals[field] += row[field]

                if (
                    row["amount_currency"] is not None
                    and partner_vals["amount_currency"] is not None
                ):
                    partner_vals["amount_currency"] += row["amount_currency"]
                    partner_vals["currency_id"] = row["currency_id"]
                else:
                    partner_vals["amount_currency"] = None
                    partner_vals["currency_id"] = None

        company_currency = self.env.company.currency_id

        # Execute the queries and dispatch the results.
        query = self._get_query_sums(report, options)

        groupby_partners = {}

        self.env.cr.execute(query)
        for res in self.env.cr.dictfetchall():
            update_partner_sums(res)
        _debug.perf.count("partner_sums_rows_fetched", rows=self.env.cr.rowcount)

        # Correct the sums per partner, for the lines without partner reconciled with a line having a partner
        self._add_sums_of_lines_without_partners(options, groupby_partners)

        # Retrieve the partners to browse.
        # groupby_partners.keys() contains all account ids affected by:
        # - the amls in the current period.
        # - the amls affecting the initial balance.
        if groupby_partners:
            # Note a search is done instead of a browse to preserve the table ordering.
            partners = (
                self.env["res.partner"]
                .with_context(active_test=False)
                .search_fetch(
                    [("id", "in", list(groupby_partners.keys()))],
                    ["id", "name", "trust", "company_registry", "vat"],
                )
            )
        else:
            partners = []

        # Add 'Partner Unknown' if needed
        if None in groupby_partners:
            partners = list(partners) + [None]
        _debug.pipeline(
            "partner_sums_grouped",
            report=report,
            partners_with_sums=len(groupby_partners),
            unknown_partner=None in groupby_partners,
            partners=len(partners),
        )

        return [
            (partner, groupby_partners[partner.id if partner else None])
            for partner in partners
        ]

    @_debug.perf.timed
    def _get_query_sums(self, report, options) -> SQL:
        """Construct a query retrieving all the aggregated sums to build the report. It includes:
        - sums for all partners.
        - sums for the initial balances.
        :param report:              The partner ledger report.
        :param options:             The report options.
        :return:                    query as SQL object
        :rtype: SQL
        """
        queries = []

        # Create the currency table.
        for (
            column_group_key,
            column_group_options,
        ) in report._split_options_per_column_group(options).items():
            query = report._get_report_query(column_group_options, "from_beginning")

            # With the followup reports, date_from should be None
            date_from = report._get_date_bounds_info(
                column_group_options, "strict_range"
            )[0]
            date_filter = (
                SQL("account_move_line.date >= %(date_from)s", date_from=date_from)
                if date_from
                else SQL("TRUE")
            )
            _debug.logic(
                "sums_date_filter",
                report=report,
                column_group=column_group_key,
                date_from=date_from,
                unbounded=not date_from,
            )

            queries.append(
                SQL(
                    """
                (WITH partner_sums AS (
                    SELECT
                        account_move_line.partner_id                            AS groupby,
                        %(column_group_key)s                                    AS column_group_key,
                        SUM(
                            CASE WHEN %(date_filter)s
                            THEN %(debit_select)s
                            ELSE 0
                            END
                        )                                                       AS debit,
                        SUM(
                            CASE WHEN %(date_filter)s
                            THEN %(credit_select)s
                            ELSE 0
                            END
                        )                                                       AS credit,
                        SUM(%(balance_select)s)                                 AS amount,
                        SUM(%(balance_select)s)                                 AS balance,
                        CASE
                            WHEN MIN(CASE WHEN %(date_filter)s THEN account_move_line.currency_id ELSE NULL END)
                               = MAX(CASE WHEN %(date_filter)s THEN account_move_line.currency_id ELSE NULL END)
                            THEN MIN(CASE WHEN %(date_filter)s THEN account_move_line.currency_id ELSE NULL END)
                            ELSE NULL
                        END                                                     AS currency_id,
                        CASE
                            WHEN MIN(CASE WHEN %(date_filter)s THEN account_move_line.currency_id ELSE NULL END)
                               = MAX(CASE WHEN %(date_filter)s THEN account_move_line.currency_id ELSE NULL END)
                             AND MIN(CASE WHEN %(date_filter)s THEN account_move_line.currency_id ELSE NULL END) != %(company_currency)s
                            THEN SUM(CASE WHEN %(date_filter)s THEN account_move_line.amount_currency ELSE 0 END)
                            ELSE NULL
                        END                                                     AS amount_currency,
                        MAX(account_move_line.date)                             AS latest_date
                    FROM %(table_references)s
                    %(currency_table_join)s
                    WHERE %(search_condition)s
                    GROUP BY account_move_line.partner_id
                )
                SELECT *
                FROM partner_sums
                WHERE partner_sums.balance != 0
                OR partner_sums.latest_date >= %(date_from_or_min)s
                )""",
                    column_group_key=column_group_key,
                    date_filter=date_filter,
                    date_from_or_min=date_from or "1900-01-01",
                    debit_select=report._currency_table_apply_rate(
                        SQL("account_move_line.debit")
                    ),
                    credit_select=report._currency_table_apply_rate(
                        SQL("account_move_line.credit")
                    ),
                    balance_select=report._currency_table_apply_rate(
                        SQL("account_move_line.balance")
                    ),
                    table_references=query.from_clause,
                    currency_table_join=report._currency_table_aml_join(
                        column_group_options
                    ),
                    search_condition=query.where_clause,
                    company_currency=self.env.company.currency_id.id,
                )
            )

        return SQL(" UNION ALL ").join(queries)

    @_debug.perf.timed
    def _prepare_initial_balance_values(self, partner_ids, options):
        report = self.env["account.report"].browse(options["report_id"])

        _debug.logic(
            "initial_balance_mode",
            report=report,
            partners=len(partner_ids),
            filter_date_range=report.filter_date_range,
        )
        if not report.filter_date_range:
            # Happens when the report has been manually customized to not use date ranges anymore.
            return {
                partner_id: {
                    col_group_key: {} for col_group_key in options["column_groups"]
                }
                for partner_id in partner_ids
            }

        queries = []
        for (
            column_group_key,
            column_group_options,
        ) in report._split_options_per_column_group(options).items():
            # Get sums for the initial balance.
            # period: [('date' <= options['date_from'] - 1)]
            new_options = self._get_options_initial_balance(column_group_options)
            query = report._get_report_query(
                new_options,
                "from_beginning",
                domain=[("partner_id", "in", partner_ids)],
            )
            queries.append(
                SQL(
                    """
                SELECT
                    account_move_line.partner_id,
                    %(column_group_key)s          AS column_group_key,
                    0                             AS debit,
                    0                             AS credit,
                    SUM(%(balance_select)s)       AS amount,
                    SUM(%(balance_select)s)       AS balance
                FROM %(table_references)s
                %(currency_table_join)s
                WHERE %(search_condition)s
                GROUP BY account_move_line.partner_id
                """,
                    column_group_key=column_group_key,
                    debit_select=report._currency_table_apply_rate(
                        SQL("account_move_line.debit")
                    ),
                    credit_select=report._currency_table_apply_rate(
                        SQL("account_move_line.credit")
                    ),
                    balance_select=report._currency_table_apply_rate(
                        SQL("account_move_line.balance")
                    ),
                    table_references=query.from_clause,
                    currency_table_join=report._currency_table_aml_join(
                        column_group_options
                    ),
                    search_condition=query.where_clause,
                )
            )

        self.env.cr.execute(SQL(" UNION ALL ").join(queries))

        init_balance_by_col_group = {
            partner_id: {
                column_group_key: defaultdict(float)
                for column_group_key in options["column_groups"]
            }
            for partner_id in partner_ids
        }
        for result in self.env.cr.dictfetchall():
            init_balance_by_col_group[result["partner_id"]][
                result["column_group_key"]
            ] = result
        _debug.perf.count("initial_balance_rows_fetched", rows=self.env.cr.rowcount)

        # Correct the sums per partner, for the lines without partner reconciled with a line having a partner
        new_options = self._get_options_initial_balance(options)
        self._add_sums_of_lines_without_partners(new_options, init_balance_by_col_group)
        _debug.pipeline(
            "initial_balances_read",
            report=report,
            partners=len(init_balance_by_col_group),
            column_groups=len(queries),
        )

        return init_balance_by_col_group

    def _get_options_initial_balance(self, options):
        """Create options used to compute the initial balances for each partner.
        The resulting dates domain will be:
        [('date' <= options['date_from'] - 1)]
        :param options: The report options.
        :return:        A copy of the options, modified to match the dates to use to get the initial balances.
        """
        new_date_to = fields.Date.from_string(options["date"]["date_from"]) - timedelta(
            days=1
        )
        new_options = deepcopy(options)
        new_options["date"]["date_from"] = False
        new_options["date"]["date_to"] = fields.Date.to_string(new_date_to)
        for column_group in new_options["column_groups"].values():
            column_group["forced_options"]["date"] = new_options["date"]
        return new_options

    def _add_sums_of_lines_without_partners(self, options, result_dict):
        fields2inverse = {
            "balance": ("balance", -1),
            "debit": ("credit", 1),
            "amount": ("amount", 1),
            "credit": ("debit", 1),
        }
        query = self._get_sums_without_partner(options)
        self.env.cr.execute(query)
        rows = self.env.cr.dictfetchall()
        _debug.perf.count("sums_without_partner_fetched", rows=len(rows))
        for row in rows:
            for field, (inverse_field, inverse_sign) in fields2inverse.items():
                if partner_vals := result_dict.get(row["groupby"]):
                    partner_vals[row["column_group_key"]][field] += row[field]
                if no_partner_vals := result_dict.get(None):
                    # Debit/credit are inverted for the unknown partner as the computation is made regarding the balance of the known partner
                    no_partner_vals[row["column_group_key"]][inverse_field] += (
                        inverse_sign * row[field]
                    )

    @_debug.perf.timed
    def _get_sums_without_partner(self, options):
        """Get the sum of lines without partner reconciled with a line with a partner, grouped by partner."""
        # Those lines belong to the partner for the reconciled amount, as they may clear some of the partner
        # invoice/bill and therefore have to be accounted in the partner balance.
        queries = []
        report = self.env.ref("account.partner_ledger_report")
        for (
            column_group_key,
            column_group_options,
        ) in report._split_options_per_column_group(options).items():
            partner_ids = column_group_options.pop("partner_ids", [])
            _debug.logic(
                "sums_without_partner_scope",
                report=report,
                column_group=column_group_key,
                partner_constraint=bool(partner_ids),
                partners=len(partner_ids),
            )
            query = report._get_report_query(column_group_options, "from_beginning")
            queries.append(
                SQL(
                    """
                SELECT
                    %(column_group_key)s        AS column_group_key,
                    aml_with_partner.partner_id AS groupby,
                    SUM(%(debit_select)s)       AS debit,
                    SUM(%(credit_select)s)      AS credit,
                    SUM(%(balance_select)s)     AS amount,
                    SUM(%(balance_select)s)     AS balance
                FROM %(table_references)s
                JOIN account_partial_reconcile partial
                    ON account_move_line.id = partial.debit_move_id OR account_move_line.id = partial.credit_move_id
                JOIN account_move_line aml_with_partner ON
                    (aml_with_partner.id = partial.debit_move_id OR aml_with_partner.id = partial.credit_move_id)
                    AND aml_with_partner.partner_id IS NOT NULL
                %(currency_table_join)s
                WHERE partial.max_date <= %(date_to)s AND %(search_condition)s
                    AND account_move_line.partner_id IS NULL
                    %(partner_id_constraint)s
                GROUP BY aml_with_partner.partner_id
                """,
                    column_group_key=column_group_key,
                    debit_select=report._currency_table_apply_rate(
                        SQL(
                            "CASE WHEN aml_with_partner.balance > 0 THEN 0 ELSE partial.amount END"
                        )
                    ),
                    credit_select=report._currency_table_apply_rate(
                        SQL(
                            "CASE WHEN aml_with_partner.balance < 0 THEN 0 ELSE partial.amount END"
                        )
                    ),
                    balance_select=report._currency_table_apply_rate(
                        SQL("-SIGN(aml_with_partner.balance) * partial.amount")
                    ),
                    table_references=query.from_clause,
                    currency_table_join=report._currency_table_aml_join(
                        column_group_options, aml_alias=SQL("aml_with_partner")
                    ),
                    date_to=column_group_options["date"]["date_to"],
                    search_condition=query.where_clause,
                    partner_id_constraint=SQL(
                        " AND aml_with_partner.partner_id = ANY(%s)", list(partner_ids)
                    )
                    if partner_ids
                    else SQL(""),
                )
            )

        return SQL(" UNION ALL ").join(queries)

    @_debug.perf.timed
    def _report_expand_unfoldable_line_partner_ledger(
        self,
        line_dict_id,
        groupby,
        options,
        progress,
        offset,
        unfold_all_batch_data=None,
    ):
        report = self.env["account.report"].browse(options["report_id"])
        markup, model, record_id = report._parse_line_id(line_dict_id)[-1]

        if model != "res.partner":
            raise UserError(
                _("Wrong ID for partner ledger line to expand: %s", line_dict_id)
            )

        prefix_groups_count = 0
        for markup, _model, _record_id in report._parse_line_id(line_dict_id):
            if isinstance(markup, dict) and "groupby_prefix_group" in markup:
                prefix_groups_count += 1
        level_shift = prefix_groups_count * 2

        lines = []

        _debug.logic(
            "partner_expand_mode",
            report=report,
            partner=record_id,
            offset=offset,
            prefix_groups=prefix_groups_count,
            initial_balance=offset == 0 and not options.get("hide_initial_balance"),
            batched=bool(unfold_all_batch_data),
        )
        # Get initial balance
        if offset == 0 and not options.get("hide_initial_balance"):
            if unfold_all_batch_data:
                init_balance_by_col_group = unfold_all_batch_data["initial_balances"][
                    record_id
                ]
            else:
                init_balance_by_col_group = self._prepare_initial_balance_values(
                    [record_id], options
                )[record_id]
            initial_balance_line = (
                report._get_partner_and_general_ledger_initial_balance_line(
                    options,
                    line_dict_id,
                    init_balance_by_col_group,
                    level_shift=level_shift,
                )
            )
            if initial_balance_line:
                for column in initial_balance_line["columns"]:
                    if column.get("expression_label") in ("debit", "credit"):
                        column["blank_if_zero"] = True
                lines.append(initial_balance_line)

                # For the first expansion of the line, the initial balance line gives the progress
                progress = self._init_load_more_progress(options, initial_balance_line)

        limit_to_load = (
            report.load_more_limit + 1
            if report.load_more_limit and options["export_mode"] != "print"
            else None
        )

        if unfold_all_batch_data:
            aml_results = unfold_all_batch_data["aml_values"][record_id]
        else:
            aml_results = self._prepare_aml_values(
                options, [record_id], offset=offset, limit=limit_to_load
            )[record_id]

        aml_report_lines, next_progress, treated_results_count, has_more = (
            self._get_partner_aml_report_lines(
                report,
                options,
                line_dict_id,
                aml_results,
                progress,
                offset,
                level_shift=level_shift,
            )
        )
        lines.extend(aml_report_lines)

        _debug.pipeline(
            "partner_expanded",
            report=report,
            partner=record_id,
            aml_results=len(aml_results),
            lines=len(lines),
            treated=treated_results_count,
            has_more=has_more,
            limit=limit_to_load,
        )
        return {
            "lines": lines,
            "offset_increment": treated_results_count,
            "has_more": has_more,
            "progress": next_progress,
        }

    def _init_load_more_progress(self, options, line_dict):
        return {
            column["column_group_key"]: line_col.get("no_format", 0)
            for column, line_col in zip(
                options["columns"], line_dict["columns"], strict=False
            )
            if column["expression_label"] == "balance"
        }

    def _get_partner_aml_report_lines(
        self,
        report,
        options,
        partner_line_id,
        aml_results,
        progress,
        offset=0,
        level_shift=0,
    ):
        lines = []
        has_more = False
        treated_results_count = 0
        next_progress = progress
        for result in aml_results:
            if self._is_report_limit_reached(report, options, treated_results_count):
                # We loaded one more than the limit on purpose: this way we know we need a "load more" line
                has_more = True
                break

            new_line = self._get_report_line_move_line(
                options, result, partner_line_id, next_progress, level_shift=level_shift
            )
            lines.append(new_line)
            next_progress = self._init_load_more_progress(options, new_line)
            treated_results_count += 1
        return lines, next_progress, treated_results_count, has_more

    def _is_report_limit_reached(self, report, options, results_count):
        return (
            options["export_mode"] != "print"
            and report.load_more_limit
            and results_count == report.load_more_limit
        )

    def _prepare_additional_aml_columns_sql(self):
        """Hook returning the additional fields to select in the partner ledger query."""
        # Meant to be overridden by other modules, e.g. SQL("account_move_line.date AS date,").
        return SQL()

    def _prepare_aml_order_by_sql(self):
        return SQL("account_move_line.date, account_move_line.id")

    @_debug.perf.timed
    def _prepare_aml_values(self, options, partner_ids, offset=0, limit=None):
        rslt = {partner_id: [] for partner_id in partner_ids}

        partner_ids_wo_none = [x for x in partner_ids if x]
        directly_linked_aml_partner_clauses = []
        indirectly_linked_aml_partner_clause = SQL(
            "aml_with_partner.partner_id IS NOT NULL"
        )
        if None in partner_ids:
            directly_linked_aml_partner_clauses.append(
                SQL("account_move_line.partner_id IS NULL")
            )
        if partner_ids_wo_none:
            directly_linked_aml_partner_clauses.append(
                SQL("account_move_line.partner_id = ANY(%s)", list(partner_ids_wo_none))
            )
            indirectly_linked_aml_partner_clause = SQL(
                "aml_with_partner.partner_id = ANY(%s)", list(partner_ids_wo_none)
            )
        directly_linked_aml_partner_clause = SQL(
            "(%s)", SQL(" OR ").join(directly_linked_aml_partner_clauses)
        )
        _debug.logic(
            "aml_partner_clauses",
            report=options.get("report_id"),
            partners=len(partner_ids_wo_none),
            unknown_partner=None in partner_ids,
            offset=offset,
            limit=limit,
        )

        queries = []
        journal_name = self.env["account.journal"]._field_to_sql("journal", "name")
        report = self.env.ref("account.partner_ledger_report")
        additional_columns = self._prepare_additional_aml_columns_sql()
        order_by = self._prepare_aml_order_by_sql()
        for column_group_key, group_options in report._split_options_per_column_group(
            options
        ).items():
            group_options.pop(
                "partner_ids", None
            )  # Handled by the partner_ids parameter, to support the case of misc entries (without partner) reconciled with invoices
            query = report._get_report_query(group_options, "strict_range")
            account_alias = query.left_join(
                lhs_alias="account_move_line",
                lhs_column="account_id",
                rhs_table="account_account",
                rhs_column="id",
                link="account_id",
            )
            account_code = self.env["account.account"]._field_to_sql(
                account_alias, "code", query
            )
            account_name = self.env["account.account"]._field_to_sql(
                account_alias, "name"
            )

            # For the move lines directly linked to this partner
            queries.append(
                SQL(
                    """
                    SELECT
                        account_move_line.id,
                        account_move_line.date_maturity,
                        account_move_line.name,
                        account_move_line.ref,
                        account_move_line.parent_state,
                        account_move_line.company_id,
                        account_move_line.account_id,
                        account_move_line.payment_id,
                        account_move_line.partner_id,
                        account_move_line.currency_id,
                        account_move_line.amount_currency,
                        account_move_line.matching_number,
                        account_move_line.no_followup,
                        %(additional_columns)s
                        COALESCE(account_move.invoice_date, account_move_line.date)      AS invoice_date,
                        %(debit_select)s                                                 AS debit,
                        %(credit_select)s                                                AS credit,
                        %(balance_select)s                                               AS amount,
                        %(balance_select)s                                               AS balance,
                        account_move.name                                                AS move_name,
                        account_move.move_type                                           AS move_type,
                        %(account_code)s                                                 AS account_code,
                        %(account_name)s                                                 AS account_name,
                        journal.code                                                     AS journal_code,
                        %(journal_name)s                                                 AS journal_name,
                        %(column_group_key)s                                             AS column_group_key,
                        'directly_linked_aml'                                            AS key,
                        0                                                                AS partial_id
                    FROM %(table_references)s
                    JOIN account_move ON account_move.id = account_move_line.move_id
                    %(currency_table_join)s
                    LEFT JOIN res_company company               ON company.id = account_move_line.company_id
                    LEFT JOIN res_partner partner               ON partner.id = account_move_line.partner_id
                    LEFT JOIN account_journal journal           ON journal.id = account_move_line.journal_id
                    WHERE %(search_condition)s AND %(directly_linked_aml_partner_clause)s
                    ORDER BY %(order_by)s
                    """,
                    additional_columns=additional_columns,
                    debit_select=report._currency_table_apply_rate(
                        SQL("account_move_line.debit")
                    ),
                    credit_select=report._currency_table_apply_rate(
                        SQL("account_move_line.credit")
                    ),
                    balance_select=report._currency_table_apply_rate(
                        SQL("account_move_line.balance")
                    ),
                    account_code=account_code,
                    account_name=account_name,
                    journal_name=journal_name,
                    column_group_key=column_group_key,
                    table_references=query.from_clause,
                    currency_table_join=report._currency_table_aml_join(group_options),
                    search_condition=query.where_clause,
                    directly_linked_aml_partner_clause=directly_linked_aml_partner_clause,
                    order_by=order_by,
                )
            )

            # For the move lines linked to no partner, but reconciled with this partner. They will appear in grey in the report
            queries.append(
                SQL(
                    """
                SELECT
                    account_move_line.id,
                    COALESCE(account_move_line.date_maturity, account_move_line.date) AS date_maturity,
                    account_move_line.name,
                    account_move_line.ref,
                    account_move_line.parent_state,
                    account_move_line.company_id,
                    account_move_line.account_id,
                    account_move_line.payment_id,
                    aml_with_partner.partner_id,
                    account_move_line.currency_id,
                    account_move_line.amount_currency,
                    account_move_line.matching_number,
                    account_move_line.no_followup,
                    %(additional_columns)s
                    COALESCE(account_move.invoice_date, account_move_line.date)      AS invoice_date,
                    %(debit_select)s                                                 AS debit,
                    %(credit_select)s                                                AS credit,
                    %(balance_select)s                                               AS amount,
                    %(balance_select)s                                               AS balance,
                    account_move.name                                                AS move_name,
                    account_move.move_type                                           AS move_type,
                    %(account_code)s                                                 AS account_code,
                    %(account_name)s                                                 AS account_name,
                    journal.code                                                     AS journal_code,
                    %(journal_name)s                                                 AS journal_name,
                    %(column_group_key)s                                             AS column_group_key,
                    'indirectly_linked_aml'                                          AS key,
                    partial.id                                                       AS partial_id
                FROM %(table_references)s
                    %(currency_table_join)s,
                    account_partial_reconcile partial,
                    account_move,
                    account_move_line aml_with_partner,
                    account_journal journal
                WHERE
                    (account_move_line.id = partial.debit_move_id OR account_move_line.id = partial.credit_move_id)
                    AND account_move_line.partner_id IS NULL
                    AND account_move.id = account_move_line.move_id
                    AND (aml_with_partner.id = partial.debit_move_id OR aml_with_partner.id = partial.credit_move_id)
                    AND %(indirectly_linked_aml_partner_clause)s
                    AND journal.id = account_move_line.journal_id
                    AND %(account_alias)s.id = account_move_line.account_id
                    AND %(search_condition)s
                    AND partial.max_date BETWEEN %(date_from)s AND %(date_to)s
                ORDER BY %(order_by)s
                """,
                    additional_columns=additional_columns,
                    debit_select=report._currency_table_apply_rate(
                        SQL(
                            "CASE WHEN aml_with_partner.balance > 0 THEN 0 ELSE partial.amount END"
                        )
                    ),
                    credit_select=report._currency_table_apply_rate(
                        SQL(
                            "CASE WHEN aml_with_partner.balance < 0 THEN 0 ELSE partial.amount END"
                        )
                    ),
                    balance_select=report._currency_table_apply_rate(
                        SQL("-SIGN(aml_with_partner.balance) * partial.amount")
                    ),
                    account_code=account_code,
                    account_name=account_name,
                    journal_name=journal_name,
                    column_group_key=column_group_key,
                    table_references=query.from_clause,
                    currency_table_join=report._currency_table_aml_join(group_options),
                    indirectly_linked_aml_partner_clause=indirectly_linked_aml_partner_clause,
                    account_alias=SQL.identifier(account_alias),
                    search_condition=query.where_clause,
                    date_from=group_options["date"]["date_from"],
                    date_to=group_options["date"]["date_to"],
                    order_by=order_by,
                )
            )

        query = SQL(" UNION ALL ").join(SQL("(%s)", query) for query in queries)

        if offset:
            query = SQL("%s OFFSET %s ", query, offset)

        if limit:
            query = SQL("%s LIMIT %s ", query, limit)

        self.env.cr.execute(query)
        for aml_result in self.env.cr.dictfetchall():
            if aml_result["key"] == "indirectly_linked_aml":
                # Append the line to the partner found through the reconciliation.
                if aml_result["partner_id"] in rslt:
                    rslt[aml_result["partner_id"]].append(aml_result)

                # Balance it with an additional line in the Unknown Partner section but having reversed amounts.
                if None in rslt:
                    rslt[None].append(
                        {
                            **aml_result,
                            "debit": aml_result["credit"],
                            "credit": aml_result["debit"],
                            "amount": aml_result["credit"] - aml_result["debit"],
                            "balance": -aml_result["balance"],
                        }
                    )
            else:
                rslt[aml_result["partner_id"]].append(aml_result)
        _debug.perf.count("aml_value_rows_fetched", rows=self.env.cr.rowcount)

        if _debug.pipeline.enabled:
            _debug.pipeline(
                "aml_values_fetched",
                report=options.get("report_id"),
                column_groups=len(queries) // 2,
                partners=len(rslt),
                partners_with_amls=sum(1 for amls in rslt.values() if amls),
                rows=sum(len(amls) for amls in rslt.values()),
            )
        return rslt

    ####################################################
    # COLUMNS/LINES
    ####################################################
    @_debug.perf.timed
    def _get_report_line_partners(
        self, options, partner, partner_values, level_shift=0
    ):
        company_currency = self.env.company.currency_id

        partner_data = next(iter(partner_values.values()))
        unfoldable = not company_currency.is_zero(
            partner_data.get("debit", 0) or partner_data.get("credit", 0)
        )
        column_values = []
        report = self.env["account.report"].browse(options["report_id"])
        for column in options["columns"]:
            col_expr_label = column["expression_label"]
            value = (
                None
                if options.get("hide_partner_totals")
                else partner_values[column["column_group_key"]].get(col_expr_label)
            )
            unfoldable = unfoldable or (
                col_expr_label in ("debit", "credit", "amount")
                and value
                and not company_currency.is_zero(value)
            )
            currency_id = partner_values[column["column_group_key"]].get("currency_id")
            currency = (
                self.env["res.currency"].browse(currency_id)
                if column["expression_label"] == "amount_currency" and currency_id
                else False
            )
            column_values.append(
                report._prepare_column_dict(
                    value, column, options=options, currency=currency
                )
            )

        line_id = (
            report._get_generic_line_id("res.partner", partner.id)
            if partner
            else report._get_generic_line_id("res.partner", None, markup="no_partner")
        )

        return {
            "id": line_id,
            "name": (partner is not None and (partner.name or "")[:128])
            or self._get_no_partner_line_label(),
            "columns": column_values,
            "level": 1 + level_shift,
            "trust": partner.trust if partner else None,
            "unfoldable": unfoldable,
            "unfolded": line_id in options["unfolded_lines"] or options["unfold_all"],
            "expand_function": "_report_expand_unfoldable_line_partner_ledger",
        }

    def _get_no_partner_line_label(self):
        return _("Unknown Partner")

    @api.model
    def _format_aml_name(self, line_name, move_ref, move_name=None):
        """Format the display of an account.move.line record. As its very costly to fetch the account.move.line
        records, only line_name, move_ref, move_name are passed as parameters to deal with sql-queries more easily.

        :param line_name:   The name of the account.move.line record.
        :param move_ref:    The reference of the account.move record.
        :param move_name:   The name of the account.move record.
        :return:            The formatted name of the account.move.line record.
        """
        return self.env["account.move.line"]._format_aml_name(
            line_name, move_ref, move_name=move_name
        )

    @_debug.perf.timed
    def _get_report_line_move_line(
        self,
        options,
        aml_query_result,
        partner_line_id,
        init_bal_by_col_group,
        level_shift=0,
    ):
        if aml_query_result["payment_id"]:
            caret_type = "account.payment"
        else:
            caret_type = "account.move.line"

        columns = []
        report = self.env["account.report"].browse(options["report_id"])
        for column in options["columns"]:
            col_expr_label = column["expression_label"]

            if col_expr_label not in aml_query_result:
                raise UserError(
                    _(
                        "The column '%s' is not available for this report.",
                        col_expr_label,
                    )
                )

            col_value = (
                aml_query_result[col_expr_label]
                if column["column_group_key"] == aml_query_result["column_group_key"]
                else None
            )

            if col_value is None:
                columns.append(report._prepare_column_dict(None, None))
            else:
                currency = False

                if col_expr_label == "balance":
                    col_value += init_bal_by_col_group[column["column_group_key"]]

                if col_expr_label == "amount_currency":
                    currency = self.env["res.currency"].browse(
                        aml_query_result["currency_id"]
                    )

                    if currency == self.env.company.currency_id:
                        col_value = ""

                columns.append(
                    report._prepare_column_dict(
                        col_value, column, options=options, currency=currency
                    )
                )

        return {
            "id": report._get_generic_line_id(
                "account.move.line",
                aml_query_result["id"],
                parent_line_id=partner_line_id,
                markup=aml_query_result["partial_id"],
            ),
            "parent_id": partner_line_id,
            "name": self._format_aml_name(
                aml_query_result["name"],
                aml_query_result["ref"],
                aml_query_result["move_name"],
            ),
            "columns": columns,
            "caret_options": caret_type,
            "level": 3 + level_shift,
            "is_draft": aml_query_result["parent_state"] == "draft",
            "no_followup": aml_query_result["no_followup"],
        }

    @_debug.perf.timed
    def _get_report_line_total(self, options, totals_by_column_group):
        column_values = []
        report = self.env["account.report"].browse(options["report_id"])
        for column in options["columns"]:
            col_value = totals_by_column_group[column["column_group_key"]].get(
                column["expression_label"]
            )
            column_values.append(
                report._prepare_column_dict(col_value, column, options=options)
            )

        return {
            "id": report._get_generic_line_id(None, None, markup="total"),
            "name": _("Total"),
            "level": 1,
            "columns": column_values,
        }

    @_debug.perf.timed
    def _get_report_send_recipients(self, options):
        partners = options.get("partner_ids", [])
        if not partners:
            report = self.env["account.report"].browse(options["report_id"])
            self.env.cr.execute(self._get_query_sums(report, options))
            partners = [
                row["groupby"] for row in self.env.cr.dictfetchall() if row["groupby"]
            ]
        return self.env["res.partner"].browse(partners)

    @_debug.perf.timed
    def open_journal_items(self, options, params):
        _debug.lifecycle("open_journal_items", records=self)
        params["view_ref"] = "account.view_account_move_line_list_grouped_partner"
        report = self.env["account.report"].browse(options["report_id"])
        action = report.open_journal_items(options=options, params=params)
        action.get("context", {}).update({"search_default_group_by_account": 0})
        return action
