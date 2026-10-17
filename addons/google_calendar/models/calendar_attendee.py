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

    def _sync_event(self, recurrence_update_setting=None):
        # For weird reasons, we can't sync status when we are not the responsible
        # We can't adapt google_value to only keep ['id', 'summary', 'attendees', 'start', 'end', 'reminders']
        # and send that. We get a Forbidden for non-organizer error even if we only send start, end that are mandatory !
        events = self.event_id.filtered('google_id')
        follow_events = events.filtered(lambda e: e.follow_recurrence and e.recurrence_id.google_id)
        recurrences = self.env['calendar.recurrence']
        for recurrence, selected in follow_events.grouped('recurrence_id').items():
            followers = recurrence.calendar_event_ids.filtered(lambda e: e.follow_recurrence and e.google_id)
            if followers <= selected:
                # Whole chain updated -> we can update the recurrence instead of individual events
                recurrences |= recurrence
                events -= selected

        # Update the recurrence, let Google handle the instances
        for user, user_recurrences in recurrences.grouped(lambda r: r._get_event_user()).items():
            service = GoogleCalendarService(self.env['google.service'].with_user(user))
            user_recurrences.with_user(user)._sync_odoo2google(service)

        # Google API doesn't support patching a set of instances at once. Patch them one by one, but only the first
        # patch of each organizer should send an update to prevent notification spam.
        for user, user_events in events.grouped(lambda e: e._get_event_user()).items():
            service = GoogleCalendarService(self.env['google.service'].with_user(user))
            first = user_events.sorted('start')[:1]
            first.with_user(user)._sync_odoo2google(service)
            (user_events - first).with_user(user).with_context(google_skip_update_notification=True)._sync_odoo2google(service)
