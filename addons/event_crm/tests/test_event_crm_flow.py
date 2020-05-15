# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.event_crm.tests.common import TestEventCrmCommon
from odoo.tools import mute_logger


class TestEventCrmFlow(TestEventCrmCommon):

    @classmethod
    def setUpClass(cls):
        super(TestEventCrmFlow, cls).setUpClass()

        test_registration_values = [{
            'event_id': cls.event_0.id,
            'name': 'Main Test Registration',
            'email': 'main@example.com',
            'phone': '0456000042',
        }]
        test_registration_values += [{
            'event_id': cls.event_0.id,
            'name': 'Test Registration %s' % i,
            'email': 'test%s@example.com' % i,
            'phone': '045600009%s' % i,
        } for i in range(2)]
        test_registration_values.append({
            'event_id': cls.event_0.id,
            'name': 'Test Registration Other',
            'email': 'other@other.com',
            'phone': '0456000099',
        })
        cls.env['event.registration'].create(test_registration_values)

    @mute_logger('odoo.addons.base.models.ir_model', 'odoo.models')
    def test_event_crm_flow_per_attendee(self):
        leads = self.env['crm.lead'].search([
            ('event_id', '=', self.event_0.id),
            ('event_lead_rule_id', '=', self.test_rule_attendee.id)
        ])

        self.assertEqual(len(leads), 3,
            "Event CRM: registration which does not check the rule should not create lead")

        self.assertEqual(len(leads.event_id.registration_ids), 4,
            "Event CRM: three registrations should have been created for the event")

    @mute_logger('odoo.addons.base.models.ir_model', 'odoo.models')
    def test_event_crm_flow_per_order(self):
        lead = self.env['crm.lead'].search([
            ('event_id', '=', self.event_0.id),
            ('event_lead_rule_id', '=', self.test_rule_order.id)
        ])

        self.assertEqual(len(lead), 1,
            "Event CRM: one lead sould be created for the set of attendees")

        self.assertEqual(lead.registration_count, 3,
            "Event CRM: registration which does not check the rule should not be linked to the lead")

        self.assertEqual(len(lead.event_id.registration_ids), 4,
            "Event CRM: four registrations should have been created for the event")

    @mute_logger('odoo.addons.base.models.ir_model', 'odoo.models')
    def test_event_crm_multi_rules(self):
        leads = self.env['crm.lead'].search([
            ('event_id', '=', self.event_0.id),
            ('event_lead_rule_id', 'in', [self.test_rule_attendee.id, self.test_rule_order.id])
        ])

        self.assertEqual(len(leads), 4,
            "Event CRM: four leads sould be created for the set of attendees")

        self.assertEqual(len(leads.event_id.registration_ids), 4,
            "Event CRM: four registrations should have been created for the event")
