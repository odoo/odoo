# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.tests.common import SavepointCase


class TestSalesCommon(SavepointCase):

    @classmethod
    def setUpClass(cls):
        super(TestSalesCommon, cls).setUpClass()

        # Salesmen organization
        # ------------------------------------------------------------
        # Role: M (team member) R (team manager)
        # SALESMAN---------------sales_team_1
        # admin------------------M-----------
        # user_sales_manager-----R-----------
        # user_sales_leads-------M-----------
        # user_sales_salesman----/-----------

        # Sales teams organization
        # ------------------------------------------------------------
        # SALESTEAM-----------SEQU-----COMPANY
        # sales_team_1--------5--------False
        # data----------------9999-----??

        cls.company_main = cls.env.user.company_id
        cls.user_sales_manager = mail_new_test_user(
            cls.env, login='user_sales_manager',
            name='Martin Sales Manager', email='crm_manager@test.example.com',
            company_id=cls.company_main.id,
            notification_type='inbox',
            groups='sales_team.group_sale_manager,base.group_partner_manager',
        )
        cls.user_sales_leads = mail_new_test_user(
            cls.env, login='user_sales_leads',
            name='Laetitia Sales Leads', email='crm_leads@test.example.com',
            company_id=cls.company_main.id,
            notification_type='inbox',
            groups='sales_team.group_sale_salesman_all_leads,base.group_partner_manager',
        )
        cls.user_sales_salesman = mail_new_test_user(
            cls.env, login='user_sales_salesman',
            name='Orteil Sales Own', email='crm_salesman@test.example.com',
            company_id=cls.company_main.id,
            notification_type='inbox',
            groups='sales_team.group_sale_salesman',
        )
        cls.user_admin = cls.env.ref('base.user_admin')

        cls.env['crm.team'].search([]).write({'sequence': 9999})
        cls.sales_team_1 = cls.env['crm.team'].create({
            'name': 'Test Sales Team',
            'sequence': 5,
            'company_id': False,
            'user_id': cls.user_sales_manager.id,
            'member_ids': [(4, cls.user_sales_leads.id), (4, cls.user_admin.id)],
        })


class TestSalesMC(TestSalesCommon):
    """ Multi Company / Multi Sales Team environment """

    @classmethod
    def setUpClass(cls):
        super(TestSalesMC, cls).setUpClass()
        cls.company_2 = cls.env['res.company'].create({
            'name': 'New Test Company',
            'email': 'company.2@test.example.com',
            'country_id': cls.env.ref('base.fr'),
        })
        cls.team_c2 = cls.env['crm.team'].create({
            'name': 'C2 Team1',
            'sequence': 1,
            'company_id': cls.company_2.id,
        })
