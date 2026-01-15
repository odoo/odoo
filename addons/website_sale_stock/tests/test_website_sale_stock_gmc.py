# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.website_sale.tests.common_gmc import WebsiteSaleGMCCommon


@tagged('post_install', '-at_install')
class TestWebsiteSaleStockGMC(WebsiteSaleGMCCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.website.warehouse_id = cls.env.ref('stock.warehouse0')
        cls.stock_loc = cls.website.warehouse_id.lot_stock_id
        cls.supplier_loc = cls.env.ref('stock.stock_location_suppliers')
        (cls.blue_sofa + cls.red_sofa + cls.blanket).write({
            'is_storable': True,
            'allow_out_of_stock_order': False,
        })
        cls.red_sofa.allow_out_of_stock_order = True
        cls.env['stock.quant'].create({
            'product_id': cls.blue_sofa.id,
            'quantity': 10.0,
            'location_id': cls.stock_loc.id,
        })

    def test_gmc_items_availability_check_stock(self):
        self.update_items()

        self.assertEqual('in_stock', self.blue_sofa_item['availability'])
        self.assertEqual('out_of_stock', self.items[self.blanket]['availability'])
        self.assertEqual('in_stock', self.red_sofa_item['availability']) # allow_out_of_stock_order

    def test_gmc_items_keep_website_stock_separate(self):
        self.blue_sofa.allow_out_of_stock_order = False
        # setup second website with seperate stock
        warehouse2 = self.env['stock.warehouse'].create({'name': 'Stock 2', 'code': 'WH2'})
        self.gmc_feed.website_id = self.env['website'].create({
            'name': 'Website Test 2',
            'domain': 'https://my-website.net',
            'warehouse_id': warehouse2.id,
        })

        self.update_items()

        self.assertEqual('out_of_stock', self.red_sofa_item['availability'])
