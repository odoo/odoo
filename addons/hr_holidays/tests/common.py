# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common


class TestHrHolidaysBase(common.TransactionCase):

    def setUp(self):
        super(TestHrHolidaysBase, self).setUp()

        Users = self.env['res.users'].with_context(no_reset_password=True)

        # Find Employee group
        group_employee_id = self.ref('base.group_user')

        # Test users to use through the various tests
        self.user_leavemanager_id = Users.create({
            'name': 'Bastien HrManager',
            'login': 'bastien',
            'alias_name': 'bastien',
            'email': 'bastien.hrmanager@example.com',
            'groups_id': [(6, 0, [group_employee_id, self.ref('hr_holidays.group_leave_manager')])]
        }).id
        self.user_employee_id = Users.create({
            'name': 'David Employee',
            'login': 'david',
            'alias_name': 'david',
            'email': 'david.employee@example.com',
            'groups_id': [(6, 0, [group_employee_id])]
        }).id

        # Hr Data
        self.employee_emp_id = self.env['hr.employee'].create({
            'name': 'David Employee',
            'user_id': self.user_employee_id,
        }).id
        self.employee_hrmanager_id = self.env['hr.employee'].create({
            'name': 'Bastien HrManager',
            'user_id': self.user_leavemanager_id,
        }).id
