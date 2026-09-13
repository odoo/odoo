import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from .ir_websocket import SUBCHANNEL as BUS_SUBCHANNEL
from .workflow_edge import SETTLED_STATES

_logger = logging.getLogger(__name__)

DISPATCH_BATCH_SIZE = 500


class AutomationRuntime(models.Model):
    _name = "automation.runtime"
    _description = "Automation Workflow Runtime Instance"
    _inherit = ["mixin.mail.thread", "mixin.mail.activity"]
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
        comodel_name="automation.rule",
        string="Automation",
        required=True,
        index=True,
        tracking=True,
        ondelete="restrict",
        help="The automation workflow definition being executed",
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Partner",
        domain=["|", ("parent_id", "=", False), ("is_company", "=", True)],
        index=True,
        tracking=True,
        help="Main partner for this operation (optional)",
    )
    diff_partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Alternative Partner",
        domain=["|", ("parent_id", "=", False), ("is_company", "=", True)],
        help="Alternative partner for specific actions in workflow",
    )
    res_model = fields.Char(
        string="Target Model",
        index=True,
        help="Model of the record being automated (e.g. 'res.partner')",
    )
    res_id = fields.Integer(
        string="Target Record ID",
        index=True,
        help="ID of the specific record being automated",
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
            ("waiting_resume", "Waiting to Resume"),
            ("done", "Done"),
            ("error", "Failed"),
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
        help="Per-step execution history",
    )
    parent_line_id = fields.Many2one(
        comodel_name="automation.runtime.line",
        string="Parent Step",
        index="btree_not_null",
        ondelete="cascade",
        readonly=True,
        copy=False,
        help="The Sub-workflow step this run was started by, if any",
    )
    edge_ids = fields.One2many(
        comodel_name="automation.runtime.edge",
        inverse_name="runtime_id",
        string="Workflow Edges",
        readonly=True,
        help="The DAG this run was started with, conditions included",
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

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            seq_env = self.sudo()
            if "company_id" in vals:
                seq_env = seq_env.with_company(vals["company_id"])

            if vals.get("name", _("New")) == _("New"):
                seq_date = (
                    fields.Datetime.context_timestamp(
                        seq_env,
                        fields.Datetime.to_datetime(vals["date"]),
                    )
                    if "date" in vals
                    else None
                )
                vals["name"] = seq_env.env["ir.sequence"].next_by_code(
                    "automation.runtime",
                    sequence_date=seq_date,
                ) or _("New")

        return super().create(vals_list)

    def _settled_line_counts(self):
        return {
            runtime.id: (
                len(
                    runtime.line_ids.filtered(
                        lambda l: l.state in SETTLED_STATES,
                    ),
                ),
                len(runtime.line_ids),
            )
            for runtime in self
        }

    @api.depends("line_ids.state")
    def _compute_progress(self):
        counts = self._settled_line_counts()
        for runtime in self:
            settled, total = counts[runtime.id]
            runtime.progress = round((settled / total) * 100) if total else 0

    @api.depends("line_ids.state")
    def _compute_progress_display(self):
        counts = self._settled_line_counts()
        for runtime in self:
            settled, total = counts[runtime.id]
            runtime.progress_display = f"{settled}/{total} steps"

    def action_start(self):
        self.check_singleton()

        if self.state != "draft":
            return

        self._create_action_lines()
        self.state = "in_progress"

        self.message_post(
            body=_("Workflow started with %d steps", len(self.line_ids)),
            subject=_("Workflow Started"),
        )
        self._notify_workflow_change()

    def _notify_workflow_change(self):
        for runtime in self:
            rule = runtime.automation_id
            if not rule:
                continue
            rule._bus_send(
                "automation.workflow/update",
                {
                    "automation_id": rule.id,
                    "runtime_id": runtime.id,
                    "state": runtime.state,
                },
                subchannel=BUS_SUBCHANNEL,
            )

    def action_run_all(self):
        self.check_singleton()

        while self.state == "in_progress":
            ready_lines = self.line_ids.filtered(lambda l: l.state == "ready")
            if not ready_lines:
                self._settle_idle()
                break
            for line in ready_lines:
                line.action_execute()
                if self.state != "in_progress":
                    break

        self._notify_workflow_change()
        return self.state

    def _settle_idle(self):
        self.check_singleton()
        if self._finish_if_settled():
            return
        if self.line_ids.filtered(
            lambda l: (
                l.state in ("paused", "scheduled")
                or (l.state == "waiting" and l._awaits_event())
            ),
        ):
            if self.state == "in_progress":
                self.action_wait()
            return
        blocked = self.line_ids.filtered(lambda l: l.state not in SETTLED_STATES)
        if blocked:
            _logger.warning(
                "Runtime %s cannot advance: %s step(s) never became ready (%s).",
                self.name,
                len(blocked),
                ", ".join(blocked.mapped("name")),
            )
            blocked.action_mark_error(
                _("Step never became ready: its dependencies cannot complete."),
            )
            self.action_error()

    def _is_queued(self):
        self.check_singleton()
        return self.automation_id.run_mode == "queued"

    def _launch(self):
        for runtime in self:
            runtime.action_start()
            if runtime._is_queued():
                runtime._request_dispatch()
            else:
                runtime.action_run_all()

    def _request_dispatch(self):
        self.env.ref("automation.ir_cron_data_automation_resume")._trigger()

    def _advance(self):
        for runtime in self.filtered(
            lambda run: run.state in ("in_progress", "waiting_resume"),
        ):
            if not runtime._is_queued():
                runtime.state = "in_progress"
                runtime.action_run_all()
            elif runtime.line_ids.filtered(lambda l: l.state == "ready"):
                runtime.state = "in_progress"
                runtime._request_dispatch()
            else:
                runtime._settle_idle()

    def _finish_if_settled(self):
        self.check_singleton()
        if self.state not in ("in_progress", "waiting_resume"):
            return False
        if any(line.state not in SETTLED_STATES for line in self.line_ids):
            return False
        self.action_done()
        return True

    def action_cancel(self):
        self.check_singleton()

        if self.state in ["done", "cancel", "error"]:
            return

        self.state = "cancel"
        self.line_ids.filtered(
            lambda l: l.state not in SETTLED_STATES,
        ).action_cancel()
        self.message_post(body=_("Workflow cancelled"), subject=_("Workflow Cancelled"))

    def _release_parent_line(self):
        for runtime in self.filtered(
            lambda run: run.parent_line_id.state == "paused",
        ):
            line = runtime.parent_line_id
            parent = line.runtime_id
            if parent.state == "waiting_resume":
                parent.state = "in_progress"
            if runtime.state == "done":
                line.action_resume()
            else:
                line.action_mark_error(
                    _("Sub-workflow '%(name)s' did not complete.", name=runtime.name),
                )
                if not line._has_error_handler():
                    parent.action_error()
                    continue
            parent._advance()

    def action_wait(self):
        self.check_singleton()

        if self.state != "in_progress":
            return

        self.state = "waiting_resume"

    def action_resume(self):
        now = self.env.cr.now()
        for runtime in self.filtered(lambda run: run.state == "waiting_resume"):
            due = runtime.line_ids.filtered(
                lambda step: (
                    step.state in ("paused", "scheduled")
                    and step.date_resume
                    and step.date_resume <= now
                ),
            )
            if not due:
                continue
            runtime.state = "in_progress"
            due.filtered(lambda step: step.state == "paused").action_resume()
            for step in due.filtered(lambda step: step.state == "scheduled"):
                step._settle_readiness()
            runtime._advance()

    @api.model
    def _resume_waiting_executions(self):
        waiting = self.search(
            [
                ("state", "=", "waiting_resume"),
                (
                    "line_ids",
                    "any",
                    [
                        ("state", "in", ("paused", "scheduled")),
                        ("date_resume", "<=", self.env.cr.now()),
                    ],
                ),
            ],
        )
        if waiting:
            _logger.info("Resuming %s paused workflow run(s)", len(waiting))
        waiting.action_resume()
        return len(waiting)

    @api.model
    def _dispatch_due_steps(self):
        self._resume_waiting_executions()
        Line = self.env["automation.runtime.line"]
        handled = set()
        while lines := Line.search(
            [
                ("state", "=", "ready"),
                ("id", "not in", list(handled)),
                ("runtime_id.state", "in", ("in_progress", "waiting_resume")),
                ("runtime_id.automation_id.run_mode", "=", "queued"),
            ],
            order="id",
            limit=DISPATCH_BATCH_SIZE,
        ):
            handled.update(lines.ids)
            for action, batch in lines.grouped("action_id").items():
                runtimes = batch.runtime_id
                runtimes.filtered(
                    lambda run: run.state == "waiting_resume"
                ).state = "in_progress"
                action._execute_runtime_lines(batch)
                for runtime in runtimes.filtered(
                    lambda run: (
                        run.state == "in_progress"
                        and not run.line_ids.filtered(lambda l: l.state == "ready")
                    ),
                ):
                    runtime._settle_idle()
                if self.env.context.get("cron_id") and not self.env[
                    "ir.cron"
                ]._commit_progress(len(batch)):
                    self._request_dispatch()
                    return len(handled)
        return len(handled)

    def action_done(self):
        self.check_singleton()

        if self.state not in ("in_progress", "waiting_resume"):
            return

        self.state = "done"
        self.message_post(
            body=_("Workflow completed successfully"),
            subject=_("Workflow Completed"),
        )
        self._release_parent_line()

    def action_error(self):
        self.check_singleton()

        if self.state not in ("in_progress", "waiting_resume"):
            return

        self.state = "error"
        failed = self.line_ids.filtered(lambda l: l.state == "error")
        self.line_ids.filtered(lambda l: l.state not in SETTLED_STATES).write(
            {
                "state": "error",
                "date_resume": False,
                "date_settled": self.env.cr.now(),
                "error_message": _("Step never ran: the workflow already failed."),
            }
        )
        self._release_parent_line()
        self.message_post(
            body=_(
                "Workflow failed at: %(steps)s",
                steps=", ".join(failed.mapped("name")) or _("unknown step"),
            ),
            subject=_("Workflow Failed"),
        )

    def action_next_step(self):
        self.check_singleton()

        if self.state != "in_progress":
            raise UserError(_("Workflow is not in progress"))

        ready_lines = self.line_ids.filtered(lambda l: l.state == "ready")

        if not ready_lines:
            incomplete = self.line_ids.filtered(
                lambda l: l.state not in SETTLED_STATES,
            )
            if not incomplete:
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
            raise UserError(
                _("No actions are ready to execute. Check dependencies."),
            )

        next_line = ready_lines[0]
        context = self._get_execution_context()
        context.update(
            {
                "runtime_id": self.id,
                "runtime_line_id": next_line.id,
            },
        )
        return next_line.with_context(**context).action_execute()

    def _create_action_lines(self):
        self.check_singleton()

        actions = self.automation_id.action_server_ids.sorted("sequence")
        if not actions:
            raise UserError(
                _(
                    "Automation '%s' has no server actions configured",
                    self.automation_id.name,
                ),
            )

        lines = self.env["automation.runtime.line"].create(
            [
                {
                    "runtime_id": self.id,
                    "action_id": action.id,
                    "name": action.name,
                    "sequence": action.sequence,
                    "state": "waiting",
                }
                for action in actions
            ]
        )
        line_by_action: dict[int, models.Model] = dict(
            zip(actions.ids, lines, strict=True)
        )

        self.env["automation.runtime.edge"].create(
            [
                {
                    "runtime_id": self.id,
                    "source_line_id": line_by_action[edge.source_node_id.id].id,
                    "target_line_id": line_by_action[edge.target_node_id.id].id,
                    "condition": edge.condition,
                    "condition_expr": edge.condition_expr,
                    "event_code": edge.event_code,
                    "delay": edge.delay,
                    "delay_unit": edge.delay_unit,
                }
                for edge in self.automation_id.edge_ids
                if edge.source_node_id.id in line_by_action
                and edge.target_node_id.id in line_by_action
            ]
        )

        for line in line_by_action.values():
            if line._predecessors_satisfied():
                line.action_mark_ready()

        return self.env["automation.runtime.line"].browse(
            [line.id for line in line_by_action.values()]
        )

    def _get_target_record(self):
        self.check_singleton()
        if not self.res_model:
            return self.env["automation.runtime"].browse(self.id)
        return self.env[self.res_model].browse(self.res_id or [])

    def _get_execution_context(self):
        self.check_singleton()
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
        self.check_singleton()
        return {
            "name": _("Automation Workflow"),
            "type": "ir.actions.act_window",
            "res_model": "automation.rule",
            "view_mode": "form",
            "res_id": self.automation_id.id,
        }
