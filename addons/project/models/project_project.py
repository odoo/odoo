import json
from collections import defaultdict, deque
from datetime import datetime, time, timedelta
from typing import Any, Self

from odoo import api, fields, models
from odoo.api import ValuesType
from odoo.exceptions import UserError
from odoo.fields import Command, Domain
from odoo.libs.numbers import float_utils
from odoo.tools import SQL, LazyTranslate, formatLang, get_lang
from odoo.tools.cache_version import versioned_envelope
from odoo.tools.date_utils import localized
from odoo.tools.misc import unquote
from odoo.tools.translate import _

from ..tools import debug_log as dbg
from .project_task import CLOSED_STATES, DELIVERED_STATES
from .project_update import STATUS_COLOR
from odoo.addons.mail.tools.discuss import Store
from odoo.addons.rating.models import rating_data

_lt = LazyTranslate(__name__)


class ProjectProject(models.Model):
    _name = "project.project"
    _description = "Project"
    _inherit = [
        "mixin.analytic.plan.fields",
        "mixin.mail.activity",
        "mixin.mail.alias",
        "mixin.mail.tracking.duration",
        "mixin.portal",
        "mixin.rating.parent",
        "mixin.user.favorite",
    ]
    _order = "sequence, name, id"
    _rating_satisfaction_days = 30
    _track_duration_field = "phase_id"

    @dbg.timed
    def _compute_task_counts(self) -> None:
        closed_states = set(CLOSED_STATES)
        counts: dict[int, list[int]] = {}
        active_projects = self.filtered("active")
        for subset, active_test in (
            (active_projects, True),
            (self - active_projects, False),
        ):
            if not subset:
                continue
            ProjectTask = self.env["project.task"].with_context(active_test=active_test)
            for project, state, count in ProjectTask._read_group(  # noqa: E8507 - two queries: active and archived tasks
                Domain("project_id", "in", subset.ids)
                & Domain("is_template", "=", False),
                ["project_id", "state"],
                ["__count"],
            ):
                total = counts.setdefault(project.id, [0, 0, 0])
                total[0] += count
                total[2 if state in closed_states else 1] += count
        for project in self:
            project.task_count, project.open_task_count, project.closed_task_count = (
                counts.get(project.id, (0, 0, 0))
            )

    def _default_phase_id(self) -> int | bool:
        return self.env["project.phase"].search([], limit=1)

    company_id = fields.Many2one(
        comodel_name="res.company",
        compute="_compute_company_id",
        inverse="_inverse_company_id",
        store=True,
        readonly=False,
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        export_string_translation=False,
        compute="_compute_currency_id",
        readonly=True,
    )
    account_id = fields.Many2one(
        comodel_name="account.analytic.account",
        copy=False,
        domain="['|', ('company_id', '=', False), ('company_id', '=?', company_id)]",
        ondelete="set null",
    )
    amount_analytic_balance = fields.Monetary(related="account_id.balance")
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Customer",
        index="btree_not_null",
        domain="['|', ('company_id', '=?', company_id), ('company_id', '=', False)]",
        bypass_search_access=True,
        tracking=True,
    )
    resource_calendar_id = fields.Many2one(
        comodel_name="resource.calendar",
        string="Working Time",
        export_string_translation=False,
        compute="_compute_resource_calendar_id",
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Project Manager",
        default=lambda self: self.env.user,
        falsy_value_label=_lt("👤 Unassigned"),
        tracking=True,
    )
    alias_id = fields.Many2one(
        help="Internal email associated with this project. Incoming emails are automatically synchronized "
        "with Tasks (or optionally Issues if the Issue Tracker module is installed)."
    )

    phase_id = fields.Many2one(
        comodel_name="project.phase",
        default=_default_phase_id,
        index=True,
        copy=False,
        group_expand="_read_group_expand_full",
        ondelete="restrict",
        tracking=True,
        groups="project.group_project_stages",
    )
    phase_color = fields.Integer(
        related="phase_id.color",
        string="Phase Color",
        export_string_translation=False,
    )

    name = fields.Char(
        translate=True,
        index="trigram",
        required=True,
        tracking=True,
        default_export_compatible=True,
    )
    active = fields.Boolean(
        export_string_translation=False,
        default=True,
        copy=False,
    )
    sequence = fields.Integer(
        export_string_translation=False,
        default=10,
    )
    description = fields.Html(
        help="Description to provide more information and context about this project"
    )
    label_tasks = fields.Char(
        string="Use Tasks as",
        translate=True,
        default=lambda s: s.env._("Tasks"),
        help="Name used to refer to the tasks of your project e.g. tasks, tickets, sprints, etc...",
    )
    color = fields.Integer(
        string="Color Index",
        export_string_translation=False,
    )
    duration_tracking = fields.Json(groups="project.group_project_stages")
    date_start = fields.Date(
        string="Start Date",
        copy=False,
    )
    date_end = fields.Date(
        string="End Date",
        index=True,
        copy=False,
        tracking=True,
        help="Date on which this project ends. The timeframe defined on the "
        "project is taken into account when viewing its planning.",
    )
    date = fields.Date(
        related="date_end",
        string="Expiration Date",
        readonly=False,
    )

    privacy_visibility = fields.Selection(
        selection=[
            ("followers", "Team members only"),
            ("invited_users", "Team members and invited portal users"),
            ("employees", "All internal users"),
            ("portal", "All internal users and invited portal users"),
        ],
        string="Visibility",
        default="portal",
        required=True,
        tracking=True,
        help="Who can access the project and its tasks:\n"
        "- Team members only: the project manager and the team members.\n"
        "- Team members and invited portal users: the same, plus the portal users invited as collaborators.\n"
        "- All internal users: every internal user.\n"
        "- All internal users and invited portal users: every internal user, plus the portal users invited as collaborators.\n\n"
        "Collaborator access modes:\n"
        "- View: read the tasks and write in their chatter.\n"
        "- Edit: also create and update tasks.\n"
        "- Advanced Edit: also move tasks between steps and change their priority.\n\n"
        "Following a project or a task only subscribes to its notifications. An internal user "
        "or portal contact following a task can still read that task.",
    )
    member_user_ids = fields.Many2many(
        comodel_name="res.users",
        relation="project_project_member_user_rel",
        column1="project_id",
        column2="user_id",
        string="Team Members",
        domain=[("share", "=", False)],
        help="Internal users who can access the project when its visibility is limited to team members.",
    )
    user_has_access = fields.Boolean(
        export_string_translation=False,
        compute="_compute_user_has_access",
        search="_search_user_has_access",
    )
    access_instruction_message = fields.Char(
        export_string_translation=False,
        compute="_compute_access_instruction_message",
    )
    allow_dependencies = fields.Boolean(
        string="Task Dependencies",
        inverse="_inverse_allow_dependencies",
    )
    allow_milestones = fields.Boolean(
        string="Milestones",
        inverse="_inverse_allow_milestones",
    )
    allow_recurring_tasks = fields.Boolean(
        string="Recurring Tasks",
        inverse="_inverse_allow_recurring_tasks",
    )
    use_sprints = fields.Boolean(help="Enable time-boxed iterations for this project.")

    sprint_ids = fields.One2many(
        comodel_name="project.sprint",
        inverse_name="project_id",
        string="Sprints",
        export_string_translation=False,
    )
    active_sprint_id = fields.Many2one(
        comodel_name="project.sprint",
        export_string_translation=False,
        compute="_compute_active_sprint_id",
    )
    sprint_count = fields.Count(
        count_of="sprint_ids",
        export_string_translation=False,
    )

    tag_ids = fields.Many2many(
        comodel_name="project.tags",
        relation="project_project_project_tags_rel",
        string="Tags",
    )
    favorite_user_ids = fields.Many2many(string="Members")
    is_user_favorite = fields.Boolean(string="Show Project on Dashboard")
    workflow_step_ids = fields.Many2many(
        comodel_name="project.workflow.step",
        relation="project_workflow_step_project_rel",
        column1="project_id",
        column2="step_id",
        string="Workflow Steps",
        export_string_translation=False,
    )
    task_ids = fields.One2many(
        comodel_name="project.task",
        inverse_name="project_id",
        string="Tasks",
    )
    task_properties_definition = fields.PropertiesDefinition(string="Task Properties")
    task_count = fields.Integer(
        export_string_translation=False,
        compute="_compute_task_counts",
    )
    open_task_count = fields.Integer(
        export_string_translation=False,
        compute="_compute_task_counts",
    )
    closed_task_count = fields.Integer(
        export_string_translation=False,
        compute="_compute_task_counts",
    )
    task_completion_percentage = fields.Float(
        export_string_translation=False,
        compute="_compute_task_completion_percentage",
    )

    collaborator_ids = fields.One2many(
        comodel_name="project.collaborator",
        inverse_name="project_id",
        string="Collaborators",
        export_string_translation=False,
        copy=False,
    )
    collaborator_count = fields.Integer(
        string="# Collaborators",
        export_string_translation=False,
        compute="_compute_collaborator_count",
        compute_sudo=True,
    )

    update_ids = fields.One2many(
        comodel_name="project.update",
        inverse_name="project_id",
        export_string_translation=False,
    )
    update_count = fields.Integer(
        export_string_translation=False,
        compute="_compute_update_count",
    )
    last_update_id = fields.Many2one(
        comodel_name="project.update",
        export_string_translation=False,
        copy=False,
    )
    last_update_status = fields.Selection(
        selection=[
            ("on_track", "On Track"),
            ("at_risk", "At Risk"),
            ("off_track", "Off Track"),
            ("on_hold", "On Hold"),
            ("to_define", "Set Status"),
            ("done", "Complete"),
        ],
        export_string_translation=False,
        compute="_compute_last_update_status",
        default="to_define",
        store=True,
        readonly=False,
        required=True,
    )
    last_update_color = fields.Integer(
        export_string_translation=False,
        compute="_compute_last_update_color",
    )

    milestone_ids = fields.One2many(
        comodel_name="project.milestone",
        inverse_name="project_id",
        export_string_translation=False,
        copy=True,
    )
    milestone_count = fields.Integer(
        export_string_translation=False,
        compute="_compute_milestone_count",
        groups="project.group_project_milestone",
    )
    milestone_count_reached = fields.Integer(
        export_string_translation=False,
        compute="_compute_milestone_reached_count",
        groups="project.group_project_milestone",
    )
    is_milestone_exceeded = fields.Boolean(
        export_string_translation=False,
        compute="_compute_is_milestone_exceeded",
        search="_search_is_milestone_exceeded",
    )
    milestone_progress = fields.Integer(
        string="Milestones Reached",
        export_string_translation=False,
        compute="_compute_milestone_reached_count",
        groups="project.group_project_milestone",
    )
    next_milestone_id = fields.Many2one(
        comodel_name="project.milestone",
        export_string_translation=False,
        compute="_compute_next_milestone_indicators",
        groups="project.group_project_milestone",
    )
    can_mark_milestone_as_done = fields.Boolean(
        export_string_translation=False,
        compute="_compute_next_milestone_indicators",
        groups="project.group_project_milestone",
    )
    is_milestone_deadline_exceeded = fields.Boolean(
        export_string_translation=False,
        compute="_compute_next_milestone_indicators",
        groups="project.group_project_milestone",
    )

    benefit_ids = fields.One2many(
        comodel_name="project.benefit",
        inverse_name="project_id",
        string="Benefits",
        export_string_translation=False,
    )
    benefit_count = fields.Count(
        count_of="benefit_ids",
        export_string_translation=False,
    )

    baseline_ids = fields.One2many(
        comodel_name="project.baseline",
        inverse_name="project_id",
        string="Baselines",
        export_string_translation=False,
    )
    current_baseline_id = fields.Many2one(
        comodel_name="project.baseline",
        export_string_translation=False,
        compute="_compute_current_baseline_id",
    )

    gate_ids = fields.One2many(
        comodel_name="project.gate",
        inverse_name="project_id",
        string="Gate Reviews",
        export_string_translation=False,
    )
    gate_count = fields.Count(
        count_of="gate_ids",
        string="Gates",
        export_string_translation=False,
    )

    history_ids = fields.One2many(
        comodel_name="project.history",
        inverse_name="project_id",
        string="History Records",
        export_string_translation=False,
    )

    premortem_done = fields.Boolean(
        string="Pre-Mortem Conducted",
        help="Was a pre-mortem exercise conducted at project kickoff?",
    )
    date_premortem = fields.Date(string="Pre-Mortem Date")
    premortem_participant_ids = fields.Many2many(
        comodel_name="res.users",
        relation="project_premortem_participants_rel",
        column1="project_id",
        column2="user_id",
        string="Pre-Mortem Participants",
    )
    premortem_notes = fields.Html(
        string="Pre-Mortem Notes",
        help="'Imagine this project has failed. Why?' — capture all identified failure modes.",
    )

    retrospective_ids = fields.One2many(
        comodel_name="project.retrospective",
        inverse_name="project_id",
        string="Retrospectives",
        export_string_translation=False,
    )
    retrospective_count = fields.Integer(
        export_string_translation=False,
        compute="_compute_retrospective_count",
    )

    health_score = fields.Integer(
        export_string_translation=False,
        compute="_compute_health_indicators",
        store=True,
        help="Composite 0-100 score based on deadlines, milestones, risk, and staleness.",
    )
    health_status = fields.Selection(
        selection=[
            ("healthy", "Healthy"),
            ("attention", "Needs Attention"),
            ("warning", "Warning"),
            ("critical", "Critical"),
        ],
        string="Health",
        export_string_translation=False,
        compute="_compute_health_indicators",
        store=True,
        help="Derived from health_score: healthy (80-100), attention (60-79), warning (40-59), critical (0-39).",
    )

    risk_ids = fields.One2many(
        comodel_name="project.risk",
        inverse_name="project_id",
        string="Risks",
        export_string_translation=False,
    )
    risk_count = fields.Integer(
        export_string_translation=False,
        compute="_compute_risk_counts",
    )
    high_risk_count = fields.Integer(
        string="High/Critical Risks",
        export_string_translation=False,
        compute="_compute_risk_counts",
    )

    wip_count = fields.Integer(
        string="WIP Count",
        export_string_translation=False,
        compute="_compute_flow_metrics",
        store=True,
        help="Number of open, non-blocked tasks.",
    )
    avg_lead_time = fields.Float(
        string="Avg Lead Time (hours)",
        export_string_translation=False,
        digits=(16, 1),
        compute="_compute_flow_metrics",
        store=True,
        help="Average working hours from creation to closure (last 90 days). "
        "Includes queue wait time.",
    )
    avg_cycle_time = fields.Float(
        string="Avg Cycle Time (hours)",
        export_string_translation=False,
        digits=(16, 1),
        compute="_compute_flow_metrics",
        store=True,
        help="Average working hours from assignment to closure (last 90 days). "
        "Excludes queue wait time.",
    )
    throughput_week = fields.Float(
        string="Throughput / Week",
        export_string_translation=False,
        digits=(16, 1),
        compute="_compute_flow_metrics",
        store=True,
        help="Tasks closed per week (rolling 4-week average).",
    )
    deadline_compliance_pct = fields.Float(
        string="Deadline Compliance %",
        export_string_translation=False,
        digits=(5, 1),
        compute="_compute_flow_metrics",
        store=True,
        help="Percentage of closed tasks with deadlines that met their deadline.",
    )

    is_template = fields.Boolean(
        export_string_translation=False,
        copy=False,
    )
    show_ratings = fields.Boolean(
        export_string_translation=False,
        compute="_compute_show_ratings",
    )

    _project_date_greater = models.Constraint(
        "check(date_end >= date_start)",
        "The project's start date must be before its end date.",
    )

    @api.onchange("company_id")
    def _onchange_company_id(self) -> None:
        if (
            self.env.user.has_group("project.group_project_stages")
            and self.phase_id.company_id
            and self.phase_id.company_id != self.company_id
        ):
            self.phase_id = (
                self.env["project.phase"]
                .search(
                    [("company_id", "in", [self.company_id.id, False])],
                    order=f"sequence asc, {self.env['project.phase']._order}",
                    limit=1,
                )
                .id
            )

    @api.depends(
        "milestone_ids", "milestone_ids.is_reached", "milestone_ids.date_deadline"
    )
    def _compute_next_milestone_indicators(self) -> None:
        milestones_per_project_id = {
            project.id: milestones
            for project, milestones in self.env["project.milestone"]._read_group(
                [("project_id", "in", self.ids), ("is_reached", "=", False)],
                ["project_id"],
                ["id:recordset"],
            )
        }
        milestones = self.env["project.milestone"].concat(
            *milestones_per_project_id.values()
        )
        task_read_group = self.env["project.task"]._read_group(
            [("milestone_id", "in", milestones.ids)],
            ["milestone_id", "state"],
            ["__count"],
        )
        task_count_per_milestones = defaultdict(lambda: (0, 0))
        for milestone, state, count in task_read_group:
            opened_task_count, closed_task_count = task_count_per_milestones[
                milestone.id
            ]
            if state in CLOSED_STATES:
                closed_task_count += count
            else:
                opened_task_count += count
            task_count_per_milestones[milestone.id] = (
                opened_task_count,
                closed_task_count,
            )
        for project in self:
            milestones = milestones_per_project_id.get(
                project.id, self.env["project.milestone"]
            )
            project.next_milestone_id = milestones[:1]
            milestone_deadline_exceeded = False
            milestone_marked_as_done = False
            for m in milestones:
                opened_task_count, closed_task_count = task_count_per_milestones[m.id]
                if (
                    not milestone_deadline_exceeded
                    and m.is_deadline_exceeded
                    and (opened_task_count > 0 or closed_task_count == 0)
                ):
                    milestone_deadline_exceeded = True
                    break
                if (
                    not milestone_marked_as_done
                    and opened_task_count == 0
                    and closed_task_count > 0
                ):
                    milestone_marked_as_done = True
            project.is_milestone_deadline_exceeded = milestone_deadline_exceeded
            project.can_mark_milestone_as_done = milestone_marked_as_done

    @api.depends("sprint_ids", "sprint_ids.state")
    def _compute_active_sprint_id(self) -> None:
        for project in self:
            project.active_sprint_id = project.sprint_ids.filtered(
                lambda s: s.state == "active"
            )[:1]

    @api.depends("baseline_ids", "baseline_ids.is_current")
    def _compute_current_baseline_id(self) -> None:
        for project in self:
            project.current_baseline_id = project.baseline_ids.filtered("is_current")[
                :1
            ]

    def action_archive_to_history(self) -> None:
        self.check_singleton()
        dbg.lifecycle.debug("project.project.action_archive_to_history %s", self.id)
        self.env["project.history"].create_from_project(self)

    @dbg.timed
    def action_compute_critical_path(self) -> None:
        self.check_singleton()
        tasks = self.env["project.task"].search(
            [
                ("project_id", "=", self.id),
                ("is_template", "=", False),
                ("state", "not in", list(CLOSED_STATES)),
            ]
        )
        dbg.pipeline.debug(
            "[project:%s] critical path: %d open tasks", self.id, len(tasks)
        )
        if not tasks:
            return

        task_set = set(tasks.ids)
        deps_on, successors_of = self._get_cpm_predecessors_and_successors(
            tasks, task_set
        )
        duration = {t.id: t._get_cpm_duration_hours() for t in tasks}
        dbg.pipeline.debug(
            "[project:%s] critical path: %s edges, total duration %s h",
            self.id,
            dbg.lazy(lambda: sum(len(preds) for preds in deps_on.values())),
            dbg.lazy(lambda: f"{sum(duration.values()):.2f}"),
        )
        self._check_no_cyclic_dependencies(task_set, deps_on)
        topo = self._get_cpm_topological_order(task_set, deps_on, successors_of)
        es, ef = self._get_cpm_earliest_start_and_finish(topo, deps_on, duration)
        project_end = max(ef.values()) if ef else 0.0
        ls_map = self._get_cpm_latest_start(
            topo, deps_on, successors_of, duration, project_end
        )
        dbg.logic.debug(
            "[project:%s] critical path: end=%.2f h, critical tasks %s",
            self.id,
            project_end,
            dbg.lazy(
                lambda: [tid for tid in topo if abs(ls_map[tid] - es[tid]) < 0.01]
            ),
        )
        self._update_cpm_schedule(tasks, es, ef, ls_map)

    def _get_cpm_predecessors_and_successors(
        self, tasks: Any, task_set: set[int]
    ) -> tuple[dict[int, list[tuple[int, str, float]]], dict[int, list[int]]]:
        deps_on: dict[int, list[tuple[int, str, float]]] = defaultdict(list)
        successors_of: dict[int, list[int]] = defaultdict(list)
        seen_edges: set[tuple[int, int]] = set()

        def add_edge(tid, pred_id, dtype, lag) -> None:
            if tid not in task_set or pred_id not in task_set:
                return
            if (tid, pred_id) in seen_edges:
                return
            seen_edges.add((tid, pred_id))
            deps_on[tid].append((pred_id, dtype, lag))
            successors_of[pred_id].append(tid)

        for dep in self.env["project.task.dependency"].search(
            [("project_id", "=", self.id)]
        ):
            add_edge(
                dep.task_id.id,
                dep.depends_on_id.id,
                dep.dependency_type,
                dep.lag_hours,
            )
        for task in tasks:
            for pred in task.predecessor_ids:
                add_edge(task.id, pred.id, "fs", 0.0)
        return deps_on, successors_of

    def _check_no_cyclic_dependencies(
        self, task_set: set[int], deps_on: dict[int, list[tuple[int, str, float]]]
    ) -> None:
        _UNVISITED, _IN_STACK, _DONE = 0, 1, 2
        color = dict.fromkeys(task_set, _UNVISITED)
        for root in task_set:
            if color[root] != _UNVISITED:
                continue
            dfs_stack: list[tuple[int, int]] = [(root, 0)]
            while dfs_stack:
                node, idx = dfs_stack[-1]
                color[node] = _IN_STACK
                preds = deps_on[node]
                if idx < len(preds):
                    dfs_stack[-1] = (node, idx + 1)
                    pred_id = preds[idx][0]
                    if color.get(pred_id) == _IN_STACK:
                        raise UserError(
                            self.env._(
                                "A dependency cycle was detected among the tasks "
                                "of project %(project)s. Resolve the circular "
                                "dependency before computing the critical path.",
                                project=self.display_name,
                            )
                        )
                    if color.get(pred_id, _UNVISITED) == _UNVISITED:
                        dfs_stack.append((pred_id, 0))
                else:
                    color[node] = _DONE
                    dfs_stack.pop()

    def _get_cpm_topological_order(
        self,
        task_set: set[int],
        deps_on: dict[int, list[tuple[int, str, float]]],
        successors_of: dict[int, list[int]],
    ) -> list[int]:
        indegree = {tid: len(deps_on[tid]) for tid in task_set}
        ready = deque(sorted(tid for tid in task_set if indegree[tid] == 0))
        topo: list[int] = []
        while ready:
            tid = ready.popleft()
            topo.append(tid)
            for succ_id in successors_of[tid]:
                indegree[succ_id] -= 1
                if indegree[succ_id] == 0:
                    ready.append(succ_id)
        return topo

    def _get_cpm_earliest_start_and_finish(
        self,
        topo: list[int],
        deps_on: dict[int, list[tuple[int, str, float]]],
        duration: dict[int, float],
    ) -> tuple[dict[int, float], dict[int, float]]:
        es: dict[int, float] = {}
        ef: dict[int, float] = {}
        for tid in topo:
            preds = deps_on[tid]
            if not preds:
                es[tid] = 0.0
                ef[tid] = duration[tid]
                continue
            max_es = 0.0
            max_ef_constraint = 0.0
            has_ef_constraint = False
            for pred_id, dtype, lag in preds:
                if dtype == "fs":
                    max_es = max(max_es, ef[pred_id] + lag)
                elif dtype == "ss":
                    max_es = max(max_es, es[pred_id] + lag)
                elif dtype == "ff":
                    max_ef_constraint = max(max_ef_constraint, ef[pred_id] + lag)
                    has_ef_constraint = True
                elif dtype == "sf":
                    max_ef_constraint = max(max_ef_constraint, es[pred_id] + lag)
                    has_ef_constraint = True
            if has_ef_constraint:
                max_es = max(max_es, max_ef_constraint - duration[tid])
            es[tid] = max_es
            ef[tid] = es[tid] + duration[tid]
        return es, ef

    def _get_cpm_latest_start(
        self,
        topo: list[int],
        deps_on: dict[int, list[tuple[int, str, float]]],
        successors_of: dict[int, list[int]],
        duration: dict[int, float],
        project_end: float,
    ) -> dict[int, float]:
        lf: dict[int, float] = {}
        ls_map: dict[int, float] = {}
        for tid in reversed(topo):
            lf[tid] = project_end
            for succ_id in successors_of[tid]:
                for pred_id, dtype, lag in deps_on[succ_id]:
                    if pred_id != tid:
                        continue
                    if dtype == "fs":
                        lf[tid] = min(lf[tid], ls_map[succ_id] - lag)
                    elif dtype == "ss":
                        lf[tid] = min(lf[tid], ls_map[succ_id] - lag + duration[tid])
                    elif dtype == "ff":
                        lf[tid] = min(lf[tid], lf[succ_id] - lag)
                    elif dtype == "sf":
                        lf[tid] = min(lf[tid], lf[succ_id] - lag + duration[tid])
            ls_map[tid] = lf[tid] - duration[tid]
        return ls_map

    def _update_cpm_schedule(
        self,
        tasks: Any,
        es: dict[int, float],
        ef: dict[int, float],
        ls_map: dict[int, float],
    ) -> None:
        calendar = self.resource_calendar_id
        now = fields.Datetime.now()

        def hours_to_datetime(hours):
            if not hours:
                return now
            if calendar:
                return calendar.plan_hours(hours, now)
            return now + timedelta(hours=hours)

        tasks_by_vals = defaultdict(lambda: self.env["project.task"])
        vals_by_key = {}
        for task in tasks:
            tid = task.id
            es_h = es.get(tid, 0.0)
            ls_h = ls_map.get(tid, 0.0)
            total_fl = ls_h - es_h
            cpm_start = hours_to_datetime(es_h)
            vals = {
                "cpm_date_earliest_start": cpm_start,
                "cpm_date_latest_start": hours_to_datetime(ls_h),
                "total_float": total_fl,
                "is_critical_path": abs(total_fl) < 0.01,
                "cpm_date_start": cpm_start,
                "cpm_date_end": hours_to_datetime(ef.get(tid, 0.0)),
            }
            key = repr(sorted(vals.items()))
            tasks_by_vals[key] |= task
            vals_by_key[key] = vals
        dbg.performance.debug(
            "_update_cpm_schedule [project:%s]: %d tasks in %d write groups",
            self.id,
            len(tasks),
            len(tasks_by_vals),
        )
        for key, group in tasks_by_vals.items():
            group.write(vals_by_key[key])

    def _get_levelling_day_capacity(
        self, calendar: Any, date_start: Any, date_end: Any
    ) -> dict:
        per_day: dict = defaultdict(float)
        if calendar:
            intervals = calendar._work_intervals_batch(
                localized(date_start), localized(date_end)
            )[False]
            for start, stop, _recs in intervals:
                per_day[start.date()] += (stop - start).total_seconds() / 3600.0
        else:
            day = date_start.date()
            while day <= date_end.date():
                per_day[day] = 8.0
                day += timedelta(days=1)
        return per_day

    @staticmethod
    def _get_levelling_spread(slot: tuple, day_capacity: dict) -> dict:
        start, stop, hours, _task_id = slot
        days = {
            day: capacity
            for day, capacity in day_capacity.items()
            if start.date() <= day <= stop.date() and capacity
        }
        total = sum(days.values())
        if not total:
            return {}
        return {day: hours * capacity / total for day, capacity in days.items()}

    @dbg.timed
    def action_level_resources(self) -> None:
        self.check_singleton()
        dbg.pipeline.debug("[project:%s] level resources -> critical path", self.id)
        self.action_compute_critical_path()

        calendar = self.resource_calendar_id
        tasks = self.env["project.task"].search(
            [
                ("project_id", "=", self.id),
                ("is_template", "=", False),
                ("state", "not in", list(CLOSED_STATES)),
                ("cpm_date_start", "!=", False),
                ("cpm_date_end", "!=", False),
            ]
        )
        if not tasks:
            return

        leveling_order = sorted(
            tasks.filtered(lambda t: not t.is_critical_path),
            key=lambda t: -(t.total_float or 0.0),
        )
        dbg.logic.debug(
            "[project:%s] level resources: %d tasks, %d non-critical to level",
            self.id,
            len(tasks),
            len(leveling_order),
        )

        def get_load_per_assignee(task) -> float:
            hours = task.allocated_hours or task.planned_hours or 0.0
            return hours / max(len(task.user_ids), 1)

        user_slots: dict[int, list[tuple]] = defaultdict(list)
        for task in tasks:
            share = get_load_per_assignee(task)
            for user in task.user_ids:
                user_slots[user.id].append(
                    (
                        task.cpm_date_start,
                        task.cpm_date_end,
                        share,
                        task.id,
                    )
                )

        window_start = min(tasks.mapped("cpm_date_start"))
        window_end = max(tasks.mapped("cpm_date_end"))
        day_capacity_per_calendar: dict = {}

        def get_day_capacity(user):
            user_calendar = user.resource_calendar_id or calendar
            if user_calendar.id not in day_capacity_per_calendar:
                day_capacity_per_calendar[user_calendar.id] = (
                    self._get_levelling_day_capacity(
                        user_calendar, window_start, window_end
                    )
                )
            return day_capacity_per_calendar[user_calendar.id]

        for task in leveling_order:
            task_share = get_load_per_assignee(task)
            if not task.user_ids or not task_share:
                continue
            for user in task.user_ids:
                slots = user_slots[user.id]
                overlapping = [
                    s
                    for s in slots
                    if s[3] != task.id
                    and s[0] < task.cpm_date_end
                    and s[1] > task.cpm_date_start
                ]
                if not overlapping:
                    continue
                capacity_by_day = get_day_capacity(user)
                load_by_day: dict = defaultdict(float)
                for slot in [
                    *overlapping,
                    (task.cpm_date_start, task.cpm_date_end, task_share, task.id),
                ]:
                    for day, hours in self._get_levelling_spread(
                        slot, capacity_by_day
                    ).items():
                        load_by_day[day] += hours
                candidate_days = [
                    day
                    for day in load_by_day
                    if task.cpm_date_start.date() <= day <= task.cpm_date_end.date()
                ]
                if not any(
                    float_utils.float_compare(
                        load_by_day[day],
                        capacity_by_day.get(day, 0.0),
                        precision_digits=2,
                    )
                    > 0
                    for day in candidate_days
                ):
                    continue
                latest_end = max(
                    (s[1] for s in overlapping), default=task.cpm_date_start
                )
                max_shift_hours = task.total_float or 0.0
                if not latest_end:
                    continue
                new_start = (
                    calendar.plan_hours(0.0, latest_end) if calendar else latest_end
                )
                shift_hours = (
                    calendar.get_work_duration_data(
                        task.cpm_date_start, new_start, compute_leaves=True
                    )["hours"]
                    if calendar and new_start > task.cpm_date_start
                    else (new_start - task.cpm_date_start).total_seconds() / 3600
                )
                dbg.logic.debug(
                    "level resources %s: user %s overloaded, shift %.2f h "
                    "(float %.2f h) -> %s",
                    dbg.rec(task),
                    user.id,
                    shift_hours,
                    max_shift_hours,
                    "shift" if 0 < shift_hours <= max_shift_hours else "keep",
                )
                if 0 < shift_hours <= max_shift_hours:
                    new_end = (
                        calendar.plan_hours(task._get_cpm_duration_hours(), new_start)
                        if calendar
                        else new_start + (task.cpm_date_end - task.cpm_date_start)
                    )
                    user_slots[user.id] = [s for s in slots if s[3] != task.id] + [
                        (new_start, new_end, task_share, task.id)
                    ]
                    task.write(
                        {
                            "cpm_date_start": new_start,
                            "cpm_date_end": new_end,
                        }
                    )

    @api.depends("retrospective_ids")
    def _compute_retrospective_count(self) -> None:
        retro_data = self.env["project.retrospective"]._read_group(
            [("project_id", "in", self.ids)],
            ["project_id"],
            ["__count"],
        )
        counts = {project.id: count for project, count in retro_data}
        for project in self:
            project.retrospective_count = counts.get(project.id, 0)

    @dbg.timed
    def _compute_health_indicators(self) -> None:
        if not self.ids:
            self.health_score = 100
            self.health_status = "healthy"
            return

        now = self.env.cr.now()
        today = now.date()

        self.env["project.task"].flush_model(
            [
                "project_id",
                "state",
                "date_end",
                "date_last_status_change",
                "create_date",
                "is_template",
                "active",
            ]
        )
        self.env["project.milestone"].flush_model(
            ["project_id", "is_reached", "date_deadline"]
        )
        self.env["project.risk"].flush_model(["project_id", "risk_score", "active"])

        self.env.cr.execute(
            SQL(
                """
            SELECT
                t.project_id,
                -- Schedule: pct of open tasks with deadline that are not overdue
                CASE
                    WHEN COUNT(*) FILTER (
                        WHERE t.state NOT IN %(closed_states)s
                          AND t.date_end IS NOT NULL
                    ) = 0 THEN 100.0
                    ELSE 100.0 * COUNT(*) FILTER (
                        WHERE t.state NOT IN %(closed_states)s
                          AND t.date_end IS NOT NULL
                          AND t.date_end >= %(now)s
                    ) / NULLIF(COUNT(*) FILTER (
                        WHERE t.state NOT IN %(closed_states)s
                          AND t.date_end IS NOT NULL
                    ), 0)
                END AS schedule_score,
                -- Staleness: pct of open tasks not rotting
                CASE
                    WHEN COUNT(*) FILTER (
                        WHERE t.state NOT IN %(closed_states)s
                    ) = 0 THEN 100.0
                    ELSE 100.0 * COUNT(*) FILTER (
                        WHERE t.state NOT IN %(closed_states)s
                          AND COALESCE(t.date_last_status_change, t.create_date)
                              >= %(now)s - INTERVAL '14 days'
                    ) / NULLIF(COUNT(*) FILTER (
                        WHERE t.state NOT IN %(closed_states)s
                    ), 0)
                END AS staleness_score
            FROM project_task t
            WHERE t.project_id IN %(project_ids)s
              AND t.is_template IS NOT TRUE
              AND t.active = TRUE
            GROUP BY t.project_id
            """,
                project_ids=tuple(self.ids),
                closed_states=tuple(CLOSED_STATES),
                now=now,
            )
        )
        task_scores = {row[0]: (row[1], row[2]) for row in self.env.cr.fetchall()}

        milestone_scores: dict[int, float] = {}
        if self.ids:
            self.env.cr.execute(
                SQL(
                    """
                SELECT
                    project_id,
                    CASE
                        WHEN COUNT(*) = 0 THEN 100.0
                        ELSE 100.0 * COUNT(*) FILTER (
                            WHERE is_reached
                               OR date_deadline IS NULL
                               OR date_deadline >= %(today)s
                        ) / COUNT(*)
                    END AS milestone_score
                FROM project_milestone
                WHERE project_id IN %(project_ids)s
                GROUP BY project_id
                """,
                    project_ids=tuple(self.ids),
                    today=today,
                )
            )
            milestone_scores = {row[0]: row[1] for row in self.env.cr.fetchall()}

        risk_data: dict[int, int] = {}
        if self.ids:
            self.env.cr.execute(
                SQL(
                    """
                SELECT project_id, COALESCE(SUM(risk_score), 0)
                FROM project_risk
                WHERE project_id IN %(project_ids)s AND active = TRUE
                  AND state != %(excluded_state)s
                GROUP BY project_id
                """,
                    project_ids=tuple(self.ids),
                    excluded_state=self._LIVE_RISK_STATE_EXCLUDED,
                )
            )
            risk_data = dict(self.env.cr.fetchall())

        for project in self:
            schedule, staleness = task_scores.get(project.id, (100.0, 100.0))
            milestone = milestone_scores.get(project.id, 100.0)
            total_risk = risk_data.get(project.id, 0)
            risk_health = max(0.0, 100.0 - total_risk * 2)

            score = int((schedule + staleness + milestone + risk_health) / 4)
            dbg.logic.debug(
                "health [project:%s]: schedule=%.1f staleness=%.1f milestone=%.1f "
                "risk=%.1f -> %d",
                project.id,
                schedule,
                staleness,
                milestone,
                risk_health,
                score,
            )
            project.health_score = max(0, min(100, score))
            if score >= 80:
                project.health_status = "healthy"
            elif score >= 60:
                project.health_status = "attention"
            elif score >= 40:
                project.health_status = "warning"
            else:
                project.health_status = "critical"

    _LIVE_RISK_STATE_EXCLUDED = "resolved"

    @dbg.timed
    @api.depends("risk_ids", "risk_ids.risk_level", "risk_ids.active", "risk_ids.state")
    def _compute_risk_counts(self) -> None:
        if not self.ids:
            self.risk_count = 0
            self.high_risk_count = 0
            return
        risk_data = self.env["project.risk"]._read_group(
            [
                ("project_id", "in", self.ids),
                ("active", "=", True),
                ("state", "!=", self._LIVE_RISK_STATE_EXCLUDED),
            ],
            ["project_id", "risk_level"],
            ["__count"],
        )
        counts: dict[int, tuple[int, int]] = {}
        for project, risk_level, count in risk_data:
            total, high = counts.get(project.id, (0, 0))
            total += count
            if risk_level in ("high", "critical"):
                high += count
            counts[project.id] = (total, high)
        for project in self:
            total, high = counts.get(project.id, (0, 0))
            project.risk_count = total
            project.high_risk_count = high

    @dbg.timed
    def _compute_flow_metrics(self) -> None:
        if not self.ids:
            self.wip_count = 0
            self.avg_lead_time = 0.0
            self.avg_cycle_time = 0.0
            self.throughput_week = 0.0
            self.deadline_compliance_pct = 0.0
            return

        now = self.env.cr.now()

        self.env["project.task"].flush_model(
            [
                "project_id",
                "state",
                "date_closed",
                "date_end",
                "lead_time_hours",
                "cycle_time_hours",
                "is_template",
                "active",
            ]
        )

        self.env.cr.execute(
            SQL(
                """
            SELECT
                project_id,
                -- WIP: open non-blocked tasks
                COUNT(*) FILTER (
                    WHERE state NOT IN %(wip_excluded_states)s
                ) AS wip_count,
                -- Avg lead time: create→close (closed in last 90 days).
                -- NOTE: date_closed is the actual completion timestamp; date_end
                -- is the (renamed) deadline. Rolling windows must key off closure.
                AVG(lead_time_hours) FILTER (
                    WHERE state IN %(delivered_states)s
                      AND date_closed >= %(now)s - INTERVAL '90 days'
                      AND lead_time_hours > 0
                ) AS avg_lead_time,
                -- Avg cycle time: assign→close (closed in last 90 days)
                AVG(cycle_time_hours) FILTER (
                    WHERE state IN %(delivered_states)s
                      AND date_closed >= %(now)s - INTERVAL '90 days'
                      AND cycle_time_hours > 0
                ) AS avg_cycle_time,
                -- Throughput: tasks closed in last 28 days / 4
                COUNT(*) FILTER (
                    WHERE state IN %(delivered_states)s
                      AND date_closed >= %(now)s - INTERVAL '28 days'
                ) / 4.0 AS throughput_week,
                -- Deadline compliance: pct of deadline-having closed tasks whose
                -- actual closure (date_closed) landed on or before the deadline.
                CASE
                    WHEN COUNT(*) FILTER (
                        WHERE state IN %(delivered_states)s
                          AND date_end IS NOT NULL
                          AND date_closed IS NOT NULL
                    ) = 0 THEN 0.0
                    ELSE 100.0 * COUNT(*) FILTER (
                        WHERE state IN %(delivered_states)s
                          AND date_end IS NOT NULL
                          AND date_closed IS NOT NULL
                          AND date_closed <= date_end
                    ) / COUNT(*) FILTER (
                        WHERE state IN %(delivered_states)s
                          AND date_end IS NOT NULL
                          AND date_closed IS NOT NULL
                    )
                END AS deadline_compliance_pct
            FROM project_task
            WHERE project_id IN %(project_ids)s
              -- is_template has no default, so it is NULL (not FALSE) for normal
              -- tasks; `= FALSE` would wrongly exclude every non-template task.
              AND is_template IS NOT TRUE
              AND active = TRUE
            GROUP BY project_id
            """,
                project_ids=tuple(self.ids),
                delivered_states=DELIVERED_STATES,
                wip_excluded_states=(*CLOSED_STATES, "blocked"),
                now=now,
            )
        )
        results = {row[0]: row[1:] for row in self.env.cr.fetchall()}
        for project in self:
            wip, avg_lt, avg_ct, tp, dcp = results.get(
                project.id, (0, 0.0, 0.0, 0.0, 0.0)
            )
            dbg.logic.debug(
                "flow [project:%s]: wip=%s lead=%s cycle=%s throughput=%s "
                "deadline_pct=%s",
                project.id,
                wip,
                avg_lt,
                avg_ct,
                tp,
                dcp,
            )
            project.wip_count = wip or 0
            project.avg_lead_time = avg_lt or 0.0
            project.avg_cycle_time = avg_ct or 0.0
            project.throughput_week = tp or 0.0
            project.deadline_compliance_pct = dcp or 0.0

    _SNAPSHOT_METRIC_FIELDS = (
        "health_score",
        "health_status",
        "wip_count",
        "avg_lead_time",
        "avg_cycle_time",
        "throughput_week",
        "deadline_compliance_pct",
    )

    @dbg.timed
    def _reset_metrics(self) -> None:
        dbg.lifecycle.debug("project.project._reset_metrics %s", dbg.rec(self))
        for fname in self._SNAPSHOT_METRIC_FIELDS:
            self.env.add_to_compute(self._fields[fname], self)
        self.env.flush_all()

    @api.model
    def _cron_reset_metrics(self) -> None:
        projects = self.search([])
        dbg.lifecycle.debug(
            "project.project._cron_reset_metrics: %d projects", len(projects)
        )
        projects._reset_metrics()
        dbg.lifecycle.debug("project.project._cron_reset_metrics: done")

    def action_reset_metrics(self) -> bool:
        self._reset_metrics()
        return True

    def _compute_access_url(self) -> None:
        super()._compute_access_url()
        for project in self:
            project.access_url = f"/my/projects/{project.id}"

    @api.depends("account_id.company_id", "partner_id.company_id")
    def _compute_company_id(self) -> None:
        for project in self:
            if project.account_id.company_id:
                project.company_id = project.account_id.company_id
            if not project.company_id and project.partner_id.company_id:
                project.company_id = project.partner_id.company_id

    @api.depends_context("company")
    @api.depends("company_id", "company_id.resource_calendar_id")
    def _compute_resource_calendar_id(self) -> None:
        for project in self:
            project.resource_calendar_id = (
                project.company_id.resource_calendar_id
                or self.env.company.resource_calendar_id
            )

    def _inverse_company_id(self) -> None:
        for project in self:
            account = project.account_id
            if (
                project.partner_id
                and project.partner_id.company_id
                and project.company_id
                and project.company_id != project.partner_id.company_id
            ):
                raise UserError(
                    _(
                        "The project and the associated partner must be linked to the same company."
                    )
                )
            if not account or not account.company_id:
                continue
            dbg.logic.debug(
                "_inverse_company_id [project:%s]: company %s -> %s, account %s "
                "(projects=%s, has lines=%s)",
                project.id,
                account.company_id.id,
                project.company_id.id,
                account.id,
                account.project_count,
                bool(account.line_ids),
            )
            if (
                account.project_count > 1 or account.line_ids
            ) and project.company_id != account.company_id:
                raise UserError(
                    _(
                        "The project's company cannot be changed if its analytic account has analytic lines or if more than one project is linked to it."
                    )
                )
            account.company_id = project.company_id or project.partner_id.company_id

    @api.depends("last_update_id.status")
    def _compute_last_update_status(self) -> None:
        for project in self:
            project.last_update_status = project.last_update_id.status or "to_define"

    @api.depends("last_update_status")
    def _compute_last_update_color(self) -> None:
        for project in self:
            project.last_update_color = STATUS_COLOR[project.last_update_status]

    @api.depends("milestone_ids")
    def _compute_milestone_count(self) -> None:
        read_group = self.env["project.milestone"]._read_group(
            [("project_id", "in", self.ids)], ["project_id"], ["__count"]
        )
        mapped_count = {project.id: count for project, count in read_group}
        for project in self:
            project.milestone_count = mapped_count.get(project.id, 0)

    @api.depends("milestone_ids.is_reached", "milestone_count")
    def _compute_milestone_reached_count(self) -> None:
        read_group = self.env["project.milestone"]._read_group(
            [("project_id", "in", self.ids), ("is_reached", "=", True)],
            ["project_id"],
            ["__count"],
        )
        mapped_count = {project.id: count for project, count in read_group}
        for project in self:
            project.milestone_count_reached = mapped_count.get(project.id, 0)
            project.milestone_progress = (
                project.milestone_count
                and project.milestone_count_reached * 100 // project.milestone_count
            )

    @api.depends(
        "milestone_ids",
        "milestone_ids.is_reached",
        "milestone_ids.date_deadline",
        "allow_milestones",
    )
    def _compute_is_milestone_exceeded(self) -> None:
        today = fields.Date.context_today(self)
        read_group = self.env["project.milestone"]._read_group(
            [
                ("project_id", "in", self.filtered("allow_milestones").ids),
                ("is_reached", "=", False),
                ("date_deadline", "<=", today),
            ],
            ["project_id"],
            ["__count"],
        )
        mapped_count = {project.id: count for project, count in read_group}
        for project in self:
            project.is_milestone_exceeded = bool(mapped_count.get(project.id))

    @api.depends_context("company")
    @api.depends("company_id")
    def _compute_currency_id(self) -> None:
        default_currency_id = self.env.company.currency_id
        for project in self:
            project.currency_id = project.company_id.currency_id or default_currency_id

    @api.model
    def _search_is_milestone_exceeded(self, operator: str, value: Any) -> list:
        if operator != "in":
            return NotImplemented

        sql = SQL("""(
            SELECT P.id
              FROM project_project P
         LEFT JOIN project_milestone M ON P.id = M.project_id
             WHERE M.is_reached IS false
               AND P.allow_milestones IS true
               AND M.date_deadline <= CAST(now() AS date)
        )""")
        return [("id", "any", sql)]

    @api.depends("collaborator_ids", "privacy_visibility")
    def _compute_collaborator_count(self) -> None:
        project_sharings = self.filtered(
            lambda project: project.privacy_visibility in ["invited_users", "portal"]
        )
        collaborator_read_group = self.env["project.collaborator"]._read_group(
            [("project_id", "in", project_sharings.ids)],
            ["project_id"],
            ["__count"],
        )
        collaborator_count_by_project = {
            project.id: count for project, count in collaborator_read_group
        }
        for project in self:
            project.collaborator_count = collaborator_count_by_project.get(
                project.id, 0
            )

    @api.depends_context("uid")
    @api.depends("privacy_visibility", "member_user_ids", "user_id", "collaborator_ids")
    def _compute_user_has_access(self) -> None:
        accessible = set(
            self.sudo()
            .with_context(active_test=False)
            ._search([("id", "in", self._origin.ids), ("user_has_access", "=", True)])
        )
        for project in self:
            project.user_has_access = project._origin.id in accessible

    def _search_user_has_access(self, operator: str, value: Any) -> Domain:
        if operator not in ("in", "not in"):
            return NotImplemented
        accessible = self._get_domain_user_access()
        return accessible if (operator == "in") == (True in value) else ~accessible

    def _get_domain_user_access(self) -> Domain:
        user = self.env.user
        if user.share:
            collaborations = (
                self.env["project.collaborator"]
                .sudo()
                ._search([("partner_id", "=", user.partner_id.id)])
            )
            return Domain(
                "privacy_visibility", "in", ["invited_users", "portal"]
            ) & Domain("id", "in", collaborations.subselect("project_id"))
        return (
            Domain("privacy_visibility", "in", ["employees", "portal"])
            | Domain("member_user_ids", "in", user.id)
            | Domain("user_id", "=", user.id)
        )

    @api.depends("privacy_visibility")
    def _compute_access_instruction_message(self) -> None:
        for project in self:
            if project.privacy_visibility == "portal":
                project.access_instruction_message = self.env._(
                    "Every internal user can access the project. Invite portal users as collaborators to give them access."
                )
            elif project.privacy_visibility == "followers":
                project.access_instruction_message = self.env._(
                    "Only the project manager and the team members can access the project."
                )
            elif project.privacy_visibility == "invited_users":
                project.access_instruction_message = self.env._(
                    "Only the project manager and the team members can access the project, plus the portal users invited as collaborators."
                )
            else:
                project.access_instruction_message = ""

    @api.depends("update_ids")
    def _compute_update_count(self) -> None:
        update_count_per_project = dict(
            self.env["project.update"]._read_group(
                [("project_id", "in", self.ids)],
                ["project_id"],
                ["id:count"],
            )
        )
        for project in self:
            project.update_count = update_count_per_project.get(project, 0)

    @api.depends("workflow_step_ids.rating_active")
    def _compute_show_ratings(self) -> None:
        projects_with_rating_active = (
            self.env["project.workflow.step"]
            .search_fetch(
                domain=[
                    ("project_ids", "in", self.ids),
                    ("rating_active", "=", True),
                ],
                field_names=["project_ids"],
            )
            .project_ids
        )
        for project in self:
            project.show_ratings = project in projects_with_rating_active

    @dbg.timed
    def _inverse_allow_dependencies(self) -> None:
        project_with_task_dependencies_feature = self.filtered("allow_dependencies")
        projects_without_task_dependencies_feature = (
            self - project_with_task_dependencies_feature
        )
        ProjectTask = self.env["project.task"]
        if project_with_task_dependencies_feature and (
            open_tasks_with_dependencies := ProjectTask.search(
                [
                    (
                        "project_id",
                        "in",
                        project_with_task_dependencies_feature.ids,
                    ),
                    ("predecessor_ids.state", "in", ProjectTask.OPEN_STATES),
                    ("state", "in", ProjectTask.OPEN_STATES),
                ]
            )
        ):
            dbg.logic.debug(
                "_inverse_allow_dependencies: blocking %s",
                dbg.rec(open_tasks_with_dependencies),
            )
            open_tasks_with_dependencies.state = "blocked"
        if projects_without_task_dependencies_feature and (
            waiting_tasks := ProjectTask.search(
                [
                    (
                        "project_id",
                        "in",
                        projects_without_task_dependencies_feature.ids,
                    ),
                    ("state", "=", "blocked"),
                ]
            )
        ):
            dbg.logic.debug(
                "_inverse_allow_dependencies: unblocking %s", dbg.rec(waiting_tasks)
            )
            waiting_tasks.state = "in_progress"
        res = self._sync_feature_group_to_usage(
            "allow_dependencies", "project.group_project_task_dependencies"
        )
        if res or res is False:
            self.env.ref("project.mt_task_waiting").sudo().hidden = not res
            self.env.ref("project.mt_project_task_waiting").sudo().hidden = not res

    def _inverse_allow_milestones(self) -> None:
        self._sync_feature_group_to_usage(
            "allow_milestones", "project.group_project_milestone"
        )

    def _inverse_allow_recurring_tasks(self) -> None:
        self._sync_feature_group_to_usage(
            "allow_recurring_tasks", "project.group_project_recurring_tasks"
        )

    @api.model
    def _prepare_map_tasks_defaults(self, project: Self) -> dict:
        return {
            "state": "in_progress",
            "company_id": project.company_id.id,
            "project_id": project.id,
        }

    @dbg.timed
    def map_tasks(self, new_project_id: int) -> bool:
        project = self.browse(new_project_id)
        tasks = (
            self.env["project.task"]
            .with_context(active_test=False)
            .search([("project_id", "=", self.id), ("parent_id", "=", False)])
        )
        dbg.pipeline.debug(
            "[project:%s] map_tasks -> %s: %d root tasks",
            self.id,
            project.id,
            len(tasks),
        )
        if self.allow_dependencies and "task_mapping" not in self.env.context:
            self = self.with_context(task_mapping={})
        defaults = self._prepare_map_tasks_defaults(project)
        new_tasks = tasks.with_context(copy_project=True).copy(defaults)
        all_subtasks = new_tasks._get_all_subtasks()
        relinked = all_subtasks.filtered(lambda child: child.project_id == self)
        dbg.pipeline.debug(
            "[project:%s] map_tasks: copied %s, relinking %d of %d subtasks",
            self.id,
            dbg.rec(new_tasks),
            len(relinked),
            len(all_subtasks),
        )
        relinked.write({"project_id": project.id})
        return True

    def copy_data(self, default: ValuesType | None = None) -> list[ValuesType]:
        default = dict(default or {})
        vals_list = super().copy_data(default=default)
        copy_from_template = self.env.context.get("copy_from_template")
        dbg.lifecycle.debug(
            "project.project.copy_data %s: default=%s copy_from_template=%s",
            dbg.rec(self),
            dbg.keys(default),
            copy_from_template,
        )
        has_project_stage_feature = False
        if copy_from_template and "phase_id" not in default:
            has_project_stage_feature = self.env.user.has_group(
                "project.group_project_stages"
            )
        for project, vals in zip(self, vals_list, strict=True):
            if project.is_template and not copy_from_template:
                vals["is_template"] = True
            if copy_from_template:
                if has_project_stage_feature:
                    vals["phase_id"] = project.phase_id.id
                for field in self._get_template_field_blacklist():
                    if field in vals and field not in default:
                        del vals[field]
            if copy_from_template or (
                not project.is_template and vals.get("is_template")
            ):
                vals["name"] = default.get("name", project.name)
            else:
                vals["name"] = default.get(
                    "name", self.env._("%s (copy)", project.name)
                )
        return vals_list

    def copy_translations(self, new, excluded=()):
        super().copy_translations(new, excluded=(*excluded, "name"))
        self._copy_translations_of_renamed_field(
            new, "name", lambda record, term: record.env._("%s (copy)", term)
        )

    @dbg.timed
    def copy(self, default: ValuesType | None = None) -> Self:
        default = dict(default or {})
        default["milestone_ids"] = False
        copy_context = dict(
            self.env.context,
            mail_auto_subscribe_no_notify=True,
            mail_create_nosubscribe=True,
        )
        copy_context.pop("default_phase_id", None)
        new_projects = super(ProjectProject, self.with_context(copy_context)).copy(
            default=default
        )
        dbg.lifecycle.debug(
            "project.project.copy %s -> %s", dbg.rec(self), dbg.rec(new_projects)
        )
        if "milestone_mapping" not in self.env.context:
            self = self.with_context(milestone_mapping={})
        for old_project, new_project in zip(self, new_projects, strict=True):
            dbg.pipeline.debug(
                "[project:%s] copy -> %s: followers=%d milestones=%s tasks=%s",
                old_project.id,
                new_project.id,
                len(old_project.message_follower_ids),
                old_project.allow_milestones,
                "task_ids" not in default,
            )
            for follower in old_project.message_follower_ids:
                new_project.message_subscribe(
                    partner_ids=follower.partner_id.ids,
                    subtype_ids=follower.subtype_ids.ids,
                )
            if old_project.allow_milestones:
                new_project.milestone_ids = old_project.milestone_ids.copy().ids
            if "task_ids" not in default:
                old_project.map_tasks(new_project.id)
            if not old_project.active:
                new_project.with_context(active_test=False).task_ids.active = True
        shared_embedded_actions_mapping = self._copy_shared_embedded_actions(
            new_projects
        )
        self._copy_embedded_actions_config(
            new_projects, shared_embedded_actions_mapping
        )
        return new_projects

    @dbg.timed
    def _copy_shared_embedded_actions(self, new_projects: Self) -> dict[int, int]:
        shared_embedded_actions_per_record = dict(
            self.env["ir.embedded.actions"]
            .sudo()
            ._read_group(
                domain=[
                    ("parent_res_id", "in", self.ids),
                    ("parent_res_model", "=", self._name),
                    ("user_id", "=", False),
                ],
                groupby=["parent_res_id"],
                aggregates=["id:recordset"],
            )
        )
        shared_embedded_actions_mapping = {}
        for project, new_project in zip(self, new_projects, strict=True):
            shared_embedded_actions = shared_embedded_actions_per_record.get(project.id)
            if shared_embedded_actions:
                copy_shared_embedded_actions = shared_embedded_actions.copy(
                    {"parent_res_id": new_project.id}
                )
                for original_action, copied_action in zip(
                    shared_embedded_actions,
                    copy_shared_embedded_actions,
                    strict=True,
                ):
                    shared_embedded_actions_mapping[original_action.id] = (
                        copied_action.id
                    )
                    copied_action.filter_ids = original_action.filter_ids.copy(
                        {"embedded_parent_res_id": new_project.id}
                    )
        dbg.logic.debug(
            "_copy_shared_embedded_actions %s: %d actions copied",
            dbg.rec(self),
            len(shared_embedded_actions_mapping),
        )
        return shared_embedded_actions_mapping

    @dbg.timed
    def _copy_embedded_actions_config(
        self,
        new_projects: Self,
        shared_embedded_actions_mapping: dict | None = None,
    ) -> None:
        shared_embedded_actions_mapping = shared_embedded_actions_mapping or {}
        embedded_action_configs_per_project = dict(
            self.env["res.users.settings.embedded.action"]
            .sudo()
            ._read_group(
                [("res_id", "in", self.ids), ("res_model", "=", self._name)],
                ["res_id"],
                ["id:recordset"],
            )
        )
        valid_embedded_action_ids = self.env["ir.embedded.actions"].sudo().search(
            domain=[
                ("parent_res_model", "=", self._name),
                ("user_id", "=", False),
            ],
        ).ids + [False]
        new_embedded_actions_config_vals_list = []
        for project, new_project in zip(self, new_projects, strict=True):
            configs = embedded_action_configs_per_project.get(
                project.id, self.env["res.users.settings.embedded.action"]
            )
            config_vals_list = configs.copy_data({"res_id": new_project.id})
            for config_vals in config_vals_list:
                if config_vals["embedded_actions_visibility"]:
                    embedded_actions_visibility = [
                        shared_embedded_actions_mapping.get(action_id, action_id)
                        for action_id in [
                            False if x == "false" else int(x)
                            for x in config_vals["embedded_actions_visibility"].split(
                                ","
                            )
                        ]
                        if action_id in valid_embedded_action_ids
                    ]
                    config_vals["embedded_actions_visibility"] = ",".join(
                        "false" if action_id is False else str(action_id)
                        for action_id in embedded_actions_visibility
                    )
                if config_vals["embedded_actions_order"]:
                    embedded_actions_order = [
                        shared_embedded_actions_mapping.get(action_id, action_id)
                        for action_id in [
                            False if x == "false" else int(x)
                            for x in config_vals["embedded_actions_order"].split(",")
                        ]
                        if action_id in valid_embedded_action_ids
                    ]
                    config_vals["embedded_actions_order"] = ",".join(
                        "false" if action_id is False else str(action_id)
                        for action_id in embedded_actions_order
                    )
                new_embedded_actions_config_vals_list.append(config_vals)
        dbg.logic.debug(
            "_copy_embedded_actions_config %s: %d user configs copied",
            dbg.rec(self),
            len(new_embedded_actions_config_vals_list),
        )
        self.env["res.users.settings.embedded.action"].sudo().create(
            new_embedded_actions_config_vals_list
        )

    @api.model
    def _check_date_pair(self, date_start: Any, date_end: Any) -> None:
        if bool(date_start) != bool(date_end):
            raise UserError(
                self.env._(
                    "A project's start date and end date must be set "
                    "together: define both or clear both."
                )
            )

    def _create_default_workflow_steps(self) -> None:
        stepless = self.filtered(lambda project: not project.workflow_step_ids)
        if not stepless:
            return
        dbg.lifecycle.debug(
            "_create_default_workflow_steps: 'New' step for %s", dbg.rec(stepless)
        )
        self.env["project.workflow.step"].sudo().create(
            [
                {"name": _("New"), "project_ids": [Command.link(project.id)]}
                for project in stepless
            ]
        )

    @dbg.timed
    @api.model_create_multi
    def create(self, vals_list: list[ValuesType]) -> Self:
        dbg.lifecycle.debug(
            "project.project.create: %d vals, keys=%s, uid=%s",
            len(vals_list),
            dbg.vals_keys(vals_list),
            self.env.uid,
        )
        self = self.with_context(mail_create_nosubscribe=True)
        if any("label_tasks" in vals and not vals["label_tasks"] for vals in vals_list):
            task_label = _("Tasks")
            for vals in vals_list:
                if "label_tasks" in vals and not vals["label_tasks"]:
                    vals["label_tasks"] = task_label
        if self.env.user.has_group("project.group_project_stages"):
            if "default_phase_id" in self.env.context:
                stage = self.env["project.phase"].browse(
                    self.env.context["default_phase_id"]
                )
                if stage.company_id:
                    for vals in vals_list:
                        if vals.get("phase_id"):
                            continue
                        vals["company_id"] = stage.company_id.id
            else:
                companies_ids = [
                    vals.get("company_id", False) for vals in vals_list
                ] + [False]
                stages = self.env["project.phase"].search(
                    [("company_id", "in", companies_ids)]
                )
                for vals in vals_list:
                    if vals.get("phase_id"):
                        continue
                    stage_domain = (
                        [False]
                        if "company_id" not in vals
                        else [False, vals.get("company_id")]
                    )
                    stage = stages.filtered(
                        lambda s, d=stage_domain: s.company_id.id in d
                    )[:1]
                    vals["phase_id"] = stage.id
                    dbg.logic.debug(
                        "project.project.create: default phase %s for company %s",
                        stage.id,
                        vals.get("company_id"),
                    )

        for vals in vals_list:
            self._check_date_pair(
                vals.get("date_start"),
                vals.get("date_end", vals.get("date")),
            )
        with dbg.timer(self.env, "project.project.create: super().create"):
            projects = super().create(vals_list)
        dbg.lifecycle.debug("project.project.create: created %s", dbg.rec(projects))
        dbg.pipeline.debug(
            "[project:%s] create -> default workflow steps", dbg.rec(projects)
        )
        projects._create_default_workflow_steps()
        dbg.pipeline.debug("[project:%s] create -> reset metrics", dbg.rec(projects))
        projects._reset_metrics()
        return projects

    @dbg.timed
    def write(self, vals: dict[str, Any]) -> bool:
        dbg.lifecycle.debug(
            "project.project.write on %s: keys=%s uid=%s",
            dbg.rec(self),
            dbg.keys(vals),
            self.env.uid,
        )
        if vals.get("access_token"):
            self.check_singleton()
            if self.privacy_visibility not in ["invited_users", "portal"]:
                dbg.logic.debug(
                    "project.project.write %s: visibility %s, access_token cleared",
                    dbg.rec(self),
                    self.privacy_visibility,
                )
                vals["access_token"] = ""

        company_id = vals.get("company_id")
        if self.env.user.has_group("project.group_project_stages") and company_id:
            projects_already_with_company = self.filtered(
                lambda p: p.company_id.id == company_id
            )
            if projects_already_with_company:
                dbg.logic.debug(
                    "project.project.write: %s already in company %s, "
                    "writing without company_id",
                    dbg.rec(projects_already_with_company),
                    company_id,
                )
                projects_already_with_company.write(
                    {key: value for key, value in vals.items() if key != "company_id"}
                )
                self -= projects_already_with_company
            if (
                company_id not in (None, *self.company_id.ids)
                and self.phase_id.company_id
            ):
                ProjectStage = self.env["project.phase"]
                vals["phase_id"] = ProjectStage.search(
                    [("company_id", "in", (company_id, False))],
                    order=f"sequence asc, {ProjectStage._order}",
                    limit=1,
                ).id
                dbg.logic.debug(
                    "project.project.write %s: company -> %s, phase reset to %s",
                    dbg.rec(self),
                    company_id,
                    vals["phase_id"],
                )

        if "last_update_status" in vals and vals["last_update_status"] != "to_define":
            dbg.pipeline.debug(
                "[project:%s] write -> project.update %s",
                dbg.rec(self),
                vals["last_update_status"],
            )
            for project in self:
                self.env["project.update"].with_context(
                    default_project_id=project.id
                ).create(
                    {
                        "name": _(
                            "Status Update - %(date)s",
                            date=fields.Date.today().strftime(
                                get_lang(self.env).date_format
                            ),
                        ),
                        "status": vals.get("last_update_status"),
                    }
                )
            vals.pop("last_update_status")
        visibility_before = (
            {project: project.privacy_visibility for project in self}
            if vals.get("privacy_visibility")
            else {}
        )

        if {"date_start", "date_end", "date"} & vals.keys():
            for project in self:
                self._check_date_pair(
                    vals.get("date_start", project.date_start),
                    vals.get("date_end", vals.get("date", project.date_end)),
                )

        with dbg.timer(self.env, "project.project.write: super().write"):
            res = super().write(vals) if vals else True

        if visibility_before:
            dbg.pipeline.debug(
                "[project:%s] write -> sync access to visibility %s",
                dbg.rec(self),
                vals["privacy_visibility"],
            )
            self._sync_access_to_privacy_visibility(visibility_before)

        if "allow_dependencies" in vals and not vals.get("allow_dependencies"):
            blocked = self.env["project.task"].search(
                [
                    ("project_id", "in", self.ids),
                    ("state", "=", "blocked"),
                ]
            )
            dbg.pipeline.debug(
                "[project:%s] write -> dependencies off, unblocking %s",
                dbg.rec(self),
                dbg.rec(blocked),
            )
            blocked.write({"state": "in_progress"})

        if "allow_recurring_tasks" in vals and not vals["allow_recurring_tasks"]:
            recurring = self.env["project.task"].search(
                [("project_id", "in", self.ids), ("recurring_task", "=", True)]
            )
            dbg.pipeline.debug(
                "[project:%s] write -> recurrence off, clearing %s",
                dbg.rec(self),
                dbg.rec(recurring),
            )
            recurring.write({"recurring_task": False})

        if "active" in vals:
            tasks = self.with_context(active_test=False).task_ids
            dbg.pipeline.debug(
                "[project:%s] write -> active=%s on %s",
                dbg.rec(self),
                vals["active"],
                dbg.rec(tasks),
            )
            tasks.write({"active": vals["active"]})
        if "name" in vals and self.account_id:
            projects_read_group = self.env["project.project"]._read_group(
                [("account_id", "in", self.account_id.ids)],
                ["account_id"],
                having=[("__count", "=", 1)],
            )
            analytic_account_to_update = self.env["account.analytic.account"].browse(
                [analytic_account.id for [analytic_account] in projects_read_group]
            )
            dbg.pipeline.debug(
                "[project:%s] write -> rename analytic accounts %s",
                dbg.rec(self),
                dbg.rec(analytic_account_to_update),
            )
            analytic_account_to_update.write({"name": vals["name"]})
        return res

    @dbg.timed
    def unlink(self) -> bool:
        dbg.lifecycle.debug("project.project.unlink %s", dbg.rec(self))
        self.env["res.users.settings.embedded.action"].sudo().search(
            domain=[("res_id", "in", self.ids), ("res_model", "=", self._name)],
        ).unlink()
        deleted_per_account = defaultdict(int)
        for project in self:
            if project.account_id:
                deleted_per_account[project.account_id] += 1
        analytic_accounts_to_delete = self.env["account.analytic.account"]
        for account, deleted_count in deleted_per_account.items():
            if not account.line_ids and account.project_count <= deleted_count:
                analytic_accounts_to_delete |= account
        tasks = self.with_context(active_test=False).task_ids
        dbg.pipeline.debug(
            "[project:%s] unlink -> tasks %s, then analytic accounts %s",
            dbg.rec(self),
            dbg.rec(tasks),
            dbg.rec(analytic_accounts_to_delete),
        )
        tasks.unlink()
        result = super().unlink()
        analytic_accounts_to_delete.unlink()
        return result

    @api.ondelete(at_uninstall=False)
    def _sync_feature_groups_on_unlink(self) -> None:
        self._sync_feature_group_to_usage(
            "allow_dependencies", "project.group_project_task_dependencies"
        )
        self._sync_feature_group_to_usage(
            "allow_milestones", "project.group_project_milestone"
        )
        self._sync_feature_group_to_usage(
            "allow_recurring_tasks", "project.group_project_recurring_tasks"
        )

    def _get_fields_assignment(self) -> set[str]:
        """The fields a write names the project manager through.

        `user_id` is the manager everything downstream reads, but a layer that
        composes it from fields of its own must name those here, or every hook
        keyed on a manager change stops firing.
        """
        return {"user_id"}

    def _get_assigned_users(self, values: dict[str, Any]):
        """The user a write makes the manager, whatever field carried it.

        Read before the write is applied, so a composed `user_id` cannot be read
        back from the record yet.
        """
        user_id = values.get("user_id")
        return (
            self.env["res.users"].browse(user_id) if user_id else self.env["res.users"]
        )

    @api.model
    def _prepare_assignment_vals(self, users) -> dict[str, Any]:
        return {"user_id": users[:1].id}

    def _message_auto_subscribe_followers(
        self, updated_values: dict, default_subtype_ids: list[int]
    ) -> list:
        # Not super()'s: it subscribes `user_id` only while that field is tracked,
        # and a layer composing it from its own tracked fields leaves it untracked.
        # The manager follows the project either way.
        manager = self._get_assigned_users(updated_values).sudo()
        if not manager or not manager.active or not manager.partner_id:
            return super()._message_auto_subscribe_followers(
                updated_values, default_subtype_ids
            )
        return [
            (
                manager.partner_id.id,
                default_subtype_ids,
                "mail.message_user_assigned" if manager != self.env.user else False,
            )
        ]

    def message_subscribe(
        self,
        partner_ids: list[int] | None = None,
        subtype_ids: list[int] | None = None,
    ) -> bool:
        res = super().message_subscribe(
            partner_ids=partner_ids, subtype_ids=subtype_ids
        )
        if subtype_ids:
            project_subtypes = self.env["mail.message.subtype"].browse(subtype_ids)
            task_subtypes = (
                project_subtypes.mapped("parent_id")
                | project_subtypes.filtered(lambda sub: sub.internal or sub.default)
            ).ids
            if task_subtypes:
                partner_set = set(partner_ids)
                tasks_by_partners = defaultdict(lambda: self.env["project.task"])
                for task in self.task_ids:
                    partners = frozenset(task.message_partner_ids.ids) & partner_set
                    if partners:
                        tasks_by_partners[partners] |= task
                dbg.pipeline.debug(
                    "[project:%s] message_subscribe -> %d task groups, subtypes %s",
                    dbg.rec(self),
                    len(tasks_by_partners),
                    task_subtypes,
                )
                for partners, tasks in tasks_by_partners.items():
                    tasks.message_subscribe(
                        partner_ids=list(partners),
                        subtype_ids=task_subtypes,
                    )
                self.update_ids.message_subscribe(
                    partner_ids=partner_ids, subtype_ids=subtype_ids
                )
        return res

    def message_unsubscribe(self, partner_ids: list[int] | None = None) -> None:
        dbg.pipeline.debug(
            "[project:%s] message_unsubscribe %s -> tasks",
            dbg.rec(self),
            partner_ids,
        )
        self.task_ids.message_unsubscribe(partner_ids=partner_ids)
        super().message_unsubscribe(partner_ids=partner_ids)

    def _alias_get_creation_values(self) -> dict:
        values = super()._alias_get_creation_values()
        values["alias_model_id"] = self.env["ir.model"]._get("project.task").id
        if self.id:
            values["alias_defaults"] = defaults = self._prepare_alias_defaults()
            defaults["project_id"] = self.id
        return values

    @api.constrains("phase_id")
    def _check_phase_has_same_company(self) -> None:
        for project in self:
            if (
                project.phase_id.company_id
                and project.phase_id.company_id != project.company_id
            ):
                raise UserError(
                    _(
                        "This project is associated with %(project_company)s, whereas the selected stage belongs to %(stage_company)s. "
                        "There are a couple of options to consider: either remove the company designation "
                        "from the project or from the stage. Alternatively, you can update the company "
                        "information for these records to align them under the same company.",
                        project_company=project.company_id.name,
                        stage_company=project.phase_id.company_id.name,
                    )
                    if project.company_id
                    else _(
                        "This project is not associated with any company, while the stage is associated with %s. "
                        "There are a couple of options to consider: either change the project's company "
                        "to align with the stage's company or remove the company designation from the stage",
                        project.phase_id.company_id.name,
                    )
                )

    @versioned_envelope
    def get_template_tasks(self) -> list:
        self.check_singleton()
        return self.env["project.task"].search_read(
            [("project_id", "=", self.id), ("is_template", "=", True)],
            ["id", "name"],
        )

    @api.model
    def _sync_feature_group_to_usage(
        self, field_name: str, group_name: str
    ) -> bool | None:
        has_user_group = bool(self.env.user.has_group(group_name))
        group = self.env.ref(group_name)
        base_group_user = self.env.ref("base.group_user")
        has_project_field_set = bool(
            self.env["project.project"]
            .sudo()
            .search_count([(field_name, "=", True)], limit=1)
        )
        res = None

        if not has_user_group and has_project_field_set:
            base_group_user.sudo().write({"implied_ids": [Command.link(group.id)]})
            res = True
        elif has_user_group and not has_project_field_set:
            base_group_user.sudo().write({"implied_ids": [Command.unlink(group.id)]})
            group.sudo().write({"user_ids": [Command.clear()]})
            res = False
        dbg.logic.debug(
            "_sync_feature_group_to_usage %s/%s: has_group=%s in_use=%s -> %s",
            field_name,
            group_name,
            has_user_group,
            has_project_field_set,
            {True: "implied", False: "removed", None: "unchanged"}[res],
        )
        return res

    def _get_project_features_mapping(self) -> dict:
        return {
            "allow_dependencies": "project.group_project_task_dependencies",
            "allow_milestones": "project.group_project_milestone",
            "allow_recurring_tasks": "project.group_project_recurring_tasks",
        }

    @api.model
    def get_features_enabled(
        self, updated_features: list[str] | None = None
    ) -> dict[str, bool]:
        if not self.env.user.has_group("project.group_project_user"):
            return {}
        if updated_features:
            return {
                field_name: self.env.user.has_group(group)
                for field_name, group in self._get_project_features_mapping().items()
                if field_name in updated_features
            }
        return {
            field_name: self.env.user.has_group(group)
            for field_name, group in self._get_project_features_mapping().items()
        }

    def _track_template(self, changes: dict[str, Any]) -> dict:
        res = super()._track_template(changes)
        project = self[0]
        if (
            self.env.user.has_group("project.group_project_stages")
            and "phase_id" in changes
            and project.phase_id.mail_template_id
            and project.phase_id.mail_template_id.model == self._name
        ):
            res["phase_id"] = (
                project.phase_id.mail_template_id,
                {
                    "auto_delete_keep_log": False,
                    "subtype_id": self.env["ir.model.data"]._xmlid_to_res_id(
                        "mail.mt_note"
                    ),
                    "email_layout_xmlid": "mail.mail_notification_light",
                },
            )
        return res

    def _track_subtype(self, init_values: dict[str, Any]) -> Self:
        self.check_singleton()
        if "phase_id" in init_values:
            return self.env.ref("project.mt_project_stage_change")
        return super()._track_subtype(init_values)

    def _mail_get_message_subtypes(self) -> Self:
        res = super()._mail_get_message_subtypes()
        if len(self) == 1:
            waiting_subtype = self.env.ref("project.mt_project_task_waiting")
            if not self.allow_dependencies and waiting_subtype in res:
                res -= waiting_subtype
        return res

    def _notify_get_recipients_groups(
        self,
        message: Any,
        model_description: str,
        msg_vals: dict | bool = False,
    ) -> list:
        groups = super()._notify_get_recipients_groups(
            message, model_description, msg_vals=msg_vals
        )
        if not self:
            return groups

        self.check_singleton()
        portal_privacy = self.privacy_visibility in ["invited_users", "portal"]
        for group_name, _group_method, group_data in groups:
            if group_name in ["portal", "portal_customer"] and not portal_privacy:
                group_data["has_button_access"] = False
        return groups

    def action_project_task_burndown_chart_report(self) -> dict:
        action = self.env["ir.actions.act_window"]._get_action_dict_by_xml_id(
            "project.action_project_task_burndown_chart_report"
        )
        action["display_name"] = _("%(name)s's Burndown Chart", name=self.name)
        context = action["context"].replace("active_id", str(self.id))
        context = self.env["ir.actions.actions"]._eval_action_context(context)
        context.update(
            {
                "stage_name_and_sequence_per_id": {
                    stage.id: {"sequence": stage.sequence, "name": stage.name}
                    for stage in self.workflow_step_ids
                }
            }
        )
        action["context"] = context
        return action

    def action_view_scatter_plot(self) -> dict:
        action = self.env["ir.actions.act_window"]._get_action_dict_by_xml_id(
            "project.action_project_task_scatter"
        )
        action["display_name"] = _("%(name)s's Cycle Time Scatter", name=self.name)
        return action

    def action_find_similar_projects(self) -> dict:
        self.check_singleton()
        domain = []
        if self.tag_ids:
            domain.append(("tag_ids", "in", self.tag_ids.ids))
        if self.task_count:
            team_size = len(
                self.env["project.task"]
                .search(
                    [
                        ("project_id", "=", self.id),
                        ("user_ids", "!=", False),
                    ]
                )
                .mapped("user_ids")
            )
            if team_size:
                domain.append(("team_size", ">=", max(1, team_size - 2)))
                domain.append(("team_size", "<=", team_size + 2))
        action = self.env["ir.actions.act_window"]._get_action_dict_by_xml_id(
            "project.action_project_history"
        )
        action["display_name"] = _("Similar Projects to %(name)s", name=self.name)
        action["domain"] = domain
        return action

    def action_view_project_updates(self) -> dict:
        action = self.env["ir.actions.act_window"]._get_action_dict_by_xml_id(
            "project.project_update_all_action"
        )
        action["display_name"] = _("%(name)s Dashboard", name=self.name)
        return action

    def action_view_share_project_wizard(self) -> dict:
        template = self.env.ref(
            "project.mail_template_project_sharing", raise_if_not_found=False
        )

        local_context = self.env.context | {
            "default_template_id": template.id if template else False,
            "default_email_layout_xmlid": "mail.mail_notification_light",
            "active_id": self.id,
            "active_model": "project.project",
        }
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "project.project_share_wizard_action"
        )
        if self.env.context.get("default_access_mode"):
            action["name"] = _("Share Project")
        action["context"] = local_context
        return action

    def action_view_tasks(self) -> dict:
        action = (
            self.env["ir.actions.act_window"]
            .with_context(active_id=self.id)
            ._get_action_dict_by_xml_id(
                "project.act_project_project_2_project_task_all"
            )
        )
        action["display_name"] = self.name
        context = action["context"].replace("active_id", str(self.id))
        context = self.env["ir.actions.actions"]._eval_action_context(context)
        context.update(
            {
                "create": self.active,
                "active_test": self.active,
                "active_id": self.id,
                "allow_milestones": self.allow_milestones,
                "allow_dependencies": self.allow_dependencies,
            }
        )
        action["context"] = context
        if self.is_template:
            action["context"].update({"template_project": True})
            action["views"] = [
                (view_id, view_type)
                for view_id, view_type in action["views"]
                if view_type not in ("pivot", "graph")
            ]
        return action

    def action_view_all_rating(self) -> dict:
        action = self.env["ir.actions.act_window"]._get_action_dict_by_xml_id(
            "project.rating_rating_action_view_project_rating"
        )
        action["display_name"] = _("%(name)s's Rating", name=self.name)
        action_context = (
            self.env["ir.actions.actions"]._eval_action_context(action["context"])
            if action["context"]
            else {}
        )
        action_context.update(self.env.context)
        action_context["search_default_filter_write_date"] = (
            "custom_write_date_last_30_days"
        )
        action_context.pop("group_by", None)
        action["domain"] = [
            ("consumed", "=", True),
            ("parent_res_model", "=", "project.project"),
            ("parent_res_id", "=", self.id),
        ]
        if self.rating_child_count == 1:
            action.update(
                {
                    "view_mode": "form",
                    "views": [
                        (view_id, view_type)
                        for view_id, view_type in action["views"]
                        if view_type == "form"
                    ],
                    "res_id": self.rating_child_ids[0].id,
                }
            )
        return dict(action, context=action_context)

    def action_view_tasks_analysis(self) -> dict:
        action = self.env["ir.actions.act_window"]._get_action_dict_by_xml_id(
            "project.action_project_task_user_tree"
        )
        action["display_name"] = _("%(name)s's Tasks Analysis", name=self.name)
        action_context = (
            self.env["ir.actions.actions"]._eval_action_context(action["context"])
            if action["context"]
            else {}
        )
        action_context["search_default_project_id"] = self.id
        return dict(action, context=action_context)

    def action_view_assigned_resources(self) -> dict:
        self.check_singleton()
        task_ids = self.env["project.task"].search([("project_id", "=", self.id)]).ids
        action = self.env["ir.actions.act_window"]._get_action_dict_by_xml_id(
            "project.action_project_task_assigned_resources"
        )
        action["display_name"] = _("%(name)s's Assigned Resources", name=self.name)
        action["domain"] = [
            ("res_model", "=", "project.task"),
            ("res_id", "in", task_ids),
        ]
        return action

    def action_get_list_view(self) -> dict:
        action = self.env["ir.actions.act_window"]._get_action_dict_by_xml_id(
            "project.project_milestone_action"
        )
        action["display_name"] = _("%(name)s's Milestones", name=self.name)
        return action

    def action_view_tasks_from_project_milestone(self) -> dict:
        action = self.env["ir.actions.act_window"]._get_action_dict_by_xml_id(
            "project.project_milestone_action_view_tasks"
        )
        action["display_name"] = _("Tasks")
        action["domain"] = [("milestone_id", "in", self.milestone_ids.ids)]
        return action

    def action_profitability_items(
        self,
        section_name: str,
        domain: list | None = None,
        res_id: int | bool = False,
    ) -> dict:
        return {}

    def get_last_update_or_default(self) -> dict:
        self.check_singleton()
        labels = dict(
            self._fields["last_update_status"]._description_selection(self.env)
        )
        return {
            "status": labels.get(self.last_update_status, _("Set Status")),
            "color": self.last_update_color,
        }

    @dbg.timed
    def get_panel_data(self) -> dict:
        self.check_singleton()
        if not self.env.user.has_group("project.group_project_user"):
            return {}
        self._reset_metrics()
        show_profitability = self._is_profitability_shown()
        dbg.logic.debug(
            "get_panel_data [project:%s]: profitability=%s milestones=%s",
            self.id,
            show_profitability,
            self.allow_milestones,
        )
        panel_data = {
            "user": self._get_user_values(),
            "buttons": sorted(self._get_stat_buttons(), key=lambda k: k["sequence"]),
            "currency_id": self.currency_id.id,
            "show_project_profitability_helper": show_profitability
            and self._is_profitability_helper_shown(),
            "show_milestones": self.allow_milestones,
        }
        if self.allow_milestones:
            panel_data["milestones"] = self._get_milestones()
        if show_profitability:
            profitability_items = self.with_context(
                active_test=False
            )._get_profitability_items()
            if (
                self._get_profitability_sequence_per_invoice_type()
                and profitability_items
                and "revenues" in profitability_items
                and "costs" in profitability_items
            ):
                profitability_items["revenues"]["data"] = sorted(
                    profitability_items["revenues"]["data"],
                    key=lambda k: k["sequence"],
                )
                profitability_items["costs"]["data"] = sorted(
                    profitability_items["costs"]["data"],
                    key=lambda k: k["sequence"],
                )
            panel_data["profitability_items"] = profitability_items
            panel_data["profitability_labels"] = self._get_profitability_labels()
        return panel_data

    def get_milestones(self) -> dict:
        if self.env.user.has_group("project.group_project_user"):
            return self._get_milestones()
        return {}

    def _get_profitability_labels(self) -> dict:
        return {}

    def _get_profitability_sequence_per_invoice_type(self) -> dict:
        return {}

    def _get_already_included_profitability_invoice_line_ids(self) -> list:
        return []

    def _get_user_values(self) -> dict:
        return {
            "is_project_user": self.env.user.has_group("project.group_project_user"),
        }

    def _is_profitability_shown(self) -> bool:
        self.check_singleton()
        return True

    def _is_profitability_helper_shown(self) -> bool:
        return self.env.user.has_group("analytic.group_analytic_accounting")

    def _get_domain_profitability_aal(self) -> list:
        return [("account_id", "in", self.account_id.ids)]

    def _get_profitability_items(self, with_action: bool = True) -> dict:
        return self._get_items_from_aal(with_action)

    def _get_items_from_aal(self, with_action: bool = True) -> dict:
        return {
            "revenues": {
                "data": [],
                "total": {"invoiced": 0.0, "to_invoice": 0.0},
            },
            "costs": {"data": [], "total": {"billed": 0.0, "to_bill": 0.0}},
        }

    def _get_milestones(self) -> dict:
        self.check_singleton()
        return {
            "data": self.milestone_ids._get_export_values_list(),
        }

    def _get_stat_buttons(self) -> list:
        self.check_singleton()
        closed_task_count = self.task_count - self.open_task_count
        if self.task_count:
            number = self.env._(
                "%(closed_task_count)s / %(task_count)s (%(closed_rate)s%%)",
                closed_task_count=closed_task_count,
                task_count=self.task_count,
                closed_rate=round(100 * closed_task_count / self.task_count),
            )
        else:
            number = self.env._(
                "%(closed_task_count)s / %(task_count)s",
                closed_task_count=closed_task_count,
                task_count=self.task_count,
            )
        buttons = [
            {
                "icon": "check",
                "text": self.label_tasks,
                "number": number,
                "action_type": "object",
                "action": "action_view_tasks",
                "show": True,
                "sequence": 1,
            }
        ]
        if self.rating_child_count != 0:
            if self.rating_child_avg >= rating_data.RATING_AVG_TOP:
                icon = "smile-o text-success"
            elif self.rating_child_avg >= rating_data.RATING_AVG_OK:
                icon = "meh-o text-warning"
            else:
                icon = "frown-o text-danger"
            buttons.append(
                {
                    "icon": icon,
                    "text": self.env._("Average Rating"),
                    "number": f"{int(self.rating_child_avg) if self.rating_child_avg.is_integer() else round(self.rating_child_avg, 1)} / 5",
                    "action_type": "object",
                    "action": "action_view_all_rating",
                    "show": self.show_ratings,
                    "sequence": 15,
                }
            )
        if self.env.user.has_group("project.group_project_user"):
            buttons.append(
                {
                    "icon": "area-chart",
                    "text": self.env._("Burndown Chart"),
                    "action_type": "action",
                    "action": "project.action_project_task_burndown_chart_report",
                    "additional_context": json.dumps(
                        {
                            "active_id": self.id,
                            "stage_name_and_sequence_per_id": {
                                stage.id: {
                                    "sequence": stage.sequence,
                                    "name": stage.name,
                                }
                                for stage in self.workflow_step_ids
                            },
                        }
                    ),
                    "show": True,
                    "sequence": 60,
                }
            )
        return buttons

    @dbg.timed
    def _get_profitability_values(self) -> tuple[dict, bool]:
        if not self.env.user.has_group("project.group_project_manager"):
            return {}, False
        profitability_items = self._get_profitability_items(False)
        if (
            profitability_items
            and "revenues" in profitability_items
            and "costs" in profitability_items
        ):
            profitability_items["revenues"]["data"] = sorted(
                profitability_items["revenues"]["data"],
                key=lambda k: k["sequence"],
            )
            profitability_items["costs"]["data"] = sorted(
                profitability_items["costs"]["data"],
                key=lambda k: k["sequence"],
            )
        costs = sum(profitability_items["costs"]["total"].values())
        revenues = sum(profitability_items["revenues"]["total"].values())
        margin = revenues + costs
        to_bill_to_invoice = (
            profitability_items["costs"]["total"]["to_bill"]
            + profitability_items["revenues"]["total"]["to_invoice"]
        )
        billed_invoiced = (
            profitability_items["costs"]["total"]["billed"]
            + profitability_items["revenues"]["total"]["invoiced"]
        )
        (
            expected_percentage,
            to_bill_to_invoice_percentage,
            billed_invoiced_percentage,
        ) = (0, 0, 0)
        if revenues:
            expected_percentage = formatLang(
                self.env, (margin / revenues) * 100, digits=0
            )
        if profitability_items["revenues"]["total"]["to_invoice"]:
            to_bill_to_invoice_percentage = formatLang(
                self.env,
                (
                    to_bill_to_invoice
                    / profitability_items["revenues"]["total"]["to_invoice"]
                )
                * 100,
                digits=0,
            )
        if profitability_items["revenues"]["total"]["invoiced"]:
            billed_invoiced_percentage = formatLang(
                self.env,
                (billed_invoiced / profitability_items["revenues"]["total"]["invoiced"])
                * 100,
                digits=0,
            )
        profitability_values_dict = {
            "account_id": self.account_id,
            "costs": profitability_items["costs"],
            "revenues": profitability_items["revenues"],
            "expected_percentage": expected_percentage,
            "to_bill_to_invoice_percentage": to_bill_to_invoice_percentage,
            "billed_invoiced_percentage": billed_invoiced_percentage,
            "total": {
                "costs": costs,
                "revenues": revenues,
                "margin": margin,
                "margin_percentage": formatLang(
                    self.env,
                    (
                        not float_utils.float_is_zero(costs, precision_digits=2)
                        and (margin / -costs) * 100
                    )
                    or 0.0,
                    digits=0,
                ),
            },
            "labels": self._get_profitability_labels(),
        }
        show_profitability = bool(
            profitability_values_dict.get("account_id")
            and (
                profitability_values_dict.get("costs")
                or profitability_values_dict.get("revenues")
            )
        )
        return profitability_values_dict, show_profitability

    def _is_partner_hidden(self) -> bool:
        return False

    @api.model
    def _prepare_analytic_account_vals_list(
        self, project_vals_list: list[dict]
    ) -> list[dict]:
        project_plan, _other_plans = self.env["account.analytic.plan"]._get_all_plans()
        return [
            {
                "name": project_vals.get(
                    "name", self.env._("Unknown Analytic Account")
                ),
                "company_id": project_vals.get("company_id", False),
                "partner_id": project_vals.get("partner_id", False),
                "plan_id": project_plan.id,
            }
            for project_vals in project_vals_list
        ]

    @dbg.timed
    def _create_analytic_account(self) -> None:
        analytic_accounts_values = self._prepare_analytic_account_vals_list(
            self._read_format(["name", "company_id", "partner_id"], None)
        )
        analytic_accounts = self.env["account.analytic.account"].create(
            analytic_accounts_values
        )
        dbg.lifecycle.debug(
            "_create_analytic_account %s -> %s",
            dbg.rec(self),
            dbg.rec(analytic_accounts),
        )
        for project, analytic_account in zip(self, analytic_accounts, strict=True):
            project.account_id = analytic_account

    def _get_domain_projects_to_make_billable(self) -> list:
        return [("partner_id", "!=", False)]

    @api.constrains(lambda self: self._get_plan_fnames())
    def _check_account_id(self) -> None:
        pass

    def _get_domain_plan(self, plan: Any) -> list:
        return Domain.AND(
            [
                super()._get_domain_plan(plan),
                [
                    "|",
                    ("company_id", "=", False),
                    ("company_id", "=?", unquote("company_id")),
                ],
            ]
        )

    def _prepare_account_node_context(self, plan: Any) -> dict:
        return {
            **super()._prepare_account_node_context(plan),
            "default_company_id": unquote("company_id"),
        }

    @dbg.timed
    def _sync_access_to_privacy_visibility(self, visibility_before: dict) -> None:
        shared = ("invited_users", "portal")
        for project in self:
            old_visibility = visibility_before[project]
            if project.privacy_visibility == old_visibility:
                continue
            dbg.logic.debug(
                "_sync_access_to_privacy_visibility [project:%s]: %s -> %s",
                project.id,
                old_visibility,
                project.privacy_visibility,
            )
            if project.privacy_visibility in shared and old_visibility not in shared:
                project._add_collaborators(project.partner_id, access_mode="view")
                for task in project.task_ids.filtered("partner_id"):
                    task.message_subscribe(partner_ids=task.partner_id.ids)
            elif old_visibility in shared and project.privacy_visibility not in shared:
                portal_users = project.message_partner_ids.user_ids.filtered("share")
                dbg.pipeline.debug(
                    "[project:%s] visibility closed -> unsubscribing portal users %s, "
                    "clearing tokens",
                    project.id,
                    dbg.rec(portal_users),
                )
                project.message_unsubscribe(partner_ids=portal_users.partner_id.ids)
                project.task_ids._unsubscribe_portal_users()
                project.task_ids.access_token = ""
                project.access_token = ""

    def _is_project_sharing_accessible(self) -> bool:
        self.check_singleton()
        if self.privacy_visibility not in ["invited_users", "portal"]:
            dbg.logic.debug(
                "_is_project_sharing_accessible [project:%s]: visibility %s -> no",
                self.id,
                self.privacy_visibility,
            )
            return False
        if self.env.user._is_portal():
            accessible = bool(
                self.env["project.collaborator"].search_count(
                    [
                        ("project_id", "=", self.sudo().id),
                        ("partner_id", "=", self.env.user.partner_id.id),
                    ],
                    limit=1,
                )
            )
            dbg.logic.debug(
                "_is_project_sharing_accessible [project:%s]: portal user %s "
                "collaborator=%s",
                self.id,
                self.env.uid,
                accessible,
            )
            return accessible
        return self.env.user._is_internal()

    def _add_collaborators(
        self, partners: Any, access_mode: str = "advanced_edit"
    ) -> None:
        self.check_singleton()
        new_collaborators = self._get_new_collaborators(partners)
        dbg.lifecycle.debug(
            "_add_collaborators [project:%s]: %s -> new %s (mode=%s)",
            self.id,
            dbg.rec(partners),
            dbg.rec(new_collaborators),
            access_mode,
        )
        if not new_collaborators:
            return
        self.write(
            {
                "collaborator_ids": [
                    Command.create(
                        {
                            "partner_id": collaborator.id,
                            "access_mode": access_mode,
                        }
                    )
                    for collaborator in new_collaborators
                ],
            }
        )

    def _get_new_collaborators(self, partners: Any) -> list:
        self.check_singleton()
        return partners.filtered(
            lambda partner: (
                partner not in self.collaborator_ids.partner_id
                and partner.partner_share
            )
        )

    def _add_followers(self, partners: Any) -> None:
        self.check_singleton()
        self.message_subscribe(partners.ids)

        dict_tasks_per_partner = {}
        dict_partner_ids_to_subscribe_per_partner = {}
        for task in self.task_ids:
            if task.partner_id in dict_tasks_per_partner:
                dict_tasks_per_partner[task.partner_id] |= task
            else:
                partner_ids_to_subscribe = [
                    partner.id
                    for partner in partners
                    if partner == task.partner_id
                    or partner in task.partner_id.child_ids
                ]
                if partner_ids_to_subscribe:
                    dict_tasks_per_partner[task.partner_id] = task
                    dict_partner_ids_to_subscribe_per_partner[task.partner_id] = (
                        partner_ids_to_subscribe
                    )
        dbg.pipeline.debug(
            "[project:%s] _add_followers %s -> %d task partner groups",
            self.id,
            dbg.rec(partners),
            len(dict_tasks_per_partner),
        )
        for partner, tasks in dict_tasks_per_partner.items():
            tasks.message_subscribe(dict_partner_ids_to_subscribe_per_partner[partner])

    def _thread_to_store(
        self,
        store: Store,
        fields: list[str],
        *,
        request_list: list[str] | None = None,
    ) -> None:
        super()._thread_to_store(store, fields, request_list=request_list)
        if request_list and "followers" in request_list:
            store.add(
                self,
                {
                    "collaborator_ids": Store.Many(
                        self.sudo().collaborator_ids.partner_id, []
                    )
                },
                as_thread=True,
            )

    @api.depends("task_count", "open_task_count")
    def _compute_task_completion_percentage(self) -> None:
        for task in self:
            task.task_completion_percentage = (
                task.task_count and 1 - task.open_task_count / task.task_count
            )

    def _get_template_to_project_warnings(self) -> list:
        self.check_singleton()
        return []

    def action_confirm_template_to_project(self, callbacks: dict[str, Any]) -> None:
        self.check_singleton()
        pass

    def _get_template_to_project_confirmation_callbacks(self) -> dict:
        self.check_singleton()
        return {}

    def action_toggle_project_template_mode(self) -> dict | bool:
        self.check_singleton()
        config = {
            "params": {
                "project_id": self.id,
            },
        }
        if self.is_template:
            config["tag"] = "project_template_show_undo_confirmation_dialog"
            if callbacks := self._get_template_to_project_confirmation_callbacks():
                config["params"]["callback_data"] = {
                    "method": "action_confirm_template_to_project",
                    "args": [self.id, callbacks],
                }
            if warning_messages := self._get_template_to_project_warnings():
                config["params"]["message"] = self.env._(
                    "%(warning_messages)s\nAre you sure you want to continue?",
                    warning_messages="\n".join(warning_messages),
                )
            else:
                config["params"]["message"] = self.env._(
                    "This project is currently a template. Would you like to convert it back into a regular project?",
                )
        else:
            config["tag"] = "project_to_template_redirection_action"
        return {
            "type": "ir.actions.client",
            **config,
        }

    def action_undo_create_template_from_project(
        self, callbacks: dict[str, Any]
    ) -> None:
        self.check_singleton()
        if callbacks.get("unarchive_project"):
            self.action_unarchive()

    def _get_template_from_project_undo_callbacks(self) -> dict:
        self.check_singleton()
        callbacks = {}
        if self.active:
            self.action_archive()
            callbacks["unarchive_project"] = True
        return callbacks

    def action_create_template_from_project(self) -> dict:
        self.check_singleton()
        template = self.copy(default={"is_template": True, "partner_id": False})
        dbg.lifecycle.debug(
            "project.project.action_create_template_from_project %s -> template %s",
            self.id,
            template.id,
        )
        template._update_template_mode(True)
        template.message_post(body=self.env._("Template created from %s.", self.name))
        config = {
            "tag": "project_template_show_notification",
            "params": {
                "project_id": template.id,
                "undo_method": "unlink",
            },
        }
        if callbacks := self._get_template_from_project_undo_callbacks():
            config["params"]["callback_data"] = {
                "method": "action_undo_create_template_from_project",
                "args": [self.id, callbacks],
                "post_action": {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "type": "success",
                        "message": self.env._(
                            "Template converted back to regular project."
                        ),
                    },
                },
            }
        return {
            "type": "ir.actions.client",
            **config,
        }

    def action_undo_convert_to_template(self) -> dict | bool:
        self.check_singleton()
        self._update_template_mode(False)
        self.message_post(
            body=self.env._("Template converted back to regular project.")
        )
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "type": "success",
                "message": self.env._("Template converted back to regular project."),
                "next": {
                    "type": "ir.actions.client",
                    "tag": "soft_reload",
                },
            },
        }

    def _update_template_mode(self, is_template: bool) -> None:
        self.check_singleton()
        dbg.lifecycle.debug(
            "project.project._update_template_mode [project:%s]: is_template=%s",
            self.id,
            is_template,
        )
        self.is_template = is_template
        if not is_template:
            self.task_ids.role_ids = False

    @api.model
    def _get_template_default_context_whitelist(self) -> list[str]:
        return [
            "allow_milestones",
        ]

    @api.model
    def _get_template_field_blacklist(self) -> list[str]:
        return [
            "partner_id",
        ]

    @dbg.timed
    def action_create_from_template(
        self, values: dict | None = None, role_to_users_mapping: Any = None
    ) -> Self:
        self.check_singleton()
        values = values or {}
        dbg.lifecycle.debug(
            "project.project.action_create_from_template [project:%s]: values=%s",
            self.id,
            dbg.keys(values),
        )

        if self.date_start and self.date:
            if not values.get("date_start"):
                values["date_start"] = fields.Date.today()
            if not values.get("date"):
                values["date"] = values["date_start"] + (self.date - self.date_start)

        default = {
            key.removeprefix("default_"): value
            for key, value in self.env.context.items()
            if key.startswith("default_")
            and key.removeprefix("default_")
            in self._get_template_default_context_whitelist()
        } | values
        project = self.with_context(
            copy_from_template=True, copy_from_project_template=True
        ).copy(default=default)
        dbg.pipeline.debug(
            "[project:%s] create_from_template -> project %s (%d tasks)",
            self.id,
            project.id,
            len(project.task_ids),
        )
        project.message_post(
            body=self.env._("Project created from template %(name)s.", name=self.name)
        )

        if role_to_users_mapping and (
            mapping := role_to_users_mapping.filtered(lambda entry: entry.user_ids)
        ):
            for new_task in project.task_ids:
                for entry in mapping:
                    if entry.role_id in new_task.role_ids:
                        new_task.user_ids |= entry.user_ids

        project.task_ids.role_ids = False

        tasks_to_schedule = self.env["project.task"]
        first_possible_date_per_task = {}
        if project.date_start and self.date_start:
            delta = project.date_start - self.date_start
            project_start_datetime = datetime.combine(project.date_start, time.min)
            project_end_datetime = datetime.combine(
                project.date + timedelta(days=1), time.min
            )
            for original_task, copied_task in self._get_template_task_pairs(project):
                if original_task.date_start:
                    first_possible_date_per_task[copied_task.id] = (
                        original_task.date_start + delta
                    )
                    tasks_to_schedule += copied_task
        else:
            project_start_datetime = datetime.combine(
                project.date_start or fields.Date.today(), time.min
            )
            project_end_datetime = project_start_datetime + timedelta(days=365)
            for original_task, copied_task in self._get_template_task_pairs(project):
                if original_task.date_start:
                    tasks_to_schedule += copied_task
        dbg.pipeline.debug(
            "[project:%s] create_from_template -> schedule %s in %s..%s (%d pinned)",
            project.id,
            dbg.rec(tasks_to_schedule),
            project_start_datetime,
            project_end_datetime,
            len(first_possible_date_per_task),
        )
        tasks_to_schedule._schedule_tasks(
            {
                "date_start": datetime.strftime(
                    project_start_datetime, "%Y-%m-%d %H:%M:%S"
                ),
                "date_end": datetime.strftime(
                    project_end_datetime, "%Y-%m-%d %H:%M:%S"
                ),
            },
            project_end_datetime,
            first_possible_date_per_task=first_possible_date_per_task,
        )
        return project

    def _get_template_task_pairs(self, project):

        def pair(originals, copies):
            if len(originals) != len(copies):
                raise ValueError(
                    f"template {self.id} has {len(originals)} tasks at a level "
                    f"where its copy {project.id} has {len(copies)}"
                )
            copy_per_name = {}
            for copy in copies:
                if copy.name in copy_per_name:
                    raise UserError(
                        self.env._(
                            "Two tasks of template %(template)s are both named "
                            "%(task)s. Rename one: task names are what carry the "
                            "planned dates across to the new project.",
                            template=self.display_name,
                            task=copy.name,
                        )
                    )
                copy_per_name[copy.name] = copy
            for original in originals:
                copy = copy_per_name.get(original.name)
                if copy is None:
                    raise ValueError(
                        f"template {self.id} task {original.name!r} has no copy "
                        f"of that name in {project.id}"
                    )
                yield original, copy
                yield from pair(original.child_ids, copy.child_ids)

        def get_root_tasks(tasks):
            return tasks.filtered(lambda task: not task.parent_id)

        yield from pair(get_root_tasks(self.task_ids), get_root_tasks(project.task_ids))
