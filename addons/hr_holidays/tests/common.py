# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.test_mail.tests.common import mail_new_test_user
from odoo.tests import common


class TestHrHolidaysBase(common.TransactionCase):

    def setUp(self):
        super(TestHrHolidaysBase, self).setUp()

        # Test users to use through the various tests
        self.user_hruser = mail_new_test_user(self.env, login='armande', groups='base.group_user,hr_holidays.group_hr_holidays_user')
        self.user_hruser_id = self.user_hruser.id

        self.user_hrmanager = mail_new_test_user(self.env, login='bastien', groups='base.group_user,hr_holidays.group_hr_holidays_manager')
        self.user_hrmanager_id = self.user_hrmanager.id

        self.user_employee = mail_new_test_user(self.env, login='david', groups='base.group_user')
        self.user_employee_id = self.user_employee.id

        self.user_hrmanager_2 = mail_new_test_user(self.env, login='florence', groups='base.group_user,hr_holidays.group_hr_holidays_manager')
        self.user_hrmanager_2_id = self.user_hrmanager_2.id

        # Hr Data
        Department = self.env['hr.department'].with_context(tracking_disable=True)

        self.hr_dept = Department.create({
            'name': 'Human Resources',
        })
        self.rd_dept = Department.create({
            'name': 'Research and devlopment',
        })

        self.employee_emp = self.env['hr.employee'].create({
            'name': 'David Employee',
            'user_id': self.user_employee_id,
            'department_id': self.rd_dept.id,
        })
        self.employee_emp_id = self.employee_emp.id

        self.employee_hruser = self.env['hr.employee'].create({
            'name': 'Armande HrUser',
            'user_id': self.user_hruser_id,
            'department_id': self.rd_dept.id,
        })
        self.employee_hruser_id = self.employee_hruser.id

        self.employee_hrmanager = self.env['hr.employee'].create({
            'name': 'Bastien HrManager',
            'user_id': self.user_hrmanager_id,
            'department_id': self.hr_dept.id,
        })
        self.employee_hrmanager_id = self.employee_hrmanager.id

        self.employee_hrmanager_2_id = self.env['hr.employee'].create({
            'name': 'Florence HrManager',
            'user_id': self.user_hrmanager_2_id,
            'parent_id': self.employee_hrmanager_id,
        }).id

        self.rd_dept.write({'manager_id': self.employee_hruser_id})
