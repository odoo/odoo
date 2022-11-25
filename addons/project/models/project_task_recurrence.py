# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.exceptions import ValidationError

from calendar import monthrange
from dateutil.relativedelta import relativedelta
from dateutil.rrule import rrule, rruleset, DAILY, WEEKLY, MONTHLY, YEARLY, MO, TU, WE, TH, FR, SA, SU

MONTHS = {
    'january': 31,
    'february': 28,
    'march': 31,
    'april': 30,
    'may': 31,
    'june': 30,
    'july': 31,
    'august': 31,
    'september': 30,
    'october': 31,
    'november': 30,
    'december': 31,
}

DAYS = {
    'mon': MO,
    'tue': TU,
    'wed': WE,
    'thu': TH,
    'fri': FR,
    'sat': SA,
    'sun': SU,
}

WEEKS = {
    'first': 1,
    'second': 2,
    'third': 3,
    'last': 4,
}

class ProjectTaskRecurrence(models.Model):
    _name = 'project.task.recurrence'
    _description = 'Task Recurrence'

    task_ids = fields.One2many('project.task', 'recurrence_id', copy=False)
    next_recurrence_date = fields.Date()
    recurrence_left = fields.Integer(string="Number of Tasks Left to Create", copy=False)

    repeat_interval = fields.Integer(string='Repeat Every', default=1)
    repeat_unit = fields.Selection([
        ('day', 'Days'),
        ('week', 'Weeks'),
        ('month', 'Months'),
        ('year', 'Years'),
    ], default='week')
    repeat_type = fields.Selection([
        ('forever', 'Forever'),
        ('until', 'End Date'),
        ('after', 'Number of Repetitions'),
    ], default="forever", string="Until")
    repeat_until = fields.Date(string="End Date")
    repeat_number = fields.Integer(string="Repetitions")

    repeat_on_month = fields.Selection([
        ('date', 'Date of the Month'),
        ('day', 'Day of the Month'),
    ])

    repeat_on_year = fields.Selection([
        ('date', 'Date of the Year'),
        ('day', 'Day of the Year'),
    ])

    mon = fields.Boolean(string="Mon")
    tue = fields.Boolean(string="Tue")
    wed = fields.Boolean(string="Wed")
    thu = fields.Boolean(string="Thu")
    fri = fields.Boolean(string="Fri")
    sat = fields.Boolean(string="Sat")
    sun = fields.Boolean(string="Sun")

    repeat_day = fields.Selection([
        (str(i), str(i)) for i in range(1, 32)
    ])
    repeat_week = fields.Selection([
        ('first', 'First'),
        ('second', 'Second'),
        ('third', 'Third'),
        ('last', 'Last'),
    ])
    repeat_weekday = fields.Selection([
        ('mon', 'Monday'),
        ('tue', 'Tuesday'),
        ('wed', 'Wednesday'),
        ('thu', 'Thursday'),
        ('fri', 'Friday'),
        ('sat', 'Saturday'),
        ('sun', 'Sunday'),
    ], string='Day Of The Week', readonly=False)
    repeat_month = fields.Selection([
        ('january', 'January'),
        ('february', 'February'),
        ('march', 'March'),
        ('april', 'April'),
        ('may', 'May'),
        ('june', 'June'),
        ('july', 'July'),
        ('august', 'August'),
        ('september', 'September'),
        ('october', 'October'),
        ('november', 'November'),
        ('december', 'December'),
    ])

    @api.constrains('repeat_unit', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun')
    def _check_recurrence_days(self):
        for project in self.filtered(lambda p: p.repeat_unit == 'week'):
            if not any([project.mon, project.tue, project.wed, project.thu, project.fri, project.sat, project.sun]):
                raise ValidationError('You should select a least one day')

    @api.constrains('repeat_interval')
    def _check_repeat_interval(self):
        if self.filtered(lambda t: t.repeat_interval <= 0):
            raise ValidationError('The interval should be greater than 0')

    @api.constrains('repeat_number', 'repeat_type')
    def _check_repeat_number(self):
        if self.filtered(lambda t: t.repeat_type == 'after' and t.repeat_number <= 0):
            raise ValidationError('Should repeat at least once')

    @api.constrains('repeat_type', 'repeat_until')
    def _check_repeat_until_date(self):
        today = fields.Date.today()
        if self.filtered(lambda t: t.repeat_type == 'until' and t.repeat_until < today):
            raise ValidationError('The end date should be in the future')

    @api.constrains('repeat_unit', 'repeat_on_month', 'repeat_day', 'repeat_type', 'repeat_until')
    def _check_repeat_until_month(self):
        if self.filtered(lambda r: r.repeat_type == 'until' and r.repeat_unit == 'month' and r.repeat_until and r.repeat_on_month == 'date'
           and int(r.repeat_day) > r.repeat_until.day and monthrange(r.repeat_until.year, r.repeat_until.month)[1] != r.repeat_until.day):
            raise ValidationError('The end date should be after the day of the month or the last day of the month')

    @api.model
    def _get_recurring_fields(self):
        return ['message_partner_ids', 'company_id', 'description', 'displayed_image_id', 'email_cc',
                'parent_id', 'partner_email', 'partner_id', 'partner_phone', 'planned_hours',
                'project_id', 'display_project_id', 'project_privacy_visibility', 'sequence', 'tag_ids', 'recurrence_id',
                'name', 'recurring_task', 'analytic_account_id']

    def _get_weekdays(self, n=1):
        self.ensure_one()
        if self.repeat_unit == 'week':
            return [fn(n) for day, fn in DAYS.items() if self[day]]
        return [DAYS.get(self.repeat_weekday)(n)]

    @api.model
    def _get_next_recurring_dates(self, date_start, repeat_interval, repeat_unit, repeat_type, repeat_until, repeat_on_month, repeat_on_year, weekdays, repeat_day, repeat_week, repeat_month, **kwargs):
        count = kwargs.get('count', 1)
        rrule_kwargs = {'interval': repeat_interval or 1, 'dtstart': date_start}
        repeat_day = int(repeat_day)
        start = False
        dates = []
        if repeat_type == 'until':
            rrule_kwargs['until'] = repeat_until if repeat_until else fields.Date.today()
        else:
            rrule_kwargs['count'] = count

        if repeat_unit == 'week'\
            or (repeat_unit == 'month' and repeat_on_month == 'day')\
            or (repeat_unit == 'year' and repeat_on_year == 'day'):
            rrule_kwargs['byweekday'] = weekdays

        if repeat_unit == 'day':
            rrule_kwargs['freq'] = DAILY
        elif repeat_unit == 'month':
            rrule_kwargs['freq'] = MONTHLY
            if repeat_on_month == 'date':
                start = date_start - relativedelta(days=1)
                start = start.replace(day=min(repeat_day, monthrange(start.year, start.month)[1]))
                if start < date_start:
                    # Ensure the next recurrence is in the future
                    start += relativedelta(months=repeat_interval)
                    start = start.replace(day=min(repeat_day, monthrange(start.year, start.month)[1]))
                can_generate_date = (lambda: start <= repeat_until) if repeat_type == 'until' else (lambda: len(dates) < count)
                while can_generate_date():
                    dates.append(start)
                    start += relativedelta(months=repeat_interval)
                    start = start.replace(day=min(repeat_day, monthrange(start.year, start.month)[1]))
                return dates
        elif repeat_unit == 'year':
            rrule_kwargs['freq'] = YEARLY
            month = list(MONTHS.keys()).index(repeat_month) + 1
            rrule_kwargs['bymonth'] = month
            if repeat_on_year == 'date':
                rrule_kwargs['bymonthday'] = min(repeat_day, MONTHS.get(repeat_month))
                rrule_kwargs['bymonth'] = month
        else:
            rrule_kwargs['freq'] = WEEKLY

        rules = rrule(**rrule_kwargs)
        return list(rules) if rules else []

    def _new_task_values(self, task):
        self.ensure_one()
        fields_to_copy = self._get_recurring_fields()
        task_values = task.read(fields_to_copy).pop()
        create_values = {
            field: value[0] if isinstance(value, tuple) else value for field, value in task_values.items()
        }
        create_values['stage_id'] = task.project_id.type_ids[0].id if task.project_id.type_ids else task.stage_id.id
        create_values['user_ids'] = False
        return create_values

    def _create_subtasks(self, task, new_task, depth=3):
        if depth == 0 or not task.child_ids:
            return
        children = []
        child_recurrence = []
        # copy the subtasks of the original task
        for child in task.child_ids:
            if child.recurrence_id and child.recurrence_id.id in child_recurrence:
                # The subtask has been generated by another subtask in the childs
                # This subtasks is skipped as it will be meant to be a copy of the first
                # task of the recurrence we just created.
                continue
            child_values = self._new_task_values(child)
            child_values['parent_id'] = new_task.id
            if child.recurrence_id:
                # The subtask has a recurrence, the recurrence is thus copied rather than used
                # with raw reference in order to decouple the recurrence of the initial subtask
                # from the recurrence of the copied subtask which will live its own life and generate
                # subsequent tasks.
                child_recurrence += [child.recurrence_id.id]
                child_values['recurrence_id'] = child.recurrence_id.copy().id
            if child.child_ids and depth > 1:
                # If child has childs in the following layer and we will have to copy layer, we have to
                # first create the new_child record in order to have a new parent_id reference for the
                # "grandchildren" tasks
                new_child = self.env['project.task'].sudo().create(child_values)
                self._create_subtasks(child, new_child, depth=depth - 1)
            else:
                children.append(child_values)
        children_tasks = self.env['project.task'].sudo().create(children)

    def _create_next_task(self):
        for recurrence in self:
            task = recurrence.sudo().task_ids[-1]
            create_values = recurrence._new_task_values(task)
            new_task = self.env['project.task'].sudo().create(create_values)
            recurrence._create_subtasks(task, new_task, depth=3)

    def _set_next_recurrence_date(self):
        today = fields.Date.today()
        tomorrow = today + relativedelta(days=1)
        for recurrence in self.filtered(
            lambda r:
            r.repeat_type == 'after' and r.recurrence_left >= 0
            or r.repeat_type == 'until' and r.repeat_until >= today
            or r.repeat_type == 'forever'
        ):
            if recurrence.repeat_type == 'after' and recurrence.recurrence_left == 0:
                recurrence.next_recurrence_date = False
            else:
                next_date = self._get_next_recurring_dates(tomorrow, recurrence.repeat_interval, recurrence.repeat_unit, recurrence.repeat_type, recurrence.repeat_until, recurrence.repeat_on_month, recurrence.repeat_on_year, recurrence._get_weekdays(), recurrence.repeat_day, recurrence.repeat_week, recurrence.repeat_month, count=1)
                recurrence.next_recurrence_date = next_date[0] if next_date else False

    @api.model
    def _cron_create_recurring_tasks(self):
        if not self.env.user.has_group('project.group_project_recurring_tasks'):
            return
        today = fields.Date.today()
        recurring_today = self.search([('next_recurrence_date', '<=', today)])
        recurring_today._create_next_task()
        for recurrence in recurring_today.filtered(lambda r: r.repeat_type == 'after'):
            recurrence.recurrence_left -= 1
        recurring_today._set_next_recurrence_date()

    @api.model
    def create(self, vals):
        if vals.get('repeat_number'):
            vals['recurrence_left'] = vals.get('repeat_number')
        res = super(ProjectTaskRecurrence, self).create(vals)
        res._set_next_recurrence_date()
        return res

    def write(self, vals):
        if vals.get('repeat_number'):
            vals['recurrence_left'] = vals.get('repeat_number')

        res = super(ProjectTaskRecurrence, self).write(vals)

        if 'next_recurrence_date' not in vals:
            self._set_next_recurrence_date()
        return res
