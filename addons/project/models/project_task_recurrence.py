# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, Command, fields, models
from odoo.exceptions import ValidationError, UserError
from dateutil import rrule

RRULE_WEEKDAYS = {'SUN': rrule.SU, 'MON': rrule.MO, 'TUE': rrule.TU, 'WED': rrule.WE, 'THU': rrule.TH, 'FRI': rrule.FR, 'SAT': rrule.SA}
REPEAT_UNIT_TO_RRULE = {
    'day': rrule.DAILY,
    'week': rrule.WEEKLY,
    'weekday': rrule.WEEKLY,
    'month': rrule.MONTHLY,
    'monthday': rrule.MONTHLY,
    'year': rrule.YEARLY,
}
MONTH_BY_SELECTION = [
    ('date', 'Date of month'),
    ('day', 'Day of month'),
]
BYDAY_SELECTION = [
    ('1', 'First'),
    ('2', 'Second'),
    ('3', 'Third'),
    ('4', 'Fourth'),
    ('-1', 'Last'),
]
WEEKDAY_SELECTION = [
    ('MON', 'Monday'),
    ('TUE', 'Tuesday'),
    ('WED', 'Wednesday'),
    ('THU', 'Thursday'),
    ('FRI', 'Friday'),
    ('SAT', 'Saturday'),
    ('SUN', 'Sunday'),
]
REPEAT_UNIT_SELECTION = [
    ('day', 'Days'),
    ('week', 'Weeks'),
    ('weekday', 'Week Days'),
    ('month', 'Months'),
    ('monthday', 'Month Days'),
    ('year', 'Years'),
]


class ProjectTaskRecurrence(models.Model):
    _name = 'project.task.recurrence'
    _description = 'Task Recurrence'

    task_ids = fields.One2many('project.task', 'recurrence_id', copy=False)

    repeat_interval = fields.Integer(string='Repeat Every', default=1)
    repeat_unit = fields.Selection(REPEAT_UNIT_SELECTION, default='week', export_string_translation=False)
    repeat_type = fields.Selection([
        ('forever', 'Forever'),
        ('until', 'Until'),
    ], default="forever", string="Until")
    repeat_until = fields.Date(string="End Date")
    mon = fields.Boolean()
    tue = fields.Boolean()
    wed = fields.Boolean()
    thu = fields.Boolean()
    fri = fields.Boolean()
    sat = fields.Boolean()
    sun = fields.Boolean()
    month_by = fields.Selection(MONTH_BY_SELECTION, default='date')
    repeat_date_of_month = fields.Integer(default=1)
    repeat_by_day_month = fields.Selection(BYDAY_SELECTION, string='By day')
    repeat_by_weekday_month = fields.Selection(WEEKDAY_SELECTION, string='Weekday')

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

    def _get_week_list(self):
        return tuple(
            rrule.weekday(index)
            for index, isScheduled in {
            rrule.MO.weekday: self.mon,
            rrule.TU.weekday: self.tue,
            rrule.WE.weekday: self.wed,
            rrule.TH.weekday: self.thu,
            rrule.FR.weekday: self.fri,
            rrule.SA.weekday: self.sat,
            rrule.SU.weekday: self.sun
            }.items() if isScheduled)

    def _get_recurrence_delta(self, deadline):
        self.ensure_one()
        rrule_params = dict(
            dtstart=deadline,
            interval=self.repeat_interval,
            count=2
        )
        if self.repeat_unit == 'weekday':
            weekdays = self._get_week_list()
            if not weekdays:
                raise UserError(_("You have to choose at least one day in the week to schedule taskes based on days of the week"))
            rrule_params['byweekday'] = weekdays
            rrule_params['wkst'] = rrule.weekday(int(self.env['res.lang']._get_data(code=self.env.user.lang).week_start) - 1)
            rrule_params['interval'] = 1
            # If you schedule on specific days of the week no intervl should be added
        elif self.repeat_unit == 'monthday':
            if self.month_by == 'date':
                rrule_params['bymonthday'] = self.repeat_date_of_month
            elif self.month_by == 'day':
                rrule_params['byweekday'] = RRULE_WEEKDAYS[self.repeat_by_weekday_month](int(self.repeat_by_day_month))
        rrule_date = rrule.rrule(REPEAT_UNIT_TO_RRULE[self.repeat_unit], **rrule_params)
        # rrule will give out the start date if it is considered valid, which is unwanted since we want the next date from rrule
        # we therefor calculate 2 dates and take the one that is the earliest and is not equal or smaller than the start date.
        ret = rrule_date[1] if rrule_date[0] == deadline else rrule_date[0]
        return ret - deadline

    @api.model
    def _create_next_occurrences(self, occurrences_from):
        tasks_copy = self.env['project.task']

        def should_create_occurrence(task):
            rec = task.recurrence_id.sudo()
            return (
                rec.repeat_type != 'until' or
                not task.date_deadline or
                rec.repeat_until and
                (task.date_deadline + rec._get_recurrence_delta(task.date_deadline)).date() <= rec.repeat_until
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
            if (task.date_deadline):
                delta = recurrence._get_recurrence_delta(task.date_deadline)
                create_values.update({
                    field: value and value + delta
                    for field, value in fields_to_postpone.items()
                })
            copy_data.update(create_values)
            list_create_values.append(copy_data)

        return list_create_values
