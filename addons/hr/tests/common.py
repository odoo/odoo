# -*- coding: utf-8 -*-

from openerp.tests import common


class TestHrCommon(common.TransactionCase):

    def setUp(self):
        super(TestHrCommon, self).setUp()

        self.Users = self.env['res.users']

        self.group_hr_manager_id = self.env.ref('base.group_hr_manager').id
        self.group_hr_user_id = self.env.ref('base.group_hr_user').id
        self.group_user_id = self.env.ref('base.group_user').id

        # Will be used in various test cases of test_hr_flow
        self.demo_user_id = self.env.ref('base.user_demo').id
        self.main_company_id = self.env.ref('base.main_company').id
        self.main_partner_id = self.env.ref('base.main_partner').id
        self.rd_department_id = self.env.ref('hr.dep_rd').id

        # Creating three users and assigning each a group related to Human Resource Management
        self.res_users_hr_manager = self.Users.create({
                'company_id': self.main_company_id,
                'name': 'HR manager',
                'login': 'hrm',
                'password': 'hrm',
                'email': 'hrm@example.com',
                'groups_id': [(6, 0, [self.group_hr_manager_id])]
        })

        self.res_users_hr_officer = self.Users.create({
                'company_id': self.main_company_id,
                'name': 'HR Officer',
                'login': 'hro',
                'password': 'hro',
                'email': 'hro@example.com',
                'groups_id': [(6, 0, [self.group_hr_user_id])]
        })

        self.res_users_employee = self.Users.create({
                'company_id': self.main_company_id,
                'name': 'Employee',
                'login': 'emp',
                'password': 'emp',
                'email': 'emp@example.com',
                'groups_id': [(6, 0, [self.group_user_id])]
        })

        # Will be used to test the flow of jobs(i.e. opening the job position for "Developer" for 
        # recruitment and closing it after recruitment done)
        self.job_developer = self.env(user=self.res_users_hr_officer.id).ref('hr.job_developer')
        self.employee_niv = self.env(user=self.res_users_hr_officer.id).ref('hr.employee_niv')
