# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.api import Environment
import odoo.tests
from odoo.tools import html2plaintext
import unittest

from odoo.addons.http_routing.tests.common import MockRequest
from odoo.addons.website_hr_recruitment.controllers.main import WebsiteHrRecruitment

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
        self.start_tour(self.env['website'].get_client_action_url('/jobs'), 'model_required_field_should_have_action_name', login='admin')

        self.start_tour(self.env['website'].get_client_action_url('/jobs'), 'website_hr_recruitment_tour_edit_form', login='admin')

        with odoo.tests.RecordCapturer(self.env['hr.applicant']) as capt:
            self.start_tour("/", 'website_hr_recruitment_tour')

        # check result
        self.assertEqual(len(capt.records), 2)

        guru_applicant = capt.records[0]
        self.assertEqual(guru_applicant.partner_name, 'John Smith')
        self.assertEqual(guru_applicant.email_from, 'john@smith.com')
        self.assertEqual(guru_applicant.partner_phone, '118.218')
        self.assertTrue(
            "Other Information:\n___________\n\nShort introduction from applicant : ### [GURU] HR RECRUITMENT TEST DATA ###"
            in guru_applicant.message_ids.mapped(lambda m: html2plaintext(m.body))
        )
        self.assertEqual(guru_applicant.job_id, job_guru)

        internship_applicant = capt.records[1]
        self.assertEqual(internship_applicant.partner_name, 'Jack Doe')
        self.assertEqual(internship_applicant.email_from, 'jack@doe.com')
        self.assertEqual(internship_applicant.partner_phone, '118.712')
        self.assertTrue(
            "Other Information:\n___________\n\nShort introduction from applicant : ### HR [INTERN] RECRUITMENT TEST DATA ###"
            in internship_applicant.message_ids.mapped(lambda m: html2plaintext(m.body))
        )
        self.assertEqual(internship_applicant.job_id, job_intern)

    def test_jobs_listing_city_unspecified(self):
        """ Test that the jobs listing page does not crash when a job has no address. """
        an_address, no_address = self.env['res.partner'].create([
            {
                'name': "An address",
                'company_id': self.env.company.id,
                'city': 'Paris',
            },
            {
                'name': "No address",
                'company_id': self.env.company.id,
            },
        ])
        self.env['hr.job'].create([
            {
                'name': 'Job A',
                'is_published': True,
                'address_id': an_address.id,
            },
            {
                'name': 'Job B',
                'is_published': True,
                'address_id': no_address.id,
            },
        ])
        WebsiteHrRecruitmentController = WebsiteHrRecruitment()
        with MockRequest(self.env, website=self.env['website'].browse(1)):
            response = WebsiteHrRecruitmentController.jobs()
        self.assertEqual(response.status, '200 OK')

    def test_apply_job(self):
        """ Test a user can apply to a job via the website form and add extra information inside custom field """
        research_and_development_department = self.env['hr.department'].create({
            'name': 'R&D',
        })
        developer_job = self.env['hr.job'].create({
            'name': 'Developer',
            'is_published': True,
            'department_id': research_and_development_department.id
        })
        applicant_data = {
            'partner_name': 'Georges',
            'email_from': 'georges@test.com',
            'partner_phone': '12345678',
            'job_id': developer_job.id,
            'department_id': research_and_development_department.id,
            'description': 'This is a short introduction',
            'Additional info': 'Test',
        }
        self.authenticate(None, None)
        response = self.url_open('/website/form/hr.applicant', data=applicant_data)
        applicant = self.env['hr.applicant'].browse(response.json().get('id'))
        self.assertTrue(applicant.exists())
        self.assertEqual(applicant.job_id, developer_job)
        self.assertEqual(applicant.department_id, research_and_development_department)
        self.assertEqual(applicant.partner_name, 'Georges')
        self.assertEqual(applicant.email_from, 'georges@test.com')
        self.assertEqual(applicant.partner_phone, '12345678')
        self.assertTrue(
            any(
                html2plaintext(message.body) == 'Other Information:\n___________\n\ndescription : This is a short introduction\nAdditional info : Test'
                for message in applicant.message_ids
            ),
            "One message in the chatter should contain the extra information filled in by the applicant"
        )
