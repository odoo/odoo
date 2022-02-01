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

    def test_01_mass_mailing_editor_tour(self):
        self.start_tour("/web", 'mass_mailing_editor_tour', login="demo")
        mail = self.env['mailing.mailing'].search([('subject', '=', 'Test')])[0]
        # The tour created and saved an email. The edited version should be
        # saved in body_arch, and its transpiled version (see convert_inline)
        # for email client compatibility should be saved in body_html. This
        # ensures both fields have different values.
        self.assertEqual(mail.body_arch, '<p><br></p>')
        self.assertEqual(mail.body_html, '<p style="margin:0px 0 14px 0;box-sizing:border-box;"><br></p>')
