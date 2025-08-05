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

    def setup_dynamic_snippets_assets(self):
        """ Setup test data for website generic dynamic snippets """
        self.IrAsset.create({
            'name': 'Dynamic snippet 001 SCSS',
            'bundle': 'web.assets_frontend',
            'path': 'website/static/src/snippets/s_dynamic_snippet/001.scss',
        })
        self.IrAsset.create({
            'name': 'Dynamic snippet carousel 001 SCSS',
            'bundle': 'web.assets_frontend',
            'path': 'website/static/src/snippets/s_dynamic_snippet_carousel/001.scss',
        })
        s_dynamic_snippet = self.env.ref('website.s_dynamic_snippet')
        s_dynamic_snippet_carousel = self.env.ref('website.s_dynamic_snippet_carousel')

        s_dynamic_snippet.write({
            'arch_db': s_dynamic_snippet.arch_db.replace(
                'snippet_name.f="s_dynamic_snippet"',
                'snippet_name.f="s_dynamic_snippet" vcss.f="001"')
        })
        s_dynamic_snippet.flush_recordset()
        s_dynamic_snippet_carousel.write({
            'arch_db': s_dynamic_snippet_carousel.arch_db.replace(
                'snippet_name.f="s_dynamic_snippet_carousel"',
                'snippet_name.f="s_dynamic_snippet_carousel" vcss.f="001"')
        })
        s_dynamic_snippet_carousel.flush_recordset()

    def test_homepage_outdated_and_mega_menu_up_to_date(self):
        self.Website._disable_unused_snippets_assets()
        # Old snippet with scss
        s_website_form_000_scss = self._get_snippet_asset('s_website_form', '000', 'scss')
        s_website_form_001_scss = self._get_snippet_asset('s_website_form', '001', 'scss')
        self.assertEqual(s_website_form_000_scss.active, True)
        self.assertEqual(s_website_form_001_scss.active, True)

        # Old snippet with scss and scss variables
        s_masonry_block_000_scss = self._get_snippet_asset('s_masonry_block', '000', 'scss')
        s_masonry_block_000_variables_scss = self._get_snippet_asset('s_masonry_block', '000_variables', 'scss')
        s_masonry_block_001_scss = self._get_snippet_asset('s_masonry_block', '001', 'scss')
        self.assertEqual(s_masonry_block_000_scss.active, True)
        self.assertEqual(s_masonry_block_000_variables_scss.active, True)
        self.assertEqual(s_masonry_block_001_scss.active, True)

        # New snippet
        s_image_gallery_000 = self._get_snippet_asset('s_image_gallery', '000', 'scss')
        s_image_gallery_002 = self._get_snippet_asset('s_image_gallery', '002', 'scss')
        self.assertEqual(s_image_gallery_000.active, False)
        self.assertEqual(s_image_gallery_002.active, True)

        unwanted_snippets_assets_changes = set(self.initial_active_snippets_assets) - set(self._get_active_snippets_assets()) - set([s_image_gallery_000.path])

        # The vacuum should not have activated/deactivated any other snippet asset than the original ones
        self.assertEqual(
            len(unwanted_snippets_assets_changes),
            0,
            'Following snippets are not following the snippet versioning system structure, or their previous assets have not been deactivated:\n'
            + '\n'.join(unwanted_snippets_assets_changes))

    def test_homepage_up_to_date_and_mega_menu_outdated(self):
        self.homepage.write({
            'arch_db': HOMEPAGE_UP_TO_DATE,
        })
        self.homepage.flush_recordset()
        self.mega_menu.write({
            'mega_menu_content': MEGA_MENU_OUTDATED,
        })
        self.mega_menu.flush_recordset()
        self.addCleanup(self.drop_ormcaches)

        cache_invalidated = self.env.registry.cache_invalidated
        self.Website._disable_unused_snippets_assets()
        self.assertIn('assets', cache_invalidated, 'Assets cache should have been invalidated when updating ir_assets')
        cache_invalidated.clear()
        self.Website._disable_unused_snippets_assets()
        self.assertNotIn('assets', cache_invalidated, 'No update on ir_assets expected, no invalidation should be triggered')

        s_website_form_000_scss = self._get_snippet_asset('s_website_form', '000', 'scss')
        s_website_form_001_scss = self._get_snippet_asset('s_website_form', '001', 'scss')
        self.assertEqual(s_website_form_000_scss.active, False)
        self.assertEqual(s_website_form_001_scss.active, True)

        s_masonry_block_000_scss = self._get_snippet_asset('s_masonry_block', '000', 'scss')
        s_masonry_block_000_variables_scss = self._get_snippet_asset('s_masonry_block', '000_variables', 'scss')
        s_masonry_block_001_scss = self._get_snippet_asset('s_masonry_block', '001', 'scss')
        self.assertEqual(s_masonry_block_000_scss.active, False)
        self.assertEqual(s_masonry_block_000_variables_scss.active, False)
        self.assertEqual(s_masonry_block_001_scss.active, True)

        s_image_gallery_000 = self._get_snippet_asset('s_image_gallery', '000', 'scss')
        s_image_gallery_002 = self._get_snippet_asset('s_image_gallery', '002', 'scss')
        self.assertEqual(s_image_gallery_000.active, True)
        self.assertEqual(s_image_gallery_002.active, True)

    def _get_snippet_asset(self, snippet_id, asset_version, asset_type):
        return self.IrAsset.search([('path', '=', 'website/static/src/snippets/' + snippet_id + '/' + asset_version + '.' + asset_type)], limit=1)

    def _get_active_snippets_assets(self):
        return self.IrAsset.search([('path', 'like', 'snippets'), ('active', '=', True)]).mapped('path')

    def dynamic_snippet_homepage(self, snippets):
        return f"""
        <t name="Homepage" t-name="website.dynamic_snippet_homepage">
            <t t-call="website.layout" pageName.f="homepage">
                <div id="wrap" class="oe_structure oe_empty">
                    {snippets}
                </div>
            </t>
        </t>
        """

    def generic_dynamic_snippet(self, vcss):
        data_vcss = f'data-vcss="{vcss}"' if vcss else ''
        return f"""
        <section data-snippet="s_dynamic_snippet" class="s_dynamic_snippet s_dynamic pt32 pb32 o_colored_level" data-name="Dynamic Snippet"
            data-filter-id="1"
            data-template-key="website.dynamic_filter_template_test_item"
            data-number-of-records="16"
            data-extra-classes="g-3"
            data-column-classes="col-12 col-sm-6 col-lg-4"
            {data_vcss}>
            <div class="container">
                <div class="row s_nb_column_fixed">
                    <section class="s_dynamic_snippet_content oe_unremovable oe_unmovable o_not_editable col o_colored_level">
                        <div class="dynamic_snippet_template"></div>
                    </section>
                </div>
            </div>
        </section>
        """

    def generic_dynamic_snippet_carousel(self, vcss, dynamic_snippet_vcss):
        data_vcss = f'data-vcss="{vcss}"' if vcss else ''
        data_dynamic_snippet_vcss = f'data-s_dynamic_snippet-vcss="{dynamic_snippet_vcss}"' if dynamic_snippet_vcss else ''
        return f"""
        <section data-snippet="s_dynamic_snippet_carousel" class="s_dynamic_snippet_carousel s_dynamic pt64 pb64 o_colored_level"
            data-number-of-records="4"
            data-name="Dynamic Carousel"
            data-filter-id="110"
            data-template-key="website_appointment.dynamic_filter_template_appointment_type_card"
            data-extra-classes="g-3"
            data-column-classes="s_appointments_card col-12 col-sm-6 col-lg-4 col-xxl-3"
            data-carousel-interval="5000"
            {' '.join(filter(bool, [data_vcss, data_dynamic_snippet_vcss]))}>
            <div class="s_dynamic_snippet_container container">
                <div class="row s_nb_column_fixed">
                    <section class="s_dynamic_snippet_holder d-none px-4 placeholder-glow o_colored_level">
                        <div class="row">
                            <span class="placeholder col-3 rounded"></span>
                            <span class="placeholder col-2 offset-7 rounded"></span>
                            <span class="placeholder mt-3 col-6 rounded"></span>
                        </div>
                        <div class="row mt-4">
                            <span class="placeholder col-12 rounded" style="height: 250px;"></span>
                        </div>
                    </section>
                    <section class="d-flex justify-content-between flex-column flex-md-row s_dynamic_snippet_title oe_unremovable oe_unmovable mb-lg-0 pb-3 pb-md-0 s_col_no_resize o_colored_level">
                        <div>
                            <h2 class="h3">Our latest content</h2>
                            <p class="lead">Check out what's new in our company !</p>
                        </div>
                    </section>
                    <section class="s_dynamic_snippet_content oe_unremovable oe_unmovable o_not_editable col s_col_no_resize o_colored_level">
                        <div class="dynamic_snippet_template"></div>
                    </section>
                </div>
            </div>
        </section>
        """


HOMEPAGE_UP_TO_DATE = """
<t name="Homepage" t-name="website.homepage1">
  <t t-call="website.layout" pageName.f="homepage">
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
  <t t-call="website.layout" pageName.f="homepage">
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

<section class="s_image_gallery o_slideshow pt24 o_colored_level" data-vcss="002" data-columns="3" style="height: 500px; overflow: hidden;" data-snippet="s_image_gallery" data-name="Image Gallery">
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
