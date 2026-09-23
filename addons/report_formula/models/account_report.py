import ast
import re

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.libs.debug_log import DebugLog
from odoo.tools import date_utils

_debug = DebugLog(__name__)

FIGURE_TYPE_SELECTION_VALUES = [
    ("monetary", "Monetary"),
    ("percentage", "Percentage"),
    ("integer", "Integer"),
    ("float", "Float"),
    ("date", "Date"),
    ("datetime", "Datetime"),
    ("boolean", "Boolean"),
    ("string", "String"),
]

DOMAIN_REGEX = re.compile(r"(-?sum)\((.*)\)")
CROSS_REPORT_REGEX = re.compile(r"^cross_report\((.+)\)$")

NUMBER_REGEX = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?"
REPORT_LINE_CODE_REGEX = r"[+-]?[\s(]*[^().\s*/+\-]+\.[^().\s*/+\-]+"
OPERATOR_REGEX = r"[\s*/+\-]"
SUM_CHILDREN_FORMULA = "sum_children"
HARD_FORMULAS = (SUM_CHILDREN_FORMULA,)
AGGREGATION_ENGINE_FORMULA_REGEX = re.compile(
    f"{'|'.join(HARD_FORMULAS)}|"
    rf"[\s(]*(?:{NUMBER_REGEX}|{REPORT_LINE_CODE_REGEX})[\s)]*"
    rf"(?:{OPERATOR_REGEX}[\s(]*(?:{NUMBER_REGEX}|{REPORT_LINE_CODE_REGEX})[\s)]*)*"
)
REFERENCE_UNSAFE_CHARS_REGEX = re.compile(r"[().\s*/+\-]")

AGGREGATION_TERM_SPLIT_REGEX = re.compile(r"[-+/*]")
AGGREGATION_NUMBER_TERM_REGEX = re.compile(rf"^{NUMBER_REGEX}$")
AGGREGATION_CODE_TERM_REGEX = re.compile(
    r"^(?P<line_code>[^.]+)\.(?P<expr_label>[^.]+)$"
)
IF_OTHER_EXPR_SUBFORMULA_REGEX = re.compile(
    r"if_other_expr_(above|below)\((?P<line_code>.+)[.](?P<expr_label>.+),.+\)"
)

AUDITABLE_ENGINES = frozenset({"domain", "external", "aggregation"})

NUMBER_FIGURE_TYPES = ("float", "integer", "monetary", "percentage")

LINE_ID_HIERARCHY_DELIMITER = "|"

CURRENCIES_USING_LAKH = {"AFN", "BDT", "INR", "MMK", "NPR", "PKR", "LKR"}

REPORT_OPTION_FILTER_DEPENDS = ("root_report_id", "section_main_report_ids")


def report_option_filter_field(
    field_type, field_name, string=None, default=False, **kwargs
):
    return field_type(
        string=string,
        compute=lambda records: records._compute_report_option_filter(
            field_name, default
        ),
        precompute=True,
        readonly=False,
        store=True,
        depends=list(REPORT_OPTION_FILTER_DEPENDS),
        **kwargs,
    )


