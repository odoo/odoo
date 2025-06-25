# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
from psycopg2 import IntegrityError
from unittest.mock import patch
from unittest.mock import DEFAULT

import pytz

from odoo import fields, exceptions, tests
from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.mail.tests.common_activity import ActivityScheduleCase
from odoo.addons.test_mail.models.test_mail_models import MailTestActivity
from odoo.tests import Form, HttpCase, users
from odoo.tests.common import freeze_time
from odoo.tools import mute_logger


class TestActivityCommon(ActivityScheduleCase):

    @classmethod
    def setUpClass(cls):
        super(TestActivityCommon, cls).setUpClass()
        cls.test_record, cls.test_record_2 = cls.env['mail.test.activity'].create([
            {'name': 'Test'},
            {'name': 'Test_2'},
        ])


@tests.tagged('mail_activity')
class TestActivityRights(TestActivityCommon):

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_activity_security_user_access(self):
        """ Internal user can modify assigned or created or if write on document """
        def _employee_crash(records, operation):
            """ If employee is test employee, consider they have no access on document """
            if records.env.uid == self.user_employee.id and not records.env.su:
                return records, lambda: exceptions.AccessError('Hop hop hop Ernest, please step back.')
            return DEFAULT

        act_emp_for_adm = self.test_record.with_user(self.user_employee).activity_schedule(
            'test_mail.mail_act_test_todo',
            user_id=self.user_admin.id,
        )
        act_emp_for_emp = self.test_record.with_user(self.user_employee).activity_schedule(
            'test_mail.mail_act_test_todo',
            user_id=self.user_employee.id,
        )
        act_adm_for_adm = self.test_record.with_user(self.user_admin).activity_schedule(
            'test_mail.mail_act_test_todo',
            user_id=self.user_admin.id,
        )
        act_adm_for_emp = self.test_record.with_user(self.user_admin).activity_schedule(
            'test_mail.mail_act_test_todo',
            user_id=self.user_employee.id,
        )

        for activity, can_write in [
            (act_emp_for_adm, True), (act_emp_for_emp, True),
            (act_adm_for_adm, False), (act_adm_for_emp, True),
        ]:
            with self.subTest(user=activity.user_id.name, creator=activity.create_uid.name):
                # no document access -> based on create_uid / user_id
                with patch.object(MailTestActivity, '_check_access', autospec=True, side_effect=_employee_crash):
                    activity = activity.with_user(self.user_employee)
                    self.assertEqual(activity.can_write, can_write)
                    if can_write:
                        activity.write({'summary': 'Caramba'})
                    else:
                        with self.assertRaises(exceptions.AccessError):
                            activity.write({'summary': 'Caramba'})

                # document access -> ok bypass
                activity.write({'summary': 'Caramba caramba'})

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_activity_security_user_noaccess_automated(self):
        def _employee_crash(records, operation):
            """ If employee is test employee, consider they have no access on document """
            if records.env.uid == self.user_employee.id and not records.env.su:
                return records, lambda: exceptions.AccessError('Hop hop hop Ernest, please step back.')
            return DEFAULT

        with patch.object(MailTestActivity, '_check_access', autospec=True, side_effect=_employee_crash):
            _activity = self.test_record.activity_schedule(
                'test_mail.mail_act_test_todo',
                user_id=self.user_employee.id)

            activity2 = self.test_record.activity_schedule('test_mail.mail_act_test_todo', user_id=self.user_admin.id)
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

        # can formatted_read_group activities if access to the document
        read_group_result = self.env['mail.activity'].with_user(self.user_employee).formatted_read_group(
            [('id', '=', test_activity.id)],
            ['summary'],
            ['__count'],
        )
        self.assertEqual(1, read_group_result[0]['__count'])
        self.assertEqual('Summary', read_group_result[0]['summary'])

        # cannot read_group activities if no access to the document
        with patch.object(MailTestActivity, '_check_access', autospec=True, side_effect=_employee_crash):
            with self.assertRaises(exceptions.AccessError):
                self.env['mail.activity'].with_user(self.user_employee).formatted_read_group(
                    [('id', '=', test_activity.id)],
                    ['summary'],
                    ['__count'],
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
            read_group_result = self.env['mail.activity'].with_user(self.user_employee).formatted_read_group(
                [('id', '=', test_activity.id)],
                ['summary'],
                ['__count'],
            )
            self.assertEqual(1, read_group_result[0]['__count'])
            self.assertEqual('Summary', read_group_result[0]['summary'])


@tests.tagged('mail_activity')
class TestActivityFlow(TestActivityCommon):

    def test_activity_flow_employee(self):
        with self.with_user('employee'):
            test_record = self.env['mail.test.activity'].browse(self.test_record.id)
            self.assertEqual(test_record.activity_ids, self.env['mail.activity'])

            # employee record an activity and check the deadline
            activity = self.env['mail.activity'].create({
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
            activity.action_feedback(feedback='So much feedback')
            self.assertEqual(activity.feedback, 'So much feedback')
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
        call_activity_type = ActivityType.create({'name': 'call', 'sequence': 1})
        email_activity_type = ActivityType.create({
            'name': 'email',
            'summary': 'Email Summary',
            'sequence': '30'
        })
        call_activity_type = ActivityType.create({'name': 'call', 'summary': False})
        with Form(
            self.env['mail.activity'].with_context(
                default_res_model_id=self.env['ir.model']._get_id('mail.test.activity'),
                default_res_id=self.test_record.id,
            )
        ) as ActivityForm:
            # coming from default activity type, which is to do
            self.assertEqual(ActivityForm.activity_type_id, self.env.ref("mail.mail_activity_data_todo"))
            self.assertEqual(ActivityForm.summary, "TodoSummary")
            # `res_model_id` and `res_id` are invisible, see view `mail.mail_activity_view_form_popup`
            # they must be set using defaults, see `action_feedback_schedule_next`
            ActivityForm.activity_type_id = call_activity_type
            # activity summary should be empty
            self.assertEqual(ActivityForm.summary, "TodoSummary", "Did not erase if void on type")

            ActivityForm.activity_type_id = email_activity_type
            # activity summary should be replaced with email's default summary
            self.assertEqual(ActivityForm.summary, email_activity_type.summary)

            ActivityForm.activity_type_id = call_activity_type
            # activity summary remains unchanged from change of activity type as call activity doesn't have default summary
            self.assertEqual(ActivityForm.summary, email_activity_type.summary)

    def test_activity_type_unlink(self):
        """ Removing type should allocate activities to Todo """
        email_activity_type = self.env['mail.activity.type'].create({
            'name': 'email',
            'summary': 'Email Summary',
        })
        temp_record = self.env['mail.test.activity'].create({'name': 'Test'})
        activity = temp_record.activity_schedule(
            activity_type_id=email_activity_type.id,
            user_id=self.user_employee.id,
        )
        self.assertEqual(activity.activity_type_id, email_activity_type)
        email_activity_type.unlink()
        self.assertEqual(activity.activity_type_id, self.env.ref('mail.mail_activity_data_todo'))

        # Todo is protected, niark niark
        with self.assertRaises(exceptions.UserError):
            self.env.ref('mail.mail_activity_data_todo').unlink()

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

        # document should be complete: both model and res_id
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
        # free activity is ok (no model, no res_id)
        self.env['mail.activity'].create({'user_id': self.env.uid})

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


@tests.tagged("mail_activity", "post_install", "-at_install")
class TestActivitySystray(TestActivityCommon, HttpCase):
    """Test for systray_get_activities"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.test_lead_records = cls.env['mail.test.lead'].create([
            {'name': 'Test Lead 1'},
            {'name': 'Test Lead 2'},
        ])
        cls.dt_reference = datetime(2024, 1, 15, 8, 0, 0)

        # records and leads and free activities
        # have 1 record (or activity) for today, one for tomorrow
        for record, summary, dt in (
            (cls.test_record, "Summary Today'", cls.dt_reference),
            (cls.test_record_2, "Summary Tomorrow'", cls.dt_reference + timedelta(days=1)),
            (cls.test_lead_records[0], "Summary Today'", cls.dt_reference),
            (cls.test_lead_records[1], "Summary Tomorrow'", cls.dt_reference + timedelta(days=1)),
        ):
            record.with_user(cls.user_employee).activity_schedule(
                "test_mail.mail_act_test_todo_generic",
                date_deadline=dt.date(),
                summary=summary,
                user_id=cls.user_employee.id,
            )
        for dt in (cls.dt_reference, cls.dt_reference + timedelta(days=1)):
            cls.env['mail.activity'].with_user(cls.user_employee).create({
                'date_deadline': dt,
                'summary': "Summary",
                'user_id': cls.user_employee.id,
            })

    @users("employee")
    def test_systray_activities_for_various_records(self):
        """Check that activities made on archived or not archived records, to
        check they are shown in the systray activities."""
        # archive record 1, add activities
        self.test_record.action_archive()

        self.authenticate(self.user_employee.login, self.user_employee.login)
        with freeze_time(self.dt_reference):
            data = self.make_jsonrpc_request("/mail/data", {"fetch_params": ["systray_get_activities"]})
        for model_name, msg, exp_total, exp_today, exp_planned, exp_overdue in [
            ('mail.activity', 'Free activities', 2, 2, 0, 0),
            (self.test_record._name, 'Archiving does not remove activities', 1, 1, 1, 0),
            (self.test_lead_records._name, 'Planned do not count in total', 1, 1, 1, 0),
        ]:
            with self.subTest(model_name=model_name, msg=msg):
                total_count = sum(
                    record["total_count"] for record in data["Store"]["activityGroups"]
                    if record.get("model") == model_name
                )
                today_count = sum(
                    record["today_count"] for record in data["Store"]["activityGroups"]
                    if record.get("model") == model_name
                )
                planned_count = sum(
                    record["planned_count"] for record in data["Store"]["activityGroups"]
                    if record.get("model") == model_name
                )
                overdue_count = sum(
                    record["overdue_count"] for record in data["Store"]["activityGroups"]
                    if record.get("model") == model_name
                )
                self.assertEqual(total_count, exp_total)
                self.assertEqual(today_count, exp_today)
                self.assertEqual(planned_count, exp_planned)
                self.assertEqual(overdue_count, exp_overdue)
        self.assertEqual(
            data["Store"]["activityCounter"], 4,
            '1 from lead (today), 2 from free (today), each activity=record-like, 1 from activity-test-model'
        )


@tests.tagged('mail_activity')
@freeze_time("2024-01-01 09:00:00")
class TestActivitySystrayBusNotify(TestActivityCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_employee_2 = cls.user_employee.copy(default={'login': 'employee_2', 'email': 'user_employee_2@test.lan'})

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
                                  (3, self.user_admin), (4, self.env['res.users'])):
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
                next((t for t in activity_data['activity_types'] if t['id'] == self.type_upload.id), {}),
                {
                    'id': self.type_upload.id,
                    'name': 'Document',
                    'template_ids': [],
                })

            grouped = activity_data['grouped_activities'][test_record.id][self.type_upload.id]
            grouped['ids'] = set(grouped['ids'])  # ids order doesn't matter
            self.assertDictEqual(grouped, {
                'state': 'overdue',
                'count_by_state': {'overdue': 1, 'planned': 1, 'today': 1},
                'ids': set(record_activities.ids),
                'reporting_date': record_activities[0].date_deadline,
                'user_assigned_ids': record_activities.user_id.ids,
                'summaries': [act.summary for act in record_activities],
            })

            grouped = activity_data['grouped_activities'][test_record_2.id][self.type_upload.id]
            grouped['ids'] = set(grouped['ids'])
            self.assertDictEqual(grouped, {
                'state': 'planned',
                'count_by_state': {'done': 2, 'planned': 3},  # free user is planned
                'ids': set(record_2_activities.ids),
                'reporting_date': record_2_activities[2].date_deadline,
                'user_assigned_ids': record_2_activities[2:].user_id.ids,
                'attachments_info': {
                    'count': 2, 'most_recent_id': self.attachment_2.id, 'most_recent_name': 'Uploaded doc_2'},
                'summaries': [act.summary for act in record_2_activities],
            })

            # Mark all first record activities as "done" and check activity data
            record_activities.action_feedback(feedback='Done', attachment_ids=self.attachment_1.ids)
            self.assertEqual(record_activities[2].date_done, date.today())  # Thanks to freeze_time
            activity_data = get_activity_data('mail.test.activity', None, fetch_done=True)
            grouped = activity_data['grouped_activities'][test_record.id][self.type_upload.id]
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
                },
                'summaries': [act.summary for act in record_activities],
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

            # Unarchiving activities should restore the activity
            record_activities.action_unarchive()
            self.assertFalse(any(act.date_done for act in record_activities))
            self.assertTrue(all(act.date_deadline for act in record_activities))
            activity_data = get_activity_data('mail.test.activity', None, fetch_done=True)
            grouped = activity_data['grouped_activities'][test_record.id][self.type_upload.id]
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
                'summaries': [act.summary for act in record_activities],
            })


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
            user_id=self.env.uid,
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
            user_id=self.env.uid,
        )
        MailTestActivityModel.create({
            'date': '2021-05-16',
            'name': "Task 3",
        }).activity_schedule(
            'test_mail.mail_act_test_todo',
            summary="Activity 3",
            date_deadline=fields.Date.context_today(MailTestActivityCtx) + timedelta(days=7),
            user_id=self.env.uid,
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
