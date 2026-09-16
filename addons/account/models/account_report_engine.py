import datetime
import io
import logging
import re
import zipfile
from ast import literal_eval
from collections import defaultdict
from collections.abc import Collection

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Command, Domain
from odoo.libs.debug_log import DebugLog
from odoo.tools import SQL, LazyTranslate, date_utils
from odoo.tools.misc import format_date

from odoo.addons.base.models.mixin_catalog import name_uniq_index

_lt = LazyTranslate(__name__)
_logger = logging.getLogger(__name__)

_debug = DebugLog(__name__)

ACCOUNT_CODES_ENGINE_TAG_ID_PREFIX_REGEX = re.compile(
    r"tag\(((?P<id>\d+)|(?P<ref>\w+\.\w+))\)"
)

# Performance optimisation: those engines always will receive None as their next_groupby, allowing more efficient batching.
NO_NEXT_GROUPBY_ENGINES = {"tax_tags", "account_codes"}

NUMBER_FIGURE_TYPES = ("float", "integer", "monetary", "percentage")

LINE_ID_HIERARCHY_DELIMITER = "|"

CURRENCIES_USING_LAKH = {"AFN", "BDT", "INR", "MMK", "NPR", "PKR", "LKR"}

UNDISTR_LINE_NAME = _lt("Result Brought Forward")


class AccountReportAnnotation(models.Model):
    _name = "account.report.annotation"
    _description = "Account Report Annotation"

    # This field is a OneToOne to a mail.message.
    message_id = fields.Many2one(
        comodel_name="mail.message",
        required=True,
    )
    date = fields.Date(
        required=True,
        help="Date considered as annotated by the annotation.",
    )


