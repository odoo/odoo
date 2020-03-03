# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.event_crm.tests.common import TestEventCrmCommon
from odoo.tools import mute_logger
from odoo import _


class TestEventCrmFlow(TestEventCrmCommon):

    @mute_logger('odoo.addons.base.models.ir_model', 'odoo.models')
    def test_event_crm_flow_per_attendee(self):
        leads = self.env['crm.lead'].search([
            ('event_id', '=', self.test_event.id),
            ('event_lead_rule_id', '=', self.test_rule_attendee.id)
        ])

        self.assertEqual(len(leads), 3,
            "Event CRM: registration which does not check the rule should not create lead")

        self.assertEqual(len(leads.event_id.registration_ids), 4,
            "Event CRM: three registrations should have been created for the event")

    @mute_logger('odoo.addons.base.models.ir_model', 'odoo.models')
    def test_event_crm_flow_per_order(self):
        lead = self.env['crm.lead'].search([
            ('event_id', '=', self.test_event.id),
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
            ('event_id', '=', self.test_event.id),
            ('event_lead_rule_id', 'in', [self.test_rule_attendee.id, self.test_rule_order.id])
        ])

        self.assertEqual(len(leads), 4,
            "Event CRM: four leads sould be created for the set of attendees")

        self.assertEqual(len(leads.event_id.registration_ids), 4,
            "Event CRM: four registrations should have been created for the event")
