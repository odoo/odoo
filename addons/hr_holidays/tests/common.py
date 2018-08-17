# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common


class TestHrHolidaysBase(common.TransactionCase):

    def setUp(self):
        super(TestHrHolidaysBase, self).setUp()

        self._quick_create_ctx = {
            'mail_create_nolog': True,
            'mail_create_nosubscribe': True,
            'mail_notrack': True,
        }
        self._quick_create_user_ctx = dict(self._quick_create_ctx, no_reset_password=True)

        # Test users to use through the various tests
        Users = self.env['res.users'].with_context(self._quick_create_user_ctx)
        self.user_hruser = Users.create({
            'name': 'Armande HrUser',
            'login': 'Armande',
            'email': 'armande.hruser@example.com',
            'groups_id': [(6, 0, [self.ref('base.group_user'), self.ref('hr_holidays.group_hr_holidays_user')])]
        })
        self.user_hruser_id = self.user_hruser.id
        self.user_hrmanager = Users.create({
            'name': 'Bastien HrManager',
            'login': 'bastien',
            'email': 'bastien.hrmanager@example.com',
            'groups_id': [(6, 0, [self.ref('base.group_user'), self.ref('hr_holidays.group_hr_holidays_manager')])]
        }).id
        self.user_hrmanager_id = self.user_hrmanager
        self.user_employee = Users.create({
            'name': 'David Employee',
            'login': 'david',
            'email': 'david.employee@example.com',
            'groups_id': [(6, 0, [self.ref('base.group_user')])]
        })
        self.user_employee_id = self.user_employee.id
        self.user_hrmanager_2_id = Users.create({
            'name': 'Florence HrManager',
            'login': 'florence',
            'email': 'florence.hrmanager@example.com',
            'groups_id': [(6, 0, [self.ref('base.group_user'), self.ref('hr_holidays.group_hr_holidays_manager')])]
        }).id

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
