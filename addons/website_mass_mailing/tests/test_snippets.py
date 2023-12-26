# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo
import odoo.tests


@odoo.tests.common.tagged('post_install', '-at_install')
class TestSnippets(odoo.tests.HttpCase):

    def test_01_newsletter_popup(self):
        self.start_tour('/', 'newsletter_popup_edition', login='admin')
        self.start_tour("/", "newsletter_popup_use", login=None)
        mailing_list = self.env['mailing.list'].search([], limit=1)
        emails = mailing_list.contact_ids.mapped('email')
        self.assertIn("hello@world.com", emails)

    def test_02_newsletter_block_edition(self):
        self.env.ref('base.user_admin').email = 'admin@yourcompany.example.com'
        admin_email = self.env.ref('base.user_admin').email
        # Get contacts with this email
        mass_mailing_contacts = self.env['mailing.contact'].search([('email', '=', admin_email)])
        mailing_list = self.env['mailing.list'].search([('contact_ids', 'in', mass_mailing_contacts.ids)])
        # Unsubscribe the admin's email from every mailing list to ensure the
        # tour can subscribe the admin again
        mailing_list.write({
            'contact_ids': [odoo.Command.unlink(id) for id in mass_mailing_contacts.ids]
        })
        self.start_tour(self.env['website'].get_client_action_url('/'), 'newsletter_block_edition', login='admin')
