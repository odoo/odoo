# -*- coding: utf-8 -*-

from openerp.tests.common import TransactionCase

class TestPackingneg(TransactionCase):
    def test_packingneg(self):
        ProductObj = self.env['product.product']
        PickingObj = self.env['stock.picking']
        StockPackObj = self.env['stock.pack.operation']
        StockQuantPackObj = self.env['stock.quant.package']
        LotObj = self.env['stock.production.lot']
        StockQuantObj = self.env['stock.quant']

        product_neg = ProductObj.create({
            'name': 'Negative product',
            'type': 'product',
            'categ_id': self.env.ref('product.product_category_1').id,
            'list_price': 100.0,
            'standard_price': 70.0,
            'seller_ids': [(0, 0, {'delay': 1,  'name': self.env.ref('base.res_partner_2').id, 'min_qty': 2.0, 'qty': 5.0})],
            'uom_id': self.env.ref('product.product_uom_unit').id,
            'uom_po_id': self.env.ref('product.product_uom_unit').id
            })
        pick_neg = PickingObj.create({
            'name': 'Incoming picking',
            'partner_id': self.env.ref('base.res_partner_2').id,
            'picking_type_id': self.env.ref('stock.picking_type_in').id,
            'location_id': self.env.ref('stock.stock_location_suppliers').id,
            'location_dest_id': self.env.ref('stock.stock_location_stock').id,
            'move_lines': [(0, 0, {'name': product_neg.name, 'product_id': product_neg.id, 'product_uom_qty': 300.00, 'location_id': self.env.ref('stock.stock_location_suppliers').id, 'location_dest_id': self.env.ref('stock.stock_location_stock').id, 'product_uom': self.env.ref('product.product_uom_unit').id})]
            })

        pick_neg.action_confirm()

        #Change quantity of first to 120 and create 2 others quant operations
        #create lot A
        lot_a = LotObj.create({'name': 'Lot neg', 'product_id': product_neg.id})
        #create package
        package1 = StockQuantPackObj.create({'name': 'Palneg 1'})
        package2 = StockQuantPackObj.create({'name': 'Palneg 2'})
        package3 = StockQuantPackObj.create({'name': 'Palneg 3'})
        #Create package for each line and assign it as result_package_id
        #create pack operation
        pick_neg.pack_operation_ids[0].write({'result_package_id': package1.id, 'product_qty': 120})
        new_pack1 = StockPackObj.create({'product_id': product_neg.id, 'product_uom_id': self.env.ref('product.product_uom_unit').id, 'picking_id': pick_neg.id, 'pack_lot_ids': [(0, 0, {'lot_id': lot_a.id, 'qty': 120})], 'result_package_id': package2.id, 'product_qty': 120, 'location_id': self.env.ref('stock.stock_location_suppliers').id, 'location_dest_id': self.env.ref('stock.stock_location_stock').id})

        new_pack2 = StockPackObj.create({'product_id': product_neg.id, 'product_uom_id': self.env.ref('product.product_uom_unit').id, 'picking_id': pick_neg.id, 'result_package_id': package3.id, 'product_qty': 60, 'location_id': self.env.ref('stock.stock_location_suppliers').id, 'location_dest_id': self.env.ref('stock.stock_location_stock').id})

        pick_neg.do_transfer()

        delivery_order_neg = PickingObj.create({
            'name': 'outgoing picking',
            'partner_id': self.env.ref('base.res_partner_4').id,
            'picking_type_id': self.env.ref('stock.picking_type_out').id,
            'location_id': self.env.ref('stock.stock_location_stock').id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
            'move_lines': [(0, 0, {'name': product_neg.name, 'product_id': product_neg.id, 'product_uom_qty': 300.00, 'location_id': self.env.ref('stock.stock_location_stock').id, 'location_dest_id': self.env.ref('stock.stock_location_customers').id, 'product_uom': self.env.ref('product.product_uom_unit').id})]
            })

        delivery_order_neg.action_confirm()
        delivery_order_neg.action_assign()

        for rec in delivery_order_neg.pack_operation_ids:
            if rec.package_id.name == 'Palneg 2':
                lot_ids = LotObj.search([('product_id', '=', product_neg.id), ('name', '=', 'Lot neg')])
                rec.write({'product_id': product_neg.id, 'product_qty': 140, 'pack_lot_ids': [(0, 0, {'lot_id': lot_ids[0].id, 'qty': 140})], 'product_uom_id': self.env.ref('product.product_uom_unit').id})
            if rec.package_id.name == 'Palneg 3':
                rec.write({'product_id': product_neg.id, 'product_qty': 10, 'product_uom_id': self.env.ref('product.product_uom_unit').id})

        delivery_order_neg.do_transfer()

        reco_id = StockQuantObj.search([('product_id', '=', product_neg.id)])
        pallet_3_stock_qty = 0
        for rec in reco_id:
            if rec.package_id.name == 'Palneg 1' and rec.location_id.id == self.env.ref('stock.stock_location_customers').id:
                assert rec.qty == 120, "Should have 120 pieces on pallet 1"
            elif rec.package_id.name == 'Palneg 2' and rec.location_id.id == self.env.ref('stock.stock_location_stock').id:
                assert rec.qty == -20, "Should have -20 pieces in stock on pallet 2. Got " + str(rec.qty)
                assert rec.lot_id.name == 'Lot neg', "It should have kept its Lot"
            elif rec.lot_id.name == 'Lot neg' and rec.location_id.id == self.env.ref('stock.stock_location_customers').id:
                assert ((rec.qty == 20 or rec.qty == 120) and not rec.package_id), "Should have 140 pieces (120+20) in customer location from pallet 2 and lot A"
            elif rec.package_id.name == 'Palneg 3' and rec.location_id.id == self.env.ref('stock.stock_location_stock').id:
                pallet_3_stock_qty += rec.qty
            elif not rec.package_id and not rec.lot_id and rec.location_id.id == self.env.ref('stock.stock_location_customers').id:
                assert rec.qty == 10, "Should have 10 pieces in customer location from pallet 3"
            else:
                assert False, "Unrecognized quant"
        assert pallet_3_stock_qty == 50, "Should have 50 pieces in stock on pallet 3"

        delivery_reconcile = PickingObj.create({
            'name': 'reconciling_delivery',
            'partner_id': self.env.ref('base.res_partner_4').id,
            'picking_type_id': self.env.ref('stock.picking_type_in').id,
            'location_id': self.env.ref('stock.stock_location_suppliers').id,
            'location_dest_id': self.env.ref('stock.stock_location_stock').id,
            'move_lines': [(0, 0, {'name': product_neg.name, 'product_id': product_neg.id, 'product_uom_qty': 20.0, 'location_id': self.env.ref('stock.stock_location_suppliers').id, 'location_dest_id': self.env.ref('stock.stock_location_stock').id, 'product_uom': self.env.ref('product.product_uom_unit').id})]
            })

        delivery_reconcile.action_confirm()
        lot_ids = LotObj.search([('product_id', '=', product_neg.id), ('name', '=', 'Lot neg')])
        pack_ids = StockQuantPackObj.search([('name', '=', 'Palneg 2')])
        delivery_reconcile.pack_operation_ids[0].write({'pack_lot_ids': {'lot_id': lot_ids[0].id, 'qty': 20.0}, 'result_package_id': pack_ids[0].id})
        delivery_reconcile.do_transfer()

        neg_quants = StockQuantObj.search([('product_id', '=', product_neg.id), ('qty', '<', 0)])
        assert len(neg_quants) == 0, "Negative quants should have been reconciled"
        customer_quant = StockQuantObj.search([('product_id', '=', product_neg.id), ('location_id', '=', self.env.ref('stock.stock_location_customers').id), ('lot_id.name', '=', 'Lot neg'), ('qty', '=', 20)])
        assert delivery_reconcile.move_lines[0].id in [x.id for x in customer_quant[0].history_ids]
