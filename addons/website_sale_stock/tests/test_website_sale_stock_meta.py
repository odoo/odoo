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
        info = self.blanket._prepare_meta_stock_info()
        self.assertEqual(info['availability'], 'out of stock')
        self.assertEqual(info['quantity_to_sell_on_facebook'], 0)

    def test_meta_stock_info_in_stock_with_group(self):
        """Should show quantity when user has stock access."""
        info = self.blue_sofa._prepare_meta_stock_info()
        self.assertEqual(info['availability'], 'in stock')
        self.assertEqual(info['quantity_to_sell_on_facebook'], int(self.blue_sofa.qty_available))
