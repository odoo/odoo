from openerp.addons.website_crm_score.tests.common import TestScoring


class test_dry_run(TestScoring):

    def test_dry_run(self):
        cr, uid = self.cr, self.uid

        # scoring
        self.website_crm_score.assign_scores_to_leads(cr, uid)

        l0 = self.crm_lead.read(cr, uid, self.lead0, ['score'], None)
        l1 = self.crm_lead.read(cr, uid, self.lead1, ['score'], None)
        l2 = self.crm_lead.read(cr, uid, self.lead2, ['score'], None)

        self.assertEqual(l0['score'], 1000, 'scoring failed')
        self.assertEqual(l1['score'], 900, 'scoring failed')
        self.assertEqual(l2['score'], 0, 'scoring failed')

        # dry run
        self.section.dry_assign_leads(cr, uid, None)

        fields = ['section_id', 'user_id', 'lead_id']

        dr0_sect = self.leads_dry_run.search_read(cr, uid, [('lead_id', '=', self.lead0), ('user_id', '=', False)], fields)[0]
        dr0_user = self.leads_dry_run.search_read(cr, uid, [('lead_id', '=', self.lead0), ('user_id', '!=', False)], fields)[0]

        dr1_sect = self.leads_dry_run.search_read(cr, uid, [('lead_id', '=', self.lead1), ('user_id', '=', False)], fields)[0]
        dr1_user = self.leads_dry_run.search_read(cr, uid, [('lead_id', '=', self.lead1), ('user_id', '!=', False)], fields)[0]

        dr2 = self.leads_dry_run.search_read(cr, uid, [('lead_id', '=', self.lead2)], fields)

        self.assertEqual(dr0_sect['section_id'][0], self.section0, 'dry run failed')
        self.assertEqual(dr0_user['section_id'][0], self.section0, 'dry run failed')
        self.assertEqual(dr0_user['user_id'][0], self.salesmen0, 'dry run failed')

        self.assertEqual(dr1_sect['section_id'][0], self.section1, 'dry run failed')
        self.assertEqual(dr1_user['section_id'][0], self.section1, 'dry run failed')
        self.assertEqual(dr1_user['user_id'][0], self.salesmen1, 'dry run failed')

        self.assertEqual(dr2, [], 'dry run failed')

        ldr = self.leads_dry_run.search_count(cr, uid, [], None)
        self.assertEqual(ldr, 4, 'wrong number of dry run created')

        # assignement after dry run
        self.leads_dry_run.assign_leads(cr, uid, None)

        l0 = self.crm_lead.read(cr, uid, self.lead0, ['section_id', 'user_id'], None)
        l1 = self.crm_lead.read(cr, uid, self.lead1, ['section_id', 'user_id'], None)
        l2 = self.crm_lead.read(cr, uid, self.lead2, ['section_id', 'user_id'], None)

        self.assertEqual(l0['section_id'][0], self.section0, 'assignation failed')
        self.assertEqual(l1['section_id'][0], self.section1, 'assignation failed')
        self.assertEqual(l2['section_id'], False, 'assignation failed')

        self.assertEqual(l0['user_id'][0], self.salesmen0, 'assignation failed')
        self.assertEqual(l1['user_id'][0], self.salesmen1, 'assignation failed')
        self.assertEqual(l2['user_id'], False, 'assignation failed')

        ldr = self.leads_dry_run.search_count(cr, uid, [], None)

        self.assertEqual(ldr, 0, 'dry run not removed correctly')