class AccountReport(models.Model):
    _inherit = "account.report"

    horizontal_group_ids = fields.Many2many(
        comodel_name="account.report.horizontal.group",
        string="Horizontal Groups",
    )
    return_type_ids = fields.One2many(
        comodel_name="account.return.type",
        inverse_name="report_id",
        string="Return Types",
    )

    # Those fields allow case-by-case fine-tuning of the engine, for custom reports.
    custom_handler_model_id = fields.Many2one(comodel_name="ir.model")
    custom_handler_model_name = fields.Char(
        related="custom_handler_model_id.model",
        string="Custom Handler Model Name",
    )

    # Account Coverage Report
    is_account_coverage_report_available = fields.Boolean(
        compute="_compute_is_account_coverage_report_available"
    )

    # Fields used for send reports by cron
    send_and_print_values = fields.Json(copy=False)

    # Account Audit Status
    allow_account_audit_status_on_lines = fields.Boolean(
        compute=lambda x: x._compute_report_option_filter(
            "allow_account_audit_status_on_lines"
        ),
        depends=["root_report_id"],
        precompute=True,
        store=True,
        readonly=False,
    )

    @api.constrains("custom_handler_model_id")
    @_debug.perf.timed
    def _check_custom_handler_model_id(self):
        for report in self:
            if report.custom_handler_model_id:
                custom_handler_model = self.env.registry[
                    "account.report.custom.handler"
                ]
                current_model = self.env[report.custom_handler_model_name]
                if not isinstance(current_model, custom_handler_model):
                    raise ValidationError(
                        _(
                            "Field 'Custom Handler Model' can only reference records inheriting from [%s].",
                            custom_handler_model._name,
                        )
                    )

    @_debug.perf.timed
    def unlink(self):
        _debug.lifecycle("unlink", unlink=self)
        for report in self:
            action, menuitem = report._get_existing_menuitem()
            menuitem.unlink()
            action.unlink()
        return super().unlink()

    @_debug.perf.timed
    def write(self, vals):
        _debug.lifecycle("write", records=self, fields=sorted(vals))
        if "active" in vals:
            reports = {r.id: r.name for r in self}
            actions = (
                self.env["ir.actions.client"]
                .sudo()
                .search(
                    [
                        ("name", "in", list(reports.values())),
                        ("tag", "=", "account_report"),
                    ]
                )
                .filtered(
                    lambda act: (
                        (
                            self.env["ir.actions.actions"]
                            ._eval_action_context(act.context)
                            .get("report_id"),
                            act.name,
                        )
                        in reports.items()
                    )
                )
            )
            self.env["ir.ui.menu"].sudo().search(
                [
                    ("active", "=", not vals["active"]),
                    (
                        "action",
                        "in",
                        [f"ir.actions.client,{action.id}" for action in actions],
                    ),
                ]
            ).active = vals["active"]
            _debug.logic(
                "menus_active_synced",
                records=self,
                actions=actions,
                active=vals.get("active"),
            )
        return super().write(vals)

    @api.model_create_multi
    @_debug.perf.timed
    def create(self, vals_list):
        if _debug.lifecycle.enabled:
            _debug.lifecycle(
                "create",
                model=self._name,
                count=len(vals_list),
                fields=sorted({key for vals in vals_list for key in vals}),
            )
        reports = super().create(vals_list)

        reports_by_impacted_field = {}
        for report, impacted_fields in zip(reports, vals_list, strict=False):
            for field_name in impacted_fields:
                reports_by_impacted_field.setdefault(
                    field_name, self.env["account.report"]
                )
                reports_by_impacted_field[field_name] += report

        if root_annual_statements := self.env.ref(
            "account.annual_statements", raise_if_not_found=False
        ):
            asr_section_reports = reports.filtered_domain(
                self._get_domain_asr_sections(root_annual_statements)
            )
            _debug.logic(
                "asr_sections_detected",
                reports=reports,
                asr_section_reports=asr_section_reports,
            )

            if asr_section_reports:
                # When the report needs to be added to the annual statement, the computation of some of its filters
                # might be skipped (because it's linked to a single composite report). Make sure we compute those
                # filters once before setting the link to the composite report.
                for name, field in asr_section_reports._fields.items():
                    if (
                        field._depends
                        and "section_main_report_ids" in field._depends
                        and field.store
                    ):
                        # We then need to recompute the fields on the reports not setting it in the create (all the filters are also editable)
                        reports_to_recompute = reports - reports_by_impacted_field.get(
                            name, self.env["account.report"]
                        )
                        if reports_to_recompute:
                            _debug.logic(
                                "asr_filter_recomputed",
                                field=name,
                                reports=reports_to_recompute,
                            )
                            self.env.add_to_compute(field, reports_to_recompute)
                            reports_to_recompute._recompute_field(field)

            asr_section_reports._link_annual_statements(root_annual_statements)
        return reports

    def _get_domain_asr_sections(self, root_annual_statements):
        """Return the domain filtering which reports may be a section of an annual statements report."""
        return [
            ("root_report_id", "in", root_annual_statements.section_report_ids.ids),
            (
                "availability_condition",
                "!=",
                "always",
            ),  # the report has to be localized
        ]

    @_debug.perf.timed
    def _link_annual_statements(self, root_annual_statements):
        Report = self.env["account.report"].with_context(active_test=False)
        existing_statements = Report.search(
            [
                ("root_report_id", "=", root_annual_statements.id),
                ("country_id", "in", [*self.country_id.ids, False]),
                ("chart_template", "in", list(set(self.mapped("chart_template")))),
            ]
        ).grouped(lambda report: (report.country_id, report.chart_template))
        for asr_section_report in self:
            annual_statements = existing_statements.get(
                (asr_section_report.country_id, asr_section_report.chart_template),
                self.env["account.report"],
            )
            if not annual_statements:
                annual_statements = Report.create(
                    {
                        "name": _("Annual Statements"),
                        "root_report_id": root_annual_statements.id,
                        "country_id": asr_section_report.country_id.id,
                        "use_sections": True,
                        "chart_template": asr_section_report.chart_template,
                        "availability_condition": asr_section_report.availability_condition,
                        "section_report_ids": [
                            Command.set(root_annual_statements.section_report_ids.ids)
                        ],
                    }
                )
                _debug.logic(
                    "annual_statements_created",
                    report=asr_section_report,
                    annual_statements=annual_statements,
                )

            annual_statements.section_report_ids -= asr_section_report.root_report_id

            if asr_section_report.use_sections:
                annual_statements.section_report_ids += (
                    asr_section_report.section_report_ids
                )
            else:
                annual_statements.section_report_ids += asr_section_report
                asr_section_report.sequence = asr_section_report.root_report_id.sequence
            _debug.logic(
                "annual_statements_linked",
                report=asr_section_report,
                annual_statements=annual_statements,
                use_sections=asr_section_report.use_sections,
            )

    ####################################################
    # CRON
    ####################################################

    ####################################################
    # MENU MANAGEMENT
    ####################################################

    ####################################################
    # OPTIONS: journals
    ####################################################

    ####################################################
    # OPTIONS: date + comparison
    ####################################################

    ####################################################
    # OPTIONS: analytic filter
    ####################################################

    ####################################################
    # OPTIONS: partners
    ####################################################

    ####################################################
    # OPTIONS: all_entries
    ####################################################

    ####################################################
    # OPTIONS: account_type
    ####################################################

    ACCOUNT_TYPE_FILTER_DOMAINS = {
        "trade_receivable": (False, "asset_receivable"),
        "trade_payable": (False, "liability_payable"),
        "non_trade_receivable": (True, "asset_receivable"),
        "non_trade_payable": (True, "liability_payable"),
    }

    ####################################################
    # OPTIONS: order column
    ####################################################

    ####################################################
    # OPTIONS: hierarchy
    ####################################################

    ####################################################
    # OPTIONS: prefix groups threshold
    ####################################################

    ####################################################
    # OPTIONS: MULTI COMPANY
    ####################################################

    def _init_currency_table(self, options):
        """Creates the currency table temporary table if necessary, using the provided options to compute its periods.
        This function should always be called before any query invovlving the currency table is run.
        """
        if options["currency_table"]["type"] != "monocurrency":
            companies = self.env["res.company"].browse(
                self.get_report_company_ids(options)
            )

            self.env["res.currency"]._create_currency_table(
                companies,
                [
                    (period_key, period["from"], period["to"])
                    for period_key, period in options["currency_table"][
                        "periods"
                    ].items()
                ],
                use_cta_rates=options["currency_table"]["type"] == "cta",
            )

    ####################################################
    # OPTIONS: COLUMN HEADERS
    ####################################################

    ####################################################
    # OPTIONS: BUTTONS
    ####################################################

    def _get_variants(self, report_id):
        source_report = self.env["account.report"].browse(report_id)
        if source_report.root_report_id:
            # We need to get the root report in order to get all variants
            source_report = source_report.root_report_id
        return (
            source_report
            + source_report.with_context(active_test=False).variant_report_ids
        )

    ####################################################
    # OPTIONS: CORE
    ####################################################

    ####################################################
    # QUERIES
    ####################################################

    @_debug.perf.timed
    def _create_aml_shadowing_query_for_budget(self, options):
        _stored_fields, fields_to_insert = self.env[
            "account.move.line"
        ]._prepare_aml_shadowing_for_report(
            {
                "id": SQL.identifier("id"),
                "balance": SQL.identifier("amount"),
                "company_id": self.env.company.id,
                "parent_state": "posted",
                "date": SQL.identifier("date"),
                "account_id": SQL.identifier("account_id"),
                "debit": SQL("CASE WHEN (amount > 0) THEN amount else 0 END"),
                "credit": SQL("CASE WHEN (amount < 0) THEN -amount else 0 END"),
            },
            prefix_fields_to_insert=False,
        )

        available_budget_ids = tuple(
            budget_option["id"] for budget_option in options["budgets"]
        )
        queries = [
            SQL(
                """
                SELECT %(fields_to_insert)s, budget_id
                FROM account_report_budget_item
                WHERE budget_id IN %(available_budget_ids)s
            """,
                fields_to_insert=fields_to_insert,
                available_budget_ids=available_budget_ids,
            )
        ]

        if options.get("show_all_accounts"):
            _stored_fields, fields_to_insert = self.env[
                "account.move.line"
            ]._prepare_aml_shadowing_for_report(
                {
                    # Using nextval will consume a sequence number, we decide to do it to avoid comparing apples and oranges
                    "id": SQL("(SELECT nextval('account_report_budget_item_id_seq'))"),
                    "balance": SQL("0"),
                    "company_id": self.env.company.id,
                    "parent_state": "posted",
                    "date": SQL("%s", options["date"]["date_from"]),
                    "account_id": SQL.identifier("accounts", "id"),
                    "debit": SQL("0"),
                    "credit": SQL("0"),
                },
                prefix_fields_to_insert=False,
            )
            accounts_subquery = (
                self.env["account.account"]
                .sudo()
                ._search(
                    [
                        ("company_ids", "in", self.get_report_company_ids(options)),
                        ("internal_group", "in", ["income", "expense"]),
                    ]
                )
            )

            queries.append(
                SQL(
                    """
                    SELECT %(fields_to_insert)s, budgets.id AS budget_id
                    FROM (%(accounts_subquery)s) AS accounts
                    CROSS JOIN (
                        SELECT id
                        FROM account_report_budget
                        WHERE id IN %(available_budget_ids)s
                    ) AS budgets
                """,
                    fields_to_insert=fields_to_insert,
                    accounts_subquery=accounts_subquery.select(),
                    available_budget_ids=available_budget_ids,
                )
            )

        _debug.logic(
            "budget_shadowing_built",
            report=self,
            budgets=len(available_budget_ids),
            show_all_accounts=bool(options.get("show_all_accounts")),
            queries=len(queries),
        )
        return SQL("(%s)", SQL(" UNION ALL ").join(queries))

    ####################################################
    # CARET OPTIONS MANAGEMENT
    ####################################################

    ####################################################
    # MISC
    ####################################################

    def _get_custom_handler_model(self):
        """Check whether the current report has a custom handler and if it does, return its name.
        Otherwise, try to fall back on the root report.
        """
        return (
            self.custom_handler_model_name
            or self.root_report_id.custom_handler_model_name
            or None
        )

    @_debug.perf.timed
    def _add_common_warnings(self, options, warnings):
        # Display a warning if we're displaying only the data of the current company, but it's also part of a tax unit
        if options.get("available_tax_units") and options["tax_unit"] == "company_only":
            warnings["account.common_warning_tax_unit"] = {}

        report_company_ids = self.get_report_company_ids(options)
        # The _get_accessible_branches function will return the accessible branches from the ones that are already selected,
        # and get_report_company_ids will return the current company and its branches (that are selected) with the same VAT
        # or tax unit. Therefore, we will display the warning only when the selected companies do not have the same VAT
        # and in the context of branches.
        if self.filter_multi_company == "tax_units" and any(
            accessible_branch.id not in report_company_ids
            for accessible_branch in self.env.company._get_accessible_branches()
        ):
            warnings["account.tax_report_warning_tax_id_selected_companies"] = {
                "alert_type": "warning"
            }

        # Check whether there are unposted entries for the selected period and partner or not (if the report allows it)
        if options.get("date") and options.get("all_entries") is not None:
            domain = (
                Domain(
                    self.env["account.move"]._check_company_domain(report_company_ids)
                )
                & Domain("state", "=", "draft")
                & Domain("date", "<=", options["date"]["date_to"])
            )
            if options.get("partner_ids"):
                domain &= (
                    Domain("partner_id", "in", options["partner_ids"])
                    | Domain("partner_shipping_id", "in", options["partner_ids"])
                    | Domain("commercial_partner_id", "in", options["partner_ids"])
                )
            if self.env["account.move"].search_count(domain, limit=1):
                warnings["account.common_warning_draft_in_period"] = {}
        if _debug.logic.enabled:
            _debug.logic(
                "common_warnings_checked",
                report=self,
                tax_unit=options.get("tax_unit"),
                draft_check=bool(
                    options.get("date") and options.get("all_entries") is not None
                ),
                warnings=sorted(warnings),
            )

    def _add_account_status_on_lines(self, lines, options):
        if not options["audit"]["id"]:
            _debug.logic("account_status_skipped", report=self, reason="no_audit")
            return lines

        accounts_to_search = set()
        for line in lines:
            model, id = self._get_model_info_from_id(line["id"])
            if model == "account.account":
                accounts_to_search.add(id)

        account_statuses = self.env["account.audit.account.status"].search_read(
            domain=[
                ("audit_id", "=", options["audit"]["id"]),
                ("account_id", "in", tuple(accounts_to_search)),
            ],
            fields=["id", "account_id", "audit_id", "status"],
        )
        _debug.perf.count(
            "account_statuses_fetched",
            rows=len(account_statuses),
            accounts=len(accounts_to_search),
        )

        account_statuses = {
            account_status["account_id"][0]: account_status
            for account_status in account_statuses
        }

        for line in lines:
            model, id = self._get_model_info_from_id(line["id"])
            if model == "account.account" and id in account_statuses:
                line["account_status"] = account_statuses[id]

        return lines

    def _update_line_names_for_consolidation(self, lines):
        """When grouping by account_code, in order to make the consolidation clearer, we add the account name in the context
        of the current company next to the account_code.
        """
        account_codes = []
        for line in lines:
            markup = self._get_markup(line["id"])
            if isinstance(markup, dict) and markup.get("groupby") == "account_code":
                account_codes.append(line["name"])
        if not account_codes:
            _debug.logic(
                "consolidation_names_skipped", report=self, reason="no_code_lines"
            )
            return

        account_code_to_account_name_dict = {
            account.code: account.name
            for account in self.env["account.account"].search(
                [
                    *self.env["account.account"]._check_company_domain(
                        self.env.company
                    ),
                    ("code", "in", account_codes),
                ]
            )
        }
        _debug.perf.count(
            "consolidation_accounts_fetched",
            rows=len(account_code_to_account_name_dict),
            codes=len(account_codes),
        )
        for line in lines:
            markup = self._get_markup(line["id"])
            if isinstance(markup, dict) and markup.get("groupby") == "account_code":
                account_code = line["name"]
                account_name = account_code_to_account_name_dict.get(account_code)
                if account_code and account_name:
                    line["name"] = f"{account_code} {account_name}"

    @_debug.perf.timed
    def _create_carryover_external_values(self, options):
        """Generates the account.report.external.value objects corresponding to this report's carryover under the provided options.

        In case of multicompany setup, we need to split the carryover per company, for ease of audit, and so that the carryover isn't broken when
        a company leaves a tax unit.

        We first generate the carryover for the wholy-aggregated report, so that we can see what final result we want.
        Indeed due to if_between, if_above and if_below conditions, each carryover might be different from the sum of the individidual companies'
        carryover values. To handle this case, we generate each company's carryover values separately, then do a carryover adjustment on the
        main company (main for tax units, first one selected else) in order to bring their total to the result we computed for the whole unit.
        """
        self.check_singleton()

        if len(options["column_groups"]) > 1:
            # The options must be forged in order to generate carryover values. Entering this conditions means this hasn't been done in the right way.
            raise UserError(
                _("Carryover can only be generated for a single column group.")
            )

        # Get the expressions to evaluate from the report
        carryover_expressions = self.line_ids.expression_ids.filtered(
            lambda x: x.label.startswith("_carryover_")
        )
        expressions_to_evaluate = carryover_expressions._expand_aggregations()

        # Expression totals for all selected companies
        expression_totals_per_col_group = (
            self._compute_expression_totals_for_each_column_group(
                expressions_to_evaluate, options
            )
        )
        expression_totals = expression_totals_per_col_group[
            next(iter(options["column_groups"].keys()))
        ]
        carryover_values = {
            expression: expression_totals[expression]["value"]
            for expression in carryover_expressions
        }
        _debug.pipeline(
            "carryover_totals_computed",
            report=self,
            carryover_expressions=carryover_expressions,
            expressions_to_evaluate=len(expressions_to_evaluate),
            companies=len(options["companies"]),
            split_per_company=len(options["companies"]) > 1,
        )

        if len(options["companies"]) == 1:
            company = self.env["res.company"].browse(
                self.get_report_company_ids(options)
            )
            self._create_carryover_for_company(
                options, company, dict(carryover_values.items())
            )
        else:
            multi_company_carryover_values_sum = defaultdict(lambda: 0)

            column_group_key = next(
                col_group_key for col_group_key in options["column_groups"]
            )
            for company_opt in options["companies"]:
                company = self.env["res.company"].browse(company_opt["id"])
                company_options = {
                    **options,
                    "companies": [{"id": company.id, "name": company.name}],
                }
                company_expressions_totals = (
                    self._compute_expression_totals_for_each_column_group(
                        expressions_to_evaluate, company_options
                    )
                )
                company_carryover_values = {
                    expression: company_expressions_totals[column_group_key][
                        expression
                    ]["value"]
                    for expression in carryover_expressions
                }
                self._create_carryover_for_company(
                    options, company, company_carryover_values
                )

                for carryover_expr, carryover_val in company_carryover_values.items():
                    multi_company_carryover_values_sum[carryover_expr] += carryover_val

            # Adjust multicompany amounts on main company
            main_company = self._get_sender_company_for_export(options)
            _debug.logic(
                "carryover_adjusted_on_main",
                report=self,
                main_company=main_company,
                expressions=carryover_expressions,
            )
            for expr in carryover_expressions:
                difference = (
                    carryover_values[expr] - multi_company_carryover_values_sum[expr]
                )
                self._create_carryover_for_company(
                    options,
                    main_company,
                    {expr: difference},
                    label=_("Carryover adjustment for tax unit"),
                )

    @api.model
    @_debug.perf.timed
    def _create_default_external_values(
        self, date_from, date_to, is_tax_report=False, company=None
    ):
        """Generates the account.report.external.value objects for the given dates.
        If is_tax_report, the values are only created for tax reports, else for all other reports.

        :param company: the company to seed the values for. The caller knows it -- the
            lock date wizard is opened on one company and may be opened on a company that
            is not the active one -- and `self.env.company` cannot; it is the default only
            so existing callers keep their behaviour.
        """
        if date_from >= date_to:
            # This can happen when setting the lock date back in the past
            _debug.logic(
                "default_values_skipped",
                reason="empty_period",
                date_from=date_from,
                date_to=date_to,
            )
            return

        options_dict = {}
        default_expr_by_report = defaultdict(list)
        tax_report = self.env.ref("account.generic_tax_report")
        company = company or self.env.company
        previous_options = {
            "date": {
                "date_from": date_from,
                "date_to": date_to,
            }
        }

        # Get all the default expressions from all reports
        default_expressions = self.env["account.report.expression"].search(
            [("label", "=like", "_default_%")]
        )
        # Options depend on the report, also we need to filter out tax report/other reports depending on is_tax_report
        # Hence we need to group the default expressions by report
        for expr in default_expressions:
            report = expr.report_line_id.report_id
            if is_tax_report == (
                tax_report
                in (
                    report
                    + report.root_report_id
                    + report.section_main_report_ids.root_report_id
                )
            ):
                if report not in options_dict:
                    options = report.with_context(
                        allowed_company_ids=[company.id]
                    ).get_options(previous_options)
                    options_dict[report] = options

                if report._is_available_for(options_dict[report]):
                    default_expr_by_report[report].append(expr)
        _debug.pipeline(
            "default_expressions_grouped",
            company=company,
            is_tax_report=is_tax_report,
            default_expressions=len(default_expressions),
            options_built=len(options_dict),
            reports=len(default_expr_by_report),
        )

        external_values_create_vals = []
        for report, report_default_expressions in default_expr_by_report.items():
            options = options_dict[report]

            target_by_default_expression = {}
            for default_expression in report_default_expressions:
                # The default expression needs to have the same label as the target external expression, e.g. '_default_balance'
                target_label = default_expression.label[len("_default_") :]
                target_by_default_expression[default_expression] = (
                    default_expression.report_line_id.expression_ids.filtered(
                        lambda x, target_label=target_label: x.label == target_label
                    )
                )
            # If the value has been created before/modified manually, we shouldn't create anything
            # and we won't recompute expression totals for them
            targets_with_value = {
                value.target_report_expression_id.id
                for value in self.env["account.report.external.value"].search(  # noqa: E8507 - one query per report, over every default expression at once
                    [
                        ("company_id", "=", company.id),
                        ("date", ">=", date_from),
                        ("date", "<=", date_to),
                        (
                            "target_report_expression_id",
                            "in",
                            [
                                target.id
                                for target in target_by_default_expression.values()
                            ],
                        ),
                    ]
                )
            }
            expressions_to_compute = {
                default_expression: target_external_expression.id
                for default_expression, target_external_expression in target_by_default_expression.items()
                if target_external_expression.id not in targets_with_value
            }
            _debug.logic(
                "default_values_to_compute",
                report=report,
                to_compute=len(expressions_to_compute),
                already_set=len(report_default_expressions)
                - len(expressions_to_compute),
            )

            # Evaluate the expressions for the report to fetch the value of the default expression
            # These have to be computed for each fiscal position
            expression_totals_per_col_group = report.with_company(
                company
            )._compute_expression_totals_for_each_column_group(
                expressions_to_compute, options, include_default_vals=True
            )
            expression_totals = expression_totals_per_col_group[
                next(iter(options["column_groups"].keys()))
            ]

            for expression, target_expression in expressions_to_compute.items():
                value = expression_totals[expression]["value"]
                field_name = (
                    "value" if isinstance(value, (int, float)) else "text_value"
                )
                external_values_create_vals.append(
                    {
                        "name": _("Manual value"),
                        field_name: expression_totals[expression]["value"],
                        "date": date_to,
                        "target_report_expression_id": target_expression,
                        "company_id": company.id,
                    }
                )

        _debug.pipeline(
            "default_values_prepared",
            company=company,
            count=len(external_values_create_vals),
        )
        self.env["account.report.external.value"].create(external_values_create_vals)

    @_debug.perf.timed
    def _create_carryover_for_company(
        self, options, company, carryover_per_expression, label=None
    ):
        date_from = options["date"]["date_from"]
        date_to = options["date"]["date_to"]

        external_values_create_vals = []
        for expression, carryover_value in carryover_per_expression.items():
            if not company.currency_id.is_zero(carryover_value):
                target_expression = expression._get_carryover_target_expression(options)
                external_values_create_vals.append(
                    {
                        "name": label
                        or _(
                            "Carryover from %(date_from)s to %(date_to)s",
                            date_from=format_date(self.env, date_from),
                            date_to=format_date(self.env, date_to),
                        ),
                        "value": carryover_value,
                        "date": date_to,
                        "target_report_expression_id": target_expression.id,
                        "carryover_origin_expression_label": expression.label,
                        "carryover_origin_report_line_id": expression.report_line_id.id,
                        "company_id": company.id,
                    }
                )

        self.env["account.report.external.value"].create(external_values_create_vals)

    @_debug.perf.timed
    def get_report_information(self, options):
        """Return the dictionary of information consumed by the AccountReport component."""
        self.check_singleton()
        self.env.flush_all()

        warnings = {}
        self._init_currency_table(options)
        with _debug.perf(
            "expression_totals",
            cr=self.env.cr,
            report=self,
            expression_ids_count=len(self.line_ids.expression_ids),
        ):
            all_column_groups_expression_totals = (
                self._compute_expression_totals_for_each_column_group(
                    self.line_ids.expression_ids, options, warnings=warnings
                )
            )

        # Convert all_column_groups_expression_totals to a json-friendly form (its keys are records)
        json_friendly_column_group_totals = self._get_json_friendly_column_group_totals(
            all_column_groups_expression_totals
        )

        with _debug.perf("_get_lines", cr=self.env.cr, report=self):
            lines = self._get_lines(
                options,
                all_column_groups_expression_totals=all_column_groups_expression_totals,
                warnings=warnings,
            )
        if _debug.pipeline.enabled:
            _debug.pipeline(
                "get_report_information",
                report=self,
                lines_count=len(lines),
                warnings=sorted(warnings),
            )
        return {
            "caret_options": self._get_caret_options(),
            "column_headers_render_data": self._prepare_column_headers_render_data(options),
            "column_groups_totals": json_friendly_column_group_totals,
            "context": self.env.context,
            "annotations": self.get_annotations(options, lines),
            "lines": lines,
            "warnings": warnings,
            "report": {
                "company_name": self.env.company.name,
                "company_country_code": self.env.company.country_code,
                "company_currency_symbol": self.env.company.currency_id.symbol,
                "name": self.name,
                "root_report_id": self.root_report_id,
            },
        }

    @api.readonly
    def get_report_information_readonly(self, options):
        """Readonly version of get_report_information, to be called from RPC when options['readonly_query'] is True,
        to better spread the load on servers when possible.
        """
        return self.get_report_information(options)

    @_debug.perf.timed
    def _is_available_for(self, options):
        """Called on report variants to know whether they are available for the provided options or not, computed for their root report,
        computing their availability_condition field.

        Only the options initialized by init_options with a more prioritary sequence than _init_options_variants are guaranteed to
        be in the provided options' dict (since this function is called by _init_options_variants, while resolving a call to get_options()).
        """
        companies = self.env["res.company"].browse(self.get_report_company_ids(options))

        reports = self.filtered(lambda r: r.availability_condition == "always")

        reports_by_country = self.filtered(
            lambda r: r.availability_condition == "country"
        )
        if reports_by_country:
            company_countries = companies.account_fiscal_country_id

            reports_foreign_vat = reports_by_country.filtered("allow_foreign_vat")
            reports_no_foreign_vat = reports_by_country - reports_foreign_vat

            fp_countries = self.env["res.country"]
            if reports_foreign_vat:
                foreign_vat_fpos = self.env["account.fiscal.position"].search(
                    [
                        ("foreign_vat", "!=", False),
                        ("company_id", "in", companies.ids),
                    ]
                )
                fp_countries |= foreign_vat_fpos.country_id

            reports += reports_by_country.filtered(lambda r: not r.country_id)
            reports += reports_no_foreign_vat.filtered(
                lambda r: r.country_id and r.country_id in company_countries
            )
            reports += reports_foreign_vat.filtered(
                lambda r: (
                    r.country_id and r.country_id in (company_countries | fp_countries)
                )
            )

        reports_by_coa = self.filtered(lambda r: r.availability_condition == "coa")
        if reports_by_coa:
            # When restricting to 'coa', the report is only available if all the companies have the same CoA as the report
            chart_templates = set(companies.mapped("chart_template"))
            reports += reports_by_coa.filtered(
                lambda r: r.chart_template in chart_templates
            )

        _debug.logic(
            "availability_resolved",
            reports=self,
            available=reports,
            by_country=reports_by_country,
            by_coa=reports_by_coa,
        )
        return reports

    def _format_lines_for_display(self, lines, options):
        """Apply report-specific formatting to the lines before printing.

        Overridden by reports needing it, such as the generic tax report for its carryover.

        :param lines: A list with the lines for this report.
        :param options: The options for this report.
        :return: The formatted list of lines
        """
        return lines

    def format_date(self, options, dt_filter="date"):
        date_from = fields.Date.from_string(options[dt_filter]["date_from"])
        date_to = fields.Date.from_string(options[dt_filter]["date_to"])
        return self._get_dates_period(date_from, date_to, options["date"]["mode"])[
            "string"
        ]

    @api.model
    def get_report_company_ids(self, options):
        """Returns a list containing the ids of the companies to be used to
        render this report, following the provided options.
        """
        return [comp_data["id"] for comp_data in options["companies"]]

    def _get_domain_unallocated_earnings_lines(self, fiscalyear_start, company_id=None):
        domain = [
            ("account_id.include_initial_balance", "=", False),
            ("date", "<", fiscalyear_start),
        ]
        if company_id:
            domain += [("company_id", "=", company_id)]
        return domain

    @_debug.perf.timed
    def _get_unallocated_earnings_lines(self, options, date_scope, auditable=False):
        def get_column_group_result(query_options, date_scope):
            query = self._get_report_query(
                query_options,
                date_scope,
                domain=self._get_domain_unallocated_earnings_lines(
                    self.env[self.custom_handler_model_name]._get_fiscalyear_start_date(
                        query_options
                    )
                ),
            )
            return self.env.execute_query_dict(
                SQL(
                    """
                SELECT account_move_line.company_id,
                       COALESCE(SUM(%(select_balance)s), 0.0) AS balance,
                       COALESCE(SUM(%(select_debit)s), 0.0) AS debit,
                       COALESCE(SUM(%(select_credit)s), 0.0) AS credit
                  FROM %(table_references)s
                       %(currency_table_join)s
                 WHERE %(search_condition)s
              GROUP BY account_move_line.company_id
                """,
                    select_balance=self._currency_table_apply_rate(
                        SQL("account_move_line.balance")
                    ),
                    select_debit=self._currency_table_apply_rate(
                        SQL("account_move_line.debit")
                    ),
                    select_credit=self._currency_table_apply_rate(
                        SQL("account_move_line.credit")
                    ),
                    table_references=query.from_clause,
                    currency_table_join=self._currency_table_aml_join(query_options),
                    search_condition=query.where_clause,
                )
            )

        if not self.custom_handler_model_id:
            _debug.logic("unallocated_earnings_no_handler", report=self)
            return []
        if (
            options.get("filter_search_bar")
            and options.get("filter_search_bar") not in str(UNDISTR_LINE_NAME).lower()
        ):
            _debug.logic(
                "unallocated_earnings_search_mismatch",
                report=self,
                filter_search_bar=options.get("filter_search_bar"),
            )
            return []

        unallocated_earnings_lines = defaultdict(dict)
        company_to_line_id = {}
        for (
            column_group_key,
            column_group_options,
        ) in self._split_options_per_column_group(options).items():
            # When groupby = id, the forced_domain is used to prevent displaying move lines that do not belong
            # to the period that is selected. In the unallocated earning lines, this is not needed.
            data = get_column_group_result(
                column_group_options
                | {
                    "forced_domain": [
                        domain
                        for domain in column_group_options["forced_domain"]
                        if domain != ("id", "=", False)
                    ],
                },
                date_scope,
            )
            _debug.perf.count(
                "unallocated_earnings_rows",
                rows=len(data),
                column_group_key=column_group_key,
            )

            for company_line in data:
                line_id = self._get_generic_line_id(
                    "res.company",
                    company_line["company_id"],
                    markup="undistributed_profits_losses",
                )
                company_to_line_id[company_line["company_id"]] = line_id
                unallocated_earnings_lines[column_group_key] |= {line_id: company_line}

        _debug.pipeline(
            "unallocated_earnings_fetched",
            report=self,
            date_scope=date_scope,
            column_groups=len(unallocated_earnings_lines),
            companies=len(company_to_line_id),
            auditable=auditable,
        )
        return [
            {
                "id": line_id,
                "name": (
                    str(UNDISTR_LINE_NAME)
                    if len(self.env.companies) == 1
                    else _(
                        "%(line_name)s - %(company)s",
                        line_name=UNDISTR_LINE_NAME,
                        company=self.env["res.company"].browse(company_id).name,
                    )
                ),
                "level": 1,
                "columns": [
                    self._prepare_column_dict(
                        unallocated_earnings_lines.get(column["column_group_key"], {})
                        .get(line_id, {})
                        .get(
                            column["expression_label"],
                            0.0 if column["figure_type"] == "monetary" else None,
                        ),
                        column,
                        options=options,
                    )
                    | {"auditable": auditable}
                    for column in options["columns"]
                ],
                "unfoldable": False,
                "unfolded": False,
                "caret_options": "undistributed_profits_losses",
            }
            for company_id, line_id in company_to_line_id.items()
        ]

    @_debug.perf.timed
    def _get_partner_and_general_ledger_initial_balance_line(
        self, options, parent_line_id, eval_dict, account_currency=None, level_shift=0
    ):
        """Helper to generate dynamic 'initial balance' lines, used by general ledger and partner ledger."""
        line_columns = []
        for column in options["columns"]:
            col_value = eval_dict[column["column_group_key"]].get(
                column["expression_label"]
            )
            col_expr_label = column["expression_label"]

            if col_value is None or (
                col_expr_label == "amount_currency" and not account_currency
            ):
                line_columns.append(self._prepare_column_dict(None, None))
            else:
                line_columns.append(
                    self._prepare_column_dict(
                        col_value,
                        column,
                        options=options,
                        currency=account_currency
                        if col_expr_label == "amount_currency"
                        else None,
                    )
                )

        # Display unfold & initial balance even when debit/credit column is hidden and the balance == 0
        if not any(
            isinstance(column.get("no_format"), (int, float))
            and column.get("expression_label") != "balance"
            for column in line_columns
        ):
            return None

        return {
            "id": self._get_generic_line_id(
                None, None, parent_line_id=parent_line_id, markup="initial"
            ),
            "name": _("Initial Balance"),
            "level": 3 + level_shift,
            "parent_id": parent_line_id,
            "columns": line_columns,
        }

    @_debug.perf.timed
    def _set_budget_column_comparisons(self, options, line):
        """Set the percentage values in the budget columns."""
        for col_index, col in enumerate(line["columns"]):
            col_group_data = options["column_groups"][col["column_group_key"]]
            if "budget_percentage" in col_group_data.get("forced_options", {}):
                budget_id = col_group_data["forced_options"]["budget_percentage"]
                date_key = col_group_data.get("forced_options", {}).get("date")
                if not date_key:
                    continue

                budget_base_col = None
                budget_amount_col = None
                for line_col in line["columns"]:
                    other_col_group_key = line_col["column_group_key"]
                    other_col_options = options["column_groups"][other_col_group_key]
                    if (
                        other_col_options.get("forced_options", {}).get("date")
                        == date_key
                    ):
                        if (
                            other_col_options.get("forced_options", {}).get(
                                "budget_base"
                            )
                            and line_col["figure_type"] == "monetary"
                        ):
                            budget_base_col = line_col
                        elif (
                            other_col_options.get("forced_options", {}).get(
                                "compute_budget"
                            )
                            == budget_id
                        ):
                            budget_amount_col = line_col
                if budget_base_col is None or budget_amount_col is None:
                    continue
                value = self._get_column_percent_comparison_data(
                    options,
                    budget_base_col["no_format"],
                    budget_amount_col["no_format"],
                    green_on_positive=budget_base_col["green_on_positive"],
                )
                comparison_column = self._prepare_column_dict(
                    value["name"],
                    {
                        **budget_amount_col,
                        "figure_type": "string",
                        "comparison_mode": value["mode"],
                    },
                )
                line["columns"][col_index] = comparison_column

    # ============ Accounts Coverage Debugging Tool - START ================
    # ============ Accounts Coverage Debugging Tool - END ================

    def show_error_branch_allowed(self, *args, **kwargs):
        raise UserError(
            _(
                "Please select the main company and its branches in the company selector to proceed."
            )
        )

    @api.model
    def _prepare_editable_cell_data(
        self, options, col_group_key, groupby_model, column_expression, column_value
    ):
        """Return the edit-popup payload for a cell the ledger allows editing in place, or None.

        The chassis knows a cell may be editable; which cells those are is a ledger question.
        Here it is a budget column grouped by account, for a user who may manage accounting.
        """
        editable_budget = groupby_model == "account.account" and options[
            "column_groups"
        ][col_group_key]["forced_options"].get("compute_budget")
        if not editable_budget or not self.env.user.has_group(
            "account.group_account_manager"
        ):
            return None

        return {
            "column_group_key": col_group_key,
            "target_expression_id": column_expression.id,
            "rounding": self.env.company.currency_id.decimal_places,
            "figure_type": "monetary",
            "column_value": self.env.company.currency_id.round(column_value)
            if column_value
            else column_value,
        }

    @_debug.perf.timed
    def _create_hierarchy(self, lines, options):
        """Compute the hierarchy based on account groups when the option is activated.

        The option is available only when there are account.group for the company.
        It should be called when before returning the lines to the client/templater.
        The lines are the result of _get_lines(). If there is a hierarchy, it is left
        untouched, only the lines related to an account.account are put in a hierarchy
        according to the account.group's and their prefixes.
        """
        if not lines:
            _debug.logic("hierarchy_skipped", report=self, reason="no_lines")
            return lines

        def get_account_group_hierarchy(account):
            # Create codes path in the hierarchy based on account.
            groups = self.env["account.group"]
            if account.group_id:
                group = account.group_id
                while group:
                    groups += group
                    group = group.parent_id
            return list(groups.sorted(reverse=True))

        def create_hierarchy_line(account_group, column_totals, level, parent_id):
            line_id = self._get_generic_line_id(
                "account.group",
                account_group.id if account_group else None,
                parent_line_id=parent_id,
            )
            unfolded = line_id in options.get("unfolded_lines") or options["unfold_all"]
            name = account_group.display_name if account_group else _("(No Group)")
            columns = []
            for col_total, column in zip(
                column_totals, options["columns"], strict=False
            ):
                if isinstance(col_total, tuple):
                    col_value, currency = col_total
                else:
                    col_value = col_total
                    currency = None

                columns.append(
                    self._prepare_column_dict(
                        col_value, column, options=options, currency=currency
                    )
                )

            return {
                "id": line_id,
                "name": name,
                "title_hover": name,
                "unfoldable": True,
                "unfolded": unfolded,
                "level": level,
                "parent_id": parent_id,
                "columns": columns,
            }

        def compute_group_totals(line, group=None):
            totals = []

            for total, column in zip(
                hierarchy[group]["totals"], line["columns"], strict=False
            ):
                if not isinstance(column.get("no_format"), (int, float)):
                    total = None

                if isinstance(total, (int, float)):
                    total += column["no_format"]
                elif isinstance(total, tuple):
                    if total == (None, None):
                        # Entering here only on first aggregation
                        amount = 0.0
                        currency = column.get("currency")
                    else:
                        amount, currency = total

                    if currency != column.get("currency"):
                        total = None
                    else:
                        total = (amount + column["no_format"], currency)

                totals.append(total)

            return totals

        def render_lines(
            account_groups, current_level, parent_line_id, skip_no_group=True
        ):
            to_treat = [
                (current_level, parent_line_id, group)
                for group in account_groups.sorted()
            ]

            if None in hierarchy and not skip_no_group:
                to_treat.append((current_level, parent_line_id, None))

            while to_treat:
                level_to_apply, parent_id, group = to_treat.pop(0)
                group_data = hierarchy[group]
                hierarchy_line = create_hierarchy_line(
                    group, group_data["totals"], level_to_apply, parent_id
                )
                new_lines.append(hierarchy_line)
                treated_child_groups = self.env["account.group"]

                for account_line in group_data["lines"]:
                    for child_group in group_data["child_groups"]:
                        if (
                            child_group not in treated_child_groups
                            and child_group["code_prefix_end"] < account_line["name"]
                        ):
                            render_lines(
                                child_group,
                                hierarchy_line["level"] + 1,
                                hierarchy_line["id"],
                            )
                            treated_child_groups += child_group

                    markup, model, account_id = self._parse_line_id(account_line["id"])[
                        -1
                    ]
                    account_line_id = self._get_generic_line_id(
                        model,
                        account_id,
                        markup=markup,
                        parent_line_id=hierarchy_line["id"],
                    )
                    account_line.update(
                        {
                            "id": account_line_id,
                            "parent_id": hierarchy_line["id"],
                            "level": hierarchy_line["level"] + 1,
                        }
                    )
                    new_lines.append(account_line)

                    for child_line in account_line_children_map[account_id]:
                        markup, model, res_id = self._parse_line_id(child_line["id"])[
                            -1
                        ]
                        child_line.update(
                            {
                                "id": self._get_generic_line_id(
                                    model,
                                    res_id,
                                    markup=markup,
                                    parent_line_id=account_line_id,
                                ),
                                "parent_id": account_line_id,
                                "level": account_line["level"] + 1,
                            }
                        )
                        new_lines.append(child_line)

                to_treat = [
                    (level_to_apply + 1, hierarchy_line["id"], child_group)
                    for child_group in group_data["child_groups"].sorted()
                    if child_group not in treated_child_groups
                ] + to_treat

        def create_hierarchy_dict():
            def create_totals():
                totals = []

                for column in options["columns"]:
                    default_value = None
                    if figure_type := column.get("figure_type"):
                        if figure_type == "float":
                            default_value = 0.0
                        elif figure_type == "integer":
                            default_value = 0
                        elif figure_type == "monetary":
                            default_value = (None, None)
                    totals.append(default_value)

                return totals

            return defaultdict(
                lambda: {
                    "lines": [],
                    "totals": create_totals(),
                    "child_groups": self.env["account.group"],
                }
            )

        # Precompute the account groups of the accounts in the report
        account_ids = []
        for line in lines:
            markup, res_model, model_id = self._parse_line_id(line["id"])[-1]
            if res_model == "account.account":
                account_ids.append(model_id)
        self.env["account.account"].browse(account_ids).fetch(["group_id"])
        _debug.pipeline(
            "hierarchy_input",
            report=self,
            lines=len(lines),
            account_lines=len(account_ids),
        )
        hierarchy_segments = 1  # debuglog

        new_lines, total_lines = [], []

        # root_line_id is the id of the parent line of the lines we want to render
        root_line_id = (
            self._prepare_parent_line_id(self._parse_line_id(lines[0]["id"])) or None
        )
        last_account_line_id = account_id = None
        current_level = 0
        account_line_children_map = defaultdict(list)
        account_groups = self.env["account.group"]
        root_account_groups = self.env["account.group"]
        hierarchy = create_hierarchy_dict()

        for line in lines:
            markup, res_model, model_id = self._parse_line_id(line["id"])[-1]

            # Account lines are used as the basis for the computation of the hierarchy.
            if res_model == "account.account":
                last_account_line_id = line["id"]
                current_level = line["level"]
                account_id = model_id
                account = self.env[res_model].browse(account_id)
                account_groups = get_account_group_hierarchy(account)

                if not account_groups:
                    hierarchy[None]["lines"].append(line)
                    hierarchy[None]["totals"] = compute_group_totals(line)
                else:
                    for i, group in enumerate(account_groups):
                        if i == 0:
                            hierarchy[group]["lines"].append(line)
                        if (
                            i == len(account_groups) - 1
                            and group not in root_account_groups
                        ):
                            root_account_groups += group
                        if (
                            group.parent_id
                            and group not in hierarchy[group.parent_id]["child_groups"]
                        ):
                            hierarchy[group.parent_id]["child_groups"] += group

                        hierarchy[group]["totals"] = compute_group_totals(
                            line, group=group
                        )

            # This is not an account line, so we check to see if it is a descendant of the last account line.
            # If so, it is added to the mapping of the lines that are related to this account.
            elif last_account_line_id and line.get("parent_id", "").startswith(
                last_account_line_id
            ):
                account_line_children_map[account_id].append(line)

            # This is a total line that is not linked to an account. It is saved in order to be added at the end.
            elif markup == "total":
                total_lines.append(line)

            # This line ends the scope of the current hierarchy and is (possibly) the root of a new hierarchy.
            # We render the current hierarchy and set up to build a new hierarchy
            else:
                render_lines(
                    root_account_groups,
                    current_level,
                    root_line_id,
                    skip_no_group=False,
                )

                new_lines.append(line)

                # Reset the hierarchy-related variables for a new hierarchy
                root_line_id = line["id"]
                last_account_line_id = account_id = None
                current_level = 0
                account_line_children_map = defaultdict(list)
                root_account_groups = self.env["account.group"]
                account_groups = self.env["account.group"]
                hierarchy = create_hierarchy_dict()
                hierarchy_segments += 1  # debuglog

        render_lines(
            root_account_groups, current_level, root_line_id, skip_no_group=False
        )

        _debug.pipeline(
            "hierarchy_built",
            report=self,
            segments=hierarchy_segments,
            new_lines=len(new_lines),
            total_lines=len(total_lines),
        )
        return new_lines + total_lines

    @_debug.perf.timed
    def _get_annotations_domain_date_from(self, options):
        if (
            options["date"]["filter"] in {"today", "custom"}
            and options["date"]["mode"] == "single"
        ):
            options_company_ids = [company["id"] for company in options["companies"]]
            root_companies_ids = (
                self.env["res.company"].browse(options_company_ids).root_id.ids
            )
            fiscal_year = self.env["account.fiscal.year"].search_fetch(
                [
                    ("company_id", "in", root_companies_ids),
                    ("date_from", "<=", options["date"]["date_to"]),
                    ("date_to", ">=", options["date"]["date_to"]),
                ],
                limit=1,
                field_names=["date_from"],
            )
            if fiscal_year:
                _debug.logic(
                    "date_from_fiscal_year",
                    report=self,
                    fiscal_year=fiscal_year,
                )
                return datetime.datetime.combine(
                    fiscal_year.date_from, datetime.time.min
                )

            period_date_from, _ = date_utils.get_fiscal_year(
                datetime.datetime.strptime(options["date"]["date_to"], "%Y-%m-%d"),
                day=self.env.company.fiscalyear_last_day,
                month=int(self.env.company.fiscalyear_last_month),
            )
            _debug.logic(
                "date_from_company_fiscal",
                report=self,
                date_from=period_date_from,
            )
            return period_date_from

        date_from = datetime.datetime.strptime(options["date"]["date_from"], "%Y-%m-%d")
        if options["date"]["period_type"] == "fiscalyear":
            period_date_from, _ = date_utils.get_fiscal_year(date_from)
        elif options["date"]["period_type"] in [
            "year",
            "quarter",
            "month",
            "week",
            "day",
            "hour",
        ]:
            period_date_from = date_utils.start_of(
                date_from, options["date"]["period_type"]
            )
        else:
            period_date_from = date_from
        _debug.logic(
            "date_from_period_type",
            report=self,
            period_type=options["date"]["period_type"],
            date_from=period_date_from,
        )
        return period_date_from

    @api.model
    def _postprocess_chatter_for_annotations(self, lines):
        """Add the chatter information on lines that can be annotated, so that it's then possible to open the right
        chatter for that line.
        """
        aml_id_to_report_lines_map = defaultdict(list)
        for line in lines:
            if line.get("unfoldable"):
                continue

            model, record_id = self._get_model_info_from_id(line.get("id"))
            if model == "account.move.line" and record_id is not None:
                aml_id_to_report_lines_map[record_id].append(line)
            elif model in self._get_annotatable_models():
                line["chatter"] = {
                    "model": model,
                    "id": record_id,
                }

        aml_id_to_account_move_id = {
            line["id"]: line["move_id"][0]
            for line in self.env["account.move.line"]
            .browse(aml_id_to_report_lines_map.keys())
            .read(["id", "move_id"])
        }
        _debug.pipeline(
            "annotation_chatter_mapped",
            report=self,
            lines=len(lines),
            amls=len(aml_id_to_account_move_id),
        )
        for aml_id, aml_lines in aml_id_to_report_lines_map.items():
            for line in aml_lines:
                line["chatter"] = {
                    "model": "account.move",
                    "id": aml_id_to_account_move_id[aml_id],
                }

    @api.model
    def _get_annotatable_models(self):
        return {"account.account", "account.move", "account.tax"}


