from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AutomationRuntime(models.Model):
    """Runtime instance for manual/semi-automatic workflow execution.

    This model stores the execution context for workflows that need:
    - User interaction (wizard-based steps)
    - Runtime parameters (partner, amount, dates)
    - Progress tracking
    - Multi-step orchestration

    Use Cases:
    - Manual multi-step accounting workflows
    - Bank reconciliation with context
    - Approval workflows with state
    - Multi-company operations

    For fully automatic workflows (event-triggered), use base.automation directly
    without creating runtime instances.
    """

    _name = "automation.runtime"
    _description = "Automation Workflow Runtime Instance"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _check_company_auto = True
    _order = "create_date desc, id desc"

    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
        readonly=True,
        index=True,
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        string="Currency",
        required=True,
        default=lambda self: self.env.company.currency_id,
    )
    multicompany_id = fields.Many2one(
        comodel_name="res.company",
        string="Target Company",
        help="Target company for multi-company operations",
    )
    automation_id = fields.Many2one(
        comodel_name="base.automation",
        string="Automation",
        required=True,
        domain=[("model_name", "=", "base.automation")],
        index=True,
        tracking=True,
        ondelete="restrict",
        help="The automation workflow definition to execute",
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Partner",
        required=True,
        domain=["|", ("parent_id", "=", False), ("is_company", "=", True)],
        index=True,
        tracking=True,
        help="Main partner for this operation",
    )
    diff_partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Alternative Partner",
        domain=["|", ("parent_id", "=", False), ("is_company", "=", True)],
        help="Alternative partner for specific actions in workflow",
    )
    name = fields.Char(
        string="Operation",
        required=True,
        default=lambda self: _("New"),
        readonly=True,
        copy=False,
        index="trigram",
        tracking=True,
    )
    amount = fields.Monetary(
        currency_field="currency_id",
        tracking=True,
        help="Operation amount",
    )
    reference = fields.Char(
        copy=False,
        tracking=True,
        help="External reference or description",
    )
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("in_progress", "In Progress"),
            ("done", "Done"),
            ("cancel", "Cancelled"),
        ],
        required=True,
        default="draft",
        readonly=True,
        copy=False,
        tracking=True,
        help="Workflow execution state",
    )
    date = fields.Date(
        string="Date",
        required=True,
        default=fields.Date.context_today,
        tracking=True,
        help="Reference date for this workflow execution",
    )
    line_ids = fields.One2many(
        comodel_name="automation.runtime.line",
        inverse_name="runtime_id",
        string="Workflow Steps",
        readonly=True,
        help="Execution history of workflow actions",
    )
    progress = fields.Integer(
        string="Progress %",
        compute="_compute_progress",
        compute_sudo=True,
        store=True,
        help="Completion percentage (0-100)",
    )
    progress_display = fields.Char(
        string="Progress",
        compute="_compute_progress_display",
        compute_sudo=True,
        help="Human-readable progress display",
    )

    # =========================================================================
    # CRUD Methods
    # =========================================================================

    @api.model_create_multi
    def create(self, vals_list):
        """Generate sequence name and set initial state."""
        for vals in vals_list:
            if "company_id" in vals:
                self = self.sudo().with_company(vals["company_id"])

            if vals.get("name", _("New")) == _("New"):
                seq_date = (
                    fields.Datetime.context_timestamp(
                        self,
                        fields.Datetime.to_datetime(vals["date"]),
                    )
                    if "date" in vals
                    else None
                )
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "automation.runtime",
                    sequence_date=seq_date,
                ) or _("New")

        return super().create(vals_list)

    @api.depends("line_ids.state")
    def _compute_progress(self):
        """Calculate workflow completion percentage."""
        for runtime in self:
            total = len(runtime.line_ids)
            if total == 0:
                runtime.progress = 0
                continue

            done = len(runtime.line_ids.filtered(lambda l: l.state == "done"))
            runtime.progress = int(round((done / total) * 100))

    @api.depends("line_ids.state")
    def _compute_progress_display(self):
        """Calculate human-readable progress display."""
        for runtime in self:
            total = len(runtime.line_ids)
            if total == 0:
                runtime.progress_display = "0/0 steps"
                continue

            done = len(runtime.line_ids.filtered(lambda l: l.state == "done"))
            runtime.progress_display = f"{done}/{total} steps"

    def action_start(self):
        """Start workflow execution by creating action lines."""
        self.ensure_one()

        if self.state != "draft":
            return

        if not self.partner_id:
            raise UserError(_("Please set a partner before starting the workflow."))

        # Create workflow action lines from automation's server actions
        self._create_action_lines()

        # Update state
        self.state = "in_progress"

        # Post message
        self.message_post(
            body=_("Workflow started with %d steps", len(self.line_ids)),
            subject=_("Workflow Started"),
        )

    def action_cancel(self):
        """Cancel workflow and all pending actions."""
        self.ensure_one()

        if self.state in ["done", "cancel"]:
            return

        self.state = "cancel"

        # Cancel all non-completed lines
        self.line_ids.filtered(
            lambda l: l.state not in ["done", "cancel"],
        ).action_cancel()

        self.message_post(body=_("Workflow cancelled"), subject=_("Workflow Cancelled"))

    def action_done(self):
        """Mark workflow as completed."""
        self.ensure_one()

        if self.state != "in_progress":
            return

        self.state = "done"

        self.message_post(
            body=_("Workflow completed successfully"),
            subject=_("Workflow Completed"),
        )

    def action_next_step(self):
        """Execute the next ready action in the workflow."""
        self.ensure_one()

        if self.state != "in_progress":
            raise UserError(_("Workflow is not in progress"))

        # Get ready actions
        ready_lines = self.line_ids.filtered(lambda l: l.state == "ready")

        if not ready_lines:
            # Check if workflow is complete
            incomplete = self.line_ids.filtered(
                lambda l: l.state not in ["done", "cancel"],
            )

            if not incomplete:
                # All done - mark workflow complete
                self.action_done()
                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "title": _("Workflow Complete"),
                        "message": _("All workflow steps completed successfully!"),
                        "type": "success",
                    },
                }
            else:
                raise UserError(
                    _("No actions are ready to execute. Check dependencies."),
                )

        # Execute first ready action
        next_line = ready_lines[0]

        # Mark as in progress
        next_line.state = "in_progress"

        # Build execution context
        context = self._get_execution_context()
        context.update(
            {
                "runtime_id": self.id,
                "runtime_line_id": next_line.id,
            },
        )

        # Execute the action
        return next_line.with_context(**context).action_execute()

    def _create_action_lines(self):
        """Create runtime.line records from automation's server actions.

        Builds the DAG structure using predecessor/successor relationships.
        """
        self.ensure_one()

        # Get all server actions from the automation (ordered by sequence)
        actions = self.automation_id.action_server_ids.sorted("sequence")

        if not actions:
            raise UserError(
                _(
                    "Automation '%s' has no server actions configured",
                    self.automation_id.name,
                ),
            )

        # Create lines and build DAG structure
        lines = self.env["automation.runtime.line"]
        prev_line = None

        for action in actions:
            # Prepare line values
            vals = {
                "runtime_id": self.id,
                "action_id": action.id,
                "name": action.name,
                "sequence": action.sequence,
                "state": "ready" if not prev_line else "waiting",
            }

            # Create line
            line = self.env["automation.runtime.line"].create(vals)
            lines |= line

            # Build sequential DAG (each action waits for previous)
            if prev_line:
                line.predecessor_ids = [(4, prev_line.id)]

            prev_line = line

        return lines

    def _get_execution_context(self):
        """Get context dictionary for action execution."""
        self.ensure_one()

        return {
            "default_partner_id": self.partner_id.id if self.partner_id else False,
            "default_diff_partner_id": (
                self.diff_partner_id.id if self.diff_partner_id else False
            ),
            "default_amount": self.amount,
            "default_currency_id": self.currency_id.id,
            "default_reference": self.reference,
            "default_date": self.date,
            "target_company_id": (
                self.multicompany_id.id if self.multicompany_id else False
            ),
        }

    def action_view_automation(self):
        """Open the automation workflow definition."""
        self.ensure_one()
        return {
            "name": _("Automation Workflow"),
            "type": "ir.actions.act_window",
            "res_model": "base.automation",
            "view_mode": "form",
            "res_id": self.automation_id.id,
        }
