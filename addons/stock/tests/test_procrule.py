# -*- coding: utf-8 -*-

from openerp.tests.common import TransactionCase

class TestProcurementRule(TransactionCase):
    def test_procurement_rule(self):
        ProcRuleObj = self.env['procurement.rule']
        StockPickObj = self.env['stock.picking']
        ProOrderObj = self.env['procurement.order']
        StockMoveObj = self.env['stock.move']

        global_proc_rule = ProcRuleObj.create({
            'name': 'Stock -> output',
            'action': 'move',
            'picking_type_id': self.env.ref('stock.picking_type_internal').id,
            'location_src_id': self.env.ref('stock.stock_location_stock').id,
            'location_id': self.env.ref('stock.stock_location_output').id
            })

        pick_output = StockPickObj.create({
            'name': 'Delivery order for procurement',
            'partner_id': self.env.ref('base.res_partner_2').id,
            'picking_type_id': self.env.ref('stock.picking_type_out').id,
            'location_id': self.env.ref('stock.stock_location_output').id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
            'move_lines': [(0, 0, {'name': self.env.ref('product.product_product_3').name, 'product_id': self.env.ref('product.product_product_3').id, 'product_uom_qty': 10.0, 'procure_method': 'make_to_order', 'product_uom': self.env.ref('product.product_uom_unit').id})]
            })

        pick_output.action_confirm()

        ProOrderObj.run_scheduler()

        move_id = StockMoveObj.search([('product_id', '=', self.env.ref('product.product_product_3').id), ('location_id', '=', self.env.ref('stock.stock_location_stock').id),
        ('location_dest_id', '=', self.env.ref('stock.stock_location_output').id), ('move_dest_id', '=', pick_output.move_lines[0].id)])
        self.assertEqual(len(move_id), 1, "It should have created a picking from Stock to Output with the original picking as destination")
