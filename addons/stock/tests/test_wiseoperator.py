# -*- coding: utf-8 -*-

from openerp.tests.common import TransactionCase

class TestWiseOperator(TransactionCase):
    def test_wise_operator(self):
        ProductObj = self.env['product.product']
        StockPickObj = self.env['stock.picking']
        StockPackObj = self.env['stock.pack.operation']
        StockQuantPackObj = self.env['stock.quant.package']
        StockQuantObj = self.env['stock.quant']
        LinkObj = self.env['stock.move.operation.link']

        product_wise = ProductObj.create({
            'name': 'Wise Unit',
            'type': 'product',
            'categ_id': self.env.ref('product.product_category_1').id,
            'uom_id': self.env.ref('product.product_uom_unit').id,
            'uom_po_id': self.env.ref('product.product_uom_unit').id,
            })
        pick1_wise = StockPickObj.create({
            'name': 'Incoming picking',
            'partner_id': self.env.ref('base.res_partner_2').id,
            'picking_type_id': self.env.ref('stock.picking_type_in').id,
            'location_id': self.env.ref('stock.stock_location_suppliers').id,
            'location_dest_id': self.env.ref('stock.stock_location_stock').id,
            'move_lines': [(0, 0, {'name': product_wise.name, 'product_id': product_wise.id, 'product_uom_qty': 10.00, 'location_id': self.env.ref('stock.stock_location_suppliers').id, 'location_dest_id': self.env.ref('stock.stock_location_stock').id, 'product_uom': self.env.ref('product.product_uom_unit').id})]
            })

        pick1_wise.action_confirm()
        pick1_wise.do_prepare_partial()

        package1 = StockQuantPackObj.create({'name': 'Pack 1'})
        pick1_wise.pack_operation_ids[0].write({'result_package_id': package1.id, 'product_qty': 4, 'location_dest_id': self.env.ref('stock.stock_location_components').id})
        new_pack1 = StockPackObj.create({'product_id': product_wise.id, 'product_uom_id': self.env.ref('product.product_uom_unit').id, 'picking_id': pick1_wise.id, 'product_qty': 6.0, 'location_id': self.env.ref('stock.stock_location_suppliers').id, 'location_dest_id': self.env.ref('stock.stock_location_14').id})

        pick1_wise.do_transfer()

        reco_id = StockQuantObj.search([('product_id', '=', product_wise.id)])
        self.assertEqual(len(reco_id), 2, "The number of quants created is not correct")

        delivery_order_wise1 = StockPickObj.create({
            'name': 'outgoing picking',
            'partner_id': self.env.ref('base.res_partner_4').id,
            'picking_type_id': self.env.ref('stock.picking_type_out').id,
            'location_id': self.env.ref('stock.stock_location_stock').id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
            'move_lines': [(0, 0, {'name': product_wise.name, 'product_id': product_wise.id, 'product_uom_qty': 5.0, 'location_id': self.env.ref('stock.stock_location_stock').id, 'location_dest_id': self.env.ref('stock.stock_location_customers').id, 'product_uom': self.env.ref('product.product_uom_unit').id})]
            })

        delivery_order_wise1.action_confirm()
        delivery_order_wise1.action_assign()

        delivery_order_wise2 = StockPickObj.create({
            'name': 'outgoing picking (copy)',
            'partner_id': self.env.ref('base.res_partner_4').id,
            'picking_type_id': self.env.ref('stock.picking_type_out').id,
            'location_id': self.env.ref('stock.stock_location_stock').id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
            'move_lines': [(0, 0, {'name': product_wise.name, 'product_id': product_wise.id, 'product_uom_qty': 5.00, 'location_id': self.env.ref('stock.stock_location_stock').id, 'location_dest_id': self.env.ref('stock.stock_location_customers').id, 'product_uom': self.env.ref('product.product_uom_unit').id})]
            })

        delivery_order_wise2.action_confirm()
        delivery_order_wise2.action_assign()

        picking1 = delivery_order_wise1
        picking2 = delivery_order_wise2
        pack_ids1 = picking1.pack_operation_ids
        pack_ids2 = picking2.pack_operation_ids
        pack_ids1.write({'picking_id': picking2.id})
        pack_ids2.write({'picking_id': picking1.id})
        links = LinkObj.search([('operation_id', 'in', pack_ids1.ids + pack_ids2.ids)])
        links.unlink()

        delivery_order_wise1.do_transfer()

        reco_id = StockQuantObj.search([('product_id', '=', product_wise.id), ('qty', '<', 0.0)])
        self.assertEqual(len(reco_id), 0, 'This should not have created a negative quant')

        self.assertEqual(delivery_order_wise2.state, 'partially_available', "Delivery order 2 should be back in confirmed state")

        delivery_order_wise2.do_transfer()

        reco_id = StockQuantObj.search([('product_id', '=', product_wise.id)])
        self.assertTrue(all([x.location_id.id == self.env.ref('stock.stock_location_customers').id and x.qty > 0.0 for x in reco_id]), "Negative quant or wrong location detected")
