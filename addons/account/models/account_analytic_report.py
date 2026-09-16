from odoo import _, api, fields, models
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog
from odoo.tools import SQL, Query

from odoo.addons.web.controllers.utils import clean_action

_debug = DebugLog(__name__)


class AccountReport(models.AbstractModel):
    _inherit = "account.report"

    filter_analytic_groupby = fields.Boolean(
        string="Analytic Group By",
        compute=lambda x: x._compute_report_option_filter("filter_analytic_groupby"),
        depends=["root_report_id", "section_main_report_ids"],
        store=True,
        readonly=False,
    )

    def _get_options_initializers_forced_sequence_map(self):
        """Force _init_options_analytic_groupby to run between the column headers and the columns."""
        sequence_map = super()._get_options_initializers_forced_sequence_map()
        # Sequenced between _init_options_column_headers and _init_options_columns, so the
        # column headers are already generated but the columns are not.
        sequence_map[self._init_options_analytic_groupby] = 995
        return sequence_map

    @_debug.perf.timed
    def _init_options_analytic_groupby(self, options, previous_options):
        if _debug.logic.enabled and not self.filter_analytic_groupby:
            _debug.logic("analytic_groupby_skipped", report=self, reason="filter_off")
        if not self.filter_analytic_groupby:
            return
        enable_analytic_accounts = self.env.user.has_group(
            "analytic.group_analytic_accounting"
        )
        _debug.logic(
            "analytic_groupby_access",
            report=self,
            allowed=enable_analytic_accounts,
        )
        if not enable_analytic_accounts:
            return

        options["display_analytic_groupby"] = True
        options["display_analytic_plan_groupby"] = True

        options["include_analytic_without_aml"] = previous_options.get(
            "include_analytic_without_aml", False
        )
        previous_analytic_accounts = previous_options.get(
            "analytic_accounts_groupby", []
        )
        analytic_account_ids = [int(x) for x in previous_analytic_accounts]
        selected_analytic_accounts = (
            self.env["account.analytic.account"]
            .with_context(active_test=False)
            .search([("id", "in", analytic_account_ids)])
        )
        options["analytic_accounts_groupby"] = selected_analytic_accounts.ids
        options["selected_analytic_account_groupby_names"] = (
            selected_analytic_accounts.mapped("name")
        )

        previous_analytic_plans = previous_options.get("analytic_plans_groupby", [])
        analytic_plan_ids = [int(x) for x in previous_analytic_plans]
        selected_analytic_plans = self.env["account.analytic.plan"].search(
            [("id", "in", analytic_plan_ids)]
        )
        options["analytic_plans_groupby"] = selected_analytic_plans.ids
        options["selected_analytic_plan_groupby_names"] = (
            selected_analytic_plans.mapped("name")
        )

        _debug.pipeline(
            "analytic_groupby_options_built",
            report=self,
            accounts=selected_analytic_accounts,
            plans=selected_analytic_plans,
            include_without_aml=options["include_analytic_without_aml"],
        )
        self._create_column_analytic(options)

    @_debug.perf.timed
    def _create_column_analytic(self, options):
        """Creates the analytic columns for each plan or account in the filters.

        :param dict options: report options, updated in place
        """
        # Each analytic header duplicates the previously built columns, the added ones
        # filtering on their own analytic accounts. analytic_groupby_option makes the report
        # query the shadowed table, whose analytic_distribution column holds a plain analytic
        # account id; hence the domain on it can use a simple comparison.
        analytic_headers = []
        plans = self.env["account.analytic.plan"].browse(
            options.get("analytic_plans_groupby")
        )
        accounts_in_plans = self.env["account.analytic.account"].search_fetch(
            [("plan_id", "child_of", plans.ids)], ["plan_id"]
        )
        for plan in plans:
            # child_of on the plan means "in this plan or one of its descendants",
            # which parent_path answers without a query per plan
            account_list = [
                account.id
                for account in accounts_in_plans
                if account.plan_id.parent_path.startswith(plan.parent_path)
            ]
            analytic_headers.append(
                {
                    "name": plan.name,
                    "forced_options": {
                        "analytic_groupby_option": True,
                        "analytic_accounts_list": tuple(
                            account_list
                        ),  # Analytic accounts used in the domain to filter the lines.
                        "analytic_plan_id": plan.id,
                    },
                }
            )

        accounts = self.env["account.analytic.account"].browse(
            options.get("analytic_accounts_groupby")
        )
        analytic_headers.extend(
            {
                "name": account.name,
                "forced_options": {
                    "analytic_groupby_option": True,
                    "analytic_accounts_list": (account.id,),
                },
            }
            for account in accounts
        )
        _debug.pipeline(
            "analytic_headers_built",
            report=self,
            plans=plans,
            accounts=accounts,
            headers=len(analytic_headers),
        )
        if analytic_headers:
            has_selected_budgets = any(
                budget for budget in options.get("budgets", []) if budget["selected"]
            )
            _debug.logic(
                "analytic_headers_placement",
                report=self,
                budgets=has_selected_budgets,
                same_level=has_selected_budgets
                and not options["selected_horizontal_group_id"],
            )

            if has_selected_budgets and not options["selected_horizontal_group_id"]:
                # if budget is selected, then analytic headers are placed on the same header level
                options["column_headers"][-1] = (
                    analytic_headers + options["column_headers"][-1]
                )
            else:
                # We add the analytic layer to the column_headers before creating the columns
                analytic_headers.append({"name": _("Total")})

                options["column_headers"] = [
                    *options["column_headers"],
                    analytic_headers,
                ]

    @api.model
    @_debug.perf.timed
    def _create_aml_shadowing_query_for_analytic_groupby(self):
        """Prepare a SQL subquery exposing account_analytic_line data under the account_move_line schema.

        :return: subquery usable in place of the `account_move_line` table
        :rtype: SQL
        """
        project_plan, other_plans = self.env["account.analytic.plan"]._get_all_plans()
        analytic_cols = SQL(", ").join(
            SQL('"account_analytic_line".%s', SQL.identifier(n._column_name()))
            for n in (project_plan + other_plans)
        )
        analytic_distribution_equivalent = SQL(
            "to_jsonb(UNNEST(ARRAY_REMOVE(ARRAY[%s], NULL)))", analytic_cols
        )

        change_equivalence_dict = {
            "balance": SQL("-amount"),
            "display_type": "product",
            "parent_state": "posted",
            "account_id": SQL.identifier("general_account_id"),
            "debit": SQL("CASE WHEN (amount < 0) THEN -amount else 0 END"),
            "credit": SQL("CASE WHEN (amount > 0) THEN amount else 0 END"),
            "analytic_distribution": analytic_distribution_equivalent,
            "date": SQL("account_analytic_line.date"),
            "company_id": SQL("account_analytic_line.company_id"),
        }

        all_stored_aml_fields = {
            field
            for field, attrs in self.env["account.move.line"].fields_get().items()
            if attrs["type"] not in ["many2many", "one2many"] and attrs.get("store")
        }

        # Fields with no analytic counterpart fall back to the joined account_move_line
        # column, which is NULL for analytic lines without a move line.
        for aml_field in all_stored_aml_fields:
            if aml_field not in change_equivalence_dict:
                change_equivalence_dict[aml_field] = SQL(
                    '"account_move_line".%s', SQL.identifier(aml_field)
                )

        _debug.pipeline(
            "analytic_shadowing_columns",
            plans=len(project_plan) + len(other_plans),
            stored_aml_fields=len(all_stored_aml_fields),
            mapped_fields=len(change_equivalence_dict),
        )
        _stored_fields, fields_to_insert = self.env[
            "account.move.line"
        ]._prepare_aml_shadowing_for_report(
            change_equivalence_dict, prefix_fields_to_insert=False
        )

        return SQL(
            """
            (
                SELECT %(fields_to_insert)s
                FROM account_analytic_line
                LEFT JOIN account_move_line
                    ON account_analytic_line.move_line_id = account_move_line.id
                WHERE
                    account_analytic_line.general_account_id IS NOT NULL
            )
        """,
            fields_to_insert=fields_to_insert,
        )

    @_debug.perf.timed
    def _get_report_query(self, options, date_scope, domain=None) -> Query:
        # Override to add the context key which will eventually trigger the shadowing of the table
        context_self = self.with_context(
            account_report_analytic_groupby=options.get("analytic_groupby_option")
        )

        # We add the domain filter for analytic_distribution here, as the search is not available
        query = super(AccountReport, context_self)._get_report_query(
            options, date_scope, domain
        )
        _debug.logic(
            "analytic_filter_mode",
            report=self,
            groupby=options.get("analytic_groupby_option"),
            filtered=bool(options.get("analytic_accounts")),
            shadowed="analytic_accounts_list" in options,
        )
        if options.get("analytic_accounts"):
            if "analytic_accounts_list" in options:
                # the table `account_move_line` will be shadowed by _create_aml_shadowing_query_for_analytic_groupby and thus analytic_distribution will be a single ID
                analytic_account_ids = tuple(
                    str(account_id) for account_id in options["analytic_accounts"]
                )
                query.add_where(
                    SQL(
                        """account_move_line.analytic_distribution = ANY(%s)""",
                        list(analytic_account_ids),
                    )
                )
            else:
                # Real `account_move_line` table so real JSON with percentage
                analytic_account_ids = [
                    [str(account_id) for account_id in options["analytic_accounts"]]
                ]
                query.add_where(
                    SQL(
                        "%s && %s",
                        analytic_account_ids,
                        self.env["account.move.line"]._query_analytic_accounts(),
                    )
                )

        return query

    @_debug.perf.timed
    def action_audit_cell(self, options, params):
        _debug.lifecycle("action_audit_cell", records=self)
        column_group_options = self._get_column_group_options(
            options, params["column_group_key"]
        )
        _debug.logic(
            "audit_cell_target",
            report=self,
            analytic_groupby=bool(column_group_options.get("analytic_groupby_option")),
            coverage=options.get("column_percent_comparison") == "analytic_coverage",
        )

        if not column_group_options.get("analytic_groupby_option"):
            action = super().action_audit_cell(options, params)
            if options.get("column_percent_comparison") == "analytic_coverage":
                context = action.get("context", {})
                context.update(
                    {
                        "selected_analytic_plan": options["analytic_plans_groupby"][0],
                    }
                )
                action["context"] = context
                view_id = (
                    self.env.ref(
                        "account.view_analytic_move_line_tree",
                        raise_if_not_found=False,
                    )
                    or False
                )
                if view_id:
                    action["views"] = [(view_id.id, "list")]
            return action
        else:
            # Start by getting the domain from the options.
            report_line = self.env["account.report.line"].browse(
                params["report_line_id"]
            )
            expression = report_line.expression_ids.filtered(
                lambda x: x.label == params["expression_label"]
            )
            line_domain = self._get_domain_audit_line(
                column_group_options, expression, params
            )
            # The line domain is made for move lines, so we need some postprocessing to have it work with analytic lines.
            domain = []
            AccountAnalyticLine = self.env["account.analytic.line"]
            for expression in line_domain:
                if (
                    len(expression) == 1
                ):  # For operators such as '&' or '|' we can juste add them again.
                    domain.append(expression)
                    continue

                field, operator, right_term = expression
                # On analytic lines, the account.account field is named general_account_id and not account_id.
                if field.split(".")[0] == "account_id":
                    field = field.replace("account_id", "general_account_id")
                    expression = [(field, operator, right_term)]
                elif field == "analytic_distribution":
                    if options.get("column_percent_comparison") == "analytic_coverage":
                        expression = [(1, "=", 1)]
                    else:
                        expression = [("auto_account_id", "in", right_term)]
                # For other fields not present in on the analytic line model, map them to get the info from the move_line.
                # Or ignore these conditions if there is no move lines.
                elif field.split(".")[0] not in AccountAnalyticLine._fields:
                    expression = [(f"move_line_id.{field}", operator, right_term)]
                    if options.get("include_analytic_without_aml"):
                        expression = Domain.OR(
                            [
                                [("move_line_id", "=", False)],
                                expression,
                            ]
                        )
                else:
                    expression = [expression]  # just for the extend
                domain.extend(expression)

            _debug.pipeline(
                "audit_cell_domain_translated",
                report=self,
                domain_terms=len(domain),
                include_without_aml=options.get("include_analytic_without_aml"),
            )
            action = clean_action(
                self.env.ref(
                    "analytic.account_analytic_line_action_entries"
                )._get_action_dict(),
                env=self.env,
            )
            action["domain"] = domain
            if options.get("column_percent_comparison") == "analytic_coverage":
                context = self.env["ir.actions.actions"]._eval_action_context(
                    action.get("context", "{}")
                )
                context.update(
                    {
                        "selected_analytic_plan": options["analytic_plans_groupby"][0],
                        "group_by": "move_line_id",
                    }
                )
                action["context"] = context
                action["display_name"] += (
                    " - " + options["selected_analytic_plan_groupby_names"][0]
                )
                view_id = (
                    self.env.ref(
                        "account.view_analytic_line_tree",
                        raise_if_not_found=False,
                    )
                    or False
                )
                if view_id:
                    action["views"] = [(view_id.id, "list")]

            return action

    @api.model
    def _get_domain_options_journals(self, options):
        domain = super()._get_domain_options_journals(options)
        # Add False to the domain in order to select lines without journals for analytics columns.
        if options.get("include_analytic_without_aml"):
            domain |= Domain("journal_id", "=", False)
        return domain

    def _get_domain_options(self, options, date_scope):
        self.check_singleton()
        domain = super()._get_domain_options(options, date_scope)

        # Get the analytic accounts that we need to filter on from the options and add a domain for them.
        if "analytic_accounts_list" in options:
            domain &= Domain(
                "analytic_distribution", "in", options.get("analytic_accounts_list", [])
            )

        return domain


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"
    _search_visibility_fields = ()

    @api.model
    @_debug.perf.timed
    def _search(self, *args, **kwargs):
        """Shadow the account_move_line table with analytic data when a report needs analytic columns."""
        # Done here so every query built for the report transparently reads the analytic
        # subquery instead of the real table, without touching each computation.
        query = super()._search(*args, **kwargs)
        if self.env.context.get(
            "account_report_analytic_groupby"
        ) and not self.env.context.get("account_report_cash_basis"):
            query._tables["account_move_line"] = self.env[
                "account.report"
            ]._create_aml_shadowing_query_for_analytic_groupby()
        return query
