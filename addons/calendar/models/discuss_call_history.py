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
        # the meeting is read as sudo (see `_get_meeting`): the call is logged on the
        # document whoever attended it, as it already is for a scheduled meeting.
        return meeting._create_meeting_activity()

    def _get_log_contact(self):
        if contact := super()._get_log_contact():
            return contact
        return self._get_meeting().user_id.partner_id

    def _get_meeting(self):
        """ Return the meeting this call took place in. A recurrence shares a single
        channel between its occurrences (task-6460543), so the occurrence the call
        overlaps with is the one it belongs to, falling back on the closest one in
        time: nothing links a call to one occurrence more precisely than that.

        :return: a sudoed ``calendar.event`` recordset, void for an ad-hoc call"""
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
