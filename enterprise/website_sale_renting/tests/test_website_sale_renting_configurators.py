# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
from odoo.tests import HttpCase, tagged

from odoo.addons.website_sale_renting.tests.common import TestWebsiteSaleRentingCommon


@tagged('post_install', '-at_install')
class TestWebsiteSaleRentingConfigurators(HttpCase, TestWebsiteSaleRentingCommon):

    def test_website_sale_renting_product_configurator(self):
        optional_product = self._create_product(
            name="Optional product",
            website_published=True,
            product_pricing_ids=[
                Command.create({'recurrence_id': self.recurrence_hour.id, 'price': 6}),
                Command.create({'recurrence_id': self.recurrence_day.id, 'price': 16}),
            ],
        )
        self._create_product(
            name="Main product",
            optional_product_ids=[Command.set(optional_product.product_tmpl_id.ids)],
            website_published=True,
            product_pricing_ids=[
                Command.create({'recurrence_id': self.recurrence_hour.id, 'price': 5}),
                Command.create({'recurrence_id': self.recurrence_day.id, 'price': 15}),
            ],
        )
        self.start_tour('/', 'website_sale_renting_product_configurator')

    def test_website_sale_renting_combo_configurator(self):
        combo = self.env['product.combo'].create({
            'name': "Test combo",
            'combo_item_ids': [
                Command.create({'product_id': self._create_product(website_published=True).id}),
                Command.create({'product_id': self._create_product(website_published=True).id}),
            ],
        })
        self._create_product(
            name="Combo product",
            type='combo',
            combo_ids=[Command.link(combo.id)],
            website_published=True,
            product_pricing_ids=[
                Command.create({'recurrence_id': self.recurrence_hour.id, 'price': 5}),
                Command.create({'recurrence_id': self.recurrence_day.id, 'price': 15}),
            ],
        )
        self.start_tour('/', 'website_sale_renting_combo_configurator')
