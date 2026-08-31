# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models

from odoo.addons.google_calendar.utils.google_calendar import GoogleCalendarService


class CalendarAttendee(models.Model):
    _inherit = 'calendar.attendee'

    def do_tentative(self):
        # Synchronize event after state change
        res = super().do_tentative()
        self._sync_event()
        return res

    def do_accept(self):
        # Synchronize event after state change
        res = super().do_accept()
        self._sync_event()
        return res


    def do_decline(self):
        # Synchronize event after state change
        res = super().do_decline()
        self._sync_event()
        return res

    def _sync_event(self):
        # For weird reasons, we can't sync status when we are not the responsible
        # We can't adapt google_value to only keep ['id', 'summary', 'attendees', 'start', 'end', 'reminders']
        # and send that. We get a Forbidden for non-organizer error even if we only send start, end that are mandatory !
        all_events = self.mapped('event_id').filtered(lambda e: e.google_id)
        # When the whole recurrence chain is updated, patch the master recurrence once instead of every
        # instance. Google then propagates the change to all instances. We only do this when every
        # instance that follows the recurrence is part of the update.
        follow_events = all_events.filtered(lambda e: e.follow_recurrence and e.recurrence_id.google_id)
        recurrences = follow_events.recurrence_id.filtered(
            lambda r: r.calendar_event_ids.filtered(lambda e: e.follow_recurrence and e.google_id) <= all_events
        )
        follow_events = follow_events.filtered(lambda e: e.recurrence_id in recurrences)
        single_events = all_events - follow_events
        recurrences = follow_events.recurrence_id
        other_events = single_events.filtered(lambda e: e.user_id and e.user_id != self.env.user)
        other_recurrences = recurrences.filtered(
            lambda r: r.base_event_id.user_id and r.base_event_id.user_id != self.env.user
        )
        events_by_user = other_events.grouped('user_id')
        recurrences_by_user = other_recurrences.grouped(lambda r: r.base_event_id.user_id)
        for user in other_events.user_id | other_recurrences.base_event_id.user_id:
            service = GoogleCalendarService(self.env['google.service'].with_user(user))
            events_by_user.get(user, other_events.browse()).with_user(user)._sync_odoo2google(service)
            recurrences_by_user.get(user, other_recurrences.browse()).with_user(user)._sync_odoo2google(service)
        google_service = GoogleCalendarService(self.env['google.service'])
        (single_events - other_events)._sync_odoo2google(google_service)
        (recurrences - other_recurrences)._sync_odoo2google(google_service)
