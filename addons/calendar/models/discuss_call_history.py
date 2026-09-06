# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class DiscussCallHistory(models.Model):
    _inherit = "discuss.call.history"

    def _get_activity_to_link(self):
        """ A meeting planned from a document carries an activity in the chatter
        of that document: the call taking place in that meeting is logged on it. """
        if activity := super()._get_activity_to_link():
            return activity
        activities = self._get_meeting().meeting_activity_ids
        return next(
            (activity for activity in activities if not activity.date_done),
            self.env["mail.activity"],
        )

    def _get_log_contact(self):
        if contact := super()._get_log_contact():
            return contact
        return self._get_meeting().user_id.partner_id

    def _get_meeting(self):
        """ Return the meeting this call took place in. A recurrence shares a single
        channel between its occurrences, so the occurrence the call overlaps with is
        the one it belongs to, falling back on the closest one in time.

        TODO: rely on the call <-> meeting link once task-6460543 provides it.

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
