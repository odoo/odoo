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
        today = fields.Date.context_today(self)
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

        def should_create_occurrence(task):
            rec = task.recurrence_id.sudo()
            return (
                rec.repeat_type != 'until' or
                not task.date_deadline or
                rec.repeat_until and
                (task.date_deadline + rec._get_recurrence_delta()).date() <= rec.repeat_until
            )

        occurrences_from = occurrences_from.filtered(should_create_occurrence)

        if occurrences_from:
            recurrence_by_task = {task: task.recurrence_id.sudo() for task in occurrences_from}
            tasks_copy = self.env['project.task'].sudo().create(
                self._create_next_occurrences_values(recurrence_by_task)
            ).sudo(False)
            occurrences_from._resolve_copied_dependencies(tasks_copy)
        return tasks_copy

    @api.model
    def _create_next_occurrences_values(self, recurrence_by_task):
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
            create_values = {
                'priority': '0',
                'stage_id': task.sudo().project_id.type_ids[0].id if task.sudo().project_id.type_ids else task.stage_id.id,
                'child_ids': [Command.create(vals) for vals in self._create_next_occurrences_values({child: recurrence for child in task.child_ids})]
            }

            if fields_to_postpone.get('date_deadline'):
                start_dt, end_dt, planned_data, fields_to_postpone = self._plan_task(fields_to_postpone, self._get_original_task(recurrence), recurrence)
                copy_data = self._filter_non_working_employees(copy_data, self._get_original_task(recurrence), task, start_dt, end_dt)
                create_values.update(planned_data)

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

    def _filter_non_working_employees(self, data, original_task, last_task, next_task_date_begin, next_task_date_deadline):
        '''
        Filters out all users that should not be assign to this perticular reccurent task
        and adds back in the user that should be assigned, if they weren't in the previous task.
        This function is inherited by other modules.

        :param data: the data used to creat this recurent task

        :param original_task: the task that originaly started the recurrence

        :param last_task: the previous task that trigger the creation of this task

        :param next_task_date_begin: the begin datetime for this task

        :param next_task_date_deadline: the end/deadline for this task

        :return: the updated data with the correct users.
        '''
        return data

    def _plan_task(self, field_data, original_task, recurrence):
        '''
        Plans the recuring task. This function is inherited by other modules.

        :param field_data: the time dependent fields for the new task

        :param original_task: the task that originaly started the recurrence

        :return: returns a turple with the four following values:
            - The datetime at which the task has been planned to start
            - The datetime at which the task has been planned to end
            - A dictionary containg all the planned time dependant fields in 'field_data'
            - A dictionary containg all the unused time dependent fields in 'field_data'
        '''
        new_data = {}
        has_start = hasattr(self.env['project.task'], 'planned_date_begin') and field_data['planned_date_begin']
        new_data.update({
                field: value and value + recurrence._get_recurrence_delta()
                for field, value in field_data.items()
            })
        field_data = {}
        date_deadline = new_data['date_deadline']
        date_begin = new_data['planned_date_begin'] if has_start else False
        return (date_begin, date_deadline, new_data, field_data)

    def _get_original_task(self, recurrence):
        return recurrence.task_ids[0]
