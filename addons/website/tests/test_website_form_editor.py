# Part of Odoo. See LICENSE file for full copyright and licensing details.
# -*- coding: utf-8 -*-

import odoo.tests


@odoo.tests.tagged('post_install', '-at_install')
class TestWebsiteFormEditor(odoo.tests.HttpCase):
    def test_tour(self):
        self.start_tour("/", 'website_form_editor_tour', login="admin")
        self.start_tour("/", 'website_form_editor_tour_submit')
        self.start_tour("/", 'website_form_editor_tour_results', login="admin")

    def test_website_form_contact_us_edition_with_email(self):
        self.start_tour('/contactus', 'website_form_contactus_edition_with_email', login="admin")
        self.start_tour('/contactus', 'website_form_contactus_submit', login="portal")
        mail = self.env['mail.mail'].search([], order='id desc', limit=1)
        self.assertEqual(
            mail.email_to,
            'test@test.test',
            'The email was edited, the form should have been sent to the configured email')

    def test_website_form_contact_us_edition_no_email(self):
        self.start_tour('/contactus', 'website_form_contactus_edition_no_email', login="admin")
        self.start_tour('/contactus', 'website_form_contactus_submit', login="portal")
        mail = self.env['mail.mail'].search([], order='id desc', limit=1)
        self.assertEqual(
            mail.email_to,
            self.env.company.email,
            'The email was not edited, the form should still have been sent to the company email')

    def test_website_form_conditional_required_checkboxes(self):
        self.start_tour('/', 'website_form_conditional_required_checkboxes', login="admin")
