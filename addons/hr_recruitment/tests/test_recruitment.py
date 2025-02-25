# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged, TransactionCase

@tagged('recruitment')
class TestRecruitment(TransactionCase):

    def test_infer_applicant_lang_from_context(self):
        # Prerequisites
        self.env['res.lang']._activate_lang('pl_PL')
        self.env['res.lang']._activate_lang('en_US')
        self.env['ir.default'].set('res.partner', 'lang', 'en_US')

        # Creating an applicant will create a partner (email_from inverse)
        candidate = self.env['hr.candidate'].sudo().with_context(lang='pl_PL').create({
            'partner_name': 'Test Applicant', 'email_from': "test_aplicant@example.com"
        })
        applicant = self.env['hr.applicant'].sudo().with_context(lang='pl_PL').create({
            'candidate_id': candidate.id,
        })
        self.assertEqual(applicant.partner_id.lang, 'pl_PL', 'Context langague not used for partner creation')

    def test_duplicate_email(self):
        # Tests that duplicate email match ignores case
        # And that no match is found when there is none
        dup1, dup2, no_dup = self.env['hr.applicant'].create([
            {
                'candidate_id': self.env['hr.candidate'].create({'partner_name': 'Application 1'}).id,
                'partner_name': 'Application 1',
                'email_from': 'laurie.poiret@aol.ru',
            },
            {
                'candidate_id': self.env['hr.candidate'].create({'partner_name': 'Application 2'}).id,
                'partner_name': 'Application 2',
                'email_from': 'laurie.POIRET@aol.ru',
            },
            {
                'candidate_id': self.env['hr.candidate'].create({'partner_name': 'Application 3'}).id,
                'partner_name': 'Application 3',
                'email_from': 'laure.poiret@aol.ru',
            },
        ])
        self.assertEqual(dup1.candidate_id.similar_candidates_count, 1)
        self.assertEqual(dup2.candidate_id.similar_candidates_count, 1)
        self.assertEqual(no_dup.candidate_id.similar_candidates_count, 0)

    def test_similar_candidates_count(self):
        """ Test that we find same candidates based on simmilar mail,
            phone or mobile phone.
        """
        A, B, C, D, E, _ = self.env['hr.applicant'].create([
            {
                'active': False,  # Refused/archived application should still count
                'candidate_id': self.env['hr.candidate'].create({
                    'partner_name': 'Application A',
                    'email_from': 'abc@odoo.com',
                    'partner_phone': '123',
                }).id,
            },
            {
                'candidate_id': self.env['hr.candidate'].create({
                    'partner_name': 'Application B',
                    'partner_phone': '456',
                }).id,
            },
            {
                'candidate_id': self.env['hr.candidate'].create({
                    'partner_name': 'Application C',
                    'email_from': 'def@odoo.com',
                    'partner_phone': '123',
                }).id,
            },
            {
                'candidate_id': self.env['hr.candidate'].create({
                    'partner_name': 'Application D',
                    'email_from': 'abc@odoo.com',
                    'partner_phone': '456',
                }).id,
            },
            {
                'candidate_id': self.env['hr.candidate'].create({
                    'partner_name': 'Application E',
                    'partner_phone': '',
                }).id,
            },
            {
                'candidate_id': self.env['hr.candidate'].create({
                    'partner_name': 'Application F',
                }).id,
            },
        ])
        self.assertEqual(A.candidate_id.similar_candidates_count, 2)  # C, D
        self.assertEqual(B.candidate_id.similar_candidates_count, 1)  # D, F
        self.assertEqual(C.candidate_id.similar_candidates_count, 1)  # A, D
        self.assertEqual(D.candidate_id.similar_candidates_count, 2)  # A, B, C
        self.assertEqual(E.candidate_id.similar_candidates_count, 0)  # Should not match with G

    def test_application_no_partner_duplicate(self):
        """ Test that when applying, the existing partner
            doesn't get duplicated.
        """
        applicant_data = {
            'candidate_id': self.env['hr.candidate'].create({'partner_name': 'Test - CEO'}).id,
            'partner_name': 'Test',
            'email_from': 'test@thisisatest.com',
        }
        # First application, a partner should be created
        self.env['hr.applicant'].create(applicant_data)
        partner_count = self.env['res.partner'].search_count([('email', '=', 'test@thisisatest.com')])
        self.assertEqual(partner_count, 1)
        # Second application, no partner should be created
        self.env['hr.applicant'].create(applicant_data)
        partner_count = self.env['res.partner'].search_count([('email', '=', 'test@thisisatest.com')])
        self.assertEqual(partner_count, 1)

    def test_applicant_refuse_reason(self):

        refuse_reason = self.env['hr.applicant.refuse.reason'].create([{'name': 'Fired'}])

        dup1, dup2, no_dup = self.env['hr.applicant'].create([
            {
                'candidate_id': self.env['hr.candidate'].create({'partner_name': 'Application 1'}).id,
                'partner_name': 'Laurie Poiret',
                'email_from': 'laurie.poiret@aol.ru',
            },
            {
                'candidate_id': self.env['hr.candidate'].create({'partner_name': 'Application 2'}).id,
                'partner_name': 'Laurie Poiret (lap)',
                'email_from': 'laurie.POIRET@aol.ru',
            },
            {
                'candidate_id': self.env['hr.candidate'].create({'partner_name': 'Application 3'}).id,
                'partner_name': 'Mitchell Admin',
                'email_from': 'mitchell_admin@example.com',
            },
        ])

        applicant_get_refuse_reason = self.env['applicant.get.refuse.reason'].create([{
            'refuse_reason_id': refuse_reason.id,
            'applicant_ids': [dup1.id],
            'duplicates': True
        }])
        applicant_get_refuse_reason.action_refuse_reason_apply()
        self.assertFalse(self.env['hr.applicant'].search([('email_from', 'ilike', 'laurie.poiret@aol.ru')]))
        self.assertEqual(
            self.env['hr.applicant'].search([('email_from', 'ilike', 'mitchell_admin@example.com')]),
            no_dup
        )

    def test_other_applications_count(self):
        """ Test that the other_applications_count field does not change
            when archiving or refusing an application.
        """
        candidate = self.env['hr.candidate'].create({'partner_name': 'Test'})
        application1 = self.env['hr.applicant'].create({'candidate_id': candidate.id})
        application2 = self.env['hr.applicant'].create({'candidate_id': candidate.id})
        application3 = self.env['hr.applicant'].create({'candidate_id': candidate.id})
        self.assertEqual(application1.other_applications_count, 2)
        application2.action_archive()
        self.env.invalidate_all()
        self.assertEqual(application1.other_applications_count, 2, 'The other_applications_count should not change when archiving an application')
        # refuse application3
        refuse_reason = self.env['hr.applicant.refuse.reason'].create([{'name': 'Fired'}])
        applicant_get_refuse_reason = self.env['applicant.get.refuse.reason'].create([{
            'refuse_reason_id': refuse_reason.id,
            'applicant_ids': [application3.id],
        }])
        applicant_get_refuse_reason.action_refuse_reason_apply()
        self.env.invalidate_all()
        self.assertEqual(application1.other_applications_count, 2, 'The other_applications_count should not change when refusing an application')

    def test_open_other_applications_count(self):
        """
            The smart button labeled 'Other Applications N' (where N represents the number of
            other job applications for the same candidate) should, when clicked, open a list view
            displaying all related applications.

            This list should include both the N other applications and the current one,
            resulting in a total of N + 1 records.
        """

        candidate = self.env['hr.candidate'].create({'partner_name': 'Test'})
        application1 = self.env['hr.applicant'].create({'candidate_id': candidate.id})
        application2 = self.env['hr.applicant'].create({'candidate_id': candidate.id})
        application3 = self.env['hr.applicant'].create({'candidate_id': candidate.id})
        res = application1.action_open_other_applications()
        self.assertEqual(len(res['domain'][0][2]), 3, "The list view should display 3 applications")
