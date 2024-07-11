# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.base.tests.common import HttpCaseWithUserDemo
from odoo.addons.mass_mailing.tests.common import MassMailCommon
from odoo.tests import tagged


@tagged('-at_install', 'post_install')
class TestMailingUi(MassMailCommon, HttpCaseWithUserDemo):

    @classmethod
    def setUpClass(cls):
        super(TestMailingUi, cls).setUpClass()

        cls.user_marketing.write({
            'groups_id': [
                (4, cls.env.ref('mail.group_mail_template_editor').id),
            ],
        })
        cls.user_demo.write({
            'groups_id': [
                (4, cls.env.ref('mass_mailing.group_mass_mailing_campaign').id),
                (4, cls.env.ref('mass_mailing.group_mass_mailing_user').id),
            ],
        })

    def test_mailing_campaign_tour(self):
        # self.env.ref('base.group_user').write({'implied_ids': [(4, self.env.ref('mass_mailing.group_mass_mailing_campaign').id)]})
        campaign = self.env['utm.campaign'].create({
            'name': 'Test Newsletter',
            'user_id': self.env.ref("base.user_admin").id,
            'tag_ids': [(4, self.env.ref('utm.utm_tag_1').id)],
        })
        self.env['mailing.mailing'].create({
            'name': 'First Mailing to disply x2many',
            'subject': 'Bioutifoul mailing',
            'state': 'draft',
            'campaign_id': campaign.id,
        })
        self.env['mailing.list'].create({
            'name': 'Test Newsletter',
        })
        self.user_marketing.write({
            'groups_id': [
                (4, self.env.ref('mass_mailing.group_mass_mailing_campaign').id),
            ],
        })
        self.start_tour("/web", 'mailing_campaign', login="user_marketing")

    def test_mailing_editor_tour(self):
        mailing = self.env['mailing.mailing'].search([('subject', '=', 'TestFromTour')], limit=1)
        self.assertFalse(mailing)
        self.start_tour("/web", 'mailing_editor', login="user_marketing")

        # The tour created and saved a mailing. The edited version should be
        # saved in body_arch, and its transpiled version (see convert_inline)
        # for email client compatibility should be saved in body_html. This
        # ensures both fields have different values (the mailing body should
        # have been converted to a table in body_html).
        mailing = self.env['mailing.mailing'].search([('subject', '=', 'TestFromTour')], limit=1)
        self.assertTrue(mailing)
        self.assertIn('data-snippet="s_title"', mailing.body_arch)
        self.assertTrue(mailing.body_arch.startswith('<div'))
        self.assertIn('data-snippet="s_title"', mailing.body_html)
        self.assertTrue(mailing.body_html.startswith('<table'))

    def test_mailing_editor_theme_tour(self):
        self.start_tour('/web', 'mailing_editor_theme', login="demo")

    def test_snippets_mailing_menu_tabs_tour(self):
        self.start_tour("/web", 'snippets_mailing_menu_tabs', login="demo")

    def test_snippets_mailing_menu_toolbar_tour(self):
        self.start_tour("/web", 'snippets_mailing_menu_toolbar', login="demo")

    def test_snippets_mailing_menu_toolbar_mobile_tour(self):
        self.start_tour("/web", 'snippets_mailing_menu_toolbar_mobile', login="demo")

    def test_mass_mailing_code_view_tour(self):
        self.start_tour("/web?debug=tests", 'mass_mailing_code_view_tour', login="demo")
