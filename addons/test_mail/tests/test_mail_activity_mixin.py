from datetime import date, datetime, timedelta, timezone
from dateutil.relativedelta import relativedelta
from freezegun import freeze_time
from unittest.mock import patch

import pytz
import random

from odoo import fields, tests
from odoo.addons.mail.models.mail_activity import MailActivity
from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.test_mail.tests.test_mail_activity import TestActivityCommon
from odoo.tests import tagged, users
from odoo.tools import mute_logger


@tagged('mail_activity', 'mail_activity_mixin')
class TestActivityMixin(TestActivityCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

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
            self.assertEqual(len(self.test_record.message_ids), 1)
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
                today_user + relativedelta(days=-1),
                user_id=self.user_employee.id,
            )
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
                user_id=self.user_employee.id,
            )
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
                feedback='Test feedback',
            )
            self.assertEqual(self.test_record.activity_ids, act2 | act3)
            self.assertFalse(act1.active)

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
            self.assertFalse(act3.active)

            # Setting activities as done should delete them and post messages
            self.assertEqual(self.test_record.activity_ids, act2)
            self.assertEqual(len(self.test_record.message_ids), 3)
            act_messages = self.test_record.message_ids[:2]
            self.assertEqual(act_messages.subtype_id, self.env.ref('mail.mt_activities'))

            # Unlink meeting activities
            self.test_record.activity_unlink(['test_mail.mail_act_test_meeting'])

            # Canceling activities should simply remove them
            self.assertEqual(self.test_record.activity_ids, self.env['mail.activity'])
            self.assertEqual(len(self.test_record.message_ids), 3)
            self.assertFalse(self.test_record.activity_state)
            self.assertFalse(act2.exists())

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_activity_mixin_not_only_automated(self):

        # Schedule activity and create manual activity
        act_type_todo = self.env.ref('test_mail.mail_act_test_todo')
        auto_act = self.test_record.activity_schedule(
            'test_mail.mail_act_test_todo',
            date_deadline=date.today() + relativedelta(days=1),
        )
        man_act = self.env['mail.activity'].create({
            'activity_type_id': act_type_todo.id,
            'res_id': self.test_record.id,
            'res_model_id': self.env['ir.model']._get_id(self.test_record._name),
            'date_deadline': date.today() + relativedelta(days=1)
        })
        self.assertEqual(auto_act.automated, True)
        self.assertEqual(man_act.automated, False)

        # Test activity reschedule on not only automated activities
        self.test_record.activity_reschedule(
            ['test_mail.mail_act_test_todo'],
            date_deadline=date.today() + relativedelta(days=2),
            only_automated=False
        )
        self.assertEqual(auto_act.date_deadline, date.today() + relativedelta(days=2))
        self.assertEqual(man_act.date_deadline, date.today() + relativedelta(days=2))

        # Test activity feedback on not only automated activities
        self.test_record.activity_feedback(
            ['test_mail.mail_act_test_todo'],
            feedback='Test feedback',
            only_automated=False
        )
        self.assertEqual(self.test_record.activity_ids, self.env['mail.activity'])
        self.assertFalse(auto_act.active)
        self.assertFalse(man_act.active)

        # Test activity unlink on not only automated activities
        auto_act = self.test_record.activity_schedule(
            'test_mail.mail_act_test_todo',
        )
        man_act = self.env['mail.activity'].create({
            'activity_type_id': act_type_todo.id,
            'res_id': self.test_record.id,
            'res_model_id': self.env['ir.model']._get_id(self.test_record._name)
        })
        self.test_record.activity_unlink(['test_mail.mail_act_test_todo'], only_automated=False)
        self.assertEqual(self.test_record.activity_ids, self.env['mail.activity'])
        self.assertFalse(auto_act.exists())
        self.assertFalse(man_act.exists())

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_activity_mixin_archive(self):
        rec = self.test_record.with_user(self.user_employee)
        new_act = rec.activity_schedule(
            'test_mail.mail_act_test_todo',
            user_id=self.user_admin.id,
        )
        self.assertEqual(rec.activity_ids, new_act)
        rec.action_archive()
        self.assertEqual(rec.active, False)
        self.assertEqual(rec.activity_ids, new_act)
        rec.action_unarchive()
        self.assertEqual(rec.active, True)
        self.assertEqual(rec.activity_ids, new_act)

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
        archived_users = self.env['res.users'].browse(x.id for x in random.sample(test_users, 2))  # pick 2 users to archive
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
        self.assertFalse(first_activity.active)

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
        self.assertFalse(first_activity.active)

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
        record = self.env['mail.test.activity'].create({'name': 'Record'})

        with freeze_time(datetime(2020, 1, 1, 16)):
            today_utc = datetime.today()
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

        # Create some records without activity schedule on it for testing
        self.env['mail.test.activity'].create([
            {'name': 'Record %i' % record_i}
            for record_i in range(5)
        ])

        origin_1, origin_2 = self.env['mail.test.activity'].search([], limit=2)
        activity_type = self.env.ref('test_mail.mail_act_test_todo')

        with freeze_time(datetime(2020, 1, 1, 16)):
            today_utc = datetime.today()
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

            result = self.env['mail.test.activity'].search([('activity_state', 'not in', ('today'))])
            self.assertTrue(len(result) > 0)
            self.assertEqual(result, all_activity_mixin_record.filtered(lambda p: p.activity_state != 'today'))

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
            read_group_params = {
                'domain': [('id', 'in', (origin_1 | origin_2).ids)],
                'groupby': ['activity_state'],
                'aggregates': ['__count'],
            }
            self.assertEqual(Model.search(**search_params), origin_1)
            self.assertEqual(
                {(e['activity_state'], e['__count']) for e in Model.formatted_read_group(**read_group_params)},
                {('today', 1), ('overdue', 1)})
            origin_1_activity_2.action_feedback(feedback='Done')
            self.assertFalse(Model.search(**search_params))
            self.assertEqual(
                {(e['activity_state'], e['__count']) for e in Model.formatted_read_group(**read_group_params)},
                {('today', 2)})

    @mute_logger('odoo.addons.mail.models.mail_mail', 'odoo.tests')
    def test_mail_activity_mixin_search_state_different_day_but_close_time(self):
        """Test the case where there's less than 24 hours between the deadline and now_tz,
        but one day of difference (e.g. 23h 01/01/2020 & 1h 02/02/2020). So the state
        should be "planned" and not "today". This case was tricky to implement in SQL
        that's why it has its own test.
        """

        # Create some records without activity schedule on it for testing
        self.env['mail.test.activity'].create([
            {'name': 'Record %i' % record_i}
            for record_i in range(5)
        ])

        origin_1 = self.env['mail.test.activity'].search([], limit=1)

        with freeze_time(datetime(2020, 1, 1, 23)):
            today_utc = datetime.today()
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
        act1 = test_record.activity_schedule(summary='Active', user_id=self.env.uid)
        act2 = test_record.activity_schedule(summary='Archived', active=False, user_id=self.env.uid)
        test_record.unlink()
        self.assertFalse((act1 + act2).exists(), 'Removing records should remove activities, even archived')

    @users('employee')
    def test_record_unlinked_orphan_activities(self):
        """Test the fix preventing error on corrupted database where activities without related record are present."""
        test_record = self.env['mail.test.activity'].with_context(
            self._test_context).create({'name': 'Test'}).with_user(self.user_employee)
        act = test_record.activity_schedule("test_mail.mail_act_test_todo", summary='Orphan activity')
        act.action_done()
        # Delete the record while preventing the cascade deletion of the activity to simulate a corrupted database
        with patch.object(MailActivity, 'unlink', lambda self: None):
            test_record.unlink()
        self.assertTrue(act.exists())
        self.assertFalse(act.sudo().active)
        self.assertFalse(test_record.exists())
        self.assertFalse(self.env['mail.activity'].with_user(self.user_admin).with_context(active_test=False).search(
            [('active', '=', False)]))


