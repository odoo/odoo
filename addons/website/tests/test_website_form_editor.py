# Part of Odoo. See LICENSE file for full copyright and licensing details.
# -*- coding: utf-8 -*-

from odoo.http import request
from odoo.addons.base.tests.common import HttpCaseWithUserPortal
from odoo.addons.website.controllers.form import WebsiteForm
from odoo.addons.website.tools import MockRequest
from odoo.tests.common import tagged, TransactionCase


@tagged('post_install', '-at_install')
class TestWebsiteFormEditor(HttpCaseWithUserPortal):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.email = "info@yourcompany.example.com"
        cls.env.ref("base.user_admin").write({
            'name': "Mitchell Admin",
            'phone': "+1 555-555-5555",
        })

    def test_tour(self):
        self.start_tour(self.env['website'].get_client_action_url('/'), 'website_form_editor_tour', login='admin', timeout=240)
        self.start_tour('/', 'website_form_editor_tour_submit')
        self.start_tour('/', 'website_form_editor_tour_results', login="admin")

    def test_website_form_contact_us_edition_with_email(self):
        self.start_tour('/web', 'website_form_contactus_edition_with_email', login="admin")
        self.start_tour('/contactus', 'website_form_contactus_submit', login="portal")
        mail = self.env['mail.mail'].search([], order='id desc', limit=1)
        self.assertEqual(
            mail.email_to,
            'test@test.test',
            'The email was edited, the form should have been sent to the configured email')

    def test_website_form_contact_us_edition_no_email(self):
        self.env.company.email = 'website_form_contactus_edition_no_email@mail.com'
        self.start_tour('/web', 'website_form_contactus_edition_no_email', login="admin")
        self.start_tour('/contactus', 'website_form_contactus_submit', login="portal")
        mail = self.env['mail.mail'].search([], order='id desc', limit=1)
        self.assertEqual(
            mail.email_to,
            self.env.company.email,
            'The email was not edited, the form should still have been sent to the company email')

    def test_website_form_conditional_required_checkboxes(self):
        self.start_tour('/', 'website_form_conditional_required_checkboxes', login="admin")

    def test_contactus_form_email_stay_dynamic(self):
        # The contactus form should always be sent to the company email except
        # if the user explicitly changed it in the options.
        self.env.company.email = 'before.change@mail.com'
        self.start_tour('/contactus', 'website_form_contactus_change_random_option', login="admin")
        self.env.company.email = 'after.change@mail.com'
        self.start_tour('/contactus', 'website_form_contactus_check_changed_email', login="portal")

    def test_website_form_editable_content(self):
        self.start_tour('/', 'website_form_editable_content', login="admin")

    def test_website_form_special_characters(self):
        self.start_tour('/', 'website_form_special_characters', login='admin')
        mail = self.env['mail.mail'].search([], order='id desc', limit=1)
        self.assertIn('Test1&#34;&#39;', mail.body_html, 'The single quotes and double quotes characters should be visible on the received mail')
        self.assertIn('Test2`\\', mail.body_html, 'The backtick and backslash characters should be visible on the received mail')


@tagged('post_install', '-at_install')
class TestWebsiteForm(TransactionCase):

    def test_website_form_html_escaping(self):
        website = self.env['website'].browse(1)
        WebsiteFormController = WebsiteForm()
        with MockRequest(self.env, website=website):
            WebsiteFormController.insert_record(
                request,
                self.env['ir.model'].search([('model', '=', 'mail.mail')]),
                {'email_from': 'odoobot@example.com', 'subject': 'John <b>Smith</b>', 'email_to': 'company@company.company'},
                "John <b>Smith</b>",
            )
            mail = self.env['mail.mail'].search([], order='id desc', limit=1)
            self.assertNotIn('<b>', mail.body_html, "HTML should be escaped in website form")
            self.assertIn('&lt;b&gt;', mail.body_html, "HTML should be escaped in website form (2)")
