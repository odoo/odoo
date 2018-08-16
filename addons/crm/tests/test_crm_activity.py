# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from .common import TestCrmCases
from odoo import fields
from datetime import datetime, timedelta


class TestCrmMailActivity(TestCrmCases):

    def setUp(self):
        super(TestCrmMailActivity, self).setUp()
        # Set up activities
        lead_model_id = self.env['ir.model']._get('crm.lead').id
        ActivityType = self.env['mail.activity.type']
        self.activity3 = ActivityType.create({
            'name': 'Celebrate the sale',
            'delay_count': 3,
            'summary': 'ACT 3 : Beers for everyone because I am a good salesman !',
            'res_model_id': lead_model_id,
        })
        self.activity2 = ActivityType.create({
            'name': 'Call for Demo',
            'delay_count': 6,
            'summary': 'ACT 2 : I want to show you my ERP !',
            'res_model_id': lead_model_id,
        })
        self.activity1 = ActivityType.create({
            'name': 'Initial Contact',
            'delay_count': 5,
            'summary': 'ACT 1 : Presentation, barbecue, ... ',
            'res_model_id': lead_model_id,
        })

        # I create an opportunity, as salesman
        self.partner_client = self.env.ref("base.res_partner_1")
        self.lead = self.env['crm.lead'].sudo(self.crm_salesman.id).create({
            'name': 'Test Opp',
            'type': 'opportunity',
            'partner_id': self.partner_client.id,
            'team_id': self.env.ref("sales_team.team_sales_department").id,
            'user_id': self.crm_salesman.id,
        })

    def test_crm_activity_recipients(self):
        """ This test case checks
                - no internal subtype followed by client
                - activity subtype are not default ones
                - only activity followers are recipients when this kind of activity is logged
        """
        # Activity I'm going to log
        activity = self.activity2

        # Add explicitly a the client as follower
        self.lead.message_subscribe([self.partner_client.id])

        # Check the client is not follower of any internal subtype
        internal_subtypes = self.lead.message_follower_ids.filtered(lambda fol: fol.partner_id == self.partner_client).mapped('subtype_ids').filtered(lambda subtype: subtype.internal)
        self.assertFalse(internal_subtypes)

        # Add sale manager as follower of default subtypes
        self.lead.message_subscribe([self.crm_salemanager.partner_id.id], subtype_ids=[self.env.ref('mail.mt_activities').id, self.env.ref('mail.mt_comment').id])

        activity = self.env['mail.activity'].sudo(self.crm_salesman.id).create({
            'activity_type_id': self.activity1.id,
            'note': 'Content of the activity to log',
            'res_id': self.lead.id,
            'res_model_id': self.env.ref('crm.model_crm_lead').id,
        })
        activity._onchange_activity_type_id()
        self.assertEqual(self.lead.activity_type_id, self.activity1)
        self.assertEqual(self.lead.activity_summary, self.activity1.summary)
        # self.assertEqual(self.lead.activity_date_deadline, self.activity1.summary)

        # mark as done, check lead and posted message
        activity.action_done()
        self.assertFalse(self.lead.activity_type_id.id)
        self.assertFalse(self.lead.activity_ids)
        activity_message = self.lead.message_ids[0]
        self.assertEqual(activity_message.needaction_partner_ids, self.crm_salemanager.partner_id)
        self.assertEqual(activity_message.subtype_id, self.env.ref('mail.mt_activities'))

    def test_crm_activity_next_action(self):
        """ This test case set the next activity on a lead, log another, and schedule a third. """
        # Add the next activity (like we set it from a form view)
        lead_model_id = self.env['ir.model']._get('crm.lead').id
        activity = self.env['mail.activity'].sudo(self.crm_salesman.id).create({
            'activity_type_id': self.activity1.id,
            'summary': 'My Own Summary',
            'res_id': self.lead.id,
            'res_model_id': lead_model_id,
        })
        activity._onchange_activity_type_id()

        # Check the next activity is correct
        self.assertEqual(self.lead.activity_summary, activity.summary)
        self.assertEqual(self.lead.activity_type_id, activity.activity_type_id)
        # self.assertEqual(fields.Datetime.from_string(self.lead.activity_date_deadline), datetime.now() + timedelta(days=activity.activity_type_id.days))

        activity.write({
            'activity_type_id': self.activity2.id,
            'summary': '',
            'note': 'Content of the activity to log',
        })
        activity._onchange_activity_type_id()

        self.assertEqual(self.lead.activity_summary, activity.activity_type_id.summary)
        self.assertEqual(self.lead.activity_type_id, activity.activity_type_id)
        # self.assertEqual(fields.Datetime.from_string(self.lead.activity_date_deadline), datetime.now() + timedelta(days=activity.activity_type_id.days))

        activity.action_done()

        # Check the next activity on the lead has been removed
        self.assertFalse(self.lead.activity_type_id)
