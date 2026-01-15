# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time

from odoo.fields import Command

from odoo.addons.website_sale.controllers.product_feed import ProductFeed
from odoo.addons.product.tests.common import ProductVariantsCommon
from odoo.addons.website_sale.tests.common import MockRequest, WebsiteSaleCommon


class WebsiteSaleGMCCommon(ProductVariantsCommon, WebsiteSaleCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.ProductFeedController = ProductFeed()
        cls.website.enabled_gmc_src = True

        cls.gmc_feed = cls.env['product.feed'].create({
            'name': "GMC",
            'website_id': cls.website.id,
        })

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
        cls.eur_pricelist = cls._create_pricelist(
            name="EUR",
            currency_id=cls.eur_currency.id,
            selectable=True,
        )

    def update_items(self, feed=None):
        feed = feed or self.gmc_feed
        feed = feed.with_context(lang=feed.lang_id.code)
        with MockRequest(
            feed.env,
            website=feed.website_id,
            website_sale_current_pl=feed.pricelist_id.id,
        ):
            self.items = feed._prepare_gmc_items()

        self.red_sofa_item = self.items[self.red_sofa]
        self.blue_sofa_item = self.items[self.blue_sofa]