class AccountReportLine(models.Model):
    _inherit = "account.report.line"

    display_custom_groupby_warning = fields.Boolean(
        compute="_compute_display_custom_groupby_warning"
    )

    def fetch(self, field_names: Collection[str] | None = None) -> None:
        super().fetch(field_names)
        # TODO remove in master: `account_or_unaff_id` falls back to `account_id`
        if (
            field_names is None
            or "groupby" in field_names
            or "user_groupby" in field_names
        ):
            for line in self:
                if "account_or_unaff_id" in (line.groupby or ""):
                    _debug.logic("legacy_groupby_rewritten", report_line=line)
                    line.groupby = line.groupby.replace(
                        "account_or_unaff_id", "account_id"
                    )
                if "account_or_unaff_id" in (line.user_groupby or ""):
                    _debug.logic("legacy_user_groupby_rewritten", report_line=line)
                    line.user_groupby = line.user_groupby.replace(
                        "account_or_unaff_id", "account_id"
                    )

    @api.depends("groupby", "user_groupby")
    def _compute_display_custom_groupby_warning(self):
        for line in self:
            line.display_custom_groupby_warning = (
                line.get_external_id()[line.id] and line.user_groupby != line.groupby
            )

    @api.constrains("groupby", "user_groupby")
    @_debug.perf.timed
    def _check_groupby(self):
        super()._check_groupby()
        for report_line in self:
            report_line.report_id._check_groupby_fields(report_line.user_groupby)
            report_line.report_id._check_groupby_fields(report_line.groupby)

    @_debug.perf.timed
    def _expand_groupby(
        self,
        line_dict_id,
        groupby,
        options,
        offset=0,
        limit=None,
        load_one_more=False,
        unfold_all_batch_data=None,
    ):
        """Expand function used to get the sublines of a groupby.
        groupby param is a string consisting of one or more coma-separated field names. Only the first one
        will be used for the expansion; if there are subsequent ones, the generated lines will themselves used them as
        their groupby value, and point to this expand_function, hence generating a hierarchy of groupby).
        """
        self.check_singleton()

        group_indent = 0
        line_id_list = self.report_id._parse_line_id(line_dict_id)

        # Parse groupby
        groupby_data = self._parse_groupby(options, groupby_to_expand=groupby)
        groupby_model = groupby_data["current_groupby_model"]
        next_groupby = groupby_data["next_groupby"]
        current_groupby = groupby_data["current_groupby"]
        custom_groupby_map = groupby_data["custom_groupby_map"]

        # If this line is a sub-groupby of groupby line (for example, when grouping by partner, id; the id line is a subgroup of partner),
        # we need to add the domain of the parent groupby criteria to the options
        prefix_groups_count = 0
        sub_groupby_domain = []
        full_sub_groupby_key_elements = []
        parent_groupby_nber = 0
        for markup, model, value in line_id_list:
            if isinstance(markup, dict) and "groupby" in markup:
                parent_groupby_nber += 1
                field_name = markup["groupby"]
                if field_name in custom_groupby_map:
                    sub_groupby_domain += custom_groupby_map[field_name][
                        "domain_builder"
                    ](value)
                else:
                    sub_groupby_domain.append((field_name, "=", value))
                full_sub_groupby_key_elements.append(f"{field_name}:{value}")
            elif isinstance(markup, dict) and "groupby_prefix_group" in markup:
                prefix_groups_count += 1

            if model == "account.group":
                group_indent += 1

        if sub_groupby_domain:
            forced_domain = options.get("forced_domain", []) + sub_groupby_domain
            options = {**options, "forced_domain": forced_domain}
        _debug.logic(
            "groupby_parsed",
            report=self.report_id,
            report_line=self,
            line_dict_id=line_dict_id,
            current_groupby=current_groupby,
            next_groupby=next_groupby,
            groupby_model=groupby_model,
            parent_groupbys=parent_groupby_nber,
            prefix_groups=prefix_groups_count,
            sub_groupby_domain_len=len(sub_groupby_domain),
        )

        # If the report transmitted custom_unfold_all_batch_data dictionary, use it
        full_sub_groupby_key = (
            f"[{self.id}]{','.join(full_sub_groupby_key_elements)}=>{current_groupby}"
        )

        cached_result = (unfold_all_batch_data or {}).get(full_sub_groupby_key)

        if cached_result is not None or options.get("test_unfold_all"):
            all_column_groups_expression_totals = cached_result
        else:
            all_column_groups_expression_totals = (
                self.report_id._compute_expression_totals_for_each_column_group(
                    self.expression_ids,
                    options,
                    groupby_to_expand=groupby,
                    offset=offset,
                    limit=limit + 1 if limit and load_one_more else limit,
                )
            )
        _debug.logic(
            "groupby_totals_source",
            report_line=self,
            source="unfold_all_batch"
            if cached_result is not None
            else ("test_unfold_all" if options.get("test_unfold_all") else "computed"),
            offset=offset,
            limit=limit,
            load_one_more=load_one_more,
        )

        # Put similar grouping keys from different totals/periods together, so that we don't display multiple
        # lines for the same grouping key

        figure_types_defaulting_to_0 = {"monetary", "percentage", "integer", "float"}

        default_value_per_expr_label = {
            col_opt["expression_label"]: 0
            if col_opt["figure_type"] in figure_types_defaulting_to_0
            else None
            for col_opt in options["columns"]
        }

        # Gather default value for each expression, in case it has no value for a given grouping key
        default_value_per_expression = {}
        for expression in self.expression_ids:
            if expression.figure_type:
                default_value = (
                    0
                    if expression.figure_type in figure_types_defaulting_to_0
                    else None
                )
            else:
                default_value = default_value_per_expr_label.get(expression.label)

            default_value_per_expression[expression] = {"value": default_value}

        # Build each group's result
        aggregated_group_totals = defaultdict(
            lambda: defaultdict(default_value_per_expression.copy)
        )
        for (
            column_group_key,
            expression_totals,
        ) in all_column_groups_expression_totals.items():
            for expression in self.expression_ids:
                sublines_info = expression_totals[expression]["sublines_info"]
                for grouping_key, result in expression_totals[expression]["value"]:
                    aggregated_group_totals[grouping_key][column_group_key][
                        expression
                    ] = {
                        "value": result,
                        "sublines_info": grouping_key in sublines_info,
                    }

        # Generate groupby lines
        group_lines_by_keys = {}
        for grouping_key, group_totals in aggregated_group_totals.items():
            # For this, we emulate a dict formatted like the result of _compute_expression_totals_for_each_column_group, so that we can call
            # _prepare_static_line_columns like on non-grouped lines
            line_id = self.report_id._get_generic_line_id(
                groupby_model,
                grouping_key,
                parent_line_id=line_dict_id,
                markup={"groupby": current_groupby},
            )
            caret_option = None
            if not next_groupby:
                caret_builder = custom_groupby_map.get(current_groupby, {}).get(
                    "caret_builder", {}
                )
                if caret_builder:
                    caret_option = caret_builder(grouping_key)
                else:
                    caret_option = groupby_model

            columns = self.report_id._prepare_static_line_columns(
                self, options, group_totals, groupby_model=groupby_model
            )
            has_children = bool(next_groupby) and any(
                col["has_sublines"] for col in columns
            )

            group_line_dict = {
                # 'name' key will be set later, so that we can browse all the records of this expansion at once (in case we're dealing with records)
                "id": line_id,
                "unfoldable": has_children,
                "unfolded": (has_children and next_groupby and options["unfold_all"])
                or line_id in options["unfolded_lines"],
                "groupby": next_groupby,
                "columns": columns,
                "level": self.hierarchy_level
                + 2 * (prefix_groups_count + parent_groupby_nber + 1)
                + (group_indent - 1),
                "parent_id": line_dict_id,
                "expand_function": "_report_expand_unfoldable_line_with_groupby"
                if next_groupby
                else None,
                "caret_options": caret_option,
            }

            if self.report_id.custom_handler_model_id:
                self.env[
                    self.report_id.custom_handler_model_name
                ]._custom_groupby_line_completer(
                    self.report_id, options, group_line_dict, current_groupby
                )

            # Growth comparison column.
            if options.get("column_percent_comparison") == "growth":
                compared_expression = self.expression_ids.filtered(
                    lambda expr, group_line_dict=group_line_dict: (
                        expr.label == group_line_dict["columns"][0]["expression_label"]
                    )
                )

                if options["comparison"]["period_order"] == "descending":
                    first_value, second_value = (
                        group_line_dict["columns"][0]["no_format"],
                        group_line_dict["columns"][1]["no_format"],
                    )
                else:
                    first_value, second_value = (
                        group_line_dict["columns"][1]["no_format"],
                        group_line_dict["columns"][0]["no_format"],
                    )

                group_line_dict["column_percent_comparison_data"] = (
                    self.report_id._get_column_percent_comparison_data(
                        options,
                        first_value,
                        second_value,
                        green_on_positive=compared_expression.green_on_positive,
                    )
                )
            # Manage budget comparison
            elif options.get("column_percent_comparison") == "budget":
                self.report_id._set_budget_column_comparisons(options, group_line_dict)
            elif options.get("column_percent_comparison") == "analytic_coverage":
                group_line_dict["column_percent_comparison_data"] = (
                    self.report_id._get_column_percent_comparison_data(
                        options,
                        group_line_dict["columns"][0]["no_format"],
                        group_line_dict["columns"][1]["no_format"],
                        green_on_positive=False,
                    )
                )
            group_lines_by_keys[grouping_key] = group_line_dict

        _debug.pipeline(
            "groupby_lines_built",
            report_line=self,
            groups=len(group_lines_by_keys),
            column_groups=len(all_column_groups_expression_totals),
            percent_comparison=options.get("column_percent_comparison"),
        )
        draft_entries = {}  # move state used order to color the line if it's draft
        # Sort grouping keys in the right order and generate line names
        keys_and_names_in_sequence = {}  # Order of this dict will matter

        custom_groupby_name_builder = custom_groupby_map.get(current_groupby, {}).get(
            "label_builder"
        )
        if groupby_model and not custom_groupby_name_builder:
            browsed_groupby_keys = self.env[groupby_model].browse(
                [key for key in group_lines_by_keys if key is not None]
            )

            out_of_sorting_record = None
            records_to_sort = browsed_groupby_keys
            if (
                browsed_groupby_keys
                and load_one_more
                and len(browsed_groupby_keys) >= limit
            ):
                out_of_sorting_record = browsed_groupby_keys[-1]
                records_to_sort = records_to_sort[:-1]

            for record in records_to_sort.with_context(active_test=False).sorted():
                keys_and_names_in_sequence[record.id] = record.display_name

                if groupby_model == "account.move.line":
                    draft_entries[record.id] = record.parent_state

                if groupby_model == "account.move":
                    draft_entries[record.id] = record.state

            if None in group_lines_by_keys:
                keys_and_names_in_sequence[None] = _("Unknown")

            if out_of_sorting_record:
                keys_and_names_in_sequence[out_of_sorting_record.id] = (
                    out_of_sorting_record.display_name
                )

        elif custom_groupby_name_builder:
            keys_and_names_in_sequence = custom_groupby_name_builder(
                group_lines_by_keys.keys()
            )  # Batch this when we have a label builder. This function also ensures the order of the name sequence
        else:
            for non_relational_key in sorted(
                group_lines_by_keys.keys(),
                key=lambda k: (k is None, isinstance(k, str), k),
            ):
                if non_relational_key is None:
                    keys_and_names_in_sequence[non_relational_key] = _("Undefined")
                else:
                    groupby_field = self.env["account.move.line"]._fields[
                        groupby_data["current_groupby"]
                    ]
                    if groupby_field.type == "selection":
                        selection_options = dict(
                            groupby_field._description_selection(self.env)
                        )
                        keys_and_names_in_sequence[non_relational_key] = (
                            selection_options.get(non_relational_key) or _("Undefined")
                        )
                    else:
                        keys_and_names_in_sequence[non_relational_key] = str(
                            non_relational_key
                        )
        _debug.logic(
            "group_names_strategy",
            report_line=self,
            strategy="label_builder"
            if custom_groupby_name_builder
            else ("records" if groupby_model else "raw_values"),
            named=len(keys_and_names_in_sequence),
        )

        # Build result: add a name to the groupby lines and handle totals below section for multi-level groupby
        group_lines = []
        for grouping_key, line_name in keys_and_names_in_sequence.items():
            group_line_dict = group_lines_by_keys[grouping_key]
            group_line_dict["name"] = line_name
            if draft_entries.get(grouping_key) == "draft":
                group_line_dict["is_draft"] = True
            group_lines.append(group_line_dict)

        if options.get("hierarchy"):
            group_lines = self.report_id._create_hierarchy(group_lines, options)

        _debug.pipeline(
            "groupby_expanded",
            report_line=self,
            group_lines=len(group_lines),
            drafts=len(draft_entries),
            hierarchy=bool(options.get("hierarchy")),
        )
        return group_lines

    @_debug.perf.timed
    def _parse_groupby(self, options, groupby_to_expand=None):
        """Retrieves the information needed to handle the groupby feature on the current line.

        :param groupby_to_expand:    A coma-separated string containing, in order, all the fields that are used in the groupby we're expanding.
                                     None if we're not expanding anything.

        :return: A dictionary with 4 keys:
            'current_groupby':       The name of the value to be used to retrieve the results of the current groupby we're
                                     expanding, or None if nothing is being expanded. That value can be either a field of account.move.line, or
                                     a custom groupby value defined in this report's custom handler's _get_custom_groupby_map function.

            'next_groupby':          The subsequent groupings to be applied after current_groupby, as a string of coma-separated values (again,
                                     either field names from account.move.line or a custom groupby defined on the handler).
                                     If no subsequent grouping exists, next_groupby will be None.

            'current_groupby_model': The model name corresponding to current_groupby, or None if current_groupby is None.

            'custom_groupby_map';    The groupby map, used to handle custom groupby values, as returned by the _get_custom_groupby_map function
                                     of the custom handler (by default, it will be an empty dict)

        Each expansion consumes the leftmost field of groupby_to_expand into current_groupby and
        leaves the remainder in next_groupby, which becomes the groupby_to_expand of the next level.
        """
        self.check_singleton()

        if groupby_to_expand:
            groupby_to_expand = groupby_to_expand.replace(" ", "")
            split_groupby = groupby_to_expand.split(",")
            current_groupby = split_groupby[0]
            next_groupby = (
                ",".join(split_groupby[1:]) if len(split_groupby) > 1 else None
            )
        else:
            current_groupby = None
            groupby = self._get_groupby(options)
            next_groupby = groupby.replace(" ", "") if groupby else None

        custom_handler_name = self.report_id._get_custom_handler_model()
        custom_groupby_map = (
            self.env[custom_handler_name]._get_custom_groupby_map()
            if custom_handler_name
            else {}
        )
        if current_groupby in custom_groupby_map:
            groupby_model = custom_groupby_map[current_groupby]["model"]
        elif current_groupby == "id":
            groupby_model = "account.move.line"
        elif current_groupby:
            groupby_model = (
                self.env["account.move.line"]._fields[current_groupby].comodel_name
            )
        else:
            groupby_model = None

        _debug.logic(
            "groupby_parsed",
            report_line=self,
            current_groupby=current_groupby,
            next_groupby=next_groupby,
            groupby_model=groupby_model,
            custom=current_groupby in custom_groupby_map,
        )
        return {
            "current_groupby": current_groupby,
            "next_groupby": next_groupby,
            "current_groupby_model": groupby_model,
            "custom_groupby_map": custom_groupby_map,
        }

    def _get_groupby(self, options):
        self.check_singleton()

        if options["export_mode"] == "file":
            return self.groupby

        groupby_lst = [
            groupby.strip() for groupby in (self.user_groupby or "").split(",")
        ]
        if options["consolidation"] and "account_id" in groupby_lst:
            index_account_id = groupby_lst.index("account_id")
            groupby_lst.insert(index_account_id, "account_code")
            return ",".join(groupby_lst)

        return self.user_groupby

    @_debug.perf.timed
    def action_reset_custom_groupby(self):
        _debug.lifecycle("action_reset_custom_groupby", records=self)
        self.check_singleton()
        self.user_groupby = self.groupby


