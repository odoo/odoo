# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.crm.tests.common import TestCrmCommon


class TestCrmMailActivity(TestCrmCommon):

    @classmethod
    def setUpClass(cls):
        super(TestCrmMailActivity, cls).setUpClass()

        cls.activity_type_1 = cls.env['mail.activity.type'].create({
            'name': 'Initial Contact',
            'delay_count': 5,
            'summary': 'ACT 1 : Presentation, barbecue, ... ',
            'res_model_id': cls.env['ir.model']._get('crm.lead').id,
        })
        cls.activity_type_2 = cls.env['mail.activity.type'].create({
            'name': 'Call for Demo',
            'delay_count': 6,
            'summary': 'ACT 2 : I want to show you my ERP !',
            'res_model_id': cls.env['ir.model']._get('crm.lead').id,
        })

    def test_crm_activity_recipients(self):
        """ This test case checks
                - no internal subtype followed by client
                - activity subtype are not default ones
                - only activity followers are recipients when this kind of activity is logged
        """
        # Add explicitly a the client as follower
        self.lead_1.message_subscribe([self.contact_1.id])

        # Check the client is not follower of any internal subtype
        internal_subtypes = self.lead_1.message_follower_ids.filtered(lambda fol: fol.partner_id == self.contact_1).mapped('subtype_ids').filtered(lambda subtype: subtype.internal)
        self.assertFalse(internal_subtypes)

        # Add sale manager as follower of default subtypes
        self.lead_1.message_subscribe([self.user_sales_manager.partner_id.id], subtype_ids=[self.env.ref('mail.mt_activities').id, self.env.ref('mail.mt_comment').id])

        activity = self.env['mail.activity'].with_user(self.user_sales_leads).create({
            'activity_type_id': self.activity_type_1.id,
            'note': 'Content of the activity to log',
            'res_id': self.lead_1.id,
            'res_model_id': self.env.ref('crm.model_crm_lead').id,
        })
        activity._onchange_activity_type_id()
        self.assertEqual(self.lead_1.activity_type_id, self.activity_type_1)
        self.assertEqual(self.lead_1.activity_summary, self.activity_type_1.summary)
        # self.assertEqual(self.lead.activity_date_deadline, self.activity_type_1.summary)

        # mark as done, check lead and posted message
        activity.action_done()
        self.assertFalse(self.lead_1.activity_type_id.id)
        self.assertFalse(self.lead_1.activity_ids)
        activity_message = self.lead_1.message_ids[0]
        self.assertEqual(activity_message.notified_partner_ids, self.user_sales_manager.partner_id)
        self.assertEqual(activity_message.subtype_id, self.env.ref('mail.mt_activities'))

    def test_crm_activity_next_action(self):
        """ This test case set the next activity on a lead, log another, and schedule a third. """
        # Add the next activity (like we set it from a form view)
        lead_model_id = self.env['ir.model']._get('crm.lead').id
        activity = self.env['mail.activity'].with_user(self.user_sales_manager).create({
            'activity_type_id': self.activity_type_1.id,
            'summary': 'My Own Summary',
            'res_id': self.lead_1.id,
            'res_model_id': lead_model_id,
        })
        activity._onchange_activity_type_id()

        # Check the next activity is correct
        self.assertEqual(self.lead_1.activity_summary, activity.summary)
        self.assertEqual(self.lead_1.activity_type_id, activity.activity_type_id)
        # self.assertEqual(fields.Datetime.from_string(self.lead.activity_date_deadline), datetime.now() + timedelta(days=activity.activity_type_id.days))

        activity.write({
            'activity_type_id': self.activity_type_2.id,
            'summary': '',
            'note': 'Content of the activity to log',
        })
        activity._onchange_activity_type_id()

        self.assertEqual(self.lead_1.activity_summary, activity.activity_type_id.summary)
        self.assertEqual(self.lead_1.activity_type_id, activity.activity_type_id)
        # self.assertEqual(fields.Datetime.from_string(self.lead.activity_date_deadline), datetime.now() + timedelta(days=activity.activity_type_id.days))

        activity.action_done()

        # Check the next activity on the lead has been removed
        self.assertFalse(self.lead_1.activity_type_id)
