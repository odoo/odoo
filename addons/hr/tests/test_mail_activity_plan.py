# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.mail.tests.test_mail_activity import ActivityScheduleCase
from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged, users


class ActivityScheduleHRCase(ActivityScheduleCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.plan_onboarding = cls.env['mail.activity.plan'].create({
            'name': 'Test Onboarding',
            'res_model': 'hr.employee',
            'template_ids': [
                Command.create({
                    'activity_type_id': cls.activity_type_todo.id,
                    'responsible_id': cls.user_admin.id,
                    'responsible_type': 'other',
                    'sequence': 10,
                    'summary': 'Plan training',
                }), Command.create({
                    'activity_type_id': cls.activity_type_todo.id,
                    'responsible_id': False,
                    'responsible_type': 'coach',
                    'sequence': 20,
                    'summary': 'Training',
                }),
            ]
        })
        cls.plan_party = cls.env['mail.activity.plan'].create({
            'name': 'Test Party Plan',
            'res_model': 'res.partner',
            'template_ids': [
                Command.create({
                    'activity_type_id': cls.activity_type_todo.id,
                    'responsible_id': cls.user_admin.id,
                    'responsible_type': 'on_demand',
                    'sequence': 10,
                    'summary': 'Party',
                }),
            ]
        })

        cls.user_manager = mail_new_test_user(
            cls.env,
            email='test.manager@test.mycompany.com',
            groups='base.group_user,hr.group_hr_manager',
            login='test_manager',
            name='Test Manager',
        )
        cls.user_coach = mail_new_test_user(
            cls.env,
            email='test.coach@test.mycompany.com',
            groups='base.group_user,hr.group_hr_manager',
            login='test_coach',
            name='Test Coach',
        )
        cls.user_employee_1 = mail_new_test_user(
            cls.env,
            email='test.employee1@test.mycompany.com',
            groups='base.group_user,hr.group_hr_manager',
            login='test_employee1',
            name='Test Employee 1',
        )
        cls.user_employee_2 = mail_new_test_user(
            cls.env,
            email='test.employee2@test.mycompany.com',
            groups='base.group_user,hr.group_hr_manager',
            login='test_employee2',
            name='Test Employee 2',
        )
        cls.user_employee_dep_b = mail_new_test_user(
            cls.env,
            email='test.employeedepb@test.mycompany.com',
            groups='base.group_user,hr.group_hr_manager',
            login='test_employee_dep_b',
            name='Test Employee DepB',
        )
        cls.users = cls.user_manager + cls.user_coach + cls.user_employee_1 + cls.user_employee_2 + cls.user_employee_dep_b

        cls.user_internal_basic = mail_new_test_user(
            cls.env,
            email='non.employee@test.mycompany.com',
            groups='base.group_user',
            login='non_employee',
            name='Non Employee',
        )

        cls.employees = cls.env['hr.employee'].create([
            {
                'name': user.name,
                'user_id': user.id,
                'work_email': user.email,
            } for user in cls.users
        ])
        cls.employee_manager, cls.employee_coach, cls.employee_1, cls.employee_2, cls.employee_dep_b = cls.employees
        cls.department_a = cls.env['hr.department'].create({
            'name': 'Test Department A',
            'member_ids': [Command.link(employee.id) for employee in cls.employees - cls.employee_dep_b],
        })
        cls.department_b = cls.env['hr.department'].create({
            'name': 'Test Department B',
            'member_ids': [Command.link(cls.employee_dep_b.id)],
        })
        cls.employee_1.coach_id = cls.employee_coach
        cls.employee_1.parent_id = cls.employee_manager
        cls.employee_2.coach_id = cls.employee_coach
        cls.employee_2.parent_id = cls.employee_manager
        cls.employee_coach.parent_id = cls.employee_manager
        cls.employee_dep_b.coach_id = cls.employee_coach


@tagged('mail_activity', 'mail_activity_plan')
class TestActivitySchedule(ActivityScheduleHRCase):

    @users('admin')
    def test_department(self):
        """ Check that the allowed plan are filtered according to the department. """
        no_plan = self.env['mail.activity.plan']
        plan_department_a, plan_department_b = self.env['mail.activity.plan'].create([
            {
                'department_id': department.id,
                'name': f'plan {department.name}',
                'res_model': 'hr.employee',
                'template_ids': [(0, 0, {'activity_type_id': self.activity_type_todo.id})],
            } for department in self.department_a + self.department_b
        ])
        for employees, expected_department, authorized_plans, non_authorized_plans in (
            (self.employee_1 + self.employee_dep_b, False, self.plan_onboarding, no_plan),
            (self.employee_1 + self.employee_2, self.department_a, self.plan_onboarding + plan_department_a, plan_department_b),
            (self.employee_1, self.department_a, self.plan_onboarding + plan_department_a, plan_department_b),
            (self.employee_dep_b, self.department_b, self.plan_onboarding + plan_department_b, plan_department_a),
        ):
            with self._instantiate_activity_schedule_wizard(employees) as form:
                if expected_department:
                    self.assertEqual(form.department_id, expected_department)
                else:
                    self.assertFalse(form.department_id)
            for plan in non_authorized_plans:
                self.assertNotIn(plan, form.plan_available_ids)
            for plan in authorized_plans:
                with self._instantiate_activity_schedule_wizard(employees) as form:
                    form.plan_id = plan

    def test_res_model_compatibility(self):
        """ Check that we cannot change the plan model to a model different
        of employee if hr plan specific features are used. """
        with self.assertRaises(
                UserError,
                msg="Coach, manager or employee can only be chosen as template responsible with employee plan."):
            self.plan_onboarding.res_model = 'res.partner'
        self.plan_onboarding.template_ids[1].responsible_type = 'on_demand'
        self.plan_onboarding.res_model = 'res.partner'
        self.plan_onboarding.res_model = 'hr.employee'
        self.plan_onboarding.template_ids[1].responsible_type = 'manager'
        with self.assertRaises(
                UserError,
                msg="Coach, manager or employee can only be chosen as template responsible with employee plan."):
            self.plan_onboarding.res_model = 'res.partner'
        self.plan_onboarding.template_ids[1].responsible_type = 'employee'
        with self.assertRaises(
                UserError,
                msg="Coach, manager or employee can only be chosen as template responsible with employee plan."):
            self.plan_onboarding.res_model = 'res.partner'
        self.plan_onboarding.template_ids[1].responsible_type = 'on_demand'
        self.plan_onboarding.res_model = 'res.partner'
        self.plan_onboarding.res_model = 'hr.employee'
        self.plan_onboarding.department_id = self.department_a
        self.plan_onboarding.res_model = 'res.partner'
        self.assertFalse(self.plan_onboarding.department_id)

    def test_responsible(self):
        """ Check that the responsible is correctly configured. """
        self.plan_onboarding.template_ids[0].write({
            'responsible_type': 'manager',
            'responsible_id': False,
        })
        self.plan_onboarding.write({
            'template_ids': [(0, 0, {
                'activity_type_id': self.activity_type_todo.id,
                'summary': 'Send feedback to the manager',
                'responsible_type': 'employee',
                'sequence': 30,
            })],
        })
        for employees in (self.employee_1, self.employee_1 + self.employee_2):
            # Happy case
            form = self._instantiate_activity_schedule_wizard(employees)
            form.plan_id = self.plan_onboarding
            self.assertEqual(form.plan_summary,
                             "<ul>Manager <ul><li>To-Do: Plan training</li>"
                             "</ul>Coach <ul><li>To-Do: Training</li>"
                             "</ul>Employee <ul><li>To-Do: Send feedback to the manager</li></ul></ul>")
            self.assertFalse(form.has_error)
            wizard = form.save()
            wizard.action_schedule_plan()
            for employee in employees:
                activities = self.get_last_activities(employee, 3)
                self.assertEqual(len(activities), 3)
                self.assertEqual(activities[0].user_id, self.user_manager)
                self.assertEqual(activities[1].user_id, self.user_coach)
                self.assertEqual(activities[2].user_id, employee.user_id)

            # Cases with errors
            self.employee_1.parent_id = False
            self.employee_1.coach_id = False
            form = self._instantiate_activity_schedule_wizard(employees)
            form.plan_id = self.plan_onboarding
            self.assertTrue(form.has_error)
            n_error = form.error.count('<li>')
            self.assertEqual(n_error, 2)
            self.assertIn(f'Manager of employee {self.employee_1.name} is not set.', form.error)
            self.assertIn(f'Coach of employee {self.employee_1.name} is not set.', form.error)
            with self.assertRaises(ValidationError):
                form.save()
            self.employee_1.parent_id = self.employee_manager
            self.employee_1.coach_id = self.employee_coach
            self.employee_coach.user_id = False
            self.employee_manager.user_id = False
            form = self._instantiate_activity_schedule_wizard(employees)
            form.plan_id = self.plan_onboarding
            self.assertTrue(form.has_error)
            n_error = form.error.count('<li>')
            self.assertEqual(n_error, 2 * len(employees))
            self.assertIn(f"The user of {self.employee_1.name}'s coach is not set.", form.error)
            self.assertIn(f'The manager of {self.employee_1.name} should be linked to a user.', form.error)
            if len(employees) > 1:
                self.assertIn(f"The user of {self.employee_2.name}'s coach is not set.", form.error)
                self.assertIn(f'The manager of {self.employee_2.name} should be linked to a user.', form.error)
            with self.assertRaises(ValidationError):
                form.save()
            self.employee_coach.user_id = self.user_coach
            self.employee_manager.user_id = self.user_manager
