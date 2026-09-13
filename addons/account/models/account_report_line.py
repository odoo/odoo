import re
from collections import defaultdict

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.libs.debug_log import DebugLog

from odoo.addons.account.models.account_report import (
    DOMAIN_REGEX,
    REFERENCE_UNSAFE_CHARS_REGEX,
)

_debug = DebugLog(__name__)


def _replace_codes_in_formula(formula, code_mapping):
    if not code_mapping:
        return formula
    alternatives = "|".join(
        re.escape(old_code) for old_code in sorted(code_mapping, key=len, reverse=True)
    )
    return re.sub(
        rf"(?<=\W)(?:{alternatives})(?=\W)",
        lambda match: code_mapping[match.group()],
        f" {formula} ",
    ).strip()


class AccountReportLine(models.Model):
    _name = "account.report.line"
    _description = "Accounting Report Line"
    _order = "sequence, id"

    name = fields.Char(
        translate=True,
        required=True,
    )
    expression_ids = fields.One2many(
        comodel_name="account.report.expression",
        inverse_name="report_line_id",
        string="Expressions",
    )
    report_id = fields.Many2one(
        comodel_name="account.report",
        string="Parent Report",
        compute="_compute_report_id",
        precompute=True,
        recursive=True,
        store=True,
        index=True,
        readonly=False,
        required=True,
        ondelete="cascade",
    )
    hierarchy_level = fields.Integer(
        string="Level",
        compute="_compute_hierarchy_level",
        precompute=True,
        recursive=True,
        store=True,
        readonly=False,
        required=True,
    )
    parent_id = fields.Many2one(
        comodel_name="account.report.line",
        string="Parent Line",
        index="btree_not_null",
        ondelete="set null",
    )
    children_ids = fields.One2many(
        comodel_name="account.report.line",
        inverse_name="parent_id",
        string="Child Lines",
    )
    groupby = fields.Char(
        string="Group By",
        help="Comma-separated list of fields from account.move.line (Journal Item). When set, this line will generate sublines grouped by those keys.",
    )
    user_groupby = fields.Char(
        string="User Group By",
        compute="_compute_user_groupby",
        precompute=True,
        store=True,
        readonly=False,
        help="Comma-separated list of fields from account.move.line (Journal Item). When set, this line will generate sublines grouped by those keys.",
    )
    sequence = fields.Integer()
    code = fields.Char(help="Unique identifier for this line.")
    foldable = fields.Boolean(
        help="By default, we always unfold the lines that can be. If this is checked, the line won't be unfolded by default, and a folding button will be displayed."
    )
    print_on_new_page = fields.Boolean(
        help="When checked this line and everything after it will be printed on a new page."
    )
    action_id = fields.Many2one(
        comodel_name="ir.actions.actions",
        help="Setting this field will turn the line into a link, executing the action when clicked.",
    )
    hide_if_zero = fields.Boolean(
        string="Hide if Zero",
        help="This line and its children will be hidden when all of their columns are 0.",
    )
    domain_formula = fields.Char(
        string="Domain Formula Shortcut",
        inverse="_inverse_domain_formula",
        store=False,
        copy=False,
        help="Internal field to shorten expression_ids creation for the domain engine",
    )
    account_codes_formula = fields.Char(
        string="Account Codes Formula Shortcut",
        inverse="_inverse_account_codes_formula",
        store=False,
        copy=False,
        help="Internal field to shorten expression_ids creation for the account_codes engine",
    )
    aggregation_formula = fields.Char(
        string="Aggregation Formula Shortcut",
        inverse="_inverse_aggregation_formula",
        store=False,
        copy=False,
        help="Internal field to shorten expression_ids creation for the aggregation engine",
    )
    external_formula = fields.Char(
        string="External Formula Shortcut",
        inverse="_inverse_external_formula",
        store=False,
        copy=False,
        help="Internal field to shorten expression_ids creation for the external engine",
    )
    horizontal_split_side = fields.Selection(
        selection=[("left", "Left"), ("right", "Right")],
        compute="_compute_horizontal_split_side",
        recursive=True,
        store=True,
        readonly=False,
    )
    tax_tags_formula = fields.Char(
        string="Tax Tags Formula Shortcut",
        inverse="_inverse_tax_tags_formula",
        store=False,
        copy=False,
        help="Internal field to shorten expression_ids creation for the tax_tags engine",
    )

    _code_uniq = models.UniqueIndex(
        "(report_id, code) WHERE code IS NOT NULL",
        "A report line with the same code already exists.",
    )

    @api.constrains("code")
    @_debug.perf.timed
    def _check_code(self):
        for report_line in self:
            if report_line.code and REFERENCE_UNSAFE_CHARS_REGEX.search(
                report_line.code
            ):
                raise ValidationError(
                    _(
                        'The code of line "%(line)s" is "%(code)s". A code is what an '
                        "aggregation formula and a carryover target name a line by, so "
                        "it cannot contain a dot, a bracket, whitespace or an operator.",
                        line=report_line.name,
                        code=report_line.code,
                    )
                )

    @api.depends("parent_id.hierarchy_level")
    def _compute_hierarchy_level(self):
        for report_line in self:
            if report_line.parent_id:
                increase_level = 3 if report_line.parent_id.hierarchy_level == 0 else 2
                report_line.hierarchy_level = (
                    report_line.parent_id.hierarchy_level + increase_level
                )
            else:
                report_line.hierarchy_level = 1

    @api.depends("parent_id.report_id")
    def _compute_report_id(self):
        for report_line in self:
            if report_line.parent_id:
                report_line.report_id = report_line.parent_id.report_id

    @api.depends("parent_id.horizontal_split_side")
    def _compute_horizontal_split_side(self):
        for report_line in self:
            if report_line.parent_id:
                report_line.horizontal_split_side = (
                    report_line.parent_id.horizontal_split_side
                )

    def _compute_user_groupby(self):
        for report_line in self:
            report_line.user_groupby = report_line.groupby

    @api.constrains("parent_id")
    @_debug.perf.timed
    def _check_groupby_no_child(self):
        for report_line in self:
            if report_line.parent_id.groupby or report_line.parent_id.user_groupby:
                raise ValidationError(
                    _(
                        "A line cannot have both children and a groupby value (line '%s').",
                        report_line.parent_id.name,
                    )
                )

    @api.constrains("groupby", "user_groupby")
    @_debug.perf.timed
    def _check_groupby(self):
        self.expression_ids._check_engine()

    @api.constrains("parent_id", "report_id")
    @_debug.perf.timed
    def _check_parent_report(self):
        for line in self:
            if line.parent_id and line.parent_id.report_id != line.report_id:
                raise ValidationError(
                    _(
                        'Line "%(line)s" belongs to report "%(report)s" but its parent '
                        '"%(parent)s" belongs to "%(parent_report)s". A line and its '
                        "parent must be in the same report.",
                        line=line.name,
                        report=line.report_id.display_name,
                        parent=line.parent_id.name,
                        parent_report=line.parent_id.report_id.display_name,
                    )
                )

    @api.constrains("parent_id")
    @_debug.perf.timed
    def _check_parent_line(self):
        for line in self.filtered(lambda x: x.parent_id == x):
            raise ValidationError(
                _('Line "%s" defines itself as its parent.', line.name)
            )
        if self._has_cycle("parent_id"):
            raise ValidationError(
                _("Report lines cannot form a recursive parent hierarchy.")
            )

    @_debug.perf.timed
    def _copy_hierarchy(self, copied_report):
        line_ids = set(self.ids)
        lines_by_parent_id = defaultdict(self.browse)
        for line in self:
            parent_id = line.parent_id.id if line.parent_id.id in line_ids else False
            lines_by_parent_id[parent_id] |= line

        code_mapping = {}
        taken_codes = set()

        def allocate_codes(line):
            if line.code:
                code = f"{line.code}_COPY"
                while code in taken_codes:
                    code = f"{code}_COPY"
                taken_codes.add(code)
                code_mapping[line.code] = code
            for child in lines_by_parent_id[line.id]:
                allocate_codes(child)

        for root in lines_by_parent_id[False]:
            allocate_codes(root)
        _debug.pipeline(
            "hierarchy_codes_allocated",
            report=copied_report,
            lines=self,
            roots=len(lines_by_parent_id[False]),
            renamed_codes=len(code_mapping),
        )

        copied_line_by_id = {}
        generation = lines_by_parent_id[False]
        while generation:
            vals_list = generation.copy_data()
            for line, vals in zip(generation, vals_list, strict=True):
                vals["report_id"] = copied_report.id
                vals["parent_id"] = (
                    copied_line_by_id[line.parent_id.id].id
                    if line.parent_id.id in copied_line_by_id
                    else False
                )
                vals["code"] = code_mapping.get(line.code, False)
            for line, copied_line in zip(
                generation, self.create(vals_list), strict=True
            ):
                copied_line_by_id[line.id] = copied_line
            next_generation = self.browse()
            for line in generation:
                next_generation |= lines_by_parent_id[line.id]
            _debug.pipeline(
                "hierarchy_generation_copied",
                report=copied_report,
                copied=len(vals_list),
                next_generation=len(next_generation),
            )
            generation = next_generation

        source_expressions = self.expression_ids
        if source_expressions:
            vals_list = source_expressions.copy_data()
            for expression, vals in zip(source_expressions, vals_list, strict=True):
                vals["report_line_id"] = copied_line_by_id[
                    expression.report_line_id.id
                ].id
                if expression.engine == "aggregation":
                    for key in ("formula", "subformula"):
                        if vals.get(key):
                            vals[key] = _replace_codes_in_formula(
                                vals[key], code_mapping
                            )
            _debug.pipeline(
                "hierarchy_expressions_copied",
                report=copied_report,
                expressions=source_expressions,
                copied_lines=len(copied_line_by_id),
            )
            self.env["account.report.expression"].create(vals_list)

        return code_mapping

    def _inverse_domain_formula(self):
        self._create_report_expression(engine="domain")

    def _inverse_aggregation_formula(self):
        self._create_report_expression(engine="aggregation")

    def _inverse_tax_tags_formula(self):
        self._create_report_expression(engine="tax_tags")

    def _inverse_account_codes_formula(self):
        self._create_report_expression(engine="account_codes")

    def _inverse_external_formula(self):
        self._create_report_expression(engine="external")

    @_debug.perf.timed
    def _create_report_expression(self, engine):
        vals_list = []
        xml_ids = self.expression_ids.filtered(
            lambda exp: exp.label == "balance"
        ).get_external_id()
        for report_line in self:
            if engine == "domain" and report_line.domain_formula:
                domain_match = DOMAIN_REGEX.match(report_line.domain_formula)
                if not domain_match:
                    raise ValidationError(
                        _(
                            "Invalid domain formula '%(formula)s' on report line "
                            "'%(line)s'. Expected the form 'sum(<domain>)' "
                            "(optionally '-sum(<domain>)').",
                            formula=report_line.domain_formula,
                            line=report_line.name,
                        )
                    )
                subformula, formula = domain_match.groups()
                formula = re.sub(
                    r"""\bref\((?P<quote>['"])(?P<xmlid>.+?)(?P=quote)\)""",
                    lambda m: str(self.env.ref(m["xmlid"]).id),
                    formula,
                )
            elif engine == "account_codes" and report_line.account_codes_formula:
                subformula, formula = None, report_line.account_codes_formula
            elif engine == "aggregation" and report_line.aggregation_formula:
                subformula, formula = None, report_line.aggregation_formula
            elif engine == "external" and report_line.external_formula:
                subformula, formula = "editable", "most_recent"
                if report_line.external_formula == "percentage":
                    subformula = "editable;rounding=0"
                elif report_line.external_formula == "monetary":
                    formula = "sum"
            elif engine == "tax_tags" and report_line.tax_tags_formula:
                subformula, formula = None, report_line.tax_tags_formula
            else:
                report_line.expression_ids.filtered(
                    lambda exp: (
                        exp.engine == engine
                        and exp.label == "balance"
                        and not xml_ids.get(exp.id)
                    )
                ).unlink()
                continue

            vals = {
                "report_line_id": report_line.id,
                "label": "balance",
                "engine": engine,
                "formula": formula,
                "subformula": subformula,
                "figure_type": (
                    report_line.external_formula if engine == "external" else False
                ),
            }

            balance_expression = report_line.expression_ids.filtered(
                lambda exp: exp.label == "balance"
            )
            if not balance_expression:
                vals_list.append(vals)
            elif xml_ids.get(balance_expression.id):
                balance_expression.unlink()
                vals_list.append(vals)
            else:
                balance_expression.write(vals)

        _debug.pipeline(
            "report_expressions_synced",
            engine=engine,
            lines=self,
            created=len(vals_list),
        )
        if vals_list:
            self.env["account.report.expression"].create(vals_list)

    @api.ondelete(at_uninstall=False)
    @_debug.perf.timed
    def _unlink_child_expressions(self):
        _debug.lifecycle("_unlink_child_expressions", records=self)
        self.expression_ids.unlink()
