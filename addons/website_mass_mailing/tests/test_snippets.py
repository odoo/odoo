# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo
import odoo.tests


@odoo.tests.common.tagged('post_install', '-at_install')
class TestSnippets(odoo.tests.HttpCase):

    def test_01_newsletter_popup(self):
        self.start_tour("/?enable_editor=1", "newsletter_popup_edition", login='admin')
        self.start_tour("/", "newsletter_popup_use", login=None)
        mailing_list = self.env['mailing.list'].search([], limit=1)
        emails = mailing_list.contact_ids.mapped('email')
        self.assertIn("hello@world.com", emails)

    def test_02_newsletter_block_edition(self):
        self.start_tour(self.env['website'].get_client_action_url('/'), 'newsletter_block_edition', login='admin')
