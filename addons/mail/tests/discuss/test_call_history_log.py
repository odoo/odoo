# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields
from odoo.tests import Form, tagged

from odoo.addons.mail.tests.common import MailCommon


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

    def test_duration_human_readable(self):
        self.assertEqual(self.call_history.duration_human_readable, "1h 23m 45s")
        self.assertEqual(self.call_history.activity_done_label, "Meeting done (1h 23m 45s)")

    def test_action_log_meeting_creates_activity_on_contact(self):
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

    def test_log_meeting_message_links_the_call(self):
        """Marking the activity done posts the call label, linked to the call history."""
        partner = self.env["res.partner"].create({"name": "Test Partner"})
        activity = partner.activity_schedule("mail.mail_activity_data_meeting")
        self.call_history.activity_id = activity
        activity.action_done()
        message = partner.message_ids[0]
        self.assertIn("Meeting done (1h 23m 45s)", message.body)
        self.assertIn(f'data-oe-model="discuss.call.history" data-oe-id="{self.call_history.id}"', message.body)
