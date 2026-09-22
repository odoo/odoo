import bisect
import datetime
import itertools
import re
from collections import defaultdict
from collections.abc import Collection

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Command, Domain
from odoo.libs.debug_log import DebugLog
from odoo.tools import SQL, date_utils
from odoo.tools.misc import format_date

from odoo.addons.account.tools.display_types import NON_ACCOUNTABLE_DISPLAY_TYPES
from odoo.addons.account.tools.report_engines import (
    ACCOUNT_CODES_ENGINE_SPLIT_REGEX,
    ACCOUNT_CODES_ENGINE_TAG_ID_PREFIX_REGEX,
    ACCOUNT_CODES_ENGINE_TERM_REGEX,
    LEDGER_ENGINES,
    UNDISTR_LINE_NAME,
)
from odoo.addons.report_formula.models.account_report import (
    report_option_filter_field,
)

_debug = DebugLog(__name__)


class AccountReport(models.Model):
    _inherit = "report.formula"

    chart_template = fields.Selection(
        selection=lambda self: self.env[
            "account.chart.template"
        ]._select_chart_template(),
        string="Chart of Accounts",
    )
    only_tax_exigible = report_option_filter_field(
        fields.Boolean, "only_tax_exigible", "Only Tax Exigible Lines"
    )
    allow_foreign_vat = report_option_filter_field(
        fields.Boolean, "allow_foreign_vat", "Allow Foreign VAT"
    )
    currency_translation = report_option_filter_field(
        fields.Selection,
        "currency_translation",
        default="cta",
        selection=[
            ("current", "Use the most recent rate at the date of the report"),
            ("cta", "Use CTA"),
        ],
    )
    filter_multi_company = report_option_filter_field(
        fields.Selection,
        "filter_multi_company",
        "Multi-Company",
        default="selector",
        selection=[
            ("selector", "Use Company Selector"),
            ("tax_units", "Use Tax Units"),
        ],
    )
    filter_show_draft = report_option_filter_field(
        fields.Boolean,
        "filter_show_draft",
        "Draft Entries",
        default=True,
    )
    filter_unreconciled = report_option_filter_field(
        fields.Boolean,
        "filter_unreconciled",
        "Unreconciled Entries",
        default=False,
    )
    filter_journals = report_option_filter_field(
        fields.Boolean, "filter_journals", "Journals"
    )
    filter_analytic = report_option_filter_field(
        fields.Boolean, "filter_analytic", "Analytic Filter"
    )
    filter_hierarchy = report_option_filter_field(
        fields.Selection,
        "filter_hierarchy",
        "Account Groups",
        default="optional",
        selection=[
            ("by_default", "Enabled by Default"),
            ("optional", "Optional"),
            ("never", "Never"),
        ],
    )
    filter_account_type = report_option_filter_field(
        fields.Selection,
        "filter_account_type",
        "Account Types",
        default="disabled",
        selection=[
            ("both", "Payable and receivable"),
            ("payable", "Payable"),
            ("receivable", "Receivable"),
            ("disabled", "Disabled"),
        ],
    )
    filter_partner = report_option_filter_field(
        fields.Boolean, "filter_partner", "Partners"
    )
    filter_aml_ir_filters = report_option_filter_field(
        fields.Boolean,
        "filter_aml_ir_filters",
        "Favorite Filters",
        help="If activated, user-defined filters on journal items can be selected on this report",
    )
    filter_budgets = report_option_filter_field(
        fields.Boolean, "filter_budgets", "Budgets"
    )
    default_opening_date_filter = fields.Selection(
        selection_add=[
            ("this_return_period", "This Return Period"),
            ("previous_return_period", "Last Return Period"),
        ],
        ondelete={
            "this_return_period": "set null",
            "previous_return_period": "set null",
        },
    )
    availability_condition = fields.Selection(
        selection_add=[
            ("country",),
            ("coa", "Chart of Accounts Matches"),
            ("always",),
        ],
        ondelete={"coa": "set always"},
    )

    @api.constrains("availability_condition", "chart_template")
    def _check_availability_condition_chart_template(self):
        for record in self:
            if record.availability_condition == "coa" and not record.chart_template:
                raise ValidationError(
                    _(
                        "The Availability is set to 'Chart of Accounts Matches' but the field Chart of Accounts is not set."
                    )
                )

    @_debug.perf.timed
    def _move_tax_tags_to_country(self, country_id):
        moving_reports = self.filtered(lambda x: x.country_id.id != country_id)
        tax_tags_expressions = moving_reports.line_ids.expression_ids.filtered(
            lambda x: x.engine == "tax_tags"
        )
        if not tax_tags_expressions:
            _debug.logic(
                "tag_move_skipped", report=self, reason="no_tax_tags_expressions"
            )
            return

        tag_model = self.env["account.account.tag"].with_context(
            active_test=False, lang="en_US"
        )
        source_tags = tax_tags_expressions._get_matching_tags()
        if not source_tags:
            _debug.logic("tag_move_skipped", report=self, reason="no_matching_tags")
            return

        reports_by_tag = defaultdict(self.env["report.formula"].browse)
        for expression in source_tags._get_related_tax_report_expressions():
            reports_by_tag[expression._tax_tag_key()] |= (
                expression.report_line_id.report_id
            )

        destination_names = set(
            tag_model.search(
                [
                    ("applicability", "=", "taxes"),
                    ("country_id", "=", country_id),
                    ("name", "in", source_tags.mapped("name")),
                ]
            ).mapped("name")
        )

        tags_to_move = tag_model.browse()
        for tag in source_tags:
            users = reports_by_tag[(tag.name, tag.country_id.id)]
            if tag.name not in destination_names and users <= moving_reports:
                tags_to_move += tag
        _debug.logic(
            "tags_partitioned",
            report=self,
            country_id=country_id,
            source_tags=source_tags,
            destination_names=len(destination_names),
            tags_to_move=tags_to_move,
        )
        tags_to_move.write({"country_id": country_id})

        missing_names = (
            set(source_tags.mapped("name"))
            - destination_names
            - set(tags_to_move.mapped("name"))
        )
        expression_model = self.env["report.formula.expression"]
        _debug.pipeline(
            "missing_tags_creating",
            report=self,
            country_id=country_id,
            missing_names=len(missing_names),
        )
        tag_model.create(
            [
                tag_vals
                for name in sorted(missing_names)
                for tag_vals in expression_model._prepare_tag_vals(name, country_id)
            ]
        )

    horizontal_group_ids = fields.Many2many(
        comodel_name="account.report.horizontal.group",
        string="Horizontal Groups",
    )
    return_type_ids = fields.One2many(
        comodel_name="account.return.type",
        inverse_name="report_id",
        string="Return Types",
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
        if "country_id" in vals:
            self._move_tax_tags_to_country(vals["country_id"])
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
                    field_name, self.env["report.formula"]
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
                            name, self.env["report.formula"]
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
        Report = self.env["report.formula"].with_context(active_test=False)
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
                self.env["report.formula"],
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

    ACCOUNT_TYPE_FILTER_DOMAINS = {
        "trade_receivable": (False, "asset_receivable"),
        "trade_payable": (False, "liability_payable"),
        "non_trade_receivable": (True, "asset_receivable"),
        "non_trade_payable": (True, "liability_payable"),
    }

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
    def _init_options_return_periodicity(self, options, previous_options):
        if not self._reads_ledger():
            return
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
                return_type := self.env["report.formula"]
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

    def _init_options_hierarchy(self, options, previous_options):
        if not self._reads_ledger():
            return
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

    # ####################################################
    # OPTIONS: ALL ENTRIES
    ####################################################
    def _init_options_all_entries(self, options, previous_options):
        if self.filter_show_draft:
            options["all_entries"] = previous_options.get("all_entries", False)
        else:
            options["all_entries"] = False

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
    # OPTIONS: READONLY QUERY
    ####################################################
    def _init_options_readonly_query(self, options, previous_options):
        options["readonly_query"] = options["currency_table"]["type"] == "monocurrency"

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

    def _get_source_domains(self, options, date_scope):
        if not self._reads_ledger():
            return super()._get_source_domains(options, date_scope)
        domains = [
            Domain("display_type", "not in", NON_ACCOUNTABLE_DISPLAY_TYPES),
            self._get_domain_options_journals(options)
            if not options.get("compute_budget")
            else Domain.TRUE,
            self._get_domain_options_partner(options),
            self._get_domain_options_all_entries(options),
            self._get_domain_options_unreconciled(options),
            self._get_domain_options_account_type(options),
            self._get_options_aml_ir_filters(options),
            self.env["account.move.line"]._get_domain_tax_exigible()
            if self.only_tax_exigible
            else Domain.TRUE,
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

        return domains

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

    def _apply_branch_rules_to_buttons(self, options):
        if not self._reads_ledger():
            super()._apply_branch_rules_to_buttons(options)
            return
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

    def _get_options_companies(self, options, previous_options):
        if self.filter_multi_company == "tax_units":
            return self._multi_company_tax_units_init_options(
                options, previous_options=previous_options
            )
        return super()._get_options_companies(options, previous_options)

    def _init_options_filters(self, options, previous_options):
        super()._init_options_filters(options, previous_options)
        options["filters"]["show_draft"] = self.filter_show_draft
        options["filters"]["show_unreconciled"] = self.filter_unreconciled

    def _normalize_date_filter(self, options, options_filter, period_date_to):
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
                fy_start = self._get_year_bounds(
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
        return options_filter

    def _get_custom_period_bounds(
        self, options, options_filter, period_date_from, period_date_to, current
    ):
        if "return_period" not in options_filter:
            return super()._get_custom_period_bounds(
                options, options_filter, period_date_from, period_date_to, current
            )
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
        return date_from, date_to, period_type

    def _convert_custom_period_filter(
        self, options, options_filter, date, period_date_to, date_to
    ):
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
        return options_filter

    def _finalize_custom_period_options(self, options, options_filter):
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

    def _get_custom_period_name(self, period_type, date_from, date_to, options_return):
        if period_type != "return_period" or not options_return:
            return super()._get_custom_period_name(
                period_type, date_from, date_to, options_return
            )
        day = options_return["start_day"]
        month = options_return["start_month"]
        return self.env["account.return.type"]._get_period_name(
            period_from=fields.Date.to_string(date_from),
            period_to=fields.Date.to_string(date_to),
            start_day=day,
            start_month=month,
        )

    def _get_shifted_custom_period(
        self, options, periods, return_period, period_type, mode, date_from
    ):
        if not (return_period or "return_period" in period_type):
            return super()._get_shifted_custom_period(
                options, periods, return_period, period_type, mode, date_from
            )
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

    def _get_custom_date_scope_bounds(self, options, date_scope, date_from, date_to):
        if date_scope != "previous_return_period":
            return super()._get_custom_date_scope_bounds(
                options, date_scope, date_from, date_to
            )
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
                            self.env["report.formula.expression"]
                            ._fields["date_scope"]
                            ._description_selection(self.env)
                        )["previous_return_period"],
                    )
                )
            return_types = return_types[0]

        current_period_start, _current_period_end = return_types._get_period_boundaries(
            self.env.company,
            fields.Date.from_string(options["date"]["date_from"]),
        )
        eve_of_period_start = current_period_start - relativedelta(days=1)
        date_from, date_to = return_types._get_period_boundaries(
            self.env.company, eve_of_period_start
        )
        return date_from, date_to

    def _get_variant_preferred_country(self):
        return self.env.company.account_config_id.account_fiscal_country_id

    def _init_options_buttons(self, options, previous_options):
        super()._init_options_buttons(options, previous_options)
        if not self._reads_ledger():
            return
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

    @_debug.perf.timed
    def _get_formula_batch_with_engine_tax_tags(
        self,
        options,
        date_scope,
        formulas_dict,
        current_groupby,
        next_groupby,
        offset=0,
        limit=None,
        warnings=None,
        batch_ids_cache=None,
    ):
        self._check_groupby_fields(
            (next_groupby.split(",") if next_groupby else [])
            + ([current_groupby] if current_groupby else [])
        )
        all_expressions = self.env["report.formula.expression"]
        for expressions in formulas_dict.values():
            all_expressions |= expressions
        tags = all_expressions._get_matching_tags()
        _debug.pipeline(
            "tax_tags_matched",
            report=self,
            date_scope=date_scope,
            formulas=len(formulas_dict),
            expressions=len(all_expressions),
            tags=len(tags),
            groupby=current_groupby,
            offset=offset,
            limit=limit,
        )

        query = self._get_report_query(options, date_scope)
        groupby_sql = (
            self.env["account.move.line"]._field_to_sql(
                "account_move_line", current_groupby, query
            )
            if current_groupby
            else None
        )
        tail_query = self._get_engine_query_tail(offset, limit)
        acc_tag_name = (
            self.with_context(lang="en_US")
            .env["account.account.tag"]
            ._field_to_sql("acc_tag", "name")
        )
        sql = SQL(
            """
            SELECT
                %(acc_tag_name)s AS formula,
                SUM(%(balance_select)s) AS balance,
                COUNT(account_move_line.id) AS aml_count
                %(select_groupby_sql)s

            FROM %(table_references)s

            JOIN account_account_tag_account_move_line_rel aml_tag
                ON aml_tag.account_move_line_id = account_move_line.id
            JOIN account_account_tag acc_tag
                ON aml_tag.account_account_tag_id = acc_tag.id
            %(currency_table_join)s

            WHERE %(search_condition)s
              AND aml_tag.account_account_tag_id IN %(tag_ids)s

            GROUP BY %(groupby_clause)s

            ORDER BY %(groupby_clause)s

            %(tail_query)s
            """,
            acc_tag_name=acc_tag_name,
            select_groupby_sql=SQL(", %s AS grouping_key", groupby_sql)
            if groupby_sql
            else SQL(),
            table_references=query.from_clause,
            tag_ids=tuple(tags.ids),
            balance_select=self._currency_table_apply_rate(
                SQL("account_move_line.balance")
            ),
            currency_table_join=self._currency_table_aml_join(options),
            search_condition=query.where_clause,
            # Ordinals, not the alias and not the expression: the joins can carry
            # a `formula` column (account_tax has one) and PostgreSQL resolves a
            # GROUP BY name to an input column first, while the expression holds
            # a bound parameter, so a second spelling of it is a second parameter.
            groupby_clause=SQL("1, 4") if groupby_sql else SQL("1"),
            tail_query=tail_query,
        )

        rslt = {
            (formula_str.lstrip("-"), formula_expr): []
            if current_groupby
            else {"result": 0, "has_sublines": False}
            for formula_str, formula_expr in formulas_dict.items()
        }
        tag_rows = 0  # debuglog
        for tax_tag, balance, aml_count, *grouping_key in self.env.execute_query(sql):
            tag_rows += 1  # debuglog
            if expression := formulas_dict.get(f"-{tax_tag}"):
                balance *= -1
            else:
                expression = formulas_dict[tax_tag]
            rslt_dict = {"result": balance, "has_sublines": aml_count > 0}
            if current_groupby:
                rslt[tax_tag, expression].append((grouping_key[0], rslt_dict))
            else:
                rslt[tax_tag, expression] = rslt_dict
        _debug.perf.count("tax_tag_rows_fetched", rows=tag_rows)

        if _debug.pipeline.enabled:
            _debug.pipeline(
                "tax_tags_results",
                report=self,
                results=len(rslt),
                groups=sum(len(v) for v in rslt.values() if isinstance(v, list))
                if current_groupby
                else None,
            )
        return rslt

    @_debug.perf.timed
    def _get_formula_batch_with_engine_account_codes(
        self,
        options,
        date_scope,
        formulas_dict,
        current_groupby,
        next_groupby,
        offset=0,
        limit=None,
        warnings=None,
        batch_ids_cache=None,
    ):
        self._check_groupby_fields(
            (next_groupby.split(",") if next_groupby else [])
            + ([current_groupby] if current_groupby else [])
        )
        prefilter = self.env["account.account"]._check_company_domain(
            self.get_report_company_ids(options)
        )

        all_accounts = (
            self.env["account.account"]
            .with_context(active_test=False)
            .search([*prefilter])
        )
        accounts = []

        for account in all_accounts:
            account_code = account.code
            if not account_code:
                for company in account.company_ids:
                    account_code = account.with_company(company).code
                    if account_code:
                        break
            accounts.append(
                {
                    "id": account.id,
                    "code": account_code,
                    "tag_ids": account.tag_ids.ids,
                }
            )

        accounts.sort(key=lambda acc: acc["code"])
        tags_map = defaultdict(list)
        for acc in accounts:
            # If an account has no tags, map it to the pseudo-tag `False` such
            # that a ref which does not exist matches it, otherwise DK balance
            # fails in `test_generate_all_export_files`
            for tag in acc["tag_ids"] or [False]:
                tags_map[tag].append(acc)

        accounts_prefix_map = defaultdict(set)
        # Gather the account code prefixes to compute the total from
        prefix_details_by_formula = {}  # in the form {formula: [(1, prefix1), (-1, prefix2)]}
        for formula in formulas_dict:
            prefix_details_by_formula[formula] = []
            for token in filter(
                None, ACCOUNT_CODES_ENGINE_SPLIT_REGEX.split(formula.replace(" ", ""))
            ):
                token_match = ACCOUNT_CODES_ENGINE_TERM_REGEX.match(token)

                if not token_match:
                    raise UserError(
                        _(
                            "Invalid token '%(token)s' in account_codes formula '%(formula)s'",
                            token=token,
                            formula=formula,
                        )
                    )

                multiplicator = -1 if token_match["sign"] == "-" else 1
                excluded_prefixes_match = token_match["excluded_prefixes"]
                excluded_prefixes = (
                    tuple(excluded_prefixes_match.split(","))
                    if excluded_prefixes_match
                    else ()
                )
                prefix = token_match["prefix"]

                # We group using both prefix and excluded_prefixes as keys, for the case where two expressions would
                # include the same prefix, but exlcude different prefixes (example 104\(1041) and 104\(1042))
                prefix_key = (prefix, *excluded_prefixes)
                prefix_details_by_formula[formula].append(
                    (multiplicator, prefix_key, token_match["balance_character"])
                )

                if tag := ACCOUNT_CODES_ENGINE_TAG_ID_PREFIX_REGEX.match(prefix):
                    if tag["ref"]:
                        tag_id = self.env["ir.model.data"]._xmlid_to_res_id(tag["ref"])
                    else:
                        tag_id = int(tag["id"])
                    accs = tags_map[tag_id]
                else:
                    idx = bisect.bisect_left(
                        accounts, prefix, key=lambda acc: acc["code"]
                    )
                    accs = itertools.takewhile(
                        lambda acc, prefix=prefix: acc["code"].startswith(prefix),
                        itertools.islice(accounts, idx, None),
                    )

                for account in accs:
                    if excluded_prefixes and account["code"].startswith(
                        excluded_prefixes
                    ):
                        continue
                    accounts_prefix_map[account["id"]].add(prefix_key)

        _debug.pipeline(
            "account_prefixes_mapped",
            report=self,
            date_scope=date_scope,
            groupby=current_groupby,
            formulas=len(prefix_details_by_formula),
            accounts=len(accounts),
            tags=len(tags_map),
            matched_accounts=len(accounts_prefix_map),
        )

        # Run main query
        query = self._get_report_query(options, date_scope)

        current_groupby_aml_sql = (
            self.env["account.move.line"]._field_to_sql(
                "account_move_line", current_groupby, query
            )
            if current_groupby
            else None
        )
        tail_query = self._get_engine_query_tail(offset, limit)
        if current_groupby_aml_sql and tail_query:
            tail_query_additional_groupby_where_sql = SQL(
                """
                AND %(current_groupby_aml_sql)s IN (
                    SELECT DISTINCT %(current_groupby_aml_sql)s
                    FROM %(table_references)s
                    WHERE %(search_condition)s
                    ORDER BY %(current_groupby_aml_sql)s
                    %(tail_query)s
                )
                """,
                current_groupby_aml_sql=current_groupby_aml_sql,
                # Must be the same FROM as the outer query: under budget reporting the
                # query shadows account_move_line with a budget-item subquery, and naming
                # the real table here would pick the load-more window from journal items
                # while the outer query aggregates budget rows.
                table_references=query.from_clause,
                search_condition=query.where_clause,
                tail_query=tail_query,
            )
        else:
            tail_query_additional_groupby_where_sql = SQL()
        _debug.logic(
            "account_codes_pagination",
            report=self,
            offset=offset,
            limit=limit,
            groupby_subquery=bool(tail_query_additional_groupby_where_sql),
        )

        extra_groupby_sql = (
            SQL(", %s", current_groupby_aml_sql) if current_groupby_aml_sql else SQL()
        )
        extra_select_sql = (
            SQL(", %s AS grouping_key", current_groupby_aml_sql)
            if current_groupby_aml_sql
            else SQL()
        )

        query = SQL(
            """
            SELECT
                account_move_line.account_id AS account_id,
                SUM(%(balance_select)s) AS sum
                %(extra_select_sql)s
            FROM %(table_references)s
            %(currency_table_join)s
            WHERE %(search_condition)s
            %(tail_query_additional_groupby_where_sql)s
            GROUP BY account_move_line.account_id%(extra_groupby_sql)s
            %(order_by_sql)s
            %(tail_query)s
            """,
            extra_select_sql=extra_select_sql,
            table_references=query.from_clause,
            balance_select=self._currency_table_apply_rate(
                SQL("account_move_line.balance")
            ),
            currency_table_join=self._currency_table_aml_join(options),
            search_condition=query.where_clause,
            extra_groupby_sql=extra_groupby_sql,
            tail_query_additional_groupby_where_sql=tail_query_additional_groupby_where_sql,
            order_by_sql=SQL("ORDER BY %s", current_groupby_aml_sql)
            if current_groupby_aml_sql
            else SQL(),
            tail_query=tail_query
            if not tail_query_additional_groupby_where_sql
            else SQL(),
        )
        self.env.cr.execute(query)

        # Parse result
        rslt = {}

        res_by_prefix_account_id = {}
        for query_res in self.env.cr.dictfetchall():
            # Done this way so that we can run similar code for groupby and non-groupby
            grouping_key = query_res["grouping_key"] if current_groupby else None
            account_id = query_res["account_id"]
            for prefix_key in accounts_prefix_map[account_id]:
                res_by_prefix_account_id.setdefault(prefix_key, {}).setdefault(
                    account_id, []
                ).append(
                    (
                        grouping_key,
                        {
                            "result": query_res["sum"],
                            # A grouped row exists only where at least one line does,
                            # so its presence is the sublines flag.
                            "has_sublines": True,
                        },
                    )
                )
        _debug.perf.count("account_codes_rows_fetched", rows=self.env.cr.rowcount)
        _debug.pipeline(
            "account_codes_rows_parsed",
            report=self,
            prefixes_with_results=len(res_by_prefix_account_id),
        )

        for formula, prefix_details in prefix_details_by_formula.items():
            rslt_key = (formula, formulas_dict[formula])
            rslt_destination = rslt.setdefault(
                rslt_key,
                [] if current_groupby else {"result": 0, "has_sublines": False},
            )
            rslt_groups_by_grouping_keys = {}
            for multiplicator, prefix_key, balance_character in prefix_details:
                res_by_account_id = res_by_prefix_account_id.get(prefix_key, {})

                for account_results in res_by_account_id.values():
                    account_total_value = sum(
                        group_val["result"]
                        for (group_key, group_val) in account_results
                    )
                    comparator = self.env.company.currency_id.compare_amounts(
                        account_total_value, 0.0
                    )

                    # Manage balance_character.
                    if (
                        not balance_character
                        or (balance_character == "D" and comparator >= 0)
                        or (balance_character == "C" and comparator < 0)
                    ):
                        for group_key, group_val in account_results:
                            rslt_group = {
                                **group_val,
                                "result": multiplicator * group_val["result"],
                            }
                            if not current_groupby:
                                rslt_destination["result"] += rslt_group["result"]
                                rslt_destination["has_sublines"] = (
                                    rslt_destination["has_sublines"]
                                    or rslt_group["has_sublines"]
                                )
                            elif group_key in rslt_groups_by_grouping_keys:
                                # Will happen if the same grouping key is used on move lines with different accounts.
                                # This comes from the GROUPBY in the SQL query, which uses both grouping key and account.
                                # When this happens, we want to aggregate the results of each grouping key, to avoid duplicates in the end result.
                                already_treated_rslt_group = (
                                    rslt_groups_by_grouping_keys[group_key]
                                )
                                already_treated_rslt_group["has_sublines"] = (
                                    already_treated_rslt_group["has_sublines"]
                                    or rslt_group["has_sublines"]
                                )
                                already_treated_rslt_group["result"] += rslt_group[
                                    "result"
                                ]
                            else:
                                rslt_groups_by_grouping_keys[group_key] = rslt_group
                                rslt_destination.append((group_key, rslt_group))

        _debug.pipeline("account_codes_results", report=self, results=len(rslt))
        return rslt

    @_debug.perf.timed
    def _get_domain_expression_audit(self, expression_to_audit, options):
        _debug.logic(
            "audit_domain_engine",
            report=self,
            expression=expression_to_audit,
            engine=expression_to_audit.engine,
            supported=expression_to_audit.engine
            in ("account_codes", "tax_tags", "domain"),
        )
        if expression_to_audit.engine == "account_codes":
            formula = expression_to_audit.formula.replace(" ", "")

            account_codes_domains = []
            for token in ACCOUNT_CODES_ENGINE_SPLIT_REGEX.split(
                formula.replace(" ", "")
            ):
                if token:
                    match_dict = ACCOUNT_CODES_ENGINE_TERM_REGEX.match(
                        token
                    ).groupdict()
                    tag_match = ACCOUNT_CODES_ENGINE_TAG_ID_PREFIX_REGEX.match(
                        match_dict["prefix"]
                    )
                    account_codes_domain = []

                    if tag_match:
                        if tag_match["ref"]:
                            tag_id = self.env["ir.model.data"]._xmlid_to_res_id(
                                tag_match["ref"]
                            )
                        else:
                            tag_id = int(tag_match["id"])

                        account_codes_domain.append(
                            ("account_id.tag_ids", "in", [tag_id])
                        )
                    else:
                        account_codes_domain.append(
                            ("account_id.code", "=like", f"{match_dict['prefix']}%")
                        )

                    excluded_prefix_str = match_dict["excluded_prefixes"]
                    if excluded_prefix_str:
                        for excluded_prefix in excluded_prefix_str.split(","):
                            # "'not like', prefix%" doesn't work
                            account_codes_domain += [
                                "!",
                                ("account_id.code", "=like", f"{excluded_prefix}%"),
                            ]

                    account_codes_domains.append(account_codes_domain)

            _debug.pipeline(
                "account_codes_audit_domain",
                expression=expression_to_audit,
                tokens=len(account_codes_domains),
            )
            return Domain.OR(account_codes_domains)

        if expression_to_audit.engine == "tax_tags":
            tags = self.env["account.account.tag"]._get_tax_tags(
                expression_to_audit.formula,
                expression_to_audit.report_line_id.report_id.country_id.id,
            )
            return [("tax_tag_ids", "in", tags.ids)]

        return super()._get_domain_expression_audit(expression_to_audit, options)

    @api.model
    def _currency_table_apply_rate(self, value: SQL) -> SQL:
        if not self._reads_ledger():
            return super()._currency_table_apply_rate(value)
        return SQL(
            "(%(value)s) * COALESCE(account_currency_table.rate, 1)", value=value
        )

    @api.model
    @_debug.perf.timed
    def _currency_table_aml_join(
        self,
        options,
        aml_alias=SQL("account_move_line"),  # noqa: B008  SQL is immutable, one shared default is safe
    ) -> SQL:
        if not self._reads_ledger():
            return super()._currency_table_aml_join(options, aml_alias)
        _debug.logic(
            "currency_table_join",
            table_type=options.get("currency_table", {}).get("type"),
            period_key=options.get("date", {}).get("currency_table_period_key"),
        )
        if options["currency_table"]["type"] == "cta":
            return SQL(
                """
                JOIN account_account aml_ct_account
                    ON aml_ct_account.id = %(aml_table)s.account_id
                LEFT JOIN %(currency_table)s
                    ON %(aml_table)s.company_id = account_currency_table.company_id
                    AND (
                        account_currency_table.rate_type = CASE
                            WHEN aml_ct_account.account_type LIKE ANY (ARRAY[%(income_prefix)s, %(expense_prefix)s, 'equity_unaffected']) THEN 'average'
                            WHEN aml_ct_account.account_type LIKE %(equity_prefix)s THEN 'historical'
                            ELSE 'current'
                        END
                    )
                    AND (account_currency_table.date_from IS NULL OR account_currency_table.date_from <= %(aml_table)s.date)
                    AND (account_currency_table.date_next IS NULL OR account_currency_table.date_next > %(aml_table)s.date)
                    AND (account_currency_table.period_key = %(period_key)s OR account_currency_table.period_key IS NULL)
                """,
                aml_table=aml_alias,
                equity_prefix="equity%",
                income_prefix="income%",
                expense_prefix="expense%",
                currency_table=self._get_currency_table(options),
                period_key=options["date"]["currency_table_period_key"],
            )

        return SQL(
            """
            JOIN %(currency_table)s
                ON %(aml_table)s.company_id = account_currency_table.company_id
                AND (account_currency_table.period_key = %(period_key)s OR account_currency_table.period_key IS NULL)
            """,
            aml_table=aml_alias,
            currency_table=self._get_currency_table(options),
            period_key=options["date"]["currency_table_period_key"],
        )

    @api.model
    def _get_currency_table(self, options) -> SQL:
        if options["currency_table"]["type"] == "monocurrency":
            companies = self.env["res.company"].browse(
                self.get_report_company_ids(options)
            )
            # No CTA rates here by construction: this branch is the monocurrency one.
            return self.env["res.currency"]._get_monocurrency_currency_table_sql(
                companies, use_cta_rates=False
            )

        return SQL("account_currency_table")

    def _currency_table_external_value_join(self, options) -> SQL:
        return SQL(
            """
            JOIN %(currency_table)s
            ON account_currency_table.company_id = report_formula_external_value.company_id
            AND account_currency_table.rate_type = 'current'
            """,
            currency_table=self._get_currency_table(options),
        )

    def _adapt_report_query_domain(self, options, domain):
        if options.get("compute_budget"):
            domain = domain.optimize(self._get_source_model())
            aml_required_columns = {
                "move_id",
                "currency_id",
                "journal_id",
                "display_type",
            }
            domain = domain.map_conditions(
                lambda condition: (
                    Domain.TRUE
                    if condition.field_expr in aml_required_columns
                    else condition
                )
            )
        return domain

    def _adapt_report_query(self, options, query):
        if options.get("compute_budget"):
            query._tables["account_move_line"] = (
                self._create_aml_shadowing_query_for_budget(options)
            )
            query.add_where(SQL("budget_id = %s", options["compute_budget"]))

    def _init_options_horizontal_groups(self, options, previous_options):
        if not self._reads_ledger():
            super()._init_options_horizontal_groups(options, previous_options)
            return
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

    def _get_options_initializers_forced_sequence_map(self):
        return {
            **super()._get_options_initializers_forced_sequence_map(),
            "_init_options_return_periodicity": 29,
            "_init_options_journals": 80,
            "_init_options_journals_names": 90,
            "_init_options_audit": 100,
            "_init_options_hierarchy": 1030,
            "_init_options_currency_table": 1055,
            "_init_options_readonly_query": 1070,
        }

    def _get_totals_below_sections(self):
        if not self._reads_ledger():
            return super()._get_totals_below_sections()
        return self.env.company.account_config_id.totals_below_sections

    def _prepare_info_popup_data(
        self,
        options,
        col_group_key,
        column_expr_label,
        target_line_res_dict,
        line_expressions_map,
    ):
        if not self._reads_ledger():
            return super()._prepare_info_popup_data(
                options,
                col_group_key,
                column_expr_label,
                target_line_res_dict,
                line_expressions_map,
            )
        info_popup_data = {}

        # Check carryover
        carryover_expr_label = "_carryover_%s" % column_expr_label
        carryover_value = target_line_res_dict.get(carryover_expr_label, {}).get(
            "value", 0
        )
        if self.env.company.currency_id.compare_amounts(0, carryover_value) != 0:
            info_popup_data["carryover"] = self._format_value(
                options, carryover_value, "monetary"
            )

            carryover_expression = line_expressions_map[carryover_expr_label]
            if carryover_expression.carryover_target:
                info_popup_data["carryover_target"] = (
                    carryover_expression._get_carryover_target_expression(
                        options
                    ).report_line_name
                )
            # If it's not set, it means the carryover needs to target the same expression

        applied_carryover_value = target_line_res_dict.get(
            "_applied_carryover_%s" % column_expr_label, {}
        ).get("value", 0)
        if (
            self.env.company.currency_id.compare_amounts(0, applied_carryover_value)
            != 0
        ):
            info_popup_data["applied_carryover"] = self._format_value(
                options, applied_carryover_value, "monetary"
            )
            info_popup_data["allow_carryover_audit"] = self.env.user.has_group(
                "base.group_no_one"
            )
            info_popup_data["expression_id"] = line_expressions_map[
                "_applied_carryover_%s" % column_expr_label
            ]["id"]
            info_popup_data["column_group_key"] = col_group_key
        return info_popup_data

    @_debug.perf.timed
    def get_annotations(self, options, lines):
        """Return the annotations to display on the report, based on its dates and their display mode.

        :param dict options: options used to generate the report.
        :param list lines: report lines, used to build the domain for the annotations.
        :return: for each annotated line_id, the list of annotations linked to it.
        :rtype: dict
        """
        if not self._reads_ledger():
            return super().get_annotations(options, lines)
        self.check_singleton()
        annotations_by_line = defaultdict(list)
        line_dict_ids_by_record = defaultdict(set)
        model_ids_map = defaultdict(set)
        for line in lines:
            if line.get("chatter"):
                line_dict_ids_by_record[
                    line["chatter"]["model"], line["chatter"]["id"]
                ].add(line["id"])
                model_ids_map[line["chatter"]["model"]].add(line["chatter"]["id"])

        domain = Domain.OR(
            [
                Domain("message_id.model", "=", model)
                & Domain("message_id.res_id", "in", ids)
                for model, ids in model_ids_map.items()
            ]
        )
        if options.get("date"):
            period_date_from = self._get_annotations_domain_date_from(options)
            period_date_from = self._adjust_date_for_joined_comparison(
                options, period_date_from
            )
            dates_domain = Domain("date", ">=", period_date_from) & Domain(
                "date", "<=", options["date"]["date_to"]
            )
            dates_domain = self._adjust_domain_for_unjoined_comparison(
                options, dates_domain
            )
            domain &= dates_domain

        order = "create_date ASC" if options["export_mode"] else ""
        _debug.logic(
            "annotations_scope_decided",
            report=self,
            models=len(model_ids_map),
            records=len(line_dict_ids_by_record),
            dated=bool(options.get("date")),
            order=order,
        )
        report_annotations = self.env["account.report.annotation"].search(
            domain, order=order
        )
        for annotation in report_annotations:
            message = annotation.message_id
            for line_id in line_dict_ids_by_record[message.model, message.res_id]:
                annotations_by_line[line_id].append(
                    {
                        "id": message.id,
                        "model": message.model,
                        "res_id": message.res_id,
                        "date": annotation.date,
                        "body": message.body,
                        "line_id": line_id,
                    }
                )
        _debug.pipeline(
            "annotations_fetched",
            report=self,
            lines=len(lines),
            annotations=len(report_annotations),
            annotated_lines=len(annotations_by_line),
        )
        return annotations_by_line

    def _get_engines_without_next_groupby(self):
        # These engines always receive None as their next_groupby, which lets
        # their expressions be batched together.
        return super()._get_engines_without_next_groupby() | LEDGER_ENGINES

    def _reads_ledger(self):
        return self[:1].source_model in {False, "account.move.line"}

    def _get_source_model(self):
        source_model = super()._get_source_model()
        return self.env["account.move.line"] if source_model is None else source_model

    def _get_source_measure_field(self):
        measure_field = super()._get_source_measure_field()
        if measure_field or not self._reads_ledger():
            return measure_field
        return "balance"

    def _get_year_bounds(self, date):
        if not self._reads_ledger():
            return super()._get_year_bounds(date)
        return self.env.company.compute_fiscalyear_dates(date)

    def _get_year_end(self):
        if not self._reads_ledger():
            return super()._get_year_end()
        config = self.env.company.account_config_id
        return config.fiscalyear_last_day, int(config.fiscalyear_last_month)

    def _init_currency_table(self, options):
        """Creates the currency table temporary table if necessary, using the provided options to compute its periods.
        This function should always be called before any query invovlving the currency table is run.
        """
        if not self._reads_ledger():
            return
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

    @_debug.perf.timed
    def _add_common_warnings(self, options, warnings):
        # Display a warning if we're displaying only the data of the current company, but it's also part of a tax unit
        if not self._reads_ledger():
            super()._add_common_warnings(options, warnings)
            return
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
        if not self._reads_ledger():
            return super()._add_account_status_on_lines(lines, options)
        if not self.allow_account_audit_status_on_lines:
            return lines
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
        if not self._reads_ledger():
            super()._update_line_names_for_consolidation(lines)
            return
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
        """Generates the report.formula.external.value objects corresponding to this report's carryover under the provided options.

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
        """Generates the report.formula.external.value objects for the given dates.
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
        default_expressions = self.env["report.formula.expression"].search(
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
                for value in self.env["report.formula.external.value"].search(  # noqa: E8507 - one query per report, over every default expression at once
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
        self.env["report.formula.external.value"].create(external_values_create_vals)

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

        self.env["report.formula.external.value"].create(external_values_create_vals)

    @_debug.perf.timed
    def _is_available_for(self, options):
        """Called on report variants to know whether they are available for the provided options or not, computed for their root report,
        computing their availability_condition field.

        Only the options initialized by init_options with a more prioritary sequence than _init_options_variants are guaranteed to
        be in the provided options' dict (since this function is called by _init_options_variants, while resolving a call to get_options()).
        """
        if not self._reads_ledger():
            return super()._is_available_for(options)
        companies = self.env["res.company"].browse(self.get_report_company_ids(options))

        reports = self.filtered(lambda r: r.availability_condition == "always")

        reports_by_country = self.filtered(
            lambda r: r.availability_condition == "country"
        )
        if reports_by_country:
            company_countries = companies.account_config_id.account_fiscal_country_id

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
            chart_templates = set(companies.account_config_id.mapped("chart_template"))
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
        if not self._reads_ledger():
            super()._set_budget_column_comparisons(options, line)
            return
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
        if not self._reads_ledger():
            return super()._prepare_editable_cell_data(
                options, col_group_key, groupby_model, column_expression, column_value
            )
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
        if not self._reads_ledger():
            return super()._create_hierarchy(lines, options)
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
                day=self.env.company.account_config_id.fiscalyear_last_day,
                month=int(self.env.company.account_config_id.fiscalyear_last_month),
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
        if not self._reads_ledger():
            super()._postprocess_chatter_for_annotations(lines)
            return
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

        # load=False keeps move_id a bare id instead of an (id, display_name)
        # pair: the chatter only needs the number, and resolving a display
        # name for every annotated line's move is pure waste.
        aml_id_to_account_move_id = {
            line["id"]: line["move_id"]
            for line in self.env["account.move.line"]
            .browse(aml_id_to_report_lines_map.keys())
            .read(["id", "move_id"], load=False)
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
    _inherit = "report.formula.line"

    account_codes_formula = fields.Char(
        string="Account Codes Formula Shortcut",
        inverse="_inverse_account_codes_formula",
        store=False,
        copy=False,
        help="Internal field to shorten expression_ids creation for the account_codes engine",
    )
    tax_tags_formula = fields.Char(
        string="Tax Tags Formula Shortcut",
        inverse="_inverse_tax_tags_formula",
        store=False,
        copy=False,
        help="Internal field to shorten expression_ids creation for the tax_tags engine",
    )

    def _inverse_tax_tags_formula(self):
        self._create_report_expression(engine="tax_tags")

    def _inverse_account_codes_formula(self):
        self._create_report_expression(engine="account_codes")

    def _get_indenting_groupby_models(self):
        return ("account.group",)

    def _get_groupby_record_state(self, groupby_model, record):
        if groupby_model == "account.move.line":
            return record.parent_state
        if groupby_model == "account.move":
            return record.state
        return super()._get_groupby_record_state(groupby_model, record)

    def _get_shortcut_expression_formula(self, engine):
        if engine == "account_codes" and self.account_codes_formula:
            return None, self.account_codes_formula
        if engine == "tax_tags" and self.tax_tags_formula:
            return None, self.tax_tags_formula
        return super()._get_shortcut_expression_formula(engine)

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

    def _get_groupby(self, options):
        groupby = super()._get_groupby(options)
        if options["export_mode"] == "file":
            return groupby

        groupby_lst = [
            groupby.strip() for groupby in (self.user_groupby or "").split(",")
        ]
        if options["consolidation"] and "account_id" in groupby_lst:
            index_account_id = groupby_lst.index("account_id")
            groupby_lst.insert(index_account_id, "account_code")
            return ",".join(groupby_lst)
        return groupby


class AccountReportExpression(models.Model):
    _inherit = "report.formula.expression"

    engine = fields.Selection(
        selection_add=[
            ("domain",),
            ("tax_tags", "Tax Tags"),
            ("aggregation",),
            ("account_codes", "Prefix of Account Codes"),
        ],
        ondelete={"tax_tags": "cascade", "account_codes": "cascade"},
    )
    date_scope = fields.Selection(
        selection_add=[("previous_return_period", "From previous return period")],
        ondelete={"previous_return_period": "set default"},
    )
    carryover_target = fields.Char(
        string="Carry Over To",
        help="Formula in the form line_code.expression_label. This allows setting the target of the carryover for this expression "
        "(on a _carryover_*-labeled expression), in case it is different from the parent line.",
    )

    def _get_auditable_engines(self):
        return super()._get_auditable_engines() | LEDGER_ENGINES

    @api.constrains("formula")
    def _check_formula_account_codes(self):
        for expression in self.filtered(lambda x: x.engine == "account_codes"):
            for token in ACCOUNT_CODES_ENGINE_SPLIT_REGEX.split(
                expression.formula.replace(" ", "")
            ):
                if token:
                    token_match = ACCOUNT_CODES_ENGINE_TERM_REGEX.match(token)
                    prefix = token_match and token_match["prefix"]
                    if not prefix:
                        expression._raise_formula_error()

    @api.model_create_multi
    def create(self, vals_list):
        result = super().create(vals_list)
        result.filtered(lambda x: x.engine == "tax_tags")._create_missing_tax_tags()
        return result

    def write(self, vals):
        self._strip_formula_vals(vals)

        tax_tags_expressions = self.filtered(lambda x: x.engine == "tax_tags")
        _debug.logic(
            "tax_tags_engine_change",
            records=self,
            tax_tags_expressions=tax_tags_expressions,
            new_engine=vals.get("engine"),
            formula_changed="formula" in vals,
        )

        if vals.get("engine") == "tax_tags":
            (self - tax_tags_expressions)._create_missing_tax_tags(
                formula_override=vals.get("formula")
            )

        if vals.get("engine") and vals["engine"] != "tax_tags":
            tax_tags_expressions._release_tax_tags()

        if "formula" not in vals or (
            vals.get("engine") and vals["engine"] != "tax_tags"
        ):
            _debug.logic(
                "tag_rename_skipped", records=self, reason="no_tax_tags_formula"
            )
            return super().write(vals)

        former_formulas_by_country = defaultdict(list)
        for expr in tax_tags_expressions:
            former_formulas_by_country[expr.report_line_id.report_id.country_id].append(
                expr.formula
            )

        result = super().write(vals)
        new_formula = vals["formula"]
        tag_model = self.env["account.account.tag"]
        for country, former_formulas_list in former_formulas_by_country.items():
            new_tag_exists = bool(tag_model._get_tax_tags(new_formula, country.id))
            _debug.logic(
                "tag_rename_country",
                records=self,
                country=country,
                new_tag_exists=new_tag_exists,
                former_formulas=len(former_formulas_list),
            )
            for former_formula in former_formulas_list:
                if new_tag_exists:
                    break
                former_tax_tags = tag_model._get_tax_tags(former_formula, country.id)
                if former_tax_tags and all(
                    tag_expr in self
                    for tag_expr in former_tax_tags._get_related_tax_report_expressions()
                ):
                    former_tax_tags._update_field_translations(
                        "name", {"en_US": new_formula.lstrip("-")}
                    )
                    _debug.logic(
                        "former_tag_renamed", records=self, tags=former_tax_tags
                    )
                else:
                    _debug.logic(
                        "new_tag_created",
                        records=self,
                        country=country,
                        shared_former_tags=former_tax_tags,
                    )
                    tag_model.create(self._prepare_tag_vals(new_formula, country.id))
                new_tag_exists = True

        return result

    @api.constrains("carryover_target", "label")
    @_debug.perf.timed
    def _check_carryover_target(self):
        for expression in self:
            if not expression.carryover_target:
                continue
            if not expression.label.startswith("_carryover_"):
                _debug.logic(
                    "carryover_target_rejected",
                    expression=expression,
                    label=expression.label,
                    reason="label_prefix",
                )
                raise ValidationError(
                    _(
                        "You cannot use the field carryover_target in an expression that does not have the label starting with _carryover_"
                    )
                )
            _line_code, target_label = expression._parse_carryover_target()
            if not target_label.startswith("_applied_carryover_"):
                _debug.logic(
                    "carryover_target_label_rejected",
                    expression=expression,
                    target_label=target_label,
                )
                raise ValidationError(
                    _(
                        "When targeting an expression for carryover, the label of that expression must start with _applied_carryover_"
                    )
                )

    def _parse_carryover_target(self):
        self.check_singleton()
        parts = self.carryover_target.split(".")
        if len(parts) != 2 or not all(parts):
            raise ValidationError(
                _(
                    "The carryover target of expression '%(label)s' must have the form "
                    "'line_code.expression_label', but is '%(target)s'.",
                    label=self.label,
                    target=self.carryover_target,
                )
            )
        return parts[0], parts[1]

    def _tax_tag_key(self):
        self.check_singleton()
        return (
            self.formula.lstrip("-"),
            self.report_line_id.report_id.country_id.id,
        )

    @api.model
    @_debug.perf.timed
    def _search_tax_tags(self, tag_keys):
        tag_model = self.env["account.account.tag"]
        if not tag_keys:
            return tag_model
        return tag_model.with_context(active_test=False, lang="en_US").search(
            Domain.OR(
                Domain(tag_model._get_domain_tax_tags(tag_name, country_id))
                for tag_name, country_id in tag_keys
            )
        )

    @_debug.perf.timed
    def _create_missing_tax_tags(self, formula_override=None):
        wanted_keys = set()
        for expression in self:
            tag_name, country_id = expression._tax_tag_key()
            if formula_override:
                tag_name = formula_override.lstrip("-")
            wanted_keys.add((tag_name, country_id))
        existing_keys = {
            (tag.name, tag.country_id.id) for tag in self._search_tax_tags(wanted_keys)
        }
        tags_create_vals = [
            tag_vals
            for tag_name, country_id in sorted(
                wanted_keys - existing_keys, key=lambda key: (key[0], key[1] or 0)
            )
            for tag_vals in self._prepare_tag_vals(tag_name, country_id)
        ]
        _debug.pipeline(
            "missing_tax_tags_resolved",
            expressions=self,
            wanted=len(wanted_keys),
            existing=len(existing_keys),
            to_create=len(tags_create_vals),
            formula_override=bool(formula_override),
        )
        if tags_create_vals:
            self.env["account.account.tag"].create(tags_create_vals)

    @api.ondelete(at_uninstall=False)
    @_debug.perf.timed
    def _unlink_archive_used_tags(self):
        _debug.lifecycle("_unlink_archive_used_tags", records=self)
        self._release_tax_tags()

    @_debug.perf.timed
    def _release_tax_tags(self):
        expressions_tags = self._get_matching_tags().with_context(lang="en_US")
        if not expressions_tags:
            _debug.logic("tag_release_skipped", records=self, reason="no_matching_tags")
            return

        still_referenced_keys = {
            expression._tax_tag_key()
            for expression in expressions_tags.sudo()._get_related_tax_report_expressions()
            - self
        }
        orphan_tags = expressions_tags.filtered(
            lambda tag: (tag.name, tag.country_id.id) not in still_referenced_keys
        )
        if not orphan_tags:
            _debug.logic(
                "tag_release_skipped",
                records=self,
                reason="all_tags_still_referenced",
                tags=expressions_tags,
            )
            return

        tags_used_by_aml_ids = {
            tag.id
            for [tag] in self.env["account.move.line"]
            .sudo()
            ._read_group(
                [("tax_tag_ids", "in", orphan_tags.ids)], groupby=["tax_tag_ids"]
            )
        }
        tags_to_archive = orphan_tags.filtered(
            lambda tag: tag.id in tags_used_by_aml_ids
        )
        tags_to_unlink = orphan_tags - tags_to_archive

        rep_lines_with_tag = (
            self.env["account.tax.repartition.line"]
            .sudo()
            .search([("tag_ids", "in", orphan_tags.ids)])
        )
        rep_lines_with_tag.write(
            {"tag_ids": [Command.unlink(tag.id) for tag in orphan_tags]}
        )
        _debug.pipeline(
            "tags_released",
            records=self,
            orphan_tags=orphan_tags,
            archived=tags_to_archive,
            unlinked=tags_to_unlink,
            repartition_lines=rep_lines_with_tag,
        )
        tags_to_archive.active = False
        tags_to_unlink.unlink()

    def _get_matching_tags(self):
        return self._search_tax_tags(
            {
                expression._tax_tag_key()
                for expression in self
                if expression.engine == "tax_tags"
            }
        )

    @api.model
    def _prepare_tag_vals(self, tag_name, country_id):
        return [
            {
                "name": tag_name.lstrip("-"),
                "applicability": "taxes",
                "country_id": country_id,
            }
        ]

    def _get_carryover_target_expression(self, options):
        self.check_singleton()

        if self.carryover_target:
            line_code, expr_label = self._parse_carryover_target()
            _debug.logic(
                "carryover_target_explicit",
                expression=self,
                line_code=line_code,
                expr_label=expr_label,
            )
            return self.env["report.formula.expression"].search(
                [
                    ("report_line_id.code", "=", line_code),
                    ("label", "=", expr_label),
                    ("report_line_id.report_id", "=", self.report_line_id.report_id.id),
                ],
                limit=1,
            )

        main_expr_label = re.sub(r"^_carryover_", "", self.label)
        target_label = "_applied_carryover_%s" % main_expr_label
        auto_chosen_target = self.report_line_id.expression_ids.filtered(
            lambda x: x.label == target_label
        )

        if not auto_chosen_target:
            _debug.logic(
                "carryover_target_not_found", expression=self, target_label=target_label
            )
            raise UserError(
                _(
                    "Could not determine carryover target automatically for expression %s.",
                    self.label,
                )
            )

        _debug.logic(
            "carryover_target_auto", expression=self, target=auto_chosen_target
        )
        return auto_chosen_target

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
            "res_model": "report.formula.external.value",
            "views": [(False, "list")],
            "domain": [
                ("target_report_expression_id", "=", self.id),
                ("date", ">=", date_from),
                ("date", "<=", date_to),
            ],
        }


class AccountReportExternalValue(models.Model):
    _inherit = "report.formula.external.value"

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
