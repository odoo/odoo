# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import datetime, timedelta

from odoo import fields
from odoo.addons.base.models.avatar_mixin import generate_text_avatar_svg
from odoo.fields import Domain
from odoo.tests import Form
from odoo.tests.common import HttpCase, TransactionCase, freeze_time, new_test_user


@freeze_time("2024-05-20 10:00:00")
class TestDiscussMeetings(TransactionCase):
    """A meeting holding a Discuss video call link owns its channel right away, so that it
    shows in the Discuss "Meetings" tab and its invitation link can be shared."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.organizer = new_test_user(cls.env, "test_meeting_organizer", tz="UTC")
        cls.attendee = new_test_user(cls.env, "test_meeting_attendee", tz="UTC")
        cls.env = cls.env(user=cls.organizer)

    def _create_meeting(self, name, start, with_videocall=True, **values):
        return self.env["calendar.event"].create({
            "name": name,
            "partner_ids": [(4, self.organizer.partner_id.id), (4, self.attendee.partner_id.id)],
            "start": start,
            "stop": start + timedelta(hours=1),
            "videocall_location": (
                self.env["calendar.event"].get_discuss_videocall_location()
                if with_videocall
                else False
            ),
            **values,
        })

    def _create_ad_hoc_meeting(self, name):
        """The channel a "Start Now" meeting opens: a video call backing no meeting.

        `create_date` comes from the database clock, which `freeze_time` alone does not reach."""
        with self.mock_datetime_and_now(fields.Datetime.now()):
            return self.env["discuss.channel"]._create_group(
                self.organizer, default_display_mode="video_full_screen", name=name,
            )

    def _create_recurring_meeting(self, name, start, **values):
        return self._create_meeting(
            name,
            start,
            count=3,
            end_type="count",
            interval=1,
            mon=True,
            recurrency=True,
            rrule_type="weekly",
            **values,
        )

    def test_filling_in_the_scheduling_form_creates_no_channel(self):
        """Ticking "All day" makes `_onchange_date` write on the draft record of the form: no
        channel may come out of it, the meeting itself is not created yet (and has no name)."""
        channels = self.env["discuss.channel"].search([])
        videocall_location = self.env["calendar.event"].get_discuss_videocall_location()
        form = Form(
            # the defaults `openScheduleMeeting` opens the calendar on
            self.env["calendar.event"].with_context(
                default_access_token=videocall_location.split("/")[-1],
                default_videocall_location=videocall_location,
                is_quick_create_form=True,
            ),
            view="calendar.view_calendar_event_form_quick_create",
        )
        form.allday = True
        self.assertEqual(
            self.env["discuss.channel"].search([]),
            channels,
            "the channel waits for the meeting to be saved",
        )

    def test_meeting_with_videocall_owns_a_pinned_meeting_channel(self):
        meeting = self._create_meeting("Product Demo", datetime(2024, 5, 20, 14, 0))
        channel = meeting.videocall_channel_id
        self.assertEqual(channel.name, "Product Demo")
        self.assertEqual(channel.channel_type, "group")
        self.assertEqual(channel.default_display_mode, "video_full_screen")
        self.assertEqual(
            channel.channel_member_ids.partner_id,
            self.organizer.partner_id + self.attendee.partner_id,
            "attendees having a user are members of the meeting channel",
        )
        self.assertEqual(channel.description, meeting.display_time)
        self.assertTrue(
            all(channel.channel_member_ids.mapped("is_pinned")),
            "the meeting shows in the Discuss meetings tab of every member",
        )

    def test_only_upcoming_meetings_with_a_discuss_videocall_get_a_channel(self):
        upcoming = self._create_meeting("Product Demo", datetime(2024, 5, 20, 14, 0))
        over = self._create_meeting("Yesterday Retrospective", datetime(2024, 5, 19, 14, 0))
        no_videocall = self._create_meeting(
            "Coffee Break", datetime(2024, 5, 20, 16, 0), with_videocall=False,
        )
        custom_videocall = self._create_meeting(
            "Google Meet Call",
            datetime(2024, 5, 20, 17, 0),
            with_videocall=False,
            videocall_location="https://meet.google.com/odoo-test",
        )
        meetings = upcoming + over + no_videocall + custom_videocall
        self.assertEqual(
            meetings.filtered("videocall_channel_id"),
            upcoming,
            "only a Discuss video call still to come at the frozen now (10:00) owns a channel",
        )

    def test_adding_a_videocall_afterwards_creates_the_channel(self):
        meeting = self._create_meeting(
            "Product Demo", datetime(2024, 5, 20, 14, 0), with_videocall=False,
        )
        meeting._set_discuss_videocall_location()
        self.assertEqual(meeting.videocall_channel_id.name, "Product Demo")

    def test_editing_a_meeting_keeps_its_channel_in_sync(self):
        meeting = self._create_meeting("Product Demo", datetime(2024, 5, 20, 14, 0))
        channel = meeting.videocall_channel_id
        meeting.write({"name": "Product Demo v2", "start": datetime(2024, 5, 21, 14, 0)})
        self.assertEqual(meeting.videocall_channel_id, channel, "the channel is kept")
        self.assertEqual(channel.name, "Product Demo v2")
        self.assertEqual(channel.description, meeting.display_time)

    def test_deleting_a_meeting_removes_its_channel(self):
        deleted = self._create_meeting("Product Demo", datetime(2024, 5, 20, 14, 0))
        kept = self._create_meeting("Weekly Sync", datetime(2024, 5, 20, 15, 0))
        channels = deleted.videocall_channel_id + kept.videocall_channel_id
        deleted.unlink()
        self.assertEqual(
            channels.exists(),
            kept.videocall_channel_id,
            "only the video call of the deleted meeting is gone",
        )

    def test_deleting_a_meeting_with_messages_keeps_its_channel_unpinned(self):
        deleted = self._create_meeting("Product Demo", datetime(2024, 5, 20, 14, 0))
        channel = deleted.videocall_channel_id
        channel.message_post(body="Let's review the demo", message_type="comment")
        with freeze_time("2024-05-21 10:00:00"):
            # the unpin happens after the last message, so that `unpin_dt` is not equal to
            # `last_interest_dt`, which `is_pinned` treats as still pinned
            deleted.unlink()
        self.assertTrue(
            channel.exists(),
            "the chat history of a meeting that already hosted a conversation is kept",
        )
        self.assertFalse(channel.calendar_event_ids)
        self.assertTrue(
            all(not member.is_pinned for member in channel.channel_member_ids),
            "the kept channel is unpinned for everyone, so it drops out of the meetings tab",
        )

    def test_deleting_a_recurrence_removes_its_channel_with_the_last_meeting(self):
        meeting = self._create_recurring_meeting("Weekly Sync", datetime(2024, 5, 20, 14, 0))
        occurrences = meeting.recurrence_id.calendar_event_ids
        channel = occurrences.videocall_channel_id
        occurrences[0].unlink()
        self.assertEqual(
            channel.exists(),
            channel,
            "the video call is still shared by the remaining occurrences",
        )
        occurrences.exists().unlink()
        self.assertFalse(channel.exists(), "the last meeting took its video call away")

    def test_today_filter_domain_only_matches_the_meetings_of_today(self):
        """Domain behind the "Today" filter of the Discuss "Meetings" tab, see
        `DiscussMessagingMenuController._get_menu_tab_filter_domain`."""
        today = self._create_meeting("Product Demo", datetime(2024, 5, 20, 14, 0))
        # a meeting running over several days is on today too, one of another day is not
        spanning = self._create_meeting("Team Building", datetime(2024, 5, 19, 9, 0))
        spanning.stop = datetime(2024, 5, 21, 18, 0)
        # the channel of tomorrow's meeting is created today, yet the meeting is not of today
        tomorrow = self._create_meeting("Weekly Sync", datetime(2024, 5, 21, 14, 0))
        # an ad-hoc meeting ("Start Now") backs no meeting: it takes place the day it is started
        ad_hoc = self._create_ad_hoc_meeting("Ad-hoc Call")
        with freeze_time("2024-05-19 10:00:00"):
            over = self._create_ad_hoc_meeting("Yesterday Call")
        channels = (today + spanning + tomorrow).videocall_channel_id + ad_hoc + over
        self.assertEqual(
            self.env["discuss.channel"].search(
                Domain("id", "in", channels.ids)
                & self.env["discuss.channel"]._get_meeting_today_domain()
            ),
            (today + spanning).videocall_channel_id + ad_hoc,
        )

    def test_ongoing_domain_matches_the_meetings_still_to_come(self):
        """Domain putting the meetings the tab lists first on the first page of the load more,
        see `DiscussMessagingMenuController._get_menu_tab_priority_domain`."""
        over = self._create_meeting("Retrospective", datetime(2024, 5, 20, 8, 0))
        going_on = self._create_meeting("Product Demo", datetime(2024, 5, 20, 9, 30))
        to_come = self._create_meeting("Weekly Sync", datetime(2024, 5, 21, 14, 0))
        channels = (over + going_on + to_come).videocall_channel_id
        self.assertEqual(
            self.env["discuss.channel"].search(
                Domain("id", "in", channels.ids)
                & self.env["discuss.channel"]._get_meeting_ongoing_domain()
            ),
            (going_on + to_come).videocall_channel_id,
        )

    def test_meeting_dates_expose_the_ongoing_or_next_occurrence(self):
        """The occurrences of a recurrence share a single channel, so the one going on or coming
        next stands for it, and the last one keeps standing for it once they are all over."""
        meeting = self._create_recurring_meeting("Weekly Sync", datetime(2024, 5, 20, 14, 0))
        first, second, third = meeting.recurrence_id.calendar_event_ids.sorted("start")
        channel = meeting.videocall_channel_id
        self.assertEqual((channel.meeting_start_dt, channel.meeting_stop_dt), (first.start, first.stop))
        with freeze_time("2024-05-20 14:30:00"):
            channel.invalidate_recordset()
            self.assertEqual(channel.meeting_start_dt, first.start, "the meeting going on stands for the channel")
        with freeze_time("2024-05-20 16:00:00"):
            channel.invalidate_recordset()
            self.assertEqual(channel.meeting_start_dt, second.start, "the next occurrence takes over")
        with freeze_time("2024-06-20 10:00:00"):
            channel.invalidate_recordset()
            self.assertEqual(channel.meeting_start_dt, third.start, "the last occurrence keeps standing")

    def test_ad_hoc_meeting_dates_come_from_the_creation_of_its_channel(self):
        channel = self._create_ad_hoc_meeting("Ad-hoc Call")
        self.assertEqual(channel.meeting_start_dt, channel.create_date)
        self.assertEqual(channel.meeting_stop_dt, channel.create_date)

    def test_meeting_thread_takes_place_along_with_its_meeting(self):
        meeting = self._create_meeting("Product Demo", datetime(2024, 5, 20, 14, 0))
        thread = meeting.videocall_channel_id._create_sub_channel(name="Demo follow-up")
        self.assertEqual(thread.meeting_start_dt, meeting.start)
        self.assertEqual(thread.meeting_stop_dt, meeting.stop)

    @freeze_time("2024-05-20 23:00:00")
    def test_today_filter_domain_follows_the_timezone_of_the_user(self):
        """Late evening in UTC is already the next day for a user ahead of it."""
        today_for_them = self._create_meeting("Product Demo", datetime(2024, 5, 21, 10, 0))
        tomorrow_for_them = self._create_meeting("Weekly Sync", datetime(2024, 5, 21, 23, 0))
        # started at 23:00 UTC, which is already the next day for them
        started_for_them = self._create_ad_hoc_meeting("Ad-hoc Call")
        with freeze_time("2024-05-20 20:00:00"):
            # still the same UTC day, but the day before for them
            started_yesterday_for_them = self._create_ad_hoc_meeting("Earlier Call")
        channels = (
            (today_for_them + tomorrow_for_them).videocall_channel_id
            + started_for_them
            + started_yesterday_for_them
        )
        # already 2024-05-21 01:00 in Brussels, whose day ends at 2024-05-21 21:59:59 UTC
        channel_of_them = self.env["discuss.channel"].with_context(tz="Europe/Brussels")
        self.assertEqual(
            channel_of_them.search(
                Domain("id", "in", channels.ids) & channel_of_them._get_meeting_today_domain()
            ),
            today_for_them.videocall_channel_id + started_for_them,
        )

    def test_recurring_meeting_shares_a_single_channel(self):
        meeting = self._create_recurring_meeting("Weekly Sync", datetime(2024, 5, 20, 14, 0))
        occurrences = meeting.recurrence_id.calendar_event_ids
        self.assertEqual(len(occurrences), 3)
        self.assertEqual(
            occurrences.videocall_channel_id,
            meeting.videocall_channel_id,
            "every occurrence of the recurrence joins the same video call",
        )
        self.assertEqual(occurrences.videocall_channel_id.name, "Weekly Sync")

    def test_meeting_channel_avatar_shows_the_meeting_day(self):
        meeting = self._create_meeting("Product Demo", datetime(2024, 5, 24, 14, 0))
        channel = meeting.videocall_channel_id
        self.assertEqual(
            bytes(channel._generate_avatar()),
            bytes(generate_text_avatar_svg("24", str(channel.id))),
            "the avatar shows the meeting day (the 24th), not the creation day",
        )

    def test_meeting_channel_avatar_of_a_past_meeting_keeps_the_creation_day(self):
        meeting = self._create_meeting("Product Demo", datetime(2024, 5, 24, 14, 0))
        channel = meeting.videocall_channel_id
        with freeze_time("2024-05-25 10:00:00"):
            self.assertEqual(
                bytes(channel._generate_avatar()),
                bytes(generate_text_avatar_svg(str(channel.create_date.day), str(channel.id))),
                "once the meeting is over, the avatar keeps its creation day",
            )


@freeze_time("2024-05-20 10:00:00")
class TestDiscussMeetingsGuest(HttpCase):
    """A guest of a meeting channel is not allowed to read the meeting itself, so the "Today"
    filter of the messaging menu must not resolve into a domain that reads it as them."""

    def test_today_filter_is_served_to_a_guest(self):
        organizer = new_test_user(self.env, "test_meeting_organizer", tz="UTC")
        meeting = self.env["calendar.event"].with_user(organizer).create({
            "name": "Product Demo",
            "partner_ids": [(4, organizer.partner_id.id)],
            "start": datetime(2024, 5, 20, 14, 0),
            "stop": datetime(2024, 5, 20, 15, 0),
            "videocall_location": self.env["calendar.event"].get_discuss_videocall_location(),
        })
        guest = self.env["mail.guest"].create({"name": "Guest"})
        meeting.videocall_channel_id.sudo()._add_members(guests=guest)
        res = self.make_jsonrpc_request(
            "/mail/store",
            {
                "fetch_params": [
                    [
                        "/mail/messaging_menu/discuss.channel/load_more",
                        {"tab_id": "meeting", "filter_ids": ["meeting_today"], "limit": 30},
                    ],
                ],
            },
            cookies={guest._cookie_name: guest._format_auth_cookie()},
        )
        self.assertIn(
            meeting.videocall_channel_id.id,
            [channel["id"] for channel in res["discuss.channel"]],
            "the guest gets the meeting of today they are invited to",
        )
