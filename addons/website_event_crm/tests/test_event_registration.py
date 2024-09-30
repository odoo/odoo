# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.event_crm.tests.common import TestEventCrmCommon
from odoo.tests.common import tagged, users


@tagged('event_crm', 'post_install', '-at_install')
class EventRegistrationCase(TestEventCrmCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.event_0.write({
            "question_ids": [
                (0, 0, {
                'title': 'Text Input Question',
                'question_type': 'text_box',
                }),
            ],
        })
        # add sales rights to event manager, to enable lead check
        cls.user_eventmanager.write({
            'groups_id': [(4, cls.env.ref('sales_team.group_sale_salesman').id)],
        })

        cls.test_lang_website = cls.env['website'].sudo().create({
            'name': 'test lang website',
            'user_id': cls.env.ref('base.user_admin').id,
            'language_ids': [cls.env.ref('base.lang_en').id, cls.env.ref('base.lang_fr').id]
        })
        cls.test_lang_visitor = cls.env['website.visitor'].sudo().create({
            'name': 'test visitor language',
            'lang_id': cls.env.ref('base.lang_en').id,
            'access_token': 'f9d2ffa0427d4e4b1d740cf5eb3cdc20',
            'website_id': cls.test_lang_website.id,
        })

    @users('user_eventregistrationdesk')
    def test_event_registration_lead_description(self):
        """ Ensure that the lead description is well formatted/escaped
        when created from an event registration. """
        self.env.invalidate_all()

        # registration desk user: limited rights
        test_rule_attendee = self.test_rule_attendee.with_user(self.env.user)
        test_rule_order = self.test_rule_order.with_user(self.env.user)
        # manager with sales rights
        test_rule_attendee_manager = self.test_rule_attendee.with_user(self.user_eventmanager)
        test_rule_order_manager = self.test_rule_order.with_user(self.user_eventmanager)

        # have some registration values holding answers, to check their presence
        # in lead description
        registration_values = [
            dict(
                customer_data,
                event_id=self.event_0.id,
                registration_answer_ids=[(0, 0, {
                    'question_id': self.event_0.question_ids[0].id,
                    'value_text_box': f"<div>answer from {customer_data.get('name', 'no_name')}</div>",
                })],
            )
            for customer_data in self.batch_customer_data
        ]

        self.assertEqual(len(test_rule_attendee_manager.lead_ids), 0)
        self.assertEqual(len(test_rule_order_manager.lead_ids), 0)

        registrations = self.env['event.registration'].create(registration_values)
        registrations = registrations.sorted('id')
        self.assertEqual(len(registrations), 5)
        self.assertEqual(len(test_rule_attendee.lead_ids), 5)
        self.assertEqual(len(test_rule_order.lead_ids), 1)

        # grouped description: all answers in lead
        order_lead = test_rule_order.lead_ids
        for customer_data in self.batch_customer_data:
            self.assertIn(
                f'&lt;div&gt;answer from {customer_data.get("name", "no_name")}&lt;/div&gt;',
                order_lead.description,
                "Answers should be escaped")
            self.assertIn('<li>', order_lead.description, 'HTML around the text box value should not be escaped')

        # attendee-based descriptions
        attendee_leads = test_rule_attendee.lead_ids
        for lead, registration, customer_data in zip(attendee_leads, registrations, self.batch_customer_data):
            self.assertEqual(lead.registration_ids, registration)
            self.assertEqual(registration.lead_ids, lead + order_lead)
            self.assertIn(
                f'&lt;div&gt;answer from {customer_data.get("name", "no_name")}&lt;/div&gt;', lead.description,
                "Answers should be escaped")
            self.assertIn('<li>', lead.description, 'HTML around the text box value should not be escaped')

    @users('user_eventregistrationdesk')
    def test_visitor_language_propagation(self):
        """
        This test makes sure that visitor and its language are propagated to the lead when a lead is
        created through a lead generation rule.

        `_run_on_registration`, which creates the lead, is called at `event.registration` creation
        and does not need to be called manually.
        """
        self.env.invalidate_all()

        # 3 leads created w/ Lead Generation rules in TestEventCrmCommon: 1 per attendee and 1 per order
        reg1, reg2 = self.env['event.registration'].create([
            {
                'event_id': self.event_0.id,
                'visitor_id': self.test_lang_visitor.id,
                'email': 'test@test.example.com',
            }, {
                'event_id': self.event_0.id,
                'visitor_id': self.test_lang_visitor.id,
                'email': 'test2@test.example.com',
            },
        ])
        leads = reg1.lead_ids + reg2.lead_ids
        self.assertEqual(leads.visitor_ids, self.test_lang_visitor)
        self.assertEqual(leads.lang_id, self.test_lang_visitor.lang_id)
