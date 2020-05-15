# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.event.tests.common import TestEventCommon


class TestEventCrmCommon(TestEventCommon):

    @classmethod
    def setUpClass(cls):
        super(TestEventCrmCommon, cls).setUpClass()

        cls.test_lead_tag = cls.env['crm.tag'].create({'name': 'TagTest'})

        cls.test_rule_attendee = cls.env['event.lead.rule'].with_user(cls.user_eventmanager).create({
            'name': 'TestEventCrm Attendee',
            'lead_creation_basis': 'attendee',
            'event_id': cls.event_0.id,
            'event_registration_filter': [['email', 'ilike', '@example.com']],
            'lead_tag_ids': cls.test_lead_tag,
            'lead_type': 'lead',
        })

        cls.test_rule_order = cls.env['event.lead.rule'].with_user(cls.user_eventmanager).create({
            'name': 'TestEventCrm Order',
            'lead_creation_basis': 'order',
            'event_id': cls.event_0.id,
            'event_registration_filter': [['email', 'ilike', '@example.com']],
            'lead_user_id': cls.user_eventmanager.id,
            'lead_type': 'opportunity',
        })

        cls.test_customer = cls.env['res.partner'].create({
            'name': 'Test Customer',
            'email': 'TestCustomer <test.customer@example.com>',
            'country_id': cls.env.ref('base.be').id,
            'mobile': '0456998877',
        })

        cls.batch_customer_data = [{
            'name': 'Batch Registrations',
            'email': 'email.%02d@example.com' % x,
            'phone': '04560000%02d' % x,
        }  for x in range(0, 4)]
