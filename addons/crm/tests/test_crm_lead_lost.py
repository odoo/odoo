# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.crm.tests import common as crm_common
from odoo.exceptions import AccessError
from odoo.tests.common import tagged, users


@tagged('lead_manage', 'lead_lost')
class TestLeadConvert(crm_common.TestCrmCommon):

    @classmethod
    def setUpClass(cls):
        super(TestLeadConvert, cls).setUpClass()
        cls.lost_reason = cls.env['crm.lost.reason'].create({
            'name': 'Test Reason'
        })

    @users('user_sales_salesman')
    def test_lead_lost(self):
        self.lead_1.with_user(self.user_sales_manager).write({
            'user_id': self.user_sales_salesman.id,
            'probability': 32,
        })
        self.flush_tracking()

        lead = self.lead_1.with_user(self.env.user)
        self.assertEqual(lead.probability, 32)
        self.assertEqual(len(lead.message_ids), 2, 'Should have tracked new responsible')

        lost_wizard = self.env['crm.lead.lost'].with_context({
            'active_ids': lead.ids,
        }).create({
            'lost_reason_id': self.lost_reason.id
        })

        lost_wizard.action_lost_reason_apply()
        self.flush_tracking()

        self.assertEqual(lead.probability, 0)
        self.assertEqual(lead.automated_probability, 0)
        self.assertFalse(lead.active)
        self.assertEqual(lead.lost_reason, self.lost_reason)  # TDE FIXME: should be called lost_reason_id non didjou
        # check messages
        self.assertEqual(len(lead.message_ids), 3, 'Should have logged a tracking message for lost lead with reason')

    @users('user_sales_salesman')
    def test_lead_lost_crm_rights(self):
        lead = self.lead_1.with_user(self.env.user)

        # nice try little salesman but only managers can create lost reason to avoid bloating the DB
        with self.assertRaises(AccessError):
            lost_reason = self.env['crm.lost.reason'].create({
                'name': 'Test Reason'
            })

        with self.with_user('user_sales_manager'):
            lost_reason = self.env['crm.lost.reason'].create({
                'name': 'Test Reason'
            })

        lost_wizard = self.env['crm.lead.lost'].with_context({
            'active_ids': lead.ids
        }).create({
            'lost_reason_id': lost_reason.id
        })

        # nice try little salesman, you cannot invoke a wizard to update other people leads
        with self.assertRaises(AccessError):
            lost_wizard.action_lost_reason_apply()
