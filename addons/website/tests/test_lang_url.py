# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.http_routing.models.ir_http import url_lang
from odoo.addons.website.tools import MockRequest
from odoo.tests import HttpCase, tagged


@tagged('-at_install', 'post_install')
class TestLangUrl(HttpCase):
    def setUp(self):
        super(TestLangUrl, self).setUp()

        # Simulate multi lang without loading translations
        self.website = self.env.ref('website.default_website')
        lang_fr = self.env.ref('base.lang_fr')
        lang_fr.write({'active': True, 'url_code': 'fr'})
        self.website.language_ids = self.env.ref('base.lang_en') + lang_fr
        self.website.default_lang_id = self.env.ref('base.lang_en')

    def test_01_url_lang(self):
        with MockRequest(self.env, website=self.website):
            self.assertEqual(url_lang('', '[lang]'), '/[lang]/hello/', "`[lang]` is used to be replaced in the url_return after installing a language, it should not be replaced or removed.")

    def test_02_url_redirect(self):
        url = '/fr_WHATEVER/contactus'
        r = self.url_open(url)
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.url.endswith('/fr/contactus'), "fr_WHATEVER should be forwarded to 'fr_FR' lang as closest match")

        url = '/fr_FR/contactus'
        r = self.url_open(url)
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.url.endswith('/fr/contactus'), "lang in url should use url_code ('fr' in this case)")
