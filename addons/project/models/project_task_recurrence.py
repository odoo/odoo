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
        self.ensure_one()
        # Prevent double mail_followers creation
        create_values = self._create_next_occurrence_values(occurrence_from)
        date_deadline = create_values['date_deadline']
        if not (self.repeat_type == 'until' and date_deadline and date_deadline.date() > self.repeat_until):
            occurrence_from.with_context(copy_project=True).sudo().copy(create_values)

    def _create_next_occurrence_values(self, occurrence_from):
        self.ensure_one()
        fields_to_copy = occurrence_from.read(self._get_recurring_fields_to_copy()).pop()
        create_values = {
            field: value[0] if isinstance(value, tuple) else value
            for field, value in fields_to_copy.items()
        }

        fields_to_postpone = occurrence_from.read(self._get_recurring_fields_to_postpone()).pop()
        fields_to_postpone.pop('id', None)
        create_values.update({
            field: value and value + self._get_recurrence_delta()
            for field, value in fields_to_postpone.items()
        })

        create_values['priority'] = '0'
        create_values['stage_id'] = occurrence_from.project_id.type_ids[0].id if occurrence_from.project_id.type_ids else occurrence_from.stage_id.id
        create_values['child_ids'] = [
            child.with_context(copy_project=True).sudo().copy(self._create_next_occurrence_values(child)).id for child in occurrence_from.with_context(active_test=False).child_ids
        ]
        return create_values
