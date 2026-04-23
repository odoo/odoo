# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged
from odoo.addons.website.tests.test_disable_unused_snippets_assets import TestDisableSnippetsAssets


@tagged('post_install', '-at_install')
class TestDisableSharedAssets(TestDisableSnippetsAssets):
    def setUp(self):
        super().setUp()
        self.setup_dynamic_snippets_assets()
        # Currently, the `website_sale.alternative_products` template uses
        # a specific inline dynamic snippet without asset version (`data-vcss`
        # or `data-s_dynamic_snippet[_carousel]-vcss`). As a result, in
        # scenarios where the assets `s_dynamic_snippet[_carousel]/000.scss`
        # should be disabled, the test will always fail because this inline
        # snippet still depends on them.
        alternative_products_view = self.env.ref('website_sale.alternative_products')
        alternative_products_view.write({'arch': alternative_products_view.arch_db.replace(
            'data-snippet="s_dynamic_snippet_products"',
            'data-snippet="s_dynamic_snippet_products" t-att-data-s_dynamic_snippet-vcss="001" t-att-data-s_dynamic_snippet_carousel-vcss="001"'
        )})

    def test_dynamic_snippet_new_generic_carousel_new_shared_specific_carousel(self):
        snippets = f"""
            {self.generic_dynamic_snippet_carousel('001', '001')}
            {self.specific_dynamic_snippet_carousel('', '', '001')}
            """
        self.homepage.write({'arch_db': self.dynamic_snippet_homepage(snippets)})
        self.homepage.flush_recordset()
        self.Website._disable_unused_snippets_assets()

        s_dynamic_snippet_000_scss = self._get_snippet_asset('s_dynamic_snippet', '000', 'scss')
        s_dynamic_snippet_001_scss = self._get_snippet_asset('s_dynamic_snippet', '001', 'scss')
        s_dynamic_snippet_carousel_000_scss = self._get_snippet_asset('s_dynamic_snippet_carousel', '000', 'scss')
        s_dynamic_snippet_carousel_001_scss = self._get_snippet_asset('s_dynamic_snippet_carousel', '001', 'scss')

        # `s_dynamic_snippet/000.scss` is still used by the specific snippet
        # (no `data-s_dynamic_snippet-vcss`) and `s_dynamic_snippet/001.scss`
        # is used by the generic one (`data-s_dynamic_snippet-vcss="001"`).
        # `s_dynamic_snippet_carousel/001.scss` is used by both specific and
        # generic snippets.
        # `s_dynamic_snippet_carousel/000.scss` will be disabled.
        self.assertEqual(s_dynamic_snippet_000_scss.active, True)
        self.assertEqual(s_dynamic_snippet_001_scss.active, True)
        self.assertEqual(s_dynamic_snippet_carousel_000_scss.active, False)
        self.assertEqual(s_dynamic_snippet_carousel_001_scss.active, True)

    def test_dynamic_snippet_new_generic_new_shared_specific_carousel(self):
        snippets = f"""
            {self.generic_dynamic_snippet('001')}
            {self.specific_dynamic_snippet_carousel('001', '001', '001')}
            """
        self.homepage.write({'arch_db': self.dynamic_snippet_homepage(snippets)})
        self.homepage.flush_recordset()
        self.Website._disable_unused_snippets_assets()

        s_dynamic_snippet_000_scss = self._get_snippet_asset('s_dynamic_snippet', '000', 'scss')
        s_dynamic_snippet_001_scss = self._get_snippet_asset('s_dynamic_snippet', '001', 'scss')
        s_dynamic_snippet_carousel_000_scss = self._get_snippet_asset('s_dynamic_snippet_carousel', '000', 'scss')
        s_dynamic_snippet_carousel_001_scss = self._get_snippet_asset('s_dynamic_snippet_carousel', '001', 'scss')

        # The `s_dynamic_snippet/000.scss` asset will be disabled and
        # `s_dynamic_snippet/001.scss` should still be active (both generic
        # and specific dynamic snippets have `data-vcss="001"` and
        # `data-s_dynamic_snippet-vcss="001"`).
        # The only specific carousel dynamic snippet is using the asset
        # `s_dynamic_snippet_carousel/001.scss`.
        self.assertEqual(s_dynamic_snippet_000_scss.active, False)
        self.assertEqual(s_dynamic_snippet_001_scss.active, True)
        self.assertEqual(s_dynamic_snippet_carousel_000_scss.active, False)
        self.assertEqual(s_dynamic_snippet_carousel_001_scss.active, True)

    def test_dynamic_snippet_new_generic_new_generic_carousel(self):
        snippets = f"""
            {self.generic_dynamic_snippet('001')}
            {self.generic_dynamic_snippet_carousel('001', '')}
            """
        self.homepage.write({'arch_db': self.dynamic_snippet_homepage(snippets)})
        self.homepage.flush_recordset()
        self.Website._disable_unused_snippets_assets()

        s_dynamic_snippet_000_scss = self._get_snippet_asset('s_dynamic_snippet', '000', 'scss')
        s_dynamic_snippet_001_scss = self._get_snippet_asset('s_dynamic_snippet', '001', 'scss')
        s_dynamic_snippet_carousel_000_scss = self._get_snippet_asset('s_dynamic_snippet_carousel', '000', 'scss')
        s_dynamic_snippet_carousel_001_scss = self._get_snippet_asset('s_dynamic_snippet_carousel', '001', 'scss')

        # `s_dynamic_snippet/000.scss` and `s_dynamic_snippet/001.scss` are
        # both used (no `data-s_dynamic_snippet-vcss` on the carousel generic
        # and `data-vcss` added on generic).
        # The only carousel generic will use `s_dynamic_snippet_carousel/001.scss`.
        self.assertEqual(s_dynamic_snippet_000_scss.active, True)
        self.assertEqual(s_dynamic_snippet_001_scss.active, True)
        self.assertEqual(s_dynamic_snippet_carousel_000_scss.active, False)
        self.assertEqual(s_dynamic_snippet_carousel_001_scss.active, True)

    def test_dynamic_snippet_new_specific_carousel_new_specific_carousel(self):
        snippets = f"""
            {self.specific_dynamic_snippet_carousel('', '001', '')}
            {self.specific_dynamic_snippet_carousel('', '001', '001')}
            """
        self.homepage.write({'arch_db': self.dynamic_snippet_homepage(snippets)})
        self.homepage.flush_recordset()
        self.Website._disable_unused_snippets_assets()

        s_dynamic_snippet_000_scss = self._get_snippet_asset('s_dynamic_snippet', '000', 'scss')
        s_dynamic_snippet_001_scss = self._get_snippet_asset('s_dynamic_snippet', '001', 'scss')
        s_dynamic_snippet_carousel_000_scss = self._get_snippet_asset('s_dynamic_snippet_carousel', '000', 'scss')
        s_dynamic_snippet_carousel_001_scss = self._get_snippet_asset('s_dynamic_snippet_carousel', '001', 'scss')

        # `s_dynamic_snippet/000.scss` should be disabled
        # (`data-s_dynamic_snippet-vcss` on both snippets).
        # Both assets `s_dynamic_snippet_carousel/000.scss` and
        # `s_dynamic_snippet_carousel/001.scss` are used (only one carousel
        # specific has the ``data-s_dynamic_snippet_carousel-vcss`) attribute.
        self.assertEqual(s_dynamic_snippet_000_scss.active, False)
        self.assertEqual(s_dynamic_snippet_001_scss.active, True)
        self.assertEqual(s_dynamic_snippet_carousel_000_scss.active, True)
        self.assertEqual(s_dynamic_snippet_carousel_001_scss.active, True)

    def specific_dynamic_snippet_carousel(self, vcss, dynamic_snippet_vcss, dynamic_snippet_carousel_vcss):
        data_vcss = f'data-vcss="{vcss}"' if vcss else ''
        data_dynamic_snippet_vcss = f'data-s_dynamic_snippet-vcss="{dynamic_snippet_vcss}"' if dynamic_snippet_vcss else ''
        data_dynamic_snippet_carousel_vcss = f'data-s_dynamic_snippet_carousel-vcss="{dynamic_snippet_carousel_vcss}"' if dynamic_snippet_carousel_vcss else ''
        return f"""
        <section data-snippet="s_dynamic_snippet_products" class="s_dynamic_snippet_products oe_website_sale s_dynamic pt64 pb64 s_product_product_products_item o_colored_level"
            data-name="Products"
            data-number-of-records="16"
            data-product-category-id="all"
            data-show-variants="true"
            data-filter-id="1"
            data-template-key="website_sale.dynamic_filter_template_product_product_products_item"
            data-number-of-elements="4"
            data-number-of-elements-small-devices="2"
            data-carousel-interval="5000"
            {' '.join(filter(bool, [data_vcss, data_dynamic_snippet_vcss, data_dynamic_snippet_carousel_vcss]))}>
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
                    <section class="d-flex flex-column s_dynamic_snippet_title oe_unremovable oe_unmovable mb-lg-0 pb-3 pb-md-0 s_col_no_resize o_colored_level">
                        <div class="w-lg-50">
                            <h2 class="h3">Our latest products</h2>
                            <p class="lead">Explore our curated selection and find the products that perfectly match your needs.</p>
                        </div>
                        <div>
                            <a class="btn btn-secondary" href="/shop">Shop all</a>
                        </div>
                    </section>
                    <section class="s_dynamic_snippet_content oe_unremovable oe_unmovable o_not_editable col s_col_no_resize o_colored_level">
                        <div class="dynamic_snippet_template"></div>
                    </section>
                </div>
            </div>
        </section>
        """
