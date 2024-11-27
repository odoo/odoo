# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from lxml import html
from unittest.mock import patch

from odoo import http
from odoo.addons.website.models.website import Website
import odoo.tests

from odoo.addons.base.tests.common import HttpCaseWithUserDemo


@odoo.tests.common.tagged('post_install', '-at_install')
class TestWebsiteSession(HttpCaseWithUserDemo):

    def test_01_run_test(self):
        self.start_tour('/', 'test_json_auth')

    def test_02_inactive_session_lang(self):
        session = self.authenticate(None, None)
        self.env.ref('base.lang_fr').active = False
        session.context['lang'] = 'fr_FR'
        odoo.http.root.session_store.save(session)

        # ensure that _get_current_website_id will be able to match a website
        current_website_id = self.env["website"]._get_current_website_id(odoo.tests.HOST)
        self.env["website"].browse(current_website_id).domain = odoo.tests.HOST

        res = self.url_open('/test_website_sitemap')  # any auth='public' route would do
        res.raise_for_status()

    def test_03_totp_login_with_inactive_session_lang(self):
        session = self.authenticate(None, None)
        self.env.ref('base.lang_fr').active = False
        session.context['lang'] = 'fr_FR'
        odoo.http.root.session_store.save(session)

        # ensure that _get_current_website_id will be able to match a website
        current_website_id = self.env["website"]._get_current_website_id(odoo.tests.HOST)
        self.env["website"].browse(current_website_id).domain = odoo.tests.HOST

        with patch.object(self.env.registry["res.users"], "_mfa_url", return_value="/web/login/totp"):
            res = self.url_open('/web/login', allow_redirects=False, data={
                'login': 'demo',
                'password': 'demo',
                'csrf_token': http.Request.csrf_token(self),
            })
            res.raise_for_status()
        self.assertEqual(res.status_code, 303)
        self.assertTrue(res.next.path_url.startswith("/web/login/totp"))

    def test_04_ensure_website_get_cached_values_can_be_called(self):
        session = self.authenticate('admin', 'admin')

        # Force a browser language that is not installed
        session.context['lang'] = 'fr_MC'
        http.root.session_store.save(session)

        # Disable cache in order to make sure that values would be fetched at any time
        get_cached_values_without_cache = Website._get_cached_values.__cache__.method
        with patch.object(Website, '_get_cached_values',
                          side_effect=get_cached_values_without_cache, autospec=True):

            # ensure that permissions on logout are OK
            res = self.url_open('/web/session/logout')
            self.assertEqual(res.status_code, 200)

    def test_branding_cache(self):
        def has_branding(html_text):
            el = html.fromstring(html_text)
            return el.xpath('//*[@data-oe-model="test.model"]')

        self.user_demo.groups_id += self.env.ref('website.group_website_restricted_editor')
        self.user_demo.groups_id += self.env.ref('test_website.group_test_website_admin')
        self.user_demo.groups_id -= self.env.ref('website.group_website_designer')

        # Create session for demo user.
        public_session = self.authenticate(None, None)
        demo_session = self.authenticate('demo', 'demo')
        record = self.env['test.model'].search([])
        result = self.url_open(f'/test_website/model_item_sudo/{record.id}')
        self.assertTrue(has_branding(result.text), "Should have branding for user demo")

        # Public user.
        self.opener.cookies['session_id'] = public_session.sid
        result = self.url_open(f'/test_website/model_item_sudo/{record.id}')
        self.assertFalse(has_branding(result.text), "Should have no branding for public user")

        # Back to demo user.
        self.opener.cookies['session_id'] = demo_session.sid
        result = self.url_open(f'/test_website/model_item_sudo/{record.id}')
        self.assertTrue(has_branding(result.text), "Should have branding for user demo")
