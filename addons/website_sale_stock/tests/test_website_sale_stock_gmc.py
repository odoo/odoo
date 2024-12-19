# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
import pytz

from odoo.tests import tagged

from odoo.addons.website_sale.tests.test_website_sale_gmc import TestWebsiteSaleGMCCommon


@tagged('post_install', '-at_install')
class TestWebsiteSaleStockGMCItems(TestWebsiteSaleGMCCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.website.warehouse_id = cls.env.ref('stock.warehouse0')
        cls.stock_loc = cls.website.warehouse_id.lot_stock_id
        cls.supplier_loc = cls.env.ref('stock.stock_location_suppliers')
        cls.black_mouse.write({
            'is_storable': True,
            'allow_out_of_stock_order': False,
        })
        cls.white_mouse.write({
            'is_storable': True,
            'allow_out_of_stock_order': True,
        })
        cls.keyboard.write({
            'is_storable': True,
            'allow_out_of_stock_order': False,
        })

    def replenish(self, product, loc_dest, qty, planned_date):
        """Create a picking to replenish the stock at `planned_date`."""
        picking = self.env['stock.picking'].create({
            'picking_type_id': self.env.ref('stock.picking_type_in').id,
            'location_id': self.supplier_loc.id,
            'location_dest_id': loc_dest.id,
        })
        self.env['stock.move'].create({
            'name': 'Replenishment',
            'product_id': product.id,
            'product_uom_qty': qty,
            'product_uom': product.uom_id.id,
            'location_id': self.supplier_loc.id,
            'location_dest_id': loc_dest.id,
            'date': planned_date,
            'picking_id': picking.id,
        })
        picking.action_confirm()

    def test_gmc_product_availability_override(self):
        self.env['stock.quant'].create({
            'product_id': self.black_mouse.id,
            'quantity': 10.0,
            'location_id': self.stock_loc.id,
        })
        self.update_items()
        self.assertEqual(
            'in_stock',
            self.black_mouse_item['availability'],
            'Black mouse has some stock => in_stock',
        )
        self.assertEqual(
            'in_stock',
            self.white_mouse_item['availability'],
            'White mouse does not have stock, but allow out of stock order => in_stock',
        )
        self.assertEqual(
            'out_of_stock',
            self.items[self.keyboard]['availability'],
            'Keyboard does not have stock and does not allow out of stock order => out_of_stock',
        )

        planned_date = datetime.datetime.now() + datetime.timedelta(10)
        self.replenish(self.white_mouse, self.stock_loc, 10.0, planned_date)
        self.update_items()
        self.assertEqual('backorder', self.white_mouse_item['availability'])
        self.assertEqual(
            pytz.UTC.localize(planned_date).isoformat(timespec='minutes'),
            self.white_mouse_item['availability_date'],
        )

    def test_keep_website_stock_seperate(self):
        """Test that stock availabilies are website specific."""
        website_1_planned_date = datetime.datetime.now() + datetime.timedelta(10)
        self.replenish(self.white_mouse, self.stock_loc, 10.0, website_1_planned_date)
        # setup second website with seperate stock
        website_2_warehouse = self.env['stock.warehouse'].create({'name': 'Stock 2', 'code': 'WH2'})
        website_2 = self.env['website'].create({
            'name': 'Website Test 2',
            'domain': 'https://my-website.net',
            'warehouse_id': website_2_warehouse.id,
        })
        website_2_planned_date = datetime.datetime.now() + datetime.timedelta(20)
        self.replenish(
            self.white_mouse, website_2_warehouse.lot_stock_id, 10.0, website_2_planned_date
        )

        self.update_items()
        self.assertEqual('backorder', self.white_mouse_item['availability'])
        self.assertEqual(
            pytz.UTC.localize(website_1_planned_date).isoformat(timespec='minutes'),
            self.white_mouse_item['availability_date'],
            'Should use moves related to self.website to figure out the availability_date',
        )

        self.update_items(website=website_2)
        self.assertEqual('backorder', self.white_mouse_item['availability'])
        self.assertEqual(
            pytz.UTC.localize(website_2_planned_date).isoformat(timespec='minutes'),
            self.white_mouse_item['availability_date'],
            'Should use moves related to website_2 to figure out the availability_date',
        )
