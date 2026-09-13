# Part of Odoo. See LICENSE file for full copyright and licensing details.
from ast import literal_eval

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestProjectActivityLog(TransactionCase):
    """The "Log Activity in Chatter" wizard, for the Task record type project contributes."""

    def test_log_call_offers_every_task_the_attendees_ones_first(self):
        """A call held in a channel is about whoever was in it: their tasks are offered
        first, the others after, and the wizard starts on one of theirs."""
        attendee = self.env["res.partner"].create({"name": "Call Attendee"})
        project = self.env["project.project"].create({"name": "Test Project"})
        attendee_task = self.env["project.task"].create({
            "name": "Test Attendee Task", "partner_id": attendee.id, "project_id": project.id,
        })
        other_task = self.env["project.task"].create({
            "name": "Test Other Task", "project_id": project.id,
        })
        # the user logging the call is the one the wizard defaults its contact to
        context = {"log_channel_partner_ids": attendee.ids, "log_contact_id": self.env.user.partner_id.id}
        wizard = self.env["mail.activity.schedule"].with_context(**context).new({
            "res_model_selection": "project.task",
        })

        domain = literal_eval(wizard.task_id_domain)
        offered = [
            id_ for id_, _name in self.env["project.task"].with_context(**context).name_search(domain=domain)
        ]

        self.assertEqual(offered[0], attendee_task.id, "the task of an attendee comes first")
        self.assertIn(other_task.id, offered, "a task about nobody who attended is still offered")
        self.assertEqual(wizard.task_id, attendee_task, "the wizard starts on a task of an attendee")

    def test_log_call_starts_on_the_task_offered_first(self):
        """The wizard fills its field in with the task at the top of its dropdown: what a
        user reads there is what picking the first one offered would have given them."""
        attendee = self.env["res.partner"].create({"name": "Call Attendee"})
        project = self.env["project.project"].create({"name": "Test Project"})
        # the newest task comes last, the model ordering tasks by sequence before id
        first, newest = self.env["project.task"].create([
            {"name": "Test Task", "partner_id": attendee.id, "project_id": project.id, "sequence": 1},
            {"name": "Test Newest Task", "partner_id": attendee.id, "project_id": project.id, "sequence": 10},
        ])
        context = {"log_channel_partner_ids": attendee.ids, "log_contact_id": self.env.user.partner_id.id}
        wizard = self.env["mail.activity.schedule"].with_context(**context).new({
            "res_model_selection": "project.task",
        })

        domain = literal_eval(wizard.task_id_domain)
        offered = self.env["project.task"].with_context(**context).name_search(domain=domain)

        self.assertEqual(offered[0][0], first.id)
        self.assertEqual(wizard.task_id, first, "the task offered first, not the newest one")
        self.assertNotEqual(wizard.task_id, newest)
