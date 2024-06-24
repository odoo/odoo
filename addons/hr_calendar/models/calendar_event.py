# Part of Odoo. See LICENSE file for full copyright and licensing details.
from pytz import UTC

from odoo import api, fields, models

from odoo.addons.resource.models.utils import Intervals, sum_intervals, timezone_datetime


class CalendarEvent(models.Model):
    _inherit = "calendar.event"

    unavailable_partner_ids = fields.Many2many('res.partner', compute='_compute_unavailable_partner_ids')

    @api.depends('partner_ids', 'start', 'stop', 'allday')
    def _compute_unavailable_partner_ids(self):
        complete_events = self.filtered(
            lambda event: event.start and event.stop and event.stop >= event.start and event.partner_ids)
        incomplete_event = self - complete_events
        incomplete_event.unavailable_partner_ids = []
        if not complete_events:
            return
        event_intervals = complete_events._get_events_interval()
        # Event without start and stop are skipped, except all day event: their interval is computed
        # based on company calendar's interval.
        for event, event_interval in event_intervals.items():
            start = event_interval._items[0][0]
            stop = event_interval._items[0][1]
            schedule_by_partner = event.partner_ids._get_schedule(start, stop, merge=False)
            event.unavailable_partner_ids = event._check_employees_availability_for_event(
                schedule_by_partner, event_interval)

    @api.model
    def get_unusual_days(self, date_from, date_to=None):
        return self.env.user.employee_id._get_unusual_days(date_from, date_to)

    def _get_events_interval(self):
        """
        Calculate the interval of an event based on its start, stop, and allday values. If an event is scheduled for the
        entire day, its interval will correspond to the work interval defined by the company's calendar.
        """
        start = min(self.mapped('start')).replace(hour=0, minute=0, second=0, tzinfo=UTC)
        stop = max(self.mapped('stop')).replace(hour=23, minute=59, second=59, tzinfo=UTC)
        company_calendar = self.env.company.resource_calendar_id
        global_interval = company_calendar._work_intervals_batch(start, stop)[False]
        interval_by_event = {}
        for event in self:
            event_interval = Intervals([(
                timezone_datetime(event.start),
                timezone_datetime(event.stop),
                self.env['resource.calendar']
            )])
            if event.allday:
                interval_by_event[event] = event_interval & global_interval
            else:
                interval_by_event[event] = event_interval
        return interval_by_event

    def _check_employees_availability_for_event(self, schedule_by_partner, event_interval):
        unavailable_partners = []
        for partner, schedule in schedule_by_partner.items():
            common_interval = schedule & event_interval
            if sum_intervals(common_interval) != sum_intervals(event_interval):
                unavailable_partners.append(partner.id)
        return unavailable_partners
