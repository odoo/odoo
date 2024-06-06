# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from lxml import html

import odoo.tests

from odoo.addons.base.tests.common import HttpCaseWithUserDemo


@odoo.tests.common.tagged('post_install', '-at_install')
class TestWebsiteSession(HttpCaseWithUserDemo):

    def test_01_run_test(self):
        self.start_tour('/', 'test_json_auth')

    def test_branding_cache(self):
        def has_branding(html_text):
            el = html.fromstring(html_text)
            return el.xpath('//*[@data-oe-model="test.model"]')

        self.user_demo.groups_id += self.env.ref('website.group_website_restricted_editor')
        self.user_demo.groups_id -= self.env.ref('website.group_website_designer')

        # Create session for demo user.
        public_session = self.authenticate(None, None)
        demo_session = self.authenticate('demo', 'demo')
        record = self.env['test.model'].search([])
        result = self.url_open(f'/test_website/model_item/{record.id}')
        self.assertTrue(has_branding(result.text), "Should have branding for user demo")

        # Public user.
        self.opener.cookies['session_id'] = public_session.sid
        result = self.url_open(f'/test_website/model_item/{record.id}')
        self.assertFalse(has_branding(result.text), "Should have no branding for public user")

        # Back to demo user.
        self.opener.cookies['session_id'] = demo_session.sid
        result = self.url_open(f'/test_website/model_item/{record.id}')
        self.assertTrue(has_branding(result.text), "Should have branding for user demo")
