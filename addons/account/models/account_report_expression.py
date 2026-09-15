import ast
import re
from collections import defaultdict

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Command, Domain
from odoo.libs.debug_log import DebugLog

from odoo.addons.account.models.account_report import (
    ACCOUNT_CODES_ENGINE_SPLIT_REGEX,
    ACCOUNT_CODES_ENGINE_TERM_REGEX,
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
    _name = "account.report.expression"
    _description = "Accounting Report Expression"
    _rec_name = "report_line_name"

    report_line_id = fields.Many2one(
        comodel_name="account.report.line",
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
            ("tax_tags", "Tax Tags"),
            ("aggregation", "Aggregate Other Formulas"),
            ("account_codes", "Prefix of Account Codes"),
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
            ("previous_return_period", "From previous return period"),
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

    carryover_target = fields.Char(
        string="Carry Over To",
        help="Formula in the form line_code.expression_label. This allows setting the target of the carryover for this expression "
        "(on a _carryover_*-labeled expression), in case it is different from the parent line.",
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

    @api.constrains("formula")
    @_debug.perf.timed
    def _check_formula(self):
        def raise_formula_error(expression, cause=None):
            raise ValidationError(
                self.env._(
                    "Invalid formula for expression '%(label)s' of line '%(line)s': %(formula)s",
                    label=expression.label,
                    line=expression.report_line_name,
                    formula=expression.formula,
                )
            ) from cause

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
                self.env["account.move.line"]._search(domain)
            except Exception as error:
                raise_formula_error(expression, error)

        for expression in expressions_by_engine.get("account_codes", []):
            for token in ACCOUNT_CODES_ENGINE_SPLIT_REGEX.split(
                expression.formula.replace(" ", "")
            ):
                if token:
                    token_match = ACCOUNT_CODES_ENGINE_TERM_REGEX.match(token)
                    prefix = token_match and token_match["prefix"]
                    if not prefix:
                        raise_formula_error(expression)

        for expression in expressions_by_engine.get("aggregation", []):
            if not AGGREGATION_ENGINE_FORMULA_REGEX.fullmatch(expression.formula):
                raise_formula_error(expression)

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

        result = super().create(vals_list)
        result.filtered(lambda x: x.engine == "tax_tags")._create_missing_tax_tags()
        return result

    @_debug.perf.timed
    def write(self, vals):
        _debug.lifecycle("write", records=self, fields=sorted(vals))
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
            sub_expressions = self.env["account.report.expression"]

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
                sub_expressions |= self.env["account.report.expression"].search(
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
                self.env["account.report"].browse(int(cross_report_value)).exists()
            )
        else:
            target_report = self.env.ref(cross_report_value, raise_if_not_found=False)
            if target_report and target_report._name != "account.report":
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
            return self.env["account.report.expression"].search(
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
