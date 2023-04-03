# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.crm.tests.test_crm_lead_assignment import TestLeadAssignCommon
from odoo.tests.common import tagged


@tagged('lead_assign')
class TestSalesLeadAssign(TestLeadAssignCommon):
    def test_cron_assign_leads(self):
        """ Test leads assignment with sale orders from different companies are not merged. """
        def _create_crm_lead(name, email, company_id=False, lead_type="lead"):
            return self.env['crm.lead'].create({
                'name': name,
                'email_from': email,
                'type': lead_type,
                'company_id': company_id,
                'team_id': False,
                'user_id': False,
            })

        def is_assigned(opportunity, assigned=False):
            self.assertTrue(opportunity.exists())
            self.assertEqual(bool(opportunity.team_id), assigned)
            self.assertEqual(bool(opportunity.user_id), assigned)

        company_1 = self.env.ref('base.main_company')
        email = ['test1@test.example.com', 'test2@test.example.com', 'test3@test.example.com', 'test4@test.example.com', 'test5@test.example.com']
        self._activate_multi_company()
        self.team_company2.company_id = False

        opportunity1 = _create_crm_lead("Opportunity 1 without sale order and company1", email[0], company_1.id, lead_type="opportunity")
        dup_opportunity1 = _create_crm_lead("Duplicate of opportunity 1 with sale order and company2", email[0], self.company_2.id)

        opportunity2 = _create_crm_lead("Opportunity 2 without sale order and company 1", email[1], company_1.id, lead_type="opportunity")
        dup1_opportunity2 = _create_crm_lead("Duplicate of 1 opportunity 2 with sale order and company 2", email[1], self.company_2.id)
        dup2_opportunity2 = _create_crm_lead("Duplicate 2 of opportunity 2 without sale order and company 1", email[1], company_1.id)

        opportunity3 = _create_crm_lead("Opportunity 3 with sale order and company 2", email[2], self.company_2.id, lead_type="opportunity")
        dup1_opportunity3 = _create_crm_lead("Duplicate 1 of opportunity 3 without sale order and company", email[2])
        dup2_opportunity3 = _create_crm_lead("Duplicate 2 of opportunity 3 with sale order and company 1", email[2], company_1.id)

        opportunity4 = _create_crm_lead("Opportunity 4 without sale order and company 2", email[3], self.company_2.id, lead_type="opportunity")
        dup1_opportunity4 = _create_crm_lead("Duplicate 1 of opportunity 4 without sale order and company 2", email[3], self.company_2.id)
        dup2_opportunity4 = _create_crm_lead("Duplicate 2 of opportunity 4 with sale order and company 1", email[3], company_1.id)
        dup3_opportunity4 = _create_crm_lead("Duplicate 3 of opportunity 4 with sale order and company 2", email[3], self.company_2.id)

        opportunity5 = _create_crm_lead("Opportunity 5 without sale order and without company", email[4], lead_type="opportunity")
        dup1_opportunity5 = _create_crm_lead("Opportunity 5 without sale order and company 2", email[4], self.company_2.id)
        dup2_opportunity5 = _create_crm_lead("Opportunity 5 witt sale order and company 1", email[4], company_1.id)

        so_of_opportunities = {
            dup_opportunity1,
            dup1_opportunity2,
            opportunity3,
            dup2_opportunity3,
            opportunity4,
            dup2_opportunity4,
            dup3_opportunity4,
            dup1_opportunity5,
        }
        so_vals = [{
            'partner_id': self.contact_1.id,
            'company_id': opportunity.company_id.id or company_1.id,
            'opportunity_id': opportunity.id
        } for opportunity in so_of_opportunities]

        self.env['sale.order'].create(so_vals)
        self.env['crm.team']._cron_assign_leads()

        is_assigned(opportunity1)
        is_assigned(dup_opportunity1)

        is_assigned(opportunity2, True)
        is_assigned(dup1_opportunity2)
        self.assertFalse(dup2_opportunity2.exists())

        is_assigned(opportunity3, True)
        is_assigned(dup2_opportunity3)
        self.assertFalse(dup1_opportunity3.exists())

        is_assigned(opportunity4, True)
        is_assigned(dup2_opportunity4)
        self.assertFalse(dup1_opportunity4.exists())
        self.assertFalse(dup3_opportunity4.exists())

        is_assigned(opportunity5, True)
        is_assigned(dup1_opportunity5, False)
        self.assertFalse(dup2_opportunity5.exists())
