# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.hr_timesheet.tests.test_timesheet import TestCommonTimesheet
from odoo.tests import Form


class TestProjectTaskQuickCreate(TestCommonTimesheet):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.project_customer.write({'allow_timesheets': True})

    def test_create_task_with_valid_expressions(self):
        # tuple format = (display name, [expected name, expected tags count, expected users count, expected priority, expected planned hours])
        valid_expressions = {
            'task A 30H 2.5h #tag1 @user_employee2 2H #tag2 @user_employee 5h !': ('task A', 2, 2, "1", 39.5),
            'task A 30.H 2.h 1H #tag2 ! @user_employee ! @user_employee2 2.13h !': ('task A 30.H 2.h', 1, 2, "1", 3.13),
        }

        for expression, values in valid_expressions.items():
            task_form = Form(self.env['project.task'].with_context({'tracking_disable': True, 'default_project_id': self.project_customer.id}), view="project.quick_create_task_form")
            task_form.display_name = expression
            task = task_form.save()
            results = (task.name, len(task.tag_ids), len(task.user_ids), task.priority, task.allocated_hours)
            self.assertEqual(results, values)

    def test_create_task_with_invalid_expressions(self):
        invalid_expressions = (
            '30H #tag1 @raouf1 @raouf2 !',
            '30h #tag1 @raouf1 @raouf2 !',
        )

        for expression in invalid_expressions:
            task_form = Form(self.env['project.task'].with_context({'tracking_disable': True, 'default_project_id': self.project_customer.id}), view="project.quick_create_task_form")
            task_form.display_name = expression
            task = task_form.save()
            results = (task.name, len(task.tag_ids), len(task.user_ids), task.priority, task.allocated_hours)
            self.assertEqual(results, (expression, 0, 0, '0', 0))
