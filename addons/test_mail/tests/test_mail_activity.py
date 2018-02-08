# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date
from dateutil.relativedelta import relativedelta

from odoo import exceptions
from odoo.addons.test_mail.tests.common import BaseFunctionalTest
from odoo.tools import mute_logger


class TestMailActivity(BaseFunctionalTest):

    @classmethod
    def setUpClass(cls):
        super(TestMailActivity, cls).setUpClass()
        cls.test_record = cls.env['mail.test.activity'].create({'name': 'Test'})

    def test_activity_flow_employee(self):
        with self.sudoAs('ernest'):
            test_record = self.env['mail.test.activity'].browse(self.test_record.id)
            self.assertEqual(test_record.activity_ids, self.env['mail.activity'])

            # employee record an activity and check the deadline
            self.env['mail.activity'].create({
                'summary': 'Test Activity',
                'date_deadline':  date.today() + relativedelta(days=1),
                'activity_type_id': self.env.ref('mail.mail_activity_data_email').id,
                'res_model_id': self.env['ir.model']._get(test_record._name).id,
                'res_id': test_record.id,
            })
            self.assertEqual(test_record.activity_summary, 'Test Activity')
            self.assertEqual(test_record.activity_state, 'planned')

            test_record.activity_ids.write({'date_deadline':  date.today() - relativedelta(days=1)})
            test_record.invalidate_cache()  # TDE note: should not have to do it I think
            self.assertEqual(test_record.activity_state, 'overdue')

            test_record.activity_ids.write({'date_deadline':  date.today()})
            test_record.invalidate_cache()  # TDE note: should not have to do it I think
            self.assertEqual(test_record.activity_state, 'today')

            # activity is done
            test_record.activity_ids.action_feedback(feedback='So much feedback')
            self.assertEqual(test_record.activity_ids, self.env['mail.activity'])
            self.assertEqual(test_record.message_ids[0].subtype_id, self.env.ref('mail.mt_activities'))

    def test_activity_flow_portal(self):
        portal_user = self.env['res.users'].with_context(self._quick_create_user_ctx).create({
            'name': 'Chell Gladys',
            'login': 'chell',
            'email': 'chell@gladys.portal',
            'groups_id': [(6, 0, [self.env.ref('base.group_portal').id])],
        })

        with self.sudoAs('chell'):
            test_record = self.env['mail.test.activity'].browse(self.test_record.id)
            # test_record.name
            # test_record.read()
            with self.assertRaises(exceptions.AccessError):
                self.env['mail.activity'].create({
                    'summary': 'Test Activity',
                    'activity_type_id': self.env.ref('mail.mail_activity_data_email').id,
                    'res_model_id': self.env['ir.model']._get(test_record._name).id,
                    'res_id': test_record.id,
                })
            # self.assertEqual(test_record.activity_ids, self.env['mail.activity'])
