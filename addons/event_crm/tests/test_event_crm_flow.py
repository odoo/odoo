# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.addons.base.tests.test_ir_cron import CronMixinCase
from odoo.addons.event_crm.tests.common import TestEventCrmCommon
from odoo.tests import tagged
from odoo.tests.common import users


@tagged('event_crm')
class TestEventCrmFlow(TestEventCrmCommon, CronMixinCase):

    @classmethod
    def setUpClass(cls):
        super(TestEventCrmFlow, cls).setUpClass()

        cls.registration_values = [
            dict(customer_data, event_id=cls.event_0.id)
            for customer_data in cls.batch_customer_data
        ]
        cls.registration_values[-1]['email'] = '"John Doe" <invalid@not.example.com>'

    def test_assert_initial_data(self):
        """ Ensure base test values to ease test understanding and maintenance """
        self.assertEqual(len(self.registration_values), 5)

        self.assertEqual(self.event_customer.country_id, self.env.ref('base.be'))
        self.assertEqual(self.event_customer.email_normalized, 'constantin@test.example.com')
        self.assertFalse(self.event_customer.mobile)
        self.assertEqual(self.event_customer.phone, '0485112233')

    @users('user_eventmanager')
    @patch('odoo.addons.event_crm.models.event_lead_request.EventLeadRequest._REGISTRATIONS_BATCH_SIZE', 4)
    def test_action_generate_leads(self):
        """ Test that the action to manually generate leads on an event works in batch as expected. """
        LeadRequestSudo = self.env['event.lead.request'].sudo()

        # modify the create rule to not match anything
        self.test_rule_attendee.event_registration_filter = [['email', 'ilike', '@nomatch.com']]
        self.env['event.registration'].create(self.registration_values)
        self.assertEqual(len(self.event_0.registration_ids), 5)

        # as the rule did not match anything, no leads were created
        self.assertFalse(bool(self.test_rule_attendee.lead_ids))

        # modify the rule again to match everything then manually ask to generate leads on the event
        # calling the action should create the generation request as well as a CRON trigger
        self.test_rule_attendee.event_registration_filter = False
        with self.capture_triggers('event_crm.ir_cron_generate_leads') as captured_trigger:
            self.event_0.action_generate_leads()
        self.assertEqual(len(LeadRequestSudo.search([])), 1)
        self.assertEqual(len(captured_trigger.records), 1)

        # first CRON run creates 4 leads (see patched batch size) and a CRON trigger
        with self.capture_triggers('event_crm.ir_cron_generate_leads') as captured_trigger:
            LeadRequestSudo._cron_generate_leads()

        self.assertEqual(len(self.test_rule_attendee.lead_ids), 4)
        self.assertEqual(len(captured_trigger.records), 1)

        # second and last CRON run creates the final lead and completes the batch
        # it should unlink the generation request and not create a CRON trigger
        with self.capture_triggers('event_crm.ir_cron_generate_leads') as captured_trigger:
            LeadRequestSudo._cron_generate_leads()

        self.assertEqual(len(self.test_rule_attendee.lead_ids), 5)
        self.assertEqual(len(captured_trigger.records), 0)
        self.assertFalse(bool(LeadRequestSudo.search([])))

    @users('user_eventregistrationdesk')
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

    @users('user_eventregistrationdesk')
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

    @users('user_eventregistrationdesk')
    def test_event_crm_flow_per_attendee_single_wo_partner(self):
        """ Single registration, attendee based, no partner involved, check
        contact info propagation """
        for name, email, phone in [
            ('My Name', 'super.email@test.example.com', '0456442211'),
            (False, 'super.email@test.example.com', False),
            ('"My Name"', '"My Name" <my.name@test.example.com>', False),
        ]:
            with self.subTest(name=name, email=email, phone=phone):
                registration = self.env['event.registration'].create({
                    'name': name,
                    'partner_id': False,
                    'email': email,
                    'phone': phone,
                    'event_id': self.event_0.id,
                })
                self.assertLeadConvertion(self.test_rule_attendee, registration, partner=None)

        # test: partner but with other contact information -> registration prior
        registration = self.env['event.registration'].create({
            'partner_id': self.event_customer.id,
            'email': 'other.email@test.example.com',
            'phone': '0456112233',
            'event_id': self.event_0.id,
        })
        self.assertLeadConvertion(self.test_rule_attendee, registration, partner=None)

    @users('user_eventregistrationdesk')
    def test_event_crm_flow_per_attendee_single_wpartner(self):
        """ Single registration, attendee based, with partner involved, check
        contact information, check synchronization and update """
        self.event_customer2.write({
            'email': False,
            'phone': False,
        })
        self.test_rule_attendee.write({
            'event_registration_filter': '[]',  # try various email combinations
        })
        for email, phone, base_partner, expected_partner in [
            (False, False, self.event_customer, self.event_customer),  # should take partner info
            ('"Other Name" <constantin@test.example.com>', False, self.event_customer, self.event_customer),  # same email normalized
            ('other.email@test.example.com', False, self.event_customer, self.env['res.partner']),  # not same email -> no partner on lead
            (False, '+32485112233', self.event_customer, self.event_customer),  # same phone but differently formatted
            (False, '0485112244', self.event_customer, self.env['res.partner']),  # other phone -> no partner on lead
            ('other.email@test.example.com', '0485112244', self.event_customer2, self.event_customer2),  # mail / phone update from registration as void on partner
        ]:
            with self.subTest(email=email, phone=phone, base_partner=base_partner):
                registration = self.env['event.registration'].create({
                    'partner_id': base_partner.id,
                    'email': email,
                    'phone': phone,
                    'event_id': self.event_0.id,
                })
                self.assertLeadConvertion(self.test_rule_attendee, registration, partner=expected_partner)

    @users('user_eventregistrationdesk')
    def test_event_crm_trigger_done(self):
        """Test the case when the "crm.lead.rule" is executed when we write on the
        registration state. """
        registration = self.env['event.registration'].create({
            'partner_id': self.event_customer.id,
            'email': 'trigger.test@not.test.example.com',
            'phone': '0456112233',
            'event_id': self.event_0.id,
        })

        leads = self.env['crm.lead'].sudo().search([
            ('registration_ids', 'in', registration.ids),
        ])
        self.assertFalse(leads, 'The lead must not be created yet')

        registration.action_set_done()

        self.assertLeadConvertion(self.test_rule_order_done, registration)

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
            'event_id': self.event_0.id,
        })
        self.assertEqual(len(self.test_rule_order.lead_ids), 1)
        self.assertEqual(len(test_rule_order_2.lead_ids), 0)
