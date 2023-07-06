# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date

from odoo.addons.mail.tests.test_mail_activity import ActivityScheduleCase
from odoo.exceptions import ValidationError
from odoo.tests.common import Form
from odoo.tools import mute_logger


class TestActivitySchedule(ActivityScheduleCase):
    """ Test plan and activity schedule

     We test:
     - activity scheduling on a single record and in batch
     - plan scheduling on a single record and in batch
     - plan creation and consistency
     """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.test_record_1, cls.test_record_2, cls.test_record_3 = cls.env['mail.test.activity'].create([
            {'name': f'test_record_{idx + 1}'} for idx in range(3)])

    def get_default_deadline(self, activity_type, context=None):
        return self.env['mail.activity'].with_context(**(context or {}))._calculate_date_deadline(activity_type)

    def assertActivitiesFromPlan(self, plan, on_record, given_responsible_id=None, given_date_deadline=None):
        """ Check that the last activities on the record correspond to the one
        that the plan must create (number of activities and activities content).

        :param <mail.activity.plan> plan: activity plan that has been applied on the record
        :param recordset on_record: record on which the plan has been applied
        :param <res.user> given_responsible_id: responsible provided when scheduling the plan
        :param date given_date_deadline: deadline provided when scheduling the plan
        """
        expected_number_of_activity = len(plan.template_ids)
        activities = self.get_last_activities(on_record, expected_number_of_activity)
        default_responsible_id = given_responsible_id or self.env.user
        self.assertEqual(len(activities), expected_number_of_activity)
        for activity, template in zip(activities, plan.template_ids):
            self.assertEqual(activity.activity_type_id, template.activity_type_id)
            self.assertEqual(activity.summary, template.summary)
            self.assertEqual(activity.note, template.note)
            responsible_id = default_responsible_id if template.responsible_type == 'on_demand' else template.responsible_id
            self.assertEqual(activity.user_id, responsible_id)
            self.assertEqual(activity.date_deadline,
                             given_date_deadline or self.get_default_deadline(template.activity_type_id))

    def assertMessagesFromPlan(self, plan, on_record, given_responsible_id=None, given_date_deadline=None):
        """ Check that the last posted message on the record correspond to the one
        that the plan must generate (number of activities and activities content).

        :param <mail.activity.plan> plan: activity plan that has been applied on the record
        :param recordset on_record: record on which the plan has been applied
        :param <res.user> given_responsible_id: responsible provided when scheduling the plan
        :param date given_date_deadline: deadline provided when scheduling the plan
        """
        default_responsible_id = given_responsible_id or self.env.user
        message = self.get_last_message(on_record)
        self.assertIn(f'The plan "{plan.name}" has been started', message.body)
        for template in plan.template_ids:
            self.assertIn(template.summary, message.body)
            responsible_id = default_responsible_id if template.responsible_type == 'on_demand' else template.responsible_id
            date_deadline = given_date_deadline or self.get_default_deadline(template.activity_type_id)
            self.assertIn(f'{template.summary or template.activity_type_id.name}, '
                          f'assigned to {responsible_id.name}, due on the {date_deadline}', message.body)

    def assertPlanExecution(self, records, given_responsible_id=None, given_date_deadline=None):
        """ Check that the plan has created the right activities and send the
        right message on the records (see assertActivitiesFromPlan and
        assertMessagesFromPlan). """
        for record in records:
            self.assertActivitiesFromPlan(self.plan_party, record, given_date_deadline=given_date_deadline,
                                          given_responsible_id=given_responsible_id)
            self.assertMessagesFromPlan(self.plan_party, record, given_date_deadline=given_date_deadline,
                                        given_responsible_id=given_responsible_id)

    @mute_logger('odoo.tests', 'odoo.addons.mail.models.mail_mail', 'odoo.models.unlink')
    def test_activity_schedule(self):
        """ Test schedule of an activity on a single or multiple records. """
        for records in (self.test_record_1, self.test_record_1 + self.test_record_2 + self.test_record_3):
            form = self._instantiate_activity_schedule_wizard(records)
            self.assertFalse(form.has_error)
            form.activity_type_id = self.env['mail.activity.type']
            self.assertTrue(form.has_error)
            self.assertIn('Activity type is required', form.error)
            form.activity_type_id = self.activity_type_todo
            self.assertFalse(form.has_error)
            form.user_id = self.env['res.users']
            self.assertTrue(form.has_error)
            self.assertIn('Responsible is required', form.error)
            form.user_id = self.user_admin
            self.assertFalse(form.has_error)
            form.summary = 'Write specification'
            form.note = '<p>Useful link ...</p>'
            wizard = form.save()
            wizard.action_schedule_activities()
            for record in records:
                activity = self.get_last_activities(record, 1)[0]
                self.assertEqual(activity.activity_type_id, self.activity_type_todo)
                self.assertEqual(activity.date_deadline, self.get_default_deadline(self.activity_type_todo))
                self.assertEqual(activity.note, '<p>Useful link ...</p>')
                self.assertEqual(activity.summary, 'Write specification')
                self.assertEqual(activity.user_id, self.user_admin)

            form = self._instantiate_activity_schedule_wizard(records)
            form.activity_type_id = self.activity_type_call
            wizard = form.save()
            wizard.with_context(mail_activity_quick_update=True).action_schedule_and_mark_as_done()
            for record in records:
                message = self.get_last_message(record)
                self.assertEqual(message.mail_activity_type_id, self.activity_type_call)
                self.assertIn(self.activity_type_call.name, message.body)
                self.assertIn('done', message.body)

            form = self._instantiate_activity_schedule_wizard(records)
            form.activity_type_id = self.activity_type_todo
            wizard = form.save()
            wizard_res = wizard.with_context(mail_activity_quick_update=True).action_done_schedule_next()
            self.assertEqual({**wizard_res, 'context': False}, {
                'name': "Schedule Activity On Selected Records" if len(records) > 1 else "Schedule Activity",
                'context': False,  # tested below
                'view_mode': 'form',
                'res_model': 'mail.activity.schedule',
                'views': [(False, 'form')],
                'type': 'ir.actions.act_window',
                'target': 'new',
            })
            for record in records:
                message = self.get_last_message(record)
                self.assertEqual(message.mail_activity_type_id, self.activity_type_todo)
                self.assertIn(self.activity_type_todo.name, message.body)
                self.assertIn('done', message.body)
            form = Form(self.env['mail.activity.schedule'].with_context(wizard_res['context']))
            form.activity_type_id = self.activity_type_call
            wizard = form.save()
            wizard.with_context(mail_activity_quick_update=True).action_schedule_activities()
            for record in records:
                activity = self.get_last_activities(record, 1)[0]
                self.assertEqual(activity.activity_type_id, self.activity_type_call)
                self.assertEqual(activity.date_deadline,
                                 self.get_default_deadline(self.activity_type_call, context=wizard_res['context']))
                self.assertEqual(activity.note, False)
                self.assertEqual(activity.summary, False)
                self.assertEqual(activity.user_id, self.env.user)

        self.assertEqual(len(self.get_last_activities(self.test_record_1)), 4)
        self.assertEqual(len(self.get_last_activities(self.test_record_2)), 2)
        self.assertEqual(len(self.get_last_activities(self.test_record_3)), 2)

    def test_plan_create(self):
        """ Test plan consistency. """
        plan = self.env['mail.activity.plan'].create({'name': 'test'})
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

    def test_plan_mode(self):
        """ Test the plan_mode that allows to preselect a compatible plan. """
        self.test_activity = self.env['mail.test.activity'].create({'name': 'test'})
        context = {
            'default_res_ids': str(self.test_activity.id),
            'default_res_model': 'mail.test.activity',
        }
        with Form(self.env['mail.activity.schedule'].with_context(context)) as form:
            self.assertFalse(form.plan_id)
        context = {
            **context,
            'plan_mode': True,
        }
        self.plan_party.res_model_ids = self.env.ref('test_mail.model_mail_test_activity')
        with Form(self.env['mail.activity.schedule'].with_context(context)) as form:
            self.assertEqual(form.plan_id, self.plan_party)
        self.plan_party.res_model_ids = self.model_res_partner
        self.plan_onboarding.res_model_ids = self.env.ref('test_mail.model_mail_test_activity')
        with Form(self.env['mail.activity.schedule'].with_context(context)) as form:
            self.assertEqual(form.plan_id, self.plan_onboarding)

    def test_plan_setup_model_consistency(self):
        """ Test the model consistency of a plan.

        Model consistency between activity_type - activity_template - plan:
        - a plan can be restricted to some model
        - a plan contains activity plan templates which can be limited to some model
        through activity type
         """
        # Setup independent activities type to avoid interference with existing data
        activity_type_todo_2, activity_type_call_2 = (
            self.env['mail.activity.type'].create([{'name': name} for name in ('to do 2', 'call 2')]))
        for template_id in self.plan_party.template_ids:
            template_id.activity_type_id = activity_type_todo_2

        self.plan_party.res_model_ids = self.model_res_partner
        with self.assertRaises(
                ValidationError,
                msg='Plan limited to "partner" while the to-do activity can only be applied to "mail.test.activity".'):
            activity_type_todo_2.res_model = 'mail.test.activity'
        activity_type_todo_2.res_model = self.model_res_partner.model
        activity_type_todo_2.res_model = False
        self.plan_party.res_model_ids = False
        with self.assertRaises(
                ValidationError,
                msg='Plan not limited while the to-do activity can only be applied to "mail.test.activity".'):
            activity_type_todo_2.res_model = 'mail.test.activity'
        activity_type_todo_2.res_model = False
        self.plan_party.res_model_ids = self.model_res_partner
        activity_type_call_2.res_model = 'mail.test.activity'
        with self.assertRaises(
                ValidationError,
                msg='Plan limited to "partner" while the call activity can only be applied to "mail.test.activity".'):
            self.env['mail.activity.plan.template'].create({
                'activity_type_id': activity_type_call_2.id,
                'summary': 'Call room responsible',
                'responsible_type': 'other',
                'responsible_id': self.user_admin.id,
                'plan_id': self.plan_party.id,
            })

    @mute_logger('odoo.tests', 'odoo.addons.mail.models.mail_mail', 'odoo.models.unlink')
    def test_plan_schedule(self):
        """ Test schedule of a plan on a single or multiple records. """
        for records in (self.test_record_1, self.test_record_1 + self.test_record_2 + self.test_record_3):
            # No date_deadline specified, No responsible specified
            form = self._instantiate_activity_schedule_wizard(records)
            self.assertFalse(form.plan_assignation_summary)
            form.plan_id = self.plan_onboarding
            self.assertEqual(form.plan_assignation_summary,
                             '<ul><li>To-Do - other: Plan training</li><li>To-Do - other: Training</li></ul>')
            self.assertTrue(form._get_modifier('on_demand_user_id', 'invisible'))
            form.plan_id = self.plan_party
            self.assertIn('Book a place', form.plan_assignation_summary)
            self.assertFalse(form._get_modifier('on_demand_user_id', 'invisible'))
            wizard = form.save()
            wizard.action_schedule_plan()
            self.assertPlanExecution(records)
            # date_deadline specified, responsible specified
            given_date_deadline = date(2050, 1, 15)
            given_responsible_id = self.user_admin
            form = self._instantiate_activity_schedule_wizard(records)
            form.plan_id = self.plan_party
            form.date_plan_deadline = given_date_deadline
            form.on_demand_user_id = self.env['res.users']
            self.assertTrue(form.has_error)
            self.assertIn(f'No responsible specified for {self.activity_type_todo.name}: Book a place',
                          form.error)
            form.on_demand_user_id = given_responsible_id
            self.assertFalse(form.has_error)
            wizard = form.save()
            wizard.action_schedule_plan()
            self.assertPlanExecution(records,
                                     given_date_deadline=given_date_deadline,
                                     given_responsible_id=given_responsible_id)
