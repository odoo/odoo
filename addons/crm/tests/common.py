# -*- coding: utf-8 -*-

from odoo.tests.common import TransactionCase
from odoo.addons.mail.tests.common import TestMail

class TestCrm(TestMail):

    @classmethod
    def setUpClass(cls):
        super(TestCrm, cls).setUpClass()

        user_group_employee = cls.env.ref('base.group_user')
        user_group_salesman_all = cls.env.ref('base.group_sale_salesman_all_leads')

        # Test users to use through the various tests
        Users = cls.env['res.users'].with_context({'no_reset_password': True, 'mail_create_nosubscribe': True})
        cls.user_salesman_all = Users.create({
            'name': 'Riton La Chignole',
            'login': 'riton',
            'alias_name': 'riton',
            'email': 'riton.salesman_all@example.com',
            'groups_id': [(6, 0, [user_group_employee.id, user_group_salesman_all.id])]})

        cls.sales_team_1 = cls.env['crm.team'].create({
            'name': 'Test Sales Team',
            'alias_name': 'test_sales_team',
        })

class TestCrmCases(TransactionCase):

    def setUp(self):
        super(TestCrmCases, self).setUp()

        self.CrmLead = self.env['crm.lead']
        self.ResUsers = self.env['res.users']

        self.partner1_id = self.ref("base.res_partner_1")
        self.partner2_id = self.ref("base.res_partner_2")
        self.sales_team_dept_id = self.ref("sales_team.team_sales_department")
        self.stage_lead1_id = self.ref("crm.stage_lead1")

        # Create a user as 'Crm Salesmanager' and added the `sales manager` group
        self.crm_salemanager_id = self.ResUsers.create({
            'company_id': self.ref("base.main_company"),
            'name': "Crm Sales manager",
            'login': "csm",
            'email': "crmmanager@yourcompany.com",
            'groups_id': [(6, 0, [self.ref('base.group_sale_manager')])]
        }).id

        # Create a user as 'Crm Salesman' and added few groups
        self.crm_salesman_id = self.ResUsers.create({
            'company_id': self.ref("base.main_company"),
            'name': "Crm Salesman",
            'login': "csu",
            'email': "crmuser@yourcompany.com",
            'groups_id': [(6, 0, [self.ref('base.group_sale_salesman_all_leads'), self.ref('base.group_partner_manager')])]
        }).id
