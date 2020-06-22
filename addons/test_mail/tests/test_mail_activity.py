# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from unittest.mock import patch
from unittest.mock import DEFAULT

import pytz

from odoo import exceptions, tests
from odoo.addons.test_mail.tests.common import BaseFunctionalTest
from odoo.addons.test_mail.models.test_mail_models import MailTestActivity
from odoo.tools import mute_logger
from odoo.tests.common import Form


class TestActivityCommon(BaseFunctionalTest):

    @classmethod
    def setUpClass(cls):
        super(TestActivityCommon, cls).setUpClass()
        cls.test_record = cls.env['mail.test.activity'].with_context(cls._test_context).create({'name': 'Test'})
        # reset ctx
        cls.test_record = cls.test_record.with_context(
            mail_create_nolog=False,
            mail_create_nosubscribe=False,
            mail_notrack=False
        )


@tests.tagged('mail_activity')
class TestActivityRights(TestActivityCommon):

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_activity_security_user_access_other(self):
        activity = self.test_record.with_user(self.user_employee).activity_schedule(
            'test_mail.mail_act_test_todo',
            user_id=self.user_admin.id)
        self.assertTrue(activity.can_write)
        activity.write({'user_id': self.user_employee.id})

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_activity_security_user_access_own(self):
        activity = self.test_record.with_user(self.user_employee).activity_schedule(
            'test_mail.mail_act_test_todo')
        self.assertTrue(activity.can_write)
        activity.write({'user_id': self.user_admin.id})

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_activity_security_user_noaccess_automated(self):
        def _employee_crash(*args, **kwargs):
            """ If employee is test employee, consider he has no access on document """
            recordset = args[0]
            if recordset.env.uid == self.user_employee.id:
                raise exceptions.AccessError('Hop hop hop Ernest, please step back.')
            return DEFAULT

        with patch.object(MailTestActivity, 'check_access_rights', autospec=True, side_effect=_employee_crash):
            activity = self.test_record.activity_schedule(
                'test_mail.mail_act_test_todo',
                user_id=self.user_employee.id)

            activity2 = self.test_record.activity_schedule('test_mail.mail_act_test_todo')
            activity2.write({'user_id': self.user_employee.id})

    def test_activity_security_user_noaccess_manual(self):
        def _employee_crash(*args, **kwargs):
            """ If employee is test employee, consider he has no access on document """
            recordset = args[0]
            if recordset.env.uid == self.user_employee.id:
                raise exceptions.AccessError('Hop hop hop Ernest, please step back.')
            return DEFAULT

        # cannot create activities for people that cannot access record
        with patch.object(MailTestActivity, 'check_access_rights', autospec=True, side_effect=_employee_crash):
            with self.assertRaises(exceptions.UserError):
                activity = self.env['mail.activity'].create({
                    'activity_type_id': self.env.ref('test_mail.mail_act_test_todo').id,
                    'res_model_id': self.env.ref('test_mail.model_mail_test_activity').id,
                    'res_id': self.test_record.id,
                    'user_id': self.user_employee.id,
                })

        # cannot create activities if no access to the document
        with patch.object(MailTestActivity, 'check_access_rights', autospec=True, side_effect=_employee_crash):
            with self.assertRaises(exceptions.AccessError):
                activity = self.test_record.with_user(self.user_employee).activity_schedule(
                    'test_mail.mail_act_test_todo',
                    user_id=self.user_admin.id)


