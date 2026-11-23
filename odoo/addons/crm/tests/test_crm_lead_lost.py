# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.crm.tests import common as crm_common
from odoo.exceptions import AccessError
from odoo.tests.common import tagged, users
from odoo.tools import mute_logger


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
        """ Test setting a lead as lost using the wizard. Also check that an
        'html editor' void content used as feedback is not logged on the lead. """
        # Initial data
        self.assertEqual(len(self.lead_1.message_ids), 1, 'Should contain creation message')
        creation_message = self.lead_1.message_ids[0]
        self.assertEqual(creation_message.subtype_id, self.env.ref('crm.mt_lead_create'))

        # Update responsible as ACLs is "own only" for user_sales_salesman
        self.lead_1.with_user(self.user_sales_manager).write({
            'user_id': self.user_sales_salesman.id,
            'probability': 32,
        })
        self.flush_tracking()

        lead = self.env['crm.lead'].browse(self.lead_1.ids)
        self.assertFalse(lead.lost_reason_id)
        self.assertEqual(lead.probability, 32)
        self.assertEqual(len(lead.message_ids), 2, 'Should have tracked new responsible')
        update_message = lead.message_ids[0]
        self.assertEqual(update_message.subtype_id, self.env.ref('mail.mt_note'))

        # mark as lost using the wizard
        lost_wizard = self.env['crm.lead.lost'].create({
            'lead_ids': lead.ids,
            'lost_reason_id': self.lost_reason.id,
            'lost_feedback': '<p></p>',  # void content
        })

        lost_wizard.action_lost_reason_apply()
        self.flush_tracking()

        # check lead update
        self.assertFalse(lead.active)
        self.assertEqual(lead.automated_probability, 0)
        self.assertEqual(lead.lost_reason_id, self.lost_reason)  # TDE FIXME: should be called lost_reason_id non didjou
        self.assertEqual(lead.probability, 0)
        # check messages
        self.assertEqual(len(lead.message_ids), 3, 'Should have logged a tracking message for lost lead with reason')
        update_message = lead.message_ids[0]
        self.assertEqual(update_message.subtype_id, self.env.ref('crm.mt_lead_lost'))
        self.assertEqual(len(update_message.tracking_value_ids), 2, 'Tracking: active, lost reason')
        self.assertTracking(
            update_message,
            [('active', 'boolean', True, False),
             ('lost_reason_id', 'many2one', False, self.lost_reason)
            ]
        )

    @users('user_sales_leads')
    def test_lead_lost_batch_wfeedback(self):
        """ Test setting leads as lost in batch using the wizard, including a log
        message. """
        leads = self._create_leads_batch(lead_type='lead', count=10, probabilities=[10, 20, 30])
        self.assertEqual(len(leads), 10)
        self.flush_tracking()

        lost_wizard = self.env['crm.lead.lost'].create({
            'lead_ids': leads.ids,
            'lost_reason_id': self.lost_reason.id,
            'lost_feedback': '<p>I cannot find it. It was in my closet and pouf, disappeared.</p>',
        })
        lost_wizard.action_lost_reason_apply()
        self.flush_tracking()

        for lead in leads:
            # check content
            self.assertFalse(lead.active)
            self.assertEqual(lead.automated_probability, 0)
            self.assertEqual(lead.probability, 0)
            self.assertEqual(lead.lost_reason_id, self.lost_reason)
            # check messages
            self.assertEqual(len(lead.message_ids), 2, 'Should have 2 messages: creation, lost with log')
            lost_message = lead.message_ids.filtered(lambda msg: msg.subtype_id == self.env.ref('crm.mt_lead_lost'))
            self.assertTrue(lost_message)
            self.assertTracking(
                lost_message,
                [('active', 'boolean', True, False),
                 ('lost_reason_id', 'many2one', False, self.lost_reason)
                ]
            )
            self.assertIn('<p>I cannot find it. It was in my closet and pouf, disappeared.</p>', lost_message.body,
                          'Feedback should be included directly within tracking message')

    @users('user_sales_salesman')
    @mute_logger('odoo.addons.base.models')
    def test_lead_lost_crm_rights(self):
        """ Test ACLs of lost reasons management and usage """
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

        # nice try little salesman, you cannot invoke a wizard to update other people leads
        with self.assertRaises(AccessError):
            # wizard needs to be here due to cache clearing in assertRaises
            # (ORM does not load m2m records unavailable to the user from database)
            lost_wizard = self.env['crm.lead.lost'].create({
                'lead_ids': lead.ids,
                'lost_reason_id': lost_reason.id
            })
            lost_wizard.action_lost_reason_apply()
