# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
from psycopg2 import IntegrityError
from unittest.mock import patch
from unittest.mock import DEFAULT

import pytz
import random

from odoo import fields, exceptions, tests
from odoo.addons.mail.models.mail_activity import MailActivity
from odoo.addons.mail.tests.common import mail_new_test_user, MailCommon
from odoo.addons.test_mail.models.test_mail_models import MailTestActivity
from odoo.tests import Form, HttpCase, users
from odoo.tests.common import freeze_time
from odoo.tools import mute_logger


class TestActivityCommon(MailCommon):

    @classmethod
    def setUpClass(cls):
        super(TestActivityCommon, cls).setUpClass()
        cls.test_record, cls.test_record_2 = cls.env['mail.test.activity'].create([
            {'name': 'Test'},
            {'name': 'Test_2'},
        ])


@tests.tagged('mail_activity')
class TestActivityRights(TestActivityCommon):

    def test_activity_action_open_document_no_access(self):
        def _employee_no_access(records, operation):
            """Simulates employee having no access to the document"""
            if records.env.uid == self.user_employee.id and not records.env.su:
                return records, lambda: exceptions.AccessError('Access denied to document')
            return DEFAULT

        test_activity = self.env['mail.activity'].with_user(self.user_admin).create({
            'activity_type_id': self.env.ref('test_mail.mail_act_test_todo').id,
            'res_model_id': self.env.ref('test_mail.model_mail_test_activity').id,
            'res_id': self.test_record.id,
            'user_id': self.user_employee.id,
            'summary': 'Test Activity',
        })

        action = test_activity.with_user(self.user_employee).action_open_document()
        self.assertEqual(action['res_model'], self.test_record._name)
        self.assertEqual(action['res_id'], self.test_record.id)

        # If user has no access to the record, should return activity view instead
        with patch.object(MailTestActivity, '_check_access', autospec=True, side_effect=_employee_no_access):
            self.assertFalse(self.test_record.with_user(self.user_employee).has_access('read'))

            action = test_activity.with_user(self.user_employee).action_open_document()
            self.assertEqual(action['res_model'], 'mail.activity')
            self.assertEqual(action['res_id'], test_activity.id)

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

    def test_activity_security_user_access_customized(self):
        """ Test '_get_mail_message_access' support when scheduling activities. """
        access_open, access_ro, access_locked = self.env['mail.test.access.custo'].with_user(self.user_admin).create([
            {'name': 'Open'},
            {'name': 'Open RO', 'is_readonly': True},
            {'name': 'Locked', 'is_locked': True},
        ])
        # sanity checks on rule implementation
        (access_open + access_ro + access_locked).with_user(self.user_employee).check_access('read')
        access_open.with_user(self.user_employee).check_access('write')
        with self.assertRaises(exceptions.AccessError):
            (access_ro + access_locked).with_user(self.user_employee).check_access('write')

        # '_get_mail_message_access' allows to post, hence posting activities
        access_open.with_user(self.user_employee).activity_schedule(
            'test_mail.mail_act_test_todo_generic',
        )
        access_ro.with_user(self.user_employee).activity_schedule(
            'test_mail.mail_act_test_todo_generic',
        )

        with self.assertRaises(exceptions.AccessError):
            access_locked.with_user(self.user_employee).activity_schedule(
                'test_mail.mail_act_test_todo_generic',
            )

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_activity_security_user_noaccess_automated(self):
        def _employee_crash(records, operation):
            """ If employee is test employee, consider they have no access on document """
            if records.env.uid == self.user_employee.id and not records.env.su:
                return records, lambda: exceptions.AccessError('Hop hop hop Ernest, please step back.')
            return DEFAULT

        with patch.object(MailTestActivity, '_check_access', autospec=True, side_effect=_employee_crash):
            activity = self.test_record.activity_schedule(
                'test_mail.mail_act_test_todo',
                user_id=self.user_employee.id)

            activity2 = self.test_record.activity_schedule('test_mail.mail_act_test_todo')
            activity2.write({'user_id': self.user_employee.id})

    def test_activity_security_user_noaccess_manual(self):
        def _employee_crash(records, operation):
            """ If employee is test employee, consider they have no access on document """
            if records.env.uid == self.user_employee.id and not records.env.su:
                raise exceptions.AccessError('Hop hop hop Ernest, please step back.')
            return DEFAULT

        test_activity = self.env['mail.activity'].with_user(self.user_admin).create({
            'activity_type_id': self.env.ref('test_mail.mail_act_test_todo').id,
            'res_model_id': self.env.ref('test_mail.model_mail_test_activity').id,
            'res_id': self.test_record.id,
            'user_id': self.user_admin.id,
            'summary': 'Summary',
        })
        test_activity.flush_recordset()

        # can _search activities if access to the document
        self.env['mail.activity'].with_user(self.user_employee)._search(
            [('id', '=', test_activity.id)])

        # cannot _search activities if no access to the document
        with patch.object(MailTestActivity, '_check_access', autospec=True, side_effect=_employee_crash):
            with self.assertRaises(exceptions.AccessError):
                searched_activity = self.env['mail.activity'].with_user(self.user_employee)._search(
                    [('id', '=', test_activity.id)])

        # can read_group activities if access to the document
        read_group_result = self.env['mail.activity'].with_user(self.user_employee).read_group(
            [('id', '=', test_activity.id)],
            ['summary'],
            ['summary'],
        )
        self.assertEqual(1, read_group_result[0]['summary_count'])
        self.assertEqual('Summary', read_group_result[0]['summary'])

        # cannot read_group activities if no access to the document
        with patch.object(MailTestActivity, '_check_access', autospec=True, side_effect=_employee_crash):
            with self.assertRaises(exceptions.AccessError):
                self.env['mail.activity'].with_user(self.user_employee).read_group(
                    [('id', '=', test_activity.id)],
                    ['summary'],
                    ['summary'],
                )

        # cannot read activities if no access to the document
        with patch.object(MailTestActivity, '_check_access', autospec=True, side_effect=_employee_crash):
            with self.assertRaises(exceptions.AccessError):
                searched_activity = self.env['mail.activity'].with_user(self.user_employee).search(
                    [('id', '=', test_activity.id)])
                searched_activity.read(['summary'])

        # cannot search_read activities if no access to the document
        with patch.object(MailTestActivity, '_check_access', autospec=True, side_effect=_employee_crash):
            with self.assertRaises(exceptions.AccessError):
                self.env['mail.activity'].with_user(self.user_employee).search_read(
                    [('id', '=', test_activity.id)],
                    ['summary'])

        # can create activities for people that cannot access record
        with patch.object(MailTestActivity, '_check_access', autospec=True, side_effect=_employee_crash):
            self.env['mail.activity'].create({
                'activity_type_id': self.env.ref('test_mail.mail_act_test_todo').id,
                'res_model_id': self.env.ref('test_mail.model_mail_test_activity').id,
                'res_id': self.test_record.id,
                'user_id': self.user_employee.id,
            })

        # cannot create activities if no access to the document
        with patch.object(MailTestActivity, '_check_access', autospec=True, side_effect=_employee_crash):
            with self.assertRaises(exceptions.AccessError):
                activity = self.test_record.with_user(self.user_employee).activity_schedule(
                    'test_mail.mail_act_test_todo',
                    user_id=self.user_admin.id)

        test_activity.user_id = self.user_employee
        test_activity.flush_recordset()

        # user can read activities assigned to him even if he has no access to the document
        with patch.object(MailTestActivity, '_check_access', autospec=True, side_effect=_employee_crash):
            found = self.env['mail.activity'].with_user(self.user_employee).search(
                [('id', '=', test_activity.id)])
            self.assertEqual(found, test_activity)
            found.read(['summary'])

        # user can read_group activities assigned to him even if he has no access to the document
        with patch.object(MailTestActivity, '_check_access', autospec=True, side_effect=_employee_crash):
            read_group_result = self.env['mail.activity'].with_user(self.user_employee).read_group(
                [('id', '=', test_activity.id)],
                ['summary'],
                ['summary'],
            )
            self.assertEqual(1, read_group_result[0]['summary_count'])
            self.assertEqual('Summary', read_group_result[0]['summary'])