class AccountReportExpression(models.Model):
    _inherit = "account.report.expression"

    @_debug.perf.timed
    def action_view_carryover_lines(self, options, column_group_key=None):
        _debug.lifecycle("action_view_carryover_lines", records=self)
        if column_group_key:
            options = self.report_line_id.report_id._get_column_group_options(
                options, column_group_key
            )

        date_from, date_to = self.report_line_id.report_id._get_date_bounds_info(
            options, self.date_scope
        )

        return {
            "type": "ir.actions.act_window",
            "name": _("Carryover lines for: %s", self.report_line_name),
            "res_model": "account.report.external.value",
            "views": [(False, "list")],
            "domain": [
                ("target_report_expression_id", "=", self.id),
                ("date", ">=", date_from),
                ("date", "<=", date_to),
            ],
        }


class AccountReportExternalValue(models.Model):
    _inherit = "account.report.external.value"

    @api.model_create_multi
    @_debug.perf.timed
    def create(self, vals_list):
        if _debug.lifecycle.enabled:
            _debug.lifecycle(
                "create",
                model=self._name,
                count=len(vals_list),
                fields=sorted({key for vals in vals_list for key in vals}),
            )
        records = super().create(vals_list)
        self._check_lock_date_violation(
            set(self._prepare_vals_to_check_for_lock_date(records))
        )
        return records

    @_debug.perf.timed
    def write(self, vals):
        # We need to build vals_to_check before the super() call because of the 'target_report_expression_id' field :
        # if the user tries to modify this specific field, it'll potentially change the linked report id, and so he can
        # bypass the lock dates from the original report (if it was a tax report for example)
        _debug.lifecycle("write", records=self, fields=sorted(vals))
        vals_to_check = set(self._prepare_vals_to_check_for_lock_date(self))
        res = super().write(vals)
        # Then we add the modified records
        vals_to_check.update(self._prepare_vals_to_check_for_lock_date(self))
        self._check_lock_date_violation(vals_to_check)
        return res

    @api.model
    def _prepare_vals_to_check_for_lock_date(self, records):
        """Yield one (is_tax, date, company) tuple per record, where:

        - is_tax (bool): whether the external value is linked to a tax report
        - date (date): the date to check the lock dates for
        - company (res.company): the company to check the lock dates for
        """
        generic_tax_report = self.env.ref("account.generic_tax_report")
        for external_value in records:
            report = external_value.target_report_expression_id.report_line_id.report_id
            yield (
                not self.env.context.get("ignore_tax_lock_date")
                and generic_tax_report
                in (
                    report
                    + report.root_report_id
                    + report.section_main_report_ids.root_report_id
                ),  # is tax
                external_value.date,  # date to check
                external_value.company_id,  # company
            )

    @_debug.perf.timed
    def _check_lock_date_violation(self, vals_to_check):
        """Raise if a company has a lock date after the date we want to create/write the values for.

        :param vals_to_check: a set of tuples like: `{(is_tax, date, company_id)}`
        """
        for is_tax, date, company_id in vals_to_check:
            violated_lock_dates = company_id._get_lock_date_violations(
                date,
                sale=False,
                purchase=False,
                tax=is_tax,
            )
            if violated_lock_dates:
                lock_date_names = [
                    company_id._fields[lock_date[1]].get_description(self.env)["string"]
                    for lock_date in violated_lock_dates
                ]
                lock_dates = "\n- " + "\n- ".join(lock_date_names)
                raise ValidationError(
                    _("You cannot update this value as it's locked by: %s", lock_dates)
                )


