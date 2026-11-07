# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models

from odoo.addons.google_calendar.utils.google_calendar import GoogleCalendarService


class CalendarAttendee(models.Model):
    _inherit = 'calendar.attendee'

    def do_tentative(self, recurrence_update_setting=None):
        # Synchronize event after state change
        res = super().do_tentative(recurrence_update_setting)
        self._sync_event(recurrence_update_setting)
        return res

    def do_accept(self, recurrence_update_setting=None):
        # Synchronize event after state change
        res = super().do_accept(recurrence_update_setting)
        self._sync_event(recurrence_update_setting)
        return res


    def do_decline(self, recurrence_update_setting=None):
        # Synchronize event after state change
        res = super().do_decline(recurrence_update_setting)
        self._sync_event(recurrence_update_setting)
        return res

    def _sync_event(self, recurrence_update_setting=None):
        # For weird reasons, we can't sync status when we are not the responsible
        # We can't adapt google_value to only keep ['id', 'summary', 'attendees', 'start', 'end', 'reminders']
        # and send that. We get a Forbidden for non-organizer error even if we only send start, end that are mandatory !
        events = self.event_id.filtered('google_id')
        recurrences = self.env['calendar.recurrence']

        follow_events = events.filtered(lambda e: e.follow_recurrence and e.recurrence_id.google_id)
        for recurrence, selected in follow_events.grouped('recurrence_id').items():
            followers = recurrence.calendar_event_ids.filtered(lambda e: e.follow_recurrence and e.google_id)
            if followers <= selected:
                # Whole chain updated: patch the master once, Google propagates to the instances.
                recurrences |= recurrence
            elif recurrence_update_setting == 'future_events':
                # Break the recurrence at the first selected event, as _apply_recurrence_values does.
                recurrence._split_from(selected.sorted('start')[0])._apply_recurrence()
            else:
                continue
            events -= selected  # handled at recurrence level, not individually

        for records in (events, recurrences):
            for user, user_records in records.grouped(lambda r: r._get_event_user()).items():
                service = GoogleCalendarService(self.env['google.service'].with_user(user))
                user_records.with_user(user)._sync_odoo2google(service)
