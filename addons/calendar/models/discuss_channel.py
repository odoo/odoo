# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.fields import Domain
from odoo.tools.sql import SQL

from odoo.addons.base.models.avatar_mixin import generate_text_avatar_svg


class DiscussChannel(models.Model):
    _inherit = "discuss.channel"

    calendar_event_ids = fields.One2many("calendar.event", "videocall_channel_id")

    def _videocall_channel_ids(self, domain=Domain.TRUE):
        """Subquery of the channels backing a meeting matching `domain`.

        The meetings are resolved into channel ids rather than left as an "any" on
        `calendar_event_ids`, whose subquery would check them against the reader: the guests and
        portal members of a meeting channel are not allowed to read the meeting itself.
        """
        events = self.env["calendar.event"]
        # sudo: calendar.event: whether a channel backs a meeting, and when it takes place, is not private
        return events.sudo()._search(Domain("videocall_channel_id", "!=", False) & domain).select(
            SQL("videocall_channel_id")
        )

    def _get_meeting_today_domain(self):
        """Meeting channels of today: those backing a meeting taking place today, and the
        ad-hoc ones started today (see `super`), which back no meeting at all."""
        events = self.env["calendar.event"]
        ad_hoc = super()._get_meeting_today_domain() & Domain(
            "id", "not in", self._videocall_channel_ids()
        )
        return Domain("id", "in", self._videocall_channel_ids(events._get_today_domain())) | ad_hoc

    def _get_meeting_ongoing_domain(self):
        """A meeting still to come, or taking place right now, is not over (see `super`)."""
        still_to_come = Domain("stop", ">=", fields.Datetime.now())
        return Domain("id", "in", self._videocall_channel_ids(still_to_come)) | super()._get_meeting_ongoing_domain()

    @api.depends("calendar_event_ids.start", "calendar_event_ids.stop")
    def _compute_meeting_dt(self):
        """A meeting channel takes place along with the meeting it backs: the one going on or
        coming next, as a recurrence shares a single channel between its occurrences. Once they
        are all over, the last one keeps standing for the channel."""
        super()._compute_meeting_dt()
        now = fields.Datetime.now()
        # sudo: calendar.event: when the meeting of an accessible channel takes place is not private
        meetings = (self | self.parent_channel_id).sudo().calendar_event_ids.sorted("start")
        meetings_by_channel = meetings.grouped("videocall_channel_id")
        for channel in self:
            if not (events := meetings_by_channel.get(channel.parent_channel_id or channel)):
                continue
            event = next((event for event in events if event.stop >= now), events[-1])
            channel.meeting_start_dt = event.start
            channel.meeting_stop_dt = event.stop

    def _should_invite_members_to_join_call(self):
        if self.calendar_event_ids:
            return False
        return super()._should_invite_members_to_join_call()

    def _generate_avatar(self):
        """A meeting channel identifies itself by the day of its meeting, not of its
        creation: the channel may be created days before the meeting takes place.

        Meetings that are over keep the creation day, like any other channel."""
        # sudo: calendar.event: whether an accessible channel backs a meeting is not private
        if self.sudo().calendar_event_ids and self.meeting_stop_dt >= fields.Datetime.now():
            local_start = fields.Datetime.context_timestamp(self, self.meeting_start_dt)
            return generate_text_avatar_svg(str(local_start.day), str(self.id))
        return super()._generate_avatar()

    def _unlink_orphan_meeting_channels(self):
        """Drop the channels of self that no longer back any meeting: the video call of a
        deleted meeting has no reason to stay in Discuss.

        A channel that already hosted a conversation is spared: it is only unpinned, so the
        chat history of the meeting stays reachable from Discuss while its video call drops
        out of the "Meetings" tab.

        The channel is shared by every event of a recurrence, so it only goes away once the
        last of those meetings is gone.
        """
        # sudo: discuss.channel: dropping or unpinning, for every member, the video call of a
        # meeting the user was allowed to delete, and counting the meetings it has left.
        channels = self.sudo().with_context(active_test=False)
        channels = channels.filtered(lambda channel: not channel.calendar_event_ids)
        channels.filtered(lambda channel: channel.message_count).channel_member_ids.unpin_dt = fields.Datetime.now()
        if orphans := channels.filtered(lambda channel: not channel.message_count):
            self.env.cr.flush()
            orphans.unlink()
