# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase
from odoo.addons.mail.tests.common import TestMail

class TestCrm(TestMail):

    @classmethod
    def setUpClass(cls):
        super(TestCrm, cls).setUpClass()

        user_group_employee = cls.env.ref('base.group_user')
        user_group_salesman_all = cls.env.ref('sales_team.group_sale_salesman_all_leads')

        # Test users to use through the various tests
        Users = cls.env['res.users'].with_context({'no_reset_password': True, 'mail_create_nosubscribe': True})
        cls.user_salesman_all = Users.create({
            'name': 'Riton La Chignole',
            'login': 'riton',
            'email': 'riton.salesman_all@example.com',
            'groups_id': [(6, 0, [user_group_employee.id, user_group_salesman_all.id])]
        })

        cls.sales_team_1 = cls.env['crm.team'].create({
            'name': 'Test Sales Team',
            'alias_name': 'test_sales_team',
        })


class TestCrmCases(TransactionCase):

    def setUp(self):
        super(TestCrmCases, self).setUp()

        # Create a user as 'Crm Salesmanager' and added the `sales manager` group
        self.crm_salemanager = self.env['res.users'].create({
            'company_id': self.env.ref("base.main_company").id,
            'name': "Crm Sales manager",
            'login': "csm",
            'email': "crmmanager@yourcompany.com",
            'groups_id': [(6, 0, [self.ref('sales_team.group_sale_manager')])]
        })

        # Create a user as 'Crm Salesman' and added few groups
        self.crm_salesman = self.env['res.users'].create({
            'company_id': self.env.ref("base.main_company").id,
            'name': "Crm Salesman",
            'login': "csu",
            'email': "crmuser@yourcompany.com",
            'groups_id': [(6, 0, [self.env.ref('sales_team.group_sale_salesman_all_leads').id, self.env.ref('base.group_partner_manager').id])]
        })
