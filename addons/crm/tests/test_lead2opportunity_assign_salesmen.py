# -*- coding: utf-8 -*-

from .common import TestCrmCases


class TestLead2opportunityAssignSalesmen(TestCrmCases):

    def test_lead2opportunity_assign_salesmen(self):
        """ Tests for Test Lead2opportunity Assign Salesmen """
        CrmLead2OpportunityPartnerMass = self.env['crm.lead2opportunity.partner.mass']
        SalesmanLead = self.CrmLead.sudo(self.crm_salesman_id)

        # During a lead to opp conversion, salesmen should be assigned to leads following the round-robin method.  Start by creating 4 salesmen (A to D) and 6 leads (1 to 6).
        test_res_user_01 = self.ResUsers.create({
            'name': 'Test user A',
            'login':'tua@example.com',
            'new_password': 'tua'
        })
        test_res_user_02 = self.ResUsers.create({
            'name': 'Test user B',
            'login': 'tub@example.com',
            'new_password': 'tub'
        })
        test_res_user_03 = self.ResUsers.create({
            'name': 'Test user C',
            'login': 'tuc@example.com',
            'new_password': 'tuc'
        })
        test_res_user_04 = self.ResUsers.create({
            'name': 'Test user D',
            'login': 'tud@example.com',
            'new_password': 'tud'
        })

        # Salesman also creates lead so giving access rights of salesman.
        test_crm_lead_01 = SalesmanLead.create({
            'type': 'lead',
            'name': 'Test lead 1',
            'email_from': 'Raoul Grosbedon <raoul@grosbedon.fr>',
            'stage_id': self.stage_lead1_id
        })
        test_crm_lead_02 = SalesmanLead.create({
            'type':'lead',
            'name': 'Test lead 2',
            'email_from': 'Raoul Grosbedon <raoul@grosbedon.fr>',
            'stage_id': self.stage_lead1_id
        })
        test_crm_lead_03 = SalesmanLead.create({
            'type': 'lead',
            'name': 'Test lead 3',
            'email_from': 'Raoul Grosbedon <raoul@grosbedon.fr>',
            'stage_id': self.stage_lead1_id
        })
        test_crm_lead_04 = SalesmanLead.create({
            'type': 'lead',
            'name': 'Test lead 4',
            'email_from': 'Fabrice Lepoilu',
            'stage_id': self.stage_lead1_id
        })
        test_crm_lead_05 = SalesmanLead.create({
            'type': 'lead',
            'name': 'Test lead 5',
            'email_from': 'Fabrice Lepoilu',
            'stage_id': self.stage_lead1_id
        })
        test_crm_lead_06 = SalesmanLead.create({
            'type': 'lead',
            'name': 'Test lead 6',
            'email_from': 'Agrolait SuperSeed SA',
            'stage_id': self.stage_lead1_id
        })

        lead_ids = [test_crm_lead_01.id, test_crm_lead_02.id, test_crm_lead_03.id, test_crm_lead_04.id, test_crm_lead_05.id, test_crm_lead_06.id]
        salesmen_ids = [test_res_user_01.id, test_res_user_02.id, test_res_user_03.id, test_res_user_04.id]

        # Salesman create a mass convert wizard and convert all the leads.
        context = {'active_model': 'crm.lead', 'active_ids': lead_ids, 'active_id': test_crm_lead_01.id}
        mass = CrmLead2OpportunityPartnerMass.sudo(self.crm_salesman_id).with_context(context).create({
            'user_ids': [(6, 0, salesmen_ids)],
            'team_id': self.sales_team_dept_id,
            'deduplicate': False,
            'force_assignation': True
        })
        mass.sudo(self.crm_salesman_id).mass_convert()

        # The leads should now be opps with a salesman and a salesteam.  Also, salesmen should have been assigned following a round-robin method.
        opps = self.CrmLead.browse(lead_ids)
        i = 0
        for opp in opps:
            self.assertEqual(opp.type, 'opportunity', 'Type mismatch: this should be an opp, not a lead')
            self.assertEqual(opp.user_id.id, salesmen_ids[i], 'Salesman mismatch: expected salesman %r, got %r' % (salesmen_ids[i], opp.user_id.id))
            i = i + 1 if (i < len(salesmen_ids) - 1) else 0
