import contextlib
import datetime
from collections import defaultdict

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models, modules
from odoo.exceptions import UserError
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog
from odoo.tools import date_utils
from odoo.tools.misc import format_date

from .account_report_engine import CURRENCIES_USING_LAKH
from odoo.addons.account.tools.display_types import NON_ACCOUNTABLE_DISPLAY_TYPES

_debug = DebugLog(__name__)


class AccountReportOptions(models.Model):
    _inherit = "account.report"

    @_debug.perf.timed
    def _init_options_journals(
        self, options, previous_options, additional_journals_domain=None
    ):
        # additional_journals_domain allows calling this with an extra restriction on journals,
        # to regenerate the journal options accordingly.
        def option_value(value, selected=False, group_journals=None):
            result = {
                "id": value.id,
                "model": value._name,
                "name": value.display_name,
                "selected": selected,
            }

            if value._name == "account.journal.group":
                result.update(
                    {
                        "title": value.display_name,
                        "journals": group_journals.ids,
                        "journal_types": list(set(group_journals.mapped("type"))),
                    }
                )
            elif value._name == "account.journal":
                result.update(
                    {
                        "title": f"{value.name} - {value.code}",
                        "type": value.type,
                        "visible": True,
                    }
                )

            return result

        if not self.filter_journals:
            _debug.logic("journals_skipped", report=self, reason="filter_disabled")
            return

        previous_journals = previous_options.get("journals", [])
        previous_journal_group_action = previous_options.get(
            "__journal_group_action", {}
        )

        all_journals = self._get_filter_journals(
            options, additional_domain=additional_journals_domain
        )
        all_journal_groups = self._get_filter_journal_groups(options)

        options["journals"] = []
        options["selected_journal_groups"] = {}

        groups_journals_selected = set()
        options_journal_groups = []

        # First time opening the report, and make sure it's not specifically stated that we should not reset the filter
        is_opening_report = previous_options.get(
            "is_opening_report"
        )  # key from JS controller when report is being opened
        # a key to prevent the reset of the journals filter even when is_opening_report is True
        can_reset_journals_filter = not previous_options.get(
            "not_reset_journals_filter"
        )

        # 1. Handle journal group selection
        for group in all_journal_groups:
            group_journals = all_journals - group.excluded_journal_ids
            if group.company_id:
                company_domain = self.env["account.journal"]._check_company_domain(
                    group.company_id
                )
                group_journals = group_journals.filtered_domain(company_domain)

            selected = False
            first_group_already_selected = bool(
                options["selected_journal_groups"]
            )  # only one group should be selected at most

            # select the first group by default when opening the report
            if (
                is_opening_report
                and not first_group_already_selected
                and can_reset_journals_filter
            ):
                selected = True
            # Otherwise, select the previous selected group (if any)
            elif group.id == previous_journal_group_action.get("id"):
                selected = previous_journal_group_action.get("action") == "add"

            group_option = option_value(
                group, selected=selected, group_journals=group_journals
            )
            options_journal_groups.append(group_option)

            # Select all the group journals
            if selected:
                options["selected_journal_groups"] = group_option
                groups_journals_selected |= set(group_journals.ids)

        # 2. Handle journals selection
        previous_selected_journals_ids = {
            journal["id"]
            for journal in previous_journals
            if journal.get("model") == "account.journal" and journal.get("selected")
        }

        company_journals_map = defaultdict(list)
        journals_selected = set()

        for journal in all_journals:
            selected = False

            if journal.id in groups_journals_selected:
                selected = True

            elif (
                not options["selected_journal_groups"]
                and previous_journal_group_action.get("action") != "remove"
            ):
                if journal.id in previous_selected_journals_ids:
                    selected = True

            if selected:
                journals_selected.add(journal.id)

            company_journals_map[journal.company_id].append(
                option_value(journal, selected=journal.id in journals_selected)
            )

        # 3. Recompute selected groups in case the set of selected journals is equal to a group's accepted journals
        for group in options_journal_groups:
            if journals_selected == set(group["journals"]):
                group["selected"] = True
                options["selected_journal_groups"] = group

        # 4. Unselect all journals if all are selected and no group is specifically selected
        if (
            journals_selected == set(all_journals.ids)
            and not options["selected_journal_groups"]
        ):
            for journals in company_journals_map.values():
                for journal in journals:
                    journal["selected"] = False

        # 5. Build group options
        if all_journal_groups:
            options["journals"] = [
                {
                    "id": "divider",
                    "name": _("Multi-ledger"),
                    "model": "account.journal.group",
                }
            ] + options_journal_groups

        _debug.pipeline(
            "journals_selected",
            report=self,
            journals=len(all_journals),
            groups=len(all_journal_groups),
            selected=len(journals_selected),
            group_selected=bool(options["selected_journal_groups"]),
            is_opening_report=is_opening_report,
            can_reset=can_reset_journals_filter,
            companies=len(company_journals_map),
        )
        if not company_journals_map:
            options["name_journal_group"] = _("No Journal")
            return

        _debug.logic(
            "journals_layout_chosen",
            report=self,
            per_company=len(company_journals_map) > 1 or bool(all_journal_groups),
        )
        # 6. Build journals options
        if len(company_journals_map) > 1 or all_journal_groups:
            for company, journals in company_journals_map.items():
                # users may not have full access to the parent company in case they are in a branch, yet they have to see the company name
                company_name = company.sudo().display_name

                # if not is_opening_report, then gets the unfolded attribute of the company from the previous options
                unfolded = (
                    False
                    if is_opening_report
                    else next(
                        (
                            entry.get("unfolded")
                            for entry in previous_journals
                            if entry["model"] == "res.company"
                            and entry["name"] == company_name
                        ),
                        False,
                    )
                )

                for journal in journals:
                    journal["visible"] = unfolded

                options["journals"].append(
                    {
                        "id": "divider",
                        "model": "res.company",
                        "name": company_name,
                        "unfolded": unfolded,
                    }
                )

                options["journals"] += journals

        else:
            options["journals"].extend(next(iter(company_journals_map.values()), []))

    def _init_options_audit(self, options, previous_options):
        if not self.allow_account_audit_status_on_lines:
            return

        main_company = self._get_sender_company_for_export(options)

        date_from = options["date"]["date_from"]
        audit_return = self.env["account.return"].search_read(
            [
                ("return_type_category", "=", "audit"),
                ("company_id", "=", main_company.id),
                ("date_to", "=", options["date"]["date_to"]),
                ("date_from", "=", date_from)
                if date_from
                else ("date_from", "!=", False),
            ],
            limit=1,
            fields=["id"],
        )

        options.setdefault("audit", {})
        options["audit"]["id"] = (
            audit_return[0]["id"] if len(audit_return) > 0 else False
        )

    @_debug.perf.timed
    def _init_options_journals_names(
        self, options, previous_options, additional_journals_domain=None
    ):
        all_journals = [
            journal
            for journal in options.get("journals", [])
            if journal["model"] == "account.journal"
        ]
        journals_selected = [j for j in all_journals if j.get("selected")]
        # 1. Compute the name to display on the widget
        if options.get("selected_journal_groups"):
            names_to_display = [options["selected_journal_groups"]["name"]]
        elif len(all_journals) == len(journals_selected) or not journals_selected:
            names_to_display = [_("All Journals")]
        else:
            names_to_display = []
            for journal in options["journals"]:
                if journal.get("model") == "account.journal" and journal["selected"]:
                    names_to_display += [journal["name"]]

        # 2. Abbreviate the name
        max_nb_journals_displayed = 5
        nb_remaining = len(names_to_display) - max_nb_journals_displayed
        _debug.logic(
            "journal_names_chosen",
            report=self,
            from_group=bool(options.get("selected_journal_groups")),
            journals=len(all_journals),
            selected=len(journals_selected),
            remaining=nb_remaining,
        )
        displayed_names = ", ".join(names_to_display[:max_nb_journals_displayed])
        if nb_remaining == 1:
            options["name_journal_group"] = _(
                "%(names)s and one other", names=displayed_names
            )
        elif nb_remaining > 1:
            options["name_journal_group"] = _(
                "%(names)s and %(remaining)s others",
                names=displayed_names,
                remaining=nb_remaining,
            )
        else:
            options["name_journal_group"] = displayed_names

    @api.model
    def _get_options_journals(self, options):
        selected_journals = [
            journal
            for journal in options.get("journals", [])
            if journal["model"] == "account.journal" and journal["selected"]
        ]
        if not selected_journals:
            # If no journal is specifically selected, we actually want to select them all.
            # This is needed, because some reports will not use ALL available journals and filter by type.
            # Without getting them from the options, we will use them all, which is wrong.
            selected_journals = [
                journal
                for journal in options.get("journals", [])
                if journal["model"] == "account.journal"
            ]
        return selected_journals

    @api.model
    def _get_domain_options_journals(self, options):
        # Make sure to return an empty array when nothing selected to handle archived journals.
        selected_journals = self._get_options_journals(options)
        return (
            Domain("journal_id", "in", [j["id"] for j in selected_journals])
            if selected_journals
            else Domain.TRUE
        )

    # ####################################################
    # OPTIONS: USER DEFINED FILTERS ON AML
    ####################################################
    def _init_options_aml_ir_filters(self, options, previous_options):
        options["aml_ir_filters"] = []
        if not self.filter_aml_ir_filters:
            _debug.logic(
                "aml_ir_filters_skipped", report=self, reason="filter_disabled"
            )
            return

        ir_filters = self.env["ir.filters"].search(
            [("model_id", "=", "account.move.line")]
        )
        if not ir_filters:
            _debug.logic("aml_ir_filters_empty", report=self)
            return

        aml_ir_filters = [
            {"id": x.id, "name": x.name, "selected": False} for x in ir_filters
        ]
        previous_options_aml_ir_filters = previous_options.get("aml_ir_filters", [])
        previous_options_filters_map = {
            filter_item["id"]: filter_item
            for filter_item in previous_options_aml_ir_filters
        }

        for filter_item in aml_ir_filters:
            if filter_item["id"] in previous_options_filters_map:
                filter_item["selected"] = previous_options_filters_map[
                    filter_item["id"]
                ]["selected"]

        options["aml_ir_filters"] = aml_ir_filters
        _debug.pipeline(
            "aml_ir_filters_built",
            report=self,
            filters=len(aml_ir_filters),
            previous=len(previous_options_filters_map),
        )

    @api.model
    def _get_options_aml_ir_filters(self, options):
        selected_filters_ids = [
            filter_item["id"]
            for filter_item in options.get("aml_ir_filters", [])
            if filter_item["selected"]
        ]

        if not selected_filters_ids:
            return Domain.TRUE

        selected_ir_filters = self.env["ir.filters"].browse(selected_filters_ids)
        return Domain.OR(
            filter_record._get_domain_evaluated()
            for filter_record in selected_ir_filters
        )

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
                date_from = self.env.company.compute_fiscalyear_dates(date_to)[
                    "date_from"
                ]
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
        # In case if the return_period is asked but not return type exist for this report
        if "return_period" in options_filter and not options.get("return_periodicity"):
            _debug.logic("return_period_fallback", report=self, filter=options_filter)
            options_filter = "this_month"
        elif (
            "return_period" in options_filter
        ):  # In case if the return_period is asked but it is not shown as it is a similar period than those from the default filters, we fallback
            months_per_period = options["return_periodicity"]["months_per_period"]
            start_day = options["return_periodicity"]["start_day"]
            start_month = options["return_periodicity"]["start_month"]

            if (
                "fy_start_day" not in options["return_periodicity"]
                or "fy_start_month" not in options["return_periodicity"]
            ):
                fy_start = self.env.company.compute_fiscalyear_dates(
                    fields.Date.from_string(period_date_to)
                    if period_date_to
                    else fields.Date.context_today(self)
                )["date_from"]
                options["return_periodicity"]["fy_start_day"] = fy_start.day
                options["return_periodicity"]["fy_start_month"] = fy_start.month

            if start_day == 1 and start_month == 1 and months_per_period in (1, 3):
                match months_per_period:
                    case 1:
                        options_filter = (
                            "custom_month" if period_date_to else "previous_month"
                        )
                    case 3:
                        options_filter = (
                            "custom_quarter" if period_date_to else "previous_quarter"
                        )
            elif (
                start_day == options["return_periodicity"]["fy_start_day"]
                and start_month == options["return_periodicity"]["fy_start_month"]
                and months_per_period == 12
            ):
                options_filter = "custom_year" if period_date_to else "previous_year"
            else:
                options["return_periodicity"]["is_filter_visible"] = True

        # Compute 'date_from' / 'date_to'.
        if not date_from or not date_to:
            if options_filter == "today":
                date_to = fields.Date.context_today(self)
                date_from = self.env.company.compute_fiscalyear_dates(date_to)[
                    "date_from"
                ]
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
                company_fiscalyear_dates = self.env.company.compute_fiscalyear_dates(
                    fields.Date.context_today(self)
                )
                curr_year = fields.Date.context_today(self).year
                if company_fiscalyear_dates["date_from"].year < curr_year:
                    company_fiscalyear_dates = (
                        self.env.company.compute_fiscalyear_dates(
                            company_fiscalyear_dates["date_to"] + relativedelta(days=1)
                        )
                    )
                date_from = company_fiscalyear_dates["date_from"]
                date_to = company_fiscalyear_dates["date_to"]
            elif "return_period" in options_filter:
                if period_date_from and "custom_return_period" in options_filter:
                    date_from = fields.Date.to_date(period_date_from)
                    date_to = fields.Date.to_date(period_date_to)
                else:
                    if "custom_return_period" in options_filter:
                        base_date = fields.Date.to_date(period_date_to)
                    else:
                        base_date = fields.Date.context_today(self)
                    return_type = self.env["account.return.type"].browse(
                        options["return_periodicity"]["return_type_id"]
                    )
                    date_from, date_to = return_type._get_period_boundaries(
                        self.env.company, base_date
                    )
                period_type = "return_period"

        # When the return period matches a standard date filter, fallback to the standard. This way, we can avoid displaying the return period
        # filter in the UI, and only rely on the standard ones. This condition ensures the conversion from one filter to the other.
        if options_filter in {"custom_month", "custom_quarter", "custom_year"}:
            options_date = fields.Date.from_string(period_date_to)
            diff_years = options_date.year - date_to.year
            offsetted_date = options_date + relativedelta(years=diff_years)
            diff_months = offsetted_date.month - date_to.month
            diff_months += diff_years * 12

            months_per_period = options["return_periodicity"]["months_per_period"]

            if options_date > date_to:
                prefix = "next"
            elif options_date < date_to:
                prefix = "previous"
            else:
                prefix = "this"

            match months_per_period:
                case 1:
                    date["period"] = diff_months
                    options_filter = f"{prefix}_month"
                case 3:
                    date["period"] = diff_months // months_per_period
                    options_filter = f"{prefix}_quarter"
                case 12:
                    date["period"] = diff_months // months_per_period
                    options_filter = f"{prefix}_year"

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

        if "custom_return_period" in options_filter:
            # In case we use a custom period we still use the return_period filter. In that case we still need the shift so we need to compute it manually.
            return_type = self.env["account.return.type"].browse(
                options["return_periodicity"]["return_type_id"]
            )
            current_date_to = return_type._get_period_boundaries(
                self.env.company, fields.Date.context_today(self)
            )[1]
            delta = relativedelta(
                fields.Date.from_string(options["date"]["date_to"]), current_date_to
            )
            months = delta.years * 12 + delta.months
            diffs = months // options["return_periodicity"]["months_per_period"]
            options["date"]["period"] = diffs

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
    def _init_options_return_periodicity(self, options, previous_options):
        if (
            previous_options.get("return_periodicity")
            and previous_options["return_periodicity"].get("return_type_id")
            and previous_options["return_periodicity"].get("report_id")
            in (False, self.id, options["sections_source_id"])
        ):
            options["return_periodicity"] = {
                **previous_options["return_periodicity"],
                "report_id": self.id,
            }
            _debug.logic(
                "return_periodicity_kept",
                report=self,
                return_type_id=options["return_periodicity"].get("return_type_id"),
            )
        elif (
            len(
                return_type := self.env["account.report"]
                .browse(options["sections_source_id"])
                .return_type_ids
            )
            == 1
            or "selected_return_type_id" in previous_options
        ):
            if len(return_type) > 1:
                return_type = self.env["account.return.type"].browse(
                    previous_options["selected_return_type_id"]
                )

            main_company = self.env.company
            start_day, start_month = return_type._get_start_date_elements(main_company)
            options["return_periodicity"] = {
                "periodicity": return_type._get_periodicity(main_company),
                "months_per_period": return_type._get_periodicity_months_delay(
                    main_company
                ),
                "start_day": start_day,
                "start_month": start_month,
                "return_type_id": return_type.id,
                "report_id": self.id,
            }
            _debug.logic(
                "return_periodicity_from_type",
                report=self,
                return_type=return_type,
                months_per_period=options["return_periodicity"]["months_per_period"],
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

        if self.filter_budgets and any(
            budget["selected"] for budget in options.get("budgets", [])
        ):
            options["column_percent_comparison"] = "budget"
        _debug.logic(
            "percent_comparison_chosen",
            report=self,
            mode=options.get("column_percent_comparison"),
        )

    def _get_domain_options_date(self, options, date_scope):
        date_from, date_to = self._get_date_bounds_info(options, date_scope)

        scope_domain = Domain("date", "<=", date_to)
        if date_from:
            scope_domain &= Domain("date", ">=", date_from)

        return scope_domain

    def _init_options_analytic(self, options, previous_options):
        if not self.filter_analytic:
            return

        if self.env.user.has_group("analytic.group_analytic_accounting"):
            previous_analytic_accounts = previous_options.get("analytic_accounts", [])
            analytic_account_ids = [int(x) for x in previous_analytic_accounts]
            selected_analytic_accounts = (
                self.env["account.analytic.account"]
                .with_context(active_test=False)
                .search([("id", "in", analytic_account_ids)])
            )

            options["display_analytic"] = True
            options["analytic_accounts"] = selected_analytic_accounts.ids
            options["selected_analytic_account_names"] = (
                selected_analytic_accounts.mapped("name")
            )
            _debug.pipeline(
                "analytic_accounts_selected",
                report=self,
                requested=len(analytic_account_ids),
                accounts=selected_analytic_accounts,
            )

    def _init_options_partner(self, options, previous_options):
        if not self.filter_partner:
            return

        options["partner"] = True
        previous_partner_ids = previous_options.get("partner_ids") or []
        options["partner_categories"] = previous_options.get("partner_categories") or []

        selected_partner_ids = [int(partner) for partner in previous_partner_ids]
        # search instead of browse so that record rules apply and filter out the ones the user does not have access to
        selected_partners = (
            selected_partner_ids
            and self.env["res.partner"]
            .with_context(active_test=False)
            .search([("id", "in", selected_partner_ids)])
        ) or self.env["res.partner"]
        options["selected_partner_ids"] = selected_partners.mapped("display_name")
        options["partner_ids"] = selected_partners.ids

        selected_partner_tag_ids = [
            int(category) for category in options["partner_categories"]
        ]
        selected_partner_categories = (
            selected_partner_tag_ids
            and self.env["res.partner.tag"].browse(selected_partner_tag_ids)
        ) or self.env["res.partner.tag"]
        options["selected_partner_categories"] = selected_partner_categories.mapped(
            "name"
        )

    @api.model
    def _get_domain_options_partner(self, options):
        domains = []
        if options.get("partner_ids"):
            partner_ids = [int(partner) for partner in options["partner_ids"]]
            domains.append(Domain("partner_id", "in", partner_ids))
        if options.get("partner_categories"):
            partner_tag_ids = [
                int(category) for category in options["partner_categories"]
            ]
            domains.append(Domain("partner_id.tag_ids", "in", partner_tag_ids))
        return Domain.AND(domains)

    @api.model
    def _get_domain_options_all_entries(self, options):
        if not options.get("all_entries"):
            return Domain("parent_state", "=", "posted")
        else:
            return Domain("parent_state", "!=", "cancel")

    ####################################################
    # OPTIONS: not reconciled entries
    ####################################################
    def _init_options_reconciled(self, options, previous_options):
        if self.filter_unreconciled:
            options["unreconciled"] = previous_options.get("unreconciled", False)
        else:
            options["unreconciled"] = False

    @api.model
    def _get_domain_options_unreconciled(self, options):
        if options.get("unreconciled"):
            return Domain("full_reconcile_id", "=", False) & Domain(
                "balance", "!=", "0"
            )
        return Domain.TRUE

    @_debug.perf.timed
    def _init_options_account_type(self, options, previous_options):
        """Initialize a filter based on the account_type of the line (trade/non trade, payable/receivable).

        The group display name is derived from the display names of the selected options.
        """
        if self.filter_account_type in ("disabled", False):
            _debug.logic("account_type_skipped", report=self, reason="filter_disabled")
            return

        account_type_list = [
            {"id": "trade_receivable", "name": _("Receivable"), "selected": True},
            {
                "id": "non_trade_receivable",
                "name": _("Non Trade Receivable"),
                "selected": False,
            },
            {"id": "trade_payable", "name": _("Payable"), "selected": True},
            {
                "id": "non_trade_payable",
                "name": _("Non Trade Payable"),
                "selected": False,
            },
        ]

        if self.filter_account_type == "receivable":
            options["account_type"] = account_type_list[:2]
        elif self.filter_account_type == "payable":
            options["account_type"] = account_type_list[2:]
        else:
            options["account_type"] = account_type_list

        _debug.logic(
            "account_type_scope_chosen",
            report=self,
            filter=self.filter_account_type,
            choices=len(options["account_type"]),
            from_previous=bool(previous_options.get("account_type")),
        )
        if previous_options.get("account_type"):
            previously_selected_ids = {
                x["id"] for x in previous_options["account_type"] if x.get("selected")
            }
            for opt in options["account_type"]:
                opt["selected"] = opt["id"] in previously_selected_ids

    @api.model
    def _get_domain_options_account_type(self, options):
        all_domains = []
        selected_domains = []
        for opt in options.get("account_type") or []:
            account_type_filter = self.ACCOUNT_TYPE_FILTER_DOMAINS.get(opt["id"])
            if not account_type_filter:
                # options reach this method straight from the client, so an unknown id is
                # reachable input rather than a programming error.
                continue
            non_trade, account_type = account_type_filter
            domain = [
                ("account_id.non_trade", "=", non_trade),
                ("account_id.account_type", "=", account_type),
            ]
            if opt.get("selected"):
                selected_domains.append(domain)
            all_domains.append(domain)
        _debug.logic(
            "account_type_domain",
            selected=len(selected_domains),
            available=len(all_domains),
        )
        if not all_domains:
            return Domain.TRUE
        return Domain.OR(selected_domains or all_domains)

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

    def _init_options_hierarchy(self, options, previous_options):
        company_ids = self.get_report_company_ids(options)
        if self.filter_hierarchy != "never" and self.env["account.group"].search_count(
            self.env["account.group"]._check_company_domain(company_ids), limit=1
        ):
            options["display_hierarchy_filter"] = True
            if "hierarchy" in previous_options:
                options["hierarchy"] = previous_options["hierarchy"]
            else:
                options["hierarchy"] = self.filter_hierarchy == "by_default"
        else:
            options["hierarchy"] = False
            options["display_hierarchy_filter"] = False

    def _init_options_prefix_groups_threshold(self, options, previous_options):
        options["prefix_groups_threshold"] = self.prefix_groups_threshold

    def _init_options_companies(self, options, previous_options):
        if previous_options.get("forced_companies"):
            options["forced_companies"] = previous_options["forced_companies"]
            companies = self.env.company.browse(previous_options["forced_companies"])
        elif self.filter_multi_company == "tax_units":
            companies = self._multi_company_tax_units_init_options(
                options, previous_options=previous_options
            )
        else:
            # self.filter_multi_company == 'selector'
            companies = self.env.companies

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

    @_debug.perf.timed
    def _multi_company_tax_units_init_options(self, options, previous_options):
        """Initializes the companies option for reports configured to compute it from tax units."""
        available_tax_units = self.env.company._get_available_tax_units(self)

        # Filter available units to only consider the ones whose companies are all accessible to the user
        available_tax_units = available_tax_units.filtered(
            lambda x: all(
                unit_company in self.env.user.company_ids
                for unit_company in x.sudo().company_ids
            )
            # sudo() to avoid bypassing companies the current user does not have access to
        )

        options["available_tax_units"] = [
            {
                "id": tax_unit.id,
                "name": tax_unit.name,
                "company_ids": tax_unit.company_ids.ids,
            }
            for tax_unit in available_tax_units
        ]

        # Available tax_unit option values that are currently allowed by the company selector
        # A js hack ensures the page is reloaded and the selected companies modified
        # when clicking on a tax unit option in the UI, so we don't need to worry about that here.
        companies_authorized_tax_unit_opt = {
            *(
                available_tax_units.filtered(
                    lambda x: set(self.env.companies) == set(x.company_ids)
                ).ids
            ),
            "company_only",
        }

        if previous_options.get("tax_unit") in companies_authorized_tax_unit_opt:
            options["tax_unit"] = previous_options["tax_unit"]

        # No tax_unit gotten from previous options; initialize it
        # A tax_unit will be set by default if only one tax unit is available for the report
        # (which should always be true for non-generic reports, which have a country), and the companies of
        # the unit are the only ones currently selected.
        elif companies_authorized_tax_unit_opt == {"company_only"}:
            options["tax_unit"] = "company_only"
        elif (
            len(available_tax_units) == 1
            and available_tax_units[0].id in companies_authorized_tax_unit_opt
        ):
            options["tax_unit"] = available_tax_units[0].id
        else:
            options["tax_unit"] = "company_only"

        _debug.logic(
            "tax_unit_chosen",
            report=self,
            tax_unit=options["tax_unit"],
            previous_tax_unit=previous_options.get("tax_unit"),
            available=len(available_tax_units),
            authorized=len(companies_authorized_tax_unit_opt),
        )
        # Finally initialize multi_company filter
        if options["tax_unit"] == "company_only":
            companies = self.env.company._get_branches_with_same_vat(
                accessible_only=True
            )
        else:
            tax_unit = available_tax_units.filtered(
                lambda x: x.id == options["tax_unit"]
            )
            companies = tax_unit.company_ids

        _debug.pipeline("tax_unit_companies", report=self, companies=companies)
        return companies

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
    # OPTIONS: CURRENCY TABLE
    ####################################################
    @_debug.perf.timed
    def _init_options_currency_table(self, options, previous_options):
        companies = self.env["res.company"].browse(self.get_report_company_ids(options))
        table_type = (
            "monocurrency"
            if self.env["res.currency"]._is_currency_table_monocurrency(companies)
            else self.currency_translation
        )

        periods = {}
        for col_group in options["column_groups"].values():
            if col_group["forced_options"].get("no_impact_on_currency_table"):
                # This key is used to ignore the colum group in the creation of the periods list for
                # the currency table. This way, its dates won't influence. It's useful for groups corresponding
                # to an initial balance of some sorts, like on the Trial Balance.
                continue

            col_group_date = col_group["forced_options"].get("date", options["date"])

            col_group_date_from = (
                col_group_date["date_from"]
                if col_group_date["mode"] == "range"
                else None
            )
            col_group_date_to = col_group_date["date_to"]
            period_key = col_group_date["currency_table_period_key"]

            already_present_period = periods.get(period_key)
            if already_present_period:
                # This can happen for custom reports, needing to enforce the same rates on multiple column groups with
                # different dates (e.g. Trial Balance). In that case, the date_from and date_to of the currency table period must respectively
                # be the lowest and highest among those groups.
                if (
                    col_group_date_from
                    and already_present_period["from"] > col_group_date_from
                ):
                    already_present_period["from"] = col_group_date_from

                already_present_period["to"] = max(
                    already_present_period["to"], col_group_date_to
                )
            else:
                periods[period_key] = {
                    "from": col_group_date_from,
                    "to": col_group_date_to,
                }

        options["currency_table"] = {"type": table_type, "periods": periods}
        _debug.logic(
            "currency_table_chosen",
            report=self,
            table_type=table_type,
            companies=companies,
            column_groups=len(options["column_groups"]),
            periods=len(periods),
        )

    ####################################################
    # OPTIONS: ROUNDING UNIT
    ####################################################
    def _init_options_rounding_unit(self, options, previous_options):
        default = "decimals"
        options["rounding_unit"] = previous_options.get("rounding_unit", default)
        options["rounding_unit_names"] = self._get_rounding_unit_names()

    # ####################################################
    # OPTIONS: ALL ENTRIES
    ####################################################
    def _init_options_all_entries(self, options, previous_options):
        if self.filter_show_draft:
            options["all_entries"] = previous_options.get("all_entries", False)
        else:
            options["all_entries"] = False

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
        options["available_horizontal_groups"] = [
            {
                "id": horizontal_group.id,
                "name": horizontal_group.name,
            }
            for horizontal_group in self.horizontal_group_ids
        ]
        previous_selected = previous_options.get("selected_horizontal_group_id")
        options["selected_horizontal_group_id"] = (
            previous_selected
            if previous_selected in self.horizontal_group_ids.ids
            else None
        )

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
                    "name": _("Period Total"),
                    "forced_options": {
                        "budget_base": True,
                        "no_subheader_division": True,
                    },
                    "colspan": len(self.column_ids),
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
                        self.column_ids.filtered(
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
            and len(self.column_ids) == 1
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
                "name": _("PDF"),
                "sequence": 10,
                "action": "export_file",
                "action_param": "export_to_pdf",
                "file_export_type": _("PDF"),
                "branch_allowed": True,
                "always_show": True,
            },
            {
                "name": _("XLSX"),
                "sequence": 20,
                "action": "export_file",
                "action_param": "export_to_xlsx",
                "file_export_type": _("XLSX"),
                "branch_allowed": True,
                "always_show": True,
            },
        ]

        if self.return_type_ids and self.env.user.has_group(
            "account.group_account_user"
        ):
            options["buttons"].append(
                {
                    "name": _("Returns"),
                    "action": "action_view_returns",
                    "sequence": 110,
                    "always_show": True,
                    "branch_allowed": True,
                }
            )
        _debug.pipeline("buttons_built", report=self, buttons=len(options["buttons"]))

    def _init_options_section_buttons(self, options, previous_options):
        """In case we're displaying a section, we want to replace its buttons by its source report's. This needs to be done last, after calling the
        custom handler, to avoid its _custom_options_initializer function to generate additional buttons.
        """
        if options["sections_source_id"] != self.id:
            # We need to re-call a full get_options in case a custom options initializer adds new buttons depending on other options.
            # This way, we're sure we always get all buttons that are needed.
            sections_source = self.env["account.report"].browse(
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
            previous_section_source = self.env["account.report"].browse(
                previous_section_source_id
            )
            if self in previous_section_source.section_report_ids:
                options["variants_source_id"] = (
                    previous_section_source.root_report_id or previous_section_source
                ).id
                allowed_variant_ids.add(previous_section_source_id)

        if "variants_source_id" not in options:
            options["variants_source_id"] = (self.root_report_id or self).id

        available_variants = self.env["account.report"]
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
            country_id = self.env.company.account_config_id.account_fiscal_country_id.id
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

        source_report = self.env["account.report"].browse(options["sections_source_id"])

        available_sections = (
            source_report.section_report_ids
            if source_report.use_sections
            else self.env["account.report"]
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
            self.env["account.report"]
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
    # OPTIONS: BUDGETS
    ####################################################
    def _init_options_budgets(self, options, previous_options):
        if self.filter_budgets:
            previous_selection = {
                budget_option["id"]
                for budget_option in previous_options.get("budgets", [])
                if budget_option.get("selected")
            }

            options["budgets"] = [
                {
                    "id": budget.id,
                    "name": budget.name,
                    "selected": budget.id in previous_selection,
                    "company_id": budget.company_id.id,
                }
                # Every company the report itself has selected, not just the
                # active one: the entries carry a company_id precisely because
                # several companies' budgets can coexist here, and the record
                # rule already narrows the result to what the user may see.
                for budget in self.env["account.report.budget"].search(
                    [("company_id", "in", self.env.companies.ids)]
                )
            ]
            options["show_all_accounts"] = (
                previous_options.get("show_all_accounts") or False
            )

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
    # OPTIONS: READONLY QUERY
    ####################################################
    def _init_options_readonly_query(self, options, previous_options):
        options["readonly_query"] = options["currency_table"]["type"] == "monocurrency"

    ####################################################
    # OPTIONS: FILTERS
    ####################################################
    def _init_options_filters(self, options, previous_options):
        options["filters"] = {
            "show_all": self.filter_unfold_all,
            "show_analytic": options.get("display_analytic", False),
            "show_analytic_groupby": options.get("display_analytic_groupby", False),
            "show_analytic_plan_groupby": options.get(
                "display_analytic_plan_groupby", False
            ),
            "show_draft": self.filter_show_draft,
            "show_hierarchy": options.get("display_hierarchy_filter", False),
            "show_period_comparison": self.filter_period_comparison,
            "show_totals": self.env.company.account_config_id.totals_below_sections
            and not options.get("ignore_totals_below_sections"),
            "show_unreconciled": self.filter_unreconciled,
            "show_hide_0_lines": self.filter_hide_0_lines,
        }

    ####################################################
    # OPTIONS: USER GROUPS
    ####################################################
    def _init_options_user_groups(self, options, previous_options):
        options["user_groups"] = {
            "analytic_accounting": self.env.user.has_group(
                "analytic.group_analytic_accounting"
            ),
            "account_readonly": self.env.user.has_group(
                "account.group_account_readonly"
            ),
            "account_user": self.env.user.has_group("account.group_account_user"),
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
                self.env["account.report"]
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

        options_companies = self.env["res.company"].browse(
            self.get_report_company_ids(options)
        )
        # Set export buttons to 'branch_allowed' if the currently selected company branches all share the same VAT
        # number and no unselected sub-branch of the active company has the same VAT number. Companies with an empty VAT
        # field will be considered as having the same VAT number as their closest parent with a non-empty VAT.
        if options.get("enable_export_buttons_for_common_vat_in_branches"):
            report_accepted_company_ids = set(options_companies.ids)
            same_vat_branch_ids = set(
                self.env.company._get_branches_with_same_vat().ids
            )
            if report_accepted_company_ids == same_vat_branch_ids:
                options["buttons"] = [
                    {**button, "branch_allowed": button.get("branch_allowed", True)}
                    for button in options["buttons"]
                ]

        # Disable buttons without branch_allowed = True if not all branches are selected
        if not options_companies._is_every_branch_selected():
            for button in filter(
                lambda x: not x.get("branch_allowed"), options["buttons"]
            ):
                button["error_action"] = "show_error_branch_allowed"

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
            key=lambda x: forced_sequence_map.get(x, forced_sequence_map.get("default"))
        )

        return initializers

    @_debug.perf.timed
    def _get_options_initializers_forced_sequence_map(self):
        """By default, not specific order is ensured for the filters when calling _get_options_initializers_in_sequence.
        This function allows giving them a sequence number. It can be overridden
        to make filters depend on each other.

        :return: dict(str, int): str is the filter name, int is its sequence (lowest = first).
                                 Multiple filters may share the same sequence, their relative order is then not guaranteed.
        """
        return {
            self._init_options_companies: 10,
            self._init_options_variants: 15,
            self._init_options_sections: 16,
            self._init_options_report_id: 17,
            self._init_options_return_periodicity: 29,
            self._init_options_date: 30,
            self._init_options_horizontal_groups: 40,
            self._init_options_comparison: 50,
            self._init_options_export_mode: 60,
            self._init_options_integer_rounding: 70,
            self._init_options_consolidation: 75,
            self._init_options_journals: 80,
            self._init_options_journals_names: 90,
            self._init_options_audit: 100,
            "default": 200,
            self._init_options_column_headers: 990,
            self._init_options_columns: 1000,
            self._init_options_column_percent_comparison: 1010,
            self._init_options_order_column: 1020,
            self._init_options_hierarchy: 1030,
            self._init_options_prefix_groups_threshold: 1040,
            self._init_options_custom: 1050,
            self._init_options_currency_table: 1055,
            self._init_options_section_buttons: 1060,
            self._init_options_readonly_query: 1070,
            self._init_options_filters: 1500,
        }

    @_debug.perf.timed
    def _get_domain_options(self, options, date_scope) -> Domain:
        self.check_singleton()

        available_scopes = dict(
            self.env["account.report.expression"]._fields["date_scope"].selection
        )
        if (
            date_scope and date_scope not in available_scopes
        ):  # date_scope can be passed to None explicitly to ignore the dates
            raise UserError(_("Unknown date scope: %s", date_scope))

        domains = [
            Domain("display_type", "not in", NON_ACCOUNTABLE_DISPLAY_TYPES),
            Domain("company_id", "in", self.get_report_company_ids(options)),
            self._get_domain_options_journals(options)
            if not options.get("compute_budget")
            else Domain.TRUE,
            self._get_domain_options_date(options, date_scope)
            if date_scope
            else Domain.TRUE,
            self._get_domain_options_partner(options),
            self._get_domain_options_all_entries(options),
            self._get_domain_options_unreconciled(options),
            self._get_domain_options_account_type(options),
            self._get_options_aml_ir_filters(options),
            self.env["account.move.line"]._get_domain_tax_exigible()
            if self.only_tax_exigible
            else Domain.TRUE,
            # That option key is set when splitting options between column groups
            options.get("forced_domain") or Domain.TRUE,
        ]
        _debug.pipeline(
            "domain_options_built",
            report=self,
            date_scope=date_scope,
            journals_filtered=not options.get("compute_budget"),
            tax_exigible_only=self.only_tax_exigible,
            forced_domain=bool(options.get("forced_domain")),
            foreign_vat=self.allow_foreign_vat,
        )

        # Handle foreign VAT
        if self.allow_foreign_vat:
            if (
                self.country_id
                == self.env.company.account_config_id.account_fiscal_country_id
            ):
                _debug.logic("foreign_vat_scope", report=self, scope="domestic")
                # It's a domestic report
                domains.append(
                    [
                        "|",
                        "|",
                        ("move_id.fiscal_position_id", "=", False),
                        ("move_id.fiscal_position_id.foreign_vat", "=", False),
                        (
                            "tax_tag_ids.country_id",
                            "=",
                            self.country_id.id,
                        ),  # To allow setting loca tags on an operation made nor another country (sometimes legally necessary)
                    ]
                )
            elif self.country_id:
                _debug.logic("foreign_vat_scope", report=self, scope="foreign")
                # It's a foreign report
                domains.append(
                    [
                        "|",
                        (
                            "tax_tag_ids.country_id",
                            "=",
                            self.country_id.id,
                        ),  # To allow setting loca tags on an operation made nor another country (sometimes legally necessary)
                        "&",
                        (
                            "move_id.fiscal_position_id.country_id",
                            "=",
                            self.country_id.id,
                        ),
                        ("move_id.fiscal_position_id.foreign_vat", "!=", False),
                    ]
                )
            # else: don't filter anything; the report has no county and should have access to all the data

        return Domain.AND(domains)

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
            date_tmp = self.env.company.compute_fiscalyear_dates(date_tmp)["date_from"]
            date_from = date_tmp.strftime("%Y-%m-%d")

        elif date_scope == "to_beginning_of_fiscalyear":
            date_tmp = fields.Date.from_string(date_to)
            date_tmp = self.env.company.compute_fiscalyear_dates(date_tmp)[
                "date_from"
            ] - relativedelta(days=1)
            date_to = date_tmp.strftime("%Y-%m-%d")
            date_from = None

        elif date_scope == "previous_return_period":
            return_types = self.return_type_ids  # Might be empty ; if so, we'll call the functions on an empty recordset and fallback to company periodicity

            _debug.logic(
                "previous_return_period_scope",
                report=self,
                return_types=return_types,
            )
            if len(return_types) > 1:
                if len(set(return_types.mapped("deadline_periodicity"))) > 1:
                    raise UserError(
                        _(
                            "'%s' date scope cannot be evaluated for a report used by multiple return types using different periodicities.",
                            dict(
                                self.env["account.report.expression"]
                                ._fields["date_scope"]
                                ._description_selection(self.env)
                            )["previous_return_period"],
                        )
                    )
                return_types = return_types[0]

            current_period_start, _current_period_end = (
                return_types._get_period_boundaries(
                    self.env.company,
                    fields.Date.from_string(options["date"]["date_from"]),
                )
            )
            eve_of_period_start = current_period_start - relativedelta(days=1)
            date_from, date_to = return_types._get_period_boundaries(
                self.env.company, eve_of_period_start
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
            company_fiscalyear_dates = self.env.company.compute_fiscalyear_dates(date)
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
            company_fiscalyear_dates = self.env.company.compute_fiscalyear_dates(date)
            record = company_fiscalyear_dates.get("record")
            string = record and record.name
        elif period_type == "return_period" and options_return:
            day = options_return["start_day"]
            month = options_return["start_month"]
            string = self.env["account.return.type"]._get_period_name(
                period_from=fields.Date.to_string(date_from),
                period_to=fields.Date.to_string(date_to),
                start_day=day,
                start_month=month,
            )

        if not string:
            fy_day = self.env.company.account_config_id.fiscalyear_last_day
            fy_month = int(self.env.company.account_config_id.fiscalyear_last_month)
            if mode == "single":
                string = _("As of %s", format_date(self.env, date_to))
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
                string = _(
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
        if return_period or "return_period" in period_type:
            month_per_period = options["return_periodicity"]["months_per_period"]
            return_type = self.env["account.return.type"].browse(
                options["return_periodicity"]["return_type_id"]
            )
            date_from, date_to = return_type._get_period_boundaries(
                self.env.company,
                date_from + relativedelta(months=month_per_period * periods),
            )
            return self._get_dates_period(
                date_from,
                date_to,
                mode,
                period_type="return_period",
                options_return=options["return_periodicity"],
            )
        if period_type in ("fiscalyear", "today"):
            # Don't pass the period_type to _get_dates_period to be able to retrieve the account.fiscal.year record if
            # necessary.
            company_fiscalyear_dates = {}
            # This loop is needed because a fiscal year can be a month, quarter, etc
            for _ in range(abs(periods)):
                date_to = (date_from if periods < 0 else date_to) + relativedelta(
                    days=periods / abs(periods)
                )
                company_fiscalyear_dates = self.env.company.compute_fiscalyear_dates(
                    date_to
                )
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

    def _get_filter_journals(self, options, additional_domain=None):
        return (
            self.env["account.journal"]
            .with_context(active_test=False)
            .search(
                [
                    *self.env["account.journal"]._check_company_domain(
                        self.get_report_company_ids(options)
                    ),
                    *(additional_domain or []),
                ],
                order="company_id, name",
            )
        )

    def _get_filter_journal_groups(self, options):
        return self.env["account.journal.group"].search(
            [
                *self.env["account.journal.group"]._check_company_domain(
                    self.get_report_company_ids(options)
                ),
            ],
            order="sequence",
        )

    def _get_rounding_unit_names(self):
        currency_symbol = self.env.company.currency_id.symbol
        currency_name = self.env.company.currency_id.name

        rounding_unit_names = [
            ("decimals", (f".{currency_symbol}", "")),
            ("units", (f"{currency_symbol}", "")),
            ("thousands", (f"K{currency_symbol}", _("Amounts in Thousands"))),
            ("millions", (f"M{currency_symbol}", _("Amounts in Millions"))),
        ]

        if currency_name in CURRENCIES_USING_LAKH:
            rounding_unit_names.insert(
                3, ("lakhs", (f"L{currency_symbol}", _("Amounts in Lakhs")))
            )

        return dict(rounding_unit_names)
