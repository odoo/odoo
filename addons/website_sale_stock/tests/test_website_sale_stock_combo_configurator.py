# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
from odoo.tests import tagged
from odoo.tests.common import HttpCase

from odoo.addons.website_sale_stock.tests.common import WebsiteSaleStockCommon


@tagged('post_install', '-at_install')
class TestWebsiteSaleStockComboConfigurator(HttpCase, WebsiteSaleStockCommon):

    def test_website_sale_stock_combo_configurator(self):
        product = self._create_product(
            name="Test product",
            is_storable=True,
            allow_out_of_stock_order=False,
        )
        self.env['stock.quant'].create({
            'product_id': product.id,
            'location_id': self.warehouse.lot_stock_id.id,
            'quantity': 2,
        })
        combo = self.env['product.combo'].create({
            'name': "Test combo",
            'combo_item_ids': [
                Command.create({'product_id': product.id}),
                Command.create({'product_id': self._create_product().id}),
            ],
        })
        self._create_product(
            name="Combo product",
            type='combo',
            combo_ids=[Command.link(combo.id)]
        )
        self.start_tour('/', 'website_sale_stock_combo_configurator', login='admin')
