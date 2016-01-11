# -*- coding: utf-8 -*-

from .test_crm_access_group_users import TestCrmAccessGroupUsers
from datetime import datetime


class TestCrmLeadActivity(TestCrmAccessGroupUsers):

    def test_crm_lead_activity(self):

        '''Tests For Test Crm Activity Process In Lead'''

        CrmActivity = self.env['crm.activity']
        MailMessage = self.env['mail.message']
        CrmActivityLog = self.env['crm.activity.log']

        # Salemanager create crm activity
        demo_activity = CrmActivity.sudo(self.crm_salemanager_id).create({
            'name': 'Demostration',
            'recommended_activity_ids': [(6, 0, [self.ref('crm.crm_activity_data_call'), self.ref('crm.crm_activity_data_email')])],
            })

        # Salemanager create crm lead and assign demo_activity
        demo_activity_lead = self.CrmLead.sudo(self.crm_salemanager_id).create({
            'type': 'lead',
            'name': 'Test Activity lead',
            'partner_id': self.ref("base.res_partner_1"),
            'stage_id': self.ref("crm.stage_lead1"),
            'description': 'This is the description of the test lead first.',
            'next_activity_id': demo_activity.id,
            'date_action': datetime.now()
        })
        demo_activity_lead._onchange_next_activity_id()

        # Salesman click on Log Activity button and open one wizard where either salesman can scheduled the next activities or finish current activity.
        activity_log_wizard = CrmActivityLog.create({'lead_id': demo_activity_lead.id})
        activity_log_wizard.onchange_lead_id()

        # Salesman click on 'Log & Schedule Next' button to scheduled the next sub activity which is define in demo_activity.
        next_activity_wizard = activity_log_wizard.sudo(self.crm_salesman_id).action_log_and_schedule()
        context = next_activity_wizard.get('context')
        activity_wizard = CrmActivityLog.create({'lead_id': context.get('default_lead_id'), 'last_activity_id': context.get('default_last_activity_id'), 'recommended_activity_id': self.ref('crm.crm_activity_data_email')})
        activity_wizard.onchange_recommended_activity_id()
        self.assertEqual(activity_wizard.next_activity_id.name, activity_wizard.recommended_activity_id.name, '%s should be assign in next_activity_id' % activity_wizard.recommended_activity_id.name)
        activity_wizard.action_schedule()
        self.assertEqual(demo_activity_lead.next_activity_id.name, activity_wizard.next_activity_id.name, 'Next activity should be %s' % activity_wizard.next_activity_id.name)
        message = MailMessage.search([('res_id', '=', demo_activity_lead.id), ('subtype_id', '=', activity_wizard.last_activity_id.subtype_id.id)], limit=1)
        self.assertTrue(message, "Activity log should be display in chatter also")

        # Salesman click on 'Log Only' button to finish current activity.
        activity_log_wizard = CrmActivityLog.create({'lead_id': demo_activity_lead.id,})
        activity_log_wizard.onchange_lead_id()
        activity_log_wizard.sudo(self.crm_salesman_id).action_log()
        message = MailMessage.search([('res_id', '=', demo_activity_lead.id), ('subtype_id', '=', activity_log_wizard.next_activity_id.subtype_id.id)], limit=1)
        self.assertTrue(message, "Activity log should be display in chatter also")
        self.assertFalse(demo_activity_lead.next_activity_id, 'As the next activity has been finished, Next Activity become null')