@tests.tagged('mail_activity')
class TestActivityFlow(TestActivityCommon):

    def test_activity_flow_employee(self):
        with self.with_user('employee'):
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
            self.assertEqual(test_record.activity_state, 'overdue')

            test_record.activity_ids.write({'date_deadline': date.today()})
            self.assertEqual(test_record.activity_state, 'today')

            # activity is done
            test_record.activity_ids.action_feedback(feedback='So much feedback')
            self.assertEqual(test_record.activity_ids, self.env['mail.activity'])
            self.assertEqual(test_record.message_ids[0].subtype_id, self.env.ref('mail.mt_activities'))

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_activity_notify_other_user(self):
        self.user_admin.notification_type = 'email'
        rec = self.test_record.with_user(self.user_employee)
        with self.assertSinglePostNotifications(
                [{'partner': self.partner_admin, 'type': 'email'}],
                message_info={'content': 'assigned you the following activity', 'subtype': 'mail.mt_note', 'message_type': 'user_notification'}):
            activity = rec.activity_schedule(
                'test_mail.mail_act_test_todo',
                user_id=self.user_admin.id)
        self.assertEqual(activity.create_uid, self.user_employee)
        self.assertEqual(activity.user_id, self.user_admin)

    def test_activity_notify_same_user(self):
        self.user_employee.notification_type = 'email'
        rec = self.test_record.with_user(self.user_employee)
        with self.assertNoNotifications():
            activity = rec.activity_schedule(
                'test_mail.mail_act_test_todo',
                user_id=self.user_employee.id)
        self.assertEqual(activity.create_uid, self.user_employee)
        self.assertEqual(activity.user_id, self.user_employee)

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_activity_dont_notify_no_user_change(self):
        self.user_employee.notification_type = 'email'
        activity = self.test_record.activity_schedule('test_mail.mail_act_test_todo', user_id=self.user_employee.id)
        with self.assertNoNotifications():
            activity.with_user(self.user_admin).write({'user_id': self.user_employee.id})
        self.assertEqual(activity.user_id, self.user_employee)

    def test_activity_summary_sync(self):
        """ Test summary from type is copied on activities if set (currently only in form-based onchange) """
        ActivityType = self.env['mail.activity.type']
        email_activity_type = ActivityType.create({
            'name': 'email',
            'summary': 'Email Summary',
        })
        call_activity_type = ActivityType.create({'name': 'call'})
        with Form(self.env['mail.activity'].with_context(default_res_model_id=self.env['ir.model']._get_id('mail.test.activity'), default_res_id=self.test_record.id)) as ActivityForm:
            # `res_model_id` and `res_id` are invisible, see view `mail.mail_activity_view_form_popup`
            # they must be set using defaults, see `action_feedback_schedule_next`
            ActivityForm.activity_type_id = call_activity_type
            # activity summary should be empty
            self.assertEqual(ActivityForm.summary, False)

            ActivityForm.activity_type_id = email_activity_type
            # activity summary should be replaced with email's default summary
            self.assertEqual(ActivityForm.summary, email_activity_type.summary)

            ActivityForm.activity_type_id = call_activity_type
            # activity summary remains unchanged from change of activity type as call activity doesn't have default summary
            self.assertEqual(ActivityForm.summary, email_activity_type.summary)

    @mute_logger('odoo.sql_db')
    def test_activity_values(self):
        """ Test activities are created with right model / res_id values linking
        to records without void values. 0 as res_id especially is not wanted. """
        # creating activities on a temporary record generates activities with res_id
        # being 0, which is annoying -> never create activities in transient mode
        temp_record = self.env['mail.test.activity'].new({'name': 'Test'})
        with self.assertRaises(IntegrityError):
            activity = temp_record.activity_schedule('test_mail.mail_act_test_todo', user_id=self.user_employee.id)

        test_record = self.env['mail.test.activity'].browse(self.test_record.ids)

        with self.assertRaises(IntegrityError):
            self.env['mail.activity'].create({
                'res_model_id': self.env['ir.model']._get_id(test_record._name),
            })
        with self.assertRaises(IntegrityError):
            self.env['mail.activity'].create({
                'res_model_id': self.env['ir.model']._get_id(test_record._name),
                'res_id': False,
            })
        with self.assertRaises(IntegrityError):
            self.env['mail.activity'].create({
                'res_id': test_record.id,
            })

        activity = self.env['mail.activity'].create({
            'res_id': test_record.id,
            'res_model_id': self.env['ir.model']._get_id(test_record._name),
        })
        with self.assertRaises(IntegrityError):
            activity.write({'res_model_id': False})
            self.env.flush_all()
        with self.assertRaises(IntegrityError):
            activity.write({'res_id': False})
            self.env.flush_all()
        with self.assertRaises(IntegrityError):
            activity.write({'res_id': 0})
            self.env.flush_all()


