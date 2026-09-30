# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import TransactionCase

from odoo.addons.base.tests.common import BaseCommon
from odoo.addons.mail.tests.common import mail_new_test_user


class SalesTeamCommon(BaseCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.group_sale_salesman = cls.env.ref('sales_team.group_sale_salesman')
        cls.group_sale_manager = cls.env.ref('sales_team.group_sale_manager')

        cls.sale_user = cls.env['res.users'].create({
            'name': 'Test Salesman',
            'login': 'salesman',
            'password': 'salesman',
            'email': 'default_user_salesman@example.com',
            'signature': '--\nMark',
            'notification_type': 'email',
            'group_ids': [(6, 0, cls.group_sale_salesman.ids)],
        })
        cls.sale_manager = cls.env['res.users'].create({
            'name': 'Test Sales Manager',
            'login': 'salesmanager',
            'password': 'salesmanager',
            'email': 'default_user_salesmanager@example.com',
            'signature': '--\nDamien',
            'notification_type': 'email',
            'group_ids': [(6, 0, cls.group_sale_manager.ids)],
        })
        cls.sale_team = cls.env['crm.team'].create({
            'name': 'Test Sales Team',
        })
        # Disable other teams (demo data/existing data)
        cls.env['crm.team'].search([
            ('id', '!=', cls.sale_team.id),
        ]).action_archive()

    @classmethod
    def get_default_groups(cls):
        groups = super().get_default_groups()
        return groups | cls.quick_ref('sales_team.group_sale_manager')


class TestSalesCommon(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super(TestSalesCommon, cls).setUpClass()
        cls.env['ir.config_parameter'].set_param('sales_team.membership_multi', False)

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
        cls.user_admin = cls.env.ref('base.user_admin')
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

        cls.env['crm.team'].search([]).write({'sequence': 9999})
        cls.sales_team_1 = cls.env['crm.team'].create({
            'name': 'Test Sales Team',
            'sequence': 5,
            'company_id': False,
            'user_id': cls.user_sales_manager.id,
        })
        cls.sales_team_1_m1 = cls.env['crm.team.member'].create({
            'user_id': cls.user_sales_leads.id,
            'crm_team_id': cls.sales_team_1.id,
        })
        cls.sales_team_1_m2 = cls.env['crm.team.member'].create({
            'user_id': cls.user_admin.id,
            'crm_team_id': cls.sales_team_1.id,
        })


class TestSalesMC(TestSalesCommon):
    """ Multi Company / Multi Sales Team environment """

    @classmethod
    def setUpClass(cls):
        """ Teams / Company

          * sales_team_1: False
          * team_c2: company_2
          * team_mc: company_main
        """
        super(TestSalesMC, cls).setUpClass()
        cls.company_2 = cls.env['res.company'].create({
            'name': 'New Test Company',
            'email': 'company.2@test.example.com',
            'country_id': cls.env.ref('base.fr').id,
        })
        cls.team_c2 = cls.env['crm.team'].create({
            'name': 'C2 Team1',
            'sequence': 1,
            'user_id': False,
            'company_id': cls.company_2.id,
        })
        cls.team_mc = cls.env['crm.team'].create({
            'name': 'MainCompany Team',
            'user_id': cls.user_admin.id,
            'sequence': 3,
            'company_id': cls.company_main.id
        })

        # admin and sale manager belong to new company also
        (cls.user_admin | cls.user_sales_manager).write({
            'company_ids': [(4, cls.company_2.id)]
        })
