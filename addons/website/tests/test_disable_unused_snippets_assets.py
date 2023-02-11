# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestDisableSnippetsAssets(TransactionCase):
    def setUp(self):
        super().setUp()
        self.View = self.env['ir.ui.view']
        self.WebsiteMenu = self.env['website.menu']
        self.Website = self.env['website']
        self.IrAsset = self.env['ir.asset']

        self.homepage = self.View.create({
            'name': 'Home',
            'type': 'qweb',
            'arch_db': HOMEPAGE_OUTDATED,
            'key': 'website.homepage',
        })
        self.mega_menu = self.WebsiteMenu.create({
            'name': 'Image Gallery V001',
            'mega_menu_content': MEGA_MENU_UP_TO_DATE,
        })

        self.initial_active_snippets_assets = self._get_active_snippets_assets()

    def test_homepage_outdated_and_mega_menu_up_to_date(self):
        self.Website._disable_unused_snippets_assets()
        # Old snippet with scss and js
        s_website_form_000_scss = self._get_snippet_asset('s_website_form', '000', 'scss')
        s_website_form_001_scss = self._get_snippet_asset('s_website_form', '001', 'scss')
        s_website_form_000_js = self._get_snippet_asset('s_website_form', '000', 'js')
        self.assertEqual(s_website_form_000_scss.active, True)
        self.assertEqual(s_website_form_001_scss.active, True)
        self.assertEqual(s_website_form_000_js.active, True)

        # Old snippet with scss and scss variables
        s_masonry_block_000_scss = self._get_snippet_asset('s_masonry_block', '000', 'scss')
        s_masonry_block_000_variables_scss = self._get_snippet_asset('s_masonry_block', '000_variables', 'scss')
        s_masonry_block_001_scss = self._get_snippet_asset('s_masonry_block', '001', 'scss')
        self.assertEqual(s_masonry_block_000_scss.active, True)
        self.assertEqual(s_masonry_block_000_variables_scss.active, True)
        self.assertEqual(s_masonry_block_001_scss.active, True)

        # New snippet
        s_image_gallery_000 = self._get_snippet_asset('s_image_gallery', '000', 'scss')
        s_image_gallery_001 = self._get_snippet_asset('s_image_gallery', '001', 'scss')
        self.assertEqual(s_image_gallery_000.active, False)
        self.assertEqual(s_image_gallery_001.active, True)

        unwanted_snippets_assets_changes = set(self.initial_active_snippets_assets) - set(self._get_active_snippets_assets()) - set([s_image_gallery_000.path])

        # The vaccuum should not have activated/deactivated any other snippet asset than the original ones
        self.assertEqual(
          len(unwanted_snippets_assets_changes),
          0,
          'Following snippets are not following the snippet versioning system structure, or their previous assets have not been deactivated:\n'
            + '\n'.join(unwanted_snippets_assets_changes))

    def test_homepage_up_to_date_and_mega_menu_outdated(self):
        self.homepage.write({
            'arch_db': HOMEPAGE_UP_TO_DATE,
        })
        self.mega_menu.write({
            'mega_menu_content': MEGA_MENU_OUTDATED,
        })
        self.Website._disable_unused_snippets_assets()

        s_website_form_000_scss = self._get_snippet_asset('s_website_form', '000', 'scss')
        s_website_form_001_scss = self._get_snippet_asset('s_website_form', '001', 'scss')
        s_website_form_000_js = self._get_snippet_asset('s_website_form', '000', 'js')
        self.assertEqual(s_website_form_000_scss.active, False)
        self.assertEqual(s_website_form_001_scss.active, True)
        self.assertEqual(s_website_form_000_js.active, True)

        s_masonry_block_000_scss = self._get_snippet_asset('s_masonry_block', '000', 'scss')
        s_masonry_block_000_variables_scss = self._get_snippet_asset('s_masonry_block', '000_variables', 'scss')
        s_masonry_block_001_scss = self._get_snippet_asset('s_masonry_block', '001', 'scss')
        self.assertEqual(s_masonry_block_000_scss.active, False)
        self.assertEqual(s_masonry_block_000_variables_scss.active, False)
        self.assertEqual(s_masonry_block_001_scss.active, True)

        s_image_gallery_000 = self._get_snippet_asset('s_image_gallery', '000', 'scss')
        s_image_gallery_001 = self._get_snippet_asset('s_image_gallery', '001', 'scss')
        self.assertEqual(s_image_gallery_000.active, True)
        self.assertEqual(s_image_gallery_001.active, True)

    def _get_snippet_asset(self, snippet_id, asset_version, asset_type):
        return self.IrAsset.search([('path', '=', 'website/static/src/snippets/' + snippet_id + '/' + asset_version + '.' + asset_type)], limit=1)

    def _get_active_snippets_assets(self):
        return self.IrAsset.search([('path', 'like', 'snippets'), ('active', '=', True)]).mapped('path')

