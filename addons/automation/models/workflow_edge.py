from odoo import _, api, exceptions, fields, models
from odoo.tools.date_utils import time_unit_selection

CONDITION_SELECTION = [
    ("on_success", "On Success"),
    ("on_error", "On Error"),
    ("always", "Always"),
    ("expression", "Expression"),
    ("event", "On Event"),
    ("no_event", "Without Event"),
]
EVENT_CONDITIONS = ("event", "no_event")
EDGE_DELAY_UNITS = time_unit_selection("minute", "hour", "day", "week", "month")

SETTLED_STATES = ("done", "error", "cancel", "skipped")


class WorkflowEdge(models.Model):
    _name = "workflow.edge"
    _description = "Workflow DAG Edge"
    _order = "automation_rule_id, id"

    source_node_id = fields.Many2one(
        comodel_name="ir.actions.server",
        string="Source",
        index=True,
        required=True,
        ondelete="cascade",
    )
    target_node_id = fields.Many2one(
        comodel_name="ir.actions.server",
        string="Target",
        index=True,
        required=True,
        ondelete="cascade",
    )
    automation_rule_id = fields.Many2one(  # noqa: E8529  One2many inverse, cascading FK
        comodel_name="automation.rule",
        related="source_node_id.automation_rule_id",
        string="Automation Rule",
        store=True,
        index=True,
        ondelete="cascade",
    )

    condition = fields.Selection(
        selection=CONDITION_SELECTION,
        default="on_success",
        required=True,
        help="When this edge lets the target advance:\n"
        "- On Success: the source completed\n"
        "- On Error: the source failed\n"
        "- Always: the source settled, however it settled\n"
        "- Expression: the source settled and the expression is truthy\n"
        "- On Event: the source received the event\n"
        "- Without Event: the source did not receive the event within the delay",
    )
    condition_expr = fields.Char(
        string="Expression",
        help="Python expression evaluated against the runtime; "
        "required when the condition is Expression",
    )
    event_code = fields.Char(
        string="Event",
        help="The event this edge waits for, or waits out; "
        "required when the condition is On Event or Without Event",
    )
    delay = fields.Integer(
        default=0,
        help="How long after its condition holds the target becomes ready. "
        "For Without Event, how long the source waits for the event.",
    )
    delay_unit = fields.Selection(
        selection=EDGE_DELAY_UNITS,
        default="hour",
        required=True,
    )
    label = fields.Char(help="Shown on the edge when the workflow is drawn")

    display_name = fields.Char(compute="_compute_display_name")

    _edge_uniq = models.Constraint(
        "UNIQUE(source_node_id, target_node_id)",
        "These two steps are already connected.",
    )

    @api.constrains("source_node_id", "target_node_id")
    def _check_same_automation(self):
        for edge in self:
            source_rule = edge.source_node_id.automation_rule_id
            target_rule = edge.target_node_id.automation_rule_id
            if source_rule != target_rule:
                raise exceptions.ValidationError(
                    _(
                        "Step '%(target)s' cannot depend on '%(source)s': they "
                        "belong to different automations.\n\n"
                        "Dependencies only order the steps of one automation, so "
                        "a step from another rule can never complete within this "
                        "run.",
                        source=edge.source_node_id.name,
                        target=edge.target_node_id.name,
                    ),
                )

    @api.constrains("source_node_id", "target_node_id")
    def _check_no_cycle(self):
        for edge in self:
            if edge.source_node_id == edge.target_node_id:
                raise exceptions.ValidationError(
                    _(
                        "Action '%(action)s' cannot depend on itself.",
                        action=edge.target_node_id.name,
                    )
                )
            target = edge.target_node_id
            seen: set[int] = set()
            frontier = target._get_predecessors()
            while frontier:
                if target.id in frontier.ids:
                    raise exceptions.ValidationError(
                        _(
                            "Circular dependency detected: action '%(action)s' "
                            "would create a cycle in the workflow DAG.",
                            action=target.name,
                        )
                    )
                seen.update(frontier.ids)
                frontier = frontier._get_predecessors().filtered(
                    lambda node: node.id not in seen,  # noqa: B023 - filtered() evaluates the lambda immediately, within this same loop iteration
                )

    @api.constrains("condition", "delay", "source_node_id")
    def _check_condition_is_honoured(self):
        for edge in self:
            rule = edge.automation_rule_id
            if (edge.condition == "on_success" and not edge.delay) or not rule:
                continue
            if not rule._is_runtime_backed():
                raise exceptions.ValidationError(
                    _(
                        "'%(source)s' -> '%(target)s' is conditional, but "
                        "automation '%(name)s' does not record its runs, so the "
                        "condition would be ignored.\n\n"
                        "Switch on 'Record Every Run' on the automation, or make "
                        "this connection unconditional.",
                        source=edge.source_node_id.name,
                        target=edge.target_node_id.name,
                        name=rule.name,
                    ),
                )

    @api.constrains("condition", "condition_expr")
    def _check_condition_expr(self):
        for edge in self:
            if (
                edge.condition == "expression"
                and not (edge.condition_expr or "").strip()
            ):
                raise exceptions.ValidationError(
                    _(
                        "Edge '%(source)s' -> '%(target)s' is conditional on an "
                        "expression but carries none, so the target could never "
                        "become ready.",
                        source=edge.source_node_id.name,
                        target=edge.target_node_id.name,
                    ),
                )

    @api.constrains("condition", "event_code", "delay")
    def _check_timing(self):
        for edge in self:
            if edge.delay < 0:
                raise exceptions.ValidationError(
                    _(
                        "Edge '%(source)s' -> '%(target)s' has a negative delay.",
                        source=edge.source_node_id.name,
                        target=edge.target_node_id.name,
                    ),
                )
            if (
                edge.condition in EVENT_CONDITIONS
                and not (edge.event_code or "").strip()
            ):
                raise exceptions.ValidationError(
                    _(
                        "Edge '%(source)s' -> '%(target)s' depends on an event but "
                        "names none, so no event could ever settle it.",
                        source=edge.source_node_id.name,
                        target=edge.target_node_id.name,
                    ),
                )

    def _runtime_copy_vals(self):
        self.check_singleton()
        return {
            "condition": self.condition,
            "condition_expr": self.condition_expr,
            "event_code": self.event_code,
            "delay": self.delay,
            "delay_unit": self.delay_unit,
        }

    @api.depends("source_node_id", "target_node_id", "condition", "label")
    def _compute_display_name(self):
        conditions = dict(self._fields["condition"]._description_selection(self.env))
        for edge in self:
            edge.display_name = self.env._(
                "%(from_node)s → %(to_node)s (%(condition)s)",
                from_node=edge.source_node_id.name or "?",
                to_node=edge.target_node_id.name or "?",
                condition=edge.label or conditions.get(edge.condition, edge.condition),
            )