class AccountReport(models.Model):
    _name = "report.formula"
    _description = "Formula Report"
    _order = "sequence, id"

    name = fields.Char(
        translate=True,
        required=True,
    )
    sequence = fields.Integer()
    active = fields.Boolean(default=True)
    line_ids = fields.One2many(
        comodel_name="report.formula.line",
        inverse_name="report_id",
        string="Lines",
    )
    column_ids = fields.One2many(
        comodel_name="report.formula.column",
        inverse_name="report_id",
        string="Columns",
    )
    root_report_id = fields.Many2one(
        comodel_name="report.formula",
        index="btree_not_null",
        help="The report this report is a variant of.",
    )
    variant_report_ids = fields.One2many(
        comodel_name="report.formula",
        inverse_name="root_report_id",
        string="Variants",
    )
    section_report_ids = fields.Many2many(
        comodel_name="report.formula",
        relation="report_formula_section_rel",
        column1="main_report_id",
        column2="sub_report_id",
        string="Sections",
    )
    section_main_report_ids = fields.Many2many(
        comodel_name="report.formula",
        relation="report_formula_section_rel",
        column1="sub_report_id",
        column2="main_report_id",
        string="Section Of",
    )
    use_sections = fields.Boolean(
        string="Composite Report",
        compute="_compute_use_sections",
        store=True,
        readonly=False,
        help="Create a structured report with multiple sections for convenient navigation and simultaneous printing.",
    )
    country_id = fields.Many2one(comodel_name="res.country")
    availability_condition = fields.Selection(
        selection=[
            ("country", "Country Matches"),
            ("always", "Always"),
        ],
        string="Availability",
        compute="_compute_availability_condition",
        store=True,
        readonly=False,
    )
    custom_handler_model_id = fields.Many2one(comodel_name="ir.model")
    custom_handler_model_name = fields.Char(
        related="custom_handler_model_id.model",
        string="Custom Handler Model Name",
    )
    source_model = fields.Char(
        help="Technical name of the model the report's 'domain' expressions search "
        "and its lines group by. Empty: the module that owns the report decides.",
    )
    source_date_field = fields.Char(
        help="Date field of the source model the report's period filters on. "
        "Empty: 'date'.",
    )
    source_measure_field = fields.Char(
        help="Numeric field of the source model a 'domain' expression sums.",
    )
    load_more_limit = fields.Integer()
    search_bar = fields.Boolean()
    prefix_groups_threshold = fields.Integer(default=4000)
    integer_rounding = fields.Selection(
        selection=[("HALF-UP", "Nearest"), ("UP", "Up"), ("DOWN", "Down")]
    )
    default_opening_date_filter = report_option_filter_field(
        fields.Selection,
        "default_opening_date_filter",
        "Default Opening",
        default="previous_month",
        selection=[
            ("this_year", "This Year"),
            ("this_quarter", "This Quarter"),
            ("this_month", "This Month"),
            ("today", "Today"),
            ("previous_month", "Last Month"),
            ("previous_quarter", "Last Quarter"),
            ("previous_year", "Last Year"),
        ],
    )

    filter_date = report_option_filter_field(
        fields.Boolean,
        "filter_date",
        "Date Filter",
        default=True,
        help="A report whose figures do not depend on a period hides the date filter.",
    )
    filter_date_range = report_option_filter_field(
        fields.Boolean,
        "filter_date_range",
        "Date Range",
        default=True,
    )
    filter_unfold_all = report_option_filter_field(
        fields.Boolean, "filter_unfold_all", "Unfold All"
    )
    filter_hide_0_lines = report_option_filter_field(
        fields.Selection,
        "filter_hide_0_lines",
        "Hide lines at 0",
        default="optional",
        selection=[
            ("by_default", "Enabled by Default"),
            ("optional", "Optional"),
            ("never", "Never"),
        ],
    )
    filter_period_comparison = report_option_filter_field(
        fields.Boolean, "filter_period_comparison", "Period Comparison", default=True
    )
    filter_growth_comparison = report_option_filter_field(
        fields.Boolean, "filter_growth_comparison", "Growth Comparison", default=True
    )

    def _get_custom_handler_model(self):
        return (
            self.custom_handler_model_name
            or self.root_report_id.custom_handler_model_name
            or None
        )

    def _get_variants(self, report_id):
        source_report = self.env["report.formula"].browse(report_id)
        if source_report.root_report_id:
            # We need to get the root report in order to get all variants
            source_report = source_report.root_report_id
        return (
            source_report
            + source_report.with_context(active_test=False).variant_report_ids
        )

    @api.model
    def get_report_company_ids(self, options):
        return [comp_data["id"] for comp_data in options["companies"]]

    @api.constrains("custom_handler_model_id")
    @_debug.perf.timed
    def _check_custom_handler_model_id(self):
        for report in self:
            if report.custom_handler_model_id:
                custom_handler_model = self.env.registry[
                    "report.formula.custom.handler"
                ]
                current_model = self.env[report.custom_handler_model_name]
                if not isinstance(current_model, custom_handler_model):
                    raise ValidationError(
                        self.env._(
                            "Field 'Custom Handler Model' can only reference records inheriting from [%s].",
                            custom_handler_model._name,
                        )
                    )

    def _get_required_source_model(self):
        source_model = self._get_source_model()
        if source_model is None:
            raise UserError(
                self.env._(
                    "Report '%(report)s' has no source model, so it can neither "
                    "evaluate a 'domain' expression nor group its lines.",
                    report=self.display_name,
                )
            )
        return source_model

    def _get_source_date_field(self):
        return self.source_date_field or self.root_report_id.source_date_field or "date"

    def _get_source_measure_field(self):
        """The numeric field a `domain` expression sums; None when the report has none."""
        return (
            self.source_measure_field
            or self.root_report_id.source_measure_field
            or None
        )

    @api.constrains("source_model", "source_date_field", "source_measure_field")
    def _check_source_fields(self):
        for report in self:
            if not report.source_model:
                continue
            if report.source_model not in self.env:
                raise ValidationError(
                    self.env._(
                        "Report '%(report)s' names the source model '%(model)s', "
                        "which does not exist.",
                        report=report.name,
                        model=report.source_model,
                    )
                )
            source_fields = self.env[report.source_model]._fields
            for fname in (report.source_date_field, report.source_measure_field):
                if fname and fname not in source_fields:
                    raise ValidationError(
                        self.env._(
                            "Report '%(report)s': '%(field)s' is not a field of "
                            "'%(model)s'.",
                            report=report.name,
                            field=fname,
                            model=report.source_model,
                        )
                    )

    def _get_source_domains(self, options, date_scope):
        return []

    def _get_year_bounds(self, date):
        date_from, date_to = date_utils.get_fiscal_year(date)
        return {"date_from": date_from, "date_to": date_to}

    def _get_year_end(self):
        return 31, 12

    def _get_totals_below_sections(self):
        return False

    def _init_currency_table(self, options):
        return

    def _add_common_warnings(self, options, warnings):
        return

    def _add_account_status_on_lines(self, lines, options):
        return lines

    def _create_hierarchy(self, lines, options):
        return lines

    def _update_line_names_for_consolidation(self, lines):
        return

    def _postprocess_chatter_for_annotations(self, lines):
        return

    def _set_budget_column_comparisons(self, options, line):
        return

    def _prepare_editable_cell_data(
        self, options, col_group_key, groupby_model, column_expression, column_value
    ):
        return None

    def _prepare_info_popup_data(
        self,
        options,
        col_group_key,
        column_expr_label,
        target_line_res_dict,
        line_expressions_map,
    ):
        return {}

    def _is_available_for(self, options):
        """Among these variants, those the options' companies may use."""
        countries = (
            self.env["res.company"]
            .browse(self.get_report_company_ids(options))
            .country_id
        )
        return self.filtered(
            lambda report: (
                report.availability_condition == "always"
                or (
                    report.availability_condition == "country"
                    and (not report.country_id or report.country_id in countries)
                )
            )
        )

    def _apply_branch_rules_to_buttons(self, options):
        return

    def get_annotations(self, options, lines):
        return {}

    def _get_source_model(self):
        """The model a `domain` expression searches; None when the report has none."""
        source_model = self.source_model or self.root_report_id.source_model
        return self.env[source_model] if source_model else None

    @_debug.perf.timed
    def _compute_report_option_filter(self, field_name, default_value=False):
        sections = self.filtered("section_main_report_ids")
        accessible_report_ids = (
            sections._get_accessible_report_ids() if sections else set()
        )
        for report in self.sorted(lambda x: not x.section_report_ids):
            is_accessible = report.id in accessible_report_ids
            is_variant = bool(report.root_report_id)
            if (is_accessible or is_variant) and report.section_main_report_ids:
                continue
            if is_variant:
                source_report = report.root_report_id
            elif len(report.section_main_report_ids) == 1 and not is_accessible:
                source_report = report.section_main_report_ids
            else:
                source_report = None
            report[field_name] = (
                source_report[field_name]
                if source_report is not None
                else default_value
            )

    def _get_accessible_report_ids(self):
        candidate_ids = {report.id for report in self if isinstance(report.id, int)}
        if not candidate_ids:
            return set()
        contexts = (
            self.env["ir.actions.client"]
            .search([("tag", "=", "account_report")])
            .mapped("context")
        )
        return candidate_ids & {
            report_id
            for report_id in map(self._read_action_report_id, contexts)
            if report_id is not None
        }

    @staticmethod
    def _read_action_report_id(context):
        try:
            parsed_context = ast.literal_eval(context or "{}")
        except ValueError, SyntaxError, MemoryError, RecursionError:
            return None
        if not isinstance(parsed_context, dict):
            return None
        report_id = parsed_context.get("report_id")
        return report_id if isinstance(report_id, int) else None

    @api.depends("root_report_id", "country_id")
    def _compute_availability_condition(self):
        for report in self:
            if report.root_report_id and report.country_id:
                report.availability_condition = "country"
            elif not report.availability_condition:
                report.availability_condition = "always"

    @api.depends("section_report_ids")
    def _compute_use_sections(self):
        for report in self:
            report.use_sections = bool(report.section_report_ids)

    @api.constrains("root_report_id")
    @_debug.perf.timed
    def _check_root_report_id(self):
        for report in self:
            if report.root_report_id.root_report_id:
                _debug.logic(
                    "root_report_rejected", report=report, reason="root_has_root"
                )
                raise ValidationError(
                    self.env._(
                        "Only a report without a root report of its own can be selected as root report."
                    )
                )
            if report.root_report_id and report.variant_report_ids:
                _debug.logic(
                    "variant_root_rejected",
                    report=report,
                    variants=report.variant_report_ids,
                )
                raise ValidationError(
                    self.env._(
                        'Report "%(report)s" is the root report of %(count)s other '
                        "report(s), so it cannot become a variant itself.",
                        report=report.display_name,
                        count=len(report.variant_report_ids),
                    )
                )

    @api.constrains("line_ids")
    @_debug.perf.timed
    def _check_parent_sequence(self):
        for report in self:
            seen_ids = set()
            for line in report.line_ids.sorted(lambda x: (x.sequence, x.id)):
                if line.parent_id and line.parent_id.id not in seen_ids:
                    raise ValidationError(
                        self.env._(
                            'Line "%(line)s" defines line "%(parent_line)s" as its parent, but appears before it in the report. '
                            "The parent must always come first.",
                            line=line.name,
                            parent_line=line.parent_id.name,
                        )
                    )
                seen_ids.add(line.id)

    @api.constrains("section_report_ids")
    @_debug.perf.timed
    def _check_section_report_ids(self):
        for record in self:
            if not record.section_report_ids:
                continue
            if (
                any(section.section_report_ids for section in record.section_report_ids)
                or record.section_main_report_ids
            ):
                raise ValidationError(
                    self.env._(
                        "The sections defined on a report cannot have sections themselves."
                    )
                )

    @api.constrains("availability_condition", "country_id")
    @_debug.perf.timed
    def _check_availability_condition(self):
        for record in self:
            if record.availability_condition == "country" and not record.country_id:
                raise ValidationError(
                    self.env._(
                        "The Availability is set to 'Country Matches' but the field Country is not set."
                    )
                )

    @api.onchange("availability_condition")
    def _onchange_availability_condition(self):
        if self.availability_condition != "country":
            self.country_id = None

    @_debug.perf.timed
    def copy_data(self, default=None):
        _debug.lifecycle("copy_data", records=self)
        vals_list = super().copy_data(default=default)
        return [
            dict(vals, name=report._get_copied_name())
            for report, vals in zip(self, vals_list, strict=True)
        ]

    @_debug.perf.timed
    def copy(self, default=None):
        _debug.lifecycle("copy", records=self)
        new_reports = super().copy(default=default)
        for old_report, new_report in zip(self, new_reports, strict=True):
            old_report.line_ids._copy_hierarchy(new_report)
            old_report.column_ids.copy({"report_id": new_report.id})
        return new_reports

    @api.ondelete(at_uninstall=False)
    @_debug.perf.timed
    def _unlink_if_no_variant(self):
        _debug.lifecycle("_unlink_if_no_variant", records=self)
        if self.variant_report_ids:
            raise UserError(self.env._("You can't delete a report that has variants."))
        self.line_ids.unlink()

    def _get_copied_name(self):
        self.check_singleton()
        base_name = f"{self.name} {self.env._('(copy)')}"
        taken = set(
            self.with_context(active_test=False)
            .search([("name", "=like", f"{base_name}%")])
            .mapped("name")
        )
        if base_name not in taken:
            return base_name
        counter = 2
        while f"{base_name} {counter}" in taken:
            counter += 1
        return f"{base_name} {counter}"

    @api.depends("name", "country_id")
    def _compute_display_name(self):
        for report in self:
            if report.name:
                report.display_name = report.name + (
                    f" ({report.country_id.code})" if report.country_id else ""
                )
            else:
                report.display_name = False
