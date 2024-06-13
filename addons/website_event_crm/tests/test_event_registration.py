# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.event_crm.tests.common import TestEventCrmCommon


class EventRegistrationCase(TestEventCrmCommon):

    def test_event_registration_lead_description(self):
        """ Ensure that the lead description is well formatted/escaped
        when created from an event registration. """

        questions = self.env['event.question'].create([{
            'title': 'Text Input Question',
            'question_type': 'text_box',
        }])

        self.event_0.write({
            'question_ids': [(4, question.id) for question in questions]
        })

        customer_data = self.batch_customer_data[1]
        customer_data['registration_answer_ids'] = [(0, 0, {
            'question_id': questions[0].id,
            'value_text_box': "<div>hello world</div>",
        })]

        registration_values = dict(self.batch_customer_data[1], event_id=self.event_0.id)
        self.assertEqual(len(self.test_rule_attendee.lead_ids), 0)
        self.env['event.registration'].create(registration_values)
        lead = self.test_rule_attendee.lead_ids
        self.assertEqual(len(self.test_rule_attendee.lead_ids), 1)
        self.assertTrue('&lt;div&gt;hello world&lt;/div&gt;' in lead.description, 'Description should contain the escaped text box value')
        self.assertTrue('<li>' in lead.description, 'HTML around the text box value should not be escaped')
