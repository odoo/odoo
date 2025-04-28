# Part of Odoo. See LICENSE file for full copyright and licensing details.
from dateutil.relativedelta import relativedelta
from pytz import UTC

from odoo import api, models

from odoo.tools.intervals import Intervals
from odoo.tools.date_utils import localized, sum_intervals


class CalendarEvent(models.Model):
    _inherit = "calendar.event"

    @api.depends('allday')
    def _compute_unavailable_partner_ids(self):
        super()._compute_unavailable_partner_ids()
        complete_events = self.filtered(
            lambda event: event.start and event.stop and (event.stop > event.start or (event.stop >= event.start and event.allday)) and event.partner_ids)
        if not complete_events:
            return
        event_intervals = complete_events._get_events_interval()
        for event, event_interval in event_intervals.items():
            # Event_interval is empty when an allday event contains at least one day where the company is closed
            if not event_interval:
                continue
            start = event_interval._items[0][0]
            stop = event_interval._items[-1][1]
            schedule_by_partner = event.partner_ids._get_schedule(start, stop, merge=False)
            event.unavailable_partner_ids |= event._check_employees_availability_for_event(
                schedule_by_partner, event_interval)

    @api.model
    def get_unusual_days(self, date_from, date_to=None):
        return self.env.user.employee_id._get_unusual_days(date_from, date_to)

    def _get_events_interval(self):
        """
        This method will returned an Intervals object that represent the event's interval based of its parameters.

        If an event is scheduled for the entire day, its interval will correspond to the work interval defined by the
        company's calendar.
        If an allday event is scheduled on a day when the company is closed, the interval of this event will be empty.
        """
        start = min(self.mapped('start')).replace(hour=0, minute=0, second=0, tzinfo=UTC)
        stop = max(self.mapped('stop')).replace(hour=23, minute=59, second=59, tzinfo=UTC)
        company_calendar = self.env.company.resource_calendar_id
        global_interval = company_calendar._work_intervals_batch(start, stop)[False]
        interval_by_event = {}
        for event in self:
            if event.allday:
                # Avoid allday event with a duration of 0
                allday_event_interval = Intervals([(
                    event.start.replace(hour=0, minute=0, second=0, tzinfo=UTC),
                    event.stop.replace(hour=23, minute=59, second=59, tzinfo=UTC),
                    self.env['resource.calendar']
                )])

                if any(not (Intervals([(
                    event.start.replace(hour=0, minute=0, second=0, tzinfo=UTC) + relativedelta(days=i),
                    event.start.replace(hour=23, minute=59, second=59, tzinfo=UTC) + relativedelta(days=i),
                    self.env['resource.calendar']
                )]) & global_interval) for i in range(0, (event.stop_date - event.start_date).days + 1)):
                    interval_by_event[event] = Intervals([])
                else:
                    interval_by_event[event] = allday_event_interval & global_interval
            else:
                interval_by_event[event] = Intervals([(
                    localized(event.start),
                    localized(event.stop),
                    self.env['resource.calendar']
                )])
        return interval_by_event

    def _check_employees_availability_for_event(self, schedule_by_partner, event_interval):
        unavailable_partners = self.env["res.partner"]
        for partner, schedule in schedule_by_partner.items():
            common_interval = schedule & event_interval
            if sum_intervals(common_interval) != sum_intervals(event_interval):
                unavailable_partners |= partner
        return unavailable_partners
