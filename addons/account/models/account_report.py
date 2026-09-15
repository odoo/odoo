import ast
import re
from collections import defaultdict

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.libs.debug_log import DebugLog

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

ACCOUNT_CODES_ENGINE_SPLIT_REGEX = re.compile(r"(?=[+-])")
ACCOUNT_CODES_ENGINE_TERM_REGEX = re.compile(
    r"^(?P<sign>[+-]?)"
    r"(?P<prefix>([A-Za-z\d.]*|tag\([\w.]+\))((?=\\)|(?<=[^CD])))"
    r"(\\\((?P<excluded_prefixes>([A-Za-z\d.]+,)*[A-Za-z\d.]*)\))?"
    r"(?P<balance_character>[DC]?)$"
)

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

AUDITABLE_ENGINES = frozenset(
    {"tax_tags", "domain", "account_codes", "external", "aggregation"}
)

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
    _name = "account.report"
    _description = "Accounting Report"
    _order = "sequence, id"

    name = fields.Char(
        translate=True,
        required=True,
    )
    sequence = fields.Integer()
    active = fields.Boolean(default=True)
    line_ids = fields.One2many(
        comodel_name="account.report.line",
        inverse_name="report_id",
        string="Lines",
    )
    column_ids = fields.One2many(
        comodel_name="account.report.column",
        inverse_name="report_id",
        string="Columns",
    )
    root_report_id = fields.Many2one(
        comodel_name="account.report",
        index="btree_not_null",
        help="The report this report is a variant of.",
    )
    variant_report_ids = fields.One2many(
        comodel_name="account.report",
        inverse_name="root_report_id",
        string="Variants",
    )
    section_report_ids = fields.Many2many(
        comodel_name="account.report",
        relation="account_report_section_rel",
        column1="main_report_id",
        column2="sub_report_id",
        string="Sections",
    )
    section_main_report_ids = fields.Many2many(
        comodel_name="account.report",
        relation="account_report_section_rel",
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
    chart_template = fields.Selection(
        selection=lambda self: self.env[
            "account.chart.template"
        ]._select_chart_template(),
        string="Chart of Accounts",
    )
    country_id = fields.Many2one(comodel_name="res.country")
    only_tax_exigible = report_option_filter_field(
        fields.Boolean, "only_tax_exigible", "Only Tax Exigible Lines"
    )
    availability_condition = fields.Selection(
        selection=[
            ("country", "Country Matches"),
            ("coa", "Chart of Accounts Matches"),
            ("always", "Always"),
        ],
        string="Availability",
        compute="_compute_availability_condition",
        store=True,
        readonly=False,
    )
    load_more_limit = fields.Integer()
    search_bar = fields.Boolean()
    prefix_groups_threshold = fields.Integer(default=4000)
    integer_rounding = fields.Selection(
        selection=[("HALF-UP", "Nearest"), ("UP", "Up"), ("DOWN", "Down")]
    )
    allow_foreign_vat = report_option_filter_field(
        fields.Boolean, "allow_foreign_vat", "Allow Foreign VAT"
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
            ("this_return_period", "This Return Period"),
            ("previous_return_period", "Last Return Period"),
        ],
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
    filter_date_range = report_option_filter_field(
        fields.Boolean,
        "filter_date_range",
        "Date Range",
        default=True,
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
                    _(
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
                    _(
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
                        _(
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
                    _(
                        "The sections defined on a report cannot have sections themselves."
                    )
                )

    @api.constrains("availability_condition", "country_id", "chart_template")
    @_debug.perf.timed
    def _check_availability_condition(self):
        for record in self:
            if record.availability_condition == "country" and not record.country_id:
                raise ValidationError(
                    _(
                        "The Availability is set to 'Country Matches' but the field Country is not set."
                    )
                )
            if record.availability_condition == "coa" and not record.chart_template:
                raise ValidationError(
                    _(
                        "The Availability is set to 'Chart of Accounts Matches' but the field Chart of Accounts is not set."
                    )
                )

    @api.onchange("availability_condition")
    def _onchange_availability_condition(self):
        if self.availability_condition != "country":
            self.country_id = None

    @_debug.perf.timed
    def write(self, vals):
        _debug.lifecycle("write", records=self, fields=sorted(vals))
        if "country_id" in vals:
            self._move_tax_tags_to_country(vals["country_id"])
        return super().write(vals)

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

        reports_by_tag = defaultdict(self.env["account.report"].browse)
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
        expression_model = self.env["account.report.expression"]
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
            raise UserError(_("You can't delete a report that has variants."))
        self.line_ids.unlink()

    def _get_copied_name(self):
        self.check_singleton()
        base_name = f"{self.name} {_('(copy)')}"
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