@tests.tagged('mail_activity', 'mail_activity_mixin')
class TestORM(TestActivityCommon):
    """Test for read_progress_bar"""

    def test_groupby_activity_state_progress_bar_behavior(self):
        """ Test activity_state groupby logic on mail.test.lead when 'activity_state'
        is present multiple times in the groupby field list. """
        lead_timedelta_setup = [0, 0, -2, -2, -2, 2]

        leads = self.env["mail.test.lead"].create([
            {"name": f"CRM Lead {i}"}
            for i in range(1, len(lead_timedelta_setup) + 1)
        ])

        with freeze_time("2025-05-21 10:00:00"):
            self.env["mail.activity"].create([
                {
                    "date_deadline": datetime.now(timezone.utc) + timedelta(days=delta_days),
                    "res_id": lead.id,
                    "res_model_id": self.env["ir.model"]._get_id("mail.test.lead"),
                    "summary": f"Test activity for CRM lead {lead.id}",
                    "user_id": self.env.user.id,
                } for lead, delta_days in zip(leads, lead_timedelta_setup)
            ])

            # grouping by 'activity_state' and 'activity_state' as the progress bar
            domain = [("name", "!=", "")]
            groupby = "activity_state"
            progress_bar = {
                "field": "activity_state",
                "colors": {
                    "overdue": "danger",
                    "today": "warning",
                    "planned": "success",
                },
            }
            progressbars = self.env["mail.test.lead"].read_progress_bar(
                domain=domain, group_by=groupby, progress_bar=progress_bar,
            )

            self.assertEqual(len(progressbars), 3)
            expected_progressbars = {
                "overdue": {"overdue": 3, "today": 0, "planned": 0},
                "today": {"overdue": 0, "today": 2, "planned": 0},
                "planned": {"overdue": 0, "today": 0, "planned": 1},
            }
            self.assertEqual(dict(progressbars), expected_progressbars)

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
                user_id=self.env.uid,
            )
            self.env['mail.test.activity'].create({
                'date': '2021-05-09',
                'name': "Things we said today",
            }).activity_schedule(
                'test_mail.mail_act_test_todo',
                summary="Make another test asap",
                date_deadline=fields.Date.context_today(MailTestActivityCtx),
                user_id=self.env.uid,
            )
            self.env['mail.test.activity'].create({
                'date': '2021-05-16',
                'name': "Tomorrow Never Knows",
            }).activity_schedule(
                'test_mail.mail_act_test_todo',
                summary="Make a test tomorrow",
                date_deadline=fields.Date.context_today(MailTestActivityCtx) + timedelta(days=7),
                user_id=self.env.uid,
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
            groups = MailTestActivityCtx.formatted_read_group(domain, groupby=[groupby])
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

        self.assertEqual(groups[0][groupby][0], pg_groups["overdue"])
        self.assertEqual(groups[1][groupby][0], pg_groups["today"])
        self.assertEqual(groups[2][groupby][0], pg_groups["planned"])
