# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import HttpCase, tagged


@tagged('post_install', '-at_install', 'ssr_test')
class TestDynamicSnippetSSR(HttpCase):

    def test_dynamic_snippet_products_ssr(self):
        website = self.env['website'].get_current_website()
        self.env['product.template'].create({
            'name': 'Product 1',
            'website_published': True,
            'website_id': website.id,
            'list_price': 10.0,
        })
        self.env['product.template'].create({
            'name': 'Product 2',
            'website_published': True,
            'website_id': website.id,
            'list_price': 20.0,
        })

        filter_newest = self.env.ref('website_sale.dynamic_filter_newest_products')
        view = self.env['ir.ui.view'].create({
            'name': 'QWeb View',
            'type': 'qweb',
            'key': 'website_sale.ssr_view_test',
            'arch': f"""
                <t t-name="website_sale.ssr_view_test">
                    <t t-call="website.layout">
                        <div id="wrap">
                            <section class="s_dynamic_snippet_products"
                                     data-snippet="s_dynamic_snippet_products"
                                     data-filter-id="{filter_newest.id}"
                                     data-template-key="website_sale.dynamic_filter_template_product_product_products_item"
                                     data-number-of-records="2">
                                <div class="container">
                                    <div class="dynamic_snippet_template row"/>
                                </div>
                            </section>
                        </div>
                    </t>
                </t>
            """,
        })

        self.env['website.page'].create({
            'view_id': view.id,
            'url': '/test',
            'is_published': True,
        })

        response = self.url_open('/test')
        self.assertEqual(response.status_code, 200)

        content = response.content.decode()
        self.assertIn(
            'data-ssr-rendered="true"',
            content,
            "Dynamic snippet should be SSR rendered")

        self.assertIn('Product 1', content, "Product 1 should be present in the rendered content")
        self.assertIn('Product 2', content, "Product 2 should be present in the rendered content")
