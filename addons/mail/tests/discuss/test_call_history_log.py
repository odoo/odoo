# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo import fields
from odoo.tests import Form, tagged

from odoo.addons.mail.tests.common import mail_new_test_user, MailCommon


@tagged("post_install", "-at_install")
class TestCallHistoryLog(MailCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.channel = cls.env["discuss.channel"].create({
            "name": "Test Channel",
            "channel_type": "group",
        })
        cls.call_history = cls.env["discuss.call.history"].create({
            "channel_id": cls.channel.id,
            "start_dt": fields.Datetime.to_datetime("2026-08-14 11:16:00"),
            "end_dt": fields.Datetime.to_datetime("2026-08-14 12:39:45"),
        })

    def _log_call_on_a_new_partner(self):
        """Mark done an activity logging the call, as ending the call does, and return
        the message it posted in the chatter."""
        partner = self.env["res.partner"].create({"name": "Test Partner"})
        activity = partner.activity_schedule("mail.mail_activity_data_meeting")
        self.call_history.activity_id = activity
        activity.action_done()
        return partner.message_ids[0]

    def _make_the_recording_available(self):
        """Upload the recording of the call, as its callback does once the call is over."""
        artifact = self.env["mail.call.artifact"].create({
            "discuss_call_history_id": self.call_history.id,
            "start_ms": 0,
            "end_ms": 1_000,
            "recording_upload_pending": True,
        })
        self.env["ir.attachment"].create({
            "mimetype": "audio/webm",
            "name": "recording.webm",
            "raw": b"recording",
            "res_id": artifact.id,
            "res_model": artifact._name,
        })
        artifact.invalidate_recordset(["media_id"])
        artifact.recording_upload_pending = False
        self.call_history._broadcast_recording_availability()

    def _pushed_message_updates(self, message):
        """The payloads of the bus notifications sent so far for ``message``."""
        self.env.cr.precommit.run()  # bus.bus records are created on precommit
        return [
            payload
            for notification in self.env["bus.bus"].sudo().search([])
            for payload in json.loads(notification.message)["payload"].get("mail.message", [])
            if payload["id"] == message.id
        ]

    def test_duration_human_readable(self):
        self.assertEqual(self.call_history.duration_human_readable, "1h 23m 45s")
        self.assertEqual(self.call_history.activity_done_label, "Meeting done (1h 23m 45s)")

    def test_logged_call_keeps_its_message(self):
        """The message logging the call is kept, so that the artifacts it announces can
        be added to it once they land."""
        message = self._log_call_on_a_new_partner()
        self.assertEqual(self.call_history.activity_done_message_id, message)

    def test_recording_after_log(self):
        """The recording lands after the message logging the call was rendered: that
        message gets the recording icon all the same."""
        message = self._log_call_on_a_new_partner()
        self.assertNotIn("Recording available", message.body, "no recording yet")
        self._make_the_recording_available()
        self.assertIn("Recording available", message.body)
        self.assertIn("Meeting done (1h 23m 45s)", message.body, "the call label is kept")

    def test_recording_after_log_is_pushed(self):
        """The chatter is likely open when the recording lands, the meeting having just
        taken place: the new body reaches it over the bus, not on the next reload."""
        message = self._log_call_on_a_new_partner()
        self._reset_bus()
        self._make_the_recording_available()
        pushed = self._pushed_message_updates(message)
        self.assertEqual(len(pushed), 1, "the updated body is pushed once")
        self.assertIn("Recording available", message.body)
        self.assertEqual(pushed[0]["body"], ["markup", message.body])

    def test_recording_before_log(self):
        """The other order: the recording is already there when the call gets logged."""
        self._make_the_recording_available()
        message = self._log_call_on_a_new_partner()
        self.assertIn("Recording available", message.body)

    def test_recording_of_unlogged_call(self):
        """A call nobody logged has no chatter message to add its recording to."""
        self._make_the_recording_available()
        self.assertFalse(self.call_history.activity_done_message_id)

    def test_ongoing_call_logged_then_ended(self):
        """Logging an ongoing call only schedules its activity (see `is_call_ongoing`):
        the call ending is what marks it done and posts it, through the RTC session
        leaving rather than through `_link_and_complete_activity` by hand."""
        partner = self.env["res.partner"].create({"name": "Test Partner"})
        channel = self.env["discuss.channel"].create({
            "name": "Ongoing Call",
            "channel_type": "group",
        })
        member = channel.self_member_id
        member._rtc_join_call()
        call_history = self.env["discuss.call.history"].search(
            [("channel_id", "=", channel.id)],
        )
        form = Form.from_action(self.env, call_history.action_log_meeting())
        form.contact_id = partner
        activity = form.save()._action_schedule_activities()
        self.assertEqual(call_history.activity_id, activity)
        self.assertFalse(activity.date_done, "the call is still going on")
        member._rtc_leave_call()
        self.assertTrue(activity.date_done, "the call ended: its activity is done")
        self.assertIn("Meeting done", partner.message_ids[0].body)

    def test_unknown_caller_contact(self):
        """A call placed to a number no contact holds is about nobody: the wizard leaves
        its contact empty rather than pre-selecting a stranger, which Mark Done would
        then persist as the contact the call was with."""
        self.env["res.partner"].create({"name": "AAA Unrelated Contact"})
        wizard = self.env["mail.activity.schedule.call"].with_context(
            default_res_model_selection="res.partner", log_contact_id=False,
        ).new()
        self.assertFalse(wizard.contact_id)

    def test_log_meeting_on_contact(self):
        """Logging a call on a contact links the call to the activity created on it."""
        partner = self.env["res.partner"].create({"name": "Test Partner"})
        form = Form.from_action(self.env, self.call_history.action_log_meeting())
        form.contact_id = partner
        self.assertEqual(form.res_model_selection, "res.partner")
        self.assertEqual(form.res_ids, f"[{partner.id}]")
        wizard = form.save()
        activity = wizard._action_schedule_activities()
        self.assertEqual(activity.res_model, "res.partner")
        self.assertEqual(activity.res_id, partner.id)
        self.assertEqual(self.call_history.activity_id, activity)
        self.assertEqual(self.call_history.activity_res_id, partner.id)

    def test_log_meeting_message_link(self):
        """Marking the activity done posts the call label, linked to the call history."""
        partner = self.env["res.partner"].create({"name": "Test Partner"})
        activity = partner.activity_schedule("mail.mail_activity_data_meeting")
        self.call_history.activity_id = activity
        activity.action_done()
        message = partner.message_ids[0]
        self.assertIn("Meeting done (1h 23m 45s)", message.body)
        self.assertIn(f'data-oe-model="discuss.call.history" data-oe-id="{self.call_history.id}"', message.body)

    def test_log_channel_partners_exclude_self(self):
        """The user logging the call knows they attended it: the records ranked first
        are the ones about whoever else was there."""
        attendee = self.env["res.partner"].create({"name": "Test Attendee"})
        self.channel._add_members(partners=self.env.user.partner_id | attendee)
        context = self.call_history.action_log_meeting()["context"]
        self.assertEqual(context["log_channel_partner_ids"], attendee.ids)

    def test_default_contact_excludes_self(self):
        """The wizard never fills its contact in with the user logging the call, even
        when no record is closer to it."""
        user = mail_new_test_user(self.env, login="test_call_logger", name="AAAA Myself")
        someone_else = self.env["res.partner"].create({"name": "AAAB Someone Else"})
        self.channel._add_members(users=user)
        env = self.env(user=user)
        form = Form.from_action(env, self.call_history.with_env(env).action_log_meeting())
        self.assertEqual(form.contact_id, someone_else)

    def test_rank_attendee_tier_first(self):
        """Whoever was in the call is who the document being logged on is expected to be
        about: their records come before any other the wizard allows."""
        attendee = self.env["res.partner"].create({"name": "AAA Call Attendee"})
        other = self.env["res.partner"].create({"name": "AAA Other Contact"})
        self.channel._add_members(partners=attendee)
        domain = [("id", "in", (attendee | other).ids)]
        # ordered by name, the attendee comes first here only by chance
        self.assertEqual(
            [id_ for id_, _name in self.env["res.partner"].name_search("AAA", domain)],
            (attendee | other).ids,
        )
        # ordered by name, the attendee would come last: it is ranked first nonetheless
        other.name = "AAA A Other Contact"
        context = self.call_history.action_log_meeting()["context"]
        ranked = self.env["res.partner"].with_context(**context).name_search("AAA", domain)
        self.assertEqual([id_ for id_, _name in ranked], (attendee | other).ids)

    def test_rank_commercial_tiers_next(self):
        """After the attendees come the tiers of their commercial entity: the companies
        they work for first, then the other contacts of those companies."""
        company = self.env["res.partner"].create({"name": "AAA Company", "is_company": True})
        attendee, colleague = self.env["res.partner"].create([
            {"name": "AAA Attendee", "parent_id": company.id},
            {"name": "AAA Colleague", "parent_id": company.id},
        ])
        outsider = self.env["res.partner"].create({"name": "AAA Outsider"})
        self.channel._add_members(partners=attendee)
        everyone = company | attendee | colleague | outsider
        domain = [("id", "in", everyone.ids)]
        # left to its own order, the model lists the company before whoever attended
        self.assertEqual(
            [id_ for id_, _name in self.env["res.partner"].name_search("AAA", domain)],
            (company | attendee | colleague | outsider).ids,
        )
        context = self.call_history.action_log_meeting()["context"]
        ranked = self.env["res.partner"].with_context(**context).name_search("AAA", domain)
        self.assertEqual(
            [id_ for id_, _name in ranked], (attendee | company | colleague | outsider).ids,
        )

    def test_rank_keeps_untiered_contacts(self):
        """A contact the call has nothing to do with is still one the user may log it
        on: ranking pushes it down the list, it never filters it out."""
        attendee = self.env["res.partner"].create({"name": "ZZZ Call Attendee"})
        self.channel._add_members(partners=attendee)
        context = self.call_history.action_log_meeting()["context"]
        ranked = self.env["res.partner"].with_context(**context).name_search()
        self.assertEqual(ranked[0][0], attendee.id)
        self.assertEqual(len(ranked), len(self.env["res.partner"].name_search()))
