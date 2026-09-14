from datetime import datetime, timedelta
from typing import Self

from odoo import Command, _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.libs.datetime import timezone

from ..tools import debug_log as dbg


class ProjectTaskRecurrence(models.Model):
    _name = "project.task.recurrence"
    _description = "Task Recurrence"
    _inherit = ["mixin.recurrence.rule"]

    task_ids = fields.One2many(
        comodel_name="project.task",
        inverse_name="recurrence_id",
        copy=False,
    )

    repeat_until = fields.Date(string="End Date")
    date_recurrence_origin = fields.Datetime(copy=False)
    recurrence_anchor_field = fields.Char(copy=False)

    @api.constrains("repeat_type", "repeat_until")
    def _check_repeat_until_date(self) -> None:
        today = fields.Date.today()
        if self.filtered(lambda t: t.repeat_type == "until" and not t.repeat_until):
            raise ValidationError(_("The end date is required for 'Until' recurrence."))
        if self.filtered(
            lambda t: (
                t.repeat_type == "until" and t.repeat_until and t.repeat_until < today
            )
        ):
            raise ValidationError(_("The end date should be in the future"))

    def write(self, vals) -> bool:
        if "date_recurrence_origin" not in vals and vals.keys() & {
            "repeat_interval",
            "repeat_unit",
        }:
            vals = {
                **vals,
                "date_recurrence_origin": False,
                "recurrence_anchor_field": False,
            }
        return super().write(vals)

    @api.model
    def _get_recurring_fields_to_copy(self) -> list[str]:
        return [
            "recurrence_id",
        ]

    @api.model
    def _get_recurring_fields_to_postpone(self) -> list[str]:
        return [
            "date_end",
            "date_start",
        ]

    def _get_occurrence_anchor(self, task) -> tuple[str, datetime] | tuple[None, None]:
        return next(
            (
                (field, task[field])
                for field in self._get_recurring_fields_to_postpone()
                if task[field]
            ),
            (None, None),
        )

    def _get_next_occurrence_shift(self, task) -> timedelta | None:
        self.check_singleton()
        field, anchor = self._get_occurrence_anchor(task)
        if not anchor:
            return None
        origin = (
            self.date_recurrence_origin
            if self.date_recurrence_origin and self.recurrence_anchor_field == field
            else anchor
        )
        tz = timezone((task.company_id or self.env.company).partner_id.tz or "UTC")
        return self._get_next_recurrence_after(origin, anchor, tz) - anchor

    def _get_last_task_id_per_recurrence_id(self) -> dict[int, int]:
        return (
            {}
            if not self
            else {
                recurrence.id: max_task_id
                for recurrence, max_task_id in self.env["project.task"]
                .sudo()
                ._read_group(
                    [("recurrence_id", "in", self.ids)],
                    ["recurrence_id"],
                    ["id:max"],
                )
            }
        )

    @dbg.timed
    @api.model
    def _create_next_occurrences(self, occurrences_from: Self) -> Self:
        tasks_copy = self.env["project.task"]
        requested = occurrences_from

        def is_occurrence_allowed(task) -> bool:
            rec = task.recurrence_id.sudo()
            return (
                rec.repeat_type != "until"
                or not task.date_end
                or (
                    rec.repeat_until
                    and fields.Datetime.context_timestamp(
                        rec, task.date_end + rec._get_next_occurrence_shift(task)
                    ).date()
                    <= rec.repeat_until
                )
            )

        occurrences_from = occurrences_from.filtered(is_occurrence_allowed)
        dbg.logic.debug(
            "recurrence._create_next_occurrences: %s allowed of %s "
            "(repeat_until reached on the rest)",
            dbg.rec(occurrences_from),
            dbg.rec(requested),
        )

        if occurrences_from:
            recurrence_by_task = {
                task: task.recurrence_id.sudo() for task in occurrences_from
            }
            tasks_copy = (
                self.env["project.task"]
                .sudo()
                .create(self._prepare_next_occurrence_vals_list(recurrence_by_task))
                .sudo(False)
            )
            for task, recurrence in recurrence_by_task.items():
                field, anchor = recurrence._get_occurrence_anchor(task)
                if anchor and (
                    not recurrence.date_recurrence_origin
                    or recurrence.recurrence_anchor_field != field
                ):
                    recurrence.write(
                        {
                            "date_recurrence_origin": anchor,
                            "recurrence_anchor_field": field,
                        }
                    )
            dbg.lifecycle.debug(
                "recurrence._create_next_occurrences: %s -> %s",
                dbg.rec(occurrences_from),
                dbg.rec(tasks_copy),
            )
            dbg.pipeline.debug(
                "[recurrence:%s] next occurrences -> copy dependencies",
                dbg.lazy(
                    lambda: sorted({rec.id for rec in recurrence_by_task.values()})
                ),
            )
            occurrences_from._update_copied_dependencies(tasks_copy)
        return tasks_copy

    @api.model
    def _prepare_next_occurrence_vals_list(
        self, recurrence_by_task: dict, shift_by_task: dict | None = None
    ) -> list[dict]:
        shift_by_task = shift_by_task or {}
        tasks = self.env["project.task"].concat(*recurrence_by_task.keys())
        list_create_values = []
        list_copy_data = (
            tasks.with_context(copy_project=True, active_test=False).sudo().copy_data()
        )
        list_fields_to_copy = tasks.sudo()._read_format(
            self._get_recurring_fields_to_copy()
        )
        list_fields_to_postpone = tasks.sudo()._read_format(
            self._get_recurring_fields_to_postpone()
        )

        for task, copy_data, fields_to_copy, fields_to_postpone in zip(
            tasks,
            list_copy_data,
            list_fields_to_copy,
            list_fields_to_postpone,
            strict=True,
        ):
            recurrence = recurrence_by_task[task]
            shift = (
                shift_by_task[task]
                if task in shift_by_task
                else recurrence._get_next_occurrence_shift(task)
            )
            if shift is None:
                shift = recurrence._get_recurrence_delta()
            fields_to_copy.pop("id", None)
            fields_to_postpone.pop("id", None)
            create_values = {
                "priority": "0",
                "step_id": (
                    task.sudo().project_id.workflow_step_ids[0].id
                    if task.sudo().project_id.workflow_step_ids
                    else task.step_id.id
                ),
                "child_ids": [
                    Command.create(vals)
                    for vals in self._prepare_next_occurrence_vals_list(
                        dict.fromkeys(task.child_ids, recurrence),
                        dict.fromkeys(task.child_ids, shift),
                    )
                ],
            }
            create_values.update(
                {
                    field: value[0] if isinstance(value, tuple) else value
                    for field, value in fields_to_copy.items()
                }
            )
            create_values.update(
                {
                    field: value and value + shift
                    for field, value in fields_to_postpone.items()
                }
            )
            dbg.logic.debug(
                "_prepare_next_occurrence_vals_list %s: step=%s postponed=%s "
                "children=%d",
                dbg.rec(task),
                create_values["step_id"],
                dbg.lazy(
                    lambda vals=create_values, postponed=fields_to_postpone: {
                        field: vals[field] for field in postponed if field in vals
                    }
                ),
                len(create_values["child_ids"]),
            )
            copy_data.update(create_values)
            list_create_values.append(copy_data)

        return list_create_values
