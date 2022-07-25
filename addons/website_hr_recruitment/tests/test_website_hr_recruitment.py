# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.api import Environment
import odoo.tests

@odoo.tests.tagged('post_install', '-at_install')
class TestWebsiteHrRecruitmentForm(odoo.tests.HttpCase):
    def test_tour(self):
        job_guru = self.env['hr.job'].create({
            'name': 'Guru',
            'is_published': True,
        })
        job_intern = self.env['hr.job'].create({
            'name': 'Internship',
            'is_published': True,
        })
        self.start_tour('/', 'website_hr_recruitment_tour_edit_form', login='admin')
        self.start_tour('/', 'website_hr_recruitment_tour')

        # check result
        guru_applicant = self.env['hr.applicant'].search([('description', '=', '### [GURU] HR RECRUITMENT TEST DATA ###'),
                                                        ('job_id', '=', job_guru.id),])
        self.assertEqual(len(guru_applicant), 1)
        self.assertEqual(guru_applicant.partner_name, 'John Smith')
        self.assertEqual(guru_applicant.email_from, 'john@smith.com')
        self.assertEqual(guru_applicant.partner_phone, '118.218')

        internship_applicant = self.env['hr.applicant'].search([('description', '=', '### HR [INTERN] RECRUITMENT TEST DATA ###'),
                                                                ('job_id', '=', job_intern.id),])
        self.assertEqual(len(internship_applicant), 1)
        self.assertEqual(internship_applicant.partner_name, 'Jack Doe')
        self.assertEqual(internship_applicant.email_from, 'jack@doe.com')
        self.assertEqual(internship_applicant.partner_phone, '118.712')
