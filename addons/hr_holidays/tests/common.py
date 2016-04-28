# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common


class TestHrHolidaysBase(common.TransactionCase):

    def setUp(self):
        super(TestHrHolidaysBase, self).setUp()

        # Usefull models
        self.Employee = self.env['hr.employee']
        self.Holidays = self.env['hr.holidays']
        self.HolidaysStatus = self.env['hr.holidays.status']
        self.Partner = self.env['res.partner']
        self.Users = self.env['res.users'].with_context(no_reset_password=True)

        # Find Employee group
        group_employee = self.env.ref('base.group_user', False)
        self.group_employee_id = group_employee and group_employee.id or False

        # Find Hr User group
        group_hr_user = self.env.ref('base.group_hr_user', False)
        self.group_hr_user_id = group_hr_user and group_hr_user.id or False

        # Find Hr Manager group
        group_hr_manager = self.env.ref('base.group_hr_manager', False)
        self.group_hr_manager_id = group_hr_manager and group_hr_manager.id or False

        # Test users to use through the various tests
        self.user_hruser_id = self.Users.create({
            'name': 'Armande HrUser',
            'login': 'Armande',
            'alias_name': 'armande',
            'email': 'armande.hruser@example.com',
            'groups_id': [(6, 0, [self.group_employee_id, self.group_hr_user_id])]
        }).id
        self.user_hrmanager_id = self.Users.create({
            'name': 'Bastien HrManager',
            'login': 'bastien',
            'alias_name': 'bastien',
            'email': 'bastien.hrmanager@example.com',
            'groups_id': [(6, 0, [self.group_employee_id, self.group_hr_manager_id])]
        }).id
        self.user_employee_id = self.Users.create({
            'name': 'David Employee',
            'login': 'david',
            'alias_name': 'david',
            'email': 'david.employee@example.com',
            'groups_id': [(6, 0, [self.group_employee_id])]
        }).id

        # Hr Data
        self.employee_emp_id = self.Employee.create({
            'name': 'David Employee',
            'user_id': self.user_employee_id,
        }).id
        self.employee_hruser_id = self.Employee.create({
            'name': 'Armande HrUser',
            'user_id': self.user_hruser_id,
        }).id