@tests.tagged('mail_activity')
class TestActivityFlow(TestActivityCommon):

    def test_activity_flow_employee(self):
        with self.sudo('employee'):
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

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_activity_notify_other_user(self):
        self.user_admin.notification_type = 'email'
        rec = self.test_record.with_user(self.user_employee)
        with self.assertNotifications(partner_admin=(1, 'email', 'read')):
            activity = rec.activity_schedule(
                'test_mail.mail_act_test_todo',
                user_id=self.user_admin.id)
        self.assertEqual(activity.create_uid, self.user_employee)
        self.assertEqual(activity.user_id, self.user_admin)

    def test_activity_notify_same_user(self):
        self.user_employee.notification_type = 'email'
        rec = self.test_record.with_user(self.user_employee)
        with self.assertNotifications(partner_employee=(0, 'email', 'read')):
            activity = rec.activity_schedule(
                'test_mail.mail_act_test_todo',
                user_id=self.user_employee.id)
        self.assertEqual(activity.create_uid, self.user_employee)
        self.assertEqual(activity.user_id, self.user_employee)

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_activity_dont_notify_no_user_change(self):
        self.user_employee.notification_type = 'email'
        activity = self.test_record.activity_schedule('test_mail.mail_act_test_todo', user_id=self.user_employee.id)
        with self.assertNotifications(partner_employee=(0, 'email', 'read')):
            activity.with_user(self.user_admin).write({'user_id': self.user_employee.id})
        self.assertEqual(activity.user_id, self.user_employee)

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_activity_summary_sync(self):
        """ Test summary from type is copied on activities if set (currently only in form-based onchange) """
        ActivityType = self.env['mail.activity.type']
        email_activity_type = ActivityType.create({
            'name': 'email',
            'summary': 'Email Summary',
        })
        call_activity_type = ActivityType.create({'name': 'call'})
        with Form(self.env['mail.activity'].with_context(default_res_model_id=self.env.ref('base.model_res_partner'))) as ActivityForm:
            ActivityForm.res_model_id = self.env.ref('base.model_res_partner')

            ActivityForm.activity_type_id = call_activity_type
            # activity summary should be empty
            self.assertEqual(ActivityForm.summary, False)

            ActivityForm.activity_type_id = email_activity_type
            # activity summary should be replaced with email's default summary
            self.assertEqual(ActivityForm.summary, email_activity_type.summary)

            ActivityForm.activity_type_id = call_activity_type
            # activity summary remains unchanged from change of activity type as call activity doesn't have default summary
            self.assertEqual(ActivityForm.summary, email_activity_type.summary)

    def test_action_feedback_attachment(self):
        Partner = self.env['res.partner']
        Activity = self.env['mail.activity']
        Attachment = self.env['ir.attachment']
        Message = self.env['mail.message']

        partner = self.env['res.partner'].create({
            'name': 'Tester',
        })

        activity = Activity.create({
            'summary': 'Test',
            'activity_type_id': 1,
            'res_model_id': self.env.ref('base.model_res_partner').id,
            'res_id': partner.id,
        })

        attachments = Attachment
        attachments += Attachment.create({
            'name': 'test',
            'res_name': 'test',
            'res_model': 'mail.activity',
            'res_id': activity.id,
            'datas': 'test',
        })
        attachments += Attachment.create({
            'name': 'test2',
            'res_name': 'test',
            'res_model': 'mail.activity',
            'res_id': activity.id,
            'datas': 'testtest',
        })

        # Adding the attachments to the activity
        activity.attachment_ids = attachments

        # Checking if the attachment has been forwarded to the message
        # when marking an activity as "Done"
        activity.action_feedback()
        activity_message = Message.search([], order='id desc', limit=1)
        self.assertEqual(set(activity_message.attachment_ids.ids), set(attachments.ids))
        for attachment in attachments:
            self.assertEqual(attachment.res_id, activity_message.id)
            self.assertEqual(attachment.res_model, activity_message._name)

