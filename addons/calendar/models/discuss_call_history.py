# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class DiscussCallHistory(models.Model):
    _inherit = "discuss.call.history"

    def _get_activity_to_link(self):
        """ A meeting linked to a document carries an activity in the chatter of that
        document: the call taking place in that meeting is logged on it. A meeting linked
        to a document only after it was created has no such activity yet: it gets one. """
        if activity := super()._get_activity_to_link():
            return activity
        meeting = self._get_meeting()
        activities = meeting.meeting_activity_ids
        pending = next(
            (activity for activity in activities if not activity.date_done),
            self.env["mail.activity"],
        )
        if pending or not meeting:
            return pending
        return meeting._create_meeting_activity()

    def _get_log_contact(self):
        # an organizer logging their own meeting is not who it was held with
        if contact := super()._get_log_contact():
            return contact
        return self._get_meeting().user_id.partner_id - self.env.user.partner_id

    def _get_meeting(self):
        """ The meeting this call took place in, sudoed and void for an ad-hoc call.
        Occurrences of a recurrence share a single channel (task-6460543): the call
        belongs to the one it overlaps with, or else to the closest one in time. """
        self.ensure_one()
        # sudo: calendar.event: which meeting a call took place in, and hence which activity
        # planned it, does not depend on the reader being allowed to see that meeting.
        events = self.channel_id.sudo().calendar_event_ids
        if len(events) <= 1:
            return events
        end_dt = self.end_dt or fields.Datetime.now()
        if attended := events.filtered(lambda event: event.start <= end_dt and event.stop >= self.start_dt):
            return attended.sorted("start")[0]
        return min(events, key=lambda event: abs((event.start - self.start_dt).total_seconds()))
