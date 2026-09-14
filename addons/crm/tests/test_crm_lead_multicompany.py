from odoo import Command
from odoo.exceptions import AccessError, UserError
from odoo.tests import Form, tagged
from odoo.tests.common import users

from odoo.addons.crm.tests.common import INCOMING_EMAIL, TestCrmCommon


@tagged("multi_company")
class TestCRMLeadMultiCompany(TestCrmCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._activate_multi_company()

    def test_initial_data(self):
        self.assertFalse(self.sales_team_1.company_id)
        self.assertEqual(self.user_sales_manager_mc.company_id, self.company_2)

    @users("user_sales_manager_mc")
    def test_lead_mc_company_computation(self):
        lead_no_team = self.env["crm.lead"].create(
            {
                "name": "L1",
                "team_id": False,
                "user_id": False,
            }
        )
        self.assertFalse(lead_no_team.company_id)
        self.assertFalse(lead_no_team.team_id)
        self.assertFalse(lead_no_team.user_id)

        lead_team_c2 = self.env["crm.lead"].create(
            {
                "name": "L2",
                "team_id": self.team_company2.id,
                "user_id": False,
            }
        )
        self.assertEqual(lead_team_c2.company_id, self.company_2)
        self.assertFalse(lead_team_c2.user_id)

        lead_team_c2.team_id = self.sales_team_1
        self.assertFalse(lead_team_c2.company_id)

        lead_team_no_company = self.env["crm.lead"].create(
            {
                "name": "No company",
                "team_id": self.sales_team_1.id,
                "user_id": False,
            }
        )
        self.assertFalse(lead_no_team.company_id)

        lead_team_no_company.team_id = self.team_company2
        self.assertEqual(lead_team_no_company.company_id, self.company_2)
        self.assertEqual(lead_team_no_company.team_id, self.team_company2)

    @users("user_sales_manager_mc")
    def test_lead_mc_company_computation_env_team_norestrict(self):
        LeadUnsyncCids = self.env["crm.lead"].with_context(
            allowed_company_ids=[self.company_main.id]
        )
        self.assertEqual(LeadUnsyncCids.env.company, self.company_main)
        self.assertEqual(LeadUnsyncCids.env.companies, self.company_main)
        self.assertEqual(LeadUnsyncCids.env.user.company_id, self.company_2)

        with self.assertRaises(AccessError):
            lead = LeadUnsyncCids.create(
                {"name": "My Lead MC", "team_id": self.team_company2.id}
            )

        lead = LeadUnsyncCids.sudo().create(
            {
                "name": "My Lead MC",
                "team_id": self.team_company2.id,
            }
        )
        self.assertEqual(lead.company_id, self.company_2)
        self.assertEqual(lead.team_id, self.team_company2)
        self.assertEqual(lead.user_id, self.user_sales_manager_mc)

    @users("user_sales_manager_mc")
    def test_lead_mc_company_computation_env_user_restrict(self):
        LeadUnsyncCids = self.env["crm.lead"].with_context(
            allowed_company_ids=[self.company_main.id]
        )
        self.assertEqual(LeadUnsyncCids.env.company, self.company_main)
        self.assertEqual(LeadUnsyncCids.env.companies, self.company_main)
        self.assertEqual(LeadUnsyncCids.env.user.company_id, self.company_2)

        lead_1_auto = LeadUnsyncCids.sudo().create(
            {
                "name": "My Lead MC 1 Auto",
            }
        )
        self.assertEqual(
            lead_1_auto.team_id,
            self.sales_team_1,
            "[Auto/1] First available team in current company should have been assigned (fallback as user in no team in Main Company).",
        )
        self.assertEqual(
            lead_1_auto.company_id,
            self.company_main,
            "[Auto/1] Current company should be set on the lead as no company was assigned given by team and company is allowed for user.",
        )
        self.assertEqual(
            lead_1_auto.user_id,
            self.user_sales_manager_mc,
            "[Auto/1] Current user should have been assigned.",
        )
        lead_1_manual = LeadUnsyncCids.create(
            {
                "name": "My Lead MC",
            }
        )
        self.assertEqual(
            lead_1_manual.team_id,
            self.sales_team_1,
            "[Auto/1] First available team in current company should have been assigned (fallback as user in no team in Main Company).",
        )
        self.assertEqual(
            lead_1_manual.company_id,
            self.company_main,
            "[Auto/1] Current company should be set on the lead as no company was given by team and company is allowed for user.",
        )
        self.assertEqual(
            lead_1_manual.user_id,
            self.user_sales_manager_mc,
            "[Manual/1] Current user should have been assigned.",
        )

        LeadUnsyncCids = self.env["crm.lead"].with_context(
            allowed_company_ids=[self.company_main.id, self.company_2.id]
        )
        LeadUnsyncCids = LeadUnsyncCids.with_company(self.company_2)
        self.assertEqual(LeadUnsyncCids.env.company, self.company_2)

        lead_2_auto = LeadUnsyncCids.sudo().create(
            {
                "name": "My Lead MC 2 Auto",
            }
        )
        self.assertEqual(
            lead_2_auto.team_id,
            self.team_company2,
            "[Auto/2] First available team user is a member of, in current company, should have been assigned.",
        )
        self.assertEqual(
            lead_2_auto.company_id,
            self.company_2,
            "[Auto/2] Current company should be set on the lead as company was assigned on team.",
        )
        self.assertEqual(
            lead_2_auto.user_id,
            self.user_sales_manager_mc,
            "[Auto/2] Current user should have been assigned.",
        )
        lead_2_manual = LeadUnsyncCids.create(
            {
                "name": "My Lead MC 2 Manual",
            }
        )
        self.assertEqual(
            lead_2_manual.team_id,
            self.team_company2,
            "[Manual/2] First available team user is a member of, in current company, should have been assigned.",
        )
        self.assertEqual(
            lead_2_manual.company_id,
            self.company_2,
            "[Manual/2] Current company should be set on the lead as company was assigned on team.",
        )
        self.assertEqual(
            lead_2_manual.user_id,
            self.user_sales_manager_mc,
            "[Manual/2] Current user should have been assigned.",
        )

        self.team_company2.write({"company_id": False})
        lead_3_auto = LeadUnsyncCids.sudo().create(
            {
                "name": "My Lead MC 3 Auto",
            }
        )
        self.assertEqual(
            lead_3_auto.team_id,
            self.team_company2,
            "[Auto/3] First available team user is a member of should have been assigned (fallback as no team with same company defined).",
        )
        self.assertEqual(
            lead_3_auto.company_id,
            self.company_2,
            "[Auto/3] Current company should be set on the lead as no company was given by team and company is allowed for user.",
        )
        self.assertEqual(
            lead_3_auto.user_id,
            self.user_sales_manager_mc,
            "[Auto/3] Current user should have been assigned.",
        )
        lead_3_manual = LeadUnsyncCids.create(
            {
                "name": "My Lead MC 3 Manual",
            }
        )
        self.assertEqual(
            lead_3_manual.company_id,
            self.company_2,
            "[Auto/3] First available team user is a member of should have been assigned (fallback as no team with same company defined).",
        )
        self.assertEqual(
            lead_3_manual.team_id,
            self.team_company2,
            "[Auto/3] Current company should be set on the lead as no company was given by team and company is allowed for user.",
        )
        self.assertEqual(
            lead_3_manual.user_id,
            self.user_sales_manager_mc,
            "[Manual/3] Current user should have been assigned.",
        )

        self.team_company2.write({"member_ids": [(3, self.user_sales_manager_mc.id)]})

        lead_4_auto = LeadUnsyncCids.sudo().create(
            {
                "name": "My Lead MC 4 Auto",
            }
        )
        self.assertEqual(
            lead_4_auto.team_id,
            self.sales_team_1,
            "[Auto/4] As no team has current user as member nor current company as company_id, first available team should have been assigned.",
        )
        self.assertEqual(
            lead_4_auto.company_id,
            self.company_2,
            "[Auto/4] Current company should be set on the lead as no company was given by team and company is allowed for user.",
        )
        self.assertEqual(
            lead_4_auto.user_id,
            self.user_sales_manager_mc,
            "[Auto/4] Current user should have been assigned.",
        )
        lead_4_manual = LeadUnsyncCids.create(
            {
                "name": "My Lead MC 4 Manual",
            }
        )
        self.assertEqual(
            lead_4_manual.company_id,
            self.company_2,
            "[Manual/4] As no team has current user as member nor current company as company_id, first available team should have been assigned.",
        )
        self.assertEqual(
            lead_4_manual.team_id,
            self.sales_team_1,
            "[Manual/4] Current company should be set on the lead as no company was given by team and company is allowed for user.",
        )
        self.assertEqual(
            lead_4_manual.user_id,
            self.user_sales_manager_mc,
            "[Manual/4] Current user should have been assigned.",
        )

    @users("user_sales_manager_mc")
    def test_lead_mc_company_computation_partner_restrict(self):
        partner_c2 = self.partner_c2.with_env(self.env)
        self.assertEqual(partner_c2.company_id, self.company_2)
        lead = self.env["crm.lead"].create(
            {
                "partner_id": partner_c2.id,
                "name": "MC Partner, no company lead",
                "user_id": False,
                "team_id": False,
            }
        )
        self.assertEqual(lead.company_id, self.company_2)

        partner_main = self.env["res.partner"].create(
            {
                "company_id": self.company_main.id,
                "email": "partner_main@multicompany.example.com",
                "name": "Customer for Main",
            }
        )
        lead.write({"partner_id": partner_main})
        self.assertEqual(lead.company_id, self.company_main)

        self.env.user.company_ids -= self.company_main
        with self.assertRaises(UserError):
            lead.write(
                {
                    "user_id": self.env.user,
                }
            )

    @users("user_sales_manager_mc")
    def test_lead_mc_company_form(self):
        crm_lead_form = Form(self.env["crm.lead"])
        crm_lead_form.name = "Test Lead"

        self.assertEqual(crm_lead_form.company_id, self.company_2)
        self.assertEqual(crm_lead_form.user_id, self.user_sales_manager_mc)
        self.assertEqual(crm_lead_form.team_id, self.team_company2)

        crm_lead_form.user_id = self.env["res.users"]
        self.assertEqual(crm_lead_form.company_id, self.company_2)
        self.assertEqual(crm_lead_form.user_id, self.env["res.users"])
        self.assertEqual(crm_lead_form.team_id, self.team_company2)

        crm_lead_form.user_id = self.user_sales_manager_mc
        crm_lead_form.team_id = self.env["team.team"]
        self.assertEqual(crm_lead_form.company_id, self.company_2)
        self.assertEqual(crm_lead_form.user_id, self.user_sales_manager_mc)
        self.assertEqual(crm_lead_form.team_id, self.env["team.team"])

        crm_lead_form.user_id = self.env["res.users"]
        self.assertEqual(crm_lead_form.company_id, self.env["res.company"])
        self.assertEqual(crm_lead_form.user_id, self.env["res.users"])
        self.assertEqual(crm_lead_form.team_id, self.env["team.team"])

        crm_lead_form.company_id = self.company_2
        lead = crm_lead_form.save()

        with self.assertRaises(AccessError):
            lead.with_user(self.user_sales_manager).read(["name"])

    @users("user_sales_manager_mc")
    def test_lead_mc_company_form_progressives_setup(self):
        lead = self.env["crm.lead"].create(
            {
                "name": "Test Progressive Setup",
                "user_id": False,
                "team_id": False,
            }
        )
        crm_lead_form = Form(lead)
        self.assertEqual(crm_lead_form.company_id, self.env["res.company"])

        crm_lead_form.team_id = self.sales_team_1
        self.assertEqual(crm_lead_form.company_id, self.env["res.company"])

        crm_lead_form.user_id = self.env.user
        self.assertEqual(crm_lead_form.company_id, self.company_2)

    @users("user_sales_manager_mc")
    def test_lead_mc_company_form_w_partner_id(self):
        partner_c2 = self.partner_c2.with_env(self.env)
        crm_lead_form = Form(self.env["crm.lead"])
        crm_lead_form.name = "Test Lead"

        crm_lead_form.user_id = self.user_sales_manager_mc
        crm_lead_form.partner_id = partner_c2
        self.assertEqual(
            crm_lead_form.company_id, self.company_2, "Crm: company comes from sales"
        )
        self.assertEqual(
            crm_lead_form.team_id, self.team_company2, "Crm: team comes from sales"
        )

        crm_lead_form.team_id = self.env["team.team"]
        crm_lead_form.user_id = self.env["res.users"]
        self.assertEqual(
            crm_lead_form.company_id, self.company_2, "Crm: company comes from partner"
        )

    def test_gateway_incompatible_company_error_on_incoming_email(self):
        self.env["ir.config_parameter"].set_param("crm.lead.auto.assignment", True)
        self.assertTrue(self.sales_team_1.lead_alias_name)
        self.assertFalse(self.sales_team_1.company_id)
        customer_company = self.env["res.partner"].create(
            {
                "company_id": self.company_2.id,
                "email": "customer.another.company@test.customer.com",
                "phone_ids": [
                    Command.create({"number": "+32455000000", "type": "landline"})
                ],
                "name": "InCompany Customer",
            }
        )

        new_lead = self.format_and_process(
            INCOMING_EMAIL,
            customer_company.email,
            self.sales_team_1.lead_alias_email,
            subject="Team having partner in company",
            target_model="crm.lead",
        )
        self.assertFalse(new_lead.user_id)
        self.assertEqual(new_lead.company_id, self.company_2)
        self.assertEqual(new_lead.email_from, customer_company.email)
        self.assertEqual(new_lead.partner_id, customer_company)
