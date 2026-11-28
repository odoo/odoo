# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, Command, fields, models
from odoo.exceptions import ValidationError


class ProjectTaskRecurrence(models.Model):
    _name = 'project.task.recurrence'
    _inherit = ['mail.recurrence.rule.mixin']
    _description = 'Task Recurrence'

    task_ids = fields.One2many('project.task', 'recurrence_id', copy=False)

    def _inverse_rrule(self):
        # The rule is only built from the recurrence fields, never set from an rrule string.
        # Parsing it back would turn 'forever' into 'count' (forever is serialized with a count limit).
        pass

    @api.constrains('interval')
    def _check_repeat_interval(self):
        if self.filtered(lambda t: t.interval <= 0):
            raise ValidationError(_('The interval should be greater than 0'))

    @api.constrains('end_type', 'until')
    def _check_repeat_until_date(self):
        today = fields.Date.context_today(self)
        if self.filtered(lambda t: t.end_type == 'end_date' and t.until < today):
            raise ValidationError(_('The end date should be in the future'))

    @api.model
    def _get_recurring_fields_to_copy(self):
        return [
            'recurrence_id',
        ]

    @api.model
    def _get_recurring_fields_to_postpone(self):
        return [
            'date_deadline',
        ]

    def _get_last_task_id_per_recurrence_id(self):
        return {} if not self else {
            recurrence.id: max_task_id
            for recurrence, max_task_id in self.env['project.task'].sudo()._read_group(
                [('recurrence_id', 'in', self.ids)],
                ['recurrence_id'],
                ['id:max'],
            )
        }

    def _get_next_date(self, current_date):
        self.ensure_one()
        rule = self._get_rrule(dtstart=current_date)
        return rule.after(current_date)

    def _get_postpone_delta(self, task, fields_to_postpone):
        """ Return how much the dates of the next occurrence of `task` must be postponed:
        the gap between its deadline (or first date to postpone) and the next date of the
        recurrence, so that all of its dates, and those of its sub-tasks, keep the same gaps.
        """
        self.ensure_one()
        anchor = task.date_deadline or next((value for value in fields_to_postpone.values() if value), None)
        next_date = anchor and self._get_next_date(anchor)
        return next_date and next_date - anchor

    @api.model
    def _create_next_occurrences(self, occurrences_from):
        tasks_copy = self.env['project.task']

        count_recurrences = occurrences_from.recurrence_id.sudo().filtered(lambda rec: rec.end_type == 'count')
        task_count_per_recurrence = dict(self.env['project.task'].sudo()._read_group(
            [('recurrence_id', 'in', count_recurrences.ids)], ['recurrence_id'], ['__count'],
        )) if count_recurrences else {}

        def should_create_occurrence(task):
            rec = task.recurrence_id.sudo()
            if rec.end_type == 'count' and task_count_per_recurrence.get(rec, 0) >= rec.count:
                return False
            return not task.date_deadline or bool(rec._get_next_date(task.date_deadline))

        occurrences_from = occurrences_from.filtered(should_create_occurrence)

        if occurrences_from:
            recurrence_by_task = {task: task.recurrence_id.sudo() for task in occurrences_from}
            tasks_copy = self.env['project.task'].sudo().create(
                self._create_next_occurrences_values(recurrence_by_task)
            ).sudo(False)
            occurrences_from._resolve_copied_dependencies(tasks_copy)
        return tasks_copy

    @api.model
    def _create_next_occurrences_values(self, recurrence_by_task, postpone_delta_by_task=None):
        tasks = self.env['project.task'].concat(recurrence_by_task.keys())
        list_create_values = []
        list_copy_data = tasks.with_context(copy_project=True, active_test=False).sudo().copy_data()
        list_fields_to_copy = tasks._read_format(self._get_recurring_fields_to_copy())
        list_fields_to_postpone = tasks._read_format(self._get_recurring_fields_to_postpone())

        for task, copy_data, fields_to_copy, fields_to_postpone in zip(
            tasks,
            list_copy_data,
            list_fields_to_copy,
            list_fields_to_postpone
        ):
            recurrence = recurrence_by_task[task]
            fields_to_postpone.pop('id', None)
            # sub-tasks are postponed as much as their parent task
            if postpone_delta_by_task and postpone_delta_by_task.get(task):
                postpone_delta = postpone_delta_by_task[task]
            else:
                postpone_delta = recurrence._get_postpone_delta(task, fields_to_postpone)
            create_values = {
                'priority': '0',
                'stage_id': task.sudo().project_id.type_ids[0].id if task.sudo().project_id.type_ids else task.stage_id.id,
                'child_ids': [Command.create(vals) for vals in self._create_next_occurrences_values(
                    {child: recurrence for child in task.child_ids},
                    {child: postpone_delta for child in task.child_ids},
                )],
            }
            create_values.update({
                field: value[0] if isinstance(value, tuple) else value
                for field, value in fields_to_copy.items()
            })
            create_values.update({
                field: value + postpone_delta if value and postpone_delta else value
                for field, value in fields_to_postpone.items()
            })
            copy_data.update(create_values)
            list_create_values.append(copy_data)

        return list_create_values
