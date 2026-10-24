from lxml import html

from odoo.fields import Command
from odoo.tests import HttpCase

from odoo.addons.website_sale.tests.common import WebsiteSaleCommon


class WebsiteSaleSEO(HttpCase, WebsiteSaleCommon):
    _test_user_groups = (
        'base.group_user',
        'product.group_product_manager',
        'sales_team.group_sale_manager',  # FIXME: use sales_team.group_sale_salesman
        'website.group_website_designer',  # website config (language_ids)
    )

    _test_user_name = 'Test Sales & Product Manager'

    def test_website_sale_user_designer_can_edit_seo(self):
        public_categ = self.env["product.public.category"].create({"name": "Website Category"})
        self.product.write({"public_categ_ids": [Command.link(public_categ.id)]})
        internal_user = self.env["res.users"].sudo().create({
            "name": "Web Designer",
            "login": "internal_user",
            "group_ids": [
                Command.link(self.ref("website.group_website_designer")),
                Command.link(self.ref("base.group_user")),
            ],
        })
        self.authenticate(internal_user.login, internal_user.login)
        res = self.make_jsonrpc_request(
            "/website/get_seo_data",
            {"res_id": public_categ.id, "res_model": "product.public.category"},
        )
        self.assertTrue(res["can_edit_seo"])

    def test_website_sale_product_canonical_multilang(self):
        website = self.env.ref("base.default_website")
        lang_fr = self.env["res.lang"].sudo()._activate_lang("fr_FR")
        website.language_ids = self.env.ref("base.lang_en") + lang_fr

        product_path = self.product.website_url

        res = self.url_open(product_path)
        res.raise_for_status()
        root = html.fromstring(res.content)
        canonical = root.xpath('//link[@rel="canonical"]')[0].attrib["href"]
        self.assertEqual(canonical, self.base_url() + self.product.website_url)

        res = self.url_open(f"/fr{product_path}")
        res.raise_for_status()
        root = html.fromstring(res.content)
        canonical = root.xpath('//link[@rel="canonical"]')[0].attrib["href"]
        self.assertEqual(canonical, self.base_url() + "/fr" + self.product.website_url)