@tests.tagged('mail_activity')
class TestActivityMixin(TestActivityCommon):

    @classmethod
    def setUpClass(cls):
        super(TestActivityMixin, cls).setUpClass()

        cls.user_utc = mail_new_test_user(
            cls.env,
            name='User UTC',
            login='User UTC',
        )
        cls.user_utc.tz = 'UTC'

        cls.user_australia = mail_new_test_user(
            cls.env,
            name='user Australia',
            login='user Australia',
        )
        cls.user_australia.tz = 'Australia/Sydney'

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_activity_mixin(self):
        self.user_employee.tz = self.user_admin.tz
        with self.with_user('employee'):
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
            self.test_record.invalidate_recordset(['activity_ids'])
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
            self.test_record.invalidate_recordset(['activity_ids'])
            self.assertEqual(self.test_record.activity_user_id, self.user_employee)

            self.test_record.invalidate_recordset()
            self.assertEqual(self.test_record.activity_ids, act1 | act2 | act3)

            # Perform todo activities for admin
            self.test_record.activity_feedback(
                ['test_mail.mail_act_test_todo'],
                user_id=self.user_admin.id,
                feedback='Test feedback 1')
            self.assertEqual(self.test_record.activity_ids, act2 | act3)
            self.assertFalse(act1.exists())

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
                feedback='Test feedback 2')
            self.assertFalse(act3.exists())

            # Setting activities as done should delete them and post messages
            self.assertEqual(self.test_record.activity_ids, act2)
            self.assertEqual(len(self.test_record.message_ids), 3)
            feedback2, feedback1, _create_log = self.test_record.message_ids
            self.assertEqual((feedback2 + feedback1).subtype_id, self.env.ref('mail.mt_activities'))

            # Perform meeting activities
            self.test_record.activity_unlink(['test_mail.mail_act_test_meeting'])

            # Canceling activities should simply remove them
            self.assertEqual(self.test_record.activity_ids, self.env['mail.activity'])
            self.assertEqual(len(self.test_record.message_ids), 3, 'Should not produce additional message')
            self.assertFalse(self.test_record.activity_state)
            self.assertFalse(act2.exists())

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
    def test_activity_mixin_archive_user(self):
        """
        Test when archiving an user, we unlink all his related activities
        """
        test_users = self.env['res.users']
        for i in range(5):
            test_users += mail_new_test_user(self.env, name=f'test_user_{i}', login=f'test_password_{i}')
        for user in test_users:
            self.test_record.activity_schedule(user_id=user.id)
        archived_users = self.env['res.users'].browse(map(lambda x: x.id, random.sample(test_users, 2)))  # pick 2 users to archive
        archived_users.action_archive()
        active_users = test_users - archived_users

        # archive user with company disabled
        user_admin = self.user_admin
        user_employee_c2 = self.user_employee_c2
        self.assertIn(self.company_2, user_admin.company_ids)
        self.test_record.env['ir.rule'].create({
            'model_id': self.env.ref('test_mail.model_mail_test_activity').id,
            'domain_force': "[('company_id', 'in', company_ids)]"
        })
        self.test_record.activity_schedule(user_id=user_employee_c2.id)
        user_employee_c2.with_user(user_admin).with_context(
            allowed_company_ids=(user_admin.company_ids - self.company_2).ids
        ).action_archive()
        archived_users += user_employee_c2

        self.assertFalse(any(archived_users.mapped('active')), "Users should be archived.")

        # activities of active users shouldn't be touched, each has exactly 1 activity present
        activities = self.env['mail.activity'].search([('user_id', 'in', active_users.ids)])
        self.assertEqual(len(activities), 3, "We should have only 3 activities in total linked to our active users")
        self.assertEqual(activities.mapped('user_id'), active_users,
                         "We should have 3 different users linked to the activities of the active users")

        # ensure the user's activities are removed
        activities = self.env['mail.activity'].search([('user_id', 'in', archived_users.ids)])
        self.assertFalse(activities, "Activities of archived users should be deleted.")

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

    @users('employee')
    def test_feedback_w_attachments(self):
        test_record = self.env['mail.test.activity'].browse(self.test_record.ids)

        activity = self.env['mail.activity'].create({
            'activity_type_id': 1,
            'res_id': test_record.id,
            'res_model_id': self.env['ir.model']._get_id('mail.test.activity'),
            'summary': 'Test',
        })
        attachments = self.env['ir.attachment'].create([{
            'name': 'test',
            'res_name': 'test',
            'res_model': 'mail.activity',
            'res_id': activity.id,
            'datas': 'test',
        }, {
            'name': 'test2',
            'res_name': 'test',
            'res_model': 'mail.activity',
            'res_id': activity.id,
            'datas': 'testtest',
        }])

        # Checking if the attachment has been forwarded to the message
        # when marking an activity as "Done"
        activity.action_feedback()
        activity_message = test_record.message_ids[0]
        self.assertEqual(set(activity_message.attachment_ids.ids), set(attachments.ids))
        for attachment in attachments:
            self.assertEqual(attachment.res_id, activity_message.id)
            self.assertEqual(attachment.res_model, activity_message._name)

    @users('employee')
    def test_feedback_chained_current_date(self):
        frozen_now = datetime(2021, 10, 10, 14, 30, 15)

        test_record = self.env['mail.test.activity'].browse(self.test_record.ids)
        first_activity = self.env['mail.activity'].create({
            'activity_type_id': self.env.ref('test_mail.mail_act_test_chained_1').id,
            'date_deadline': frozen_now + relativedelta(days=-2),
            'res_id': test_record.id,
            'res_model_id': self.env['ir.model']._get_id('mail.test.activity'),
            'summary': 'Test',
        })
        first_activity_id = first_activity.id

        with freeze_time(frozen_now):
            first_activity.action_feedback(feedback='Done')
        self.assertFalse(first_activity.exists())

        # check chained activity
        new_activity = test_record.activity_ids
        self.assertNotEqual(new_activity.id, first_activity_id)
        self.assertEqual(new_activity.summary, 'Take the second step.')
        self.assertEqual(new_activity.date_deadline, frozen_now.date() + relativedelta(days=10))

    @users('employee')
    def test_feedback_chained_previous(self):
        self.env.ref('test_mail.mail_act_test_chained_2').sudo().write({'delay_from': 'previous_activity'})
        frozen_now = datetime(2021, 10, 10, 14, 30, 15)

        test_record = self.env['mail.test.activity'].browse(self.test_record.ids)
        first_activity = self.env['mail.activity'].create({
            'activity_type_id': self.env.ref('test_mail.mail_act_test_chained_1').id,
            'date_deadline': frozen_now + relativedelta(days=-2),
            'res_id': test_record.id,
            'res_model_id': self.env['ir.model']._get_id('mail.test.activity'),
            'summary': 'Test',
        })
        first_activity_id = first_activity.id

        with freeze_time(frozen_now):
            first_activity.action_feedback(feedback='Done')
        self.assertFalse(first_activity.exists())

        # check chained activity
        new_activity = test_record.activity_ids
        self.assertNotEqual(new_activity.id, first_activity_id)
        self.assertEqual(new_activity.summary, 'Take the second step.')
        self.assertEqual(new_activity.date_deadline, frozen_now.date() + relativedelta(days=8),
                         'New deadline should take into account original activity deadline, not current date')

    def test_mail_activity_state(self):
        """Create 3 activity for 2 different users in 2 different timezones.

        User UTC (+0h)
        User Australia (+11h)
        Today datetime: 1/1/2020 16h

        Activity 1 & User UTC
            1/1/2020 - 16h UTC       -> The state is today

        Activity 2 & User Australia
            1/1/2020 - 16h UTC
            2/1/2020 -  1h Australia -> State is overdue

        Activity 3 & User UTC
            1/1/2020 - 23h UTC       -> The state is today
        """
        today_utc = datetime(2020, 1, 1, 16, 0, 0)

        class MockedDatetime(datetime):
            @classmethod
            def utcnow(cls):
                return today_utc

        record = self.env['mail.test.activity'].create({'name': 'Record'})

        with patch('odoo.addons.mail.models.mail_activity.datetime', MockedDatetime):
            activity_1 = self.env['mail.activity'].create({
                'summary': 'Test',
                'activity_type_id': 1,
                'res_model_id': self.env.ref('test_mail.model_mail_test_activity').id,
                'res_id': record.id,
                'date_deadline': today_utc,
                'user_id': self.user_utc.id,
            })

            activity_2 = activity_1.copy()
            activity_2.user_id = self.user_australia
            activity_3 = activity_1.copy()
            activity_3.date_deadline += relativedelta(hours=7)

            self.assertEqual(activity_1.state, 'today')
            self.assertEqual(activity_2.state, 'overdue')
            self.assertEqual(activity_3.state, 'today')

    @users('employee')
    def test_mail_activity_mixin_search_activity_user_id_false(self):
        """Test the search method on the "activity_user_id" when searching for non-set user"""
        MailTestActivity = self.env['mail.test.activity']
        test_records = self.test_record | self.test_record_2
        self.assertFalse(test_records.activity_ids)
        self.assertEqual(MailTestActivity.search([('activity_user_id', '=', False)]), test_records)

        self.env['mail.activity'].create({
            'summary': 'Test',
            'activity_type_id': self.env.ref('test_mail.mail_act_test_todo').id,
            'res_model_id': self.env.ref('test_mail.model_mail_test_activity').id,
            'res_id': self.test_record.id,
        })
        self.assertEqual(MailTestActivity.search([('activity_user_id', '!=', True)]), self.test_record_2)

    @mute_logger('odoo.addons.mail.models.mail_mail', 'odoo.tests')
    def test_mail_activity_mixin_search_state_basic(self):
        """Test the search method on the "activity_state".

        Test all the operators and also test the case where the "activity_state" is
        different because of the timezone. There's also a tricky case for which we
        "reverse" the domain for performance purpose.
        """
        today_utc = datetime(2020, 1, 1, 16, 0, 0)

        class MockedDatetime(datetime):
            @classmethod
            def utcnow(cls):
                return today_utc

        # Create some records without activity schedule on it for testing
        self.env['mail.test.activity'].create([
            {'name': 'Record %i' % record_i}
            for record_i in range(5)
        ])

        origin_1, origin_2 = self.env['mail.test.activity'].search([], limit=2)
        activity_type = self.env.ref('test_mail.mail_act_test_todo')
        activity_type.sudo().keep_done = True

        with patch('odoo.addons.mail.models.mail_activity.datetime', MockedDatetime), \
            patch('odoo.addons.mail.models.mail_activity_mixin.datetime', MockedDatetime):
            origin_1_activity_1 = self.env['mail.activity'].create({
                'summary': 'Test',
                'activity_type_id': activity_type.id,
                'res_model_id': self.env.ref('test_mail.model_mail_test_activity').id,
                'res_id': origin_1.id,
                'date_deadline': today_utc,
                'user_id': self.user_utc.id,
            })

            origin_1_activity_2 = origin_1_activity_1.copy()
            origin_1_activity_2.user_id = self.user_australia
            origin_1_activity_3 = origin_1_activity_1.copy()
            origin_1_activity_3.date_deadline += relativedelta(hours=8)

            self.assertEqual(origin_1_activity_1.state, 'today')
            self.assertEqual(origin_1_activity_2.state, 'overdue')
            self.assertEqual(origin_1_activity_3.state, 'today')

            origin_2_activity_1 = self.env['mail.activity'].create({
                'summary': 'Test',
                'activity_type_id': activity_type.id,
                'res_model_id': self.env.ref('test_mail.model_mail_test_activity').id,
                'res_id': origin_2.id,
                'date_deadline': today_utc + relativedelta(hours=8),
                'user_id': self.user_utc.id,
            })

            origin_2_activity_2 = origin_2_activity_1.copy()
            origin_2_activity_2.user_id = self.user_australia
            origin_2_activity_3 = origin_2_activity_1.copy()
            origin_2_activity_3.date_deadline -= relativedelta(hours=8)
            origin_2_activity_4 = origin_2_activity_1.copy()
            origin_2_activity_4.date_deadline = datetime(2020, 1, 2, 0, 0, 0)

            self.assertEqual(origin_2_activity_1.state, 'planned')
            self.assertEqual(origin_2_activity_2.state, 'today')
            self.assertEqual(origin_2_activity_3.state, 'today')
            self.assertEqual(origin_2_activity_4.state, 'planned')

            all_activity_mixin_record = self.env['mail.test.activity'].search([])

            result = self.env['mail.test.activity'].search([('activity_state', '=', 'today')])
            self.assertTrue(len(result) > 0)
            self.assertEqual(result, all_activity_mixin_record.filtered(lambda p: p.activity_state == 'today'))

            result = self.env['mail.test.activity'].search([('activity_state', 'in', ('today', 'overdue'))])
            self.assertTrue(len(result) > 0)
            self.assertEqual(result, all_activity_mixin_record.filtered(lambda p: p.activity_state in ('today', 'overdue')))

            result = self.env['mail.test.activity'].search([('activity_state', 'not in', ('today',))])
            self.assertTrue(len(result) > 0)
            self.assertEqual(result, all_activity_mixin_record.filtered(lambda p: p.activity_state not in ('today',)))

            result = self.env['mail.test.activity'].search([('activity_state', '=', False)])
            self.assertTrue(len(result) >= 3, "There is more than 3 records without an activity schedule on it")
            self.assertEqual(result, all_activity_mixin_record.filtered(lambda p: not p.activity_state))

            result = self.env['mail.test.activity'].search([('activity_state', 'not in', ('planned', 'overdue', 'today'))])
            self.assertTrue(len(result) >= 3, "There is more than 3 records without an activity schedule on it")
            self.assertEqual(result, all_activity_mixin_record.filtered(lambda p: not p.activity_state))

            # test tricky case when the domain will be reversed in the search method
            # because of falsy value
            result = self.env['mail.test.activity'].search([('activity_state', 'not in', ('today', False))])
            self.assertTrue(len(result) > 0)
            self.assertEqual(result, all_activity_mixin_record.filtered(lambda p: p.activity_state not in ('today', False)))

            result = self.env['mail.test.activity'].search([('activity_state', 'in', ('today', False))])
            self.assertTrue(len(result) > 0)
            self.assertEqual(result, all_activity_mixin_record.filtered(lambda p: p.activity_state in ('today', False)))

            # Check that activity done are not taken into account by group and search by activity_state.
            Model = self.env['mail.test.activity']
            search_params = {
                'domain': [('id', 'in', (origin_1 | origin_2).ids), ('activity_state', '=', 'overdue')]}
            read_group_params = {'domain': [('id', 'in', (origin_1 | origin_2).ids)], 'fields': ['id:array_agg'],
                                 'groupby': ['activity_state']}
            self.assertEqual(Model.search(**search_params), origin_1)
            self.assertEqual(
                {(e['activity_state'], e['activity_state_count']) for e in Model.read_group(**read_group_params)},
                {('today', 1), ('overdue', 1)})
            origin_1_activity_2.action_feedback(feedback='Done')
            self.assertFalse(Model.search(**search_params))
            self.assertEqual(
                {(e['activity_state'], e['activity_state_count']) for e in Model.read_group(**read_group_params)},
                {('today', 2)})

    @mute_logger('odoo.addons.mail.models.mail_mail', 'odoo.tests')
    def test_mail_activity_mixin_search_state_different_day_but_close_time(self):
        """Test the case where there's less than 24 hours between the deadline and now_tz,
        but one day of difference (e.g. 23h 01/01/2020 & 1h 02/02/2020). So the state
        should be "planned" and not "today". This case was tricky to implement in SQL
        that's why it has its own test.
        """
        today_utc = datetime(2020, 1, 1, 23, 0, 0)

        class MockedDatetime(datetime):
            @classmethod
            def utcnow(cls):
                return today_utc

        # Create some records without activity schedule on it for testing
        self.env['mail.test.activity'].create([
            {'name': 'Record %i' % record_i}
            for record_i in range(5)
        ])

        origin_1 = self.env['mail.test.activity'].search([], limit=1)

        with patch('odoo.addons.mail.models.mail_activity.datetime', MockedDatetime):
            origin_1_activity_1 = self.env['mail.activity'].create({
                'summary': 'Test',
                'activity_type_id': 1,
                'res_model_id': self.env.ref('test_mail.model_mail_test_activity').id,
                'res_id': origin_1.id,
                'date_deadline': today_utc + relativedelta(hours=2),
                'user_id': self.user_utc.id,
            })

            self.assertEqual(origin_1_activity_1.state, 'planned')
            result = self.env['mail.test.activity'].search([('activity_state', '=', 'today')])
            self.assertNotIn(origin_1, result, 'The activity state miss calculated during the search')

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_my_activity_flow_employee(self):
        self.env.ref('test_mail.mail_act_test_todo').keep_done = True
        Activity = self.env['mail.activity']
        date_today = date.today()
        Activity.create({
            'activity_type_id': self.env.ref('test_mail.mail_act_test_todo').id,
            'date_deadline': date_today,
            'res_model_id': self.env.ref('test_mail.model_mail_test_activity').id,
            'res_id': self.test_record.id,
            'user_id': self.user_admin.id,
        })
        Activity.create({
            'activity_type_id': self.env.ref('test_mail.mail_act_test_call').id,
            'date_deadline': date_today + relativedelta(days=1),
            'res_model_id': self.env.ref('test_mail.model_mail_test_activity').id,
            'res_id': self.test_record.id,
            'user_id': self.user_employee.id,
        })

        test_record_1 = self.env['mail.test.activity'].with_context(self._test_context).create({'name': 'Test 1'})
        test_record_1_late_activity = Activity.create({
            'activity_type_id': self.env.ref('test_mail.mail_act_test_todo').id,
            'date_deadline': date_today,
            'res_model_id': self.env.ref('test_mail.model_mail_test_activity').id,
            'res_id': test_record_1.id,
            'user_id': self.user_employee.id,
        })
        with self.with_user('employee'):
            record = self.env['mail.test.activity'].search([('my_activity_date_deadline', '=', date_today)])
            self.assertEqual(test_record_1, record)
            test_record_1_late_activity._action_done()
            record = self.env['mail.test.activity'].with_context(active_test=False).search([
                ('my_activity_date_deadline', '=', date_today)
            ])
            self.assertFalse(record, "Should not find record if the only late activity is done")

    @users('employee')
    def test_record_unlink(self):
        test_record = self.test_record.with_user(self.env.user)
        act1 = test_record.activity_schedule(summary='Active')
        act2 = test_record.activity_schedule(summary='Archived', active=False)
        test_record.unlink()
        self.assertFalse((act1 + act2).exists(), 'Removing records should remove activities, even archived')

    @users('employee')
    def test_record_unlinked_orphan_activities(self):
        """Test the fix preventing error on corrupted database where activities without related record are present."""
        self.env.ref("test_mail.mail_act_test_todo").sudo().keep_done = True
        test_record = self.env['mail.test.activity'].with_context(
            self._test_context).create({'name': 'Test'}).with_user(self.user_employee)
        act = test_record.activity_schedule("test_mail.mail_act_test_todo", summary='Orphan activity')
        act.action_done()
        # Delete the record while preventing the cascade deletion of the activity to simulate a corrupted database
        with patch.object(MailActivity, 'unlink', lambda self: None):
            test_record.unlink()
        self.assertTrue(act.exists())
        self.assertFalse(act.active)
        self.assertFalse(test_record.exists())

        self.env.invalidate_all()
        self.assertFalse(
            self.env['mail.activity'].with_user(self.user_admin).with_context(active_test=False).search(
                [('active', '=', False)]),
            'Should consider unassigned activity on removed record = no access'
        )
        self.env.invalidate_all()
        with self.assertRaises(exceptions.AccessError):
            _dummy = act.with_user(self.user_admin).read(['summary'])