@tests.tagged('mail_activity')
class TestActivityMixin(TestActivityCommon):

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_activity_mixin(self):
        self.user_employee.tz = self.user_admin.tz
        with self.sudo('employee'):
            self.test_record = self.env['mail.test.activity'].browse(self.test_record.id)
            self.assertEqual(self.test_record.env.user, self.user_employee)

            now_utc = datetime.now(pytz.UTC)
            now_user = now_utc.astimezone(pytz.timezone(self.env.user.tz or 'UTC'))
            today_user = now_user.date()

            # Test various scheduling of activities
            act1 = self.test_record.activity_schedule(
                'test_mail.mail_act_test_todo',
                today_user + relativedelta(days=1),
                user_id=self.user_admin.id)
            self.assertEqual(act1.automated, True)

            act_type = self.env.ref('test_mail.mail_act_test_todo')
            self.assertEqual(self.test_record.activity_summary, act_type.summary)
            self.assertEqual(self.test_record.activity_state, 'planned')
            self.assertEqual(self.test_record.activity_user_id, self.user_admin)

            act2 = self.test_record.activity_schedule(
                'test_mail.mail_act_test_meeting',
                today_user + relativedelta(days=-1))
            self.assertEqual(self.test_record.activity_state, 'overdue')
            # `activity_user_id` is defined as `fields.Many2one('res.users', 'Responsible User', related='activity_ids.user_id')`
            # it therefore relies on the natural order of `activity_ids`, according to which activity comes first.
            # As we just created the activity, its not yet in the right order.
            # We force it by invalidating it so it gets fetched from database, in the right order.
            self.test_record.invalidate_cache(['activity_ids'])
            self.assertEqual(self.test_record.activity_user_id, self.user_employee)

            act3 = self.test_record.activity_schedule(
                'test_mail.mail_act_test_todo',
                today_user + relativedelta(days=3),
                user_id=self.user_employee.id)
            self.assertEqual(self.test_record.activity_state, 'overdue')
            # `activity_user_id` is defined as `fields.Many2one('res.users', 'Responsible User', related='activity_ids.user_id')`
            # it therefore relies on the natural order of `activity_ids`, according to which activity comes first.
            # As we just created the activity, its not yet in the right order.
            # We force it by invalidating it so it gets fetched from database, in the right order.
            self.test_record.invalidate_cache(['activity_ids'])
            self.assertEqual(self.test_record.activity_user_id, self.user_employee)

            self.test_record.invalidate_cache(ids=self.test_record.ids)
            self.assertEqual(self.test_record.activity_ids, act1 | act2 | act3)

            # Perform todo activities for admin
            self.test_record.activity_feedback(
                ['test_mail.mail_act_test_todo'],
                user_id=self.user_admin.id,
                feedback='Test feedback',)
            self.assertEqual(self.test_record.activity_ids, act2 | act3)

            # Reschedule all activities, should update the record state
            self.assertEqual(self.test_record.activity_state, 'overdue')
            self.test_record.activity_reschedule(
                ['test_mail.mail_act_test_meeting', 'test_mail.mail_act_test_todo'],
                date_deadline=today_user + relativedelta(days=3)
            )
            self.assertEqual(self.test_record.activity_state, 'planned')

            # Perform todo activities for remaining people
            self.test_record.activity_feedback(
                ['test_mail.mail_act_test_todo'],
                feedback='Test feedback')

            # Setting activities as done should delete them and post messages
            self.assertEqual(self.test_record.activity_ids, act2)
            self.assertEqual(len(self.test_record.message_ids), 2)
            self.assertEqual(self.test_record.message_ids.mapped('subtype_id'), self.env.ref('mail.mt_activities'))

            # Perform meeting activities
            self.test_record.activity_unlink(['test_mail.mail_act_test_meeting'])

            # Canceling activities should simply remove them
            self.assertEqual(self.test_record.activity_ids, self.env['mail.activity'])
            self.assertEqual(len(self.test_record.message_ids), 2)

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_activity_mixin_archive(self):
        rec = self.test_record.with_user(self.user_employee)
        new_act = rec.activity_schedule(
            'test_mail.mail_act_test_todo',
            user_id=self.user_admin.id)
        self.assertEqual(rec.activity_ids, new_act)
        rec.toggle_active()
        self.assertEqual(rec.active, False)
        self.assertEqual(rec.activity_ids, self.env['mail.activity'])
        rec.toggle_active()
        self.assertEqual(rec.active, True)
        self.assertEqual(rec.activity_ids, self.env['mail.activity'])

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_activity_mixin_reschedule_user(self):
        rec = self.test_record.with_user(self.user_employee)
        rec.activity_schedule(
            'test_mail.mail_act_test_todo',
            user_id=self.user_admin.id)
        self.assertEqual(rec.activity_ids[0].user_id, self.user_admin)

        # reschedule its own should not alter other's activities
        rec.activity_reschedule(
            ['test_mail.mail_act_test_todo'],
            user_id=self.user_employee.id,
            new_user_id=self.user_employee.id)
        self.assertEqual(rec.activity_ids[0].user_id, self.user_admin)

        rec.activity_reschedule(
            ['test_mail.mail_act_test_todo'],
            user_id=self.user_admin.id,
            new_user_id=self.user_employee.id)
        self.assertEqual(rec.activity_ids[0].user_id, self.user_employee)
