import ast
import re
from collections import defaultdict

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog

from .account_report import (
    AGGREGATION_CODE_TERM_REGEX,
    AGGREGATION_ENGINE_FORMULA_REGEX,
    AGGREGATION_NUMBER_TERM_REGEX,
    AGGREGATION_TERM_SPLIT_REGEX,
    AUDITABLE_ENGINES,
    CROSS_REPORT_REGEX,
    FIGURE_TYPE_SELECTION_VALUES,
    IF_OTHER_EXPR_SUBFORMULA_REGEX,
    REFERENCE_UNSAFE_CHARS_REGEX,
    SUM_CHILDREN_FORMULA,
)

_debug = DebugLog(__name__)


class AccountReportExpression(models.Model):
    _name = "report.formula.expression"
    _description = "Formula Report Expression"
    _rec_name = "report_line_name"

    report_line_id = fields.Many2one(
        comodel_name="report.formula.line",
        index=True,
        required=True,
        ondelete="cascade",
    )
    report_line_name = fields.Char(
        related="report_line_id.name",
        string="Report Line Name",
    )
    label = fields.Char(
        copy=True,
        required=True,
    )
    engine = fields.Selection(
        selection=[
            ("domain", "Odoo Domain"),
            ("aggregation", "Aggregate Other Formulas"),
            ("external", "External Value"),
            ("custom", "Custom Python Function"),
        ],
        string="Computation Engine",
        required=True,
    )
    formula = fields.Char(required=True)
    subformula = fields.Char()
    date_scope = fields.Selection(
        selection=[
            ("from_beginning", "From the very start"),
            ("from_fiscalyear", "From the start of the fiscal year"),
            ("to_beginning_of_fiscalyear", "At the beginning of the fiscal year"),
            ("to_beginning_of_period", "At the beginning of the period"),
            ("strict_range", "Strictly on the given dates"),
        ],
        default="strict_range",
        required=True,
    )
    figure_type = fields.Selection(selection=FIGURE_TYPE_SELECTION_VALUES)
    green_on_positive = fields.Boolean(
        string="Is Growth Good when Positive",
        default=True,
    )
    blank_if_zero = fields.Boolean(
        string="Blank if Zero",
        help="When checked, 0 values will not show when displaying this expression's value.",
    )
    auditable = fields.Boolean(
        compute="_compute_auditable",
        store=True,
        readonly=False,
    )

    _domain_engine_subformula_required = models.Constraint(
        "CHECK(engine != 'domain' OR subformula IS NOT NULL)",
        "Expressions using 'domain' engine should all have a subformula.",
    )
    _line_label_uniq = models.Constraint(
        "UNIQUE(report_line_id,label)",
        "The expression label must be unique per report line.",
    )

    @api.constrains("label")
    @_debug.perf.timed
    def _check_label(self):
        for expression in self:
            if REFERENCE_UNSAFE_CHARS_REGEX.search(expression.label or ""):
                raise ValidationError(
                    _(
                        'The label of expression "%(label)s" on line "%(line)s" is the '
                        "second half of an aggregation term, so it cannot contain a "
                        "dot, a bracket, whitespace or an operator.",
                        label=expression.label,
                        line=expression.report_line_name,
                    )
                )

    def _raise_formula_error(self, cause=None):
        self.check_singleton()
        raise ValidationError(
            self.env._(
                "Invalid formula for expression '%(label)s' of line '%(line)s': %(formula)s",
                label=self.label,
                line=self.report_line_name,
                formula=self.formula,
            )
        ) from cause

    @api.constrains("formula")
    @_debug.perf.timed
    def _check_formula(self):
        expressions_by_engine = self.grouped("engine")
        if _debug.pipeline.enabled:
            _debug.pipeline(
                "formulas_checked",
                records=self,
                per_engine={
                    engine: len(exprs)
                    for engine, exprs in expressions_by_engine.items()
                },
            )
        for expression in expressions_by_engine.get("domain", []):
            try:
                domain = ast.literal_eval(expression.formula)
                source_model = expression.report_line_id.report_id._get_source_model()
                if source_model is not None:
                    source_model._search(domain)
            except (
                SyntaxError,
                TypeError,
                ValueError,
                MemoryError,
                RecursionError,
            ) as error:
                expression._raise_formula_error(error)

        for expression in expressions_by_engine.get("aggregation", []):
            if not AGGREGATION_ENGINE_FORMULA_REGEX.fullmatch(expression.formula):
                expression._raise_formula_error()

    @api.depends("engine")
    def _compute_auditable(self):
        auditable_engines = self._get_auditable_engines()
        for expression in self:
            expression.auditable = expression.engine in auditable_engines

    @api.constrains("engine", "report_line_id")
    @_debug.perf.timed
    def _check_engine(self):
        for expression in self:
            if expression.engine in ("aggregation", "external") and (
                expression.report_line_id.groupby
                or expression.report_line_id.user_groupby
            ):
                engine_description = dict(
                    expression._fields["engine"]._description_selection(self.env)
                )
                raise ValidationError(
                    _(
                        "Groupby feature isn't supported by '%(engine)s' engine. Please remove the groupby value on '%(report_line)s'",
                        engine=engine_description[expression.engine],
                        report_line=expression.report_line_id.display_name,
                    )
                )

    def _get_auditable_engines(self):
        return AUDITABLE_ENGINES

    @staticmethod
    def _strip_formula(formula):
        return re.sub(r"\s+", " ", formula.strip())

    def _strip_formula_vals(self, vals):
        for key in ("formula", "subformula"):
            if isinstance(vals.get(key), str):
                vals[key] = self._strip_formula(vals[key])

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
        for vals in vals_list:
            self._strip_formula_vals(vals)

        return super().create(vals_list)

    @_debug.perf.timed
    def write(self, vals):
        _debug.lifecycle("write", records=self, fields=sorted(vals))
        self._strip_formula_vals(vals)
        return super().write(vals)

    @api.depends("report_line_name", "label")
    def _compute_display_name(self):
        for expr in self:
            expr.display_name = f"{expr.report_line_name} [{expr.label}]"

    @_debug.perf.timed
    def _expand_aggregations(self):
        result = self

        to_expand = self.filtered(lambda x: x.engine == "aggregation")
        while to_expand:
            domains = []
            sub_expressions = self.env["report.formula.expression"]

            for candidate_expr in to_expand:
                if candidate_expr.formula == SUM_CHILDREN_FORMULA:
                    sub_expressions |= candidate_expr.report_line_id.children_ids.expression_ids.filtered(
                        lambda e, label=candidate_expr.label: e.label == label
                    )
                else:
                    labels_by_code = candidate_expr._get_aggregation_terms_details()

                    if (
                        candidate_expr.subformula
                        and candidate_expr.subformula.startswith("cross_report")
                    ):
                        report_id = candidate_expr._get_cross_report_id()
                        _debug.logic(
                            "cross_report_dependency",
                            expression=candidate_expr,
                            report_id=report_id,
                        )
                    else:
                        report_id = candidate_expr.report_line_id.report_id.id
                    cross_report_domain = [("report_line_id.report_id", "=", report_id)]

                    for line_code, expr_labels in labels_by_code.items():
                        dependency_domain = [
                            ("report_line_id.code", "=", line_code),
                            ("label", "in", tuple(expr_labels)),
                        ] + cross_report_domain
                        domains.append(dependency_domain)

            if domains:
                sub_expressions |= self.env["report.formula.expression"].search(
                    Domain.OR(domains)
                )

            seen_ids = set(result.ids)
            to_expand = sub_expressions.filtered(
                lambda x, seen_ids=seen_ids: (
                    x.engine == "aggregation" and x.id not in seen_ids
                )
            )
            result |= sub_expressions
            _debug.pipeline(
                "aggregation_pass",
                records=self,
                domains=len(domains),
                sub_expressions=len(sub_expressions),
                to_expand=len(to_expand),
            )

        _debug.pipeline("aggregations_expanded", records=self, result=len(result))
        return result

    @_debug.perf.timed
    def _get_cross_report_id(self):
        self.check_singleton()
        error_context = {
            "report_name": self.report_line_id.report_id.display_name,
            "line_name": self.report_line_name,
            "label": self.label,
        }
        subformula_match = CROSS_REPORT_REGEX.match(self.subformula or "")
        if not subformula_match:
            raise UserError(
                _(
                    "In report '%(report_name)s', on line '%(line_name)s', with label '%(label)s',\n"
                    "The format of the cross report expression is invalid. \n"
                    "Expected: cross_report(<report_id>|<xml_id>)"
                    "Example:  cross_report(my_module.my_report) or cross_report(123)",
                    **error_context,
                )
            )

        cross_report_value = subformula_match.group(1).strip()
        if cross_report_value.isdigit():
            target_report = (
                self.env["report.formula"].browse(int(cross_report_value)).exists()
            )
        else:
            target_report = self.env.ref(cross_report_value, raise_if_not_found=False)
            if target_report and target_report._name != "report.formula":
                target_report = None

        if _debug.logic.enabled:
            _debug.logic(
                "cross_report_resolved",
                expression=self,
                by_id=cross_report_value.isdigit(),
                target_report=target_report,
            )
        if not target_report:
            raise UserError(
                _(
                    "In report '%(report_name)s', on line '%(line_name)s', with label '%(label)s',\n"
                    "Failed to parse the cross report id or xml_id.\n",
                    **error_context,
                )
            )
        if target_report == self.report_line_id.report_id:
            raise UserError(_("You cannot use cross report on itself"))
        return target_report.id

    @staticmethod
    def _split_aggregation_formula_terms(formula):
        return AGGREGATION_TERM_SPLIT_REGEX.split(re.sub(r"[\s()]", "", formula))

    @staticmethod
    def _match_aggregation_code_term(term):
        if not term or AGGREGATION_NUMBER_TERM_REGEX.match(term):
            return None
        return AGGREGATION_CODE_TERM_REGEX.match(term)

    def _get_aggregation_terms_details(self):
        totals_by_code = defaultdict(set)
        for expression in self:
            if expression.engine != "aggregation":
                _debug.logic(
                    "aggregation_details_rejected",
                    expression=expression,
                    engine=expression.engine,
                )
                raise UserError(
                    _(
                        "Cannot get aggregation details from a line not using 'aggregation' engine"
                    )
                )

            for term in self._split_aggregation_formula_terms(expression.formula):
                term_match = self._match_aggregation_code_term(term)
                if term_match:
                    totals_by_code[term_match["line_code"]].add(
                        term_match["expr_label"]
                    )

            if expression.subformula:
                if_other_expr_match = IF_OTHER_EXPR_SUBFORMULA_REGEX.match(
                    expression.subformula
                )
                if if_other_expr_match:
                    totals_by_code[if_other_expr_match["line_code"]].add(
                        if_other_expr_match["expr_label"]
                    )

        _debug.pipeline(
            "aggregation_terms_collected", expressions=self, codes=len(totals_by_code)
        )
        return totals_by_code
