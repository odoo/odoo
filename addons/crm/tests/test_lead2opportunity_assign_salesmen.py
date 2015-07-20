# -*- coding: utf-8 -*-

from openerp.addons.crm.tests.test_crm_access_group_users import TestCrmAccessGroupUsers

class TestLead2opportunityAssignSalesmen(TestCrmAccessGroupUsers):

    def test_lead2opportunity_assign_salesmen(self):
        """ Tests for Test Lead2opportunity Assign Salesmen """
        ResUsers = self.env['res.users']
        CrmLead = self.env['crm.lead']
        CrmLead2OpportunityPartnerMass = self.env['crm.lead2opportunity.partner.mass']

        # During a lead to opp conversion, salesmen should be assigned to leads following the round-robin method.  Start by creating 4 salesmen (A to D) and 6 leads (1 to 6).
        test_res_user_01 = ResUsers.create(
            dict(
                name='Test user A',
                login='tua@example.com',
                new_password='tua',
            ))
        test_res_user_02 = ResUsers.create(
            dict(
                name='Test user B',
                login='tub@example.com',
                new_password='tub',
            ))
        test_res_user_03 = ResUsers.create(
            dict(
                name='Test user C',
                login='tuc@example.com',
                new_password='tuc',
            ))
        test_res_user_04 = ResUsers.create(
            dict(
                name='Test user D',
                login='tud@example.com',
                new_password='tud',
            ))

        # Salesman also creates lead so giving access rights of salesman.
        test_crm_lead_01 = CrmLead.sudo(self.crm_res_users_salesman.id).create(
            dict(
                lead_type='lead',
                name='Test lead 1',
                email_from='Raoul Grosbedon <raoul@grosbedon.fr>',
                stage_id=self.env.ref('crm.stage_lead1').id,
            ))
        test_crm_lead_02 = CrmLead.sudo(self.crm_res_users_salesman.id).create(
            dict(
                lead_type='lead',
                name='Test lead 2',
                email_from='Raoul Grosbedon <raoul@grosbedon.fr>',
                stage_id=self.env.ref('crm.stage_lead1').id,
            ))
        test_crm_lead_03 = CrmLead.sudo(self.crm_res_users_salesman.id).create(
            dict(
                lead_type='lead',
                name='Test lead 3',
                email_from='Raoul Grosbedon <raoul@grosbedon.fr>',
                stage_id=self.env.ref('crm.stage_lead1').id,
            ))
        test_crm_lead_04 = CrmLead.sudo(self.crm_res_users_salesman.id).create(
            dict(
                lead_type='lead',
                name='Test lead 4',
                email_from='Fabrice Lepoilu',
                stage_id=self.env.ref('crm.stage_lead1').id,
            ))
        test_crm_lead_05 = CrmLead.sudo(self.crm_res_users_salesman.id).create(
            dict(
                lead_type='lead',
                name='Test lead 5',
                email_from='Fabrice Lepoilu',
                stage_id=self.env.ref('crm.stage_lead1').id,
            ))
        test_crm_lead_06 = CrmLead.sudo(self.crm_res_users_salesman.id).create(
            dict(
                lead_type='lead',
                name='Test lead 6',
                email_from='Agrolait SuperSeed SA',
                stage_id=self.env.ref('crm.stage_lead1').id,
            ))

        lead_ids = [test_crm_lead_01.id, test_crm_lead_02.id, test_crm_lead_03.id, test_crm_lead_04.id, test_crm_lead_05.id, test_crm_lead_06.id]
        salesmen_ids = [test_res_user_01.id, test_res_user_02.id, test_res_user_03.id, test_res_user_04.id]

        # Salesman create a mass convert wizard and convert all the leads.
        context = {'active_model': 'crm.lead', 'active_ids': lead_ids, 'active_id': test_crm_lead_01.id}
        print ">>>>>>>>>>salesmen_ids>>salesmen_ids>>>", salesmen_ids
        mass = CrmLead2OpportunityPartnerMass.sudo(self.crm_res_users_salesman.id).with_context(context).create(
            dict(
                user_ids=[(6, 0, salesmen_ids)],
                team_id=self.env.ref('sales_team.team_sales_department').id,
                deduplicate=False,
                force_assignation=True,
            ))
        mass.mass_convert()

        # The leads should now be opps with a salesman and a salesteam.  Also, salesmen should have been assigned following a round-robin method.
        opps = CrmLead.browse(lead_ids)
        i = 0
        for opp in opps:
            self.assertEqual(opp.lead_type, 'opportunity', 'Type mismatch: this should be an opp, not a lead')
            self.assertEqual(opp.user_id.id, salesmen_ids[i], 'Salesman mismatch: expected salesman %r, got %r' % (salesmen_ids[i], opp.user_id.id))
            i = i+1 if (i < len(salesmen_ids) - 1) else 0
