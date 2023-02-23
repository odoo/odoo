# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, time
import pytz

from dateutil import rrule
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError

from odoo.addons.base.models.res_partner import _tz_get


MAX_RECURRENT_EVENT = 720

SELECT_FREQ_TO_RRULE = {
    'daily': rrule.DAILY,
    'weekly': rrule.WEEKLY,
    'monthly': rrule.MONTHLY,
    'yearly': rrule.YEARLY,
}

RRULE_FREQ_TO_SELECT = {
    rrule.DAILY: 'daily',
    rrule.WEEKLY: 'weekly',
    rrule.MONTHLY: 'monthly',
    rrule.YEARLY: 'yearly',
}

RRULE_WEEKDAY_TO_FIELD = {
    rrule.MO.weekday: 'mon',
    rrule.TU.weekday: 'tue',
    rrule.WE.weekday: 'wed',
    rrule.TH.weekday: 'thu',
    rrule.FR.weekday: 'fri',
    rrule.SA.weekday: 'sat',
    rrule.SU.weekday: 'sun',
}

RRULE_WEEKDAYS = {'SUN': 'SU', 'MON': 'MO', 'TUE': 'TU', 'WED': 'WE', 'THU': 'TH', 'FRI': 'FR', 'SAT': 'SA'}

RRULE_TYPE_SELECTION = [
    ('daily', 'Days'),
    ('weekly', 'Weeks'),
    ('monthly', 'Months'),
    ('yearly', 'Years'),
]

END_TYPE_SELECTION = [
    ('count', 'Number of repetitions'),
    ('end_date', 'End date'),
    ('forever', 'Forever'),
]

