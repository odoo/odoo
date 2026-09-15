from odoo.tests import TransactionCase

from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.sale.tests.common import SaleCommon, SaleUsersCommon


class SalesTeamCommon(SaleUsersCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.sale_team = cls.env["team.team"].create(
            {
                "use_sale": True,
                "name": "Test Sales Team",
            }
        )
        cls.env["team.team"].search(
            [("id", "!=", cls.sale_team.id), ("use_sale", "=", True)]
        ).action_archive()


class SalesTeamSaleCommon(SaleCommon, SalesTeamCommon):
    pass


class TestSalesCommon(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["ir.config_parameter"].set_param("sale_team.membership_multi", False)

        cls.company_main = cls.env.user.company_id
        cls.user_admin = cls.env.ref("base.user_admin")
        cls.user_sales_manager = mail_new_test_user(
            cls.env,
            login="user_sales_manager",
            name="Martin Sales Manager",
            email="crm_manager@test.example.com",
            company_id=cls.company_main.id,
            notification_type="inbox",
            groups="sale.group_sale_manager,base.group_partner_manager",
        )
        cls.user_sales_leads = mail_new_test_user(
            cls.env,
            login="user_sales_leads",
            name="Laetitia Sales Leads",
            email="crm_leads@test.example.com",
            company_id=cls.company_main.id,
            notification_type="inbox",
            groups="sale.group_sale_salesman_all_leads,base.group_partner_manager",
        )
        cls.user_sales_salesman = mail_new_test_user(
            cls.env,
            login="user_sales_salesman",
            name="Orteil Sales Own",
            email="crm_salesman@test.example.com",
            company_id=cls.company_main.id,
            notification_type="inbox",
            groups="sale.group_sale_salesman",
        )

        cls.env["team.team"].search([]).write({"sequence": 9999})
        cls.sales_team_1 = cls.env["team.team"].create(
            {
                "use_sale": True,
                "name": "Test Sales Team",
                "sequence": 5,
                "company_id": False,
                "user_id": cls.user_sales_manager.id,
            }
        )
        cls.sales_team_1_m1 = cls.env["team.member"].create(
            {
                "user_id": cls.user_sales_leads.id,
                "team_id": cls.sales_team_1.id,
            }
        )
        cls.sales_team_1_m2 = cls.env["team.member"].create(
            {
                "user_id": cls.user_admin.id,
                "team_id": cls.sales_team_1.id,
            }
        )


class TestSalesMC(TestSalesCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_2 = cls.env["res.company"].create(
            {
                "name": "New Test Company",
                "email": "company.2@test.example.com",
                "country_id": cls.env.ref("base.fr").id,
            }
        )
        cls.team_c2 = cls.env["team.team"].create(
            {
                "use_sale": True,
                "name": "C2 Team1",
                "sequence": 1,
                "user_id": False,
                "company_id": cls.company_2.id,
            }
        )
        cls.team_mc = cls.env["team.team"].create(
            {
                "use_sale": True,
                "name": "MainCompany Team",
                "user_id": cls.user_admin.id,
                "sequence": 3,
                "company_id": cls.company_main.id,
            }
        )

        (cls.user_admin | cls.user_sales_manager).write(
            {"company_ids": [(4, cls.company_2.id)]}
        )
