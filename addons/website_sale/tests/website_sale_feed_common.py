# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import io
from PIL import Image
import time

from odoo.fields import Command

from odoo.addons.website_sale.controllers.product_xml_feed import ProductXmlFeed
from odoo.addons.product.tests.common import ProductVariantsCommon
from odoo.addons.website_sale.tests.common import MockRequest, WebsiteSaleCommon


class WebsiteSaleFeedCommon(ProductVariantsCommon, WebsiteSaleCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.WebsiteSaleFeedController = ProductXmlFeed()
        cls.feed_url = None
        cls.enabled_flag_name = None
        cls.feed_type = None

        # Prepare products
        cls.product_template_sofa.list_price = 1000.0
        (cls.red_sofa, cls.blue_sofa) = cls.product_template_sofa.product_variant_ids[:2]
        cls.red_sofa.default_code = 'SOFA-R'
        cls.blue_sofa.product_template_attribute_value_ids.filtered(
            lambda v: v.name == 'blue'
        ).price_extra = 200.0
        cls.blanket = cls._create_product(name="Blanket")
        combos = cls.env['product.combo'].create([
            {
                'name': "Sofa Combo",
                'combo_item_ids': [
                    Command.create({'product_id': cls.red_sofa.id}),
                    Command.create({'product_id': cls.blue_sofa.id})
                ]
            },
            {
                'name': "Blanket Combo",
                'combo_item_ids': [
                    Command.create({'product_id': cls.blanket.id}),
                ]
            }
        ])
        cls.sofa_bundle = cls._create_product(
            name="Sofa + Blanket",
            type='combo',
            combo_ids=[Command.set(combos.ids)],
            list_price=1099.0
        )
        cls.products = cls.red_sofa + cls.blue_sofa + cls.blanket + cls.sofa_bundle
        cls.products.website_published = True

        # Prepare pricelists
        cls.eur_currency = cls.env.ref('base.EUR')
        cls.eur_currency.write({
            'active': True,
            'rate_ids': [
                Command.clear(),
                Command.create({'name': time.strftime('%Y-%m-%d'), 'rate': 1.1})
            ],
        })

        # Prepare delivery methods
        cls.delivery_countries = cls.env['res.country'].search([('code', 'in', ('BE', 'LU', 'GB'))])
        cls.carrier.write({
            'country_ids': [Command.set(cls.delivery_countries.ids)],  # limit computation overhead
            'free_over': True,
            'amount': 1200.0,
            'website_published': True,
        })
        cls.carrier.product_id.list_price = 5.0

    def update_items(self, website=None, pricelist=None, feed_type=None, **ctx):
        website = website or self.website
        pricelist = pricelist or self.pricelist
        feed_type = feed_type or self.feed_type

        with MockRequest(
            self.env,
            context=ctx,
            website=website,
            website_sale_current_pl=pricelist.id,
        ):
            if feed_type == 'gmc':
                self.items = self.products._prepare_gmc_items()
            elif feed_type == 'meta':
                self.items = self.products._prepare_meta_items()
            else:
                raise ValueError(f"Unsupported feed_type: {feed_type}")

        self.red_sofa_item = self.items[self.red_sofa]
        self.blue_sofa_item = self.items[self.blue_sofa]

    def _create_image(self, color):
        f = io.BytesIO()
        Image.new('RGB', (1920, 1080), color).save(f, 'JPEG')
        f.seek(0)
        return base64.b64encode(f.read())

    def _create_public_category(self, list_vals):
        """ Create a hierarchical chain of `public.product.category`

        :return: the last category in the chain (leaf)
        """
        categs = self.env['product.public.category'].create(list_vals)
        for i in range(0, len(categs) - 1):
            categs[i].parent_id = categs[i + 1]
        return categs[-1]

    def _create_variant_product(self, name, attribute_values, description=''):
        """Helper to create product with variant attributes"""
        return self.env['product.template'].create({
            'name': name,
            'description': description,
            'attribute_line_ids': [
                (0, 0, {
                    'attribute_id': attr.id,
                    'value_ids': [(6, 0, [val.id])],
                }) for attr, val in attribute_values
            ],
        }).product_variant_id