@tests.tagged("mail_activity", "post_install", "-at_install")
class TestActivitySystray(TestActivityCommon, HttpCase):
    """Test for systray_get_activities"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.test_lead_records = cls.env['mail.test.multi.company.with.activity'].create([
            {'name': 'Test Lead 1'},
            {'name': 'Test Lead 2'},
            {'name': 'Test Lead 3 (to remove)'},
            {'name': 'Test Lead 4 (Company2)', 'company_id': cls.company_2.id},
        ])
        cls.deleted_record = cls.test_lead_records[2]
        cls.dt_reference = datetime(2024, 1, 15, 8, 0, 0)

        # records and leads and free activities
        # have 1 record (or activity) for today, one for tomorrow
        cls.test_activities = cls.env['mail.activity']
        for record, summary, dt, creator in (
            (cls.test_record, "Summary Today'", cls.dt_reference, cls.user_employee),
            (cls.test_record_2, "Summary Tomorrow'", cls.dt_reference + timedelta(days=1), cls.user_employee),
            (cls.test_lead_records[0], "Summary Today'", cls.dt_reference, cls.user_employee),
            (cls.test_lead_records[1], "Summary Tomorrow'", cls.dt_reference + timedelta(days=1), cls.user_employee),
            (cls.test_lead_records[2], "Summary Tomorrow'", cls.dt_reference + timedelta(days=1), cls.user_employee),
            (cls.test_lead_records[3], "Summary Tomorrow'", cls.dt_reference + timedelta(days=1), cls.user_admin),
        ):
            cls.test_activities += record.with_user(creator).activity_schedule(
                "test_mail.mail_act_test_todo_generic",
                date_deadline=dt.date(),
                summary=summary,
                user_id=cls.user_employee.id,
            )
        cls.test_lead_activities = cls.test_activities[2:]
        cls.test_activities_removed = cls.deleted_record.activity_ids
        cls.test_activities_company_2 = cls.test_lead_records[3].activity_ids

        # add atttachments on lead-like test records
        cls.lead_act_attachments = cls.env['ir.attachment'].create(
            cls._generate_attachments_data(1, 'mail.activity', cls.test_lead_activities[-4]) +
            cls._generate_attachments_data(1, 'mail.activity', cls.test_lead_activities[-3]) +
            cls._generate_attachments_data(1, 'mail.activity', cls.test_lead_activities[-2]) +
            cls._generate_attachments_data(1, 'mail.activity', cls.test_lead_activities[-1])
        )

        # In the mean time, some FK deletes the record where the message is
        # scheduled, skipping its unlink() override
        cls.env.cr.execute(
            f"DELETE FROM {cls.test_lead_records._table} WHERE id = %s", (cls.deleted_record.id,)
        )
        cls.env.invalidate_all()

    @users("employee")
    def test_systray_activities_for_various_records(self):
        """Check that activities made on archived or not archived records, as
        well as on removed record, to check systray activities behavior and
        robustness. """
        # archive record 1
        self.test_record.action_archive()
        self.assertFalse(self.test_activities[0].exists())

        self.authenticate(self.user_employee.login, self.user_employee.login)
        with freeze_time(self.dt_reference):
            groups_data = self.make_jsonrpc_request("/mail/data", {"systray_get_activities": True}).get('Store', {}).get('activityGroups', [])
        self.assertEqual(len(groups_data), 3, 'Should have activities for 2 test models + generic for non accessible')

        for model_name, msg, (exp_total, exp_today, exp_planned, exp_overdue) in [
            ('mail.activity', 'Archiving removes activities', (0, 0, 2, 0)),
            (self.test_record._name, 'Archiving removes activities', (0, 0, 1, 0)),
            (self.test_lead_records._name, 'Planned do not count in total', (1, 1, 1, 0)),
        ]:
            with self.subTest(model_name=model_name, msg=msg):
                group_values = next(values for values in groups_data if values['model'] == model_name)
                self.assertEqual(group_values['total_count'], exp_total)
                self.assertEqual(group_values['today_count'], exp_today)
                self.assertEqual(group_values['planned_count'], exp_planned)
                self.assertEqual(group_values['overdue_count'], exp_overdue)

        # check search results with removed records
        self.env.invalidate_all()
        test_with_removed = self.env['mail.activity'].sudo().search([
            ('id', 'in', self.test_activities.ids),
            ('res_model', '=', self.test_lead_records._name),
        ])
        self.assertEqual(len(test_with_removed), 4, 'Without ACL check, activities linked to removed records are kept')

        self.env.invalidate_all()
        test_with_removed_as_admin = self.env['mail.activity'].with_user(self.user_admin).search([
            ('id', 'in', self.test_activities.ids),
            ('res_model', '=', self.test_lead_records._name),
        ])
        self.assertEqual(len(test_with_removed_as_admin), 3, 'With ACL check, activities linked to removed records are not kept is not assigned to the user')

        self.env.invalidate_all()
        self.assertFalse(
            self.test_activities_removed.with_user(self.user_admin).has_access('read'),
            'No access to an activity linked to someone and whose record has been removed '
            '(considered as no access to record); and should not crash (no MissingError)'
        )
        with self.assertRaises(exceptions.AccessError):  # should not raise a MissingError
            self.test_activities_removed.with_user(self.user_admin).read(['summary'])

        self.env.invalidate_all()
        test_with_removed = self.env['mail.activity'].search([
            ('id', 'in', self.test_activities.ids),
            ('res_model', '=', self.test_lead_records._name),
        ])
        self.assertEqual(len(test_with_removed), 4, 'Even with ACL check, activities linked to removed records are kept if assigned to the user (see odoo/odoo#112126)')

        # if not assigned -> should filter out
        self.env.invalidate_all()
        self.test_activities_removed.write({'user_id': self.user_admin.id})
        test_with_removed = self.env['mail.activity'].search([
            ('id', 'in', self.test_activities.ids),
            ('res_model', '=', self.test_lead_records._name),
        ])
        self.assertEqual(len(test_with_removed), 3, 'With ACL check, activities linked to removed records are not kept if assigned to the another user')
        self.test_activities_removed.write({'user_id': self.user_employee.id})

        # be sure activities on removed records do not crash when managed, and that
        # lost attachments are removed as well
        self.env.invalidate_all()
        lead_activities = self.test_lead_activities.with_user(self.user_employee)
        lead_act_attachments = self.lead_act_attachments.with_user(self.user_employee)
        self.assertEqual(len(lead_activities), 4, 'Simulate UI where activities are still displayed even if record removed')
        self.assertEqual(len(lead_act_attachments), 4, 'Simulate UI where activities are still displayed even if record removed')
        messages, _next_activities = lead_activities._action_done()
        self.assertEqual(len(messages), 3, 'Should have posted one message / live record')
        self.assertFalse(lead_activities.exists(), 'Mark done should unlink activities')
        self.assertEqual(
            set(lead_act_attachments.exists().mapped('res_id')), set(messages.ids),
            'Mark done should clean up attachments linked to removed record, and linked other attachments to messages')
        self.assertEqual(
            set(lead_act_attachments.exists().mapped('res_model')), set(['mail.message'] * 2))

    @users("employee")
    def test_systray_activities_multi_company(self):
        """ Explicitly check MC support, as well as allowed_company_ids, that
        limits visible records in a given session, should impact systray activities. """
        self.user_employee.write({'company_ids': [(4, self.company_2.id)]})

        self.authenticate(self.user_employee.login, self.user_employee.login)
        with freeze_time(self.dt_reference):
            groups_data = self.make_jsonrpc_request("/mail/data", {"systray_get_activities": True}).get('Store', {}).get('activityGroups', [])

        for model_name, msg, (exp_total, exp_today, exp_planned, exp_overdue) in [
            ('mail.activity', 'Non accessible: deleted', (0, 0, 1, 0)),
            (self.test_record._name, 'Archiving removes activities', (1, 1, 1, 0)),
            (self.test_lead_records._name, 'Accessible (MC with all companies)', (1, 1, 2, 0)),
        ]:
            with self.subTest(model_name=model_name, msg=msg):
                group_values = next(values for values in groups_data if values['model'] == model_name)
                self.assertEqual(group_values['total_count'], exp_total)
                self.assertEqual(group_values['today_count'], exp_today)
                self.assertEqual(group_values['planned_count'], exp_planned)
                self.assertEqual(group_values['overdue_count'], exp_overdue)
                if model_name == 'mail.activity':  # for mail.activity, there is a key with activities we can check
                    self.assertEqual(sorted(group_values['activity_ids']), sorted(self.test_activities_removed.ids))

        # when allowed companies restrict visible records, linked activities are
        # removed from systray, considering you have to log into the right company
        # to see them (change in 18+)
        with freeze_time(self.dt_reference):
            groups_data = self.make_jsonrpc_request("/mail/data", {
                "systray_get_activities": True,
                "context": {"allowed_company_ids": self.company_admin.ids},
            }).get('Store', {}).get('activityGroups', [])

        for model_name, msg, (exp_total, exp_today, exp_planned, exp_overdue) in [
            ('mail.activity', 'Non accessible: deleted (MC ignored, stripped out like inaccessible records)', (0, 0, 1, 0)),
            (self.test_record._name, 'Archiving removes activities', (1, 1, 1, 0)),
            (self.test_lead_records._name, 'Accessible', (1, 1, 1, 0)),
        ]:
            with self.subTest(model_name=model_name, msg=msg):
                group_values = next(values for values in groups_data if values['model'] == model_name)
                self.assertEqual(group_values['total_count'], exp_total)
                self.assertEqual(group_values['today_count'], exp_today)
                self.assertEqual(group_values['planned_count'], exp_planned)
                self.assertEqual(group_values['overdue_count'], exp_overdue)
                if model_name == 'mail.activity':  # for mail.activity, there is a key with activities we can check
                    self.assertEqual(sorted(group_values['activity_ids']), sorted(self.test_activities_removed.ids))

        # now not having accessible to company 2 records: tread like forbidden
        self.user_employee.write({'company_ids': [(3, self.company_2.id)]})
        with freeze_time(self.dt_reference):
            groups_data = self.make_jsonrpc_request("/mail/data", {
                "systray_get_activities": True,
                "context": {"allowed_company_ids": self.company_admin.ids},
            }).get('Store', {}).get('activityGroups', [])

        for model_name, msg, (exp_total, exp_today, exp_planned, exp_overdue) in [
            ('mail.activity', 'Non accessible: deleted + company error managed like forbidden record', (0, 0, 2, 0)),
            (self.test_record._name, 'Archiving removes activities', (1, 1, 1, 0)),
            (self.test_lead_records._name, 'Accessible', (1, 1, 1, 0)),
        ]:
            with self.subTest(model_name=model_name, msg=msg):
                group_values = next(values for values in groups_data if values['model'] == model_name)
                self.assertEqual(group_values['total_count'], exp_total)
                self.assertEqual(group_values['today_count'], exp_today)
                self.assertEqual(group_values['planned_count'], exp_planned)
                self.assertEqual(group_values['overdue_count'], exp_overdue)
                if model_name == 'mail.activity':  # for mail.activity, there is a key with activities we can check
                    self.assertEqual(sorted(group_values['activity_ids']), sorted((self.test_activities_removed + self.test_activities_company_2).ids))


@tests.tagged('mail_activity')
@freeze_time("2024-01-01 09:00:00")
class TestActivitySystrayBusNotify(TestActivityCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_employee_2 = cls.user_employee.copy(default={'login': "employee_2"})

        cls.activity_vals = [
            {
                'res_model_id': cls.env['ir.model']._get_id(cls.test_record._name),
                'res_id': cls.test_record.id,
                'date_deadline': dt,
                'user_id': cls.user_employee.id,
            } | extra
            for dt, extra in zip(
                (datetime(2023, 12, 31, 15, 0, 0), datetime(2023, 12, 31, 15, 0, 0), datetime(2024, 1, 1, 15, 0, 0), datetime(2024, 1, 2, 15, 0, 0)),
                ({'active': False}, {}, {}, {}),
            )
        ]

    @users('employee')
    def test_notify_create_unlink_activities(self):
        """Check creating and unlinking activities notifies of the change in 'to be done' activity count per user."""
        users = self.env.user + self.user_employee_2

        expected_create_notifs = [
            ([(self.env.cr.dbname, user.partner_id._name, user.partner_id.id)], [{
                "type": "mail.activity/updated",
                "payload": {
                    "activity_created": True,
                    "count_diff": 2,
                },
            }])
            for user in users
        ]
        expected_unlink_notifs = [
            ([(self.env.cr.dbname, user.partner_id._name, user.partner_id.id)], [{
                "type": "mail.activity/updated",
                "payload": {
                    "activity_deleted": True,
                    "count_diff": -2,
                },
            }])
            for user in users
        ]
        for (
            user,
            (expected_create_notif_channels, expected_create_notif_message_items),
            (expected_unlink_notif_channels, expected_unlink_notif_message_items),
        ) in zip(users, expected_create_notifs, expected_unlink_notifs):
            user_activity_vals = [vals | {'user_id': user.id} for vals in self.activity_vals]
            with self.assertBus(expected_create_notif_channels, expected_create_notif_message_items):
                activities = self.env['mail.activity'].create(user_activity_vals)
            self._reset_bus()
            with self.assertBus(expected_unlink_notif_channels, expected_unlink_notif_message_items):
                activities.unlink()

    @users('employee')
    def test_notify_update_activities(self):
        write_vals_all = [
            # added to counter for employee 2, removed from counter for current employee
            {'user_id': self.user_employee_2.id},
            {'user_id': self.user_employee_2.id, 'date_deadline': datetime(2023, 12, 31, 15, 0, 0), 'active': True},
            # just notify
            {'date_deadline': datetime(2024, 1, 2, 15, 0, 0)},  # everything is in the future -> all removed from counter
            {'date_deadline': datetime(2023, 12, 31, 15, 0, 0)},  # everything is in the past -> the one from the future is added
            {'active': False},  # everything is archived -> all removed from counter
            {'active': True},  # the archived one is unarchived -> added to counter
            {},  # no "to be done" count change -> no notif
            [{'date_deadline': datetime(2024, 1, 2, 15, 0, 0), 'active': True}, {}, {}, {}],
        ]

        expected_notifs = [
            # transfer 4 activities to the second employee, 2 todos taken and 2 given
            [
                ([(self.env.cr.dbname, user.partner_id._name, user.partner_id.id)], [{
                    "type": "mail.activity/updated",
                    "payload": {
                        "count_diff": count_diff,
                    } | ({"activity_created": True} if count_diff > 0 else {"activity_deleted": True}),
                }])
                for user, count_diff
                in zip(self.user_employee + self.user_employee_2, [-2, 2])
            ],
            # transfer 4 activities to the second employee, 2 todos are taken and 4 are given
            [
                ([(self.env.cr.dbname, user.partner_id._name, user.partner_id.id)], [{
                    "type": "mail.activity/updated",
                    "payload": {
                        "count_diff": count_diff,
                    } | ({"activity_created": True} if count_diff > 0 else {"activity_deleted": True}),
                }])
                for user, count_diff
                in zip(self.user_employee + self.user_employee_2, [-2, 4])
            ],
        ] + [[
                ([(self.env.cr.dbname, self.user_employee.partner_id._name, self.user_employee.partner_id.id)], [{
                    "type": "mail.activity/updated",
                    "payload": {
                        "count_diff": count_diff,
                    } | ({"activity_created": True} if count_diff > 0 else {"activity_deleted": True}),
                }])
            ] for count_diff in (-2, 1, -2, 1)
        ] + [
            [([], [])],  # no change -> no notif
            [([], [])],  # no change in "todo" count -> no notif
        ]
        for write_vals, expected_notif_vals in zip(write_vals_all, expected_notifs):
            with self.subTest(vals=write_vals):
                _past_archived, _past_active, _today, _tomorrow = activities = self.env['mail.activity'].create(self.activity_vals)
                self._reset_bus()
                if isinstance(write_vals, list):
                    for activity, vals in zip(activities, write_vals):
                        activity.write(vals)
                else:
                    activities.write(write_vals)
                for (notif_channels, notif_messages) in expected_notif_vals:
                    self.assertBusNotifications(notif_channels, notif_messages)
                activities.unlink()


@tests.tagged('mail_activity')
class TestActivityViewHelpers(TestActivityCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.type_todo = cls.env.ref('test_mail.mail_act_test_todo')
        cls.type_call = cls.env.ref('test_mail.mail_act_test_call')
        cls.type_upload = cls.env.ref('test_mail.mail_act_test_upload_document')
        cls.user_employee_2 = mail_new_test_user(
            cls.env,
            name='Employee2',
            login='employee2',
        )
        cls.attachment_1, cls.attachment_2 = cls.env['ir.attachment'].create([{
            'name': f"Uploaded doc_{idx + 1}",
            'raw': b'bar',
            'res_model': cls.test_record_2._name,
            'res_id': cls.test_record_2.id,
        } for idx in range(2)])
        cls.upload_type = cls.env.ref('test_mail.mail_act_test_upload_document')
        cls.upload_type.sudo().keep_done = True
        cls.user_employee.tz = cls.user_admin.tz

    @freeze_time("2023-10-18 06:00:00")
    def test_get_activity_data(self):
        get_activity_data = self.env['mail.activity'].get_activity_data
        with self.with_user('employee'):
            # Setup activities: 3 for the first record, 2 "done" and 2 ongoing for the second
            test_record, test_record_2 = self.env['mail.test.activity'].browse(
                (self.test_record + self.test_record_2).ids
            )
            now_utc = datetime.now(pytz.UTC)
            now_user = now_utc.astimezone(pytz.timezone(self.env.user.tz or 'UTC'))
            today_user = now_user.date()

            for days, user_id in ((-1, self.user_employee_2), (0, self.user_employee), (1, self.user_admin)):
                test_record.activity_schedule(
                    'test_mail.mail_act_test_upload_document',
                    today_user + relativedelta(days=days),
                    user_id=user_id.id)
            for days, user_id in ((-2, self.user_admin), (0, self.user_employee), (2, self.user_employee_2),
                                  (3, self.user_admin)):
                test_record_2.activity_schedule(
                    'test_mail.mail_act_test_upload_document',
                    today_user + relativedelta(days=days),
                    user_id=user_id.id)
            record_activities = test_record.activity_ids
            record_2_activities = test_record_2.activity_ids
            record_2_activities[0].action_feedback(feedback='Done', attachment_ids=self.attachment_1.ids)
            record_2_activities[1].action_feedback(feedback='Done', attachment_ids=self.attachment_2.ids)

            # Check get activity data
            activity_data = get_activity_data('mail.test.activity', None, fetch_done=True)
            self.assertEqual(activity_data['activity_res_ids'], [test_record.id, test_record_2.id])
            self.assertDictEqual(
                next((t for t in activity_data['activity_types'] if t['id'] == self.upload_type.id), {}),
                {
                    'id': self.upload_type.id,
                    'name': 'Upload Document',
                    'template_ids': [],
                    'keep_done': True,
                })

            grouped = activity_data['grouped_activities'][test_record.id][self.upload_type.id]
            grouped['ids'] = set(grouped['ids'])  # ids order doesn't matter
            self.assertDictEqual(grouped, {
                'state': 'overdue',
                'count_by_state': {'overdue': 1, 'planned': 1, 'today': 1},
                'ids': set(record_activities.ids),
                'reporting_date': record_activities[0].date_deadline,
                'user_assigned_ids': record_activities.user_id.ids,
            })

            grouped = activity_data['grouped_activities'][test_record_2.id][self.upload_type.id]
            grouped['ids'] = set(grouped['ids'])
            self.assertDictEqual(grouped, {
                'state': 'planned',
                'count_by_state': {'done': 2, 'planned': 2},
                'ids': set(record_2_activities.ids),
                'reporting_date': record_2_activities[2].date_deadline,
                'user_assigned_ids': record_2_activities[2:].user_id.ids,
                'attachments_info': {
                    'count': 2, 'most_recent_id': self.attachment_2.id, 'most_recent_name': 'Uploaded doc_2'}
            })

            # Mark all first record activities as "done" and check activity data
            record_activities.action_feedback(feedback='Done', attachment_ids=self.attachment_1.ids)
            self.assertEqual(record_activities[2].date_done, date.today())  # Thanks to freeze_time
            activity_data = get_activity_data('mail.test.activity', None, fetch_done=True)
            grouped = activity_data['grouped_activities'][test_record.id][self.upload_type.id]
            grouped['ids'] = set(grouped['ids'])
            self.assertDictEqual(grouped, {
                'state': 'done',
                'count_by_state': {'done': 3},
                'ids': set(record_activities.ids),
                'reporting_date': record_activities[2].date_done,
                'user_assigned_ids': [],
                'attachments_info': {
                    'count': 1,  # 1 instead of 3 because all attachments are the same one
                    'most_recent_id': self.attachment_1.id,
                    'most_recent_name': self.attachment_1.name,
                }
            })
            self.assertEqual(activity_data['activity_res_ids'], [test_record_2.id, test_record.id])

            # Check filters (domain, pagination and fetch_done)
            self.assertEqual(
                get_activity_data('mail.test.activity', domain=[('id', 'in', test_record.ids)],
                                  fetch_done=True)['activity_res_ids'],
                [test_record.id])
            self.assertEqual(get_activity_data('mail.test.activity', None, fetch_done=False)['activity_res_ids'],
                             [test_record_2.id])
            # Note that the records are ordered by ids not by deadline (so we get the "wrong" order)
            self.assertEqual(
                get_activity_data('mail.test.activity', None, offset=1, fetch_done=True)['activity_res_ids'],
                [test_record_2.id])
            self.assertEqual(
                get_activity_data('mail.test.activity', None, limit=1, fetch_done=True)['activity_res_ids'],
                [test_record.id])

            # Unset keep done and check activity data: record with only "done" activities must not be returned
            self.upload_type.sudo().keep_done = False
            activity_data = get_activity_data('mail.test.activity', None, fetch_done=True)
            self.assertDictEqual(
                next((t for t in activity_data['activity_types'] if t['id'] == self.upload_type.id), {}),
                {
                    'id': self.upload_type.id,
                    'name': 'Upload Document',
                    'template_ids': [],
                    'keep_done': False,
                })
            self.assertEqual(activity_data['activity_res_ids'], [test_record_2.id])

            # Unarchiving activities should restore the activity
            record_activities.action_unarchive()
            self.assertFalse(any(act.date_done for act in record_activities))
            self.assertTrue(all(act.date_deadline for act in record_activities))
            self.upload_type.sudo().keep_done = True
            activity_data = get_activity_data('mail.test.activity', None, fetch_done=True)
            grouped = activity_data['grouped_activities'][test_record.id][self.upload_type.id]
            self.assertEqual(grouped['state'], 'overdue')
            self.assertEqual(grouped['count_by_state'], {'overdue': 1, 'planned': 1, 'today': 1})
            self.assertEqual(grouped['reporting_date'], record_activities[0].date_deadline)
            self.assertEqual(activity_data['activity_res_ids'], [test_record.id, test_record_2.id])
            grouped['ids'] = set(grouped['ids'])
            self.assertDictEqual(grouped, {
                'state': 'overdue',
                'count_by_state': {'overdue': 1, 'planned': 1, 'today': 1},
                'ids': set(record_activities.ids),
                'reporting_date': record_activities[0].date_deadline,
                'user_assigned_ids': record_activities.user_id.ids,
            })


@tests.tagged('mail_activity')
class TestORM(TestActivityCommon):
    """Test for read_progress_bar"""

    def test_week_grouping(self):
        """The labels associated to each record in read_progress_bar should match
        the ones from read_group, even in edge cases like en_US locale on sundays
        """
        MailTestActivityCtx = self.env['mail.test.activity'].with_context({"lang": "en_US"})

        # Don't mistake fields date and date_deadline:
        # * date is just a random value
        # * date_deadline defines activity_state
        with freeze_time("2024-09-24 10:00:00"):
            self.env['mail.test.activity'].create({
                'date': '2021-05-02',
                'name': "Yesterday, all my troubles seemed so far away",
            }).activity_schedule(
                'test_mail.mail_act_test_todo',
                summary="Make another test super asap (yesterday)",
                date_deadline=fields.Date.context_today(MailTestActivityCtx) - timedelta(days=7),
            )
            self.env['mail.test.activity'].create({
                'date': '2021-05-09',
                'name': "Things we said today",
            }).activity_schedule(
                'test_mail.mail_act_test_todo',
                summary="Make another test asap",
                date_deadline=fields.Date.context_today(MailTestActivityCtx),
            )
            self.env['mail.test.activity'].create({
                'date': '2021-05-16',
                'name': "Tomorrow Never Knows",
            }).activity_schedule(
                'test_mail.mail_act_test_todo',
                summary="Make a test tomorrow",
                date_deadline=fields.Date.context_today(MailTestActivityCtx) + timedelta(days=7),
            )

            domain = [('date', "!=", False)]
            groupby = "date:week"
            progress_bar = {
                'field': 'activity_state',
                'colors': {
                    "overdue": 'danger',
                    "today": 'warning',
                    "planned": 'success',
                }
            }

            # call read_group to compute group names
            groups = MailTestActivityCtx.read_group(domain, fields=['date'], groupby=[groupby])
            progressbars = MailTestActivityCtx.read_progress_bar(domain, group_by=groupby, progress_bar=progress_bar)
            self.assertEqual(len(groups), 3)
            self.assertEqual(len(progressbars), 3)

        # format the read_progress_bar result to get a dictionary under this
        # format: {activity_state: group_name}; the original format
        # (after read_progress_bar) is {group_name: {activity_state: count}}
        pg_groups = {
            next(state for state, count in data.items() if count): group_name
            for group_name, data in progressbars.items()
        }

        self.assertEqual(groups[0][groupby], pg_groups["overdue"])
        self.assertEqual(groups[1][groupby], pg_groups["today"])
        self.assertEqual(groups[2][groupby], pg_groups["planned"])


@tests.tagged('post_install', '-at_install')
class TestTours(HttpCase):
    def test_activity_view_data_with_offset(self):
        self.patch(MailTestActivity, '_order', 'date desc, id desc')
        MailTestActivityModel = self.env['mail.test.activity']
        MailTestActivityCtx = MailTestActivityModel.with_context({"lang": "en_US"})
        MailTestActivityModel.create({
            'date': '2021-05-02',
            'name': "Task 1",
        }).activity_schedule(
            'test_mail.mail_act_test_todo',
            summary="Activity 1",
            date_deadline=fields.Date.context_today(MailTestActivityCtx) - timedelta(days=7),
        )
        MailTestActivityModel.create({
            'date': '2021-05-16',
            'name': "Task 1 without activity",
        })
        MailTestActivityModel.create({
            'date': '2021-05-09',
            'name': "Task 2",
        }).activity_schedule(
            'test_mail.mail_act_test_todo',
            summary="Activity 2",
            date_deadline=fields.Date.context_today(MailTestActivityCtx),
        )
        MailTestActivityModel.create({
            'date': '2021-05-16',
            'name': "Task 3",
        }).activity_schedule(
            'test_mail.mail_act_test_todo',
            summary="Activity 3",
            date_deadline=fields.Date.context_today(MailTestActivityCtx) + timedelta(days=7),
        )
        MailTestActivityModel.create({
            'date': '2021-05-16',
            'name': "Task 2 without activity",
        })

        self.env["ir.ui.view"].create({
            "name": "Test Activity View",
            "model": "mail.test.activity",
            "type": 'activity',
            "arch": """
                <activity string="OrderedMailTestActivity">
                    <templates>
                        <div t-name="activity-box">
                            <field name="name"/>
                        </div>
                    </templates>
                </activity>
            """,
        })
        self.start_tour(
            "/odoo?debug=1",
            "mail_activity_view",
            login="admin",
        )
