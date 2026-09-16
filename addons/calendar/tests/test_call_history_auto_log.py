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

    def test_log_on_planning_activity(self):
        """The call reaches the document through the activity that planned the meeting."""
        activity = self.customer.activity_schedule("mail.mail_activity_data_meeting")
        meeting = self._create_meeting(datetime(2026, 8, 14, 11, 0), activities=activity)
        call_history = self._start_call(meeting.videocall_channel_id, datetime(2026, 8, 14, 11, 5))
        call_history._link_and_complete_activity()
        self.assertEqual(call_history.activity_id, activity)
        self.assertEqual(call_history.activity_res_model, "res.partner")
        self.assertEqual(call_history.activity_res_id, self.customer.id)

    def test_log_on_late_linked_document(self):
        """A meeting linked to a document only after it was created has no activity to log
        the call on: it gets one, so that the call still reaches that document."""
        meeting = self._create_meeting(datetime(2026, 8, 14, 11, 0))
        meeting.res_record = self.customer
        call_history = self._start_call(meeting.videocall_channel_id, datetime(2026, 8, 14, 11, 5))
        call_history.end_dt = datetime(2026, 8, 14, 11, 5, 6)
        call_history._link_and_complete_activity()
        self.assertEqual(call_history.activity_res_model, "res.partner")
        self.assertEqual(call_history.activity_res_id, self.customer.id)
        self.assertEqual(call_history.activity_id.calendar_event_id, meeting)
        self.assertIn("Meeting done (6s)", self.customer.message_ids[0].body)

    def test_unlinked_meeting_stays_unlogged(self):
        """A meeting held for its own sake has no document to log its call on."""
        meeting = self._create_meeting(datetime(2026, 8, 14, 11, 0))
        call_history = self._start_call(meeting.videocall_channel_id, datetime(2026, 8, 14, 11, 5))
        call_history._link_and_complete_activity()
        self.assertFalse(call_history.activity_id)

    def test_activity_done_without_manual_action(self):
        """Linking the call to the activity that planned it is enough to log it in
        the chatter: the user does not have to mark the activity done by hand."""
        activity = self.customer.activity_schedule("mail.mail_activity_data_meeting")
        meeting = self._create_meeting(datetime(2026, 8, 14, 11, 0), activities=activity)
        call_history = self._start_call(meeting.videocall_channel_id, datetime(2026, 8, 14, 11, 5))
        call_history.end_dt = datetime(2026, 8, 14, 11, 22, 30)
        call_history._link_and_complete_activity()
        self.assertFalse(activity.active)
        message = self.customer.message_ids[0]
        self.assertEqual(message.date, call_history.start_dt)

    def test_logged_by_assignee(self):
        """A call ends when its last attendee leaves, who may well be an external one:
        the message logging it reads as posted by whoever the activity was assigned to,
        so that it does not depend on the order the attendees happened to leave in."""
        attendee = new_test_user(self.env, "test_last_to_leave", tz="UTC")
        activity = self.customer.activity_schedule("mail.mail_activity_data_meeting")
        self.assertEqual(activity.user_id, self.organizer, "assigned to the organizer")
        meeting = self._create_meeting(datetime(2026, 8, 14, 11, 0), activities=activity)
        call_history = self._start_call(meeting.videocall_channel_id, datetime(2026, 8, 14, 11, 5))
        # the call ends in the session of the attendee leaving it last (see
        # `discuss.channel.rtc.session.unlink`)
        call_history.with_user(attendee).sudo()._link_and_complete_activity()
        message = self.customer.message_ids[0]
        self.assertEqual(message.author_id, self.organizer.partner_id)
        self.assertNotIn(
            "originally assigned to", message.body,
            "the assignee logged it themselves: nothing to say about who did",
        )

    def test_log_on_overlapping_occurrence(self):
        """Occurrences of a recurrence share a single channel: the call belongs to the
        occurrence it overlaps with."""
        first_activity = self.customer.activity_schedule("mail.mail_activity_data_meeting")
        second_activity = self.customer.activity_schedule("mail.mail_activity_data_meeting")
        first_meeting = self._create_meeting(datetime(2026, 8, 14, 9, 0), activities=first_activity)
        second_meeting = self._create_meeting(datetime(2026, 8, 14, 14, 0), activities=second_activity)
        first_meeting.videocall_channel_id = second_meeting.videocall_channel_id
        call_history = self._start_call(first_meeting.videocall_channel_id, datetime(2026, 8, 14, 14, 5))
        call_history.end_dt = datetime(2026, 8, 14, 14, 30)
        call_history._link_and_complete_activity()
        self.assertEqual(call_history.activity_id, second_activity)

    def test_message_without_attendee_list(self):
        """The call label and the meeting summary are the whole activity title: the attendee
        list shown when a meeting is merely scheduled is not repeated next to them."""
        activity = self.customer.activity_schedule("mail.mail_activity_data_meeting")
        meeting = self._create_meeting(datetime(2026, 8, 14, 11, 0), activities=activity)
        call_history = self._start_call(meeting.videocall_channel_id, datetime(2026, 8, 14, 11, 5))
        call_history.end_dt = datetime(2026, 8, 14, 12, 28, 45)
        call_history._link_and_complete_activity()
        body = html.fromstring(self.customer.message_ids[0].body)
        title = body.find_class("o_mail_activity_title")[0]
        self.assertEqual(
            " ".join(title.text_content().split()), "Meeting done (1h 23m 45s) - Test Meeting",
        )

    def test_message_with_summary_without_notes(self):
        """The summary of a meeting says what it was about: the message logging its call
        carries it. Its notes, where video call providers write down how to connect, stay
        out of the chatter."""
        activity = self.customer.activity_schedule("mail.mail_activity_data_meeting")
        meeting = self._create_meeting(
            datetime(2026, 8, 14, 11, 0), activities=activity,
            name="Office Design and Architecture", notes="<p>Bring the mockups</p>",
        )
        call_history = self._start_call(meeting.videocall_channel_id, datetime(2026, 8, 14, 11, 5))
        call_history.end_dt = datetime(2026, 8, 14, 11, 5, 6)
        call_history._link_and_complete_activity()
        body = html.fromstring(self.customer.message_ids[0].body)
        title = body.find_class("o_mail_activity_title")[0]
        self.assertEqual(
            " ".join(title.text_content().split()),
            "Meeting done (6s) - Office Design and Architecture",
        )
        self.assertNotIn("Bring the mockups", body.text_content())

    def test_message_with_activity_summary(self):
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
        attendee = new_test_user(self.env, "test_meeting_attendee", tz="UTC")
        meeting = self._create_meeting(datetime(2026, 8, 14, 11, 0))
        call_history = self._start_call(meeting.videocall_channel_id, datetime(2026, 8, 14, 11, 5))
        action = call_history.with_user(attendee).action_log_meeting()
        self.assertEqual(action["context"]["log_contact_id"], self.organizer.partner_id.id)

    def test_log_contact_excludes_self(self):
        """An organizer logging their own meeting knows they were in it: the call is
        about who they met, not about themselves."""
        meeting = self._create_meeting(datetime(2026, 8, 14, 11, 0))
        call_history = self._start_call(meeting.videocall_channel_id, datetime(2026, 8, 14, 11, 5))
        action = call_history.action_log_meeting()
        self.assertFalse(action["context"]["log_contact_id"])

    def test_log_meeting_contact_domain_unfiltered(self):
        """A meeting call is logged for its organizer, whose own records would be a poor
        list: rank the attendees' first instead (see `discuss.call.log.mixin.name_search`),
        dropping none."""
        meeting = self._create_meeting(datetime(2026, 8, 14, 11, 0))
        call_history = self._start_call(meeting.videocall_channel_id, datetime(2026, 8, 14, 11, 5))
        action = call_history.action_log_meeting()
        wizard = self.env["mail.activity.schedule.call"].with_context(action["context"]).new()
        self.assertEqual(literal_eval(wizard.contact_id_domain), [])

    def test_log_meeting_activity_types(self):
        """The activity this call gets logged on is about the meeting that took place: only
        list activity types meant for that, not e.g. a phone call or a to-do."""
        meeting = self._create_meeting(datetime(2026, 8, 14, 11, 0))
        call_history = self._start_call(meeting.videocall_channel_id, datetime(2026, 8, 14, 11, 5))
        action = call_history.action_log_meeting()
        wizard = self.env["mail.activity.schedule.call"].with_context(action["context"]).new()
        listed_types = self.env["mail.activity.type"].search(literal_eval(wizard.activity_type_id_domain))
        self.assertIn(self.env.ref("mail.mail_activity_data_meeting"), listed_types)
        self.assertNotIn(self.env.ref("mail.mail_activity_data_todo"), listed_types)

    def test_ad_hoc_call_stays_unlogged(self):
        channel = self.env["discuss.channel"].create({"name": "Ad hoc", "channel_type": "group"})
        call_history = self._start_call(channel, datetime(2026, 8, 14, 11, 5))
        call_history._link_and_complete_activity()
        self.assertFalse(call_history.activity_id)
