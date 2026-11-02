# Part of Odoo. See LICENSE file for full copyright and licensing details.


from datetime import datetime, UTC
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.tools.misc import clean_context



MAX_RECURRENT_EVENT = 720


class CalendarRecurrence(models.Model):
    _name = 'calendar.recurrence'
    _description = 'Event Recurrence Rule'
    _inherit = ['mail.recurrence.rule.mixin']

    name = fields.Char(compute='_compute_name', store=True)
    base_event_id = fields.Many2one(
        'calendar.event', ondelete='set null', index='btree', copy=False)  # store=False ?
    calendar_event_ids = fields.One2many('calendar.event', 'recurrence_id')
    calendar_id = fields.Many2one(related='base_event_id.calendar_id', string='Calendar')

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
        context = {
            **clean_context(self.env.context),
            **{'no_mail_to_attendees': True, 'mail_create_nolog': True},
        }
        self.env['calendar.event'].with_context(context).create(event_vals)
        return detached_events

    def _setup_alarms(self):
        """ Schedule cron triggers for the alarms of the next event of each recurrence,
        starting after the date in context, or now """
        now = self.env.context.get('date') or fields.Datetime.now()
        # get next events
        self.env['calendar.event'].flush_model(fnames=['recurrence_id', 'start'])
        if not self.calendar_event_ids.ids:
            return

        self.env.cr.execute("""
            SELECT DISTINCT ON (recurrence_id) id event_id, recurrence_id
                    FROM calendar_event 
                   WHERE start > %s
                     AND id IN %s
                ORDER BY recurrence_id,start ASC;
        """, (now, tuple(self.calendar_event_ids.ids)))
        result = self.env.cr.dictfetchall()
        if not result:
            return
        events = self.env['calendar.event'].browse(value['event_id'] for value in result)
        events._setup_alarms()

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
            self.unlink()
            return detached_events

        if event.allday:
            until = self._get_start_of_period(event.start_date)
        else:
            until_datetime = self._get_start_of_period(event.start)
            until_timezoned = until_datetime.replace(tzinfo=UTC).astimezone(self._get_timezone())
            until = until_timezoned.date()
        self.write({
            'end_type': 'end_date',
            'until': until - relativedelta(days=1),
        })
        return detached_events

    @api.model
    def _detach_events(self, events):
        events.with_context(dont_notify=True).write({
            'recurrence_id': False,
            'recurrency': True,
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

    def _get_start_of_period(self, dt):
        if self.rrule_type == 'weekly':
            week_start = self._get_lang_week_start()
            start = dt + relativedelta(weekday=week_start(-1))
        elif self.rrule_type == 'monthly':
            start = dt + relativedelta(day=1)
        else:
            start = dt
        # Comparaison of DST (to manage the case of going too far back in time).
        # If we detect a change in the DST between the creation date of an event
        # and the date used for the occurrence period, we use the creation date of the event.
        # This is a hack to avoid duplication of events (for example on google calendar).
        if isinstance(dt, datetime):
            timezone = self._get_timezone()
            dst_dt = dt.replace(tzinfo=timezone, fold=1).dst()
            dst_start = start.replace(tzinfo=timezone, fold=1).dst()
            if dst_dt != dst_start:
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

    @api.depends('calendar_event_ids.start')
    def _compute_dtstart(self):
        groups = self.env['calendar.event']._read_group(
            [('recurrence_id', 'in', self.ids)],
            ['recurrence_id'],
            ['start:min']
        )
        start_mapping = {recurrence.id: start_min for recurrence, start_min in groups}
        for recurrence in self:
            recurrence.dtstart = start_mapping.get(recurrence.id)

    def _get_recurrence_limit_years(self):
        return self.env['ir.config_parameter'].sudo().get_int('calendar.max_recurrence_years', 15)

    def _get_occurrences(self, dtstart):
        """
        Get ocurrences of the rrule
        :param dtstart: start of the recurrence
        :return: iterable of datetimes
        """
        self.ensure_one()
        dtstart = self._get_start_of_period(dtstart)
        if self._is_allday():
            yield from self._get_rrule(dtstart=dtstart)
            return

        timezone = self._get_timezone()
        # Localize the starting datetime to avoid missing the first occurrence
        dtstart = dtstart.replace(tzinfo=UTC).astimezone(timezone)
        # dtstart is given as a naive datetime, but it actually represents a timezoned datetime
        # (rrule package expects a naive datetime)
        occurences = self._get_rrule(dtstart=dtstart.replace(tzinfo=None))

        # Special timezoning is needed to handle DST (Daylight Saving Time) changes.
        # Given the following recurrence:
        #   - monthly
        #   - 1st of each month
        #   - timezone America/New_York (UTC−05:00)
        #   - at 6am America/New_York = 11am UTC
        #   - from 2019/02/01 to 2019/05/01.
        # The naive way would be to store:
        # 2019/02/01 11:00 - 2019/03/01 11:00 - 2019/04/01 11:00 - 2019/05/01 11:00 (UTC)
        #
        # But a DST change occurs on 2019/03/10 in America/New_York timezone. America/New_York is now UTC−04:00.
        # From this point in time, 11am (UTC) is actually converted to 7am (America/New_York) instead of the expected 6am!
        # What should be stored is:
        # 2019/02/01 11:00 - 2019/03/01 11:00 - 2019/04/01 10:00 - 2019/05/01 10:00 (UTC)
        #                                                  *****              *****
        for occurence in occurences:
            # emulate pytz's `is_dst=False` semantics on std
            yield min(
                occurence.replace(tzinfo=timezone, fold=0),
                occurence.replace(tzinfo=timezone, fold=1),
                key=lambda d: d.utcoffset(),
            ).astimezone(UTC).replace(tzinfo=None)

    def _get_events_from(self, dtstart):
        return self.env['calendar.event'].search([
            ('id', 'in', self.calendar_event_ids.ids),
            ('start', '>=', dtstart)
        ])

    def _is_allday(self):
        """Returns whether a majority of events are allday or not (there might be some outlier events)
        """
        score = sum(1 if e.allday else -1 for e in self.calendar_event_ids)
        return score >= 0

    def _is_event_over(self):
        """Check if all events in this recurrence are in the past.
        :return: True if all events are over, False otherwise
        """
        self.ensure_one()
        if not self.calendar_event_ids:
            return False

        now = fields.Datetime.now()
        today = fields.Date.context_today(self)

        return all(
            (event.stop_date < today if event.allday else event.stop < now)
            for event in self.calendar_event_ids
        )

    def _before_calendar_cascade_unlink(self):
        """Override this method to perform actions before the cascade unlink of the recurrence when deleting a calendar."""
        return
