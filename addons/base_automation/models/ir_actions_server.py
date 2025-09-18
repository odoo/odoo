import logging

from odoo import _, api, fields, models
from odoo.fields import Domain
from odoo.tools.json import scriptsafe as json_scriptsafe

from .base_automation import get_webhook_request_payload

_logger = logging.getLogger(__name__)


class IrActionsServer(models.Model):
    _inherit = "ir.actions.server"

    # =========================================================================
    # Base Automation Integration
    # =========================================================================

    usage = fields.Selection(
        selection_add=[("base_automation", "Automation Rule")],
        ondelete={"base_automation": "cascade"},
    )
    base_automation_id = fields.Many2one(
        comodel_name="base.automation",
        string="Automation Rule",
        index="btree_not_null",
        ondelete="cascade",
    )

    # =========================================================================
    # DAG Dependency Fields
    # =========================================================================

    predecessor_ids = fields.Many2many(
        comodel_name="ir.actions.server",
        relation="ir_action_server_dependency_rel",
        column1="successor_id",
        column2="predecessor_id",
        string="Predecessors",
        help="Server actions that must complete before this action can execute",
    )
    successor_ids = fields.Many2many(
        comodel_name="ir.actions.server",
        relation="ir_action_server_dependency_rel",
        column1="predecessor_id",
        column2="successor_id",
        string="Successors",
        readonly=True,
        help="Server actions that depend on this action completing (computed from predecessors)",
    )
    action_state = fields.Selection(
        selection=[
            ("no", "Not Used"),
            ("waiting", "Waiting"),
            ("ready", "Ready"),
            ("in_progress", "In Progress"),
            ("done", "Done"),
            ("error", "Error"),
        ],
        string="Execution State",
        default="no",
        copy=False,
        index=True,
        help="Workflow execution state:\n"
        "- Waiting: Dependencies not satisfied\n"
        "- Ready: Can be executed now\n"
        "- In Progress: Currently executing\n"
        "- Done: Completed successfully\n"
        "- Error: Execution failed",
    )
    is_ready = fields.Boolean(
        string="Is Ready",
        compute="_compute_is_ready",
        store=True,
        help="True when all predecessors are done",
    )
    error_message = fields.Text(
        string="Error Message",
        help="Error details if action_state is 'error'",
    )

    # =========================================================================
    # CRUD Methods - State Management
    # =========================================================================

    @api.model_create_multi
    def create(self, vals_list):
        """Initialize action_state based on automation workflow context.

        - If action is part of a workflow DAG automation: set to 'waiting'
        - Otherwise: keep default 'no' (not part of workflow)
        """
        actions = super().create(vals_list)

        for action in actions:
            # Only set state if part of workflow automation
            if action.base_automation_id and action.base_automation_id.use_workflow_dag:
                # Set to waiting - will be marked ready by workflow reset
                if action.action_state == "no":
                    action.action_state = "waiting"

        return actions

    def write(self, vals):
        """Update action_state when automation workflow context changes.

        When base_automation_id changes or use_workflow_dag is toggled:
        - Added to workflow DAG: change 'no' → 'waiting'
        - Removed from workflow DAG: change workflow states → 'no'
        """
        result = super().write(vals)

        # Check if automation context changed
        if "base_automation_id" in vals:
            for action in self:
                if (
                    action.base_automation_id
                    and action.base_automation_id.use_workflow_dag
                ):
                    # Added to workflow automation
                    if action.action_state == "no":
                        action.action_state = "waiting"
                elif not action.base_automation_id:
                    # Removed from automation - reset to 'no'
                    if action.action_state in (
                        "waiting",
                        "ready",
                        "in_progress",
                        "done",
                        "error",
                    ):
                        action.action_state = "no"

        # Also check if automation's use_workflow_dag changed
        # This is handled by base.automation's onchange/write, but we catch edge cases
        for action in self:
            if action.base_automation_id:
                if action.base_automation_id.use_workflow_dag:
                    # Workflow enabled - ensure not 'no'
                    if action.action_state == "no":
                        action.action_state = "waiting"
                else:
                    # Workflow disabled - reset to 'no'
                    if action.action_state in (
                        "waiting",
                        "ready",
                        "in_progress",
                        "done",
                        "error",
                    ):
                        action.action_state = "no"

        return result

    # =========================================================================
    # Computed Fields
    # =========================================================================

    @api.depends("usage")
    def _compute_available_model_ids(self):
        """Stricter model limit: based on automation rule."""
        super()._compute_available_model_ids()
        rule_based = self.filtered(lambda action: action.usage == "base_automation")
        for action in rule_based:
            rule_model = action.base_automation_id.model_id
            action.available_model_ids = (
                rule_model.ids if rule_model in action.available_model_ids else []
            )

    @api.depends("predecessor_ids.action_state", "action_state")
    def _compute_is_ready(self):
        """Compute if action is ready based on predecessor states.

        An action is ready when:
        - It's in 'waiting' state
        - All predecessors are in 'done' state (or no predecessors)
        """
        for action in self:
            # Only compute for waiting actions
            if action.action_state != "waiting":
                action.is_ready = False
                continue

            # No predecessors = ready immediately
            if not action.predecessor_ids:
                action.is_ready = True
                continue

            # All predecessors must be done
            done_predecessors = action.predecessor_ids.filtered(
                lambda p: p.action_state == "done",
            )
            action.is_ready = len(done_predecessors) == len(action.predecessor_ids)

    # =========================================================================
    # State Management Actions
    # =========================================================================

    def action_mark_ready(self):
        """Mark action as ready to execute."""
        self.write({"action_state": "ready", "error_message": False})
        return True

    def action_mark_in_progress(self):
        """Mark action as in progress."""
        self.write({"action_state": "in_progress", "error_message": False})
        return True

    def action_mark_done(self):
        """Mark action as done and activate ready successors.

        This implements the core DAG resolution logic:
        1. Mark self as done
        2. Check each successor
        3. If successor's prerequisites are met, mark as ready
        """
        self.write({"action_state": "done", "error_message": False})

        # Activate successors that are now ready
        for successor in self.successor_ids:
            if successor.action_state == "waiting":
                # Trigger recomputation
                successor._compute_is_ready()

                if successor.is_ready:
                    successor.action_mark_ready()
                    _logger.info(
                        "Action '%s' (#%d) is now ready (all predecessors done)",
                        successor.name,
                        successor.id,
                    )

        return True

    def action_mark_error(self, error_msg=None):
        """Mark action as error."""
        self.write(
            {
                "action_state": "error",
                "error_message": error_msg or "Unknown error",
            },
        )
        return True

    def action_reset(self):
        """Reset action state to waiting."""
        self.write({"action_state": "waiting", "error_message": False})
        return True

    def action_open_automation(self):
        """Open the parent automation rule."""
        return {
            "type": "ir.actions.act_window",
            "target": "current",
            "views": [[False, "form"]],
            "res_model": self.base_automation_id._name,
            "res_id": self.base_automation_id.id,
        }

    # =========================================================================
    # Existing Methods (from standard base_automation)
    # =========================================================================

    def _get_children_domain(self):
        """Ensure automation actions can't be used as multi-action children."""
        return super()._get_children_domain() & Domain("base_automation_id", "=", False)

    def _get_eval_context(self, action=None):
        """Add webhook payload to eval context for code actions."""
        eval_context = super()._get_eval_context(action)
        if action and action.state == "code":
            eval_context["json"] = json_scriptsafe
            payload = get_webhook_request_payload()
            if payload:
                eval_context["payload"] = payload
        return eval_context

    def _get_warning_messages(self):
        """Validate action model matches automation rule model."""
        self.ensure_one()
        warnings = super()._get_warning_messages()

        if (
            self.base_automation_id
            and self.model_id != self.base_automation_id.model_id
        ):
            warnings.append(
                _(
                    "Model of action %(action_name)s should match the one from automated rule %(rule_name)s.",
                    action_name=self.name,
                    rule_name=self.base_automation_id.name,
                ),
            )

        return warnings

    @api.model
    def _warning_depends(self):
        """Add fields that trigger warning recomputation."""
        return super()._warning_depends() + [
            "model_id",
            "base_automation_id",
        ]
