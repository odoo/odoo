from odoo.addons.event_crm.tests.common import TestEventCrmCommon
from odoo.fields import Command
from odoo.tests import HttpCase, tagged


@tagged('post_install', '-at_install')
class TestEventCrmHttp(TestEventCrmCommon, HttpCase):

    def test_event_question_answers_lead_creation(self):
        """ Test that a rule has been created for a question.answer by clicking on the "Add rules" button
        next to it and that a lead is generated when this is selected by a new registration. """
        question = self.env["event.question"].create({
            "title": "Question test",
            "event_ids": [Command.link(self.event_0.id)],
        })
        answer = self.env["event.question.answer"].create({
            "name": "Answer test",
            "question_id": question.id,
        })
        self.start_tour("/odoo", "event_question_answers_rule_creation_tour", login="admin")
        # Check that a rule has been created for the answer.
        self.assertEqual(
            len(self.env["event.lead.rule"].search([("name", "=", "event_question_answer_rule")])),
            1
        )

        self.env["event.registration"].create({
            "event_id": self.event_0.id,
            "email": "event_question_answer_email@odoo.com",
            "registration_answer_ids": [Command.create({
                "question_id": question.id,
                "value_answer_id": answer.id,
            })],
        })
        # Check that the rule generate a lead when the answer is selected by a new registration.
        self.assertEqual(
            len(self.env["crm.lead"].search([("email_normalized", "=", "event_question_answer_email@odoo.com")])),
            1
        )
