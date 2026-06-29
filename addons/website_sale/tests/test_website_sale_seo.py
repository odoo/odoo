from odoo.fields import Command
from odoo.tests import HttpCase

from odoo.addons.website_sale.tests.common import WebsiteSaleCommon


class WebsiteSaleSEO(HttpCase, WebsiteSaleCommon):
    def test_website_sale_user_designer_can_edit_seo(self):
        public_categ = self.env['product.public.category'].create({'name': 'Website Category'})
        self.product.write({'public_categ_ids': [Command.link(public_categ.id)]})
        internal_user = self.env['res.users'].create({
            'name': 'Web Designer',
            'login': 'internal_user',
            'group_ids': [
                Command.link(self.ref('website.group_website_designer')),
                Command.link(self.ref('base.group_user')),
            ],
        })
        self.authenticate(internal_user.login, internal_user.login)
        res = self.make_jsonrpc_request(
            '/website/get_seo_data',
            {'res_id': public_categ.id, 'res_model': 'product.public.category'},
        )
        self.assertTrue(res['can_edit_seo'])

    def test_website_product_page_seo_works_with_duplicate_images(self):
        test_product = self.env["product.product"].create(
            {
                "name": "SEO Test Product 1",
                "website_published": True,
                "sale_ok": True,
                "list_price": 500,
            },
        )

        self.start_tour(
            test_product.website_url,
            "website_sale.product_editor_seo_dialog",
            login="admin",
        )
