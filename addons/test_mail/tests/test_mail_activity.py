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
                'date_deadline': date.today() + relativedelta(days=1),
                'activity_type_id': self.env.ref('mail.mail_activity_data_email').id,
                'res_model_id': self.env['ir.model']._get(test_record._name).id,
                'res_id': test_record.id,
            })
            self.assertEqual(test_record.activity_summary, 'Test Activity')
            self.assertEqual(test_record.activity_state, 'planned')

            test_record.activity_ids.write({'date_deadline': date.today() - relativedelta(days=1)})
            test_record.invalidate_cache()  # TDE note: should not have to do it I think
            self.assertEqual(test_record.activity_state, 'overdue')

            test_record.activity_ids.write({'date_deadline': date.today()})
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
            with self.assertRaises(exceptions.AccessError):
                self.env['mail.activity'].create({
                    'summary': 'Test Activity',
                    'activity_type_id': self.env.ref('mail.mail_activity_data_email').id,
                    'res_model_id': self.env['ir.model']._get(test_record._name).id,
                    'res_id': test_record.id,
                })

    def test_reminder_security(self):
        reminder = self.env['mail.activity'].sudo(self.user_admin).create({
            'note': 'Test Reminder',
            'date_deadline': date.today() + relativedelta(days=1),
        })

        with self.assertRaises(exceptions.AccessError):
            # try to delete admin record with demo user
            reminder.sudo(self.user_employee).unlink()

        with self.assertRaises(exceptions.AccessError):
            # try to update admin record with demo user
            reminder.sudo(self.user_employee).write({'note': 'Give money to demo user'})

        # but demo should be able to edit and delete its own reminder
        demo_reminder = self.env['mail.activity'].sudo(self.user_employee).create({
            'note': 'Test Reminder demo',
            'date_deadline': date.today() + relativedelta(days=2),
        })
        demo_reminder.write({'note': '<p>Holidays</p>'})
        self.assertEqual(demo_reminder.note, '<p>Holidays</p>')

        # edit of res_id and res_model should be impossible
        with self.assertRaises(exceptions.AccessError):
            demo_reminder.write({'res_id': 1})
        with self.assertRaises(exceptions.AccessError):
            demo_reminder.write({'res_model_id': 1})

        demo_reminder.unlink()

    def test_reminder_flow(self):
        with self.sudoAs('ernest'):
            reminder = self.env['mail.activity'].create({
                'note': 'Test Reminder',
                'date_deadline': date.today(),
            })
            self.assertEqual(reminder.summary, 'Test Reminder')
            reminder.write({'note': 'Holidays\nDestination: Pescara'})
            self.assertEqual(reminder.summary, 'Holidays')
            reminder.write({'note': ''})
            self.assertEqual(reminder.summary, 'Reminder')
            reminder.write({'note': 'Holidays', 'summary': 'Summary'})
            self.assertEqual(reminder.summary, 'Summary')
