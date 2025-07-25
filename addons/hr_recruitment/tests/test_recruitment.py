# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64

from odoo import Command
from odoo.fields import Domain
from odoo.tests import tagged, TransactionCase, Form


@tagged('recruitment')
class TestRecruitment(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.company = cls.env['res.company'].create({
            'name': 'Company Test',
            'country_id': cls.env.ref('base.us').id,
        })
        cls.env.user.company_id = cls.company
        cls.env.user.company_ids = [Command.set(cls.company.ids)]

        cls.TEXT = base64.b64encode(bytes("hr_recruitment", 'utf-8'))
        cls.Attachment = cls.env['ir.attachment']

    def test_infer_applicant_lang_from_context(self):
        # Prerequisites
        self.env['res.lang']._activate_lang('pl_PL')
        self.env['res.lang']._activate_lang('en_US')
        self.env['ir.default'].set('res.partner', 'lang', 'en_US')

        # Creating an applicant will create a partner (email_from inverse)
        applicant = self.env['hr.applicant'].sudo().with_context(lang='pl_PL').create({
            'partner_name': 'Test Applicant',
            'email_from': "test_aplicant@example.com"
        })
        self.assertEqual(applicant.partner_id.lang, 'pl_PL', 'Context langague not used for partner creation')

    def test_duplicate_email(self):
        # Tests that duplicate email matching is case insesitive
        dup1, dup2, no_dup = self.env['hr.applicant'].create([
            {
                'partner_name': 'Application 1',
                'email_from': 'laurie.poiret@aol.ru',
            },
            {
                'partner_name': 'Application 2',
                'email_from': 'laurie.POIRET@aol.ru',
            },
            {
                'partner_name': 'Application 3',
                'email_from': 'laure.poiret@aol.ru',
            },
        ])
        self.assertEqual(dup1.application_count, 2)
        self.assertEqual(dup2.application_count, 2)
        self.assertEqual(no_dup.application_count, 1)

    def test_similar_applicants_count(self):
        """Test that we find same applicant based on simmilar mail or phone."""
        A, B, C, D, E, F, _ = self.env['hr.applicant'].create([
            {
                'active': False,  # Refused/archived application should still count
                'partner_name': 'Application A',
                'email_from': 'abc@odoo.com',
                'partner_phone': '123',
            },
            {
                'partner_name': 'Application B',
                'partner_phone': '456',
            },
            {
                'partner_name': 'Application C',
                'email_from': 'def@odoo.com',
                'partner_phone': '123',
            },
            {
                'partner_name': 'Application D',
                'email_from': 'abc@odoo.com',
                'partner_phone': '456',
            },
            {
                'partner_name': 'Application E',
                'partner_phone': '',
            },
            {
                'partner_name': 'Application F',
                'email_from': 'ghi@odoo.com',
                'partner_phone': '789',
            },
            {
                'partner_name': 'Application G',
            },
        ])
        self.assertEqual(A.application_count, 3)  # A, C, D
        self.assertEqual(B.application_count, 2)  # B, D
        self.assertEqual(C.application_count, 2)  # C, A
        self.assertEqual(D.application_count, 3)  # D, A, B
        self.assertEqual(E.application_count, 0)  # Should not match with E and G as there is no data to use for matching.
        self.assertEqual(F.application_count, 1)  # F

    def test_talent_pool_count(self):
        tp_A, tp_B = self.env["hr.talent.pool"].create([{"name": "Cool Pool"}, {"name": "Other Pool"}])
        t_A, t_B = self.env["hr.applicant"].create(
            [
                {
                    "partner_name": "Talent A",
                    "email_from": "abc@example.com",
                    "partner_phone": "1234",
                    "linkedin_profile": "linkedin/talent",
                    "talent_pool_ids": [tp_A.id, tp_B.id],
                },
                {
                    "partner_name": "Talent B",
                    "email_from": "talent_b@example.com",
                    "partner_phone": "9999",
                    "talent_pool_ids": [tp_B.id],
                },
            ]
        )
        # The only way to create a talent is through the wizards. Talents that are
        # created through the wizard also assign their own ID as pool_applicant_id
        t_A.pool_applicant_id = t_A.id
        t_B.pool_applicant_id = t_B.id

        A, B, C, D, E, F, G = self.env["hr.applicant"].create(
            [
                {"partner_name": "A", "pool_applicant_id": t_A.id},
                {
                    "partner_name": "B",
                    "email_from": "def@example.com",
                    "partner_phone": "6789",
                    "linkedin_profile": "linkedin/b",
                    "pool_applicant_id": t_A.id,
                },
                {
                    "partner_name": "C",
                    "email_from": "def@example.com",
                },
                {
                    "partner_name": "D",
                    "partner_phone": "6789",
                },
                {
                    "partner_name": "E",
                    "linkedin_profile": "linkedin/b",
                },
                {
                    "partner_name": "F",
                    "email_from": "not_linked@example.com",
                    "partner_phone": "00000",
                    "linkedin_profile": "linkedin/not_linked",
                },
                {"partner_name": "G", "pool_applicant_id": t_B.id},
            ]
        )
        self.assertEqual(t_A.talent_pool_count, 2)
        self.assertEqual(t_B.talent_pool_count, 1)
        self.assertEqual(A.talent_pool_count, 2)
        self.assertEqual(B.talent_pool_count, 2)
        self.assertEqual(C.talent_pool_count, 2)
        self.assertEqual(D.talent_pool_count, 2)
        self.assertEqual(E.talent_pool_count, 2)
        self.assertEqual(F.talent_pool_count, 0)
        self.assertEqual(G.talent_pool_count, 1)

    def test_compute_and_search_is_applicant_in_pool(self):
        """
        Test that the _compute_is_applicant_in_pool and _search_is_applicant_in_pool
        methods return correct information.
        An application is considered to be in a pool if it is either directly linked
        to a pool (through pool_applicant_id or talents_pool_ids) or shares a phone number,
        email or linkedin with another directly linked application.
        """
        talent_pool = self.env["hr.talent.pool"].create({"name": "Cool Pool"})
        job = self.env["hr.job"].create(
            {
                "name": "Cool Job",
            }
        )
        A, B, C, D, E, F, G, H = self.env["hr.applicant"].create(
            [
                {
                    "partner_name": "Talent A",
                    "email_from": "mainTalentEmail@example.com",
                    "talent_pool_ids": talent_pool.ids,
                },
                {
                    "partner_name": "Applicant 1 B",
                    "email_from": "otherTalentEmail@example.com",
                    "partner_phone": "1234",
                    "linkedin_profile": "linkedin.com/in/applicant",
                    "job_id": job.id,
                },
                {
                    "partner_name": "Applicant 1 C",
                    "email_from": "otherTalentEmail@example.com",
                    "job_id": job.id,
                },
                {
                    "partner_name": "Applicant 1 D",
                    "partner_phone": "1234",
                    "job_id": job.id,
                },
                {
                    "partner_name": "Applicant 1 E",
                    "linkedin_profile": "linkedin.com/in/applicant",
                    "job_id": job.id,
                },
                {
                    "partner_name": "A different applicant F",
                    "email_from": "differentEmail@example.com",
                    "partner_phone": "9876",
                    "linkedin_profile": "linkedin.com/in/NotAnApplicant",
                    "job_id": job.id,
                },
                {
                    "partner_name": "Talent With No information G",
                    "talent_pool_ids": talent_pool.ids,
                },
                {
                    "partner_name": "Applicant With No information H",
                },
            ]
        )
        B.pool_applicant_id = A.id
        H.pool_applicant_id = G.id

        # Testing the compute

        # A is directly linked to Cool Pool through talent_pool_ids
        self.assertTrue(A.is_applicant_in_pool)
        # B is directly linked to Cool Pool through pool_applicant_id
        self.assertTrue(B.is_applicant_in_pool)
        # C is indirectly linked through email to B who is directly linked
        self.assertTrue(C.is_applicant_in_pool)
        # D is indirectly linked through phone to B who is directly linked
        self.assertTrue(D.is_applicant_in_pool)
        # E is indirectly linked through linkedin to B who is directly linked
        self.assertTrue(E.is_applicant_in_pool)
        # F is not linked to a Pool
        self.assertFalse(F.is_applicant_in_pool)
        # G is directly linked to Cool Pool through talent_pool_ids
        self.assertTrue(G.is_applicant_in_pool)
        # H is directly linked to Cool Pool through pool_applicant_id
        self.assertTrue(H.is_applicant_in_pool)

        # Testing the search
        # Note: For some reason testing the search does not work if the compute
        #       is not tested first which is why these two tests are in one test.
        applicant = self.env["hr.applicant"]
        in_pool_domain = applicant._search_is_applicant_in_pool("in", [True])
        in_pool_applicants = applicant.search(Domain.AND([in_pool_domain, [("company_id", "=", self.env.company.id)]]))
        out_of_pool_applicants = applicant.search(Domain.AND([~Domain(in_pool_domain), [("company_id", "=", self.env.company.id)]]))
        self.assertCountEqual(in_pool_applicants, A | B | C | D | E | G | H)
        self.assertCountEqual(out_of_pool_applicants, F)

    def test_application_no_partner_duplicate(self):
        """ Test that when applying, the existing partner
            doesn't get duplicated.
        """
        applicant_data = {
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
            'partner_name': 'Test Applicant',
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

    def test_open_refuse_applicant_wizard_without_partner_name(self):
        """Test opening the refuse wizard when the applicant has no partner_name."""
        applicant = self.env['hr.applicant'].create({
            'partner_phone': '123',
        })
        wizard = Form(self.env['applicant.get.refuse.reason'].with_context(
            default_applicant_ids=[applicant.id], active_test=False))

        wizard_applicant = wizard.applicant_ids[0]
        self.assertFalse(wizard_applicant.partner_name)

    def test_applicant_refuse_reason(self):

        refuse_reason = self.env['hr.applicant.refuse.reason'].create([{'name': 'Fired'}])

        app_1, app_2 = self.env['hr.applicant'].create([
            {
                'partner_name': 'Laurie Poiret',
                'email_from': 'laurie.poiret@aol.ru',
            },
            {
                'partner_name': 'Mitchell Admin',
                'email_from': 'mitchell_admin@example.com',
            },
        ])

        applicant_get_refuse_reason = self.env['applicant.get.refuse.reason'].create([{
            'refuse_reason_id': refuse_reason.id,
            'applicant_ids': [app_1.id],
            'duplicates': True
        }])
        applicant_get_refuse_reason.action_refuse_reason_apply()
        self.assertFalse(self.env['hr.applicant'].search([('email_from', 'ilike', 'laurie.poiret@aol.ru')]))
        self.assertEqual(
            self.env['hr.applicant'].search([('email_from', 'ilike', 'mitchell_admin@example.com')]),
            app_2
        )

    def test_copy_attachments_while_creating_employee(self):
        """
        Test that attachments are copied when creating an employee from an applicant
        """
        applicant_1 = self.env['hr.applicant'].create({
            'partner_name': 'Applicant 1',
            'email_from': 'test_applicant@example.com'
        })
        applicant_attachment = self.Attachment.create({
            'datas': self.TEXT,
            'name': 'textFile.txt',
            'mimetype': 'text/plain',
            'res_model': applicant_1._name,
            'res_id': applicant_1.id
        })

        employee_applicant = applicant_1.create_employee_from_applicant()
        self.assertTrue(employee_applicant['res_id'])
        attachment_employee_applicant = self.Attachment.search([
            ('res_model', '=', employee_applicant['res_model']),
            ('res_id', '=', employee_applicant['res_id']),
        ])
        self.assertEqual(applicant_attachment['datas'], attachment_employee_applicant['datas'])

    def test_other_applications_count(self):
        """
        Test that the application_count field does not change
        when archiving or refusing a linked application.
        """

        A1, A2, A3 = self.env["hr.applicant"].create(
            [
                {"partner_name": "test", "email_from": "test@example.com"},
                {"partner_name": "test", "email_from": "test@example.com"},
                {"partner_name": "test", "email_from": "test@example.com"},
            ]
        )

        self.assertEqual(A1.application_count, 3)

        # Archive A2
        A2.action_archive()
        self.assertEqual(
            A1.application_count,
            3,
            "Application_count should not change when archiving a linked application",
        )
        # Refuse A3
        refuse_reason = self.env["hr.applicant.refuse.reason"].create([{"name": "Fired"}])
        applicant_get_refuse_reason = self.env["applicant.get.refuse.reason"].create(
            [
                {
                    "refuse_reason_id": refuse_reason.id,
                    "applicant_ids": [A3.id],
                }
            ]
        )
        applicant_get_refuse_reason.action_refuse_reason_apply()
        self.assertEqual(
            A1.application_count,
            3,
            "The other_applications_count should not change when refusing an application",
        )

    def test_open_other_applications_count(self):
        """
        The smart button labeled 'Other Applications N' (where N represents the number of
        other job applications linked to the same applicant) should, when clicked, open a list view
        displaying all related applications.

        This list should include both the N other applications and the current one,
        resulting in a total of N + 1 records.
        """

        A1, _, _ = self.env["hr.applicant"].create(
            [
                {"partner_name": "test", "email_from": "test@example.com"},
                {"partner_name": "test", "email_from": "test@example.com"},
                {"partner_name": "test", "email_from": "test@example.com"},
            ]
        )

        res = A1.action_open_applications()
        self.assertEqual(len(res['domain'][0][2]), 3, "The list view should display 3 applications")
