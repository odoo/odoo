import logging
import math

from odoo import api, fields, models
from odoo.exceptions import ValidationError

from . import approval_trace as trace

_logger = logging.getLogger(__name__)


class ApprovalRule(models.Model):
    _name = "approval.rule"
    _description = "Conditional Approval Rule"
    _inherit = ["mixin.approval.threshold", "mixin.approval.domain"]
    _order = "category_id, sequence, id"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)
    category_id = fields.Many2one(
        comodel_name="approval.category",
        index=True,
        required=True,
        ondelete="cascade",
    )

    condition_type = fields.Selection(
        selection=[
            ("threshold", "Numeric threshold"),
            ("domain", "Source document domain"),
            ("field_selection", "Source document field"),
        ],
        default="threshold",
        required=True,
        help="""What this rule tests:

        • Numeric threshold: a normalized figure on the request itself
          (amount, quantity, date range, priority). Amounts are converted into
          the rule's currency before comparison, and overlapping auto-approve
          and auto-refuse bands are rejected outright.
        • Source document domain: a domain evaluated against the document the
          request was raised for.
        • Source document field: a field on the source document equals a
          value.

        Only 'Numeric threshold' can be range-checked. The other two read the
        source document, so a request with no source document, or one of
        another model, never matches them.""",
    )
    condition_field = fields.Selection(
        help="Request field to evaluate. Required for the 'Numeric threshold' "
        "condition type and ignored by the others."
    )
    operator = fields.Selection(
        help="Required for the 'Numeric threshold' condition type and ignored "
        "by the others."
    )
    subject_model_id = fields.Many2one(
        comodel_name="ir.model",
        string="Source Model",
        ondelete="cascade",
        help="Model whose records this rule reads. Required for every "
        "condition type except 'Numeric threshold', which reads the request. "
        "A request whose source document is another model never matches.",
    )
    subject_model_name = fields.Char(
        related="subject_model_id.model",
        string="Source Model Name",
        help="The source model's technical name, which the condition's domain editor "
        "reads its fields from.",
    )
    subject_domain = fields.Char(
        string="Source Domain",
        help="Domain evaluated against the source document.",
    )
    subject_field = fields.Char(
        string="Source Field",
        help="Field on the source model to compare.",
    )
    subject_value = fields.Char(
        string="Source Value",
        help="Value the source field must equal. Compared as text against the "
        "field's raw value, so a Selection is matched on its stored key and a "
        "Many2one on its id.",
    )
    action_type = fields.Selection(
        selection=[
            ("auto_approve", "Auto-Approve"),
            ("auto_refuse", "Auto-Refuse"),
            ("condition", "Step Condition"),
        ],
        default="condition",
        required=True,
        help="Action to take when condition matches:\n"
        "• Auto-Approve: skip approval entirely (logged in audit trail)\n"
        "• Auto-Refuse: automatically refuse the request\n"
        "• Step Condition: nothing by itself; a step of the category applies "
        "when it matches, or unless it does",
    )

    _name_category_uniq = models.Constraint(
        "unique nulls not distinct (name, category_id, company_id)",
        "Rule name must be unique per category and company.",
    )

    def _get_reading_steps(self):
        steps = (
            self.env["approval.category.step"]
            .with_context(active_test=False)
            .search(
                [
                    "|",
                    ("when_rule_ids", "in", self.ids),
                    ("unless_rule_ids", "in", self.ids),
                ]
            )
        )
        trace.RULES.event("rules_read_by_steps", rules=self.ids, steps=steps.ids)
        return steps

    def write(self, vals):
        if ("active" in vals and not vals["active"]) or (
            "action_type" in vals and vals["action_type"] != "condition"
        ):
            trace.RULES.event(
                "rule_retirement_checked",
                rules=self.ids,
                active=vals.get("active"),
                action=vals.get("action_type"),
            )
            self._check_no_step_reads_it()
        return super().write(vals)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_read_by_a_step(self) -> None:
        self._check_no_step_reads_it()

    def _check_no_step_reads_it(self) -> None:
        steps = self._get_reading_steps()
        if steps:
            trace.REFUSAL.event("rule_read_by_steps", rules=self.ids, steps=steps.ids)
            raise ValidationError(
                self.env._(
                    "Steps %(steps)s apply by these rules, so the rules must stay "
                    "active step conditions: change the steps first.",
                    steps=", ".join(steps.mapped("name")),
                )
            )

    @api.depends("category_id.company_id")
    def _compute_company_id(self) -> None:
        for rule in self:
            rule.company_id = rule.category_id.company_id

    @api.constrains("company_id", "category_id")
    def _check_company_matches_category(self):
        for rule in self:
            category_company = rule.category_id.company_id
            if (
                rule.company_id
                and category_company
                and rule.company_id != category_company
            ):
                trace.REFUSAL.event(
                    "rule_company_not_category_company",
                    rule=rule.id,
                    company=rule.company_id.id,
                    category_company=category_company.id,
                )
                raise ValidationError(
                    self.env._(
                        "Rule '%(rule)s' is scoped to %(company)s but its "
                        "category '%(category)s' belongs to %(other)s, so it "
                        "could never apply. Leave the company empty or set it "
                        "to the category's.",
                        rule=rule.name,
                        company=rule.company_id.name,
                        category=rule.category_id.name,
                        other=category_company.name,
                    ),
                )

    @api.constrains("operator", "threshold", "threshold_max")
    def _check_range_bounds(self):
        for rule in self:
            if rule.condition_type != "threshold" or rule.operator != "between":
                continue
            if rule.threshold_max and rule.threshold_max <= rule.threshold:
                trace.REFUSAL.event(
                    "rule_range_inverted",
                    rule=rule.id,
                    threshold=rule.threshold,
                    threshold_max=rule.threshold_max,
                )
                raise ValidationError(
                    self.env._(
                        "The upper bound must be greater than the lower one "
                        "(or 0 for unlimited).",
                    ),
                )

    @api.constrains(
        "category_id",
        "company_id",
        "condition_field",
        "operator",
        "threshold",
        "action_type",
        "active",
    )
    def _check_auto_action_conflict(self):
        auto_types = ("auto_approve", "auto_refuse")
        stored_peers = (
            self.sudo().search(
                [
                    ("category_id", "in", self.category_id.ids),
                    (
                        "condition_field",
                        "in",
                        list(set(self.mapped("condition_field"))),
                    ),
                    ("action_type", "in", auto_types),
                    ("active", "=", True),
                ],
            )
            if self.category_id
            else self.browse()
        )
        for rule in self:
            if rule.action_type not in auto_types or not rule.active:
                continue
            peers = (stored_peers | self).filtered(
                lambda r, cur=rule: (
                    r.id != cur.id
                    and r.category_id == cur.category_id
                    and r.condition_field == cur.condition_field
                    and r.action_type in auto_types
                    and r.active
                ),
            )
            for other in peers:
                if other.action_type == rule.action_type:
                    continue
                if (
                    rule.company_id
                    and other.company_id
                    and rule.company_id != other.company_id
                ):
                    continue
                if rule._condition_overlaps(other):
                    trace.REFUSAL.event(
                        "auto_action_bands_overlap",
                        rule=rule.id,
                        other=other.id,
                        field=rule.condition_field,
                        actions=[rule.action_type, other.action_type],
                    )
                    raise ValidationError(
                        self.env._(
                            "Rule '%(rule)s' (auto-%(rule_action)s) and "
                            "'%(other)s' (auto-%(other_action)s) can both "
                            "match the same %(field)s value — one would "
                            "silently override the other depending on "
                            "sequence. Narrow the thresholds so their "
                            "ranges don't overlap.",
                            rule=rule.name,
                            rule_action=rule.action_type.removeprefix("auto_"),
                            other=other.name,
                            other_action=other.action_type.removeprefix("auto_"),
                            field=rule.condition_field,
                        ),
                    )

    @api.constrains("threshold", "condition_field")
    def _check_threshold(self):
        for rule in self:
            if rule.condition_type != "threshold":
                continue
            if rule.condition_field == "priority" and rule.threshold not in (
                0,
                1,
                2,
                3,
            ):
                trace.REFUSAL.event(
                    "priority_threshold_out_of_range",
                    rule=rule.id,
                    threshold=rule.threshold,
                )
                raise ValidationError(
                    self.env._(
                        "Priority threshold must be 0 (Low), 1 (Normal), "
                        "2 (High), or 3 (Urgent)."
                    )
                )

    @api.constrains(
        "condition_type",
        "condition_field",
        "operator",
        "subject_model_id",
        "subject_domain",
        "subject_field",
        "subject_value",
    )
    def _check_condition_shape(self):
        for rule in self:
            if rule.condition_type == "threshold":
                if not rule.condition_field or not rule.operator:
                    trace.REFUSAL.event(
                        "threshold_rule_incomplete",
                        rule=rule.id,
                        field=rule.condition_field,
                        operator=rule.operator,
                    )
                    raise ValidationError(
                        self.env._(
                            "Rule %(name)s compares a numeric threshold, so it "
                            "needs both a request field and a comparison.",
                            name=rule.name,
                        ),
                    )
                continue

            if not rule.subject_model_id:
                trace.REFUSAL.event(
                    "subject_rule_without_model",
                    rule=rule.id,
                    kind=rule.condition_type,
                )
                raise ValidationError(
                    self.env._(
                        "Rule %(name)s reads the source document, so it needs "
                        "a source model. Without one it could never match.",
                        name=rule.name,
                    ),
                )
            model = self.env.get(rule.subject_model_id.model)
            if model is None:
                trace.REFUSAL.event(
                    "subject_model_not_in_registry",
                    rule=rule.id,
                    model=rule.subject_model_id.model,
                )
                raise ValidationError(
                    self.env._(
                        "Rule %(name)s names the model %(model)s, which is not "
                        "in the registry.",
                        name=rule.name,
                        model=rule.subject_model_id.model,
                    ),
                )
            if rule.condition_type == "domain":
                rule._check_subject_domain(model)
            else:
                rule._check_subject_field(model)

    def _domain_source_field(self) -> str:
        return "subject_domain"

    def _check_subject_domain(self, model) -> None:
        self.check_singleton()
        self._check_domain_against_model(model)

    def _check_subject_field(self, model) -> None:
        self.check_singleton()
        if not self.subject_field:
            trace.REFUSAL.event("subject_rule_without_field", rule=self.id)
            raise ValidationError(
                self.env._(
                    "Rule %(name)s compares a source field, so it needs a field name.",
                    name=self.name,
                ),
            )
        self._check_field_path(model, self.subject_field)

    _CONDITION_FIELD_DEPENDS = {
        "amount": ("amount", "currency_id", "date"),
        "quantity": ("quantity",),
        "date_range_days": ("date_start", "date_end"),
        "priority": ("priority",),
    }

    @api.model
    def _get_fields_request_trigger(self) -> frozenset[str]:
        return frozenset(
            field
            for depends in self._CONDITION_FIELD_DEPENDS.values()
            for field in depends
        )

    def _evaluate(self, request) -> bool:
        self.check_singleton()
        match self.condition_type:
            case "domain":
                matches = self._evaluate_domain(request)
                measured = None
            case "field_selection":
                matches = self._evaluate_field_selection(request)
                measured = None
            case _:
                measured = self._get_field_value(request)
                matches = (
                    False
                    if measured is None
                    else self._compare(measured, self.threshold)
                )
        trace.RULES.event(
            "evaluated",
            rule=self.id,
            request=request.id,
            kind=self.condition_type,
            field=self.condition_field,
            operator=self.operator,
            value=measured,
            threshold=self.threshold,
            threshold_max=self.threshold_max or None,
            matches=matches,
        )
        return matches

    def _get_subject(self, request):
        self.check_singleton()
        if not self.subject_model_id:
            return False
        document = request.get_source_document()
        if not document or document._name != self.subject_model_id.model:
            trace.RULES.event(
                "subject_mismatch",
                rule=self.id,
                request=request.id,
                wanted=self.subject_model_id.model,
                got=document._name if document else None,
            )
            return False
        return document.exists()

    def _evaluate_domain(self, request) -> bool:
        subject = self._get_subject(request)
        if not subject:
            trace.RULES.event(
                "domain_not_evaluated",
                rule=self.id,
                request=request.id,
                why="no_subject",
            )
            return False
        domain = self._parse_domain_or_warn()
        if domain is None:
            trace.RULES.event(
                "domain_not_evaluated",
                rule=self.id,
                request=request.id,
                why="unparseable",
            )
            return False
        matched = bool(subject.filtered_domain(domain))
        trace.RULES.event(
            "domain_evaluated",
            rule=self.id,
            request=request.id,
            subject=subject,
            matched=matched,
        )
        return matched

    def _evaluate_field_selection(self, request) -> bool:
        subject = self._get_subject(request)
        if not subject or self.subject_field not in subject._fields:
            trace.RULES.event(
                "field_selection_not_evaluated",
                rule=self.id,
                request=request.id,
                field=self.subject_field,
                why="no_subject" if not subject else "field_absent",
            )
            return False
        value = subject[self.subject_field]
        if hasattr(value, "ids"):
            value = value.id
        matched = str(value) == (self.subject_value or "")
        trace.RULES.event(
            "field_selection_evaluated",
            rule=self.id,
            request=request.id,
            field=self.subject_field,
            value=str(value),
            wanted=self.subject_value or "",
            matched=matched,
        )
        return matched

    def _condition_bounds(self) -> tuple[float, bool, float, bool] | None:
        self.check_singleton()
        if self.condition_type != "threshold":
            return None
        t = self.threshold
        if self.operator == "gt":
            return (t, False, math.inf, True)
        if self.operator == "gte":
            return (t, True, math.inf, True)
        if self.operator == "lt":
            return (-math.inf, True, t, False)
        if self.operator == "lte":
            return (-math.inf, True, t, True)
        if self.operator == "eq":
            return (t, True, t, True)
        if self.operator == "between":
            return (t, True, self.threshold_max or math.inf, False)
        return None

    def _condition_overlaps(self, other) -> bool:
        self.check_singleton()
        other.check_singleton()
        bounds_a = self._condition_bounds()
        bounds_b = other._condition_bounds()
        if bounds_a is None or bounds_b is None:
            trace.RULES.event(
                "overlap_assumed",
                rule=self.id,
                other=other.id,
                unbounded=self.id if bounds_a is None else other.id,
            )
            return True
        overlaps = self._intervals_overlap(bounds_a, bounds_b)
        trace.RULES.event(
            "overlap_checked",
            rule=self.id,
            other=other.id,
            bounds=str(bounds_a),
            other_bounds=str(bounds_b),
            overlaps=overlaps,
        )
        return overlaps
