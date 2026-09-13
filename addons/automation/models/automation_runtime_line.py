import logging
from collections import defaultdict

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from .workflow_edge import EVENT_CONDITIONS, SETTLED_STATES

_logger = logging.getLogger(__name__)


class AutomationRuntimeLine(models.Model):
    _name = "automation.runtime.line"
    _description = "Automation Runtime Action Line"
    _order = "sequence, id"

    runtime_id = fields.Many2one(
        comodel_name="automation.runtime",
        string="Workflow Runtime",
        index=True,
        required=True,
        ondelete="cascade",
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
            ("scheduled", "Scheduled"),
            ("ready", "Ready"),
            ("paused", "Paused"),
            ("in_progress", "In Progress"),
            ("done", "Done"),
            ("skipped", "Skipped"),
            ("cancel", "Cancelled"),
            ("error", "Error"),
        ],
        default="waiting",
        copy=False,
        readonly=True,
        required=True,
        help="Action execution state",
    )
    activity_ids = fields.One2many(
        comodel_name="mail.activity",
        inverse_name="automation_runtime_line_id",
        string="Approval Activities",
        readonly=True,
    )
    date_resume = fields.Datetime(
        string="Resumes At",
        copy=False,
        readonly=True,
        help="When a scheduled step becomes ready, or a paused Wait step completes",
    )
    date_ready = fields.Datetime(
        string="Ready Since",
        copy=False,
        readonly=True,
        help="When the step became ready; its validity counts from here",
    )
    date_settled = fields.Datetime(
        string="Settled At",
        copy=False,
        readonly=True,
        help="When the step finished, failed, was skipped or was cancelled; "
        "a delayed edge out of it counts from here",
    )
    skip_reason = fields.Selection(
        selection=[
            ("branch", "Branch not taken"),
            ("revoked", "Revoked by an exclusive event"),
            ("expired", "Validity passed"),
            ("filtered", "Filtered out"),
            ("cancelled", "Cancelled"),
        ],
        copy=False,
        readonly=True,
    )
    error_message = fields.Text(
        string="Error Details",
        readonly=True,
        help="Error message if execution failed",
    )

    edge_in_ids = fields.One2many(
        comodel_name="automation.runtime.edge",
        inverse_name="target_line_id",
        string="Waits For",
        help="Edges that must be satisfied before this step can execute",
    )

    edge_out_ids = fields.One2many(
        comodel_name="automation.runtime.edge",
        inverse_name="source_line_id",
        string="Enables",
        readonly=True,
        help="Edges this step's outcome can satisfy",
    )

    created_record_ref = fields.Reference(
        selection="_selection_created_record_models",
        string="Created Record",
        readonly=True,
        help="Record created or modified by this action",
    )

    @api.model
    def _selection_created_record_models(self):
        return [
            ("automation.runtime", "Workflow Runtime"),
        ]

    def _predecessors_satisfied(self):
        self.check_singleton()
        return all(edge._is_satisfied() for edge in self.edge_in_ids)

    def _get_predecessors(self):
        return self.edge_in_ids.source_line_id

    def _get_successors(self):
        return self.edge_out_ids.target_line_id

    def action_mark_ready(self, due=None):
        self.write(
            {
                "state": "ready",
                "date_ready": self.env.cr.now(),
                "date_resume": due or False,
                "error_message": False,
            }
        )

    def _is_expired(self):
        self.check_singleton()
        action = self.action_id
        return bool(
            action.validity_delay
            and self.date_ready
            and self.date_ready + action._get_validity_delta() < self.env.cr.now()
        )

    def action_cancel(self):
        lines = self.filtered(
            lambda line: line.state not in ("done", "skipped", "cancel"),
        )
        lines.write({"state": "cancel", "date_settled": self.env.cr.now()})
        for line in lines.filtered("created_record_ref"):
            if line.created_record_ref._name == "automation.runtime":
                line.created_record_ref.action_cancel()

    def _activate_successors(self):
        self.edge_out_ids.target_line_id.filtered(
            lambda successor: successor.state in ("waiting", "scheduled"),
        )._settle_readiness()

    def _settle_readiness(self):
        if not self:
            return
        now = self.env.cr.now()
        edges = self.edge_in_ids
        edges.fetch(
            [
                "source_line_id",
                "condition",
                "condition_expr",
                "event_code",
                "delay",
                "delay_unit",
                "date_event",
                "revoked",
            ]
        )
        edges.source_line_id.fetch(["state", "date_settled"])
        decided = defaultdict(self.browse)
        for line in self:
            decision = line._readiness_decision(now)
            if decision:
                decided[decision] |= line
        for (kind, value), lines in decided.items():
            if kind == "skip":
                lines._skip(reason=value)
            elif kind == "wait":
                lines.write({"state": "waiting", "date_resume": False})
            elif kind == "schedule":
                lines._schedule(value)
            else:
                lines.action_mark_ready(due=value)

    def _readiness_decision(self, now):
        self.check_singleton()
        edges = self.edge_in_ids
        if not edges:
            due = self._start_due()
            return ("schedule", due) if due and due > now else ("ready", due)
        if any(edge.source_line_id.state not in SETTLED_STATES for edge in edges):
            return None
        live = edges.filtered(lambda edge: edge.source_line_id.state != "skipped")
        verdicts = [edge._verdict(now) for edge in live]
        if not live or any(satisfied is False for satisfied, _due in verdicts):
            return ("skip", "revoked" if any(live.mapped("revoked")) else "branch")
        if any(satisfied is None for satisfied, _due in verdicts):
            return ("wait", None) if self.state == "scheduled" else None
        due = max((due for _satisfied, due in verdicts if due), default=None)
        return ("schedule", due) if due and due > now else ("ready", due)

    def _start_due(self):
        self.check_singleton()
        action = self.action_id
        if not action.start_delay:
            return None
        return (self.create_date or self.env.cr.now()) + action._get_start_delta()

    def _skip(self, reason="branch", message=False):
        self.write(
            {
                "state": "skipped",
                "skip_reason": reason,
                "date_resume": False,
                "date_settled": self.env.cr.now(),
                "error_message": message,
            }
        )
        self._activate_successors()

    def _schedule(self, due):
        self.write({"state": "scheduled", "date_resume": due})
        self._trigger_resume_at(due)

    def _trigger_resume_at(self, due):
        triggered = self.env.cr.precommit.data.setdefault(
            "automation.resume_triggers", set()
        )
        if due in triggered:
            return
        triggered.add(due)
        self.env.ref("automation.ir_cron_data_automation_resume")._trigger(at=due)

    def _awaits_event(self):
        self.check_singleton()
        return any(
            edge.condition == "event"
            and not edge.date_event
            and not edge.revoked
            and edge.source_line_id.state in ("done", "error", "cancel")
            for edge in self.edge_in_ids
        )

    def _receive_event(self, code, exclusive=False):
        now = self.env.cr.now()
        for line in self:
            edges = line.edge_out_ids
            received = edges.filtered(
                lambda edge: (
                    edge.condition in EVENT_CONDITIONS
                    and edge.event_code == code
                    and not edge.date_event
                ),
            )
            if not received and not exclusive:
                continue
            received.date_event = now
            if exclusive:
                (edges - received).revoked = True
            runtime = line.runtime_id
            if runtime.state not in ("in_progress", "waiting_resume"):
                continue
            line._activate_successors()
            runtime._advance()

    def _has_error_handler(self):
        self.check_singleton()
        return any(
            edge.condition in ("on_error", "always") for edge in self.edge_out_ids
        )

    def _contains_its_error(self):
        self.check_singleton()
        return (
            self._has_error_handler()
            or self.runtime_id.automation_id.step_error_policy == "close_branch"
        )

    def action_pause(self):
        resume_at = self.env.cr.now() + self.action_id._get_wait_delta()
        self.write(
            {"state": "paused", "date_resume": resume_at, "error_message": False}
        )
        self._trigger_resume_at(resume_at)
        _logger.info(
            "Step '%s' (#%d) paused until %s",
            self.name,
            self.id,
            resume_at,
        )
        return True

    def action_request_approval(self):
        self.check_singleton()
        record = self.runtime_id._get_target_record()
        if not record:
            self.action_mark_error(
                _("Approval cannot be requested: this run has no target record."),
            )
            self.runtime_id.action_error()
            return False

        activity_type = self.env.ref("mail.mail_activity_data_todo", False)
        summary = self.action_id.approval_note or self.name
        self.env["mail.activity"].create(
            [
                {
                    "res_model_id": self.env["ir.model"]._get_id(record._name),
                    "res_id": record.id,
                    "activity_type_id": activity_type.id if activity_type else False,
                    "summary": summary,
                    "user_id": approver.id,
                    "automation_runtime_line_id": self.id,
                }
                for approver in self.action_id.approval_user_ids
            ]
        )
        self.write({"state": "paused", "date_resume": False, "error_message": False})
        return True

    def action_start_subflow(self):
        self.check_singleton()
        parent = self.runtime_id
        child = self.env["automation.runtime"].create(
            {
                "automation_id": self.action_id.subflow_automation_id.id,
                "res_model": parent.res_model,
                "res_id": parent.res_id,
                "parent_line_id": self.id,
            }
        )
        self.write(
            {
                "state": "paused",
                "date_resume": False,
                "error_message": False,
                "created_record_ref": f"automation.runtime,{child.id}",
            }
        )
        child._launch()
        return True

    def action_refuse_approval(self, reason=False):
        for line in self.filtered(lambda step: step.state == "paused"):
            activities = line.activity_ids.filtered("active")
            runtime = line.runtime_id
            if runtime.state == "waiting_resume":
                runtime.state = "in_progress"
            line.action_mark_error(reason or _("Approval was refused."))
            activities.unlink()
            if line._contains_its_error():
                runtime._advance()
            else:
                runtime.action_error()

    def _fail_missing_approval(self):
        for line in self.filtered(
            lambda step: (
                step.state == "paused"
                and step.action_id.node_type == "approval"
                and not step.activity_ids.filtered("active")
            ),
        ):
            runtime = line.runtime_id
            if runtime.state == "waiting_resume":
                runtime.state = "in_progress"
            line.action_mark_error(
                _("The approval activity was removed before anyone acted on it."),
            )
            if line._contains_its_error():
                runtime._advance()
            else:
                runtime.action_error()

    def _check_approval_complete(self):
        approvals = self.filtered(
            lambda step: (
                step.state == "paused" and step.action_id.node_type == "approval"
            ),
        )
        for line in approvals:
            if line.activity_ids.filtered("active"):
                continue
            runtime = line.runtime_id
            if runtime.state == "waiting_resume":
                runtime.state = "in_progress"
            line.action_resume()
            runtime._advance()

    def action_resume(self):
        paused = self.filtered(lambda step: step.state == "paused")
        paused.write(
            {
                "state": "done",
                "date_resume": False,
                "date_settled": self.env.cr.now(),
            }
        )
        paused._activate_successors()

    def action_mark_done(self):
        self.write(
            {"state": "done", "date_settled": self.env.cr.now(), "error_message": False}
        )
        self._activate_successors()
        self.runtime_id._finish_if_settled()

    def action_mark_error(self, error_msg):
        self.write(
            {
                "state": "error",
                "date_settled": self.env.cr.now(),
                "error_message": error_msg,
            }
        )
        self.filtered(lambda line: line._contains_its_error())._activate_successors()

    def action_execute(self):
        self.check_singleton()

        if self.state not in ("ready", "in_progress"):
            raise UserError(_("Action is not ready to execute"))

        if self._is_expired():
            action = self.action_id
            units = dict(
                action._fields["validity_unit"]._description_selection(self.env)
            )
            self._skip(
                reason="expired",
                message=_(
                    "Skipped: it became ready at %(ready)s, and its validity of "
                    "%(delay)s %(unit)s had passed when it came to run.",
                    ready=self.date_ready,
                    delay=action.validity_delay,
                    unit=units.get(action.validity_unit, action.validity_unit),
                ),
            )
            self.runtime_id._finish_if_settled()
            return False

        if self.action_id.node_type == "wait":
            return self.action_pause()

        if self.action_id.node_type == "approval":
            return self.action_request_approval()

        if self.action_id.node_type == "subflow":
            return self.action_start_subflow()

        self.write({"state": "in_progress"})

        try:
            ctx = dict(self.env.context)
            runtime = self.runtime_id
            if runtime.res_model and runtime.res_id:
                ctx.update(
                    {
                        "active_model": runtime.res_model,
                        "active_id": runtime.res_id,
                        "active_ids": [runtime.res_id],
                        "runtime_line_id": self.id,
                        "runtime_id": runtime.id,
                    }
                )
            else:
                ctx.update(
                    {
                        "active_model": "automation.runtime",
                        "active_id": runtime.id,
                        "active_ids": [runtime.id],
                        "runtime_line_id": self.id,
                        "runtime_id": runtime.id,
                    }
                )

            _logger.info(
                "Executing action '%s' (#%d) for runtime %s",
                self.name,
                self.action_id.id,
                self.runtime_id.name,
            )

            with self.env.cr.savepoint():
                result = self.action_id.with_context(**ctx).run()

            self.action_mark_done()

            _logger.info("✓ Action '%s' completed successfully", self.name)

            return result or True

        except Exception as e:
            error_msg = str(e)
            _logger.exception(
                "✗ Action '%s' failed: %s",
                self.name,
                error_msg,
            )

            self.action_mark_error(error_msg)
            if not self._contains_its_error():
                self.runtime_id.action_error()
            return False

    def action_view_document(self):
        self.check_singleton()

        if not self.created_record_ref:
            raise UserError(_("No document created by this action"))

        return {
            "name": _("Created Record"),
            "type": "ir.actions.act_window",
            "res_model": self.created_record_ref._name,
            "view_mode": "form",
            "res_id": self.created_record_ref.id,
        }
