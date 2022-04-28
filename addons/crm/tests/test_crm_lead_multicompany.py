# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.crm.tests.common import TestCrmCommon
from odoo.exceptions import AccessError, UserError
from odoo.tests import Form, tagged
from odoo.tests.common import users


@tagged('multi_company')
class TestCRMLeadMultiCompany(TestCrmCommon):

    @classmethod
    def setUpClass(cls):
        super(TestCRMLeadMultiCompany, cls).setUpClass()
        cls._activate_multi_company()

    def test_initial_data(self):
        """ Ensure global data for those tests to avoid unwanted side effects """
        self.assertFalse(self.sales_team_1.company_id)
        self.assertEqual(self.user_sales_manager_mc.company_id, self.company_2)

    @users('user_sales_manager_mc')
    def test_lead_mc_company_computation(self):
        """ Test lead company computation depending on various parameters. Check
        the company is set from the team_id or from the env if there is no team.
        No responsible, no team, should not limit company. """
        # Lead with falsy values are kept
        lead_no_team = self.env['crm.lead'].create({
            'name': 'L1',
            'team_id': False,
            'user_id': False,
        })
        self.assertFalse(lead_no_team.company_id)
        self.assertFalse(lead_no_team.team_id)
        self.assertFalse(lead_no_team.user_id)

        # Lead with team with company sets company
        lead_team_c2 = self.env['crm.lead'].create({
            'name': 'L2',
            'team_id': self.team_company2.id,
            'user_id': False,
        })
        self.assertEqual(lead_team_c2.company_id, self.company_2)
        self.assertFalse(lead_team_c2.user_id)

        # Update team wo company: reset lead company also
        lead_team_c2.team_id = self.sales_team_1
        self.assertFalse(lead_team_c2.company_id)

        # Lead with global team has no company
        lead_team_no_company = self.env['crm.lead'].create({
            'name': 'No company',
            'team_id': self.sales_team_1.id,
            'user_id': False,
        })
        self.assertFalse(lead_no_team.company_id)

        # Update team w company updates company
        lead_team_no_company.team_id = self.team_company2
        self.assertEqual(lead_team_no_company.company_id, self.company_2)
        self.assertEqual(lead_team_no_company.team_id, self.team_company2)

    @users('user_sales_manager_mc')
    def test_lead_mc_company_computation_env_team_norestrict(self):
        """ Check that the computed company is the one coming from the team even
        when it's not in self.env.companies. This may happen when running the
        Lead Assignment task. """
        LeadUnsyncCids = self.env['crm.lead'].with_context(allowed_company_ids=[self.company_main.id])
        self.assertEqual(LeadUnsyncCids.env.company, self.company_main)
        self.assertEqual(LeadUnsyncCids.env.companies, self.company_main)
        self.assertEqual(LeadUnsyncCids.env.user.company_id, self.company_2)

        # multicompany raises if trying to create manually
        with self.assertRaises(AccessError):
            lead = LeadUnsyncCids.create({
                'name': 'My Lead MC',
                'team_id': self.team_company2.id
            })

        # simulate auto-creation through sudo (assignment-like)
        lead = LeadUnsyncCids.sudo().create({
            'name': 'My Lead MC',
            'team_id': self.team_company2.id,
        })
        self.assertEqual(lead.company_id, self.company_2)
        self.assertEqual(lead.team_id, self.team_company2)
        self.assertEqual(lead.user_id, self.user_sales_manager_mc)

    @users('user_sales_manager_mc')
    def test_lead_mc_company_computation_env_user_restrict(self):
        """ Check that the computed company is allowed (aka in self.env.companies).
        If the assigned team has a set company, the lead has the same one. Otherwise, use one
        allowed by user, preferentially choose env current company, user's company otherwise."""
        # User is logged in company_main even their default company is company_2
        LeadUnsyncCids = self.env['crm.lead'].with_context(allowed_company_ids=[self.company_main.id])
        self.assertEqual(LeadUnsyncCids.env.company, self.company_main)
        self.assertEqual(LeadUnsyncCids.env.companies, self.company_main)
        self.assertEqual(LeadUnsyncCids.env.user.company_id, self.company_2)

        # simulate auto-creation through sudo (assignment-like)
        lead_1_auto = LeadUnsyncCids.sudo().create({
            'name': 'My Lead MC 1 Auto',
        })
        self.assertEqual(lead_1_auto.team_id, self.sales_team_1,
                         '[Auto/1] First available team in current company should have been assigned (fallback as user in no team in Main Company).')
        self.assertEqual(lead_1_auto.company_id, self.company_main,
                         '[Auto/1] Current company should be set on the lead as no company was assigned given by team and company is allowed for user.')
        self.assertEqual(lead_1_auto.user_id, self.user_sales_manager_mc, '[Auto/1] Current user should have been assigned.')
        # manual creation
        lead_1_manual = LeadUnsyncCids.create({
            'name': 'My Lead MC',
        })
        self.assertEqual(lead_1_manual.team_id, self.sales_team_1,
                         '[Auto/1] First available team in current company should have been assigned (fallback as user in no team in Main Company).')
        self.assertEqual(lead_1_manual.company_id, self.company_main,
                         '[Auto/1] Current company should be set on the lead as no company was given by team and company is allowed for user.')
        self.assertEqual(lead_1_manual.user_id, self.user_sales_manager_mc, '[Manual/1] Current user should have been assigned.')

        # Logged on other company will use that one for the lead company with sales_team_2 as is assigned to company_2
        LeadUnsyncCids = self.env['crm.lead'].with_context(allowed_company_ids=[self.company_main.id, self.company_2.id])
        LeadUnsyncCids = LeadUnsyncCids.with_company(self.company_2)
        self.assertEqual(LeadUnsyncCids.env.company, self.company_2)

        lead_2_auto = LeadUnsyncCids.sudo().create({
            'name': 'My Lead MC 2 Auto',
        })
        self.assertEqual(lead_2_auto.team_id, self.team_company2,
                         '[Auto/2] First available team user is a member of, in current company, should have been assigned.')
        self.assertEqual(lead_2_auto.company_id, self.company_2,
                         '[Auto/2] Current company should be set on the lead as company was assigned on team.')
        self.assertEqual(lead_2_auto.user_id, self.user_sales_manager_mc, '[Auto/2] Current user should have been assigned.')
        lead_2_manual = LeadUnsyncCids.create({
            'name': 'My Lead MC 2 Manual',
        })
        self.assertEqual(lead_2_manual.team_id, self.team_company2,
                         '[Manual/2] First available team user is a member of, in current company, should have been assigned.')
        self.assertEqual(lead_2_manual.company_id, self.company_2,
                         '[Manual/2] Current company should be set on the lead as company was assigned on team.')
        self.assertEqual(lead_2_manual.user_id, self.user_sales_manager_mc, '[Manual/2] Current user should have been assigned.')

        # If assigned team has no company, use company
        self.team_company2.write({'company_id': False})
        lead_3_auto = LeadUnsyncCids.sudo().create({
            'name': 'My Lead MC 3 Auto',
        })
        self.assertEqual(lead_3_auto.team_id, self.team_company2,
                         '[Auto/3] First available team user is a member of should have been assigned (fallback as no team with same company defined).')
        self.assertEqual(lead_3_auto.company_id, self.company_2,
                         '[Auto/3] Current company should be set on the lead as no company was given by team and company is allowed for user.')
        self.assertEqual(lead_3_auto.user_id, self.user_sales_manager_mc, '[Auto/3] Current user should have been assigned.')
        lead_3_manual = LeadUnsyncCids.create({
            'name': 'My Lead MC 3 Manual',
        })
        self.assertEqual(lead_3_manual.company_id, self.company_2,
                         '[Auto/3] First available team user is a member of should have been assigned (fallback as no team with same company defined).')
        self.assertEqual(lead_3_manual.team_id, self.team_company2,
                         '[Auto/3] Current company should be set on the lead as no company was given by team and company is allowed for user.')
        self.assertEqual(lead_3_manual.user_id, self.user_sales_manager_mc, '[Manual/3] Current user should have been assigned.')

        # If all teams have no company and don't have user as member, the first sales team is used.
        self.team_company2.write({'member_ids': [(3, self.user_sales_manager_mc.id)]})

        lead_4_auto = LeadUnsyncCids.sudo().create({
            'name': 'My Lead MC 4 Auto',
        })
        self.assertEqual(lead_4_auto.team_id, self.sales_team_1,
                         '[Auto/4] As no team has current user as member nor current company as company_id, first available team should have been assigned.')
        self.assertEqual(lead_4_auto.company_id, self.company_2,
                         '[Auto/4] Current company should be set on the lead as no company was given by team and company is allowed for user.')
        self.assertEqual(lead_4_auto.user_id, self.user_sales_manager_mc, '[Auto/4] Current user should have been assigned.')
        lead_4_manual = LeadUnsyncCids.create({
            'name': 'My Lead MC 4 Manual',
        })
        self.assertEqual(lead_4_manual.company_id, self.company_2,
                         '[Manual/4] As no team has current user as member nor current company as company_id, first available team should have been assigned.')
        self.assertEqual(lead_4_manual.team_id, self.sales_team_1,
                         '[Manual/4] Current company should be set on the lead as no company was given by team and company is allowed for user.')
        self.assertEqual(lead_4_manual.user_id, self.user_sales_manager_mc,
                         '[Manual/4] Current user should have been assigned.')

    @users('user_sales_manager_mc')
    def test_lead_mc_company_computation_partner_restrict(self):
        """ Check company on partner limits the company on lead. As contacts may
        be separated by company, lead with a partner should be limited to that
        company. """
        partner_c2 = self.partner_c2.with_env(self.env)
        self.assertEqual(partner_c2.company_id, self.company_2)
        lead = self.env['crm.lead'].create({
            'partner_id': partner_c2.id,
            'name': 'MC Partner, no company lead',
            'user_id': False,
            'team_id': False,
        })
        self.assertEqual(lead.company_id, self.company_2)

        partner_main = self.env['res.partner'].create({
            'company_id': self.company_main.id,
            'email': 'partner_main@multicompany.example.com',
            'name': 'Customer for Main',
        })
        lead.write({'partner_id': partner_main})
        self.assertEqual(lead.company_id, self.company_main)

        # writing current user on lead would imply putting its team and team's company
        # on lead (aka self.company_2), and this clashes with company restriction on
        # customer
        with self.assertRaises(UserError):
            lead.write({
                'user_id': self.env.user,
            })

    @users('user_sales_manager_mc')
    def test_lead_mc_company_form(self):
        """ Test lead company computation using form view """
        crm_lead_form = Form(self.env['crm.lead'])
        crm_lead_form.name = "Test Lead"

        # default values: current user, its team and therefore its company
        self.assertEqual(crm_lead_form.company_id, self.company_2)
        self.assertEqual(crm_lead_form.user_id, self.user_sales_manager_mc)
        self.assertEqual(crm_lead_form.team_id, self.team_company2)

        # remove user, team only
        crm_lead_form.user_id = self.env['res.users']
        self.assertEqual(crm_lead_form.company_id, self.company_2)
        self.assertEqual(crm_lead_form.user_id, self.env['res.users'])
        self.assertEqual(crm_lead_form.team_id, self.team_company2)

        # remove team, user only
        crm_lead_form.user_id = self.user_sales_manager_mc
        crm_lead_form.team_id = self.env['crm.team']
        self.assertEqual(crm_lead_form.company_id, self.company_2)
        self.assertEqual(crm_lead_form.user_id, self.user_sales_manager_mc)
        self.assertEqual(crm_lead_form.team_id, self.env['crm.team'])

        # remove both: void company to ease assignment
        crm_lead_form.user_id = self.env['res.users']
        self.assertEqual(crm_lead_form.company_id, self.env['res.company'])
        self.assertEqual(crm_lead_form.user_id, self.env['res.users'])
        self.assertEqual(crm_lead_form.team_id, self.env['crm.team'])

        # force company manually
        crm_lead_form.company_id = self.company_2
        lead = crm_lead_form.save()

        # user_sales_manager cannot read it due to MC rules
        with self.assertRaises(AccessError):
            lead.with_user(self.user_sales_manager).read(['name'])

    @users('user_sales_manager_mc')
    def test_lead_mc_company_form_progressives_setup(self):
        """ Specific bug reported at Task-2520276. Flow
          0) The sales team have no company set
          1) Create a lead without a user_id and a team_id
          2) Assign a team to the lead
          3) Assign a user_id

        Goal: if no company is set on the sales team the lead at step 2 should
        not have any company_id set. Previous behavior
          1) set the company of the env.user
          2) Keep the company of the lead
          3) set the user company if the current company is not one of the allowed company of the user

        Wanted behavior
          1) leave the company empty
          2) set the company of the team even if it's False (so erase the company if the team has no company set)
          3) set the user company if the current company is not one of the allowed company of the user
        """
        lead = self.env['crm.lead'].create({
            'name': 'Test Progressive Setup',
            'user_id': False,
            'team_id': False,
        })
        crm_lead_form = Form(lead)
        self.assertEqual(crm_lead_form.company_id, self.env['res.company'])

        crm_lead_form.team_id = self.sales_team_1
        self.assertEqual(crm_lead_form.company_id, self.env['res.company'])

        crm_lead_form.user_id = self.env.user
        # self.assertEqual(crm_lead_form.company_id, self.env['res.company'])  # FIXME
        self.assertEqual(crm_lead_form.company_id, self.company_2)

    @users('user_sales_manager_mc')
    def test_lead_mc_company_form_w_partner_id(self):
        """ Test lead company computation with partner having a company. """
        partner_c2 = self.partner_c2.with_env(self.env)
        crm_lead_form = Form(self.env['crm.lead'])
        crm_lead_form.name = "Test Lead"

        crm_lead_form.user_id = self.user_sales_manager_mc
        crm_lead_form.partner_id = partner_c2
        self.assertEqual(crm_lead_form.company_id, self.company_2, 'Crm: company comes from sales')
        self.assertEqual(crm_lead_form.team_id, self.team_company2, 'Crm: team comes from sales')

        # reset sales: should not reset company, as partner constrains it
        crm_lead_form.team_id = self.env['crm.team']
        crm_lead_form.user_id = self.env['res.users']
        # ensuring that company_id is not overwritten when the salesperson becomes empty (w\o any team_id)
        self.assertEqual(crm_lead_form.company_id, self.company_2, 'Crm: company comes from partner')
