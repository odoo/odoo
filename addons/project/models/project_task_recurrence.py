# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
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

    task_template_id = fields.Many2one('project.task')
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
                raise ValidationError(_('You should select a least one day'))

    @api.constrains('repeat_interval')
    def _check_repeat_interval(self):
        if self.filtered(lambda t: t.repeat_interval <= 0):
            raise ValidationError(_('The interval should be greater than 0'))

    @api.constrains('repeat_number', 'repeat_type')
    def _check_repeat_number(self):
        if self.filtered(lambda t: t.repeat_type == 'after' and t.repeat_number <= 0):
            raise ValidationError(_('Should repeat at least once'))

    @api.constrains('repeat_type', 'repeat_until')
    def _check_repeat_until_date(self):
        today = fields.Date.today()
        if self.filtered(lambda t: t.repeat_type == 'until' and t.repeat_until < today):
            raise ValidationError(_('The end date should be in the future'))

    @api.constrains('repeat_unit', 'repeat_on_month', 'repeat_day', 'repeat_type', 'repeat_until')
    def _check_repeat_until_month(self):
        if self.filtered(lambda r: r.repeat_type == 'until' and r.repeat_unit == 'month' and r.repeat_until and r.repeat_on_month == 'date'
           and int(r.repeat_day) > r.repeat_until.day and monthrange(r.repeat_until.year, r.repeat_until.month)[1] != r.repeat_until.day):
            raise ValidationError(_('The end date should be after the day of the month or the last day of the month'))

    @api.model
    def _get_recurring_fields(self):
        return ['message_partner_ids', 'company_id', 'description', 'displayed_image_id', 'email_cc',
                'parent_id', 'partner_email', 'partner_id', 'partner_phone', 'planned_hours',
                'project_id', 'display_project_id', 'project_privacy_visibility', 'sequence', 'tag_ids', 'recurrence_id',
                'name', 'recurring_task', 'analytic_account_id', 'user_ids']

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
            month = list(MONTHS.keys()).index(repeat_month) + 1 if repeat_month else date_start.month
            repeat_month = repeat_month or list(MONTHS.keys())[month - 1]
            rrule_kwargs['bymonth'] = month
            if repeat_on_year == 'date':
                rrule_kwargs['bymonthday'] = min(repeat_day, MONTHS.get(repeat_month))
                rrule_kwargs['bymonth'] = month
        else:
            rrule_kwargs['freq'] = WEEKLY

        rules = rrule(**rrule_kwargs)
        return list(rules) if rules else []

    def _new_task_values(self, task_from, to_template=False):
        self.ensure_one()
        fields_to_copy = self._get_recurring_fields()
        task_values = task_from.read(fields_to_copy).pop()
        create_values = {
            field: value[0] if isinstance(value, tuple) else value for field, value in task_values.items()
        }
        create_values['stage_id'] = task_from.project_id.type_ids[0].id if task_from.project_id.type_ids\
                               else task_from.stage_id.id
        create_values['date_deadline'] = self._get_postponed_date(task_from, 'date_deadline', to_template=to_template)
        create_values['active'] = not to_template
        create_values['recurrence_template_id'] = not to_template and task_from.id
        return create_values

    def _create_subtasks(self, task_from, task_to, to_template=False):
        self.ensure_one()
        childs_from = task_from.with_context(active_test=False).child_ids
        if to_template:
            childs_to = task_from.recurrence_template_id.with_context(active_test=False).child_ids
            childs_from_to_create = childs_from.filtered(lambda t: not t.recurrence_template_id)
            childs_to_to_delete = childs_to.filtered(lambda t: t not in childs_from.recurrence_template_id)
            childs_to_to_delete.unlink_task_and_subtasks_recursively()
            (childs_to - childs_to_to_delete).parent_id = task_to
        else:
            childs_from_to_create = childs_from
        # copy the subtasks of the original task
        for child_from in childs_from_to_create:
            child_values = self._new_task_values(child_from, to_template=to_template)
            child_values['parent_id'] = task_to.id
            child_to = self.env['project.task'].sudo().create(child_values)
            if to_template:
                child_from.recurrence_template_id = child_to
            if child_from.with_context(active_test=False).child_ids:
                self._create_subtasks(child_from, child_to, to_template=to_template)

    def _create_task(self, task_from=False):
        self.ensure_one()
        to_template = bool(task_from)
        task_from = task_from or self.task_template_id
        create_values = self._new_task_values(task_from, to_template=to_template)
        task_to = self.env['project.task'].sudo().create(create_values)
        self._create_subtasks(task_from, task_to, to_template=to_template)
        if to_template:
            task_from.recurrence_template_id.unlink()
            task_from.recurrence_template_id = task_to
            if task_from.parent_id:
                task_to.parent_id = task_from.parent_id.recurrence_template_id
            else:
                self.task_template_id.unlink_task_and_subtasks_recursively()
                self.task_template_id = task_to

    def _set_next_recurrence_date(self, date_start=None):
        today = fields.Date.today()
        if not date_start:
            date_start = today + relativedelta(days=1)
        for recurrence in self.filtered(
            lambda r:
            r.repeat_type == 'after' and r.recurrence_left >= 0
            or r.repeat_type == 'until' and r.repeat_until >= today
            or r.repeat_type == 'forever'
        ):
            if recurrence.repeat_type == 'after' and recurrence.recurrence_left == 0:
                recurrence.next_recurrence_date = False
            else:
                next_date = self._get_next_recurring_dates(date_start, recurrence.repeat_interval, recurrence.repeat_unit, recurrence.repeat_type, recurrence.repeat_until, recurrence.repeat_on_month, recurrence.repeat_on_year, recurrence._get_weekdays(), recurrence.repeat_day, recurrence.repeat_week, recurrence.repeat_month, count=1)
                recurrence.next_recurrence_date = next_date[0] if next_date else False

    @api.model
    def _cron_create_recurring_tasks(self):
        if not self.env.user.has_group('project.group_project_recurring_tasks'):
            return
        today = fields.Date.today()
        recurring_today = self.search([('next_recurrence_date', '<=', today)])
        recurrence_ids = []  # to set the next recurrence date
        for recurrence in recurring_today:
            if not recurrence.task_template_id.project_id.allow_recurring_tasks:
                continue
            recurrence_ids.append(recurrence.id)
            recurrence._create_task()
            if recurrence.repeat_type == 'after':
                recurrence.recurrence_left -= 1
        self.browse(recurrence_ids)._set_next_recurrence_date()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('repeat_number'):
                vals['recurrence_left'] = vals.get('repeat_number')
        recurrences = super().create(vals_list)
        recurrences._set_next_recurrence_date()
        return recurrences

    def write(self, vals):
        if vals.get('repeat_number'):
            vals['recurrence_left'] = vals.get('repeat_number')

        res = super(ProjectTaskRecurrence, self).write(vals)

        if 'next_recurrence_date' not in vals:
            self._set_next_recurrence_date()
        return res

    def unlink(self):
        self.task_template_id.unlink_task_and_subtasks_recursively()
        return super().unlink()

    def _get_postponed_date(self, task_from, field, to_template=False):
        # We cannot just apply the recurrence's repeat interval to the task's deadline because,
        # if the recurrence is created later than the task, the planned date won't be set as expected.
        # Instead, we'll apply the delta create-deadline of the previous task to the new one's create date.

        # Apply the repeat interval to the create date :                # ~ the repeat interval
        #   p1~p2~p3   ?  ?                                             # / the expected delta create-deadline
        #  /          /  /     => p2 should be set at ?                 # c the create dates
        # c1---------c2~c3                                              # p the deadline
        #            ^ Recurrence initiation

        # Apply the previous delta create-deadline to the create date :
        #   p1         p2 p3
        #  /          /  /     => p2 is set as expected
        # c1---------c2~c3
        #            ^ Recurrence initiation
        self.ensure_one()
        if not task_from[field]:
            return False
        field_is_datetime = task_from._fields[field].type == 'datetime'
        datetime = task_from[field]
        date = datetime.date() if field_is_datetime else datetime
        delta = date - task_from.create_date.date()
        if to_template:
            next_recurrence_date = (self.task_template_id.create_date or self.create_date).date()
        else:
            next_recurrence_date = self.next_recurrence_date or fields.Date.today()
        postponed_date = next_recurrence_date + relativedelta(days=delta.days)
        if field_is_datetime:
            postponed_date += relativedelta(hour=datetime.hour, minute=datetime.minute, second=datetime.second)
        return postponed_date
