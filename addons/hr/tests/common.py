# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common


class TestHrCommon(common.TransactionCase):

    def setUp(self):
        super(TestHrCommon, self).setUp()

        self.Users = self.env['res.users']

        self.group_hr_manager_id = self.ref('hr.group_hr_manager')
        self.group_hr_user_id = self.ref('hr.group_hr_user')
        self.group_user_id = self.ref('base.group_user')

        # Will be used in various test cases of test_hr_flow
        self.demo_user_id = self.ref('base.user_demo')
        self.main_company_id = self.ref('base.main_company')
        self.main_partner_id = self.ref('base.main_partner')
        self.rd_department_id = self.ref('hr.dep_rd')

        # Creating three users and assigning each a group related to Human Resource Management
        self.res_users_hr_manager = self.Users.create({
            'company_id': self.main_company_id,
            'name': 'HR manager',
            'login': 'hrm',
            'email': 'hrm@example.com',
            'groups_id': [(6, 0, [self.group_hr_manager_id])]
        })

        self.res_users_hr_officer = self.Users.create({
            'company_id': self.main_company_id,
            'name': 'HR Officer',
            'login': 'hro',
            'email': 'hro@example.com',
            'groups_id': [(6, 0, [self.group_hr_user_id])]
        })

        self.res_users_employee = self.Users.create({
            'company_id': self.main_company_id,
            'name': 'Employee',
            'login': 'emp',
            'email': 'emp@example.com',
            'groups_id': [(6, 0, [self.group_user_id])]
        })

        # Will be used to test the flow of jobs(i.e. opening the job position for "Developer" for
        # recruitment and closing it after recruitment done)
        self.job_developer = self.env(user=self.res_users_hr_officer.id).ref('hr.job_developer')
        self.employee_niv = self.env(user=self.res_users_hr_officer.id).ref('hr.employee_niv')
