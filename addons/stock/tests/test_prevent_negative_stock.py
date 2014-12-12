# -*- coding: utf-8 -*-

from openerp.addons.stock.tests.common import TestStockCommon
from openerp.osv.orm import except_orm


class TestPreventNegativeStock(TestStockCommon):
    def test_prevent_negative_stock(self):
        """ Testing for Prevent Negative Stock creation."""
        data_obj = self.env['ir.model.data']

        # Model Data
        prod_categ_id = data_obj.xmlid_to_res_id('product.product_category_1')
        prod_uom_id = data_obj.xmlid_to_res_id('product.product_uom_kgm')

        product_vals = {
            'default_code': 'NEG',
            'name': 'Test Negative',
            'type': 'product',
            'categ_id': prod_categ_id,
            'list_price': 100.0,
            'standard_price': 70.0,
            'uom_id': prod_uom_id,
            'uom_po_id': prod_uom_id,
            'description': 'Test Negative Product'
        }

        # Test Negative Product Created.
        product = self.env['product.product'].create(product_vals)

        # Out picking created for Test Negative product.
        picking = self.env['stock.picking'].create({'picking_type_id': self.picking_type_out})

        move_vals = {
            'name': 'Test Negative',
            'picking_id': picking.id,
            'product_id': product.id,
            'product_uom': prod_uom_id,
            'product_uom_qty': 400.0,
            'location_id': self.stock_location,
            'location_dest_id': self.customer_location,
            'picking_type_id': self.picking_type_out,
        }

        # Stock Move created for Test Negative product.
        self.env['stock.move'].create(move_vals)

        # Set No negative true in current user company.
        user = self.env['res.users'].browse(self.uid)
        user.company_id.write({'no_negative_stock': True})

        # Transfer picking to check it will raise Warning .
        with self.assertRaises(except_orm):
            picking.do_transfer()
