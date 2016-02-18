# -*- coding: utf-8 -*-

from openerp.tests.common import TransactionCase

class TestPacking(TransactionCase):
    def test_stock_packing(self):
        ProductObj = self.env['product.product']
        StockPickObj = self.env['stock.picking']
        StockPackObj = self.env['stock.pack.operation']
        StockQuantPackObj = self.env['stock.quant.package']
        stockProdLotObj = self.env['stock.production.lot']
        StockQuantObj = self.env['stock.quant']

        product1 = ProductObj.create({
            'name': 'Nice product',
            'type': 'product',
            'categ_id': self.env.ref('product.product_category_1').id,
            'list_price': 100.0,
            'standard_price': 70.0,
            'seller_ids': [(0, 0, {'delay': 1,  'name': self.env.ref('base.res_partner_2').id, 'min_qty': 2.0, 'qty': 5.0})],
            'uom_id': self.env.ref('product.product_uom_unit').id,
            'uom_po_id': self.env.ref('product.product_uom_unit').id,
            })

        pick1 = StockPickObj.create({
            'name': 'Incoming picking',
            'partner_id': self.env.ref('base.res_partner_2').id,
            'picking_type_id': self.env.ref('stock.picking_type_in').id,
            'location_id': self.env.ref('stock.stock_location_suppliers').id,
            'location_dest_id': self.env.ref('stock.stock_location_stock').id,
            'move_lines': [(0, 0, {'name': product1.name, 'product_id': product1.id, 'product_uom_qty': 300.00, 'location_id': self.env.ref('stock.stock_location_suppliers').id, 'location_dest_id': self.env.ref('stock.stock_location_stock').id, 'product_uom': self.env.ref('product.product_uom_unit').id})]
            })
        pick1.action_confirm()
        pick1.do_prepare_partial()

        lot_a = stockProdLotObj.create({
            'name': 'Lot A',
            'product_id': product1.id
            })

        package1 = StockQuantPackObj.create({'name': 'Pallet 1'})
        package2 = StockQuantPackObj.create({'name': 'Pallet 2'})
        package3 = StockQuantPackObj.create({'name': 'Pallet 3'})

        pick1.pack_operation_ids[0].write({'result_package_id': package1.id, 'product_qty': 120})
        new_pack1 = StockPackObj.create({'product_id': product1.id, 'product_uom_id': self.env.ref('product.product_uom_unit').id, 'picking_id': pick1.id, 'pack_lot_ids': [(0, 0, {'lot_id': lot_a.id, 'qty': 120})], 'result_package_id': package2.id, 'product_qty': 120, 'location_id': self.env.ref('stock.stock_location_suppliers').id, 'location_dest_id': self.env.ref('stock.stock_location_stock').id})
        new_pack2 = StockPackObj.create({'product_id': product1.id, 'product_uom_id': self.env.ref('product.product_uom_unit').id, 'picking_id': pick1.id, 'result_package_id': package3.id, 'product_qty': 60, 'location_id': self.env.ref('stock.stock_location_suppliers').id, 'location_dest_id': self.env.ref('stock.stock_location_stock').id})

        pick1.do_transfer()

        reco_id = StockQuantObj.search([('product_id', '=', product1.id)])
        self.assertEqual(len(reco_id), 3, "The number of quants created is not correct")
        for rec in reco_id:
            if rec.package_id.name == 'Pallet 1':
                self.assertEqual(rec.qty, 120, "Should have 120 pieces on pallet 1, got " + str(rec.qty)
            elif rec.package_id.name == 'Pallet 2':
                self.assertEqual(rec.qty, 120, "Should have 120 pieces on pallet 2, got " + str(rec.qty)
            elif rec.package_id.name == 'Pallet 3':
                self.assertEqual(rec.qty, 60, "Should have 60 pieces on pallet 3")

        backorder = StockPickObj.search([('backorder_id', '=', pick1.id)])
        self.assertFalse(backorder, "")
        #Check extra moves created
        self.assertEqual(len(pick1.move_lines), 1, "")

        delivery_order1 = StockPickObj.create({
            'name': 'outgoing picking',
            'partner_id': self.env.ref('base.res_partner_4').id,
            'picking_type_id': self.env.ref('stock.picking_type_out').id,
            'location_id': self.env.ref('stock.stock_location_stock').id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
            'move_lines': [(0, 0, {'name': product1.name, 'product_id': product1.id, 'product_uom_qty': 300.00, 'location_id': self.env.ref('stock.stock_location_stock').id, 'location_dest_id': self.env.ref('stock.stock_location_customers').id, 'product_uom': self.env.ref('product.product_uom_unit').id})]
            })

        delivery_order1.action_confirm()
        delivery_order1.action_assign()

        delivery_order1.do_prepare_partial()
        for rec in delivery_order1.pack_operation_ids:
            if rec.package_id.name == 'Pallet 2':
                lot_ids = stockProdLotObj.search([('product_id', '=', product1.id), ('name', '=', 'Lot A')])
                rec.write({'product_id': product1.id, 'product_qty': 20, 'pack_lot_ids': [(0, 0, {'lot_id': lot_ids.ids[0], 'qty': 20})],  'product_uom_id': self.env.ref('product.product_uom_unit').id})
            if rec.package_id.name == 'Pallet 3':
                rec.write({'product_id': product1.id, 'product_qty': 10, 'product_uom_id': self.env.ref('product.product_uom_unit').id})

        delivery_order1.do_transfer()

        reco_id = StockQuantObj.search([('product_id', '=', product1.id)])
        for rec in reco_id:
            if rec.package_id.name == 'Pallet 1' and rec.location_id.id == self.env.ref('stock.stock_location_customers').id:
                self.assertEqual(rec.qty, 120, "Should have 120 pieces on pallet 1, got " + str(rec.qty))
            elif rec.package_id.name == 'Pallet 2' and rec.location_id.id == self.env.ref('stock.stock_location_stock').id:
                self.assertEqual(rec.qty, 100, "Should have 100 pieces in stock on pallet 2, got " + str(rec.qty))
            elif rec.lot_id.name == 'Lot A' and rec.location_id.id == self.env.ref('stock.stock_location_customers').id:
                self.assertTrue((rec.qty == 20 and not rec.package_id), "Should have 20 pieces in customer location from pallet 2")
            elif rec.package_id.name == 'Pallet 3' and rec.location_id.id == self.env.ref('stock.stock_location_stock').id:
                self.assertEqual(rec.qty, 50, "Should have 50 pieces in stock on pallet 3")
            elif not rec.package_id and not rec.lot_id and rec.location_id.id == self.env.ref('stock.stock_location_customers').id:
                self.assertEqual(rec.qty, 10, "Should have 10 pieces in customer location from pallet 3")
            else:
                self.assertTrue(False, "Unrecognized quant")

        backorder_ids = StockPickObj.search([('backorder_id', '=', delivery_order1.id)])
        self.assertTrue(backorder_ids, "Backorder should have been created")
        backorder_ids.action_assign()
        backorder_ids.do_prepare_partial()
        picking = backorder_ids[0]
        self.assertEqual(len(picking.pack_operation_ids), 2, "Wrong number of pack operation")
        for pack_op in picking.pack_operation_ids:
            self.assertEqual(pack_op.product_qty, 1, "Wrong quantity in pack operation (%s found instead of 1)" % (pack_op.product_qty))
            self.assertIn(pack_op.package_id.name, ('Pallet 2', 'Pallet 3'), "Wrong pallet info in pack operation (%s found)" % (pack_op.package_id.name))
        backorder_ids.do_transfer()

        reco_id = StockQuantObj.search([('product_id', '=', product1.id), ('location_id', '=', self.env.ref('stock.stock_location_stock').id)])
        total_qty = 0
        for rec in reco_id:
            total_qty += rec.qty
        self.assertEqual(total_qty, 0, "Total quantity in stock should be 0 as the backorder took everything out of stock")
        self.assertEqual(product1.qty_available, 0, "Quantity available should be 0 too")
