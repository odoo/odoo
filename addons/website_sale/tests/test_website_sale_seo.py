import json

from lxml import html

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

    def test_website_sale_product_canonical_multilang(self):
        website = self.env.ref("website.default_website")
        lang_fr = self.env["res.lang"]._activate_lang("fr_FR")
        website.language_ids = self.env.ref("base.lang_en") + lang_fr

        public_categ = self.env["product.public.category"].create({
            "name": "Website Category",
            "website_id": website.id,
        })
        self.product.public_categ_ids = [Command.link(public_categ.id)]

        slug = self.env["ir.http"]._slug
        categ_product_path = f"/shop/{slug(public_categ)}/{slug(self.product.product_tmpl_id)}"

        res = self.url_open(categ_product_path)
        res.raise_for_status()
        root = html.fromstring(res.content)
        canonical = root.xpath('//link[@rel="canonical"]')[0].attrib["href"]
        self.assertEqual(canonical, self.base_url() + self.product.website_url)

        res = self.url_open(f"/fr{categ_product_path}")
        res.raise_for_status()
        root = html.fromstring(res.content)
        canonical = root.xpath('//link[@rel="canonical"]')[0].attrib["href"]
        self.assertEqual(canonical, self.base_url() + "/fr" + self.product.website_url)

    def test_website_sale_product_jsonld_multilang(self):
        website = self.env.ref("website.default_website")
        lang_fr = self.env["res.lang"]._activate_lang("fr_FR")
        website.language_ids = self.env.ref("base.lang_en") + lang_fr
        public_categ = self.env["product.public.category"].create({"name": "Website Category"})
        size = self.env["product.attribute"].create({
            "name": "Size",
            "value_ids": [Command.create({"name": "Small"}), Command.create({"name": "Large"})],
        })
        template = self.env["product.template"].create({
            "name": "Table",
            "is_published": True,
            "public_categ_ids": [Command.link(public_categ.id)],
            "attribute_line_ids": [Command.create({
                "attribute_id": size.id,
                "value_ids": [Command.set(size.value_ids.ids)],
            })],
        })

        res = self.url_open(f"/fr{template.website_url}")
        res.raise_for_status()
        root = html.fromstring(res.content)
        canonical = root.xpath('//link[@rel="canonical"]')[0].attrib["href"]
        product_group, breadcrumb = json.loads(root.xpath('//script[@type="application/ld+json"]')[-1].text)
        self.assertEqual(canonical, self.base_url() + "/fr" + template.website_url)
        self.assertEqual(product_group["url"], self.base_url() + "/fr" + template.website_url)
        for variant in product_group["hasVariant"]:
            self.assertTrue(variant["url"].startswith(canonical + "?attribute_values="))
        all_products, category, _product = breadcrumb["itemListElement"]
        self.assertTrue(all_products["item"].startswith(self.base_url() + "/fr/shop"))
        self.assertTrue(category["item"].startswith(self.base_url() + "/fr/shop"))
