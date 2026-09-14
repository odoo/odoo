from datetime import datetime, timedelta

from odoo.tests.common import RecordCapturer, tagged, users

from odoo.addons.event_crm.tests.common import TestEventCrmCommon


@tagged("event_crm", "post_install", "-at_install")
class EventRegistrationCase(TestEventCrmCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.event_0.write(
            {
                "question_ids": [
                    (
                        0,
                        0,
                        {
                            "title": "Text Input Question",
                            "question_type": "text_box",
                        },
                    ),
                ],
            }
        )
        cls.user_eventmanager.write(
            {
                "group_ids": [(4, cls.env.ref("sale.group_sale_salesman").id)],
            }
        )

        cls.test_lang_website = (
            cls.env["website"]
            .sudo()
            .create(
                {
                    "name": "test lang website",
                    "user_id": cls.env.ref("base.user_admin").id,
                    "language_ids": [
                        cls.env.ref("base.lang_en").id,
                        cls.env.ref("base.lang_fr").id,
                    ],
                }
            )
        )
        cls.test_lang_visitor = (
            cls.env["website.visitor"]
            .sudo()
            .create(
                {
                    "name": "test visitor language",
                    "lang_id": cls.env.ref("base.lang_en").id,
                    "access_token": "f9d2ffa0427d4e4b1d740cf5eb3cdc20",
                    "website_id": cls.test_lang_website.id,
                }
            )
        )
        cls.test_lang_visitor_fr = (
            cls.env["website.visitor"]
            .sudo()
            .create(
                {
                    "name": "test visitor language 2",
                    "lang_id": cls.env.ref("base.lang_fr").id,
                    "access_token": "f9d2ffa0427d4e4b1d740cf5eb3cdc21",
                    "website_id": cls.test_lang_website.id,
                }
            )
        )

    @users("user_eventregistrationdesk")
    def test_event_registration_lead_description(self):
        self.env.invalidate_all()

        test_rule_attendee = self.test_rule_attendee.with_user(self.env.user)
        test_rule_order = self.test_rule_order.with_user(self.env.user)
        test_rule_attendee_manager = self.test_rule_attendee.with_user(
            self.user_eventmanager
        )
        test_rule_order_manager = self.test_rule_order.with_user(self.user_eventmanager)

        registration_values = [
            dict(
                customer_data,
                event_id=self.event_0.id,
                registration_answer_ids=[
                    (
                        0,
                        0,
                        {
                            "question_id": self.event_0.question_ids[0].id,
                            "value_text_box": f"<div>answer from {customer_data.get('name', 'no_name')}</div>",
                        },
                    )
                ],
            )
            for customer_data in self.batch_customer_data
        ]

        self.assertEqual(len(test_rule_attendee_manager.lead_ids), 0)
        self.assertEqual(len(test_rule_order_manager.lead_ids), 0)

        registrations = self.env["event.registration"].create(registration_values)
        registrations = registrations.sorted("id")
        self.assertEqual(len(registrations), 5)
        self.assertEqual(len(test_rule_attendee.sudo().lead_ids), 5)
        self.assertEqual(len(test_rule_order.sudo().lead_ids), 1)

        order_lead = test_rule_order.sudo().lead_ids
        for customer_data in self.batch_customer_data:
            self.assertIn(
                f"&lt;div&gt;answer from {customer_data.get('name', 'no_name')}&lt;/div&gt;",
                order_lead.description,
                "Answers should be escaped",
            )
            self.assertIn(
                "<li>",
                order_lead.description,
                "HTML around the text box value should not be escaped",
            )

        attendee_leads = test_rule_attendee.sudo().lead_ids
        for registration, customer_data in zip(
            registrations, self.batch_customer_data, strict=True
        ):
            lead = attendee_leads.filtered(
                lambda l, registration=registration: l.registration_ids == registration
            )
            self.assertTrue(lead)
            self.assertEqual(lead.registration_ids, registration)
            self.assertEqual(registration.sudo().lead_ids, lead + order_lead)
            self.assertIn(
                f"&lt;div&gt;answer from {customer_data.get('name', 'no_name')}&lt;/div&gt;",
                lead.description,
                "Answers should be escaped",
            )
            self.assertIn(
                "<li>",
                lead.description,
                "HTML around the text box value should not be escaped",
            )

    def test_event_registration_generation_from_existing(self):
        now = datetime(2024, 10, 1, 13, 30, 0)
        with RecordCapturer(self.env["crm.lead"]) as capture:
            Attendee = (
                self.env["event.registration"]
                .with_context(event_lead_rule_skip=True)
                .with_user(self.user_eventmanager)
            )
            with self.mock_datetime_and_now(now):
                attendees_1 = Attendee.create(
                    [
                        {
                            "email": "test@test.example.com",
                            "event_id": self.event_0.id,
                            "visitor_id": self.test_lang_visitor.id,
                        },
                        {
                            "email": "test2@test.example.com",
                            "event_id": self.event_0.id,
                            "visitor_id": self.test_lang_visitor.id,
                        },
                    ]
                )
            with self.mock_datetime_and_now(now + timedelta(hours=1)):
                attendees_2 = Attendee.create(
                    [
                        {
                            "email": "test.fr.later@test.example.com",
                            "event_id": self.event_0.id,
                            "visitor_id": self.test_lang_visitor_fr.id,
                        },
                        {
                            "email": "test.fr.later.2@test.example.com",
                            "event_id": self.event_0.id,
                            "visitor_id": self.test_lang_visitor_fr.id,
                        },
                    ]
                )

        self.assertFalse(len(capture.records), 4)

        test_rule_order = self.test_rule_order.with_user(self.user_eventmanager)
        leads = test_rule_order.sudo()._run_on_registrations(attendees_1 + attendees_2)
        self.assertEqual(
            len(leads),
            2,
            "Should have created one lead / batch (event + create_date key)",
        )
        self.assertEqual(leads[0].registration_ids, attendees_1)
        self.assertEqual(leads[1].registration_ids, attendees_2)

    def test_visitor_language_propagation(self):
        self.env.invalidate_all()

        with RecordCapturer(self.env["crm.lead"]) as capture:
            _attendees = (
                self.env["event.registration"]
                .with_user(self.user_eventmanager)
                .create(
                    [
                        {
                            "event_id": self.event_0.id,
                            "visitor_id": self.test_lang_visitor.id,
                            "email": "test@test.example.com",
                        },
                        {
                            "event_id": self.event_0.id,
                            "visitor_id": self.test_lang_visitor.id,
                            "email": "test2@test.example.com",
                        },
                        {
                            "event_id": self.event_0.id,
                            "visitor_id": self.test_lang_visitor_fr.id,
                            "email": "test.fr@test.example.com",
                        },
                    ]
                )
            )
        leads = capture.records.sudo()
        self.assertEqual(len(leads), 4)

        global_lead = leads.filtered(
            lambda l: l.event_lead_rule_id == self.test_rule_order
        )
        self.assertEqual(
            global_lead.visitor_ids, self.test_lang_visitor + self.test_lang_visitor_fr
        )
        self.assertEqual(global_lead.lang_id, self.test_lang_visitor.lang_id)

        attendee_lead = leads.filtered(
            lambda l: l.event_lead_rule_id == self.test_rule_attendee
        )
        self.assertEqual(
            attendee_lead.visitor_ids,
            self.test_lang_visitor + self.test_lang_visitor_fr,
        )
        self.assertEqual(
            leads.lang_id,
            self.test_lang_visitor.lang_id + self.test_lang_visitor_fr.lang_id,
        )
