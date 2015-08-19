# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from openerp.tests import common


class TestHrHolidaysCommon(common.TransactionCase):

    def setUp(self):
        super(TestHrHolidaysCommon, self).setUp()

        self.Users = self.env['res.users']
        self.HrEmployee = self.env['hr.employee']
        self.HrHolidays = self.env['hr.holidays']
        self.HrHolidaysStatus = self.env['hr.holidays.status']
        self.ResPartner = self.env['res.partner']
        self.CalenderEventType = self.env['calendar.event.type']

        # Find Hr Manager, Hr User, Employee group
        self.group_hr_manager_id = self.env.ref('base.group_hr_manager').id
        self.group_hr_user_id = self.env.ref('base.group_hr_user').id
        self.group_user_id = self.env.ref('base.group_user').id

        # Creating four users and assigning each a group related to Human Resource Management
        self.res_users_hr_manager = self.Users.create({
            'name': 'HR Manager',
            'login': 'hrm',
            'password': 'hrm',
            'alias_name': 'hrm',
            'email': 'hrm@example.com',
            'groups_id': [(6, 0, [self.group_hr_manager_id])]
        }).id

        self.res_users_hr_officer = self.Users.create({
            'name': 'HR Officer',
            'login': 'hro',
            'password': 'hro',
            'alias_name': 'hro',
            'email': 'hro@example.com',
            'groups_id': [(6, 0, [self.group_hr_user_id])]
        }).id

        self.res_users_employee = self.Users.create({
            'name': 'Employee User',
            'login': 'emp',
            'password': 'emp',
            'alias_name': 'emp',
            'email': 'emp@example.com',
            'groups_id': [(6, 0, [self.group_user_id])]
        }).id

        # Create employee and linked to above created users
        self.hr_employee_user = self.HrEmployee.create({
            'name': 'Employee User',
            'user_id': self.res_users_employee
        }).id
        self.hr_employee_officer = self.HrEmployee.create({
            'name': 'HR Officer',
            'user_id': self.res_users_hr_officer
        }).id
