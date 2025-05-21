# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.api import Environment
import odoo.tests
from odoo.tools import html2plaintext

@odoo.tests.tagged('post_install', '-at_install')
class TestWebsiteHrRecruitmentForm(odoo.tests.HttpCase):
    def test_tour(self):
        department = self.env['hr.department'].create({'name': 'guru team'})
        job_guru = self.env['hr.job'].create({
            'name': 'Guru',
            'is_published': True,
            'department_id': department.id,
        })
        job_intern = self.env['hr.job'].create({
            'name': 'Internship',
            'is_published': True,
            'department_id': department.id,
        })
        self.start_tour(self.env['website'].get_client_action_url('/jobs'), 'website_hr_recruitment_tour_edit_form', login='admin')

        with odoo.tests.RecordCapturer(self.env['hr.applicant'], []) as capt:
            self.start_tour("/", 'website_hr_recruitment_tour')

        # check result
        self.assertEqual(len(capt.records), 2)

        guru_applicant = capt.records[1]
        self.assertEqual(guru_applicant.partner_name, 'John Smith')
        self.assertEqual(guru_applicant.email_from, 'john@smith.com')
        self.assertEqual(guru_applicant.partner_mobile, '118.218')
        self.assertEqual(html2plaintext(guru_applicant.description), '### [GURU] HR RECRUITMENT TEST DATA ###')
        self.assertEqual(guru_applicant.job_id, job_guru)

        internship_applicant = capt.records[0]
        self.assertEqual(internship_applicant.partner_name, 'Jack Doe')
        self.assertEqual(internship_applicant.email_from, 'jack@doe.com')
        self.assertEqual(internship_applicant.partner_mobile, '118.712')
        self.assertEqual(html2plaintext(internship_applicant.description), '### HR [INTERN] RECRUITMENT TEST DATA ###')
        self.assertEqual(internship_applicant.job_id, job_intern)
