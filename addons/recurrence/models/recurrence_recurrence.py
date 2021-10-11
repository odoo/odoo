# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, time
import pytz

from dateutil import rrule
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.addons.base.models.res_partner import _tz_get
from odoo.tools import get_timedelta
from odoo.osv import expression

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


class RecurrenceRecurrence(models.Model):
    """ TODO big description how to use this

    """
    _name = 'recurrence.recurrence'
    _description = 'Recurrence'

    name = fields.Char(compute='_compute_name', store=True)
    model = fields.Char('Related Recurrent Model', index=True)
    base_id = fields.Many2oneReference('Related Base Document ID', index=True, model_field='model')
    record_tz = fields.Selection(
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
    batch = fields.Boolean(help="Create all the records at once or only for the following months")
    # date of the latest record created.
    last_record_time = fields.Date(store=True)
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company)

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
                rrule_args = recurrence._update_rrule_args(None)
                weekdays = recurrence._get_week_days(rrule_args)
                # Convert Weekday object
                weekdays = [str(w) for w in weekdays]
                # We need to get the day full name from its three first letters.
                week_map = {v: k for k, v in RRULE_WEEKDAYS.items()}
                weekday_short = [week_map[w] for w in weekdays]
                day_strings = [d[1] for d in WEEKDAY_SELECTION if d[0] in weekday_short]
                on = _("on %s") % ", ".join([day_name for day_name in day_strings])
            elif recurrence.rrule_type == 'monthly':
                if recurrence.month_by == 'day':
                    weekday_label = dict(BYDAY_SELECTION)[recurrence.byday]
                    on = _("on the %(position)s %(weekday)s", position=recurrence.byday, weekday=weekday_label)
                else:
                    on = _("day %s", recurrence.day)
            else:
                on = ''
            recurrence.name = ' '.join(filter(lambda s: s, [every, on, end]))

    def _compute_dtstart(self):
        models = self.mapped('model')
        for model in models:
            groups = self.env[model].read_group([('recurrence_id', 'in', self.ids)], ['start_datetime:min'],
                                                           ['recurrence_id'])
            start_mapping = {
                group['recurrence_id'][0]: group['start_datetime']
                for group in groups
            }
            for recurrence in self:
                recurrence.dtstart = start_mapping.get(recurrence.id)

    @api.depends(
        'byday', 'until', 'rrule_type', 'month_by', 'interval',
        'count', 'end_type', 'mon', 'tue', 'wed', 'thu',
        'fri', 'sat', 'sun', 'day', 'weekday')
    def _compute_rrule(self):
        for recurrence in self:
            recurrence.rrule = recurrence._rrule_serialize()

    def _inverse_rrule(self):
        for recurrence in self:
            if recurrence.rrule:
                values = self._rrule_parse(recurrence.rrule, recurrence.dtstart)
                recurrence.write(values)

    def _reconcile_records(self, ranges, existing_records):
        """
        :param ranges: iterable of tuples (datetime_start, datetime_stop)
        :param existing_records: records to keep. Normally, it should be the base record
        :return: tuple (events of the recurrence already in sync with ranges,
                 and ranges not covered by any events)
        """
        ranges = set(ranges)
        synched_records = self._get_recurrent_records(model=self.model) | existing_records
        synced_records = synched_records.filtered(lambda e: e._range() in ranges)
        existing_ranges = set(rec._range() for rec in synced_records)
        ranges_to_create = (event_range for event_range in ranges if event_range not in existing_ranges)
        return synced_records, ranges_to_create

    def _apply_recurrence(self, specific_values_creation=None, model=None, generic_values_creation=None, keep_base=False):
        """Create missing events in the recurrence and detach events which no longer
        follow the recurrence rules.
        :return: detached events
        """
        if not model:
            raise ValidationError(_("The recurrence could not be created without model name"))
        date_today = fields.Datetime.from_string(fields.Date.today())
        record_vals = []
        keep = self.env[model]
        if specific_values_creation is None:
            specific_values_creation = {}
        record_ids = self.env[model]
        recurrences = self.filtered(lambda r: r.model == model)
        for recurrence in recurrences:
            base_record = self.env[model].browse(recurrence.base_id).exists()
            if not base_record:
                base_record = recurrence._get_first_record(include_outliers=False, model=model)
                recurrence.base_id = base_record.id
            recurrence.base_id = base_record.id
            base_record.recurrence_id = recurrence.id
            record_ids |= base_record
            duration = base_record.stop_datetime - base_record.start_datetime
            if specific_values_creation:
                ranges = set([(x[1], x[2]) for x in specific_values_creation if x[0] == recurrence.id])
            else:
                batch_interval = base_record.next_recurrence_interval
                batch_util = base_record._default_batch() and date_today.date() + get_timedelta(batch_interval, 'month')
                ranges = recurrence._range_calculation(base_record, duration, batch_util)
                if keep_base:
                    keep |= base_record
            base_values = base_record._get_recurring_values()
            records_to_keep, ranges = recurrence._reconcile_records(ranges, existing_records=record_ids)
            keep |= records_to_keep

            values = []
            for start, stop in ranges:
                # Update values according to base record, recurrence and datetime. Make sure the records are active if the base record is not
                value = dict(base_values, active=True, start_datetime=start, stop_datetime=stop, recurrence_id=recurrence.id, follow_recurrence=True, recurrency=True)
                if (recurrence.id, start, stop) in specific_values_creation:
                    value.update(specific_values_creation[(recurrence.id, start, stop)])
                if generic_values_creation and recurrence.id in generic_values_creation:
                    value.update(generic_values_creation[recurrence.id])
                values += [value]
            record_vals += values
            if record_vals:
                latest_start_datetime = record_vals and max([e['start_datetime'] for e in record_vals])
                recurrence.last_record_time = latest_start_datetime and latest_start_datetime.date()

        expandable_records = self.env[model].search([('recurrence_id', 'in', recurrences.ids)]) - keep
        detached_events = self._detach_records(expandable_records)
        self.env[model].with_context(no_mail_to_attendees=True, mail_create_nolog=True).create(record_vals)
        # call post apply here to override in project ?
        # Some model will create more recurrences when parent_id/child_ids mechanism are involved.
        # These recurrences have no base_id at the creation time
        # # arj fixme: check if needed
        # orphan_recurrence = self.search([('base_id', '=', 0), ('model', '=', model)])
        # for rec in orphan_recurrence:
        #     first_record = rec._get_first_record(include_outliers=False, model=model)
        #     if first_record:
        #         rec.base_id = first_record.id
        #     else:
        #         BOUM

        return detached_events


    def _split_from(self, record, recurrence_values=None):
        """Stops the current recurrence at the given event and creates a new one starting
        with the event.
        :param event: starting point of the new recurrence
        :param recurrence_values: values applied to the new recurrence
        :return: new recurrence
        """
        if recurrence_values is None:
            recurrence_values = {}
        record.ensure_one()
        if not self:
            return
        [values] = self.copy_data()
        detached_records = self._stop_at(record)

        count = recurrence_values.get('count', 0) or len(detached_records)
        new_recurrence = self.create({
            **values,
            **recurrence_values,
            'base_id': record.id,
            'model': record._name,
            'count': max(count, 1),
            'batch': self.env[record._name]._default_batch()
        })
        return new_recurrence, detached_records

    def _stop_at(self, record):
        """Stops the recurrence at the given event. Detach the event and all following
        events from the recurrence.

        :return: detached events from the recurrence
        """
        self.ensure_one()
        records = self._get_record_from(record.start_datetime, model=self.model)
        detached_events = self._detach_records(records)

        recurring_records = self._get_recurrent_records(model=self.model)
        if not recurring_records:
            self.with_context(archive_on_error=True).unlink()
            return detached_events
        rrule_args = self._update_rrule_args()
        if record.allday:
            until = self._get_start_of_period(record.start_date, rrule_args)
        else:
            until_datetime = self._get_start_of_period(record.start_datetime, rrule_args)
            until_timezoned = pytz.utc.localize(until_datetime).astimezone(self._get_timezone())
            until = until_timezoned.date()
        self.write({
            'end_type': 'end_date',
            'until': until - relativedelta(days=1),
        })
        return detached_events

    @api.model
    def _detach_records(self, record):
        record.write({
            'recurrence_id': False,
            'recurrency': False,
        })
        return record

    def _write_records(self, values, dtstart=None):
        """
        Write values on events in the recurrence.
        :param values: event values
        :param dtstart: if provided, only write events starting from this point in time
        """
        records = self._get_record_from(dtstart, model=self.model) if dtstart else self._get_recurrent_records(model=self.model)
        return records.with_context(no_mail_to_attendees=True, dont_notify=True).write(
            dict(values, recurrence_update='self_only'))

    def _rrule_serialize(self):
        """
        Compute rule string according to value type RECUR of iCalendar
        :return: string containing recurring rule (empty if no rule)
        """
        if self.interval <= 0:
            raise UserError(_('The interval cannot be negative.'))
        if self.end_type == 'count' and self.count <= 0:
            raise UserError(_('The number of repetitions cannot be negative.'))
        rrule_args = self._update_rrule_args()
        return str(self._get_rrule(rrule_args=rrule_args)) if self.rrule_type else ''

    @api.model
    def _rrule_parse(self, rule_str, date_start):
        # LUL TODO clean this mess
        # ARJ: it works and I don't see how it could be cleaner for now
        data = {}
        day_list = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']

        if 'Z' in rule_str and date_start and not date_start.tzinfo:
            # When a rule_str is ending by 'Z', it means that it is in UTC. This is a standard
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
        return rrule.weekday(week_start - 1)  # rrule expects an int from 0 to 6

    def _get_start_of_period(self, dt, rrule_args):
        rrule_type = rrule_args.get('rrule_type')
        if rrule_type == 'weekly':
            week_start = self._get_lang_week_start()
            start = dt and dt + relativedelta(weekday=week_start(-1))
        elif rrule_type == 'monthly':
            start = dt + relativedelta(day=1)
        else:
            start = dt
        return start

    def _get_first_record(self, model=None, include_outliers=False):
        records = self._get_recurrent_records(model=model, order='start_datetime')
        if not records:
            return self.env[model]
        if not include_outliers:
            records -= self._get_outliers(model=model)
        return records[:1]

    def _get_outliers(self, model=None):
        synced_records = self.env[model]
        records = self._get_recurrent_records(model=model)
        for recurrence in self:
            records = recurrence._get_recurrent_records(model=model)
            if records:
                start = min(records.mapped('start_datetime'))
                rrule_args = self._update_rrule_args()
                starts = set(recurrence._get_occurrences(start, rrule_args))
                synced_records |= records.filtered(lambda e: e.start_datetime in starts)
        return records - synced_records

    def _update_rrule_args(self, rrule_args=None):
        """The code related to range calculation can either use the field value of the current record or rrule_args
        values to calculate hypothetical.
        This method populate rrule_args when the values needs to be taken from the current record
        """
        if not rrule_args:
            self.ensure_one()
            rrule_args = {}
            fields = self.env[self.model]._get_recurrent_fields()
            rrule_fields = [f for f in fields if f not in ['rrule', 'next_recurrence_interval']]
            for key in rrule_fields:
                rrule_args[key] = self[key]
            if rrule_args['rrule_type'] == 'weekly':
                rrule_args['weekdays'] = self._get_week_days(rrule_args)
            rrule_args['allday'] = self._is_allday()
        return rrule_args

    def _range_calculation(self, record, duration, batch_until=None, rrule_args=None, bypass_batch=None):
        """
        Calculate the range of recurrence when applying the recurrence
        The following issues are taken into account:

        First: arj todo blablabla

        Second: without batch mode
            start of period is sometimes in the past (weekly or monthly rule).
            We can easily filter these range values but then the count value may be wrong...
            In that case, we just increase the count value, recompute the ranges and dismiss the useless values
        :param record: base record used to calculate the ranges
        :param duration: duration of the 'event'
        :param batch_until: create records until this date. Used in batch mode
        :param rrule_args: rrule parameters to calculate specific ranges without using the field values in self
        :param bypass_batch: bypass batch spectific calculation. Useful in simulations to always get correct values
        :return: set of ranges
        """

        rrule_args = self._update_rrule_args(rrule_args)
        original_until = rrule_args['end_type'] == 'end_date' and rrule_args['until']
        original_count = rrule_args['end_type'] == 'count' and rrule_args['count']
        start_datetime = rrule_args.get('start_datetime') or record.start_datetime
        ranges = set(self._get_ranges(start_datetime, duration, rrule_args))
        # First issue: properly handle batch mode to avoid creating all records at once
        # We truncate events in the future
        if batch_until:
            ranges = set((x, y) for x, y in ranges if start_datetime.date() <= x.date() <= batch_until and start_datetime.date() <= y.date() <= batch_until)
        else:
            ranges = set((x, y) for x, y in ranges if x.date() >= start_datetime.date() and y.date() >= start_datetime.date())
        # Second issue: events created before the base record, end_type == count, we need to increase
        if (bypass_batch or not self.batch) and original_count and len(ranges) < original_count:
            # Rise count number because some past values will be dismissed.
            rrule_args['count'] = (2*original_count) - len(ranges)
            ranges = set(self._get_ranges(start_datetime, duration, rrule_args))
            # We set back the occurrence number to its original value
            rrule_args['count'] = original_count
        # Remove ranges of events occurring in the past
        ranges = set((x, y) for x, y in ranges if x.date() >= start_datetime.date() and y.date() >= start_datetime.date())
        if original_until != self.until:
            # Set back the until value. Mostly needed for batch processing. Inoffensive for empty recurrence
            self.until = original_until
        return ranges

    def _get_ranges(self, start, event_duration, rrule_args=None):
        starts = self._get_occurrences(start, rrule_args)
        return ((st, st + event_duration) for st in starts)

    def _get_timezone(self):
        return pytz.timezone(self.record_tz or self.env.context.get('tz') or 'UTC')

    def _get_occurrences(self, dtstart, rrule_args=None):
        """
        Get ocurrences of the rrule
        :param dtstart: start of the recurrence
        :param rrule_args: rrule args to avoid using the field values of self
        :return: iterable of datetimes
        """
        dtstart = self._get_start_of_period(dtstart, rrule_args)
        if rrule_args.get('allday'):
            return self._get_rrule(dtstart=dtstart, rrule_args=rrule_args)

        timezone = self._get_timezone()
        # Localize the starting datetime to avoid missing the first occurrence
        dtstart = pytz.utc.localize(dtstart).astimezone(timezone)
        # dtstart is given as a naive datetime, but it actually represents a timezoned datetime
        # (rrule package expects a naive datetime)
        occurences = self._get_rrule(dtstart=dtstart.replace(tzinfo=None), rrule_args=rrule_args)

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
        return (timezone.localize(occurrence, is_dst=False).astimezone(pytz.utc).replace(tzinfo=None) for occurrence in
                occurences)

    def _get_record_from(self, dtstart, model):
        model = model or self.model
        return self.env[model].search([
            ('recurrence_id', 'in', self.ids),
            ('start_datetime', '>=', dtstart)
        ])

    @api.model
    def _get_week_days(self, rrule_args):
        """
        :return: tuple of rrule weekdays for this recurrence.
        """
        return tuple(
            rrule.weekday(weekday_index)
            for weekday_index, weekday in {
                rrule.MO.weekday: rrule_args['mon'],
                rrule.TU.weekday: rrule_args['tue'],
                rrule.WE.weekday: rrule_args['wed'],
                rrule.TH.weekday: rrule_args['thu'],
                rrule.FR.weekday: rrule_args['fri'],
                rrule.SA.weekday: rrule_args['sat'],
                rrule.SU.weekday: rrule_args['sun'],
            }.items() if weekday
        )

    def _is_allday(self):
        """Returns whether a majority of events are allday or not (there might be some outlier events)
        """
        self.ensure_one()
        # base_id may not exists when this is called in unlink override to update the base_id
        record_ids = self._get_recurrent_records() | self.env[self.model].browse(self.base_id).exists()
        score = sum(1 if e.allday else -1 for e in record_ids)
        return score >= 0

    def _get_rrule(self, dtstart=None, rrule_args=None):
        if not rrule_args:
            rrule_args = self._update_rrule_args()
        rrule_params = dict(
            dtstart=dtstart,
            interval=rrule_args['interval'],
        )
        if rrule_args['rrule_type'] == 'monthly' and rrule_args['month_by'] == 'date':  # e.g. every 15th of the month
            rrule_params['bymonthday'] = rrule_args['day']
        elif rrule_args['rrule_type'] == 'monthly' and rrule_args['month_by'] == 'day':  # e.g. every 2nd Monday in the month
            rrule_params['byweekday'] = getattr(rrule, RRULE_WEEKDAYS[rrule_args['weekday']])(
                int(rrule_args['byday']))  # e.g. MO(+2) for the second Monday of the month
        elif rrule_args['rrule_type'] == 'weekly':
            weekdays = rrule_args['weekdays']
            if 'weekdays' not in rrule_args.keys():
                raise UserError(_("You have to choose at least one day in the week"))
            rrule_params['byweekday'] = weekdays
            rrule_params['wkst'] = self._get_lang_week_start()

        if rrule_args['end_type'] == 'count':  # e.g. stop after X occurence
            rrule_params['count'] = min(rrule_args['count'], MAX_RECURRENT_EVENT)
        elif rrule_args['end_type'] == 'forever':
            rrule_params['count'] = MAX_RECURRENT_EVENT
        elif rrule_args['end_type'] == 'end_date':  # e.g. stop after 12/10/2020
            rrule_params['until'] = datetime.combine(rrule_args['until'], time.max)

        return rrule.rrule(
            freq_to_rrule(rrule_args['rrule_type']), **rrule_params
        )

    def _get_recurrent_records(self, model=None, order=None):
        record_model = set(self.mapped('model'))
        if not model and len(record_model) > 1:
            # arj todo: raise usererror or something ?
            return
        model = model or record_model.pop()
        return self.env[model].search([('recurrence_id', 'in', self.ids)], order=order)

    @api.model
    def _get_batch_domain(self, model, company, delta):
        now = fields.Datetime.now()
        batch_date_domain = expression.OR([
            [('last_record_time', '<', now + delta)],
            [('last_record_time', '=', False)]
        ])
        model_domain = expression.AND([
            [('batch', '=', True)],
            [('model', '=', model)],
            [('company_id', '=', company.id)],
        ])
        until_domain = expression.AND([[('end_type', '=', 'end_date')], [('until', '>', now - delta)]])

        end_domain = expression.OR([
            until_domain,
            [('end_type', 'in', ['forever', 'count'])],
        ])
        domain = expression.AND([batch_date_domain, end_domain, model_domain])
        return domain

    @api.model
    def _cron_schedule_next(self, model):
        companies = self.env['res.company'].search([])
        recurrences = self.env['recurrence.recurrence']
        for company in companies:
            interval = self.env[model].with_company(company)._default_next_recurrence_interval()
            delta = get_timedelta(interval, 'month')
            domain = self._get_batch_domain(model, company, delta)
            recurrences |= self.search(domain)

        recurrences._repeat_records()

    def _repeat_records(self):
        """ Reapply batch recurrences to create new records.
        Recurrences without associated records are deleted.
        """
        if not self:
            return
        for recurrence in self:
            recurrence.filtered(lambda rec: rec.base_id)._apply_recurrence(model=recurrence.model)

        # arj fixme after discussion
        # records = self.env[model].search_read([('recurrence_id', 'in', self.ids)], fields=['recurrence_id'])
        # # Remove unused recurrences
        # used_ids = [d['recurrence_id'][0] for d in records]
        # unused_ids = [id for id in self.ids if id not in used_ids]
        # # arj todo: it will bring issues if project create recurrent task with 0 task at moment X (first creation in one week)
        # # and planning is asking to delete the recurrence when not needed.
        # self.browse(unused_ids).unlink()
