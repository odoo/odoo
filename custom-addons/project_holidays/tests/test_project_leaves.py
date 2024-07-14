# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import datetime
from freezegun import freeze_time

from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.tests import common


@freeze_time('2020-01-01')
class TestProjectLeaves(common.TransactionCase):

    def setUp(self):
        super().setUp()

        self.user_hruser = mail_new_test_user(self.env, login='usertest', groups='base.group_user,hr_holidays.group_hr_holidays_user')
        self.employee_hruser = self.env['hr.employee'].create({
            'name': 'Test HrUser',
            'user_id': self.user_hruser.id,
            'tz': 'UTC',
        })

        self.leave_type = self.env['hr.leave.type'].create({
            'name': 'time off',
            'requires_allocation': 'no',
            'request_unit': 'hour',
        })
        self.project = self.env['project.project'].create({
            'name': "Coucoubre",
        })

    def test_simple_employee_leave(self):

        leave = self.env['hr.leave'].sudo().create({
            'holiday_status_id': self.leave_type.id,
            'employee_id': self.employee_hruser.id,
            'request_date_from': '2020-1-1',
            'request_date_to': '2020-1-1',
        })

        task_1 = self.env['project.task'].create({
            'name': "Task 1",
            'project_id': self.project.id,
            'user_ids': self.user_hruser,
            'planned_date_begin': datetime.datetime(2020, 1, 1, 8, 0),
            'date_deadline': datetime.datetime(2020, 1, 1, 17, 0),
        })
        task_2 = self.env['project.task'].create({
            'name': "Task 2",
            'project_id': self.project.id,
            'user_ids': self.user_hruser,
            'planned_date_begin': datetime.datetime(2020, 1, 2, 8, 0),
            'date_deadline': datetime.datetime(2020, 1, 2, 17, 0),
        })

        self.assertNotEqual(task_1.leave_warning, False,
                            "leave is not validated , but warning for requested time off")

        leave.action_validate()

        self.assertNotEqual(task_1.leave_warning, False,
                            "employee is on leave, should have a warning")
        self.assertNotEqual(task_1.leave_warning.startswith(
            "Test HrUser is on time off on that day"), "single day task, should show date")

        self.assertEqual(task_2.leave_warning, False,
                         "employee is not on leave, no warning")

    def test_multiple_leaves(self):
        self.env['hr.leave'].sudo().create({
            'holiday_status_id': self.leave_type.id,
            'employee_id': self.employee_hruser.id,
            'request_date_from': '2020-1-6',
            'request_date_to': '2020-1-7',
        }).action_validate()

        self.env['hr.leave'].sudo().create({
            'holiday_status_id': self.leave_type.id,
            'employee_id': self.employee_hruser.id,
            'request_date_from': '2020-1-8',
            'request_date_to': '2020-1-10',
        }).action_validate()

        task_1 = self.env['project.task'].create({
            'name': "Task 1",
            'project_id': self.project.id,
            'user_ids': self.user_hruser,
            'planned_date_begin': datetime.datetime(2020, 1, 6, 8, 0),
            'date_deadline': datetime.datetime(2020, 1, 6, 17, 0),
        })

        self.assertNotEqual(task_1.leave_warning, False,
                            "employee is on leave, should have a warning")
        self.assertTrue(task_1.leave_warning.startswith(
            "Test HrUser is on time off from 01/06/2020 to 01/07/2020. \n"), "single day task, should show date")

        task_2 = self.env['project.task'].create({
            'name': "Task 2",
            'project_id': self.project.id,
            'user_ids': self.user_hruser,
            'planned_date_begin': datetime.datetime(2020, 1, 6, 8, 0),
            'date_deadline': datetime.datetime(2020, 1, 7, 17, 0),
        })
        self.assertEqual(task_2.leave_warning,
                         "Test HrUser is on time off from 01/06/2020 to 01/07/2020. \n")

        task_3 = self.env['project.task'].create({
            'name': "Task 3",
            'project_id': self.project.id,
            'user_ids': self.user_hruser,
            'planned_date_begin': datetime.datetime(2020, 1, 6, 8, 0),
            'date_deadline': datetime.datetime(2020, 1, 10, 17, 0),
        })
        self.assertEqual(task_3.leave_warning, "Test HrUser is on time off from 01/06/2020 to 01/10/2020. \n",
                         "should show the start of the 1st leave and end of the 2nd")
