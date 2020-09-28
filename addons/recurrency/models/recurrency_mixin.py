from datetime import timedelta, datetime

from odoo import api, fields, models, tools, SUPERUSER_ID, _
from odoo.tools import get_timedelta
from .recurrency import DAYS, WEEKS


class RecurrenceMixin(models.AbstractModel):
    _name = 'recurrency.mixin'
    _description = 'RecurrenceMixin'

    recurring_event = fields.Boolean(default=False)
    recurrence_id = fields.Many2one('recurrency.recurrency', string='Recurrence', store=True)
    repeat_interval = fields.Integer(related='recurrence_id.repeat_interval')

    recurrence_update = fields.Selection([
        ('this', 'This recurrence'),
        ('subsequent', 'This and following recuerrences'),
        ('all', 'All recurrences'),
    ], default='this', store=False)
    recurrence_message = fields.Char(string='Next Recurrencies', compute='_compute_recurrence_message')

    repeat_interval = fields.Integer(string='Repeat Every', default=1, compute='_compute_repeat', readonly=False)
    repeat_unit = fields.Selection([
        ('day', 'Days'),
        ('week', 'Weeks'),
        ('month', 'Months'),
        ('year', 'Years'),
    ], default='week', compute='_compute_repeat', readonly=False)
    repeat_type = fields.Selection([
        ('forever', 'Forever'),
        ('until', 'End Date'),
        ('after', 'Number of Repetitions'),
    ], default="forever", string="Until", compute='_compute_repeat', readonly=False)
    repeat_until = fields.Date(string="Until Date", compute='_compute_repeat', readonly=False)
    repeat_number = fields.Integer(string="Repetitions", default=1, compute='_compute_repeat', readonly=False)

    repeat_on_month = fields.Selection([
        ('date', 'Date of the Month'),
        ('day', 'Day of the Month'),
    ], default='date', compute='_compute_repeat', readonly=False)

    repeat_on_year = fields.Selection([
        ('date', 'Date of the Year'),
        ('day', 'Day of the Year'),
    ], default='date', compute='_compute_repeat', readonly=False)

    mon = fields.Boolean(string="Mon", compute='_compute_repeat', readonly=False)
    tue = fields.Boolean(string="Tue", compute='_compute_repeat', readonly=False)
    wed = fields.Boolean(string="Wed", compute='_compute_repeat', readonly=False)
    thu = fields.Boolean(string="Thu", compute='_compute_repeat', readonly=False)
    fri = fields.Boolean(string="Fri", compute='_compute_repeat', readonly=False)
    sat = fields.Boolean(string="Sat", compute='_compute_repeat', readonly=False)
    sun = fields.Boolean(string="Sun", compute='_compute_repeat', readonly=False)

    repeat_day = fields.Selection([
        (str(i), str(i)) for i in range(1, 32)
    ], compute='_compute_repeat', readonly=False)
    repeat_week = fields.Selection([
        ('first', 'First'),
        ('second', 'Second'),
        ('third', 'Third'),
        ('last', 'Last'),
    ], default='first', compute='_compute_repeat', readonly=False)
    repeat_weekday = fields.Selection([
        ('mon', 'Monday'),
        ('tue', 'Tuesday'),
        ('wed', 'Wednesday'),
        ('thu', 'Thursday'),
        ('fri', 'Friday'),
        ('sat', 'Saturday'),
        ('sun', 'Sunday'),
    ], string='Day Of The Week', compute='_compute_repeat', readonly=False)
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
    ], compute='_compute_repeat', readonly=False)

    repeat_show_dow = fields.Boolean(compute='_compute_repeat_visibility')
    repeat_show_day = fields.Boolean(compute='_compute_repeat_visibility')
    repeat_show_week = fields.Boolean(compute='_compute_repeat_visibility')
    repeat_show_month = fields.Boolean(compute='_compute_repeat_visibility')


    @api.model
    def _get_recurrence_fields(self):
        return ['repeat_interval', 'repeat_unit', 'repeat_type', 'repeat_until', 'repeat_number',
                'repeat_on_month', 'repeat_on_year', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat',
                'sun', 'repeat_day', 'repeat_week', 'repeat_month', 'repeat_weekday']

    @api.model
    def _get_recurring_fields(self):
        return ['recurring_event', 'recurrence_id']

    @api.depends('recurring_event', 'repeat_unit', 'repeat_on_month', 'repeat_on_year')
    def _compute_repeat_visibility(self):
        for recurrence in self:
            recurrence.repeat_show_day = recurrence.recurring_event and (recurrence.repeat_unit == 'month' and recurrence.repeat_on_month == 'date') or (recurrence.repeat_unit == 'year' and recurrence.repeat_on_year == 'date')
            recurrence.repeat_show_week = recurrence.recurring_event and (recurrence.repeat_unit == 'month' and recurrence.repeat_on_month == 'day') or (recurrence.repeat_unit == 'year' and recurrence.repeat_on_year == 'day')
            recurrence.repeat_show_dow = recurrence.recurring_event and recurrence.repeat_unit == 'week'
            recurrence.repeat_show_month = recurrence.recurring_event and recurrence.repeat_unit == 'year'

    @api.depends('recurring_event', 'repeat_unit')
    def _compute_repeat(self):
        rec_fields = self._get_recurrence_fields()
        defaults = self.recurrence_id.default_get(rec_fields)
        for recurrence in self:
            for f in rec_fields:
                if recurrence.recurrence_id:
                    recurrence[f] = recurrence.recurrence_id[f]
                else:
                    if recurrence.recurring_event:
                        recurrence[f] = defaults.get(f)
                    else:
                        recurrence[f] = False

    def _get_weekdays(self, n=1):
        self.ensure_one()
        if self.repeat_unit == 'week':
            return [fn(n) for day, fn in DAYS.items() if self[day]]
        return [DAYS.get(self.repeat_weekday)(n)]

    @api.depends('recurring_event', 'repeat_interval', 'repeat_unit', 'repeat_type', 'repeat_until',
        'repeat_number', 'repeat_on_month', 'repeat_on_year', 'mon', 'tue', 'wed', 'thu', 'fri',
        'sat', 'sun', 'repeat_day', 'repeat_week', 'repeat_month', 'repeat_weekday')
    def _compute_recurrence_message(self):
        self.recurrence_message = False
        for recurrence in self.filtered(lambda t: t.recurring_event and t._is_recurrence_valid()):
            date = fields.Date.today()
            number_occurrences = min(5, recurrence.repeat_number if recurrence.repeat_type == 'after' else 5)
            delta = recurrence.repeat_interval if recurrence.repeat_unit == 'day' else 1
            recurring_dates = self.env['recurrency.recurrency']._get_next_recurring_dates(
                date + timedelta(days=delta),
                recurrence.repeat_interval,
                recurrence.repeat_unit,
                recurrence.repeat_type,
                recurrence.repeat_until,
                recurrence.repeat_on_month,
                recurrence.repeat_on_year,
                recurrence._get_weekdays(WEEKS.get(recurrence.repeat_week)),
                recurrence.repeat_day,
                recurrence.repeat_week,
                recurrence.repeat_month,
                count=number_occurrences)
            date_format = self.env['res.lang']._lang_get(self.env.user.lang).date_format
            recurrence.recurrence_message = '<ul>'
            for date in recurring_dates[:5]:
                recurrence.recurrence_message += '<li>%s</li>' % date.strftime(date_format)
            if recurrence.repeat_type == 'after' and recurrence.repeat_number > 5 or recurrence.repeat_type == 'forever' or len(recurring_dates) > 5:
                recurrence.recurrence_message += '<li>...</li>'
            recurrence.recurrence_message += '</ul>'
            if recurrence.repeat_type == 'until':
                recurrence.recurrence_message += _('<p><em>Number of recurrences: %(recurrences_count)s</em></p>') % {'recurrences_count': len(recurring_dates)}

    def _get_next_recurring_datetimes(self, start_datetime, stop_datetime=False):
        for recurrency in self:
            recurrence_end_dt = False
            if recurrency.repeat_type == "until":
                recurrence_end_dt = recurrency.recurrence_id.repeat_until
            elif recurrency.repeat_type == "after":
                recurrence_end_dt = (start_datetime + recurrency.repeat_number * get_timedelta(recurrency.repeat_interval, "week"))
            if not stop_datetime:
                stop_datetime = fields.Datetime.now() + get_timedelta(self.company_id.planning_generation_interval, "month")
            range_limit = min([dt for dt in [recurrence_end_dt, stop_datetime] if dt])
            recurrency_delta = get_timedelta(recurrency.repeat_interval, recurrency.repeat_unit)
            next_start = start_datetime + recurrency_delta
            next_datetimes = []
            while next_start < range_limit:
                next_datetimes.append(next_start)
                next_start = next_start + recurrency_delta
            return next_datetimes

    @api.model
    def _get_days_from_datetime(self, vals) :
        days = list(DAYS.keys())
        start_datetime = vals.get('start_rec_datetime')
        end_datetime = vals.get('end_rec_datetime')
        vals.update({str(days[fields.Datetime.today().weekday()]):False})
        delta = end_datetime - start_datetime
        for i in range(delta.days + 1):
            day = start_datetime + timedelta(days=i)
            weekday = day.weekday()
            vals.update({str(days[weekday]): True})
        return vals

    def _set_next_recurrence_date(self, date_start):
        for recurrence in self:
            recurrence.recurrence_id._set_next_recurrence_date(date_start)


    def _get_next_recurring_dates(self, date_start, repeat_interval, repeat_unit, repeat_type, repeat_until,
                                  repeat_on_month, repeat_on_year, weekdays, repeat_day, repeat_week, repeat_month,
                                  **kwargs):
        return self.recurrence_id._get_next_recurring_dates(self, date_start, repeat_interval, repeat_unit, repeat_type, repeat_until,
                                  repeat_on_month, repeat_on_year, weekdays, repeat_day, repeat_week, repeat_month,
                                  **kwargs)

    def _is_recurrence_valid(self):
        self.ensure_one()
        return self.repeat_interval > 0 and\
                (not self.repeat_show_dow or self._get_weekdays()) and\
                (self.repeat_type != 'after' or self.repeat_number) and\
                (self.repeat_type != 'until' or self.repeat_until and self.repeat_until > fields.Date.today())

    def _new_recurrence_values(self, recurrence):
        recurrence.ensure_one()
        fields_to_copy = self._get_recurring_fields()
        recurrence_values = self.read(fields_to_copy).pop()
        create_values = {
            field: value[0] if isinstance(value, tuple) else value for field, value in recurrence_values.items()
        }
        return create_values

    def repeat_recurrent_event(self, recurring_today, stop_datetime=False):
        for recurrence in recurring_today:
            create_values = self._new_recurrence_values(recurrence)
            new_task = self.sudo().create(create_values)
            return new_task

    def _cron_create_recurring_events(self):
        return '#'