class AccountReportHorizontalGroup(models.Model):
    _name = "account.report.horizontal.group"
    _description = "Horizontal group for reports"

    name = fields.Char(
        translate=True,
        required=True,
    )
    rule_ids = fields.One2many(
        comodel_name="account.report.horizontal.group.rule",
        inverse_name="horizontal_group_id",
        string="Rules",
        required=True,
    )
    report_ids = fields.Many2many(
        comodel_name="account.report",
        string="Reports",
    )

    _name_src_uniq = name_uniq_index(
        message="A horizontal group with the same name already exists.",
    )

    def _get_header_levels_data(self):
        return [
            (rule.field_name, rule._get_matching_records()) for rule in self.rule_ids
        ]


class AccountReportHorizontalGroupRule(models.Model):
    _name = "account.report.horizontal.group.rule"
    _description = "Horizontal group rule for reports"

    def _selection_move_line_relational_fields(self):
        return [
            (aml_field["name"], aml_field["string"])
            for aml_field in self.env["account.move.line"].fields_get().values()
            if aml_field["type"] in ("many2one", "many2many")
        ]

    horizontal_group_id = fields.Many2one(
        comodel_name="account.report.horizontal.group",
        index=True,
        required=True,
    )
    domain = fields.Char(
        default="[]",
        required=True,
    )
    field_name = fields.Selection(
        selection="_selection_move_line_relational_fields",
        string="Field",
        required=True,
    )
    res_model_name = fields.Char(
        string="Model",
        compute="_compute_res_model_name",
    )

    @api.depends("field_name")
    def _compute_res_model_name(self):
        for record in self:
            if record.field_name:
                record.res_model_name = (
                    self.env["account.move.line"]
                    ._fields[record.field_name]
                    .comodel_name
                )
            else:
                record.res_model_name = None

    def _get_matching_records(self):
        self.check_singleton()
        model_name = self.env["account.move.line"]._fields[self.field_name].comodel_name
        domain = literal_eval(self.domain)
        return self.env[model_name].search(domain)


