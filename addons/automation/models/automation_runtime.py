import logging
from collections import defaultdict

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
        default=lambda self: self.env.company,
        index=True,
        readonly=True,
        required=True,
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        default=lambda self: self.env.company.currency_id,
        required=True,
    )
    multicompany_id = fields.Many2one(
        comodel_name="res.company",
        string="Target Company",
        help="Target company for multi-company operations",
    )
    automation_id = fields.Many2one(
        comodel_name="automation.rule",
        index=True,
        required=True,
        ondelete="restrict",
        tracking=True,
        help="The automation workflow definition being executed",
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        index=True,
        domain=["|", ("parent_id", "=", False), ("is_company", "=", True)],
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
        default=lambda self: _("New"),
        index="trigram",
        copy=False,
        readonly=True,
        required=True,
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
        default="draft",
        copy=False,
        readonly=True,
        required=True,
        tracking=True,
        help="Workflow execution state",
    )
    date = fields.Date(
        default=fields.Date.context_today,
        required=True,
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
        copy=False,
        readonly=True,
        ondelete="cascade",
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

            rule = self.env["automation.rule"].browse(vals.get("automation_id"))
            if vals.get("name", _("New")) == _("New") and rule.run_mode == "queued":
                vals["name"] = rule.sudo().name
            elif vals.get("name", _("New")) == _("New"):
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

        self._log_run_message(
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

    def _log_run_message(self, body, subject):
        self.check_singleton()
        if not self._is_queued():
            self.message_post(body=body, subject=subject)

    def _launch(self):
        drafts = self.filtered(lambda run: run.state == "draft")
        queued = drafts.filtered(lambda run: run._is_queued())
        if queued:
            queued.with_context(tracking_disable=True)._launch_queued()
        for runtime in drafts - queued:
            runtime.action_start()
            runtime.action_run_all()

    def _launch_queued(self):
        for rule, runtimes in self.grouped("automation_id").items():
            actions = rule.action_server_ids.sorted("sequence")
            if not actions:
                raise UserError(
                    _("Automation '%s' has no server actions configured", rule.name),
                )
            runtimes.state = "in_progress"
            lines = runtimes._materialize(actions)
            lines.filtered(lambda line: not line.edge_in_ids)._settle_readiness()
            idle = runtimes.filtered(
                lambda run: not run.line_ids.filtered(lambda l: l.state == "ready"),
            )
            if runtimes - idle:
                (runtimes - idle)._request_dispatch()
            idle.line_ids.edge_in_ids.mapped("condition")
            for runtime in idle:
                runtime._settle_idle()

    def _request_dispatch(self):
        requested = self.env.cr.precommit.data
        if requested.get("automation.dispatch_requested"):
            return
        requested["automation.dispatch_requested"] = True
        self.env.ref("automation.ir_cron_data_automation_resume")._trigger()

    def _advance(self):
        open_runs = self.filtered(
            lambda run: run.state in ("in_progress", "waiting_resume"),
        )
        open_runs.line_ids.edge_in_ids.source_line_id.mapped("state")
        for runtime in open_runs:
            if not runtime._is_queued():
                runtime.state = "in_progress"
                runtime.action_run_all()
            elif runtime.line_ids.filtered(lambda l: l.state == "ready"):
                runtime.state = "in_progress"
                runtime._request_dispatch()
            else:
                runtime._settle_idle()

    def _finish_if_settled(self):
        self.line_ids.mapped("state")
        finished = self.filtered(
            lambda run: (
                run.state in ("in_progress", "waiting_resume")
                and all(line.state in SETTLED_STATES for line in run.line_ids)
            ),
        )
        for runtime in finished:
            runtime.action_done()
        return bool(finished)

    def action_cancel(self):
        runs = self.filtered(lambda run: run.state not in ("done", "cancel", "error"))
        if not runs:
            return
        runs.state = "cancel"
        runs.line_ids.filtered(
            lambda l: l.state not in SETTLED_STATES,
        ).action_cancel()
        for run in runs:
            run._log_run_message(
                body=_("Workflow cancelled"), subject=_("Workflow Cancelled")
            )

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
                if not line._contains_its_error():
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
        due = self.filtered(
            lambda run: run.state == "waiting_resume"
        ).line_ids.filtered(
            lambda step: (
                step.state in ("paused", "scheduled")
                and step.date_resume
                and step.date_resume <= now
            ),
        )
        if not due:
            return
        runtimes = due.runtime_id
        runtimes.state = "in_progress"
        due.filtered(lambda step: step.state == "paused").action_resume()
        due.filtered(lambda step: step.state == "scheduled")._settle_readiness()
        runtimes._advance()

    @api.model
    def _resume_waiting_executions(self, rules=None):
        waiting = self.search(
            [
                ("state", "=", "waiting_resume"),
                *(
                    [("automation_id", "in", rules.ids)]
                    if rules is not None
                    else [("automation_id.active", "=", True)]
                ),
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
    def _dispatch_due_steps(self, rules=None):
        self = self.with_context(tracking_disable=True)
        self._resume_waiting_executions(rules=rules)
        Line = self.env["automation.runtime.line"]
        handled = set()
        while lines := Line.search(
            [
                ("state", "=", "ready"),
                ("id", "not in", list(handled)),
                ("runtime_id.state", "in", ("in_progress", "waiting_resume")),
                ("runtime_id.automation_id.run_mode", "=", "queued"),
                *(
                    [("runtime_id.automation_id", "in", rules.ids)]
                    if rules is not None
                    else [("runtime_id.automation_id.active", "=", True)]
                ),
            ],
            order="action_id, id",
            limit=DISPATCH_BATCH_SIZE,
        ):
            handled.update(lines.ids)
            for action, grouped in lines.grouped("action_id").items():
                batch = grouped.filtered(lambda line: line.state == "ready")
                if not batch:
                    continue
                runtimes = batch.runtime_id
                runtimes.filtered(
                    lambda run: run.state == "waiting_resume"
                ).state = "in_progress"
                action._execute_runtime_lines(batch)
                runtimes.line_ids.edge_in_ids.source_line_id.mapped("state")
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
        self._log_run_message(
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
        self._log_run_message(
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
        context = self._prepare_execution_context()
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
        lines = self._materialize(actions)
        for line in lines.filtered(lambda line: not line.edge_in_ids):
            line._settle_readiness()
        return lines

    def _materialize(self, actions):
        lines = self.env["automation.runtime.line"].create(
            [
                {
                    "runtime_id": runtime.id,
                    "action_id": action.id,
                    "name": action.name,
                    "sequence": action.sequence,
                    "state": "waiting",
                }
                for runtime in self
                for action in actions
            ]
        )
        edge_vals = []
        for runtime in self:
            line_by_action = {line.action_id.id: line for line in runtime.line_ids}
            linked = {
                (edge.source_line_id.action_id.id, edge.target_line_id.action_id.id)
                for edge in runtime.edge_ids
            }
            edge_vals += [
                {
                    "runtime_id": runtime.id,
                    "source_line_id": line_by_action[edge.source_node_id.id].id,
                    "target_line_id": line_by_action[edge.target_node_id.id].id,
                    **edge._runtime_copy_vals(),
                }
                for edge in runtime.automation_id.edge_ids
                if edge.source_node_id.id in line_by_action
                and edge.target_node_id.id in line_by_action
                and (edge.source_node_id.id, edge.target_node_id.id) not in linked
            ]
        self.env["automation.runtime.edge"].create(edge_vals)
        return lines

    def _add_steps(self, actions):
        runs = self.filtered(
            lambda run: run.state in ("in_progress", "waiting_resume"),
        )
        added = runs._materialize_missing(actions)
        added._settle_readiness()
        added.runtime_id._advance()

    def _materialize_missing(self, actions):
        added = self.env["automation.runtime.line"]
        self.line_ids.fetch(["action_id"])
        missing_by_actions = defaultdict(self.browse)
        for runtime in self:
            missing = actions - runtime.line_ids.action_id
            if missing:
                missing_by_actions[missing] |= runtime
        for missing, runtimes in missing_by_actions.items():
            added |= runtimes._materialize(missing)
        return added

    def _sync_to_definition(self):
        runs = self.filtered(
            lambda run: run.state in ("in_progress", "waiting_resume"),
        )
        if not runs:
            return
        added = self.env["automation.runtime.line"]
        changed = self.env["automation.runtime.line"]
        for rule, rule_runs in runs.grouped("automation_id").items():
            added |= rule_runs._materialize_missing(rule.action_server_ids)
            definition = {
                (edge.source_node_id.id, edge.target_node_id.id): edge
                for edge in rule.edge_ids
            }
            edges_by_vals = defaultdict(self.env["automation.runtime.edge"].browse)
            pending_edges = rule_runs.edge_ids.filtered(
                lambda edge: (
                    edge.target_line_id.state in ("waiting", "scheduled", "ready")
                ),
            )
            pending_edges.fetch(
                ["source_line_id", "target_line_id", "condition", "condition_expr"]
                + ["event_code", "delay", "delay_unit"]
            )
            for runtime_edge in pending_edges:
                edge = definition.get(
                    (
                        runtime_edge.source_line_id.action_id.id,
                        runtime_edge.target_line_id.action_id.id,
                    ),
                )
                if not edge:
                    continue
                vals = {
                    name: value
                    for name, value in edge._runtime_copy_vals().items()
                    if runtime_edge[name] != value
                }
                if vals:
                    edges_by_vals[tuple(sorted(vals.items()))] |= runtime_edge
            for vals, runtime_edges in edges_by_vals.items():
                runtime_edges.write(dict(vals))
                changed |= runtime_edges.target_line_id
        runs.line_ids.filtered(
            lambda line: (
                line.state in ("waiting", "scheduled")
                or (line.state == "ready" and (line in added or line in changed))
            ),
        )._settle_readiness()
        runs._advance()

    def _get_target_record(self):
        self.check_singleton()
        if not self.res_model:
            return self.env["automation.runtime"].browse(self.id)
        return self.env[self.res_model].browse(self.res_id or [])

    def _prepare_execution_context(self):
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
