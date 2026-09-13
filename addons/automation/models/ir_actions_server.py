import logging

from odoo import _, api, exceptions, fields, models
from odoo.fields import Domain
from odoo.tools.date_utils import get_timedelta, time_unit_selection
from odoo.tools.json import scriptsafe as json_scriptsafe

from ._canvas import NODE_SIZE_MAX, NODE_SIZE_MIN

_logger = logging.getLogger(__name__)


class IrActionsServer(models.Model):
    _inherit = "ir.actions.server"

    usage = fields.Selection(
        selection_add=[("automation", "Automation Rule")],
        ondelete={"automation": "cascade"},
    )
    automation_rule_id = fields.Many2one(
        comodel_name="automation.rule",
        index="btree_not_null",
        ondelete="cascade",
    )

    edge_in_ids = fields.One2many(
        comodel_name="workflow.edge",
        inverse_name="target_node_id",
        string="Incoming Edges",
        copy=False,
        help="Edges that must be satisfied before this action can execute",
    )
    edge_out_ids = fields.One2many(
        comodel_name="workflow.edge",
        inverse_name="source_node_id",
        string="Outgoing Edges",
        copy=False,
        help="Edges this action's outcome can satisfy",
    )

    node_type = fields.Selection(
        selection=[
            ("action", "Action"),
            ("wait", "Wait"),
            ("approval", "Approval"),
            ("subflow", "Sub-workflow"),
        ],
        default="action",
        required=True,
        help="What this step does when the workflow reaches it. An Action runs "
        "the server action; a Wait pauses the run and resumes it later.",
    )
    wait_delay = fields.Integer(
        string="Wait For",
        default=1,
        help="How long a Wait step pauses the run before its successors advance",
    )
    wait_unit = fields.Selection(
        selection=time_unit_selection("minute", "hour", "day"),
        default="hour",
        required=True,
    )

    start_delay = fields.Integer(
        default=0,
        help="For a step no edge leads to: how long after its run starts it "
        "becomes ready. Ignored on a step with predecessors, whose edges carry "
        "their own delays.",
    )
    start_delay_unit = fields.Selection(
        selection=time_unit_selection("minute", "hour", "day", "week", "month"),
        default="hour",
        required=True,
    )
    validity_delay = fields.Integer(
        string="Valid For",
        default=0,
        help="How long after the step becomes ready it may still run. A step "
        "reached later is skipped instead. Zero means it never expires.",
    )
    validity_unit = fields.Selection(
        selection=time_unit_selection("minute", "hour", "day", "week", "month"),
        default="hour",
        required=True,
    )

    pos_x = fields.Integer(
        string="Canvas X",
        help="Horizontal position of this node on the workflow canvas",
    )
    pos_y = fields.Integer(
        string="Canvas Y",
        help="Vertical position of this node on the workflow canvas",
    )
    pos_width = fields.Integer(
        string="Canvas Width",
        help="Width of this node on the workflow canvas; 0 means the default",
    )
    pos_height = fields.Integer(
        string="Canvas Height",
        help="Height of this node on the workflow canvas; 0 means the default",
    )

    approval_user_ids = fields.Many2many(
        comodel_name="res.users",
        relation="ir_actions_server_approval_user_rel",
        string="Approvers",
        help="Everyone who must mark their activity done before an Approval "
        "step lets the workflow continue",
    )
    approval_note = fields.Char(
        string="Ask For",
        help="Shown on the activity each approver receives",
    )

    subflow_automation_id = fields.Many2one(
        comodel_name="automation.rule",
        string="Sub-workflow",
        help="The automation a Sub-workflow step runs and waits for",
    )

    @api.constrains("node_type", "subflow_automation_id", "automation_rule_id")
    def _check_subflow(self):
        for action in self.filtered(lambda node: node.node_type == "subflow"):
            target = action.subflow_automation_id
            if not target:
                raise exceptions.ValidationError(
                    _(
                        "Step '%(action)s' is a sub-workflow but names no "
                        "automation to run.",
                        action=action.name,
                    )
                )
            owner = action.automation_rule_id
            seen = self.env["automation.rule"]
            frontier = target
            while frontier:
                if frontier & owner:
                    raise exceptions.ValidationError(
                        _(
                            "Step '%(action)s' would run automation '%(target)s', "
                            "which reaches back to '%(owner)s' -- a sub-workflow "
                            "cannot contain the workflow that runs it.",
                            action=action.name,
                            target=target.name,
                            owner=action.automation_rule_id.name,
                        )
                    )
                seen |= frontier
                frontier = frontier.action_server_ids.subflow_automation_id - seen

    @api.constrains("node_type", "approval_user_ids")
    def _check_approval_has_approvers(self):
        for action in self:
            if action.node_type == "approval" and not action.approval_user_ids:
                raise exceptions.ValidationError(
                    _(
                        "Step '%(action)s' asks for approval but names nobody to "
                        "give it, so the workflow would wait forever.",
                        action=action.name,
                    )
                )

    @api.constrains("pos_width", "pos_height")
    def _check_canvas_size(self):
        for action in self:
            sizes = (("width", action.pos_width), ("height", action.pos_height))
            for axis, value in sizes:
                if not value:
                    continue
                if not NODE_SIZE_MIN[axis] <= value <= NODE_SIZE_MAX[axis]:
                    raise exceptions.ValidationError(
                        _(
                            "The canvas %(axis)s of step '%(step)s' is %(value)s, "
                            "outside the %(minimum)s-%(maximum)s the canvas draws.\n\n"
                            "Use 0 to leave the step at the default size.",
                            axis=axis,
                            step=action.name or "?",
                            value=value,
                            minimum=NODE_SIZE_MIN[axis],
                            maximum=NODE_SIZE_MAX[axis],
                        )
                    )

    @api.constrains("node_type", "wait_delay")
    def _check_wait_delay(self):
        for action in self:
            if action.node_type == "wait" and action.wait_delay <= 0:
                raise exceptions.ValidationError(
                    _(
                        "Step '%(action)s' waits for %(delay)s %(unit)s, which is "
                        "not a wait. Give it a positive duration.",
                        action=action.name,
                        delay=action.wait_delay,
                        unit=action.wait_unit,
                    )
                )

    @api.constrains("validity_delay", "start_delay")
    def _check_validity_delay(self):
        for action in self:
            if action.start_delay < 0:
                raise exceptions.ValidationError(
                    _(
                        "Step '%(action)s' has a negative start delay.",
                        action=action.name,
                    ),
                )
            if action.validity_delay < 0:
                raise exceptions.ValidationError(
                    _(
                        "Step '%(action)s' has a negative validity.",
                        action=action.name,
                    ),
                )

    def _get_start_delta(self):
        self.check_singleton()
        return get_timedelta(self.start_delay, self.start_delay_unit)

    def _get_validity_delta(self):
        self.check_singleton()
        return get_timedelta(self.validity_delay, self.validity_unit)

    def _workflow_step_detail(self):
        return ""

    def _execute_runtime_lines(self, lines):
        self.check_singleton()
        for line in lines:
            line.action_execute()

    def _get_wait_delta(self):
        self.check_singleton()
        return get_timedelta(self.wait_delay, self.wait_unit)

    def _get_predecessors(self):
        return self.edge_in_ids.source_node_id

    def _get_successors(self):
        return self.edge_out_ids.target_node_id

    def _sorted_by_dependency(self):
        ordered_by_sequence = self.sorted("sequence")

        edges = {
            action.id: set(action._get_predecessors().ids) & set(self.ids)
            for action in ordered_by_sequence
        }
        if not any(edges.values()):
            return ordered_by_sequence

        remaining = list(ordered_by_sequence)
        settled: set[int] = set()
        ordered = self.browse()
        while remaining:
            ready = [a for a in remaining if edges[a.id] <= settled]
            if not ready:
                return ordered + self.browse([a.id for a in remaining])
            ordered += self.browse([a.id for a in ready])
            settled.update(a.id for a in ready)
            ready_ids = {a.id for a in ready}
            remaining = [a for a in remaining if a.id not in ready_ids]
        return ordered

    @api.depends("usage")
    def _compute_available_model_ids(self):
        super()._compute_available_model_ids()
        rule_based = self.filtered(lambda action: action.usage == "automation")
        for action in rule_based:
            rule_model = action.automation_rule_id.model_id
            action.available_model_ids = (
                rule_model.ids if rule_model in action.available_model_ids else []
            )

    def action_view_automation(self):
        return {
            "type": "ir.actions.act_window",
            "target": "current",
            "views": [[False, "form"]],
            "res_model": self.automation_rule_id._name,
            "res_id": self.automation_rule_id.id,
        }

    def _get_domain_children(self):
        return super()._get_domain_children() & Domain("automation_rule_id", "=", False)

    def _prepare_eval_context(self, action):
        eval_context = super()._prepare_eval_context(action)
        if action.state == "code":
            eval_context["json"] = json_scriptsafe
            line_id = self.env.context.get("runtime_line_id")
            if line_id:
                line = self.env["automation.runtime.line"].browse(line_id)
                eval_context["runtime_line"] = line
                eval_context["runtime"] = line.runtime_id
            elif runtime_id := self.env.context.get("runtime_id"):
                eval_context["runtime"] = self.env["automation.runtime"].browse(
                    runtime_id,
                )
        return eval_context

    def _get_warning_messages(self):
        self.check_singleton()
        warnings = super()._get_warning_messages()

        if (
            self.automation_rule_id
            and self.model_id != self.automation_rule_id.model_id
        ):
            warnings.append(
                _(
                    "Model of action %(action_name)s should match the one from automated rule %(rule_name)s.",
                    action_name=self.name,
                    rule_name=self.automation_rule_id.name,
                ),
            )

        return warnings

    @api.model
    def _get_fields_warning_depends(self):
        return super()._get_fields_warning_depends() + [
            "model_id",
            "automation_rule_id",
        ]
