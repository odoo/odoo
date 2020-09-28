# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.exceptions import UserError
from calendar import monthrange
from dateutil.relativedelta import relativedelta
from dateutil.rrule import rrule, rruleset, DAILY, WEEKLY, MONTHLY, YEARLY, MO, TU, WE, TH, FR, SA, SU
from datetime import date, datetime
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


class Recurrence(models.Model):
    _name = 'recurrency.recurrency'
    _description = 'Recurrence'

    last_generated_end_datetime = fields.Datetime("Last Generated End Date", readonly=True)
    next_recurrence_date = fields.Date()
    recurrence_left = fields.Integer(string="Number of events left to create")
    repeat_interval = fields.Integer(string='Repeat Every', default=1)
    company_id = fields.Many2one('res.company', string="Company", readonly=True, required=True,
                                 default=lambda self: self.env.company)

    start_rec_datetime = fields.Datetime("Start Datetime", store=True, readonly=False)
    end_rec_datetime = fields.Datetime("End Datetime", store=True, readonly=False)
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
    repeat_until = fields.Datetime(string="End Date")
    repeat_number = fields.Integer(string="Repetitions", default=1)

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
        for recurrence in self.filtered(lambda p: p.repeat_unit == 'week'):
            if not any([recurrence.mon, recurrence.tue, recurrence.wed, recurrence.thu, recurrence.fri, recurrence.sat, recurrence.sun]):
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
        if self.filtered(lambda t: t.repeat_type == 'until' and t.repeat_until.date() < today):
            raise ValidationError('The end date should be in the future')

    @api.constrains('repeat_unit', 'repeat_on_month', 'repeat_day', 'repeat_type', 'repeat_until')
    def _check_repeat_until_month(self):
        if self.filtered(lambda r: r.repeat_type == 'until' and r.repeat_unit == 'month' and
                                   r.repeat_until and r.repeat_on_month == 'date' and int(r.repeat_day) > r.repeat_until.day):
            raise ValidationError('The end date should be after the day of the month')

    def _get_weekdays(self, n=1):
        self.ensure_one()
        if self.repeat_unit == 'week':
            return [fn(n) for day, fn in DAYS.items() if self[day]]
        return [DAYS.get(self.repeat_weekday)(n)]




    @api.model
    def _get_next_recurring_dates(self, date_start, repeat_interval, repeat_unit, repeat_type, repeat_until,
                                  repeat_on_month, repeat_on_year, weekdays, repeat_day, repeat_week, repeat_month,
                                  **kwargs):
        count = kwargs.get('count', 1)
        rrule_kwargs = {'interval': repeat_interval or 1, 'dtstart': date_start}
        repeat_day = int(repeat_day)
        start = False
        dates = []
        if repeat_type == 'until':
            rrule_kwargs['until'] = repeat_until if repeat_until else fields.Date.today()
        else:
            rrule_kwargs['count'] = count

        if repeat_unit == 'week' \
                or (repeat_unit == 'month' and repeat_on_month == 'day') \
                or (repeat_unit == 'year' and repeat_on_year == 'day'):
            rrule_kwargs['byweekday'] = weekdays

        if repeat_unit == 'day':
            rrule_kwargs['freq'] = DAILY
        elif repeat_unit == 'month':
            rrule_kwargs['freq'] = MONTHLY
            if repeat_on_month == 'date':
                start = date_start - relativedelta(days=1)
                if repeat_type == 'until' and repeat_until > date_start:
                    delta = relativedelta(repeat_until, date_start)
                    count = delta.years * 12 + delta.months
                for i in range(count):
                    start = start.replace(day=min(repeat_day, monthrange(start.year, start.month)[1]))
                    dates.append(start)
                    start += relativedelta(months=repeat_interval)
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

    def _set_next_recurrence_date(self, date_start):
        today = fields.Date.today()
        tomorrow = today + relativedelta(days=1)
        for recurrence in self.filtered(lambda r: r.repeat_type == 'after' and r.recurrence_left >= 0 or r.repeat_type == 'until' and r.repeat_until.date() >= today or r.repeat_type == 'forever'):
            if (recurrence.repeat_type == 'after' and recurrence.recurrence_left == 0):
                recurrence.next_recurrence_date = False
            else:
                next_date = self._get_next_recurring_dates(date_start, recurrence.repeat_interval, recurrence.repeat_unit, recurrence.repeat_type, recurrence.repeat_until, recurrence.repeat_on_month, recurrence.repeat_on_year, recurrence._get_weekdays(), recurrence.repeat_day, recurrence.repeat_week, recurrence.repeat_month, count=1)
                recurrence.next_recurrence_date = next_date[0] if next_date else False

    @api.model
    def default_get(self, default_fields):
        vals = super(Recurrence, self).default_get(default_fields)

        days = list(DAYS.keys())
        week_start = fields.Datetime.today().weekday()

        if all([d in default_fields for d in days]):

            vals[days[week_start]] = True
        if 'repeat_day' in default_fields:
            vals['repeat_day'] = str(fields.Datetime.today().day)
        if 'repeat_month' in default_fields:
            vals['repeat_month'] = self._fields.get('repeat_month').selection[fields.Datetime.today().month - 1][0]
        if 'repeat_weekday' in default_fields:
            vals['repeat_weekday'] = self._fields.get('repeat_weekday').selection[week_start][0]
        return vals

    def create(self, vals):
        start_date = fields.Date.today() + relativedelta(days=1)
        if vals.get('repeat_number'):
            vals['recurrence_left'] = vals.get('repeat_number')
        res = super(Recurrence, self).create(vals)
        res._set_next_recurrence_date(start_date)
        return res

    def write(self, vals):
        if vals.get('repeat_number'):
            vals['recurrence_left'] = vals.get('repeat_number')
        res = super(Recurrence, self).write(vals)
        if 'next_recurrence_date' not in vals:
            self._set_next_recurrence_date(fields.Date.today() + relativedelta(days=1))
        return res
