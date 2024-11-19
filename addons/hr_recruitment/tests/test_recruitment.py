# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64

from odoo.tests import tagged, TransactionCase

@tagged('recruitment')
class TestRecruitment(TransactionCase):

    def setUp(self):
        self.TEXT = base64.b64encode(bytes("hr_recruitment", 'utf-8'))
        self.Attachment = self.env['ir.attachment']
        self.Candidate = self.env['hr.candidate']
        self.candidate_0 = self.Candidate.create({
            'partner_name': 'Test Candidate',
            'email_from': 'testcandidate@example.com'
        })
        self.candidate_1 = self.Candidate.create({
            'partner_name': 'Test Candidate 1',
            'email_from': 'testcandidate1@example.com'
        })
        self.applicant_1 = self.env['hr.applicant'].create({
            'partner_name': 'Applicant 1',
            'candidate_id': self.candidate_1.id,
        })
        return super().setUp()

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

    def test_target_on_application_hiring(self):
        """
        Test that the target is updated when hiring an applicant
        """
        job = self.env['hr.job'].create({
            'name': 'Test Job',
            'no_of_recruitment': 1,
        })
        applicant = self.env['hr.applicant'].create({
            'candidate_id': self.env['hr.candidate'].create({'partner_name': 'Test Applicant'}).id,
            'job_id': job.id,
        })
        stage_new = self.env['hr.recruitment.stage'].create({
            'name': 'New',
            'sequence': 0,
            'hired_stage': False,
        })
        stage_hired = self.env['hr.recruitment.stage'].create({
            'name': 'Hired',
            'sequence': 1,
            'hired_stage': True,
        })
        self.assertEqual(job.no_of_recruitment, 1)
        applicant.stage_id = stage_hired 
        self.assertEqual(job.no_of_recruitment, 0)

        applicant.stage_id = stage_new
        self.assertEqual(job.no_of_recruitment, 1)

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

    def test_copy_attachments_while_creating_employee(self):
        """
        Test that attachments are copied when creating an employee from a candidate or applicant
        """
        applicant_attachment = self.Attachment.create({
            'datas': self.TEXT,
            'name': 'textFile.txt',
            'mimetype': 'text/plain',
            'res_model': self.applicant_1._name,
            'res_id': self.applicant_1.id
        })
        candidate_attachment = self.Attachment.create({
            'datas': self.TEXT,
            'name': 'textFile.txt',
            'mimetype': 'text/plain',
            'res_model': self.candidate_0._name,
            'res_id': self.candidate_0.id
        })
        employee_candidate = self.candidate_0.create_employee_from_candidate()
        self.assertTrue(employee_candidate['res_id'])
        attachment_employee_candidate = self.Attachment.search([
            ('res_model', '=', employee_candidate['res_model']),
            ('res_id', '=', employee_candidate['res_id']),
        ])
        self.assertEqual(candidate_attachment['datas'], attachment_employee_candidate['datas'])

        employee_applicant = self.applicant_1.create_employee_from_applicant()
        self.assertTrue(employee_applicant['res_id'])
        attachment_employee_applicant = self.Attachment.search([
            ('res_model', '=', employee_applicant['res_model']),
            ('res_id', '=', employee_applicant['res_id']),
        ])
        self.assertEqual(applicant_attachment['datas'], attachment_employee_applicant['datas'])
