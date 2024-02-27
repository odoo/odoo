# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# This test is in website_blog to ensure we have pages in the sitemap.

from odoo.addons.base.tests.common import HttpCaseWithUserPortal

class TestWebsiteLanguage(HttpCaseWithUserPortal):
    def setUp(self):
        super().setUp()
        self.website = self.env.ref('website.default_website')
        self.lang_fr = self.env['res.lang']._activate_lang('fr_FR')
        self.lang_fr.write({'url_code': 'fr'})
        self.website.language_ids = self.env.ref('base.lang_en') + self.lang_fr
        self.website.default_lang_id = self.env.ref('base.lang_en')

    def test_sitemap_language(self):
        # Simulate user going to /fr
        self.url_open('/fr')

        # Simulate user going to /sitemap.xml
        response = self.url_open('/sitemap.xml')

        self.assertIn('buying-a-telescope', response.text)
        self.assertNotIn('acheter-un-telescope', response.text)