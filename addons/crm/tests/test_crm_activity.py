# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date, timedelta

from odoo.addons.crm.tests.common import TestCrmCommon
from odoo.tests.common import users


class TestCrmMailActivity(TestCrmCommon):

    @classmethod
    def setUpClass(cls):
        super(TestCrmMailActivity, cls).setUpClass()

        cls.activity_type_1 = cls.env['mail.activity.type'].create({
            'name': 'Initial Contact',
            'delay_count': 5,
            'summary': 'ACT 1 : Presentation, barbecue, ... ',
            'res_model': 'crm.lead',
        })
        cls.activity_type_2 = cls.env['mail.activity.type'].create({
            'name': 'Call for Demo',
            'delay_count': 6,
            'summary': 'ACT 2 : I want to show you my ERP !',
            'res_model': 'crm.lead',
        })
        for activity_type in cls.activity_type_1 + cls.activity_type_2:
            cls.env['ir.model.data'].create({
                'name': activity_type.name.lower().replace(' ', '_'),
                'module': 'crm',
                'model': activity_type._name,
                'res_id': activity_type.id,
            })

    @users('user_sales_leads')
    def test_crm_activity_ordering(self):
        """ Test ordering on "my activities", linked to a hack introduced for a b2b.
        Purpose is to be able to order on "my activities", which is a filtered o2m.
        In this test we will check search, limit, order and offset linked to the
        override of search for this non stored computed field. """
        # Initialize some batch data
        default_order = self.env['crm.lead']._order
        self.assertEqual(default_order, "priority desc, id desc")  # force updating this test is order changes
        test_leads = self._create_leads_batch(count=10, partner_ids=[self.contact_1.id, self.contact_2.id, False]).sorted('id')

        # assert initial data, ensure we did not break base behavior
        for lead in test_leads:
            self.assertFalse(lead.my_activity_date_deadline)
        search_res = self.env['crm.lead'].search([('id', 'in', test_leads.ids)], limit=5, offset=0, order='id ASC')
        self.assertEqual(search_res.ids, test_leads[:5].ids)
        search_res = self.env['crm.lead'].search([('id', 'in', test_leads.ids)], limit=5, offset=5, order='id ASC')
        self.assertEqual(search_res.ids, test_leads[5:10].ids)

        # Let's schedule some activities for "myself" and "my bro"and check those are correctly computed
        # LEAD NUMBER     DEADLINE (MY) PRIORITY   LATE DEADLINE (MY)
        # 0               +2D           0          +2D
        # 1               -1D           1          +2D
        # 2               -2D           2          +2D
        # 3               -1D           0          -1D
        # 4               -2D           1          -2D
        # 5               +2D           2          +2D
        # 6+              /             0/1/2/0    /
        today = date.today()
        deadline_in2d, deadline_in1d = today + timedelta(days=2), today + timedelta(days=1)
        deadline_was2d, deadline_was1d = today + timedelta(days=-2), today + timedelta(days=-1)
        deadlines_my = [deadline_in2d, deadline_was1d, deadline_was2d, deadline_was1d, deadline_was2d,
                        deadline_in2d, False, False, False, False]
        deadlines_gl = [deadline_in1d, deadline_was1d, deadline_was2d, deadline_was1d, deadline_was2d,
                        deadline_in2d, False, False, False, False]

        test_leads[0:4].activity_schedule(act_type_xmlid='crm.call_for_demo', user_id=self.user_sales_manager.id, date_deadline=deadline_in1d)
        test_leads[0:3].activity_schedule(act_type_xmlid='crm.initial_contact', date_deadline=deadline_in2d)
        test_leads[5].activity_schedule(act_type_xmlid='crm.initial_contact', date_deadline=deadline_in2d)
        (test_leads[1] | test_leads[3]).activity_schedule(act_type_xmlid='crm.initial_contact', date_deadline=deadline_was1d)
        (test_leads[2] | test_leads[4]).activity_schedule(act_type_xmlid='crm.call_for_demo', date_deadline=deadline_was2d)
        test_leads.invalidate_cache()

        expected_ids_asc = [2, 4, 1, 3, 5, 0, 8, 7, 9, 6]
        expected_leads_asc = self.env['crm.lead'].browse([test_leads[lid].id for lid in expected_ids_asc])
        expected_ids_desc = [5, 0, 1, 3, 2, 4, 8, 7, 9, 6]
        expected_leads_desc = self.env['crm.lead'].browse([test_leads[lid].id for lid in expected_ids_desc])

        for idx, lead in enumerate(test_leads):
            self.assertEqual(lead.my_activity_date_deadline, deadlines_my[idx])
            self.assertEqual(lead.activity_date_deadline, deadlines_gl[idx], 'Fail at %s' % idx)

        # Let's go for a first batch of search
        _order = 'my_activity_date_deadline ASC, %s' % default_order
        _domain = [('id', 'in', test_leads.ids)]

        search_res = self.env['crm.lead'].search(_domain, limit=None, offset=0, order=_order)
        self.assertEqual(expected_leads_asc.ids, search_res.ids)
        search_res = self.env['crm.lead'].search(_domain, limit=4, offset=0, order=_order)
        self.assertEqual(expected_leads_asc[:4].ids, search_res.ids)
        search_res = self.env['crm.lead'].search(_domain, limit=4, offset=3, order=_order)
        self.assertEqual(expected_leads_asc[3:7].ids, search_res.ids)
        search_res = self.env['crm.lead'].search(_domain, limit=None, offset=3, order=_order)
        self.assertEqual(expected_leads_asc[3:].ids, search_res.ids)

        _order = 'my_activity_date_deadline DESC, %s' % default_order
        search_res = self.env['crm.lead'].search(_domain, limit=None, offset=0, order=_order)
        self.assertEqual(expected_leads_desc.ids, search_res.ids)
        search_res = self.env['crm.lead'].search(_domain, limit=4, offset=0, order=_order)
        self.assertEqual(expected_leads_desc[:4].ids, search_res.ids)
        search_res = self.env['crm.lead'].search(_domain, limit=4, offset=3, order=_order)
        self.assertEqual(expected_leads_desc[3:7].ids, search_res.ids)
        search_res = self.env['crm.lead'].search(_domain, limit=None, offset=3, order=_order)
        self.assertEqual(expected_leads_desc[3:].ids, search_res.ids)

    def test_crm_activity_recipients(self):
        """ This test case checks
                - no internal subtype followed by client
                - activity subtype are not default ones
                - only activity followers are recipients when this kind of activity is logged
        """
        # Add explicitly a the client as follower
        self.lead_1.message_subscribe(partner_ids=[self.contact_1.id])

        # Check the client is not follower of any internal subtype
        internal_subtypes = self.lead_1.message_follower_ids.filtered(lambda fol: fol.partner_id == self.contact_1).mapped('subtype_ids').filtered(lambda subtype: subtype.internal)
        self.assertFalse(internal_subtypes)

        # Add sale manager as follower of default subtypes
        self.lead_1.message_subscribe(partner_ids=[self.user_sales_manager.partner_id.id], subtype_ids=[self.env.ref('mail.mt_activities').id, self.env.ref('mail.mt_comment').id])

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
