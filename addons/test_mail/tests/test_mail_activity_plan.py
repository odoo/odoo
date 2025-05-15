# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from freezegun import freeze_time

from odoo import fields
from odoo.addons.mail.tests.common_activity import ActivityScheduleCase
from odoo.exceptions import ValidationError
from odoo.tests import Form, tagged, users
from odoo.tools.misc import format_date


@tagged('mail_activity', 'mail_activity_plan')
class TestActivitySchedule(ActivityScheduleCase):
    """ Test plan and activity schedule

     - activity scheduling on a single record and in batch
     - plan scheduling on a single record and in batch
     - plan creation and consistency
     """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # add some triggered and suggested next activitities
        cls.test_type_1, cls.test_type_2, cls.test_type_3 = cls.env['mail.activity.type'].create([
            {'name': 'TestAct1', 'res_model': 'mail.test.activity',},
            {'name': 'TestAct2', 'res_model': 'mail.test.activity',},
            {'name': 'TestAct3', 'res_model': 'mail.test.activity',},
        ])
        cls.test_type_1.write({
            'chaining_type': 'trigger',
            'delay_count': 2,
            'delay_from': 'current_date',
            'delay_unit': 'days',
            'triggered_next_type_id': cls.test_type_2.id,
        })
        cls.test_type_2.write({
            'chaining_type': 'suggest',
            'delay_count': 3,
            'delay_unit': 'weeks',
            'suggested_next_type_ids': [(4, cls.test_type_1.id), (4, cls.test_type_3.id)],
        })

        # prepare plans
        cls.plan_party = cls.env['mail.activity.plan'].create({
            'name': 'Test Plan A Party',
            'res_model': 'mail.test.activity',
            'template_ids': [
                (0, 0, {
                    'activity_type_id': cls.activity_type_todo.id,
                    'delay_count': 1,
                    'delay_from': 'before_plan_date',
                    'delay_unit': 'days',
                    'responsible_type': 'on_demand',
                    'sequence': 10,
                    'summary': 'Book a place',
                }), (0, 0, {
                    'activity_type_id': cls.activity_type_todo.id,
                    'delay_count': 1,
                    'delay_from': 'after_plan_date',
                    'delay_unit': 'weeks',
                    'responsible_id': cls.user_admin.id,
                    'responsible_type': 'other',
                    'sequence': 20,
                    'summary': 'Invite special guest',
                }),
            ],
        })
        cls.plan_onboarding = cls.env['mail.activity.plan'].create({
            'name': 'Test Onboarding',
            'res_model': 'mail.test.activity',
            'template_ids': [
                (0, 0, {
                    'activity_type_id': cls.activity_type_todo.id,
                    'delay_count': 3,
                    'delay_from': 'before_plan_date',
                    'delay_unit': 'days',
                    'responsible_id': cls.user_admin.id,
                    'responsible_type': 'other',
                    'sequence': 10,
                    'summary': 'Plan training',
                }), (0, 0, {
                    'activity_type_id': cls.activity_type_todo.id,
                    'delay_count': 2,
                    'delay_from': 'after_plan_date',
                    'delay_unit': 'weeks',
                    'responsible_id': cls.user_admin.id,
                    'responsible_type': 'other',
                    'sequence': 20,
                    'summary': 'Training',
                }),
            ]
        })

        # test records
        cls.reference_now = fields.Datetime.from_string('2023-09-30 14:00:00')
        cls.test_records = cls.env['mail.test.activity'].create([
            {
                'date': cls.reference_now + timedelta(days=(idx - 10)),
                'email_from': f'customer.activity.{idx}@test.example.com',
                'name': f'test_record_{idx}'
            } for idx in range(5)
        ])

        # some big dict comparisons
        cls.maxDiff = None

    @users('employee')
    def test_activity_schedule(self):
        """ Test schedule of an activity on a single or multiple records. """
        test_records_all = [self.test_records[0], self.test_records[:3]]
        # sanity check: new activity created without specifying activiy type
        # will have default type of the available activity type with the lowest sequence, then lowest id
        self.assertTrue(self.activity_type_todo.sequence < self.activity_type_call.sequence)
        for test_idx, test_case in enumerate(['mono', 'multi']):
            test_records = test_records_all[test_idx].with_env(self.env)
            with self.subTest(test_case=test_case, test_records=test_records):
                # 1. SCHEDULE ACTIVITIES
                with freeze_time(self.reference_now):
                    form = self._instantiate_activity_schedule_wizard(test_records)
                    form.summary = 'Write specification'
                    form.note = '<p>Useful link ...</p>'
                    form.activity_user_id = self.user_admin
                    with self._mock_activities():
                        form.save().action_schedule_activities()

                for record in test_records:
                    self.assertActivityCreatedOnRecord(record, {
                        'activity_type_id': self.activity_type_todo,
                        'automated': False,
                        'date_deadline': self.reference_now.date() + timedelta(days=4),  # activity type delay
                        'note': '<p>Useful link ...</p>',
                        'summary': 'Write specification',
                        'user_id': self.user_admin,
                    })

                # 2. LOG DONE ACTIVITIES
                with freeze_time(self.reference_now):
                    form = self._instantiate_activity_schedule_wizard(test_records)
                    form.activity_type_id = self.activity_type_call
                    form.activity_user_id = self.user_admin
                    with self._mock_activities(), freeze_time(self.reference_now):
                        form.save().with_context(
                            mail_activity_quick_update=True
                        ).action_schedule_activities_done()

                for record in test_records:
                    self.assertActivityDoneOnRecord(record, self.activity_type_call)

                # 3. CONTINUE WITH SCHEDULE ACTIVITIES
                # implies deadline addition on top of previous activities
                with freeze_time(self.reference_now):
                    form = self._instantiate_activity_schedule_wizard(test_records)
                    form.activity_type_id = self.activity_type_call
                    form.activity_user_id = self.user_admin
                    with self._mock_activities():
                        form.save().with_context(
                            mail_activity_quick_update=True
                        ).action_schedule_activities()

                for record in test_records:
                    self.assertActivityCreatedOnRecord(record, {
                        'activity_type_id': self.activity_type_call,
                        'automated': False,
                        'date_deadline': self.reference_now.date() + timedelta(days=1),  # activity call delay
                        'note': False,
                        'summary': 'TodoSumCallSummary',
                        'user_id': self.user_admin,
                    })

        # global activity creation from tests
        self.assertEqual(len(self.test_records[0].activity_ids), 4)
        self.assertEqual(len(self.test_records[1].activity_ids), 2)
        self.assertEqual(len(self.test_records[2].activity_ids), 2)
        self.assertEqual(len(self.test_records[3].activity_ids), 0)
        self.assertEqual(len(self.test_records[4].activity_ids), 0)

    @users('employee')
    def test_activity_schedule_norecord(self):
        """ Test scheduling free activities, supported if assigned user. """
        scheduler = self._instantiate_activity_schedule_wizard(None)
        self.assertEqual(scheduler.activity_type_id, self.activity_type_todo)
        with self._mock_activities():
            scheduler.save().action_schedule_activities()
        self.assertActivityValues(self._new_activities, {
            'res_id': False,
            'res_model': False,
            'summary': 'TodoSummary',
            'user_id': self.user_employee,
        })

        # cannot scheduler unassigned personal activities
        scheduler = self._instantiate_activity_schedule_wizard(None)
        scheduler = scheduler.save()
        with self.assertRaises(ValidationError):
            scheduler.activity_user_id = False

    def test_plan_copy(self):
        """Test plan copy"""
        copied_plan = self.plan_onboarding.copy()
        self.assertEqual(copied_plan.name, f'{self.plan_onboarding.name} (copy)')
        self.assertEqual(len(copied_plan.template_ids), len(self.plan_onboarding.template_ids))

    @users('employee')
    def test_plan_mode(self):
        """ Test the plan_mode that allows to preselect a compatible plan. """
        test_record = self.test_records[0].with_env(self.env)
        context = {
            'active_id': test_record.id,
            'active_ids': test_record.ids,
            'active_model': test_record._name
        }
        plan_mode_context = {**context, 'plan_mode': True}

        with Form(self.env['mail.activity.schedule'].with_context(context)) as form:
            self.assertFalse(form.plan_id)
        with Form(self.env['mail.activity.schedule'].with_context(plan_mode_context)) as form:
            self.assertEqual(form.plan_id, self.plan_party)
        # should select only model-plans
        self.plan_party.res_model = 'res.partner'
        with Form(self.env['mail.activity.schedule'].with_context(plan_mode_context)) as form:
            self.assertEqual(form.plan_id, self.plan_onboarding)

    @users('admin')
    def test_plan_next_activities(self):
        """ Test that next activities are displayed correctly. """
        test_plan = self.env['mail.activity.plan'].create({
            'name': 'Test Plan',
            'res_model': 'mail.test.activity',
            'template_ids': [
                (0, 0, {'activity_type_id': self.test_type_1.id}),
                (0, 0, {'activity_type_id': self.test_type_2.id}),
                (0, 0, {'activity_type_id': self.test_type_3.id}),
            ],
        })
        # Assert expected next activities
        expected_next_activities = [['TestAct2'], ['TestAct1', 'TestAct3'], []]
        for template, expected_names in zip(test_plan.template_ids, expected_next_activities, strict=True):
            self.assertEqual(template.next_activity_ids.mapped('name'), expected_names)
        # Test the plan summary
        with self.subTest(test_case='Check plan summary'), \
             freeze_time(self.reference_now):
            form = self._instantiate_activity_schedule_wizard(self.test_records[0])
            form.plan_id = test_plan
            expected_values = [
                {'description': 'TestAct1', 'deadline': datetime(2023, 9, 30).date()},
                {'description': 'TestAct2', 'deadline': datetime(2023, 10, 21).date()},
                {'description': 'TestAct2', 'deadline': datetime(2023, 9, 30).date()},
                {'description': 'TestAct1', 'deadline': datetime(2023, 10, 2).date()},
                {'description': 'TestAct3', 'deadline': datetime(2023, 9, 30).date()},
                {'description': 'TestAct3', 'deadline': datetime(2023, 9, 30).date()},
            ]
            for line, expected in zip(form.plan_schedule_line_ids._records, expected_values):
                with self.subTest(line=line, expected_values=expected):
                    self.assertEqual(line['line_description'], expected['description'])
                    self.assertEqual(line['line_date_deadline'], expected['deadline'])

    @users('employee')
    def test_plan_schedule(self):
        """ Test schedule of a plan on a single or multiple records. """
        test_records_all = [self.test_records[0], self.test_records[:3]]
        for test_idx, test_case in enumerate(['mono', 'multi']):
            test_records = test_records_all[test_idx].with_env(self.env)
            with self.subTest(test_case=test_case, test_records=test_records), \
                 freeze_time(self.reference_now):
                # No plan_date specified (-> self.reference_now is used), No responsible specified
                form = self._instantiate_activity_schedule_wizard(test_records)
                self.assertFalse(form.plan_schedule_line_ids)
                form.plan_id = self.plan_onboarding
                expected_values = [
                    {'description': 'Plan training', 'deadline': datetime(2023, 9, 27).date()},
                    {'description': 'Training', 'deadline': datetime(2023, 10, 14).date()},
                ]
                for line, expected in zip(form.plan_schedule_line_ids._records, expected_values):
                    self.assertEqual(line['line_description'], expected['description'])
                    self.assertEqual(line['line_date_deadline'], expected['deadline'])
                self.assertTrue(form._get_modifier('plan_on_demand_user_id', 'invisible'))
                form.plan_id = self.plan_party
                expected_values = [
                    {'description': 'Book a place', 'deadline': datetime(2023, 9, 29).date()},
                    {'description': 'Invite special guest', 'deadline': datetime(2023, 10, 7).date()},
                ]
                for line, expected in zip(form.plan_schedule_line_ids._records, expected_values):
                    self.assertEqual(line['line_description'], expected['description'])
                    self.assertEqual(line['line_date_deadline'], expected['deadline'])
                self.assertFalse(form._get_modifier('plan_on_demand_user_id', 'invisible'))
                with self._mock_activities():
                    form.save().action_schedule_plan()

                self.assertPlanExecution(
                    self.plan_party, test_records,
                    expected_deadlines=[(self.reference_now + relativedelta(days=-1)).date(),
                                        (self.reference_now + relativedelta(days=7)).date()])

                # plan_date specified, responsible specified
                plan_date = self.reference_now.date() + relativedelta(days=14)
                responsible_id = self.user_admin
                form = self._instantiate_activity_schedule_wizard(test_records)
                form.plan_id = self.plan_party
                form.plan_date = plan_date
                form.plan_on_demand_user_id = self.env['res.users']
                self.assertTrue(form.has_error)
                self.assertIn(f'No responsible specified for {self.activity_type_todo.name}: Book a place',
                              form.error)
                form.plan_on_demand_user_id = responsible_id
                self.assertFalse(form.has_error)
                deadline_1 = plan_date + relativedelta(days=-1)
                deadline_2 = plan_date + relativedelta(days=7)
                expected_values = [
                    {'description': 'Book a place', 'deadline': deadline_1},
                    {'description': 'Invite special guest', 'deadline': deadline_2},
                ]
                for line, expected in zip(form.plan_schedule_line_ids._records, expected_values):
                    self.assertEqual(line['line_description'], expected['description'])
                    self.assertEqual(line['line_date_deadline'], expected['deadline'])
                with self._mock_activities():
                    form.save().action_schedule_plan()

                self.assertPlanExecution(
                    self.plan_party, test_records,
                    expected_deadlines=[plan_date + relativedelta(days=-1),
                                        plan_date + relativedelta(days=7)],
                    expected_responsible=responsible_id)

    @users('admin')
    def test_plan_setup_model_consistency(self):
        """ Test the model consistency of a plan.

        Model consistency between activity_type - activity_template - plan:
        - a plan is restricted to a model
        - a plan contains activity plan templates which can be limited to some model
        through activity type
         """
        # Setup independent activities type to avoid interference with existing data
        activity_type_1, activity_type_2, activity_type_3 = self.env['mail.activity.type'].create([
            {'name': 'Todo'},
            {'name': 'Call'},
            {'name': 'Partner-specific', 'res_model': 'res.partner'},
        ])
        test_plan = self.env['mail.activity.plan'].create({
            'name': 'Test Plan',
            'res_model': 'mail.test.activity',
            'template_ids': [
                (0, 0, {'activity_type_id': activity_type_1.id}),
                (0, 0, {'activity_type_id': activity_type_2.id})
            ],
        })

        # ok, all activities generic
        test_plan.res_model = 'res.partner'
        test_plan.res_model = 'mail.test.activity'

        with self.assertRaises(
                ValidationError,
                msg='Cannot set activity type to res.partner as linked to a plan of another model'):
            activity_type_1.res_model = 'res.partner'

        activity_type_1.res_model = 'mail.test.activity'
        with self.assertRaises(
                ValidationError,
                msg='Cannot set plan to res.partner as using activities linked to another model'):
            test_plan.res_model = 'res.partner'

        with self.assertRaises(
                ValidationError,
                msg='Cannot create activity template for res.partner as linked to a plan of another model'):
            self.env['mail.activity.plan.template'].create({
                'activity_type_id': activity_type_3.id,
                'plan_id': test_plan.id,
            })

    @users('admin')
    def test_plan_setup_validation(self):
        """ Test plan consistency. """
        plan = self.env['mail.activity.plan'].create({
            'name': 'test',
            'res_model': 'mail.test.activity',
        })
        template = self.env['mail.activity.plan.template'].create({
            'activity_type_id': self.activity_type_todo.id,
            'plan_id': plan.id,
            'responsible_type': 'other',
            'responsible_id': self.user_admin.id,
        })
        template.responsible_type = 'on_demand'
        self.assertFalse(template.responsible_id)
        with self.assertRaises(
                ValidationError, msg='When selecting responsible "other", you must specify a responsible.'):
            template.responsible_type = 'other'
        template.write({'responsible_type': 'other', 'responsible_id': self.user_admin})
