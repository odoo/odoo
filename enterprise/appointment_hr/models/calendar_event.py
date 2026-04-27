# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, models
from odoo.addons.appointment.utils import interval_from_events, intervals_overlap
from odoo.addons.resource.models.utils import Intervals, timezone_datetime


class CalendarEvent(models.Model):
    _inherit = "calendar.event"

    @api.depends('start', 'stop', 'partner_ids')
    def _compute_on_leave_partner_ids(self):
        super()._compute_on_leave_partner_ids()

        user_events = self.filtered(
            lambda event:
                event.appointment_type_id.schedule_based_on == 'users' and
                event.partner_ids.filtered('user_ids') > event.on_leave_partner_ids
        )
        if not user_events:
            return

        calendar_ids = user_events.partner_ids.user_ids.employee_ids.resource_calendar_id
        calendar_to_employees = user_events.partner_ids.user_ids.employee_ids.grouped('resource_calendar_id')

        for start, stop, events in interval_from_events(user_events):
            group_calendars = calendar_ids.filtered(lambda calendar: calendar in events.partner_ids.user_ids.employee_ids.resource_calendar_id)
            calendar_to_unavailabilities = {
                calendar: calendar._unavailable_intervals_batch(
                    timezone_datetime(start), timezone_datetime(stop), calendar_to_employees[calendar].resource_id
                ) for calendar in group_calendars
            }
            for event in events:
                # avoid some work for partners already on the list
                partner_employees = (event.partner_ids - event.on_leave_partner_ids).user_ids.employee_ids
                for employee in partner_employees:
                    if not employee.resource_calendar_id or not employee.resource_id:
                        continue
                    unavailabilities = calendar_to_unavailabilities.get(employee.resource_calendar_id, {}).get(employee.resource_id.id, [])
                    if any(intervals_overlap(unavailability, (event.start, event.stop)) for unavailability in unavailabilities):
                        event.on_leave_partner_ids += employee.user_partner_id

    @api.model
    def _gantt_unavailability(self, field, res_ids, start, stop, scale):
        result = super()._gantt_unavailability(field, res_ids, start, stop, scale)

        # skip if not dealing with appointments
        if field != 'partner_ids':
            return result

        start = timezone_datetime(start)
        stop = timezone_datetime(stop)

        partners = self.env['res.partner'].browse(res_ids)
        users = partners.user_ids
        users_from_partner_id = users.grouped(lambda user: user.partner_id.id)

        calendars = users.employee_id.resource_calendar_id
        employee_by_calendar = users.employee_id.grouped('resource_calendar_id')
        unavailabilities_by_calendar = {
            calendar: calendar._unavailable_intervals_batch(
                start, stop,
                resources=employee_by_calendar[calendar].resource_id
            ) for calendar in calendars
        }

        event_unavailabilities = self._gantt_unavailabilities_events(start, stop, partners)

        for partner_id in res_ids:
            attendee_users = users_from_partner_id.get(partner_id, self.env['res.users'])
            attendee = partners.filtered(lambda partner: partner.id == partner_id)

            # calendar leaves
            unavailabilities = Intervals([
                (unavailability['start'], unavailability['stop'], self.env['res.partner'])
                for unavailability in result.get(partner_id, [])
            ])
            unavailabilities |= event_unavailabilities.get(attendee.id, Intervals([]))
            for user in attendee_users.filtered('employee_resource_calendar_id'):
                calendar_leaves = unavailabilities_by_calendar[user.employee_resource_calendar_id]
                unavailabilities |= Intervals([
                    (start, end, attendee)
                    for start, end in calendar_leaves.get(user.employee_id.resource_id.id, [])])
            result[partner_id] = [{'start': start, 'stop': stop} for start, stop, _ in unavailabilities]
        return result
