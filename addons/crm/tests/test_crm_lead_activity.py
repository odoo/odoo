# -*- coding: utf-8 -*-

from .common import TestCrmCases
from odoo.fields import Datetime


class TestCrmLeadActivity(TestCrmCases):

    def test_crm_lead_activity(self):

        '''Tests For Test Crm Activity Process In Lead'''

        MailMessage = self.env['mail.message']
        CrmActivityLog = self.env['crm.activity.log']

        activity_email_id = self.env.ref('crm.crm_activity_data_email').id
        activity_call_id = self.env.ref('crm.crm_activity_data_call').id

        # Salemanager create crm activity
        demo_activity = self.env['crm.activity'].sudo(self.crm_salemanager.id).create({
            'name': 'Demonstration',
            'recommended_activity_ids': [(6, 0, [activity_call_id, activity_email_id])],
            })

        # Salemanager create crm lead and assign demo_activity
        demo_activity_lead = self.env['crm.lead'].sudo(self.crm_salemanager.id).create({
            'type': 'lead',
            'name': 'Test Activity lead',
            'partner_id': self.env.ref("base.res_partner_1").id,
            'stage_id': self.env.ref("crm.stage_lead1").id,
            'description': 'This is the description of the test lead first.',
            'next_activity_id': demo_activity.id,
            'date_action': Datetime.now()
        })
        demo_activity_lead._onchange_next_activity_id()

        # Salesman click on Log Activity button and open one wizard where either salesman can scheduled the next activities or finish current activity.
        activity_log_wizard = CrmActivityLog.create({'lead_id': demo_activity_lead.id})
        activity_log_wizard.onchange_lead_id()

        # Salesman click on 'Log & Schedule Next' button to scheduled the next sub activity which is define in demo_activity.
        next_activity_wizard = activity_log_wizard.sudo(self.crm_salesman.id).action_log_and_schedule()
        context = next_activity_wizard.get('context')
        activity_wizard = CrmActivityLog.create({'lead_id': context.get('default_lead_id'), 'last_activity_id': context.get('default_last_activity_id'), 'recommended_activity_id': activity_email_id})
        activity_wizard.onchange_recommended_activity_id()
        self.assertEqual(activity_wizard.next_activity_id.name, activity_wizard.recommended_activity_id.name, '%s should be assign in next_activity_id' % activity_wizard.recommended_activity_id.name)
        activity_wizard.action_schedule()
        self.assertEqual(demo_activity_lead.next_activity_id.name, activity_wizard.next_activity_id.name, 'Next activity should be %s' % activity_wizard.next_activity_id.name)
        message = MailMessage.search([('res_id', '=', demo_activity_lead.id), ('subtype_id', '=', activity_wizard.last_activity_id.subtype_id.id)], limit=1)
        self.assertTrue(message, "Activity log should be display in chatter also")

        # Salesman click on 'Log Only' button to finish current activity.
        activity_log_wizard = CrmActivityLog.create({'lead_id': demo_activity_lead.id})
        activity_log_wizard.onchange_lead_id()
        activity_log_wizard.sudo(self.crm_salesman.id).action_log()
        message = MailMessage.search([('res_id', '=', demo_activity_lead.id), ('subtype_id', '=', activity_log_wizard.next_activity_id.subtype_id.id)], limit=1)
        self.assertTrue(message, "Activity log should be display in chatter also")
        self.assertFalse(demo_activity_lead.next_activity_id, 'As the next activity has been finished, Next Activity become null')
