from collections import defaultdict
from typing import Self

from odoo import api, fields, models
from odoo.api import ValuesType
from odoo.tools import format_date

from ..tools import debug_log as dbg
from .project_task import CLOSED_STATES


class ProjectMilestone(models.Model):
    _name = "project.milestone"
    _description = "Project Milestone"
    _inherit = ["mixin.mail.thread"]
    _order = "sequence, date_deadline, is_reached desc, name"

    def _default_project_id(self) -> int | bool:
        return self.env.context.get("default_project_id") or self.env.context.get(
            "active_id"
        )

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    project_id = fields.Many2one(
        comodel_name="project.project",
        default=_default_project_id,
        index=True,
        required=True,
        domain=[("is_template", "=", False)],
        ondelete="cascade",
    )
    date_deadline = fields.Date(
        copy=False,
        tracking=True,
    )
    is_reached = fields.Boolean(
        string="Reached",
        default=False,
        copy=False,
    )
    date_reached = fields.Date(
        export_string_translation=False,
        compute="_compute_date_reached",
        store=True,
    )
    task_ids = fields.One2many(
        comodel_name="project.task",
        inverse_name="milestone_id",
        string="Tasks",
        export_string_translation=False,
    )
    project_allow_milestones = fields.Boolean(
        export_string_translation=False,
        compute="_compute_project_allow_milestones",
        search="_search_project_allow_milestones",
        compute_sudo=True,
    )

    is_deadline_exceeded = fields.Boolean(
        export_string_translation=False,
        compute="_compute_is_deadline_exceeded",
    )
    is_deadline_future = fields.Boolean(
        export_string_translation=False,
        compute="_compute_is_deadline_future",
    )
    task_count = fields.Integer(
        string="# of Tasks",
        export_string_translation=False,
        compute="_compute_task_counts",
        groups="project.group_project_milestone",
    )
    done_task_count = fields.Integer(
        string="# of Done Tasks",
        export_string_translation=False,
        compute="_compute_task_counts",
        groups="project.group_project_milestone",
    )
    can_be_marked_as_done = fields.Boolean(
        export_string_translation=False,
        compute="_compute_can_be_marked_as_done",
    )

    @api.depends("is_reached")
    def _compute_date_reached(self) -> None:
        for ms in self:
            ms.date_reached = ms.is_reached and fields.Date.context_today(self)

    @api.depends("is_reached", "date_deadline")
    def _compute_is_deadline_exceeded(self) -> None:
        today = fields.Date.context_today(self)
        for ms in self:
            ms.is_deadline_exceeded = (
                not ms.is_reached and ms.date_deadline and ms.date_deadline < today
            )

    @api.depends("date_deadline")
    def _compute_is_deadline_future(self) -> None:
        for ms in self:
            ms.is_deadline_future = (
                ms.date_deadline and ms.date_deadline > fields.Date.context_today(self)
            )

    @dbg.timed
    @api.depends("task_ids.milestone_id")
    def _compute_task_counts(self) -> None:
        all_and_done_task_count_per_milestone = {
            milestone.id: (
                count,
                sum(state in CLOSED_STATES for state in state_list),
            )
            for milestone, count, state_list in self.env["project.task"]._read_group(
                [
                    ("milestone_id", "in", self.ids),
                    ("allow_milestones", "=", True),
                ],
                ["milestone_id"],
                ["__count", "state:array_agg"],
            )
        }
        for milestone in self:
            milestone.task_count, milestone.done_task_count = (
                all_and_done_task_count_per_milestone.get(milestone.id, (0, 0))
            )

    @dbg.timed
    @api.depends("is_reached", "task_ids.state", "task_ids.is_closed")
    def _compute_can_be_marked_as_done(self) -> None:
        if not any(self._ids):
            for milestone in self:
                milestone.can_be_marked_as_done = (
                    not milestone.is_reached
                    and bool(milestone.task_ids)
                    and all(milestone.task_ids.mapped(lambda t: t.is_closed))
                )
            return

        unreached_milestones = self.filtered(lambda milestone: not milestone.is_reached)
        (self - unreached_milestones).can_be_marked_as_done = False
        task_read_group = self.env["project.task"]._read_group(
            [("milestone_id", "in", unreached_milestones.ids)],
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
        for milestone in unreached_milestones:
            opened_task_count, closed_task_count = task_count_per_milestones[
                milestone.id
            ]
            milestone.can_be_marked_as_done = (
                closed_task_count > 0 and not opened_task_count
            )

    @api.depends("project_id.allow_milestones")
    def _compute_project_allow_milestones(self) -> None:
        for milestone in self:
            milestone.project_allow_milestones = milestone.project_id.allow_milestones

    def _search_project_allow_milestones(self, operator: str, value: bool) -> list:
        query = (
            self.env["project.project"]
            .sudo()
            ._search(
                [
                    ("allow_milestones", operator, value),
                ]
            )
        )
        return [("project_id", "in", query)]

    def update_is_reached(self, is_reached: bool) -> dict:
        self.check_singleton()
        dbg.lifecycle.debug(
            "project.milestone.update_is_reached %s: %s -> %s",
            dbg.rec(self),
            self.is_reached,
            is_reached,
        )
        self.update({"is_reached": is_reached})
        return self._get_export_values()

    def action_view_tasks(self) -> dict:
        self.check_singleton()
        action = self.env["ir.actions.act_window"]._get_action_dict_by_xml_id(
            "project.action_view_task_from_milestone"
        )
        action["context"] = {
            "default_project_id": self.project_id.id,
            "default_milestone_id": self.id,
        }
        if self.task_count == 1:
            action["view_mode"] = "form"
            action["res_id"] = self.task_ids.id
            if "views" in action:
                action["views"] = [
                    (view_id, view_type)
                    for view_id, view_type in action["views"]
                    if view_type == "form"
                ]
        return action

    @api.model
    def _get_fields_to_export(self) -> list[str]:
        return [
            "id",
            "name",
            "date_deadline",
            "is_reached",
            "date_reached",
            "is_deadline_exceeded",
            "is_deadline_future",
            "can_be_marked_as_done",
            "sequence",
        ]

    def _get_export_values(self) -> dict:
        self.check_singleton()
        return {field: self[field] for field in self._get_fields_to_export()}

    def _get_export_values_list(self) -> list[dict]:
        return [ms._get_export_values() for ms in self]

    def copy(self, default: ValuesType | None = None) -> Self:
        default = dict(default or {})
        new_milestones = super().copy(default)
        milestone_mapping = self.env.context.get("milestone_mapping", {})
        for old_milestone, new_milestone in zip(self, new_milestones, strict=True):
            if old_milestone.project_id.allow_milestones:
                milestone_mapping[old_milestone.id] = new_milestone.id
        dbg.lifecycle.debug(
            "project.milestone.copy %s -> %s (mapping now %d entries)",
            dbg.rec(self),
            dbg.rec(new_milestones),
            len(milestone_mapping),
        )
        return new_milestones

    @api.depends_context("lang", "display_milestone_deadline")
    def _compute_display_name(self) -> None:
        super()._compute_display_name()
        if not self.env.context.get("display_milestone_deadline"):
            return
        for milestone in self:
            if milestone.date_deadline:
                milestone.display_name = f"{milestone.display_name} - {format_date(self.env, milestone.date_deadline)}"
