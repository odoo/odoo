# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.addons.mail.tests.test_mail_activity import ActivityScheduleCase
from odoo.exceptions import UserError, ValidationError


class TestActivityScheduleHRCase(ActivityScheduleCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.model_hr_employee = cls.env.ref('hr.model_hr_employee')
        cls.user_admin = cls.env.ref('base.user_admin')
        cls.plan_onboarding.res_model_ids = cls.model_hr_employee
        cls.plan_onboarding.template_ids[1].write({
            'responsible_type': 'coach',
            'responsible_id': False,
        })
        cls.users = cls.env['res.users'].create([{
            'name': name,
            'login': name,
            'email': f'{name}@example.com',
        } for name in ('test_manager', 'test_coach', 'test_employee1', 'test_employee2', 'test_employee_dep_b')])
        cls.user_internal_basic = cls.env['res.users'].create(
            next({'name': name, 'login': name, 'email': f'{name}@example.com',
                  'groups_id': [Command.set([cls.env.ref('base.group_user').id])]} for name in ('non_employee',)))
        cls.user_manager, cls.user_coach, cls.user_employee_1, cls.user_employee_2, cls.user_employee_dep_b = cls.users
        cls.employees = cls.env['hr.employee'].create([{
            'name': user.name,
            'user_id': user.id,
            'work_email': user.email,
        } for user in cls.users])
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


class TestActivitySchedule(TestActivityScheduleHRCase):
    def test_department(self):
        """ Check that the allowed plan are filtered according to the department. """
        no_plan = self.env['mail.activity.plan']
        plan_department_a, plan_department_b = self.env['mail.activity.plan'].create([{
            'department_id': department.id,
            'name': f'plan {department.name}',
            'res_model_ids': [Command.link(self.model_hr_employee.id)],
            'template_ids': [Command.create({
                'activity_type_id': self.activity_type_todo.id,
            }),
            ]
        } for department in self.department_a + self.department_b])
        for employees, expected_department, authorized_plans, non_authorized_plans in (
                (self.employee_1 + self.employee_dep_b, False, self.plan_onboarding, no_plan),
                (self.employee_1 + self.employee_2, self.department_a,
                 self.plan_onboarding + plan_department_a, plan_department_b),
                (self.employee_1, self.department_a, self.plan_onboarding + plan_department_a, plan_department_b),
                (self.employee_dep_b, self.department_b, self.plan_onboarding + plan_department_b, plan_department_a),
        ):
            with self._instantiate_activity_schedule_wizard(employees) as form:
                if expected_department:
                    self.assertEqual(form.department_id, expected_department)
                else:
                    self.assertFalse(form.department_id)
            for plan in non_authorized_plans:
                with self.assertRaises(ValidationError), self._instantiate_activity_schedule_wizard(employees) as form:
                    form.plan_id = plan
            for plan in authorized_plans:
                with self._instantiate_activity_schedule_wizard(employees) as form:
                    form.plan_id = plan

    def test_generalize_plan(self):
        """ Check that we cannot generalize plan if hr plan specific features are used. """
        with self.assertRaises(
                UserError,
                msg="Cannot generalize the plans because they are employee specific (field: responsible: coach)."):
            self.plan_onboarding.res_model_ids = False
        with self.assertRaises(
                UserError,
                msg="Cannot generalize the plans because they are employee specific (field: responsible: coach)."):
            self.plan_onboarding.res_model_ids = self.model_hr_employee + self.model_res_partner
        self.plan_onboarding.template_ids[1].responsible_type = 'on_demand'
        self.plan_onboarding.res_model_ids = False
        self.plan_onboarding.res_model_ids = self.model_hr_employee
        self.plan_onboarding.template_ids[1].responsible_type = 'manager'
        with self.assertRaises(
                UserError,
                msg="Cannot generalize the plans because they are employee specific (field: responsible: manager)."):
            self.plan_onboarding.res_model_ids = False
        self.plan_onboarding.template_ids[1].responsible_type = 'employee'
        with self.assertRaises(
                UserError,
                msg="Cannot generalize the plans because they are employee specific (field: responsible: employee)."):
            self.plan_onboarding.res_model_ids = self.model_hr_employee + self.model_res_partner
        self.plan_onboarding.template_ids[1].responsible_type = 'on_demand'
        self.plan_onboarding.res_model_ids = False
        self.plan_onboarding.res_model_ids = self.model_hr_employee
        self.plan_onboarding.department_id = self.department_a
        self.plan_onboarding.res_model_ids = False
        self.assertFalse(self.plan_onboarding.department_id,
                         "The department must be automatically set to False when the plan is generalized.")

    def test_responsible(self):
        """ Check that the responsible is correctly configured. """
        self.plan_onboarding.template_ids[0].write({
            'responsible_type': 'manager',
            'responsible_id': False,
        })
        self.plan_onboarding.template_ids += self.env['mail.activity.plan.template'].create({
            'activity_type_id': self.activity_type_todo.id,
            'summary': 'Send feedback to the manager',
            'responsible_type': 'employee',
            'sequence': 30,
        })
        for employees in (self.employee_1, self.employee_1 + self.employee_2):
            # Happy case
            form = self._instantiate_activity_schedule_wizard(employees)
            form.plan_id = self.plan_onboarding
            self.assertEqual(form.plan_assignation_summary,
                             '<ul><li>To-Do - manager: Plan training</li><li>To-Do - coach: Training</li>'
                             '<li>To-Do - employee: Send feedback to the manager</li></ul>')
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
            self.assertIn('Manager of employee test_employee1 is not set.', form.error)
            self.assertIn('Coach of employee test_employee1 is not set.', form.error)
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
            self.assertIn("The user of test_employee1's coach is not set.", form.error)
            self.assertIn('The manager of test_employee1 should be linked to a user.', form.error)
            if len(employees) > 1:
                self.assertIn("The user of test_employee2's coach is not set.", form.error)
                self.assertIn('The manager of test_employee2 should be linked to a user.', form.error)
            with self.assertRaises(ValidationError):
                form.save()
            self.employee_coach.user_id = self.user_coach
            self.employee_manager.user_id = self.user_manager

    def test_responsible_without_access_to_employee(self):
        """ Check that when the responsible has no access to the employee record, the activity is posted on a pseudo
         employee record of type hr.plan.employee.activity. """
        for employees in (self.employee_1, self.employee_1 + self.employee_2):
            self.plan_onboarding.template_ids[0].responsible_id = self.user_internal_basic
            form = self._instantiate_activity_schedule_wizard(employees)
            form.plan_id = self.plan_onboarding
            wizard = form.save()
            wizard.action_schedule_plan()
            for employee in employees:
                activities = self.get_last_activities(employee, 1)
                self.assertEqual(len(activities), 1)
                self.assertEqual(activities[0].user_id, self.user_coach)
                activities = self.get_last_activities(
                    self.env['hr.plan.employee.activity'].search([('employee_id', '=', employee.id)]), 1)
                self.assertEqual(len(activities), 1)
                self.assertEqual(activities[0].user_id, self.user_internal_basic)

    def test_schedule_plan_with_active_ids(self):
        """ Check that active_ids and active_model context values can be used
        instead of default_res_ids and default_res_model.

        This is necessary to be compatible with the link posted at the employee
        creation as a reminder to set up the onboarding plan.
        """
        for employees in (self.employee_1, self.employee_1 + self.employee_2):
            form = self._instantiate_activity_schedule_wizard(employees)
            self.assertEqual(form.res_ids, ','.join(str(employee.id) for employee in employees))
            self.assertEqual(form.res_model, 'hr.employee')
