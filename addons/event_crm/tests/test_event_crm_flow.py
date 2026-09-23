from unittest.mock import patch

from odoo import Command
from odoo.tests import tagged
from odoo.tests.common import users

from odoo.addons.base.tests.test_ir_cron import CronMixinCase
from odoo.addons.event_crm.tests.common import TestEventCrmCommon


@tagged("event_crm")
class TestEventCrmFlow(TestEventCrmCommon, CronMixinCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.registration_values = [
            dict(customer_data, event_id=cls.event_0.id)
            for customer_data in cls.batch_customer_data
        ]
        cls.registration_values[-1]["email"] = '"John Doe" <invalid@not.example.com>'

    def test_assert_initial_data(self):
        self.assertEqual(len(self.registration_values), 5)

        self.assertEqual(self.event_customer.country_id, self.env.ref("base.be"))
        self.assertEqual(
            self.event_customer.email_normalized, "constantin@test.example.com"
        )
        self.assertEqual(self.event_customer._phone_get_number().number, "0485112233")

    @users("user_eventmanager")
    @patch(
        "odoo.addons.event_crm.models.event_lead_request.EventLeadRequest._REGISTRATIONS_BATCH_SIZE",
        4,
    )
    def test_action_generate_leads(self):
        LeadRequestSudo = self.env["event.lead.request"].sudo()

        self.test_rule_attendee.event_registration_filter = [
            ["email", "ilike", "@nomatch.com"]
        ]
        self.env["event.registration"].create(self.registration_values)
        self.assertEqual(len(self.event_0.registration_ids), 5)

        self.assertFalse(bool(self.test_rule_attendee.lead_ids))

        self.test_rule_attendee.event_registration_filter = False
        with self.capture_triggers(
            "event_crm.ir_cron_generate_leads"
        ) as captured_trigger:
            self.event_0.action_generate_leads(event_lead_rules=self.test_rule_attendee)
        self.assertEqual(len(LeadRequestSudo.search([])), 1)
        self.assertEqual(len(captured_trigger.records), 1)

        with self.capture_triggers(
            "event_crm.ir_cron_generate_leads"
        ) as captured_trigger:
            LeadRequestSudo._cron_generate_leads()

        self.assertEqual(len(self.test_rule_attendee.lead_ids), 4)
        self.assertEqual(len(captured_trigger.records), 1)

        with self.capture_triggers(
            "event_crm.ir_cron_generate_leads"
        ) as captured_trigger:
            LeadRequestSudo._cron_generate_leads()

        self.assertEqual(len(self.test_rule_attendee.lead_ids), 5)
        self.assertEqual(len(captured_trigger.records), 0)
        self.assertFalse(bool(LeadRequestSudo.search([])))

    @users("user_eventregistrationdesk")
    def test_event_crm_flow_batch_create(self):
        new_registrations = self.env["event.registration"].create(
            self.registration_values
        )
        self.assertEqual(len(self.event_0.registration_ids), 5)

        self.assertEqual(len(self.test_rule_attendee.lead_ids), 4)
        for registration in new_registrations:
            lead = self.test_rule_attendee.lead_ids.filtered(
                lambda lead, registration=registration: (
                    registration in lead.registration_ids
                )
            )
            if registration.email == '"John Doe" <invalid@not.example.com>':
                self.assertEqual(lead, self.env["crm.lead"])
                continue

            expected_partner = (
                registration.partner_id
                if registration.partner_id == self.event_customer
                else None
            )
            self.assertTrue(bool(lead))
            self.assertLeadConvertion(
                self.test_rule_attendee, registration, partner=expected_partner
            )

        self.assertEqual(len(self.test_rule_order.lead_ids), 1)
        lead = self.test_rule_order.lead_ids
        self.assertLeadConvertion(
            self.test_rule_order,
            new_registrations.filtered(
                lambda reg: reg.email != '"John Doe" <invalid@not.example.com>'
            ),
            partner=new_registrations[0].partner_id,
        )
        self.assertNotIn("invalid@not.example.com", lead.description)

    @users("user_eventregistrationdesk")
    def test_event_crm_flow_batch_update(self):
        new_registrations = self.env["event.registration"].create(
            self.registration_values
        )
        self.assertEqual(len(self.event_0.registration_ids), 5)
        self.assertEqual(len(self.test_rule_attendee.lead_ids), 4)
        self.assertEqual(len(self.test_rule_order.lead_ids), 1)

        new_registrations.write({"partner_id": self.event_customer2.id})

        self.assertEqual(len(self.test_rule_attendee.lead_ids), 4)
        for registration in new_registrations:
            lead = self.test_rule_attendee.lead_ids.filtered(
                lambda lead, registration=registration: (
                    registration in lead.registration_ids
                )
            )
            if registration.email == '"John Doe" <invalid@not.example.com>':
                self.assertEqual(lead, self.env["crm.lead"])
                continue

            self.assertLeadConvertion(
                self.test_rule_attendee, registration, partner=None
            )

        self.assertEqual(len(self.test_rule_order.lead_ids), 1)
        self.assertEqual(self.test_rule_order.lead_ids.event_id, self.event_0)
        lead = self.test_rule_order.lead_ids
        self.assertLeadConvertion(
            self.test_rule_order,
            new_registrations.filtered(
                lambda reg: reg.email != '"John Doe" <invalid@not.example.com>'
            ),
            partner=new_registrations[0].partner_id,
        )
        self.assertNotIn("invalid@not.example.com", lead.description)

    @users("user_eventregistrationdesk")
    def test_event_crm_flow_per_attendee_single_wo_partner(self):
        for name, email, phone in [
            ("My Name", "super.email@test.example.com", "0456442211"),
            (False, "super.email@test.example.com", False),
            ('"My Name"', '"My Name" <my.name@test.example.com>', False),
        ]:
            with self.subTest(name=name, email=email, phone=phone):
                registration = self.env["event.registration"].create(
                    {
                        "name": name,
                        "partner_id": False,
                        "email": email,
                        "phone_ids": [
                            Command.create({"number": phone, "type": "landline"})
                        ]
                        if phone
                        else False,
                        "event_id": self.event_0.id,
                    }
                )
                self.assertLeadConvertion(
                    self.test_rule_attendee, registration, partner=None
                )

        registration = self.env["event.registration"].create(
            {
                "partner_id": self.event_customer.id,
                "email": "other.email@test.example.com",
                "phone_ids": [
                    Command.create({"number": "0456112233", "type": "landline"})
                ],
                "event_id": self.event_0.id,
            }
        )
        self.assertLeadConvertion(self.test_rule_attendee, registration, partner=None)

    @users("user_eventregistrationdesk")
    def test_event_crm_flow_per_attendee_single_wpartner(self):
        self.event_customer2.write(
            {
                "email": False,
                "phone_ids": [Command.clear()],
            }
        )
        self.test_rule_attendee.write(
            {
                "event_registration_filter": "[]",
            }
        )
        for email, phone, base_partner, expected_partner in [
            (False, False, self.event_customer, self.event_customer),
            (
                '"Other Name" <constantin@test.example.com>',
                False,
                self.event_customer,
                self.event_customer,
            ),
            (
                "other.email@test.example.com",
                False,
                self.event_customer,
                self.env["res.partner"],
            ),
            (False, "+32485112233", self.event_customer, self.event_customer),
            (False, "0485112244", self.event_customer, self.env["res.partner"]),
            (
                "other.email@test.example.com",
                "0485112244",
                self.event_customer2,
                self.event_customer2,
            ),
        ]:
            with self.subTest(email=email, phone=phone, base_partner=base_partner):
                registration = self.env["event.registration"].create(
                    {
                        "partner_id": base_partner.id,
                        "email": email,
                        "phone_ids": [
                            Command.create({"number": phone, "type": "landline"})
                        ]
                        if phone
                        else False,
                        "event_id": self.event_0.id,
                    }
                )
                self.assertLeadConvertion(
                    self.test_rule_attendee, registration, partner=expected_partner
                )

    @users("user_eventregistrationdesk")
    def test_event_crm_trigger_done(self):
        registration = self.env["event.registration"].create(
            {
                "partner_id": self.event_customer.id,
                "email": "trigger.test@not.test.example.com",
                "phone_ids": [
                    Command.create({"number": "0456112233", "type": "landline"})
                ],
                "event_id": self.event_0.id,
            }
        )

        leads = (
            self.env["crm.lead"]
            .sudo()
            .search(
                [
                    ("registration_ids", "in", registration.ids),
                ]
            )
        )
        self.assertFalse(leads, "The lead must not be created yet")

        registration.action_set_done()

        self.assertLeadConvertion(self.test_rule_order_done, registration)

    @users("user_eventmanager")
    def test_order_rule_duplicate_lead(self):
        test_rule_order_2 = self.test_rule_order.copy(
            default={
                "event_registration_filter": [
                    ["email", "not ilike", "@test.example.com"]
                ]
            }
        )
        self.env["event.registration"].create(
            {
                "name": "My Registration",
                "partner_id": False,
                "email": "super.email@test.example.com",
                "phone_ids": [Command.clear()],
                "event_id": self.event_0.id,
            }
        )
        self.assertEqual(len(self.test_rule_order.lead_ids), 1)
        self.assertEqual(len(test_rule_order_2.lead_ids), 0)
