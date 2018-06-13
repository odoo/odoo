# -*- coding: utf-8 -*-

from openerp.tests.common import TransactionCase
from openerp.exceptions import UserError


class TestStockScrap(TransactionCase):

    def setUp(self):
        super(TestStockScrap, self).setUp()
        self.user_demo = self.env.ref('base.user_demo')
        self.scrap_obj = self.env['stock.scrap']
        self.picking_obj = self.env['stock.picking']
        self.stock_loc = self.browse_ref('stock.stock_location_stock')
        self.customer_loc = self.browse_ref('stock.stock_location_customers')
        
        # Stockable product
        self.product_stockable = self.env['product.product'].create({
            'type': 'product',
            'name': 'Stockable Product',
            'uom_id': self.env.ref('product.product_uom_unit').id,
            'uom_po_id': self.env.ref('product.product_uom_unit').id,
        })
        
        # Consumable product
        self.product_consumable = self.env['product.product'].create({
            'type': 'consu',
            'name': 'Consumable Product',
            'uom_id': self.env.ref('product.product_uom_unit').id,
            'uom_po_id': self.env.ref('product.product_uom_unit').id,
        })

        self._update_product_qty(self.product_stockable)

    def _update_product_qty(self, product):
        product_qty = self.env['stock.change.product.qty'].create({
            'location_id': self.stock_loc.id,
            'product_id': product.id,
            'new_quantity': 100.0,
        })
        product_qty.change_product_qty()
        return product_qty

    def _prepare_picking(self, product):
        picking = self.picking_obj.create({
            'name': 'picking - test',
            'location_id': self.stock_loc.id,
            'location_dest_id': self.customer_loc.id,
            'picking_type_id': self.ref('stock.picking_type_out'),
            'move_lines': [(0, 0, {
                'name': product.name,
                'product_id': product.id,
                'product_uom_qty': 20.0,
                'product_uom': product.uom_id.id,
            })]
        })
        return picking

    def test_stock_scrap_01(self):
        """ Standalone scrap a stockable product """
        with self.assertRaises(UserError):
            self.scrap_obj.create({
                'name': 'scrap - grand test',
                'product_id': self.product_stockable.id,
                'product_uom_id': self.ref('product.product_uom_unit'),
                'scrap_qty': 120,
            })
        self.assertEquals(self.product_stockable.qty_available, 100.0)

    def test_stock_scrap_02(self):
        """ Scrap a stockable product from a picking """
        picking = self._prepare_picking(self.product_stockable)
        scrap = self.scrap_obj.create({
            'name': 'scrap - grand test',
            'product_id': self.product_stockable.id,
            'product_uom_id': self.ref('product.product_uom_unit'),
            'picking_id': picking.id,
            'scrap_qty': 80,
        })
        self.assertEquals(scrap.state, 'done')
        self.assertEquals(self.product_stockable.qty_available, 20.0)

    def test_stock_scrap_03(self):
        """ Standalone scrap a consumable product """
        scrap = self.scrap_obj.create({
            'name': 'scrap - grand test',
            'product_id': self.product_consumable.id,
            'product_uom_id': self.ref('product.product_uom_unit'),
            'scrap_qty': 100,
        })
        self.assertEquals(scrap.state, 'done')
        self.assertEquals(self.product_consumable.qty_available, -100.0)
        with self.assertRaises(UserError):
            scrap.sudo(self.user_demo).unlink()

    def test_stock_scrap_04(self):
        """ Scrap a consumable product from a picking """
        picking = self._prepare_picking(self.product_consumable)
        scrap = self.scrap_obj.create({
            'name': 'scrap - grand test',
            'product_id': self.product_consumable.id,
            'product_uom_id': self.ref('product.product_uom_unit'),
            'picking_id': picking.id,
            'scrap_qty': 100,
        })
        self.assertEquals(scrap.state, 'done')
        self.assertEquals(self.product_consumable.qty_available, -100.0)
