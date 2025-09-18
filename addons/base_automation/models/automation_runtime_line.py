import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AutomationRuntimeLine(models.Model):
    """Execution tracking for individual workflow actions.

    Each line represents one execution of an ir.actions.server within
    a automation.runtime workflow instance.

    Tracks:
    - Which action was executed
    - Current state (waiting/ready/in_progress/done/cancel)
    - Results (created moves, payments, etc.)
    - Dependencies (DAG structure)
    """

    _name = "automation.runtime.line"
    _description = "Automation Runtime Action Line"
    _order = "sequence, id"

    # =========================================================================
    # Core Fields
    # =========================================================================

    runtime_id = fields.Many2one(
        comodel_name="automation.runtime",
        string="Workflow Runtime",
        required=True,
        ondelete="cascade",
        index=True,
    )
    action_id = fields.Many2one(
        comodel_name="ir.actions.server",
        string="Server Action",
        required=True,
        ondelete="restrict",
        help="The server action to execute",
    )
    name = fields.Char(
        string="Step Name",
        required=True,
        help="Description of this workflow step",
    )
    sequence = fields.Integer(
        default=10,
        help="Execution order (lower = earlier)",
    )
    state = fields.Selection(
        selection=[
            ("waiting", "Waiting"),
            ("ready", "Ready"),
            ("in_progress", "In Progress"),
            ("done", "Done"),
            ("cancel", "Cancelled"),
            ("error", "Error"),
        ],
        default="waiting",
        required=True,
        readonly=True,
        copy=False,
        help="Action execution state",
    )
    error_message = fields.Text(
        string="Error Details",
        readonly=True,
        help="Error message if execution failed",
    )

    # =========================================================================
    # DAG Structure
    # =========================================================================

    predecessor_ids = fields.Many2many(
        comodel_name="automation.runtime.line",
        relation="automation_runtime_line_dag",
        column1="successor_id",
        column2="predecessor_id",
        string="Wait For",
        help="This action waits for these predecessors to complete",
    )

    successor_ids = fields.Many2many(
        comodel_name="automation.runtime.line",
        relation="automation_runtime_line_dag",
        column1="predecessor_id",
        column2="successor_id",
        string="Enables",
        readonly=True,
        help="Completing this action enables these successors",
    )

    is_ready = fields.Boolean(
        string="Is Ready",
        compute="_compute_is_ready",
        store=True,
        help="True when all predecessors are done",
    )

    # =========================================================================
    # Results Tracking
    # =========================================================================

    created_record_ref = fields.Reference(
        string="Created Record",
        selection="_selection_created_record_models",
        readonly=True,
        help="Record created or modified by this action",
    )

    # =========================================================================
    # Selection Methods
    # =========================================================================

    @api.model
    def _selection_created_record_models(self):
        """Return available models for created_record_ref.

        Override this method in inheriting modules to add specific models.
        Base implementation returns common workflow models.
        """
        return [
            ("automation.runtime", "Workflow Runtime"),
        ]

    # =========================================================================
    # Compute Methods
    # =========================================================================

    @api.depends("predecessor_ids.state", "state")
    def _compute_is_ready(self):
        """Compute if this action is ready to execute."""
        for line in self:
            if line.state != "waiting":
                line.is_ready = False
                continue

            # No predecessors = ready immediately
            if not line.predecessor_ids:
                line.is_ready = True
                continue

            # All predecessors must be done
            done_predecessors = line.predecessor_ids.filtered(
                lambda p: p.state == "done",
            )
            line.is_ready = len(done_predecessors) == len(line.predecessor_ids)

    # =========================================================================
    # State Transitions
    # =========================================================================

    def action_mark_ready(self):
        """Mark action as ready to execute."""
        self.write({"state": "ready", "error_message": False})

    def action_cancel(self):
        """Cancel this action and propagate to sub-workflows."""
        for line in self:
            if line.state in ["done", "cancel"]:
                continue

            line.state = "cancel"

            # Cancel any created sub-workflows
            if (
                line.created_record_ref
                and line.created_record_ref._name == "automation.runtime"
            ):
                line.created_record_ref.action_cancel()

    def action_mark_done(self):
        """Mark action as done and activate successors."""
        self.write({"state": "done", "error_message": False})

        # Activate ready successors
        for successor in self.successor_ids:
            if successor.state == "waiting":
                # Recompute readiness
                successor._compute_is_ready()

                if successor.is_ready:
                    successor.action_mark_ready()
                    _logger.info(
                        "Action '%s' (#%d) is now ready",
                        successor.name,
                        successor.id,
                    )

        # Check if entire workflow is complete
        incomplete = self.runtime_id.line_ids.filtered(
            lambda l: l.state not in ["done", "cancel"],
        )

        if not incomplete:
            self.runtime_id.action_done()

    def action_mark_error(self, error_msg):
        """Mark action as failed with error message."""
        self.write({"state": "error", "error_message": error_msg})

    def action_execute(self):
        """Execute the server action for this line.

        Returns:
            Action dict or True
        """
        self.ensure_one()

        if self.state != "in_progress":
            raise UserError(_("Action is not in progress"))

        try:
            # Build execution context
            ctx = dict(self.env.context)
            ctx.update(
                {
                    "active_model": "automation.runtime",
                    "active_id": self.runtime_id.id,
                    "active_ids": [self.runtime_id.id],
                    "runtime_line_id": self.id,
                },
            )

            # Execute the server action
            _logger.info(
                "Executing action '%s' (#%d) for runtime %s",
                self.name,
                self.action_id.id,
                self.runtime_id.name,
            )

            result = self.action_id.with_context(**ctx).run()

            # Mark as done
            self.action_mark_done()

            _logger.info("✓ Action '%s' completed successfully", self.name)

            return result or True

        except Exception as e:
            error_msg = str(e)
            _logger.error(
                "✗ Action '%s' failed: %s",
                self.name,
                error_msg,
                exc_info=True,
            )

            self.action_mark_error(error_msg)
            raise

    # =========================================================================
    # Document Viewing
    # =========================================================================

    def action_view_document(self):
        """Open created document.

        Returns action to view the record stored in created_record_ref.
        """
        self.ensure_one()

        if not self.created_record_ref:
            raise UserError(_("No document created by this action"))

        return {
            "name": _("Created Record"),
            "type": "ir.actions.act_window",
            "res_model": self.created_record_ref._name,
            "view_mode": "form",
            "res_id": self.created_record_ref.id,
        }