HOMEPAGE_UP_TO_DATE = """
<t name="Homepage" t-name="website.homepage1">
  <t t-call="website.layout">
    <t t-set="pageName" t-value="'homepage'"/>
    <div id="wrap" class="oe_structure oe_empty">
      <section class="s_website_form pt16 pb16 o_colored_level" data-vcss="001" data-snippet="s_website_form" data-name="Form">
        <div class="container">
          <form action="/website_form/" method="post" enctype="multipart/form-data" class="o_mark_required" data-mark="*" data-success-mode="redirect" data-success-page="/contactus-thank-you" data-model_name="mail.mail">
          </form>
        </div>
      </section>
      <section class="s_masonry_block" data-vcss="001" data-snippet="s_masonry_block" data-name="Masonry">
        <div class="container-fluid"/>
      </section>
      <section class="s_showcase pt48 pb48 o_colored_level" data-vcss="002" data-snippet="s_showcase" data-name="Showcase">
        <div class="container">
        </div>
      </section>
    </div>
  </t>
</t>
"""

HOMEPAGE_OUTDATED = """
<t name="Homepage" t-name="website.homepage1">
  <t t-call="website.layout">
    <t t-set="pageName" t-value="'homepage'"/>
    <div id="wrap" class="oe_structure oe_empty">
      <form action="/website_form/" method="post" class="s_website_form container-fluid mt32 o_fake_not_editable" enctype="multipart/form-data" data-name="Form Builder" data-model_name="mail.mail" data-success_page="/contactus-thank-you" data-snippet="s_website_form">
        <div class="container">
        </div>
      </form>
      <section class="s_masonry_block" data-vcss="001" data-snippet="s_masonry_block" data-name="Masonry">
        <div class="container-fluid"/>
      </section>
      <section class="s_masonry_block" data-snippet="s_masonry_block" data-name="Masonry">
        <div class="container-fluid"/>
      </section>
      <section class="s_showcase pt48 pb48 o_colored_level" data-vcss="002" data-snippet="s_showcase" data-name="Showcase">
        <div class="container">
        </div>
      </section>
    </div>
  </t>
</t>
"""

MEGA_MENU_UP_TO_DATE = """
<section class="s_mega_menu_multi_menus py-4 o_colored_level" data-name="Multi-Menus">
        <div class="container">
        </div>
    </section>

<section class="s_image_gallery o_slideshow s_image_gallery_show_indicators s_image_gallery_indicators_rounded pt24 o_colored_level" data-vcss="001" data-columns="3" style="height: 500px; overflow: hidden;" data-snippet="s_image_gallery" data-name="Image Gallery">
        <div class="container">
        </div>
    </section>
"""

MEGA_MENU_OUTDATED = """
<section class="s_mega_menu_multi_menus py-4 o_colored_level" data-name="Multi-Menus">
        <div class="container">
        </div>
    </section>

<section class="s_image_gallery o_slideshow s_image_gallery_show_indicators s_image_gallery_indicators_rounded pt24 o_colored_level" data-columns="3" style="height: 500px; overflow: hidden;" data-snippet="s_image_gallery" data-name="Image Gallery">
        <div class="container">
        </div>
    </section>
"""
