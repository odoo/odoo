# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common


class TestHrHolidaysCommon(common.TransactionCase):

    def setUp(self):
        super(TestHrHolidaysCommon, self).setUp()

        # Useful models
        self.HrEmployee = self.env['hr.employee']
        self.HrHolidays = self.env['hr.holidays']
        self.HrHolidaysStatus = self.env['hr.holidays.status']
        self.ResUsers = self.env['res.users']

        # Find Hr Manager, Hr User, Employee group
        self.group_hr_manager_id = self.ref('base.group_hr_manager')
        self.group_hr_user_id = self.ref('base.group_hr_user')
        self.group_user_id = self.ref('base.group_user')

        # Test users to use through the various tests
        self.user_hr_manager_id = self.ResUsers.create({
            'name': 'Bastien HrManager',
            'login': 'bastien',
            'password': 'bastien',
            'alias_name': 'bastien',
            'email': 'bastien.hrmanager@example.com',
            'groups_id': [(6, 0, [self.group_user_id, self.group_hr_manager_id])]
        }).id
        self.user_hr_user_id = self.ResUsers.create({
            'name': 'Armande HrUser',
            'login': 'Armande',
            'password': 'Armande',
            'alias_name': 'armande',
            'email': 'armande.hruser@example.com',
            'groups_id': [(6, 0, [self.group_user_id, self.group_hr_user_id])]
        }).id
        self.user_employee_id = self.ResUsers.create({
            'name': 'David Employee',
            'login': 'david',
            'password': 'david',
            'alias_name': 'david',
            'email': 'david.employee@example.com',
            'groups_id': [(6, 0, [self.group_user_id])]
        }).id
        self.user_none_id = self.ResUsers.create({
            'name': 'Charlie Avotbonkeur',
            'login': 'charlie',
            'password': 'charlie',
            'alias_name': 'charlie',
            'email': 'charlie.noone@example.com',
            'groups_id': [(6, 0, [])]
        }).id


        # Hr Data
        self.emp_user_id = self.HrEmployee.create({
            'name': 'David Employee',
            'user_id': self.user_employee_id,
        }).id
        self.emp_hr_user_id = self.HrEmployee.create({
            'name': 'Armande HrUser',
            'user_id': self.user_hr_user_id,
        }).id
