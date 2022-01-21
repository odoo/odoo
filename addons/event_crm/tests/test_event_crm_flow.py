# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.event_crm.tests.common import TestEventCrmCommon
from odoo.tests.common import users
from odoo.tools import mute_logger


class TestEventCrmFlow(TestEventCrmCommon):

    @classmethod
    def setUpClass(cls):
        super(TestEventCrmFlow, cls).setUpClass()

        cls.registration_values = [
            dict(customer_data, event_id=cls.event_0.id)
            for customer_data in cls.batch_customer_data
        ]
        cls.registration_values[-1]['email'] = '"John Doe" <invalid@not.example.com>'

    def assert_initial_data(self):
        self.assertEqual(len(self.registration_values), 5)
        self.assertEqual(self.event_customer.email_normalized, 'constantin@test.example.com')
        self.assertEqual(self.event_customer.phone, '0485112233')
        self.assertFalse(self.event_customer.mobile)

    @users('user_eventmanager')
    def test_event_crm_flow_batch_create(self):
        """ Test attendee- and order-based registrations creation. Event-based
        creation mimics a simplified website_event flow where grouping is done
        at create. """
        new_registrations = self.env['event.registration'].create(self.registration_values)
        self.assertEqual(len(self.event_0.registration_ids), 5)

        # per-attendee rule: one lead for each registration
        self.assertEqual(len(self.test_rule_attendee.lead_ids), 4)
        for registration in new_registrations:
            lead = self.test_rule_attendee.lead_ids.filtered(lambda lead: registration in lead.registration_ids)
            # test filtering out based on domain
            if registration.email == '"John Doe" <invalid@not.example.com>':
                self.assertEqual(lead, self.env['crm.lead'])
                continue

            # only partner with matching email / phone is kept in mono attendee mode to avoid
            # loosing registration-specific email / phone informations due to lead synchronization
            expected_partner = registration.partner_id if registration.partner_id == self.event_customer else None
            self.assertTrue(bool(lead))
            self.assertLeadConvertion(self.test_rule_attendee, registration, partner=expected_partner)

        # per-order rule: one lead for all registrations (same event -> same batch, website_event style)
        self.assertEqual(len(self.test_rule_order.lead_ids), 1)
        lead = self.test_rule_order.lead_ids
        self.assertLeadConvertion(
            self.test_rule_order,
            new_registrations.filtered(lambda reg: reg.email != '"John Doe" <invalid@not.example.com>'),
            partner=new_registrations[0].partner_id
        )
        # ensuring filtering out worked also at description level
        self.assertNotIn('invalid@not.example.com', lead.description)

    @users('user_eventmanager')
    def test_event_crm_flow_batch_update(self):
        """ Test update of contact or description fields that leads to lead
        update. """
        # initial data: create registrations in batch
        new_registrations = self.env['event.registration'].create(self.registration_values)
        self.assertEqual(len(self.event_0.registration_ids), 5)
        self.assertEqual(len(self.test_rule_attendee.lead_ids), 4)
        self.assertEqual(len(self.test_rule_order.lead_ids), 1)

        # customer is updated (like a SO setting its customer)
        new_registrations.write({'partner_id': self.event_customer2.id})

        # per-attendee rule
        self.assertEqual(len(self.test_rule_attendee.lead_ids), 4)
        for registration in new_registrations:
            lead = self.test_rule_attendee.lead_ids.filtered(lambda lead: registration in lead.registration_ids)
            # test filtering out based on domain
            if registration.email == '"John Doe" <invalid@not.example.com>':
                self.assertEqual(lead, self.env['crm.lead'])
                continue

            # only partner with matching email / phone is kept in mono attendee mode to avoid
            # loosing registration-specific email / phone informations due to lead synchronization
            self.assertLeadConvertion(self.test_rule_attendee, registration, partner=None)

        # per-order rule
        self.assertEqual(len(self.test_rule_order.lead_ids), 1)
        self.assertEqual(self.test_rule_order.lead_ids.event_id, self.event_0)
        lead = self.test_rule_order.lead_ids
        self.assertLeadConvertion(
            self.test_rule_order,
            new_registrations.filtered(lambda reg: reg.email != '"John Doe" <invalid@not.example.com>'),
            partner=new_registrations[0].partner_id
        )
        # ensuring filtering out worked also at description level
        self.assertNotIn('invalid@not.example.com', lead.description)

    @users('user_eventmanager')
    def test_event_crm_flow_per_attendee_single(self):
        self.assert_initial_data()

        # test: partner-based contact information, everything synchonized
        registration = self.env['event.registration'].create({
            'partner_id': self.event_customer.id,
            'event_id': self.event_0.id,
        })
        self.assertEqual(registration.email, self.event_customer.email)
        self.assertEqual(registration.phone, self.event_customer.phone)

        # per-attendee rule
        self.assertLeadConvertion(self.test_rule_attendee, registration, partner=registration.partner_id)

        # test: no partner and contact information
        registration = self.env['event.registration'].create({
            'name': 'My Registration',
            'partner_id': False,
            'email': 'super.email@test.example.com',
            'phone': False,
            'mobile': '0456332211',
            'event_id': self.event_0.id,
        })
        self.assertEqual(len(self.event_0.registration_ids), 2)
        self.assertLeadConvertion(self.test_rule_attendee, registration, partner=None)

        # test: no partner and few information
        registration = self.env['event.registration'].create({
            'name': False,
            'partner_id': False,
            'email': 'giga.email@test.example.com',
            'phone': False,
            'mobile': False,
            'event_id': self.event_0.id,
        })
        self.assertEqual(len(self.event_0.registration_ids), 3)
        self.assertLeadConvertion(self.test_rule_attendee, registration, partner=None)

        # test: partner but with other contact information -> registration prior
        registration = self.env['event.registration'].create({
            'partner_id': self.event_customer.id,
            'email': 'other.email@test.example.com',
            'phone': False,
            'mobile': '0456112233',
            'event_id': self.event_0.id,
        })
        self.assertEqual(len(self.event_0.registration_ids), 4)
        self.assertLeadConvertion(self.test_rule_attendee, registration, partner=None)

    @users('user_eventmanager')
    def test_order_rule_duplicate_lead(self):
        """ Check when two rules match one event
            but only one match the registration,
            only one lead should be created
        """
        test_rule_order_2 = self.test_rule_order.copy(default={
            'event_registration_filter': [['email', 'not ilike', '@test.example.com']]
        })
        self.env['event.registration'].create({
            'name': 'My Registration',
            'partner_id': False,
            'email': 'super.email@test.example.com',
            'phone': False,
            'mobile': '0456332211',
            'event_id': self.event_0.id,
        })
        self.assertEqual(len(self.test_rule_order.lead_ids), 1)
        self.assertEqual(len(test_rule_order_2.lead_ids), 0)