class AccountReportCustomHandler(models.AbstractModel):
    _name = "account.report.custom.handler"
    _description = "Account Report Custom Handler"

    # This abstract model allows case-by-case localized changes of behaviors of reports.
    # This is used for custom reports, for cases that cannot be supported by the standard engines.

    def _dynamic_lines_generator(
        self, report, options, all_column_groups_expression_totals, warnings=None
    ):
        """Generates lines dynamically for reports that require a custom processing which cannot be handled
        by regular report engines.
        :return:    A list of tuples [(sequence, line_dict), ...], where:
                    - sequence is the sequence to apply when rendering the line (can be mixed with static lines),
                    - line_dict is a dict containing all the line values.
        """
        return []

    def _caret_options_initializer(self):
        """Returns the caret options dict to be used when rendering this report,
        in the same format as the one used in _caret_options_initializer_default (defined on 'account.report').
        If the result is empty, the engine will use the default caret options.
        """
        return self.env["account.report"]._caret_options_initializer_default()

    def _custom_options_initializer(self, report, options, previous_options):
        """To be overridden to add report-specific _init_options... code to the report."""
        pass

    def _custom_line_postprocessor(self, report, options, lines):
        """Postprocesses the result of the report's _get_lines() before returning it."""
        return lines

    def _custom_groupby_line_completer(
        self, report, options, line_dict, current_groupby
    ):
        """Postprocesses the dict generated by the group_by_line, to customize its content."""

    def _custom_unfold_all_batch_data_generator(
        self, report, options, lines_to_expand_by_function
    ):
        """When using the 'unfold all' option, some reports might end up recomputing the same query for
        each line to unfold, leading to very inefficient computation. This function allows batching this computation,
        and returns a dictionary where all results are cached, for use in expansion functions.
        """
        return

    def _get_custom_groupby_map(self):
        """Allows the use of custom values in the groupby field of account.report.line, to use them in custom engines. Those custom
        values can be anything, and need to be properly handled by the custom engine using them. This allows adding support for grouping on
        something else than just the fields of account.move.line, which is the default.

        :return:    A dict, in the form {groupby_name: {'model': model, 'domain_builder': domain_builder}}, where:
                        - groupby_name is the custom value to use in groupby instead of one of aml's field names
                        - model: is a model name (a string), representing the model the value returned for this custom groupby targets.
                                 The model will be used to compute the display_name to show for each generated groupby line, in the UI.
                                 This value can be passed to None ; in such case, the raw value returned by the engine will be shown.
                        - domain_builder is a function to be called when expanding a groupby line generated by this custom groupby, to compute the
                                 domain to apply in order to restrict the computation to the content of this groupby line.
                                 This function must accept a single parameter, corresponding to the groupby value to compute the domain for.
                        - label_builder is a function to be called to compute a label for the groupby value, that will be shown as the line name
                                 in the UI. This ways, translatable labels and multi-values keys serialized to json can be fully supported.
                        - caret_builder is a function called with the grouping_key as parameter and that returns a custom caret identifier for this grouping key
        """
        return {}

    def _customize_warnings(
        self, report, options, all_column_groups_expression_totals, warnings
    ):
        """To be overridden to add report-specific warnings in the warnings dictionary.
        When a root report defines something in this function, its variants without any custom handler will also call the root report's
        _customize_warnings function. This can hence be used to share warnings between all variants.

        Should only be used when necessary, _dynamic_lines_generator is preferred.
        """

    def _get_line_columns(self, report, options, data):
        line_columns = []
        for column in options["columns"]:
            col_value = data[column["column_group_key"]].get(column["expression_label"])
            line_columns.append(
                report._prepare_column_dict(
                    col_value=col_value or "",
                    col_data=column,
                    options=options,
                )
            )
        return line_columns

    def _get_zip_export(
        self, file_name: str, files: Collection[tuple[str, str | bytes]]
    ) -> dict:
        with io.BytesIO() as buffer:
            with zipfile.ZipFile(
                buffer, "w", compression=zipfile.ZIP_DEFLATED
            ) as zip_file:
                for name, content in files:
                    zip_file.writestr(name, content)
            return {
                "file_name": file_name,
                "file_content": buffer.getvalue(),
                "file_type": "zip",
            }


class AccountReportFileDownloadException(Exception):
    def __init__(self, errors, content=None):
        super().__init__()
        self.errors = errors
        self.content = content
