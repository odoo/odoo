# Part of Odoo. See LICENSE file for full copyright and licensing details.
import odoo.tests
from odoo.tests import HttpCase

@odoo.tests.common.tagged('post_install', '-at_install')
class TestSitemap(HttpCase):

    def setUp(self):
        super(TestSitemap, self).setUp()

        # Set up a website in French
        self.website = self.env.ref('website.default_website')
        self.lang_fr = self.env['res.lang']._activate_lang('fr_FR')
        self.website.language_ids = self.env.ref('base.lang_en') + self.lang_fr
        self.website.default_lang_id = self.env.ref('base.lang_en')

        # Load translations for testing
        self.env['ir.module.module'].search([('name', '=', 'website_blog')])._update_translations(['fr_FR'])

    def test_01_sitemap_language(self):
        """Ensure sitemap is in English even when navigating to the French version of the website."""

        # Navigate to the French version of the website
        response = self.url_open("/fr_FR")
        self.assertIn('/fr/contactus', response.text)

        # Access the sitemap
        response = self.url_open("/sitemap.xml")

        # Ensure the sitemap content is still in English as it's the default language
        self.assertIn("/blog/astronomy-2/feed", response.text)
        self.assertIn("/blog/astronomy-2", response.text)
        self.assertIn("/blog/travel-1/how-to-choose-the-right-hotel-3", response.text)

    def test_02_sitemap_language(self):
        """Ensure sitemap is in the default language"""

        # Set the default language to French
        self.website.default_lang_id = self.env['res.lang'].sudo()._activate_lang('fr_FR')

        # Access the sitemap
        response = self.url_open("/sitemap.xml")

        # Ensure the sitemap content is in French
        self.assertIn("/blog/astronomie-2/acheter-un-telescope-6", response.text)
        self.assertIn("blog/astronomie-2/au-dela-de-l-il-7", response.text)
        self.assertIn("/blog/voyager-1/vols-en-helicoptere-a-maui-2", response.text)
