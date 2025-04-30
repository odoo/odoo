# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.website_sale.tests.website_sale_feed_common import WebsiteSaleFeedCommon


@tagged('post_install', '-at_install')
class TestWebsiteSaleStockMeta(WebsiteSaleFeedCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.feed_type = "meta"
        cls.website.warehouse_id = cls.env.ref('stock.warehouse0')
        cls.stock_loc = cls.website.warehouse_id.lot_stock_id
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
        cls.env.user.write({'group_ids': [(4, cls.env.ref('stock.group_stock_user').id)]})

    def test_meta_stock_info_sold_out(self):
        """Ensure 'out of stock' and quantity 0 when sold out."""
        self.update_items()
        self.assertEqual('in stock', self.blue_sofa_item['availability'])
        self.assertEqual('out of stock', self.items[self.blanket]['availability'])
        self.assertEqual('in stock', self.red_sofa_item['availability'])  # allow out_of_stock

    def test_meta_stock_info_in_stock_with_group(self):
        self.blue_sofa.allow_out_of_stock_order = False
        # setup second website with seperate stock
        warehouse_2 = self.env['stock.warehouse'].create({'name': 'Stock 2', 'code': 'WH2'})
        website_2 = self.env['website'].create({
            'name': 'Website Test 2',
            'domain': 'https://my-website.net',
            'warehouse_id': warehouse_2.id,
        })
        self.update_items(website=website_2)

        self.assertEqual('out of stock', self.red_sofa_item['availability'])
