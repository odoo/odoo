# Part of Odoo. See LICENSE file for full copyright and licensing details.

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

    def test_log_channel_partners_exclude_the_user_logging_the_call(self):
        """The user logging the call knows they attended it: the records offered to them
        are the ones about whoever else was there."""
        attendee = self.env["res.partner"].create({"name": "Test Attendee"})
        self.channel._add_members(partners=self.env.user.partner_id | attendee)

        context = self.call_history.action_log_meeting()["context"]

        self.assertEqual(context["log_channel_partner_ids"], attendee.ids)

    def test_log_meeting_never_defaults_to_the_contact_of_the_user_logging_it(self):
        """The wizard never fills its contact in with the user logging the call, even
        when no record is closer to it."""
        user = mail_new_test_user(self.env, login="test_call_logger", name="AAAA Myself")
        someone_else = self.env["res.partner"].create({"name": "AAAB Someone Else"})
        self.channel._add_members(users=user)
        env = self.env(user=user)

        form = Form.from_action(env, self.call_history.with_env(env).action_log_meeting())

        self.assertEqual(form.contact_id, someone_else)

    def test_log_meeting_offers_the_contacts_of_the_call_first(self):
        """Whoever was in the call is who the document being logged on is expected to be
        about: offer their records before any other the wizard allows."""
        attendee = self.env["res.partner"].create({"name": "AAA Call Attendee"})
        other = self.env["res.partner"].create({"name": "AAA Other Contact"})
        self.channel._add_members(partners=attendee)
        domain = [("id", "in", (attendee | other).ids)]

        # ordered by name, the attendee comes first here only by chance
        self.assertEqual(
            [id_ for id_, _name in self.env["res.partner"].name_search("AAA", domain)],
            (attendee | other).ids,
        )
        # ordered by name, the attendee would come last: it is offered first nonetheless
        other.name = "AAA A Other Contact"
        context = self.call_history.action_log_meeting()["context"]
        offered = self.env["res.partner"].with_context(**context).name_search("AAA", domain)
        self.assertEqual([id_ for id_, _name in offered], (attendee | other).ids)

    def test_log_meeting_offers_the_family_of_the_contacts_next(self):
        """After the records of whoever attended the call come those of their family:
        the companies they work for first, then their colleagues there."""
        company = self.env["res.partner"].create({"name": "AAA Company", "is_company": True})
        attendee, colleague = self.env["res.partner"].create([
            {"name": "AAA Attendee", "parent_id": company.id},
            {"name": "AAA Colleague", "parent_id": company.id},
        ])
        outsider = self.env["res.partner"].create({"name": "AAA Outsider"})
        self.channel._add_members(partners=attendee)
        everyone = company | attendee | colleague | outsider
        domain = [("id", "in", everyone.ids)]
        # left to its own order, the model offers the company before whoever attended
        self.assertEqual(
            [id_ for id_, _name in self.env["res.partner"].name_search("AAA", domain)],
            (company | attendee | colleague | outsider).ids,
        )
        context = self.call_history.action_log_meeting()["context"]

        offered = self.env["res.partner"].with_context(**context).name_search("AAA", domain)

        self.assertEqual(
            [id_ for id_, _name in offered], (attendee | company | colleague | outsider).ids,
        )

    def test_log_meeting_offers_every_record_the_wizard_allows(self):
        """Records unrelated to the call are pushed down the list, never dropped from it."""
        attendee = self.env["res.partner"].create({"name": "ZZZ Call Attendee"})
        self.channel._add_members(partners=attendee)
        context = self.call_history.action_log_meeting()["context"]

        offered = self.env["res.partner"].with_context(**context).name_search()

        self.assertEqual(offered[0][0], attendee.id)
        self.assertEqual(len(offered), len(self.env["res.partner"].name_search()))
