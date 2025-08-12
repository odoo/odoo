# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, Command, fields, models
from odoo.exceptions import ValidationError

from dateutil.relativedelta import relativedelta


class ProjectTaskRecurrence(models.Model):
    _name = 'project.task.recurrence'
    _description = 'Task Recurrence'

    task_ids = fields.One2many('project.task', 'recurrence_id', copy=False)

    repeat_interval = fields.Integer(string='Repeat Every', default=1)
    repeat_unit = fields.Selection([
        ('day', 'Days'),
        ('week', 'Weeks'),
        ('month', 'Months'),
        ('year', 'Years'),
    ], default='week', export_string_translation=False)
    repeat_type = fields.Selection([
        ('forever', 'Forever'),
        ('until', 'Until'),
    ], default="forever", string="Until")
    repeat_until = fields.Date(string="End Date")

    @api.constrains('repeat_interval')
    def _check_repeat_interval(self):
        if self.filtered(lambda t: t.repeat_interval <= 0):
            raise ValidationError(_('The interval should be greater than 0'))

    @api.constrains('repeat_type', 'repeat_until')
    def _check_repeat_until_date(self):
        today = fields.Date.today()
        if self.filtered(lambda t: t.repeat_type == 'until' and t.repeat_until < today):
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

    def _get_recurrence_delta(self):
        return relativedelta(**{
            f"{self.repeat_unit}s": self.repeat_interval
        })

    @api.model
    def _create_next_occurrences(self, occurrences_from):
        tasks_copy = self.env['project.task']
        occurrences_from = occurrences_from.filtered(lambda task:
            task.recurrence_id.repeat_type != 'until' or
            not task.date_deadline or task.recurrence_id.repeat_until and
            (task.date_deadline + task.recurrence_id._get_recurrence_delta()).date() <= task.recurrence_id.repeat_until
        )
        if occurrences_from:
            recurrence_by_task = {task: task.recurrence_id for task in occurrences_from}
            tasks_copy = self.env['project.task'].create(
                self._create_next_occurrences_values(recurrence_by_task)
            )
            occurrences_from._resolve_copied_dependencies(tasks_copy)
        return tasks_copy

    @api.model
    def _create_next_occurrences_values(self, recurrence_by_task):
        tasks = self.env['project.task'].concat(*recurrence_by_task.keys())
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
            create_values = {
                'priority': '0',
                'stage_id': task.sudo().project_id.type_ids[0].id if task.sudo().project_id.type_ids else task.stage_id.id,
                'child_ids': [Command.create(vals) for vals in self._create_next_occurrences_values({child: recurrence for child in task.child_ids})]
            }
            create_values.update({
                field: value[0] if isinstance(value, tuple) else value
                for field, value in fields_to_copy.items()
            })
            create_values.update({
                field: value and value + recurrence._get_recurrence_delta()
                for field, value in fields_to_postpone.items()
            })
            copy_data.update(create_values)
            list_create_values.append(copy_data)

        return list_create_values
