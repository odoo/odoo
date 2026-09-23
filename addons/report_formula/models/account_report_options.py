import contextlib
import datetime

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, modules
from odoo.exceptions import UserError
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog
from odoo.tools import date_utils
from odoo.tools.misc import format_date

from .account_report import CURRENCIES_USING_LAKH

_debug = DebugLog(__name__)


class AccountReportOptions(models.Model):
    _inherit = "report.formula"

    def _normalize_date_filter(self, options, options_filter, period_date_to):
        return options_filter

    def _get_custom_period_bounds(
        self, options, options_filter, period_date_from, period_date_to, current
    ):
        return current

    def _convert_custom_period_filter(
        self, options, options_filter, date, period_date_to, date_to
    ):
        return options_filter

    def _finalize_custom_period_options(self, options, options_filter):
        return

    def _get_custom_period_name(self, period_type, date_from, date_to, options_return):
        return None

    def _get_shifted_custom_period(
        self, options, periods, return_period, period_type, mode, date_from
    ):
        return None

    def _get_custom_date_scope_bounds(self, options, date_scope, date_from, date_to):
        return date_from, date_to

    @_debug.perf.timed
    def _init_options_date(self, options, previous_options):
        """Initialize the 'date' options key.

        :param options:             The current report options to build.
        :param previous_options:    The previous options coming from another report.
        """
        date = previous_options.get("date", {})
        period_date_to = date.get("date_to")
        period_date_from = date.get("date_from")
        mode = date.get("mode")
        date_filter = date.get("filter", "custom")

        default_filter = self.default_opening_date_filter
        options_mode = "range" if self.filter_date_range else "single"
        date_from = date_to = period_type = False

        if mode == "single" and options_mode == "range":
            # 'single' date mode to 'range'.
            if date_filter:
                date_to = fields.Date.from_string(period_date_to or period_date_from)
                date_from = self._get_year_bounds(date_to)["date_from"]
                options_filter = "custom"
            else:
                options_filter = default_filter
        elif mode == "range" and options_mode == "single":
            # 'range' date mode to 'single'.
            if date_filter == "custom":
                date_to = fields.Date.from_string(period_date_to or period_date_from)
                date_from = date_utils.get_month(date_to)[0]
                options_filter = "custom"
            elif date_filter:
                options_filter = date_filter
            else:
                options_filter = default_filter
        elif (mode is None or mode == options_mode) and date:
            # Same date mode.
            if date_filter == "custom":
                if options_mode == "range":
                    date_from = fields.Date.from_string(period_date_from)
                    date_to = fields.Date.from_string(period_date_to)
                else:
                    date_to = fields.Date.from_string(
                        period_date_to or period_date_from
                    )
                    date_from = date_utils.get_month(date_to)[0]

                options_filter = "custom"
            else:
                options_filter = date_filter
        else:
            # Default.
            options_filter = default_filter

        _debug.logic(
            "date_mode_resolved",
            report=self,
            previous_mode=mode,
            mode=options_mode,
            previous_filter=date_filter,
            filter=options_filter,
            has_dates=bool(date_from and date_to),
        )
        options_filter = self._normalize_date_filter(
            options, options_filter, period_date_to
        )

        # Compute 'date_from' / 'date_to'.
        if not date_from or not date_to:
            if options_filter == "today":
                date_to = fields.Date.context_today(self)
                date_from = self._get_year_bounds(date_to)["date_from"]
                period_type = "today"
            elif "month" in options_filter:
                date_from, date_to = date_utils.get_month(
                    fields.Date.context_today(self)
                )
                period_type = "month"
            elif "quarter" in options_filter:
                date_from, date_to = date_utils.get_quarter(
                    fields.Date.context_today(self)
                )
                period_type = "quarter"
            elif "year" in options_filter:
                company_fiscalyear_dates = self._get_year_bounds(
                    fields.Date.context_today(self)
                )
                curr_year = fields.Date.context_today(self).year
                if company_fiscalyear_dates["date_from"].year < curr_year:
                    company_fiscalyear_dates = self._get_year_bounds(
                        company_fiscalyear_dates["date_to"] + relativedelta(days=1)
                    )
                date_from = company_fiscalyear_dates["date_from"]
                date_to = company_fiscalyear_dates["date_to"]
            else:
                date_from, date_to, period_type = self._get_custom_period_bounds(
                    options,
                    options_filter,
                    period_date_from,
                    period_date_to,
                    (date_from, date_to, period_type),
                )

        options_filter = self._convert_custom_period_filter(
            options, options_filter, date, period_date_to, date_to
        )

        _debug.logic(
            "date_scope_chosen",
            report=self,
            filter=options_filter,
            period_type=period_type,
            date_from=date_from,
            date_to=date_to,
            period=date.get("period"),
        )
        options["date"] = self._get_dates_period(
            date_from,
            date_to,
            options_mode,
            period_type=period_type,
            options_return=options.get("return_periodicity"),
        )

        if any(option in options_filter for option in ["previous", "next"]):
            new_period = date.get("period", -1 if "previous" in options_filter else 1)
            _debug.logic(
                "date_period_shifted",
                report=self,
                period=new_period,
                return_period="return_period" in options_filter,
            )
            options["date"] = self._get_shifted_dates_period(
                options,
                options["date"],
                new_period,
                return_period="return_period" in options_filter,
            )
            # This line is useful for the export and tax closing so that the period is set in the options.
            options["date"]["period"] = new_period

        self._finalize_custom_period_options(options, options_filter)

        options["date"]["filter"] = options_filter
        _debug.pipeline(
            "date_options_built",
            report=self,
            filter=options_filter,
            date_from=options["date"].get("date_from"),
            date_to=options["date"].get("date_to"),
            period=options["date"].get("period"),
        )

    @_debug.perf.timed
    def _init_options_comparison(self, options, previous_options):
        """Initialize the 'comparison' options key.

        This filter must be loaded after the 'date' filter.

        :param options:             The current report options to build.
        :param previous_options:    The previous options coming from another report.
        """
        if not self.filter_period_comparison:
            _debug.logic("comparison_skipped", report=self, reason="filter_disabled")
            return

        previous_comparison = previous_options.get("comparison", {})
        previous_filter = previous_comparison.get("filter")

        period_order = previous_comparison.get("period_order") or "descending"
        if previous_filter == "custom":
            # Try to adapt the previous 'custom' filter.
            date_from = previous_comparison.get("date_from")
            date_to = previous_comparison.get("date_to")
            number_period = 1
            options_filter = "custom"
        else:
            # Use the 'date' options.
            date_from = options["date"]["date_from"]
            date_to = options["date"]["date_to"]
            number_period = max(previous_comparison.get("number_period", 1) or 0, 0)
            options_filter = (number_period and previous_filter) or "no_comparison"

        options["comparison"] = {
            "filter": options_filter,
            "number_period": number_period,
            "date_from": date_from,
            "date_to": date_to,
            "periods": [],
            "period_order": period_order,
        }
        _debug.logic(
            "comparison_mode_chosen",
            report=self,
            previous_filter=previous_filter,
            filter=options_filter,
            number_period=number_period,
            period_order=period_order,
        )

        date_from_obj = fields.Date.from_string(date_from)
        date_to_obj = fields.Date.from_string(date_to)

        if options_filter == "custom":
            options["comparison"]["periods"].append(
                self._get_dates_period(
                    date_from_obj,
                    date_to_obj,
                    options["date"]["mode"],
                )
            )
        elif options_filter in ("previous_period", "same_last_year"):
            previous_period = options["date"]
            for _i in range(number_period):
                if options_filter == "previous_period":
                    period_vals = self._get_shifted_dates_period(
                        options, previous_period, -1
                    )
                else:
                    period_vals = self._get_dates_previous_year(
                        options, previous_period
                    )
                options["comparison"]["periods"].append(period_vals)
                previous_period = period_vals

        _debug.pipeline(
            "comparison_periods_built",
            report=self,
            filter=options_filter,
            periods=len(options["comparison"]["periods"]),
        )
        if len(options["comparison"]["periods"]) > 0:
            options["comparison"].update(options["comparison"]["periods"][0])

    def _init_options_column_percent_comparison(self, options, previous_options):
        if (
            self.filter_growth_comparison
            and len(options["columns"]) == 2
            and len(options.get("comparison", {}).get("periods", [])) == 1
        ):
            options["column_percent_comparison"] = "growth"

        if (
            options.get("display_analytic_groupby")
            and len(options.get("analytic_plans_groupby", [])) == 1
            and not options.get("analytic_accounts")
            and not options.get("comparison", {}).get("periods", [])
            and len(options["columns"]) == 2
        ):
            options["column_percent_comparison"] = "analytic_coverage"

        if any(budget["selected"] for budget in options.get("budgets", [])):
            options["column_percent_comparison"] = "budget"
        _debug.logic(
            "percent_comparison_chosen",
            report=self,
            mode=options.get("column_percent_comparison"),
        )

    def _get_domain_options_date(self, options, date_scope):
        date_from, date_to = self._get_date_bounds_info(options, date_scope)

        date_field = self._get_source_date_field()
        scope_domain = Domain(date_field, "<=", date_to)
        if date_from:
            scope_domain &= Domain(date_field, ">=", date_from)

        return scope_domain

    @api.model
    def _init_options_order_column(self, options, previous_options):
        # options['order_column'] is in the form {'expression_label': expression label of the column to order, 'direction': the direction order ('ASC' or 'DESC')}
        options["order_column"] = None

        previous_value = previous_options and previous_options.get("order_column")
        if previous_value:
            for col in options["columns"]:
                if (
                    col["sortable"]
                    and col["expression_label"] == previous_value["expression_label"]
                ):
                    options["order_column"] = previous_value
                    break

    def _init_options_prefix_groups_threshold(self, options, previous_options):
        options["prefix_groups_threshold"] = self.prefix_groups_threshold

    def _init_options_companies(self, options, previous_options):
        if previous_options.get("forced_companies"):
            options["forced_companies"] = previous_options["forced_companies"]
            companies = self.env.company.browse(previous_options["forced_companies"])
        else:
            companies = self._get_options_companies(options, previous_options)

        _debug.logic(
            "companies_resolved",
            report=self,
            forced=bool(previous_options.get("forced_companies")),
            companies=companies,
        )
        options["companies"] = [
            {"name": c.name, "id": c.id, "currency_id": c.currency_id.id}
            for c in companies
        ]

    ####################################################
    # OPTIONS: MULTI CURRENCY
    ####################################################
    def _init_options_multi_currency(self, options, previous_options):
        options["multi_currency"] = (
            any(
                company.get("currency_id") != options["companies"][0].get("currency_id")
                for company in options["companies"]
            )
            or any(column.figure_type != "monetary" for column in self.column_ids)
            or any(
                expression.figure_type and expression.figure_type != "monetary"
                for expression in self.line_ids.expression_ids
            )
        )

    ####################################################
    # OPTIONS: ROUNDING UNIT
    ####################################################
    def _init_options_rounding_unit(self, options, previous_options):
        default = "decimals"
        options["rounding_unit"] = previous_options.get("rounding_unit", default)
        options["rounding_unit_names"] = self._get_rounding_unit_names()

    ####################################################
    # OPTIONS: UNFOLDED LINES
    ####################################################
    def _init_options_unfolded(self, options, previous_options):
        options["unfold_all"] = self.filter_unfold_all and previous_options.get(
            "unfold_all", False
        )

        previous_section_source_id = previous_options.get("sections_source_id")
        if (
            not previous_section_source_id
            or previous_section_source_id == options["sections_source_id"]
        ):
            # Only keep the unfolded lines if they belong to the same report or a section of the same report
            options["unfolded_lines"] = previous_options.get("unfolded_lines", [])
        else:
            options["unfolded_lines"] = []

    ####################################################
    # OPTIONS: HIDE LINE AT 0
    ####################################################
    def _init_options_hide_0_lines(self, options, previous_options):
        if self.filter_hide_0_lines != "never":
            previous_val = previous_options.get("hide_0_lines")
            if previous_val is not None:
                options["hide_0_lines"] = previous_val
            else:
                options["hide_0_lines"] = self.filter_hide_0_lines == "by_default"
        else:
            options["hide_0_lines"] = False

    ####################################################
    # OPTIONS: HORIZONTAL GROUP
    ####################################################
    def _init_options_horizontal_groups(self, options, previous_options):
        options["available_horizontal_groups"] = []
        options["selected_horizontal_group_id"] = None

    ####################################################
    # OPTIONS: SEARCH BAR
    ####################################################
    def _init_options_search_bar(self, options, previous_options):
        if self.search_bar:
            options["search_bar"] = True
            if "filter_search_bar" in previous_options:
                options["filter_search_bar"] = previous_options["filter_search_bar"]

    @_debug.perf.timed
    def _init_options_column_headers(self, options, previous_options):
        # Prepare column headers, in case the order of the comparison is ascending we reverse the order of the columns
        all_comparison_date_vals = [options["date"]] + options.get(
            "comparison", {}
        ).get("periods", [])
        if (
            options.get("comparison")
            and options["comparison"]["period_order"] == "ascending"
        ):
            all_comparison_date_vals = all_comparison_date_vals[::-1]

        column_headers = [
            [
                {
                    "name": comparison_date_vals["string"],
                    "forced_options": {"date": comparison_date_vals},
                }
                for comparison_date_vals in all_comparison_date_vals
            ],  # First level always consists of date comparison. Horizontal groupby are done on following levels.
        ]

        # Handle horizontal groups
        selected_horizontal_group_id = options.get("selected_horizontal_group_id")
        if selected_horizontal_group_id:
            horizontal_group = self.env["account.report.horizontal.group"].browse(
                selected_horizontal_group_id
            )

            for field_name, records in horizontal_group._get_header_levels_data():
                header_level = [
                    {
                        "name": record.display_name,
                        "horizontal_groupby_element": {field_name: record.id},
                    }
                    for record in records
                ]
                column_headers.append(header_level)

        # Insert budget column headers if needed
        selected_budgets = [
            budget for budget in options.get("budgets", []) if budget["selected"]
        ]
        if selected_budgets:
            budget_headers = [
                {
                    "name": self.env._("Period Total"),
                    "forced_options": {
                        "budget_base": True,
                        "no_subheader_division": True,
                    },
                    "colspan": len(self._get_visible_columns(options)),
                }
            ]

            for budget in selected_budgets:
                # Add budget amount column
                budget_headers.append(
                    {
                        "name": budget["name"],
                        "forced_options": {
                            "compute_budget": budget["id"],
                            "no_subheader_division": True,
                        },
                        "colspan": 1,
                    }
                )
                if (
                    len(
                        self._get_visible_columns(options).filtered(
                            lambda column: column.figure_type == "monetary"
                        )
                    )
                    == 1
                ):
                    # Add budget percentage column (only if one column in the report)
                    budget_headers.append(
                        {
                            "name": "%",
                            "forced_options": {
                                "budget_percentage": budget["id"],
                                "no_subheader_division": True,
                            },
                            "colspan": 1,
                        }
                    )

            if selected_horizontal_group_id:
                column_headers[1] += budget_headers
            else:
                column_headers.append(budget_headers)

        options["column_headers"] = column_headers
        _debug.pipeline(
            "column_headers_built",
            report=self,
            levels=len(column_headers),
            date_headers=len(all_comparison_date_vals),
            horizontal_group=selected_horizontal_group_id,
            budgets=len(selected_budgets),
        )

    ####################################################
    # OPTIONS: COLUMNS
    ####################################################
    @_debug.perf.timed
    def _init_options_optional_columns(self, options, previous_options):
        optional_columns = self.column_ids.filtered("optional")
        if not optional_columns:
            return

        previously_hidden = previous_options.get("hidden_columns")
        if previously_hidden is None:
            hidden_columns = set(optional_columns.filtered("optional_hidden").ids)
        else:
            hidden_columns = set(previously_hidden) & set(optional_columns.ids)

        options["hidden_columns"] = sorted(hidden_columns)
        options["optional_columns"] = [
            {
                "id": column.id,
                "name": column.name,
                "selected": column.id not in hidden_columns,
            }
            for column in optional_columns
        ]
        _debug.logic(
            "optional_columns_resolved",
            report=self,
            optional=len(optional_columns),
            hidden=len(hidden_columns),
        )

    def _get_visible_columns(self, options):
        hidden_columns = set(options.get("hidden_columns") or ())
        return self.column_ids.filtered(lambda column: column.id not in hidden_columns)

    def _init_options_columns(self, options, previous_options):
        default_group_vals = {"horizontal_groupby_element": {}, "forced_options": {}}
        all_column_group_vals_in_order = self._generate_columns_group_vals_recursively(
            options["column_headers"], default_group_vals
        )

        columns, column_groups = self._prepare_columns_from_column_group_vals(
            options, all_column_group_vals_in_order
        )

        options["columns"] = columns
        options["column_groups"] = column_groups

        # Debug column is only shown when there is a single column group, so that we can display all the subtotals of the line in a clear way
        options["show_debug_column"] = (
            options["export_mode"] != "print"
            and self.env.user.has_group("base.group_no_one")
            and len(options["column_groups"]) == 1
            and len(self.line_ids) > 0
        )  # No debug column on fully dynamic reports by default (they can customize this)

        options["show_last_annotations"] = previous_options.get("show_last_annotations")

        selected_budgets = [
            budget for budget in options.get("budgets", []) if budget["selected"]
        ]

        # Show an additional column summing all the horizontal groups if there is no comparison or budget, and only one level of horizontal group
        options["show_horizontal_group_total"] = (
            options.get("selected_horizontal_group_id")
            and options.get("comparison", {}).get("filter") == "no_comparison"
            and len(self._get_visible_columns(options)) == 1
            and len(options["column_headers"]) == 2
            and not selected_budgets
        )
        _debug.pipeline(
            "columns_resolved",
            report=self,
            columns=len(columns),
            column_groups=len(column_groups),
            show_debug_column=options["show_debug_column"],
            horizontal_total=bool(options["show_horizontal_group_total"]),
        )

    @_debug.perf.timed
    def _init_options_buttons(self, options, previous_options):
        options["buttons"] = [
            {
                "name": self.env._("PDF"),
                "sequence": 10,
                "action": "export_file",
                "action_param": "export_to_pdf",
                "file_export_type": self.env._("PDF"),
                "branch_allowed": True,
                "always_show": True,
            },
            {
                "name": self.env._("XLSX"),
                "sequence": 20,
                "action": "export_file",
                "action_param": "export_to_xlsx",
                "file_export_type": self.env._("XLSX"),
                "branch_allowed": True,
                "always_show": True,
            },
        ]

        _debug.pipeline("buttons_built", report=self, buttons=len(options["buttons"]))

    def _init_options_section_buttons(self, options, previous_options):
        """In case we're displaying a section, we want to replace its buttons by its source report's. This needs to be done last, after calling the
        custom handler, to avoid its _custom_options_initializer function to generate additional buttons.
        """
        if options["sections_source_id"] != self.id:
            # We need to re-call a full get_options in case a custom options initializer adds new buttons depending on other options.
            # This way, we're sure we always get all buttons that are needed.
            sections_source = self.env["report.formula"].browse(
                options["sections_source_id"]
            )
            options["buttons"] = sections_source.get_options(
                previous_options={**options, "no_report_reroute": True}
            )["buttons"]

    ####################################################
    # OPTIONS: VARIANTS
    ####################################################
    @_debug.perf.timed
    def _init_options_variants(self, options, previous_options):
        allowed_variant_ids = set()

        previous_section_source_id = previous_options.get("sections_source_id")
        if previous_section_source_id:
            previous_section_source = self.env["report.formula"].browse(
                previous_section_source_id
            )
            if self in previous_section_source.section_report_ids:
                options["variants_source_id"] = (
                    previous_section_source.root_report_id or previous_section_source
                ).id
                allowed_variant_ids.add(previous_section_source_id)

        if "variants_source_id" not in options:
            options["variants_source_id"] = (self.root_report_id or self).id

        available_variants = self.env["report.formula"]
        options["has_inactive_variants"] = False
        allowed_country_variant_ids = {}
        all_variants = self._get_variants(options["variants_source_id"])
        for variant in all_variants._is_available_for(options):
            if (
                not self.root_report_id and variant != self and variant.active
            ):  # Non-route reports don't reroute the variant when computing their options
                allowed_variant_ids.add(variant.id)
                if variant.country_id:
                    allowed_country_variant_ids.setdefault(
                        variant.country_id.id, []
                    ).append(variant.id)

            if variant.active:
                available_variants += variant
            else:
                options["has_inactive_variants"] = True

        _debug.pipeline(
            "variants_filtered",
            report=self,
            variants_source_id=options["variants_source_id"],
            from_section=previous_section_source_id,
            available=len(available_variants),
            allowed=len(allowed_variant_ids),
            countries=len(allowed_country_variant_ids),
            has_inactive=options["has_inactive_variants"],
        )
        options["available_variants"] = [
            {
                "id": variant.id,
                "name": variant.display_name,
                "country_id": variant.country_id.id,  # To ease selection of default variant to open, without needing browsing again
            }
            for variant in sorted(
                available_variants,
                key=lambda x: ((x.country_id and 1) or 0, x.sequence, x.id),
            )
        ]

        previous_opt_report_id = previous_options.get("selected_variant_id")
        if (
            previous_opt_report_id in allowed_variant_ids
            or previous_opt_report_id == self.id
        ):
            options["selected_variant_id"] = previous_opt_report_id
        elif allowed_country_variant_ids:
            country_id = self._get_variant_preferred_country().id
            report_id = (
                allowed_country_variant_ids.get(country_id)
                or next(iter(allowed_country_variant_ids.values()))
            )[0]
            options["selected_variant_id"] = report_id
        else:
            options["selected_variant_id"] = self.id
        _debug.logic(
            "variant_selected",
            report=self,
            previous_variant_id=previous_opt_report_id,
            selected_variant_id=options["selected_variant_id"],
            rerouted=options["selected_variant_id"] != self.id,
        )

    ####################################################
    # OPTIONS: SECTIONS
    ####################################################
    @_debug.perf.timed
    def _init_options_sections(self, options, previous_options):
        if options.get("selected_variant_id"):
            options["sections_source_id"] = options["selected_variant_id"]
        else:
            options["sections_source_id"] = self.id

        source_report = self.env["report.formula"].browse(options["sections_source_id"])

        available_sections = (
            source_report.section_report_ids
            if source_report.use_sections
            else self.env["report.formula"]
        )
        options["sections"] = [
            {"name": section.name, "id": section.id} for section in available_sections
        ]

        if available_sections:
            section_id = previous_options.get("selected_section_id")
            if not section_id or section_id not in available_sections.ids:
                section_id = available_sections[0].id

            options["selected_section_id"] = section_id

        _debug.logic(
            "section_selected",
            report=self,
            sections_source_id=options["sections_source_id"],
            sections=len(available_sections),
            selected_section_id=options.get("selected_section_id"),
        )
        options["has_inactive_sections"] = bool(
            self.env["report.formula"]
            .with_context(active_test=False)
            .search_count(
                [
                    ("section_main_report_ids", "in", options["sections_source_id"]),
                    ("active", "=", False),
                ],
                limit=1,
            )
        )

    ####################################################
    # OPTIONS: REPORT_ID
    ####################################################
    def _init_options_report_id(self, options, previous_options):
        if previous_options.get("no_report_reroute"):
            # Used for exports
            options["report_id"] = self.id
        else:
            options["report_id"] = (
                options.get("selected_section_id")
                or options.get("selected_variant_id")
                or self.id
            )

    ####################################################
    # OPTIONS: HORIZONTAL SPLIT
    ####################################################
    def _init_options_horizontal_split(self, options, previous_options):
        if any(line.horizontal_split_side for line in self.line_ids):
            options["horizontal_split"] = previous_options.get(
                "horizontal_split", False
            )

    ####################################################
    # OPTIONS: CUSTOM
    ####################################################
    def _init_options_custom(self, options, previous_options):
        custom_handler_model = self._get_custom_handler_model()
        if custom_handler_model:
            with _debug.perf(
                "_custom_options_initializer",
                cr=self.env.cr,
                report=self,
                custom_handler_model=custom_handler_model,
            ):
                self.env[custom_handler_model]._custom_options_initializer(
                    self, options, previous_options
                )

    ####################################################
    # OPTIONS: INTEGER ROUNDING
    ####################################################
    def _init_options_integer_rounding(self, options, previous_options):
        if self.integer_rounding:
            options["integer_rounding"] = self.integer_rounding
            if options.get("export_mode") == "file":
                options["integer_rounding_enabled"] = True
            else:
                options["integer_rounding_enabled"] = previous_options.get(
                    "integer_rounding_enabled", True
                )
            return options
        return None

    ####################################################
    # OPTIONS: CONSOLIDATION
    ####################################################
    def _init_options_consolidation(self, options, previous_options):
        options["show_consolidation"] = len(
            self.get_report_company_ids(options)
        ) > 1 and any(
            groupby.strip() == "account_id"
            for groupby_str in self.line_ids.mapped("user_groupby")
            for groupby in (groupby_str or "").split(",")
        )

        options["consolidation"] = options[
            "show_consolidation"
        ] and previous_options.get("consolidation", False)

    ####################################################
    # OPTIONS: LOADING CALL
    ####################################################
    def _init_options_loading_call(self, options, previous_options):
        """Used by the js to know if it needs to reload the options (to not overwrite new options from the js)"""
        options["loading_call_number"] = (
            previous_options.get("loading_call_number") or 0
        )
        return options

    ####################################################
    # OPTIONS: FILTERS
    ####################################################
    def _init_options_export_mode(self, options, previous_options):
        options["export_mode"] = previous_options.get("export_mode")

    def _get_options_companies(self, options, previous_options):
        return self.env.companies

    def _get_variant_preferred_country(self):
        return self.env.company.country_id

    def _init_options_filters(self, options, previous_options):
        options["filters"] = {
            "show_all": self.filter_unfold_all,
            "show_date": self.filter_date,
            "show_analytic": options.get("display_analytic", False),
            "show_analytic_groupby": options.get("display_analytic_groupby", False),
            "show_analytic_plan_groupby": options.get(
                "display_analytic_plan_groupby", False
            ),
            "show_hierarchy": options.get("display_hierarchy_filter", False),
            "show_period_comparison": self.filter_period_comparison,
            "show_totals": self._get_totals_below_sections()
            and not options.get("ignore_totals_below_sections"),
            "show_hide_0_lines": self.filter_hide_0_lines,
        }

    @api.readonly
    @_debug.perf.timed
    def get_options(self, previous_options):
        self.check_singleton()

        initializers_in_sequence = self._get_options_initializers_in_sequence()

        options = {"custom_display_config": {}}

        # previous_options comes straight from the client, so this flag is settable from
        # a browser. It is honoured only while a test is actually running: three l10n
        # modules branch on it, and two of them use it to skip a check -- l10n_es waives
        # the BOE date validation, l10n_ar deselects the purchase book "to avoid raising"
        # -- which a user must not be able to ask for.
        # Read through the module, never `from ... import current_test`: the name is
        # rebound when a test starts, and a by-value import would keep the False it
        # was bound to at import time.
        if previous_options.get("_running_export_test") and modules.module.current_test:
            options["_running_export_test"] = True

        idx = None
        with contextlib.suppress(ValueError):
            idx = initializers_in_sequence.index(self._init_options_report_id) + 1

        before_report = initializers_in_sequence[:idx]
        after_report = initializers_in_sequence[idx:]

        # We need report_id to be initialized. Compute the necessary options to check for reroute.
        for initializer in before_report:
            initializer(options, previous_options=previous_options)

        # Stop the computation to check for reroute once we have computed the necessary information
        if (
            not self.root_report_id or (self.use_sections and self.section_report_ids)
        ) and options["report_id"] != self.id:
            _debug.logic(
                "get_options_rerouted", report=self, report_id=options["report_id"]
            )
            # Load the variant/section instead of the root report
            variant_options = {**previous_options}
            for reroute_opt_key in (
                "selected_variant_id",
                "selected_section_id",
                "variants_source_id",
                "sections_source_id",
            ):
                opt_val = options.get(reroute_opt_key)
                if opt_val:
                    variant_options[reroute_opt_key] = opt_val

            return (
                self.env["report.formula"]
                .browse(options["report_id"])
                .get_options(variant_options)
            )

        # No reroute; keep on and compute the other options
        for initializer in after_report:
            with _debug.perf(
                "get_options", cr=self.env.cr, report=self, name=initializer.__name__
            ):
                initializer(options, previous_options=previous_options)
        if _debug.pipeline.enabled:
            _debug.pipeline(
                "get_options",
                report=self,
                date=options.get("date", {}).get("string"),
                companies=self.get_report_company_ids(options),
                column_groups=len(options.get("column_groups", {})),
                filters=sorted(
                    k for k, v in options.items() if k.startswith("filter_") and v
                ),
            )

        self._apply_branch_rules_to_buttons(options)

        # Sort the buttons list by sequence, for rendering
        options["buttons"] = sorted(
            options["buttons"], key=lambda x: x.get("sequence", 90)
        )

        # Sanitizing date_from and date_to since they need to be JSON-serializable when exporting the report
        # on the server side, since the ORM converts them to strings automatically when sending them to the client.
        for date_dict in [options.get("date", {})] + [
            group_data["forced_options"]["date"]
            for group_data in options["column_groups"].values()
            if group_data.get("forced_options", {}).get("date")
        ]:
            if (date_from := date_dict.get("date_from")) and not isinstance(
                date_from, str
            ):
                date_dict["date_from"] = fields.Date.to_string(date_from)

            if (date_to := date_dict.get("date_to")) and not isinstance(date_to, str):
                date_dict["date_to"] = fields.Date.to_string(date_to)

        return options

    def _get_options_initializers_in_sequence(self):
        """Gets all filters in the right order to initialize them, so that each filter is
        guaranteed to be after all of its dependencies in the resulting list.

        :return: a list of initializer functions, each accepting two parameters:
            - options (mandatory): The options dictionary to be modified by this initializer to include its related option's data

            - previous_options (optional, defaults to None): A dict with default options values, coming from a previous call to the report.
                                                             These values can be considered or ignored on a case-by-case basis by the initializer,
                                                             depending on functional needs.
        """
        initializer_prefix = "_init_options_"
        initializers = [
            getattr(self, attr)
            for attr in dir(self)
            if attr.startswith(initializer_prefix)
        ]

        # Order them in a dependency-compliant way
        forced_sequence_map = self._get_options_initializers_forced_sequence_map()
        initializers.sort(
            key=lambda x: forced_sequence_map.get(
                x.__name__, forced_sequence_map["default"]
            )
        )

        return initializers

    @_debug.perf.timed
    def _get_options_initializers_forced_sequence_map(self):
        """By default, not specific order is ensured for the filters when calling _get_options_initializers_in_sequence.
        This function allows giving them a sequence number. It can be overridden
        to make filters depend on each other.

        :return: dict(str, int): the initializer's method name and its sequence (lowest first);
                                 "default" is the sequence of every initializer the map does not name.
                                 Initializers sharing a sequence run in the alphabetical order of their names.
        """
        return {
            "_init_options_companies": 10,
            "_init_options_variants": 15,
            "_init_options_sections": 16,
            "_init_options_report_id": 17,
            "_init_options_date": 30,
            "_init_options_horizontal_groups": 40,
            "_init_options_comparison": 50,
            "_init_options_export_mode": 60,
            "_init_options_integer_rounding": 70,
            "_init_options_consolidation": 75,
            "default": 200,
            "_init_options_optional_columns": 980,
            "_init_options_column_headers": 990,
            "_init_options_columns": 1000,
            "_init_options_column_percent_comparison": 1010,
            "_init_options_order_column": 1020,
            "_init_options_prefix_groups_threshold": 1040,
            "_init_options_custom": 1050,
            "_init_options_section_buttons": 1060,
            "_init_options_filters": 1500,
        }

    @_debug.perf.timed
    def _get_domain_options(self, options, date_scope) -> Domain:
        self.check_singleton()

        available_scopes = dict(
            self.env["report.formula.expression"]._fields["date_scope"].selection
        )
        if (
            date_scope and date_scope not in available_scopes
        ):  # date_scope can be passed to None explicitly to ignore the dates
            raise UserError(self.env._("Unknown date scope: %s", date_scope))

        return Domain.AND(
            [
                Domain("company_id", "in", self.get_report_company_ids(options)),
                self._get_domain_options_date(options, date_scope)
                if date_scope
                else Domain.TRUE,
                # That option key is set when splitting options between column groups
                options.get("forced_domain") or Domain.TRUE,
                *self._get_source_domains(options, date_scope),
            ]
        )

    @api.model
    def _get_dates_previous_year(self, options, period_vals):
        """Shift the period to the previous year.
        :param options:     The report options.
        :param period_vals: A dictionary generated by the _get_dates_period method.
        :return:            A dictionary in the format returned by _get_dates_period.
        """
        period_type = period_vals["period_type"]
        mode = period_vals["mode"]
        date_from = fields.Date.from_string(period_vals["date_from"])
        date_from -= relativedelta(years=1)
        date_to = fields.Date.from_string(period_vals["date_to"])
        date_to -= relativedelta(years=1)

        if period_type == "month":
            date_from, date_to = date_utils.get_month(date_to)

        return self._get_dates_period(date_from, date_to, mode, period_type=period_type)

    @_debug.perf.timed
    def _get_date_bounds_info(self, options, date_scope):
        # Default values (the ones from 'strict_range')
        date_to = options["date"]["date_to"]
        date_from = (
            options["date"]["date_from"] if options["date"]["mode"] == "range" else None
        )

        if date_scope == "from_beginning":
            date_from = None

        elif date_scope == "to_beginning_of_period":
            date_tmp = fields.Date.from_string(date_from or date_to) - relativedelta(
                days=1
            )
            date_to = date_tmp.strftime("%Y-%m-%d")
            date_from = None

        elif date_scope == "from_fiscalyear":
            date_tmp = fields.Date.from_string(date_to)
            date_tmp = self._get_year_bounds(date_tmp)["date_from"]
            date_from = date_tmp.strftime("%Y-%m-%d")

        elif date_scope == "to_beginning_of_fiscalyear":
            date_tmp = fields.Date.from_string(date_to)
            date_tmp = self._get_year_bounds(date_tmp)["date_from"] - relativedelta(
                days=1
            )
            date_to = date_tmp.strftime("%Y-%m-%d")
            date_from = None

        else:
            date_from, date_to = self._get_custom_date_scope_bounds(
                options, date_scope, date_from, date_to
            )

        _debug.logic(
            "date_bounds_resolved",
            report=self,
            date_scope=date_scope,
            date_from=date_from,
            date_to=date_to,
        )
        return date_from, date_to

    def _standardize_date_scope_for_date_range(self, date_scope):
        """Return the canonical date_scope to use for this report.

        When the report does not accept date ranges, several date scopes mean the same thing; collapsing
        them onto a single value avoids creating redundant computation batches.
        """
        if not self.filter_date_range and date_scope == "strict_range":
            return "from_beginning"
        else:
            return date_scope

    def _adjust_date_for_joined_comparison(self, options, period_date_from):
        comparison_filter = options.get("comparison", {}).get("filter")
        if comparison_filter == "previous_period":
            comparison_date_from = datetime.datetime.strptime(
                options["comparison"].get("periods", [{}])[-1].get("date_from"),
                "%Y-%m-%d",
            )
            return min(period_date_from, comparison_date_from)
        return period_date_from

    def _adjust_domain_for_unjoined_comparison(self, options, dates_domain):
        comparison_filter = options.get("comparison", {}).get("filter")
        if comparison_filter and comparison_filter not in {
            "no_comparison",
            "previous_period",
        }:
            unlinked_comparison_periods_domains_list = [
                Domain("date", ">=", period["date_from"])
                & Domain("date", "<=", period["date_to"])
                for period in options["comparison"]["periods"]
            ]
            unlinked_comparison_periods_domains_list.insert(0, dates_domain)
            dates_domain = Domain.OR(unlinked_comparison_periods_domains_list)

        return dates_domain

    @api.model
    @_debug.perf.timed
    def _get_dates_period(
        self, date_from, date_to, mode, period_type=None, options_return=False
    ):
        """Compute some information about the period:
        * The name to display on the report.
        * The period type (e.g. quarter) if not specified explicitly.
        :param date_from:   The starting date of the period.
        :param date_to:     The ending date of the period.
        :param mode:        'single' for a date-based period, 'range' for a date range.
        :param period_type: The type of the interval date_from -> date_to.
        :param options_return: The 'return_period' options, needed to name a 'return_period' period.
        :return:            A dictionary containing:
            * date_from * date_to * string * period_type * mode * currency_table_period_key *
        """

        def match(dt_from, dt_to):
            return (dt_from, dt_to) == (date_from, date_to)

        def get_quarter_name(date_to, date_from):
            date_to_quarter_string = format_date(
                self.env, fields.Date.to_string(date_to), date_format="MMM yyyy"
            )
            date_from_quarter_string = format_date(
                self.env, fields.Date.to_string(date_from), date_format="MMM"
            )
            return f"{date_from_quarter_string} - {date_to_quarter_string}"

        string = None
        # If no date_from or not date_to, we are unable to determine a period
        if not period_type or period_type == "custom":
            date = date_to or date_from
            company_fiscalyear_dates = self._get_year_bounds(date)
            if match(
                company_fiscalyear_dates["date_from"],
                company_fiscalyear_dates["date_to"],
            ):
                period_type = "fiscalyear"
                if company_fiscalyear_dates.get("record"):
                    string = company_fiscalyear_dates["record"].name
            elif match(*date_utils.get_month(date)):
                period_type = "month"
            elif match(*date_utils.get_quarter(date)):
                period_type = "quarter"
            elif match(*date_utils.get_fiscal_year(date)):
                period_type = "year"
            elif match(date_utils.get_month(date)[0], fields.Date.today()):
                period_type = "today"
            else:
                period_type = "custom"
            _debug.logic(
                "period_type_inferred",
                period_type=period_type,
                date_from=date_from,
                date_to=date_to,
                named_by_record=bool(string),
            )
        elif period_type == "fiscalyear":
            date = date_to or date_from
            company_fiscalyear_dates = self._get_year_bounds(date)
            record = company_fiscalyear_dates.get("record")
            string = record and record.name
        else:
            string = self._get_custom_period_name(
                period_type, date_from, date_to, options_return
            )

        if not string:
            fy_day, fy_month = self._get_year_end()
            if mode == "single":
                string = self.env._("As of %s", format_date(self.env, date_to))
            elif period_type == "year" or (
                period_type == "fiscalyear"
                and (date_from, date_to) == date_utils.get_fiscal_year(date_to)
            ):
                string = date_to.strftime("%Y")
            elif period_type == "fiscalyear" and (
                date_from,
                date_to,
            ) == date_utils.get_fiscal_year(date_to, day=fy_day, month=fy_month):
                string = "%s - %s" % (date_to.year - 1, date_to.year)
            elif period_type == "month":
                string = format_date(
                    self.env, fields.Date.to_string(date_to), date_format="MMM yyyy"
                )
            elif period_type == "quarter":
                string = get_quarter_name(date_to, date_from)
            else:
                dt_from_str = format_date(self.env, fields.Date.to_string(date_from))
                dt_to_str = format_date(self.env, fields.Date.to_string(date_to))
                string = self.env._(
                    "%(date_from)s - %(date_to)s",
                    date_from=dt_from_str,
                    date_to=dt_to_str,
                )

        return {
            "string": string,
            "period_type": period_type,
            "currency_table_period_key": f"{date_from if mode == 'range' else 'None'}_{date_to}",
            "mode": mode,
            "date_from": (date_from and fields.Date.to_string(date_from)) or False,
            "date_to": fields.Date.to_string(date_to),
        }

    @api.model
    @_debug.perf.timed
    def _get_shifted_dates_period(
        self, options, period_vals, periods, return_period=False
    ):
        """Shift the period.
        :param options:     The report options.
        :param period_vals: A dictionary generated by the _get_dates_period method.
        :param periods:     The number of periods we want to move either in the future or the past
        :param return_period: Force the shift to follow the return periodicity of options.
        :return:            A dictionary in the format returned by _get_dates_period, or None
                            for a period_type this method cannot shift.
        """
        period_type = period_vals["period_type"]
        mode = period_vals["mode"]
        date_from = fields.Date.from_string(period_vals["date_from"])
        date_to = fields.Date.from_string(period_vals["date_to"])
        if period_type == "month":
            date_to = date_from + relativedelta(months=periods)
        elif period_type == "quarter":
            date_to = date_from + relativedelta(months=3 * periods)
        elif period_type == "year":
            date_to = date_from + relativedelta(years=periods)
        elif period_type in {"custom", "today"}:
            date_to = date_from + relativedelta(days=periods)

        _debug.logic(
            "shift_requested",
            period_type=period_type,
            mode=mode,
            periods=periods,
            return_period=return_period,
        )
        custom_period = self._get_shifted_custom_period(
            options, periods, return_period, period_type, mode, date_from
        )
        if custom_period is not None:
            return custom_period
        if period_type in ("fiscalyear", "today"):
            # Don't pass the period_type to _get_dates_period to be able to retrieve the account.fiscal.year record if
            # necessary.
            company_fiscalyear_dates = {}
            # This loop is needed because a fiscal year can be a month, quarter, etc
            for _ in range(abs(periods)):
                date_to = (date_from if periods < 0 else date_to) + relativedelta(
                    days=periods / abs(periods)
                )
                company_fiscalyear_dates = self._get_year_bounds(date_to)
                if periods < 0:
                    date_from = company_fiscalyear_dates["date_from"]
                else:
                    date_to = company_fiscalyear_dates["date_to"]

            return self._get_dates_period(
                company_fiscalyear_dates["date_from"],
                company_fiscalyear_dates["date_to"],
                mode,
            )
        if period_type in ("month", "custom"):
            return self._get_dates_period(
                *date_utils.get_month(date_to), mode, period_type="month"
            )
        if period_type == "quarter":
            return self._get_dates_period(
                *date_utils.get_quarter(date_to), mode, period_type="quarter"
            )
        if period_type == "year":
            return self._get_dates_period(
                *date_utils.get_fiscal_year(date_to), mode, period_type="year"
            )
        _debug.logic("shift_unsupported", period_type=period_type)
        return None

    def _get_rounding_unit_names(self):
        currency_symbol = self.env.company.currency_id.symbol
        currency_name = self.env.company.currency_id.name

        rounding_unit_names = [
            ("decimals", (f".{currency_symbol}", "")),
            ("units", (f"{currency_symbol}", "")),
            ("thousands", (f"K{currency_symbol}", self.env._("Amounts in Thousands"))),
            ("millions", (f"M{currency_symbol}", self.env._("Amounts in Millions"))),
        ]

        if currency_name in CURRENCIES_USING_LAKH:
            rounding_unit_names.insert(
                3, ("lakhs", (f"L{currency_symbol}", self.env._("Amounts in Lakhs")))
            )

        return dict(rounding_unit_names)
