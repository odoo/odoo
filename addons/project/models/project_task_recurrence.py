# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
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

    def _create_next_occurrence(self, occurrence_from):
        occurences_from = occurences_from.filtered(lambda task:
            task.recurrence_id.repeat_type != 'until' or
            task.recurrence_id.repeat_until >= fields.Date.today()
        )

        fields_to_copy = self._get_recurring_fields_to_copy()
        fields_to_postpone = self._get_recurring_fields_to_postpone()

        recordset = self.env['project.task']

        for task_from in occurences_from:
            task_copy = task.with_context(copy_project=True).sudo().copy()
            recordset |= task_copy
            stack = {task: task_copy}

            while stack:
                tasks_from, tasks_copy = stack.popitem()
                child_tasks = tasks_from.child_ids
                if not child_tasks: continue

                child_tasks_copy_data_list = child_tasks.with_context(copy_project=True).sudo().copy_data({'child_ids': []})
                fields_copy_list = child_tasks._read_format(fields_to_copy)
                fields_postpone_list = child_tasks._read_format(fields_to_postpone)

                for child_task, child_tasks_copy_data, fields_copy, fields_postpone in zip(child_tasks, child_tasks_copy_data_list, fields_copy_list, fields_postpone_list):
                    update_dict = {
                        field: value[0] if isinstance(value, tuple) else value
                        for field, value in fields_copy.items()
                    }
                    fields_postpone.pop('id', None)
                    update_dict.update({
                        field: value and value + self._get_recurrence_delta()
                        for field, value in fields_postpone.items()
                    })
                    update_dict.update({
                        'priority': '0',
                        'stage_id': child_task.project_id.type_ids[0].id if child_task.project_id.type_ids else child_task.stage_id.id,
                    })
                    child_tasks_copy_data.update(update_dict)

                child_tasks_copy = self.env['project.task'].create(child_tasks_copy_data_list)
                task_copy.child_ids = child_tasks_copy

                for child_task, child_task_copy in zip(child_tasks, child_tasks_copy):
                    stack[child_task] = child_tasks_copy

        return recordset
