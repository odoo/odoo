# Part of Odoo. See LICENSE file for full copyright and licensing details.
from ast import literal_eval
from datetime import datetime, timedelta

from lxml import html

from odoo.tests.common import TransactionCase, freeze_time, new_test_user


@freeze_time("2026-08-14 11:00:00")
class TestCallHistoryAutoLog(TransactionCase):
    """A call taking place in the meeting planned by an activity is logged on that
    activity, so that it shows up in the chatter of the document holding it."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.organizer = new_test_user(
            cls.env, "test_meeting_organizer", tz="UTC",
            groups="base.group_user,base.group_partner_manager",
        )
        cls.env = cls.env(user=cls.organizer)
        cls.customer = cls.env["res.partner"].create({"name": "Test Customer"})

    def _create_meeting(self, start, activities=None, name="Test Meeting", notes=None):
        return self.env["calendar.event"].create({
            "name": name,
            "notes": notes,
            "partner_ids": [(4, self.organizer.partner_id.id)],
            "start": start,
            "stop": start + timedelta(hours=1),
            "videocall_location": self.env["calendar.event"].get_discuss_videocall_location(),
            "meeting_activity_ids": [(6, 0, activities.ids if activities else [])],
        })

    def _start_call(self, channel, start_dt):
        return self.env["discuss.call.history"].sudo().create({
            "channel_id": channel.id,
            "start_dt": start_dt,
        })

    def test_call_is_logged_on_the_activity_that_planned_the_meeting(self):
        activity = self.customer.activity_schedule("mail.mail_activity_data_meeting")
        meeting = self._create_meeting(datetime(2026, 8, 14, 11, 0), activities=activity)
        call_history = self._start_call(meeting.videocall_channel_id, datetime(2026, 8, 14, 11, 5))

        call_history._link_to_activity()

        self.assertEqual(call_history.activity_id, activity)
        self.assertEqual(call_history.activity_res_model, "res.partner")
        self.assertEqual(call_history.activity_res_id, self.customer.id)

    def test_call_marks_the_activity_done_without_manual_action(self):
        """Linking the call to the activity that planned it is enough to log it in
        the chatter: the user does not have to mark the activity done by hand."""
        activity = self.customer.activity_schedule("mail.mail_activity_data_meeting")
        meeting = self._create_meeting(datetime(2026, 8, 14, 11, 0), activities=activity)
        call_history = self._start_call(meeting.videocall_channel_id, datetime(2026, 8, 14, 11, 5))
        call_history.end_dt = datetime(2026, 8, 14, 11, 22, 30)

        call_history._link_to_activity()

        self.assertFalse(activity.active)
        message = self.customer.message_ids[0]
        self.assertEqual(message.date, call_history.start_dt)

    def test_call_is_logged_on_the_occurrence_it_takes_place_in(self):
        """Occurrences of a recurrence share a single channel: the call belongs to the
        occurrence it overlaps with."""
        first_activity = self.customer.activity_schedule("mail.mail_activity_data_meeting")
        second_activity = self.customer.activity_schedule("mail.mail_activity_data_meeting")
        first_meeting = self._create_meeting(datetime(2026, 8, 14, 9, 0), activities=first_activity)
        second_meeting = self._create_meeting(datetime(2026, 8, 14, 14, 0), activities=second_activity)
        first_meeting.videocall_channel_id = second_meeting.videocall_channel_id
        call_history = self._start_call(first_meeting.videocall_channel_id, datetime(2026, 8, 14, 14, 5))
        call_history.end_dt = datetime(2026, 8, 14, 14, 30)

        call_history._link_to_activity()

        self.assertEqual(call_history.activity_id, second_activity)

    def test_meeting_call_message_does_not_repeat_the_attendee_list(self):
        """The call label and the meeting summary are the whole activity title: the attendee
        list shown when a meeting is merely scheduled is not repeated next to them."""
        activity = self.customer.activity_schedule("mail.mail_activity_data_meeting")
        meeting = self._create_meeting(datetime(2026, 8, 14, 11, 0), activities=activity)
        call_history = self._start_call(meeting.videocall_channel_id, datetime(2026, 8, 14, 11, 5))
        call_history.end_dt = datetime(2026, 8, 14, 12, 28, 45)

        call_history._link_to_activity()

        body = html.fromstring(self.customer.message_ids[0].body)
        title = body.find_class("o_mail_activity_title")[0]
        self.assertEqual(
            " ".join(title.text_content().split()), "Meeting done (1h 23m 45s) - Test Meeting",
        )

    def test_meeting_call_message_shows_the_meeting_summary_and_notes(self):
        """The summary and the notes of the meeting are what its attendees wrote down about
        it: the message logging the call carries both."""
        activity = self.customer.activity_schedule("mail.mail_activity_data_meeting")
        meeting = self._create_meeting(
            datetime(2026, 8, 14, 11, 0), activities=activity,
            name="Office Design and Architecture", notes="<p>Bring the mockups</p>",
        )
        call_history = self._start_call(meeting.videocall_channel_id, datetime(2026, 8, 14, 11, 5))
        call_history.end_dt = datetime(2026, 8, 14, 11, 5, 6)

        call_history._link_to_activity()

        body = html.fromstring(self.customer.message_ids[0].body)
        title = body.find_class("o_mail_activity_title")[0]
        self.assertEqual(
            " ".join(title.text_content().split()),
            "Meeting done (6s) - Office Design and Architecture",
        )
        note = body.find_class("o_mail_activity_note")[0]
        self.assertEqual(note.text_content().strip(), "Bring the mockups")

    def test_meeting_call_message_shows_the_activity_summary(self):
        """A summary entered when logging an ad-hoc call, which no meeting was scheduled
        for, is shown next to the call label just like a meeting's own summary."""
        channel = self.env["discuss.channel"].create({"name": "Ad hoc", "channel_type": "group"})
        call_history = self._start_call(channel, datetime(2026, 8, 14, 11, 5))
        call_history.end_dt = datetime(2026, 8, 14, 11, 22, 30)
        activity = self.customer.activity_schedule(
            "mail.mail_activity_data_meeting", summary="Discuss the proposal",
        )
        call_history.activity_id = activity

        activity.action_done()

        body = html.fromstring(self.customer.message_ids[0].body)
        title = body.find_class("o_mail_activity_title")[0]
        self.assertEqual(
            " ".join(title.text_content().split()), "Meeting done (17m 30s) - Discuss the proposal",
        )

    def test_log_contact_defaults_to_the_organizer(self):
        meeting = self._create_meeting(datetime(2026, 8, 14, 11, 0))
        call_history = self._start_call(meeting.videocall_channel_id, datetime(2026, 8, 14, 11, 5))

        action = call_history.action_log_meeting()

        self.assertEqual(action["context"]["log_contact_id"], self.organizer.partner_id.id)

    def test_log_meeting_only_offers_meeting_activity_types(self):
        """The activity this call gets logged on is about the meeting that took place: only
        offer activity types meant for that, not e.g. a phone call or a to-do."""
        meeting = self._create_meeting(datetime(2026, 8, 14, 11, 0))
        call_history = self._start_call(meeting.videocall_channel_id, datetime(2026, 8, 14, 11, 5))

        action = call_history.action_log_meeting()

        wizard = self.env["mail.activity.schedule"].with_context(action["context"]).new()
        offered_types = self.env["mail.activity.type"].search(literal_eval(wizard.activity_type_id_domain))
        self.assertIn(self.env.ref("mail.mail_activity_data_meeting"), offered_types)
        self.assertNotIn(self.env.ref("mail.mail_activity_data_todo"), offered_types)

    def test_ad_hoc_call_stays_unlogged(self):
        channel = self.env["discuss.channel"].create({"name": "Ad hoc", "channel_type": "group"})
        call_history = self._start_call(channel, datetime(2026, 8, 14, 11, 5))

        call_history._link_to_activity()

        self.assertFalse(call_history.activity_id)
