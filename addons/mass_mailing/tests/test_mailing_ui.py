# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests
from odoo.addons.base.tests.common import HttpCaseWithUserDemo


@odoo.tests.tagged('-at_install', 'post_install')
class TestUi(HttpCaseWithUserDemo):
    def setUp(self):
        super().setUp()
        self.user_demo.groups_id |= self.env.ref('mass_mailing.group_mass_mailing_user')
        self.user_demo.groups_id |= self.env.ref('mail.group_mail_template_editor')
        self.user_demo.groups_id |= self.env.ref('mass_mailing.group_mass_mailing_campaign')

    def test_01_mass_mailing_editor_tour(self):
        self.start_tour("/web", 'mass_mailing_editor_tour', login="demo")
        mail = self.env['mailing.mailing'].search([('subject', '=', 'Test')])[0]
        # The tour created and saved an email. The edited version should be
        # saved in body_arch, and its transpiled version (see convert_inline)
        # for email client compatibility should be saved in body_html. This
        # ensures both fields have different values (the mailing body should
        # have been converted to a table in body_html).
        self.assertIn('data-snippet="s_title"', mail.body_arch)
        self.assertTrue(mail.body_arch.startswith('<div'))
        self.assertIn('data-snippet="s_title"', mail.body_html)
        self.assertTrue(mail.body_html.startswith('<table'))

    def test_02_mass_mailing_snippets_menu_tabs(self):
        self.start_tour("/web", 'mass_mailing_snippets_menu_tabs', login="demo")

    def test_03_mass_mailing_snippets_toolbar_mobile_hide(self):
        self.start_tour("/web", 'mass_mailing_snippets_menu_toolbar_new_mailing_mobile', login="demo")

    def test_04_mass_mailing_snippets_menu_hide(self):
        self.start_tour("/web", 'mass_mailing_snippets_menu_toolbar', login="demo")

    def test_05_mass_mailing_basic_theme_toolbar(self):
        self.start_tour('/web', 'mass_mailing_basic_theme_toolbar', login="demo")

    def test_06_mass_mailing_campaign_new_mailing(self):
        self.start_tour("/web", 'mass_mailing_campaing_new_mailing', login="demo")
