from odoo.addons.http_routing.tests.common import MockRequest
from odoo.addons.website.controllers.main import Website
from odoo.tests import HttpCase, tagged


@tagged('-at_install', 'post_install')
class TestWebsiteSaveXml(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.WebsiteController = Website()
        cls.env['res.lang']._activate_lang('fr_FR')
        cls.website = cls.env['website'].search([], limit=1)
        cls.view = cls.env["ir.ui.view"].create({
            "name": "Test View",
            "type": "qweb",
            "arch": "<div>OldEN</div>",
            "website_id": cls.website.id,
        })
        cls.view.with_context(lang='fr_FR').arch = "<div>OldFR</div>"

    def test_save_xml_delay_translations(self):
        with MockRequest(self.env, website=self.website):
            self.WebsiteController.save_xml(self.view.id, '<div>NewEN</div>')
        self.assertEqual(
            self.view.with_context(lang='fr_FR').arch,
            '<div>OldFR</div>',
        )
        delayed_translation = self.view.with_context(lang='fr_FR', edit_translations=True).arch
        self.assertIn(
            '<div><span class="o_delay_translation"',
            delayed_translation,
        )
        self.assertIn(
            '>NewEN</span></div>',
            delayed_translation,
        )

    def test_save_xml_disabled_delay_translations(self):
        """Test that disable_delay_translations disable delayed translation on save_xml call"""
        self.env['ir.config_parameter'].sudo().set_param('website.disable_delay_translations', '1')

        self.assertEqual(
            self.view.with_context(lang='fr_FR').arch,
            '<div>OldFR</div>',
        )
        with MockRequest(self.env, website=self.website):
            self.WebsiteController.save_xml(self.view.id, '<div>NewEN</div>')
        self.assertEqual(
            self.view.with_context(lang='fr_FR').arch,
            '<div>NewEN</div>',
        )
        delayed_translation = self.view.with_context(lang='fr_FR', edit_translations=True).arch
        self.assertNotIn(
            '<div><span class="o_delay_translation"',
            delayed_translation,
        )
        self.assertIn(
            '>NewEN</span></div>',
            delayed_translation,
        )
