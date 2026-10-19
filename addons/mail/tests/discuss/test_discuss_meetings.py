# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields
from odoo.fields import Domain
from odoo.tests.common import freeze_time, new_test_user

from odoo.addons.mail.tests.common import MailCommon


@freeze_time("2024-05-20 10:00:00")
class TestDiscussMeetings(MailCommon):
    """An ad-hoc meeting ("Start Now") backs no calendar meeting: it takes place when it is
    started, which is what the "Meetings" tab of the messaging menu reads it by."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.host = new_test_user(cls.env, "test_meeting_host", tz="UTC")
        cls.env = cls.env(user=cls.host)

    def _start_meeting(self, name):
        """`create_date` comes from the database clock, which `freeze_time` does not reach."""
        with self.mock_datetime_and_now(fields.Datetime.now()):
            return self.env["discuss.channel"]._create_group(
                self.host, default_display_mode="video_full_screen", name=name,
            )

    def test_meeting_takes_place_when_it_is_started(self):
        meeting = self._start_meeting("Ad-hoc Call")
        self.assertEqual(meeting.meeting_start_dt, meeting.create_date)
        self.assertEqual(meeting.meeting_stop_dt, meeting.create_date)

    def test_meeting_lasts_as_long_as_the_call_it_was_started_for(self):
        meeting = self._start_meeting("Ad-hoc Call")
        meeting.self_member_id.sudo()._rtc_join_call()
        self.assertEqual(
            meeting.meeting_stop_dt, meeting.create_date, "the call is still going on"
        )
        with freeze_time("2024-05-20 10:30:00"):
            meeting.self_member_id.sudo()._rtc_leave_call()
        self.assertEqual(meeting.meeting_stop_dt, fields.Datetime.from_string("2024-05-20 10:30:00"))

    def test_today_domain_only_matches_the_meetings_started_today(self):
        today = self._start_meeting("Ad-hoc Call")
        with freeze_time("2024-05-19 10:00:00"):
            yesterday = self._start_meeting("Yesterday Call")
        chat = self.env["discuss.channel"]._create_group(self.host, name="Not a meeting")
        channels = today + yesterday + chat
        self.assertEqual(
            self.env["discuss.channel"].search(
                Domain("id", "in", channels.ids)
                & self.env["discuss.channel"]._get_meeting_today_domain()
            ),
            today,
        )

    def test_ongoing_domain_only_matches_the_meetings_hosting_a_call(self):
        """The meetings still going on are the ones the tab shows first, and an ad-hoc meeting
        lasts as long as the call it was started for."""
        calling = self._start_meeting("Ad-hoc Call")
        idle = self._start_meeting("Ended Call")
        # the call history is written by the RTC machinery, never by the user
        self.env["discuss.call.history"].sudo().create([
            {"channel_id": calling.id, "start_dt": fields.Datetime.now()},
            {
                "channel_id": idle.id,
                "start_dt": fields.Datetime.now(),
                "end_dt": fields.Datetime.now(),
            },
        ])
        self.assertEqual(
            self.env["discuss.channel"].search(
                Domain("id", "in", (calling + idle).ids)
                & self.env["discuss.channel"]._get_meeting_ongoing_domain()
            ),
            calling,
        )
