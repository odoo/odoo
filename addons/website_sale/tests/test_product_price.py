# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.addons.product.tests.common import ProductVariantsCommon
from odoo.addons.website_sale.tests.common import WebsiteSaleCommon
from odoo.fields import Command


class WebsiteSaleProductPrice(ProductVariantsCommon, WebsiteSaleCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._enable_variants()
        cls._enable_pricelists()

        # Prepare product
        cls.product_template_book = cls.env['product.template'].create({
            'name': 'Book',
            'list_price': 10,
            'attribute_line_ids': [Command.create({
                'attribute_id': cls.color_attribute.id,
                'value_ids': [Command.set([
                    cls.color_attribute_red.id,
                    cls.color_attribute_blue.id,
                ])],
            })],
        })

        (cls.red_book, cls.blue_book) = cls.product_template_book.product_variant_ids

    @staticmethod
    def _price_is_valid(product_price):
        return product_price.cache_expiry > fields.Date.today()

    def _get_product_price(self, product_id, pricelist_id):
        return self.env['product.price'].search([
            ('product_product_id', '=', product_id), ('pricelist_id', '=', pricelist_id)
        ])

    @classmethod
    def _imitate_cron_price_calculation(cls, prices_to_update):
        today = fields.Date.today()
        for prod_price in prices_to_update:
            res = prod_price.pricelist_id._compute_price_rule(prod_price.product_product_id, 1)
            prod_price.price, prod_price.pricelist_item_id = res[prod_price.product_product_id.id]
        prices_to_update.cache_expiry = today + relativedelta(days=1)

    def test_create_product_price_on_product_create(self):
        test = self._create_product(name="Test Product", list_price=1000.0)
        self.assertTrue(
            self.env['product.price'].search([('product_product_id', '=', test.id)])
        )

    def test_invalidate_product_price_on_list_price_change(self):
        variant_prices = self.env['product.price'].search([
            ('product_tmpl_id', '=', self.product_template_book.id),
            ('pricelist_id', '=', self.pricelist.id),
        ])
        self._imitate_cron_price_calculation(variant_prices)
        self.env.flush_all()
        self.product_template_book.list_price = 2000.0
        self.env.flush_all()
        self.env.invalidate_all()
        self.assertFalse(all(map(self._price_is_valid, variant_prices)))

    def test_invalidate_product_price_on_standard_price_change_for_corresponding_pricelists(self):
        """Test that price is invalidated only for pricelists based on standard price."""
        # Create a pricelist based on standard price
        pricelist_on_standard = self._create_pricelist(
            name="Pricelist on Standard Price",
            currency_id=self.currency.id,
            item_ids=[Command.create({
                'price_discount': 10,
                'base': 'standard_price',
            })],
        )
        var_price_on_standard = self._get_product_price(self.red_book.id, pricelist_on_standard.id)
        var_price = self._get_product_price(self.red_book.id, self.pricelist.id)
        self._imitate_cron_price_calculation(var_price | var_price_on_standard)
        self.env.flush_all()
        self.red_book.standard_price = 200.0
        self.env.flush_all()
        self.env.invalidate_all()
        self.assertFalse(self._price_is_valid(var_price_on_standard))
        self.assertTrue(self._price_is_valid(var_price))

    def test_invalidate_product_price_on_ptav_price_extra_change(self):
        product_price_blue = self._get_product_price(self.blue_book.id, self.pricelist.id)
        product_price_red = self._get_product_price(self.red_book.id, self.pricelist.id)
        self._imitate_cron_price_calculation(product_price_blue | product_price_red)
        self.env.flush_all()
        self.blue_book.product_template_attribute_value_ids.filtered(
            lambda v: v.name == 'blue'
        ).price_extra = 200.0
        self.env.flush_all()
        self.env.invalidate_all()
        self.assertFalse(self._price_is_valid(product_price_blue))
        self.assertTrue(self._price_is_valid(product_price_red))

    def test_create_product_price_on_pricelist_create(self):
        self._create_pricelist(name="New Pricelist", currency_id=self.currency.id)
        self.assertTrue(self.env['product.price'].search([
            ('pricelist_id', '=', self.pricelist.id)
        ]))

    def test_invalidate_product_price_on_pricelist_currency_change(self):
        pricelist_prices = self.env['product.price'].search([
            ('pricelist_id', '=', self.pricelist.id),
        ])
        self._imitate_cron_price_calculation(pricelist_prices)
        self.env.flush_all()
        self.pricelist.currency_id = self.ref('base.EUR')
        self.env.flush_all()
        self.env.invalidate_all()
        self.assertFalse(all(map(self._price_is_valid, pricelist_prices)))

    def test_invalidate_chained_pricelist_prices_on_base_pricelist_change(self):
        test_pricelist = self._create_pricelist(name="Test Pricelist")
        chained_pricelist = self._create_pricelist(
            name="Chained Pricelist",
            item_ids=[Command.create({
                'base': 'pricelist',
                'base_pricelist_id': test_pricelist.id,
            })],
        )
        chained_pricelist_prices = self.env['product.price'].search([
            ('pricelist_id', '=', chained_pricelist.id),
        ])
        self._imitate_cron_price_calculation(chained_pricelist_prices)
        self.env.flush_all()
        chained_pricelist.item_ids[0].base_pricelist_id = self.pricelist.id
        self.env.flush_all()
        self.env.invalidate_all()
        self.assertFalse(all(map(self._price_is_valid, chained_pricelist_prices)))

    def test_invalidate_product_price_on_pricelist_rule_add(self):
        pricelist_prices = self.env['product.price'].search([
            ('pricelist_id', '=', self.pricelist.id)
        ])
        self._imitate_cron_price_calculation(pricelist_prices)
        self.pricelist.item_ids.create({'base': 'list_price'})
        self.assertFalse(all(map(self._price_is_valid, pricelist_prices)))

    def test_invalidate_product_price_on_pricelist_rule_change(self):
        pricelist_prices = self.env['product.price'].search([
            ('pricelist_id', '=', self.pricelist.id)
        ])
        self.pricelist.item_ids.create({'compute_price': 'fixed', 'fixed_price': 1000.0})
        pricelist_prices.pricelist_item_id = self.pricelist.item_ids
        self._imitate_cron_price_calculation(pricelist_prices)
        self.pricelist.item_ids.fixed_price = 100
        self.assertFalse(all(map(self._price_is_valid, pricelist_prices)))

    def test_invalidate_chained_pricelist_prices_on_base_pricelist_rule_change(self):
        chained_pricelist = self._create_pricelist(
            name="Chained Pricelist",
            item_ids=[Command.create({
                'base': 'pricelist',
                'base_pricelist_id': self.pricelist.id,
            })],
        )
        self.pricelist.item_ids.create({'compute_price': 'fixed', 'fixed_price': 1000.0})
        chained_pricelist_prices = self.env['product.price'].search([
            ('pricelist_id', '=', chained_pricelist.id)
        ])
        self._imitate_cron_price_calculation(chained_pricelist_prices)
        self.pricelist.item_ids.fixed_price = 100
        self.assertFalse(all(map(self._price_is_valid, chained_pricelist_prices)))


    def test_invalidate_product_price_on_pricelist_rule_delete(self):
        pricelist_prices = self.env['product.price'].search([
            ('pricelist_id', '=', self.pricelist.id)
        ])
        self.pricelist.item_ids.create({'compute_price': 'fixed', 'fixed_price': 1000.0})
        self._imitate_cron_price_calculation(pricelist_prices)
        self.pricelist.item_ids.unlink()
        self.assertFalse(all(map(self._price_is_valid, pricelist_prices)))
