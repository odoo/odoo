# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta

from odoo import fields, tools
from odoo.addons.crm.tests.common import TestCrmCommon
from odoo.addons.event.tests.common import EventCase


class EventCrmCase(TestCrmCommon, EventCase):

    @classmethod
    def setUpClass(cls):
        super(EventCrmCase, cls).setUpClass()

        # avoid clash with existing rules
        cls.env['event.lead.rule'].search([]).write({'active': False})

        cls.test_lead_tag = cls.env['crm.tag'].create({'name': 'TagTest'})

        cls.test_rule_attendee = cls.env['event.lead.rule'].create({
            'name': 'Rule Attendee',
            'lead_creation_basis': 'attendee',
            'lead_creation_trigger': 'create',
            'event_registration_filter': [['email', 'ilike', '@test.example.com']],
            'lead_type': 'lead',
            'lead_user_id': cls.user_sales_salesman.id,
            'lead_tag_ids': cls.test_lead_tag,
        })

        cls.test_rule_order = cls.env['event.lead.rule'].create({
            'name': 'Rule Order',
            'lead_creation_basis': 'order',
            'lead_creation_trigger': 'create',
            'event_registration_filter': [['email', 'ilike', '@test.example.com']],
            'lead_type': 'opportunity',
            'lead_user_id': cls.user_sales_leads.id,
            'lead_sales_team_id': cls.sales_team_1.id,
        })
        cls.test_rule_order_done = cls.env['event.lead.rule'].create({
            'name': 'Rule Order: confirmed partner only',
            'lead_creation_basis': 'order',
            'lead_creation_trigger': 'done',
            'event_registration_filter': [['partner_id', '!=', False]],
            'lead_type': 'opportunity',
        })

        cls.batch_customer_data = [{
            'partner_id': cls.event_customer.id,
        }] + [{
            'name': 'My Customer 00',
            'partner_id': cls.event_customer2.id,
            'email': 'email.00@test.example.com',
            'phone': '0456000000',
        }] + [{
            'name': 'My Customer %02d' % x,
            'partner_id': cls.env.ref('base.public_partner').id if x == 0 else False,
            'email': 'email.%02d@test.example.com' % x,
            'phone': '04560000%02d' % x,
        }  for x in range(1, 4)]

    def assertLeadConvertion(self, rule, registrations, partner=None, **expected):
        """ Tool method hiding details of lead value generation and check

        :param lead: lead created through automated rule;
        :param rule: event.lead.rule that created the lead;
        :param event: original event;
        :param registrations: source registrations (singleton or record set if done in batch);
        :param partner: partner on lead;
        """
        registrations = registrations.sorted('id')  # currently order is forced to id ASC
        lead = self.env['crm.lead'].sudo().search([
            ('registration_ids', 'in', registrations.ids),
            ('event_lead_rule_id', '=', rule.id)
        ])
        self.assertEqual(len(lead), 1, 'Invalid registrations -> lead creation, found %s leads where only 1 is expected.' % len(lead))
        self.assertEqual(lead.registration_ids, registrations, 'Invalid registrations -> lead creation, too much registrations on it.')
        event = registrations.event_id
        self.assertEqual(len(event), 1, 'Invalid registrations -> event assertion, all registrations should belong to same event')

        if partner is None:
            partner = self.env['res.partner']
        expected_reg_name = partner.name or registrations._find_first_notnull('name') or registrations._find_first_notnull('email')
        if partner:
            expected_contact_name = partner.name if not partner.is_company else False
            expected_partner_name = partner.name if partner.is_company else False
        else:
            expected_contact_name = registrations._find_first_notnull('name')
            expected_partner_name = False

        # event information
        self.assertEqual(lead.event_id, event)
        self.assertEqual(lead.referred, event.name)

        # registration information
        registration_phone = registrations._find_first_notnull('phone')
        self.assertEqual(lead.partner_id, partner)
        self.assertEqual(lead.name, '%s - %s' % (event.name, expected_reg_name))
        self.assertNotIn('False', lead.name)  # avoid a "Dear False" like construct ^^ (this assert is serious and intended)
        self.assertEqual(lead.contact_name, expected_contact_name)
        self.assertEqual(lead.partner_name, expected_partner_name)
        self.assertEqual(lead.email_from, partner.email if partner and partner.email else registrations._find_first_notnull('email'))
        self.assertEqual(lead.phone, partner.phone if partner and partner.phone else registration_phone)
        self.assertEqual(lead.mobile, partner.mobile if partner and partner.mobile else ((registration_phone != lead.phone) and registration_phone))

        # description: to improve
        self.assertNotIn('False', lead.description)  # avoid a "Dear False" like construct ^^ (this assert is serious and intended)
        for registration in registrations:
            if registration.name:
                self.assertIn(registration.name, lead.description)
            elif registration.partner_id.name:
                self.assertIn(registration.partner_id.name, lead.description)
            if registration.email:
                if tools.email_normalize(registration.email) == registration.partner_id.email_normalized:
                    self.assertIn(registration.partner_id.email, lead.description)
                else:
                    self.assertIn(tools.email_normalize(registration.email), lead.description)
            if registration.phone:
                self.assertIn(registration.phone, lead.description)

        # lead configuration
        self.assertEqual(lead.type, rule.lead_type)
        self.assertEqual(lead.user_id, rule.lead_user_id)
        self.assertEqual(lead.team_id, rule.lead_sales_team_id)
        self.assertEqual(lead.tag_ids, rule.lead_tag_ids)


class TestEventCrmCommon(EventCrmCase):

    @classmethod
    def setUpClass(cls):
        super(TestEventCrmCommon, cls).setUpClass()

        cls.event_0 = cls.env['event.event'].create({
            'name': 'TestEvent',
            'date_begin': fields.Datetime.to_string(datetime.today() + timedelta(days=1)),
            'date_end': fields.Datetime.to_string(datetime.today() + timedelta(days=15)),
            'date_tz': 'Europe/Brussels',
        })

        cls.test_rule_attendee.event_id = cls.event_0.id
        cls.test_rule_order.event_id = cls.event_0.id
