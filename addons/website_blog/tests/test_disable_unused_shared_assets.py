# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged
from odoo.addons.website.tests.test_disable_unused_snippets_assets import TestDisableSnippetsAssets


@tagged('post_install', '-at_install')
class TestDisableSharedAssets(TestDisableSnippetsAssets):
    def setUp(self):
        super().setUp()
        self.setup_dynamic_snippets_assets()

    def test_dynamic_snippet_new_generic_old_shared_specific(self):
        snippets = f"""
            {self.generic_dynamic_snippet('001')}
            {self.specific_dynamic_snippet('', '')}
            """
        self.homepage.write({'arch_db': self.dynamic_snippet_homepage(snippets)})
        self.homepage.flush_recordset()
        self.Website._disable_unused_snippets_assets()

        s_dynamic_snippet_000_scss = self._get_snippet_asset('s_dynamic_snippet', '000', 'scss')
        s_dynamic_snippet_001_scss = self._get_snippet_asset('s_dynamic_snippet', '001', 'scss')

        # The asset `s_dynamic_snippet/000.scss` is still used by the specific
        # dynamic snippet and `s_dynamic_snippet/001.scss`` is used by the
        # generic one that has a `data-vcss="001"`.
        self.assertEqual(s_dynamic_snippet_000_scss.active, True)
        self.assertEqual(s_dynamic_snippet_001_scss.active, True)

    def specific_dynamic_snippet(self, vcss, dynamic_snippet_vcss):
        data_vcss = f'data-vcss="{vcss}"' if vcss else ''
        data_dynamic_snippet_vcss = f'data-s_dynamic_snippet-vcss="{dynamic_snippet_vcss}"' if dynamic_snippet_vcss else ''
        return f"""
        <section data-snippet="s_blog_posts" class="s_blog_posts s_dynamic_snippet_blog_posts s_blog_post_big_picture s_blog_posts_effect_marley s_blog_posts_post_picture_size_default s_dynamic pt32 pb32 o_colored_level"
            data-name="Blog Posts"
            data-filter-by-blog-id="1"
            data-filter-id="1"
            data-template-key="website_blog.dynamic_filter_template_blog_post_big_picture"
            data-number-of-records="16"
            data-extra-classes="g-3"
            data-column-classes="col-12 col-sm-6 col-lg-4"
            {' '.join(filter(bool, [data_vcss, data_dynamic_snippet_vcss]))}>
            <div class="container">
                <div class="row s_nb_column_fixed">
                    <section class="s_dynamic_snippet_content oe_unremovable oe_unmovable o_not_editable col o_colored_level">
                        <div class="dynamic_snippet_template"></div>
                    </section>
                </div>
            </div>
        </section>
        """
