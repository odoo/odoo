# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date, timedelta
from freezegun import freeze_time

from odoo import Command, fields
from odoo.addons.mail.tests.test_mail_activity import ActivityScheduleCase
from odoo.exceptions import ValidationError
from odoo.tests import Form, tagged, users


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

        # prepare plans
        cls.plan_party = cls.env['mail.activity.plan'].create({
            'name': 'Test Plan A Party',
            'res_model': 'mail.test.activity',
            'template_ids': [
                Command.create({
                    'activity_type_id': cls.activity_type_todo.id,
                    'responsible_type': 'on_demand',
                    'sequence': 10,
                    'summary': 'Book a place',
                }), Command.create({
                    'activity_type_id': cls.activity_type_todo.id,
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
                Command.create({
                    'activity_type_id': cls.activity_type_todo.id,
                    'responsible_id': cls.user_admin.id,
                    'responsible_type': 'other',
                    'sequence': 10,
                    'summary': 'Plan training',
                }), Command.create({
                    'activity_type_id': cls.activity_type_todo.id,
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

    @users('employee')
    def test_activity_schedule(self):
        """ Test schedule of an activity on a single or multiple records. """
        test_records_all = [self.test_records[0], self.test_records[:3]]
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
                        'date_deadline': self.reference_now.date() + timedelta(days=4),  # activity type delay
                        'note': '<p>Useful link ...</p>',
                        'summary': 'Write specification',
                        'user_id': self.user_admin,
                    })

                # 2. LOG DONE ACTIVITIES
                with freeze_time(self.reference_now):
                    form = self._instantiate_activity_schedule_wizard(test_records)
                    form.activity_type_id = self.activity_type_call
                    with self._mock_activities(), freeze_time(self.reference_now):
                        form.save().with_context(
                            mail_activity_quick_update=True
                        ).action_schedule_activities_done()

                for record in test_records:
                    self.assertActivityDoneOnRecord(record, self.activity_type_call)

                # 3. LOG DONE ACTIVITIES, PREPARE SCHEDULE NEXT
                with freeze_time(self.reference_now):
                    form = self._instantiate_activity_schedule_wizard(test_records)
                    form.activity_type_id = self.activity_type_todo
                    with self._mock_activities():
                        wizard_res = form.save().with_context(
                            mail_activity_quick_update=True
                        ).action_schedule_activities_done_and_schedule()
                self.assertDictEqual(wizard_res, {
                    'name': "Schedule Activity On Selected Records" if len(test_records) > 1 else "Schedule Activity",
                    'context': {
                        'active_id': test_records[0].id,
                        'active_ids': test_records.ids,
                        'active_model': test_records._name,
                        'mail_activity_quick_update': True,
                        'default_previous_activity_type_id': 4,
                        'activity_previous_deadline': self.reference_now.date() + timedelta(days=4),
                        'default_res_ids': repr(test_records.ids),
                        'default_res_model': test_records._name,
                    },
                    'view_mode': 'form',
                    'res_model': 'mail.activity.schedule',
                    'views': [(False, 'form')],
                    'type': 'ir.actions.act_window',
                    'target': 'new',
                })
                for record in test_records:
                    self.assertActivityDoneOnRecord(record, self.activity_type_todo)

                # 4. CONTINUE WITH SCHEDULE ACTIVITIES
                # implies deadline addition on top of previous activities
                with freeze_time(self.reference_now):
                    form = Form(self.env['mail.activity.schedule'].with_context(wizard_res['context']))
                    form.activity_type_id = self.activity_type_call
                    with self._mock_activities():
                        form.save().with_context(
                            mail_activity_quick_update=True
                        ).action_schedule_activities()

                for record in test_records:
                    self.assertActivityCreatedOnRecord(record, {
                        'activity_type_id': self.activity_type_call,
                        'date_deadline': self.reference_now.date() + timedelta(days=5),  # both types delays
                        'note': False,
                        'summary': False,
                        'user_id': self.env.user,
                    })

        # global activity creation from tests
        self.assertEqual(len(self.test_records[0].activity_ids), 4)
        self.assertEqual(len(self.test_records[1].activity_ids), 2)
        self.assertEqual(len(self.test_records[2].activity_ids), 2)
        self.assertEqual(len(self.test_records[3].activity_ids), 0)
        self.assertEqual(len(self.test_records[4].activity_ids), 0)

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

    @users('employee')
    def test_plan_schedule(self):
        """ Test schedule of a plan on a single or multiple records. """
        test_records_all = [self.test_records[0], self.test_records[:3]]
        for test_idx, test_case in enumerate(['mono', 'multi']):
            test_records = test_records_all[test_idx].with_env(self.env)
            with self.subTest(test_case=test_case, test_records=test_records), \
                 freeze_time(self.reference_now):
                # No date_deadline specified, No responsible specified
                form = self._instantiate_activity_schedule_wizard(test_records)
                self.assertFalse(form.plan_assignation_summary)
                form.plan_id = self.plan_onboarding
                self.assertEqual(form.plan_assignation_summary,
                                 '<ul><li>To-Do: Plan training</li><li>To-Do: Training</li></ul>')
                self.assertTrue(form._get_modifier('plan_on_demand_user_id', 'invisible'))
                form.plan_id = self.plan_party
                self.assertIn('Book a place', form.plan_assignation_summary)
                self.assertFalse(form._get_modifier('plan_on_demand_user_id', 'invisible'))
                with self._mock_activities():
                    form.save().action_schedule_plan()

                self.assertPlanExecution(self.plan_party, test_records)

                # date_deadline specified, responsible specified
                force_base_date_deadline = date(2050, 1, 15)
                force_responsible_id = self.user_admin
                form = self._instantiate_activity_schedule_wizard(test_records)
                form.plan_id = self.plan_party
                form.plan_date_deadline = force_base_date_deadline
                form.plan_on_demand_user_id = self.env['res.users']
                self.assertTrue(form.has_error)
                self.assertIn(f'No responsible specified for {self.activity_type_todo.name}: Book a place',
                              form.error)
                form.plan_on_demand_user_id = force_responsible_id
                self.assertFalse(form.has_error)
                with self._mock_activities():
                    form.save().action_schedule_plan()

                self.assertPlanExecution(
                    self.plan_party, test_records,
                    force_base_date_deadline=force_base_date_deadline,
                    force_responsible_id=force_responsible_id)

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
