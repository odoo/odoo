from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError

#: Operators allowed in the left-hand comparison of a status rule.
OPERATORS = [
    (">", "Greater than"),
    (">=", "Greater than or equal"),
    ("<", "Less than"),
    ("<=", "Less than or equal"),
    ("==", "Equal to"),
    ("!=", "Not equal to"),
]

#: Right-hand operand of a status rule.
COMPARE_TYPES = [
    ("constant", "Constant value"),
    ("goal", "Goal"),
    ("percent_of_goal", "Percent of goal"),
    ("widget", "Another widget"),
    ("prev", "Previous period"),
    ("yty", "Same period last year"),
    ("mtm", "Previous month"),
    ("qtq", "Previous quarter"),
]

#: Status colours shared with the KPI baseline.
STATUSES = [
    ("red", "Red"),
    ("yellow", "Yellow"),
    ("green", "Green"),
    ("grey", "Grey"),
]


class Od19DashboardWidgetRule(models.Model):
    """One row of a widget status table.

    The left-hand side of every comparison is always the value of the widget
    that owns the rule; the right-hand side is selected through
    ``compare_type``. Rules are evaluated top to bottom and the first match
    wins, which is why the model is ordered by ``sequence`` then ``id``.
    """

    _name = "od19.dashboard.widget.rule"
    _description = "Dashboard Widget Status Rule"
    _order = "sequence, id"

    widget_id = fields.Many2one(
        "od19.dashboard.widget",
        required=True,
        ondelete="cascade",
        index=True,
    )
    sequence = fields.Integer(default=10)
    name = fields.Char(help="Short label shown in the rule table, e.g. 'Below 20% of goal'.")
    active = fields.Boolean(default=True)

    operator = fields.Selection(selection=OPERATORS, required=True, default="<=")
    compare_type = fields.Selection(
        selection=COMPARE_TYPES,
        required=True,
        default="constant",
        help="What the widget value is compared with. 'Previous month' and "
             "'Previous quarter' shift the whole period window back by one month "
             "or three months, keeping its length.",
    )
    compare_value = fields.Float(help="Used when the compare type is a constant value.")
    compare_percent = fields.Float(
        help="Used with 'Percent of goal': 80 means 80% of the widget goal.",
    )
    compare_widget_id = fields.Many2one(
        "od19.dashboard.widget",
        ondelete="cascade",
        string="Compare with",
    )
    status = fields.Selection(selection=STATUSES, required=True, default="red")
    alert_message = fields.Char(
        help="Message shown on the widget when this rule matches a bucket or the widget value.",
    )

    @api.constrains("widget_id", "compare_widget_id")
    def _check_compare_widget(self):
        """Refuse a self reference; allow a widget of another dashboard.

        Comparing with a widget of another dashboard is a cross dashboard
        value (spec phase 2, section 6). The two dashboards must belong to the
        same company and the user must be able to read the target, otherwise
        the comparison could never be resolved.
        """
        for rule in self:
            if not rule.compare_widget_id or not rule.widget_id:
                continue
            label = rule.name or rule.id
            if rule.compare_widget_id == rule.widget_id:
                raise ValidationError(
                    _("A status rule cannot compare a widget with itself (rule: %s).") % label
                )
            target = rule.compare_widget_id
            source = rule.widget_id
            if target.dashboard_id.company_id != source.dashboard_id.company_id:
                raise ValidationError(
                    _("A status rule can only compare widgets of the same company (rule: %s).")
                    % label
                )
            try:
                target.check_access("read")
                target.dashboard_id.check_access("read")
            except AccessError as error:
                raise ValidationError(
                    _("You cannot read the widget '%(widget)s' this rule compares with (rule: %(rule)s).")
                    % {"widget": target.display_name, "rule": label}
                ) from error

    @api.constrains("compare_type", "compare_widget_id", "compare_percent")
    def _check_compare_target(self):
        for rule in self:
            label = rule.name or rule.id
            if rule.compare_type == "widget" and not rule.compare_widget_id:
                raise ValidationError(
                    _("Choose the widget to compare with (rule: %s).") % label
                )
            if rule.compare_type == "percent_of_goal" and not rule.compare_percent:
                raise ValidationError(
                    _("Set the percentage of the goal to compare with (rule: %s).") % label
                )

    @api.constrains("widget_id", "compare_widget_id", "active")
    def _check_dashboard_dependency_cycle(self):
        """Refuse a rule that closes a loop in the widget graph (spec section 11).

        Writing a rule directly leaves the owning widget untouched, so the
        widget constraint never sees the new edge. Checking here keeps the
        invariant no matter which model the write goes through.
        """
        for rule in self:
            dashboard = rule.widget_id.dashboard_id
            if dashboard:
                dashboard._check_no_cycle()

    def _to_values(self):
        """Return the rule as a plain dictionary for the builder and the tests."""
        self.ensure_one()
        return {
            "id": self.id,
            "name": self.name or "",
            "sequence": self.sequence,
            "active": self.active,
            "operator": self.operator,
            "compare_type": self.compare_type,
            "compare_value": self.compare_value,
            "compare_percent": self.compare_percent,
            "compare_widget_id": self.compare_widget_id.id,
            "status": self.status,
            "alert_message": self.alert_message or "",
        }

    def _compare_operand(self, context):
        """Return the right-hand value of the comparison.

        ``context`` is the operand dictionary built by the widget:
        ``{"value": float, "goal": float, "shifts": {shift: float},
        "widget_values": {widget_id: float}}``. Returns ``None`` when the
        operand cannot be resolved, in which case the rule does not match.
        """
        self.ensure_one()
        if self.compare_type == "constant":
            return self.compare_value
        if self.compare_type == "goal":
            return context.get("goal")
        if self.compare_type == "percent_of_goal":
            goal = context.get("goal")
            if not goal or not self.compare_percent:
                return None
            return goal * self.compare_percent / 100.0
        if self.compare_type == "widget":
            if not self.compare_widget_id:
                return None
            return context.get("widget_values", {}).get(self.compare_widget_id.id)
        shift = "previous" if self.compare_type == "prev" else self.compare_type
        return context.get("shifts", {}).get(shift)