MONTH_BY_SELECTION = [
    ('date', 'Date of month'),
    ('day', 'Day of month'),
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

BYDAY_SELECTION = [
    ('1', 'First'),
    ('2', 'Second'),
    ('3', 'Third'),
    ('4', 'Fourth'),
    ('-1', 'Last'),
]

def freq_to_select(rrule_freq):
    return RRULE_FREQ_TO_SELECT[rrule_freq]


def freq_to_rrule(freq):
    return SELECT_FREQ_TO_RRULE[freq]


def weekday_to_field(weekday_index):
    return RRULE_WEEKDAY_TO_FIELD.get(weekday_index)


class RecurrenceRule(models.Model):
    _name = 'calendar.recurrence'
    _description = 'Event Recurrence Rule'

    name = fields.Char(compute='_compute_name', store=True)
    base_event_id = fields.Many2one(
        'calendar.event', ondelete='set null', copy=False)  # store=False ?
    calendar_event_ids = fields.One2many('calendar.event', 'recurrence_id')
    event_tz = fields.Selection(
        _tz_get, string='Timezone',
        default=lambda self: self.env.context.get('tz') or self.env.user.tz)
    rrule = fields.Char(compute='_compute_rrule', inverse='_inverse_rrule', store=True)
    dtstart = fields.Datetime(compute='_compute_dtstart')
    rrule_type = fields.Selection(RRULE_TYPE_SELECTION, default='weekly')
    end_type = fields.Selection(END_TYPE_SELECTION, default='count')
    interval = fields.Integer(default=1)
    count = fields.Integer(default=1)
    mon = fields.Boolean()
    tue = fields.Boolean()
    wed = fields.Boolean()
    thu = fields.Boolean()
    fri = fields.Boolean()
    sat = fields.Boolean()
    sun = fields.Boolean()
    month_by = fields.Selection(MONTH_BY_SELECTION, default='date')
    day = fields.Integer(default=1)
    weekday = fields.Selection(WEEKDAY_SELECTION, string='Weekday')
    byday = fields.Selection(BYDAY_SELECTION, string='By day')
    until = fields.Date('Repeat Until')

    _sql_constraints = [
        ('month_day',
         "CHECK (rrule_type != 'monthly' "
                "OR month_by != 'day' "
                "OR day >= 1 AND day <= 31 "
                "OR weekday in %s AND byday in %s)"
                % (tuple(wd[0] for wd in WEEKDAY_SELECTION), tuple(bd[0] for bd in BYDAY_SELECTION)),
         "The day must be between 1 and 31"),
    ]

    @api.depends('rrule')
    def _compute_name(self):
        for recurrence in self:
            period = dict(RRULE_TYPE_SELECTION)[recurrence.rrule_type]
            every = _("Every %(count)s %(period)s", count=recurrence.interval, period=period)

            if recurrence.end_type == 'count':
                end = _("for %s events", recurrence.count)
            elif recurrence.end_type == 'end_date':
                end = _("until %s", recurrence.until)
            else:
                end = ''

            if recurrence.rrule_type == 'weekly':
                weekdays = recurrence._get_week_days()
                # Convert Weekday object
                weekdays = [str(w) for w in weekdays]
                # We need to get the day full name from its three first letters.
                week_map = {v: k for k, v in RRULE_WEEKDAYS.items()}
                weekday_short = [week_map[w] for w in weekdays]
                day_strings = [d[1] for d in WEEKDAY_SELECTION if d[0] in weekday_short]
                on = _("on %s") % ", ".join([day_name for day_name in day_strings])
            elif recurrence.rrule_type == 'monthly':
                if recurrence.month_by == 'day':
                    position_label = dict(BYDAY_SELECTION)[recurrence.byday]
                    weekday_label = dict(WEEKDAY_SELECTION)[recurrence.weekday]
                    on = _("on the %(position)s %(weekday)s", position=position_label, weekday=weekday_label)
                else:
                    on = _("day %s", recurrence.day)
            else:
                on = ''
            recurrence.name = ' '.join(filter(lambda s: s, [every, on, end]))

    @api.depends('calendar_event_ids.start')
    def _compute_dtstart(self):
        groups = self.env['calendar.event'].read_group([('recurrence_id', 'in', self.ids)], ['start:min'], ['recurrence_id'])
        start_mapping = {
            group['recurrence_id'][0]: group['start']
            for group in groups
        }
        for recurrence in self:
            recurrence.dtstart = start_mapping.get(recurrence.id)

    @api.depends(
        'byday', 'until', 'rrule_type', 'month_by', 'interval', 'count', 'end_type',
        'mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun', 'day', 'weekday')
    def _compute_rrule(self):
        for recurrence in self:
            recurrence.rrule = recurrence._rrule_serialize()

    def _inverse_rrule(self):
        for recurrence in self:
            if recurrence.rrule:
                values = self._rrule_parse(recurrence.rrule, recurrence.dtstart)
                recurrence.write(values)

    def _reconcile_events(self, ranges):
        """
        :param ranges: iterable of tuples (datetime_start, datetime_stop)
        :return: tuple (events of the recurrence already in sync with ranges,
                 and ranges not covered by any events)
        """
        ranges = set(ranges)

        synced_events = self.calendar_event_ids.filtered(lambda e: e._range() in ranges)

        existing_ranges = set(event._range() for event in synced_events)
        ranges_to_create = (event_range for event_range in ranges if event_range not in existing_ranges)
        return synced_events, ranges_to_create

    def _select_new_base_event(self):
        """
        when the base event is no more available (archived, deleted, etc.), a new one should be selected
        """
        for recurrence in self:
            recurrence.base_event_id = recurrence._get_first_event()

    def _apply_recurrence(self, specific_values_creation=None, no_send_edit=False, generic_values_creation=None):
        """Create missing events in the recurrence and detach events which no longer
        follow the recurrence rules.
        :return: detached events
        """
        event_vals = []
        keep = self.env['calendar.event']
        if specific_values_creation is None:
            specific_values_creation = {}

        for recurrence in self.filtered('base_event_id'):
            recurrence.calendar_event_ids |= recurrence.base_event_id
            event = recurrence.base_event_id or recurrence._get_first_event(include_outliers=False)
            duration = event.stop - event.start
            if specific_values_creation:
                ranges = set([(x[1], x[2]) for x in specific_values_creation if x[0] == recurrence.id])
            else:
                ranges = recurrence._range_calculation(event, duration)

            events_to_keep, ranges = recurrence._reconcile_events(ranges)
            keep |= events_to_keep
            [base_values] = event.copy_data()
            values = []
            for start, stop in ranges:
                value = dict(base_values, start=start, stop=stop, recurrence_id=recurrence.id, follow_recurrence=True)
                if (recurrence.id, start, stop) in specific_values_creation:
                    value.update(specific_values_creation[(recurrence.id, start, stop)])
                if generic_values_creation and recurrence.id in generic_values_creation:
                    value.update(generic_values_creation[recurrence.id])
                values += [value]
            event_vals += values

        events = self.calendar_event_ids - keep
        detached_events = self._detach_events(events)
        self.env['calendar.event'].with_context(no_mail_to_attendees=True, mail_create_nolog=True).create(event_vals)
        return detached_events

    def _split_from(self, event, recurrence_values=None):
        """Stops the current recurrence at the given event and creates a new one starting
        with the event.
        :param event: starting point of the new recurrence
        :param recurrence_values: values applied to the new recurrence
        :return: new recurrence
        """
        if recurrence_values is None:
            recurrence_values = {}
        event.ensure_one()
        if not self:
            return
        [values] = self.copy_data()
        detached_events = self._stop_at(event)

        count = recurrence_values.get('count', 0) or len(detached_events)
        return self.create({
            **values,
            **recurrence_values,
            'base_event_id': event.id,
            'calendar_event_ids': [(6, 0, detached_events.ids)],
            'count': max(count, 1),
        })

    def _stop_at(self, event):
        """Stops the recurrence at the given event. Detach the event and all following
        events from the recurrence.

        :return: detached events from the recurrence
        """
        self.ensure_one()
        events = self._get_events_from(event.start)
        detached_events = self._detach_events(events)
        if not self.calendar_event_ids:
            self.with_context(archive_on_error=True).unlink()
            return detached_events

        if event.allday:
            until = self._get_start_of_period(event.start_date)
        else:
            until_datetime = self._get_start_of_period(event.start)
            until_timezoned = pytz.utc.localize(until_datetime).astimezone(self._get_timezone())
            until = until_timezoned.date()
        self.write({
            'end_type': 'end_date',
            'until': until - relativedelta(days=1),
        })
        return detached_events

    @api.model
    def _detach_events(self, events):
        events.write({
            'recurrence_id': False,
            'recurrency': False,
        })
        return events

    def _write_events(self, values, dtstart=None):
        """
        Write values on events in the recurrence.
        :param values: event values
        :param dstart: if provided, only write events starting from this point in time
        """
        events = self._get_events_from(dtstart) if dtstart else self.calendar_event_ids
        return events.with_context(no_mail_to_attendees=True, dont_notify=True).write(dict(values, recurrence_update='self_only'))

    def _rrule_serialize(self):
        """
        Compute rule string according to value type RECUR of iCalendar
        :return: string containing recurring rule (empty if no rule)
        """
        if self.interval <= 0:
            raise UserError(_('The interval cannot be negative.'))
        if self.end_type == 'count' and self.count <= 0:
            raise UserError(_('The number of repetitions cannot be negative.'))

        return str(self._get_rrule()) if self.rrule_type else ''

    @api.model
    def _rrule_parse(self, rule_str, date_start):
        # LUL TODO clean this mess
        data = {}
        day_list = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']

        if 'Z' in rule_str and date_start and not date_start.tzinfo:
            date_start = pytz.utc.localize(date_start)
        rule = rrule.rrulestr(rule_str, dtstart=date_start)

        data['rrule_type'] = freq_to_select(rule._freq)
        data['count'] = rule._count
        data['interval'] = rule._interval
        data['until'] = rule._until
        # Repeat weekly
        if rule._byweekday:
            for weekday in day_list:
                data[weekday] = False  # reset
            for weekday_index in rule._byweekday:
                weekday = rrule.weekday(weekday_index)
                data[weekday_to_field(weekday.weekday)] = True
                data['rrule_type'] = 'weekly'

        # Repeat monthly by nweekday ((weekday, weeknumber), )
        if rule._bynweekday:
            data['weekday'] = day_list[list(rule._bynweekday)[0][0]].upper()
            data['byday'] = str(list(rule._bynweekday)[0][1])
            data['month_by'] = 'day'
            data['rrule_type'] = 'monthly'

        if rule._bymonthday:
            data['day'] = list(rule._bymonthday)[0]
            data['month_by'] = 'date'
            data['rrule_type'] = 'monthly'

        # Repeat yearly but for odoo it's monthly, take same information as monthly but interval is 12 times
        if rule._bymonth:
            data['interval'] *= 12

        if data.get('until'):
            data['end_type'] = 'end_date'
        elif data.get('count'):
            data['end_type'] = 'count'
        else:
            data['end_type'] = 'forever'
        return data

    def _get_lang_week_start(self):
        lang = self.env['res.lang']._lang_get(self.env.user.lang)
        week_start = int(lang.week_start)  # lang.week_start ranges from '1' to '7'
        return rrule.weekday(week_start - 1) # rrule expects an int from 0 to 6

    def _get_start_of_period(self, dt):
        if self.rrule_type == 'weekly':
            week_start = self._get_lang_week_start()
            start = dt + relativedelta(weekday=week_start(-1))
        elif self.rrule_type == 'monthly':
            start = dt + relativedelta(day=1)
        else:
            start = dt
        return start

    def _get_first_event(self, include_outliers=False):
        if not self.calendar_event_ids:
            return self.env['calendar.event']
        events = self.calendar_event_ids.sorted('start')
        if not include_outliers:
            events -= self._get_outliers()
        return events[:1]

    def _get_outliers(self):
        synced_events = self.env['calendar.event']
        for recurrence in self:
            if recurrence.calendar_event_ids:
                start = min(recurrence.calendar_event_ids.mapped('start'))
                starts = set(recurrence._get_occurrences(start))
                synced_events |= recurrence.calendar_event_ids.filtered(lambda e: e.start in starts)
        return self.calendar_event_ids - synced_events

    def _range_calculation(self, event, duration):
        """ Calculate the range of recurrence when applying the recurrence
        The following issues are taken into account:
            start of period is sometimes in the past (weekly or monthly rule).
            We can easily filter these range values but then the count value may be wrong...
            In that case, we just increase the count value, recompute the ranges and dismiss the useless values
        """
        self.ensure_one()
        original_count = self.end_type == 'count' and self.count
        ranges = set(self._get_ranges(event.start, duration))
        future_events = set((x, y) for x, y in ranges if x.date() >= event.start.date() and y.date() >= event.start.date())
        if original_count and len(future_events) < original_count:
            # Rise count number because some past values will be dismissed.
            self.count = (2*original_count) - len(future_events)
            ranges = set(self._get_ranges(event.start, duration))
            # We set back the occurrence number to its original value
            self.count = original_count
        # Remove ranges of events occurring in the past
        ranges = set((x, y) for x, y in ranges if x.date() >= event.start.date() and y.date() >= event.start.date())
        return ranges


    def _get_ranges(self, start, event_duration):
        starts = self._get_occurrences(start)
        return ((start, start + event_duration) for start in starts)

    def _get_timezone(self):
        return pytz.timezone(self.event_tz or self.env.context.get('tz') or 'UTC')

    def _get_occurrences(self, dtstart):
        """
        Get ocurrences of the rrule
        :param dtstart: start of the recurrence
        :return: iterable of datetimes
        """
        self.ensure_one()
        dtstart = self._get_start_of_period(dtstart)
        if self._is_allday():
            return self._get_rrule(dtstart=dtstart)

        timezone = self._get_timezone()
        # Localize the starting datetime to avoid missing the first occurrence
        dtstart = pytz.utc.localize(dtstart).astimezone(timezone)
        # dtstart is given as a naive datetime, but it actually represents a timezoned datetime
        # (rrule package expects a naive datetime)
        occurences = self._get_rrule(dtstart=dtstart.replace(tzinfo=None))

        # Special timezoning is needed to handle DST (Daylight Saving Time) changes.
        # Given the following recurrence:
        #   - monthly
        #   - 1st of each month
        #   - timezone US/Eastern (UTC−05:00)
        #   - at 6am US/Eastern = 11am UTC
        #   - from 2019/02/01 to 2019/05/01.
        # The naive way would be to store:
        # 2019/02/01 11:00 - 2019/03/01 11:00 - 2019/04/01 11:00 - 2019/05/01 11:00 (UTC)
        #
        # But a DST change occurs on 2019/03/10 in US/Eastern timezone. US/Eastern is now UTC−04:00.
        # From this point in time, 11am (UTC) is actually converted to 7am (US/Eastern) instead of the expected 6am!
        # What should be stored is:
        # 2019/02/01 11:00 - 2019/03/01 11:00 - 2019/04/01 10:00 - 2019/05/01 10:00 (UTC)
        #                                                  *****              *****
        return (timezone.localize(occurrence, is_dst=False).astimezone(pytz.utc).replace(tzinfo=None) for occurrence in occurences)

    def _get_events_from(self, dtstart):
        return self.env['calendar.event'].search([
            ('id', 'in', self.calendar_event_ids.ids),
            ('start', '>=', dtstart)
        ])

    def _get_week_days(self):
        """
        :return: tuple of rrule weekdays for this recurrence.
        """
        return tuple(
            rrule.weekday(weekday_index)
            for weekday_index, weekday in {
                rrule.MO.weekday: self.mon,
                rrule.TU.weekday: self.tue,
                rrule.WE.weekday: self.wed,
                rrule.TH.weekday: self.thu,
                rrule.FR.weekday: self.fri,
                rrule.SA.weekday: self.sat,
                rrule.SU.weekday: self.sun,
            }.items() if weekday
        )

    def _is_allday(self):
        """Returns whether a majority of events are allday or not (there might be some outlier events)
        """
        score = sum(1 if e.allday else -1 for e in self.calendar_event_ids)
        return score >= 0

    def _get_rrule(self, dtstart=None):
        self.ensure_one()
        freq = self.rrule_type
        rrule_params = dict(
            dtstart=dtstart,
            interval=self.interval,
        )
        if freq == 'monthly' and self.month_by == 'date':  # e.g. every 15th of the month
            rrule_params['bymonthday'] = self.day
        elif freq == 'monthly' and self.month_by == 'day':  # e.g. every 2nd Monday in the month
            rrule_params['byweekday'] = getattr(rrule, RRULE_WEEKDAYS[self.weekday])(int(self.byday))  # e.g. MO(+2) for the second Monday of the month
        elif freq == 'weekly':
            weekdays = self._get_week_days()
            if not weekdays:
                raise UserError(_("You have to choose at least one day in the week"))
            rrule_params['byweekday'] = weekdays
            rrule_params['wkst'] = self._get_lang_week_start()

        if self.end_type == 'count':  # e.g. stop after X occurence
            rrule_params['count'] = min(self.count, MAX_RECURRENT_EVENT)
        elif self.end_type == 'forever':
            rrule_params['count'] = MAX_RECURRENT_EVENT
        elif self.end_type == 'end_date':  # e.g. stop after 12/10/2020
            rrule_params['until'] = datetime.combine(self.until, time.max)
        return rrule.rrule(
            freq_to_rrule(freq), **rrule_params
        )
