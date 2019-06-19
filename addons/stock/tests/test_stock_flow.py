# -*- coding: utf-8 -*-

from odoo.addons.stock.tests.common import TestStockCommon
from odoo.tests import Form
from odoo.tools import mute_logger, float_round
from odoo.exceptions import UserError

class TestStockFlow(TestStockCommon):
    def setUp(cls):
        super(TestStockFlow, cls).setUp()
        cls.partner_company2 = cls.env['res.partner'].create({
            'name': 'My Company (Chicago)-demo',
            'email': 'chicago@yourcompany.com',
            })
        cls.company = cls.env['res.company'].create({
            'currency_id': cls.env.ref('base.USD').id,
            'partner_id': cls.partner_company2.id,
            'name': 'My Company (Chicago)-demo',
            })

    @mute_logger('odoo.addons.base.models.ir_model', 'odoo.models')
    def test_00_picking_create_and_transfer_quantity(self):
        """ Basic stock operation on incoming and outgoing shipment. """
        LotObj = self.env['stock.production.lot']
        # ----------------------------------------------------------------------
        # Create incoming shipment of product A, B, C, D
        # ----------------------------------------------------------------------
        #   Product A ( 1 Unit ) , Product C ( 10 Unit )
        #   Product B ( 1 Unit ) , Product D ( 10 Unit )
        #   Product D ( 5 Unit )
        # ----------------------------------------------------------------------

        picking_in = self.PickingObj.create({
            'partner_id': self.partner_delta_id,
            'picking_type_id': self.picking_type_in,
            'location_id': self.supplier_location,
            'location_dest_id': self.stock_location})
        move_a = self.MoveObj.create({
            'name': self.productA.name,
            'product_id': self.productA.id,
            'product_uom_qty': 1,
            'product_uom': self.productA.uom_id.id,
            'picking_id': picking_in.id,
            'location_id': self.supplier_location,
            'location_dest_id': self.stock_location})
        move_b = self.MoveObj.create({
            'name': self.productB.name,
            'product_id': self.productB.id,
            'product_uom_qty': 1,
            'product_uom': self.productB.uom_id.id,
            'picking_id': picking_in.id,
            'location_id': self.supplier_location,
            'location_dest_id': self.stock_location})
        move_c = self.MoveObj.create({
            'name': self.productC.name,
            'product_id': self.productC.id,
            'product_uom_qty': 10,
            'product_uom': self.productC.uom_id.id,
            'picking_id': picking_in.id,
            'location_id': self.supplier_location,
            'location_dest_id': self.stock_location})
        move_d = self.MoveObj.create({
            'name': self.productD.name,
            'product_id': self.productD.id,
            'product_uom_qty': 10,
            'product_uom': self.productD.uom_id.id,
            'picking_id': picking_in.id,
            'location_id': self.supplier_location,
            'location_dest_id': self.stock_location})
        self.MoveObj.create({
            'name': self.productD.name,
            'product_id': self.productD.id,
            'product_uom_qty': 5,
            'product_uom': self.productD.uom_id.id,
            'picking_id': picking_in.id,
            'location_id': self.supplier_location,
            'location_dest_id': self.stock_location})

        # Check incoming shipment move lines state.
        for move in picking_in.move_lines:
            self.assertEqual(move.state, 'draft', 'Wrong state of move line.')
        # Confirm incoming shipment.
        picking_in.action_confirm()
        # Check incoming shipment move lines state.
        for move in picking_in.move_lines:
            self.assertEqual(move.state, 'assigned', 'Wrong state of move line.')

        # ----------------------------------------------------------------------
        # Replace pack operation of incoming shipments.
        # ----------------------------------------------------------------------
        picking_in.action_assign()
        move_a.move_line_ids.qty_done = 4
        move_b.move_line_ids.qty_done = 5
        move_c.move_line_ids.qty_done = 5
        move_d.move_line_ids.qty_done = 5
        lot2_productC = LotObj.create({'name': 'C Lot 2', 'product_id': self.productC.id})
        self.StockPackObj.create({
            'product_id': self.productC.id,
            'qty_done': 2,
            'product_uom_id': self.productC.uom_id.id,
            'location_id': self.supplier_location,
            'location_dest_id': self.stock_location,
            'move_id': move_c.id,
            'lot_id': lot2_productC.id,
            })
        self.StockPackObj.create({
            'product_id': self.productD.id,
            'qty_done': 2,
            'product_uom_id': self.productD.uom_id.id,
            'location_id': self.supplier_location,
            'location_dest_id': self.stock_location,
            'move_id': move_d.id
            })

        # Check incoming shipment total quantity of pack operation
        total_qty = sum(self.StockPackObj.search([('move_id', 'in', picking_in.move_lines.ids)]).mapped('qty_done'))
        self.assertEqual(total_qty, 23,  'Wrong quantity in pack operation')

        # Transfer Incoming Shipment.
        picking_in.action_done()

        # ----------------------------------------------------------------------
        # Check state, quantity and total moves of incoming shipment.
        # ----------------------------------------------------------------------

        # Check total no of move lines of incoming shipment. move line e disappear from original picking to go in backorder.
        self.assertEqual(len(picking_in.move_lines), 4, 'Wrong number of move lines.')
        # Check incoming shipment state.
        self.assertEqual(picking_in.state, 'done', 'Incoming shipment state should be done.')
        # Check incoming shipment move lines state.
        for move in picking_in.move_lines:
            self.assertEqual(move.state, 'done', 'Wrong state of move line.')
        # Check product A done quantity must be 3 and 1
        moves = self.MoveObj.search([('product_id', '=', self.productA.id), ('picking_id', '=', picking_in.id)])
        self.assertEqual(moves.product_uom_qty, 4.0, 'Wrong move quantity for product A.')
        # Check product B done quantity must be 4 and 1
        moves = self.MoveObj.search([('product_id', '=', self.productB.id), ('picking_id', '=', picking_in.id)])
        self.assertEqual(moves.product_uom_qty, 5.0, 'Wrong move quantity for product B.')
        # Check product C done quantity must be 7
        c_done_qty = self.MoveObj.search([('product_id', '=', self.productC.id), ('picking_id', '=', picking_in.id)], limit=1).product_uom_qty
        self.assertEqual(c_done_qty, 7.0, 'Wrong move quantity of product C (%s found instead of 7)' % (c_done_qty))
        # Check product D done quantity must be 7
        d_done_qty = self.MoveObj.search([('product_id', '=', self.productD.id), ('picking_id', '=', picking_in.id)], limit=1).product_uom_qty
        self.assertEqual(d_done_qty, 7.0, 'Wrong move quantity of product D (%s found instead of 7)' % (d_done_qty))

        # ----------------------------------------------------------------------
        # Check Back order of Incoming shipment.
        # ----------------------------------------------------------------------

        # Check back order created or not.
        back_order_in = self.PickingObj.search([('backorder_id', '=', picking_in.id)])
        self.assertEqual(len(back_order_in), 1, 'Back order should be created.')
        # Check total move lines of back order.
        self.assertEqual(len(back_order_in.move_lines), 2, 'Wrong number of move lines.')
        # Check back order should be created with 3 quantity of product C.
        moves = self.MoveObj.search([('product_id', '=', self.productC.id), ('picking_id', '=', back_order_in.id)])
        product_c_qty = [move.product_uom_qty for move in moves]
        self.assertEqual(sum(product_c_qty), 3.0, 'Wrong move quantity of product C (%s found instead of 3)' % (product_c_qty))
        # Check back order should be created with 8 quantity of product D.
        moves = self.MoveObj.search([('product_id', '=', self.productD.id), ('picking_id', '=', back_order_in.id)])
        product_d_qty = [move.product_uom_qty for move in moves]
        self.assertEqual(sum(product_d_qty), 8.0, 'Wrong move quantity of product D (%s found instead of 8)' % (product_d_qty))

        # ======================================================================
        # Create Outgoing shipment with ...
        #   product A ( 10 Unit ) , product B ( 5 Unit )
        #   product C (  3 unit ) , product D ( 10 Unit )
        # ======================================================================

        picking_out = self.PickingObj.create({
            'partner_id': self.partner_agrolite_id,
            'picking_type_id': self.picking_type_out,
            'location_id': self.stock_location,
            'location_dest_id': self.customer_location})
        move_cust_a = self.MoveObj.create({
            'name': self.productA.name,
            'product_id': self.productA.id,
            'product_uom_qty': 10,
            'product_uom': self.productA.uom_id.id,
            'picking_id': picking_out.id,
            'location_id': self.stock_location,
            'location_dest_id': self.customer_location})
        move_cust_b = self.MoveObj.create({
            'name': self.productB.name,
            'product_id': self.productB.id,
            'product_uom_qty': 5,
            'product_uom': self.productB.uom_id.id,
            'picking_id': picking_out.id,
            'location_id': self.stock_location,
            'location_dest_id': self.customer_location})
        move_cust_c = self.MoveObj.create({
            'name': self.productC.name,
            'product_id': self.productC.id,
            'product_uom_qty': 3,
            'product_uom': self.productC.uom_id.id,
            'picking_id': picking_out.id,
            'location_id': self.stock_location,
            'location_dest_id': self.customer_location})
        move_cust_d = self.MoveObj.create({
            'name': self.productD.name,
            'product_id': self.productD.id,
            'product_uom_qty': 10,
            'product_uom': self.productD.uom_id.id,
            'picking_id': picking_out.id,
            'location_id': self.stock_location,
            'location_dest_id': self.customer_location})
        # Confirm outgoing shipment.
        picking_out.action_confirm()
        for move in picking_out.move_lines:
            self.assertEqual(move.state, 'confirmed', 'Wrong state of move line.')
        # Product assign to outgoing shipments
        picking_out.action_assign()
        self.assertEqual(move_cust_a.state, 'partially_available', 'Wrong state of move line.')
        self.assertEqual(move_cust_b.state, 'assigned', 'Wrong state of move line.')
        self.assertEqual(move_cust_c.state, 'assigned', 'Wrong state of move line.')
        self.assertEqual(move_cust_d.state, 'partially_available', 'Wrong state of move line.')
        # Check availability for product A
        aval_a_qty = self.MoveObj.search([('product_id', '=', self.productA.id), ('picking_id', '=', picking_out.id)], limit=1).reserved_availability
        self.assertEqual(aval_a_qty, 4.0, 'Wrong move quantity availability of product A (%s found instead of 4)' % (aval_a_qty))
        # Check availability for product B
        aval_b_qty = self.MoveObj.search([('product_id', '=', self.productB.id), ('picking_id', '=', picking_out.id)], limit=1).reserved_availability
        self.assertEqual(aval_b_qty, 5.0, 'Wrong move quantity availability of product B (%s found instead of 5)' % (aval_b_qty))
        # Check availability for product C
        aval_c_qty = self.MoveObj.search([('product_id', '=', self.productC.id), ('picking_id', '=', picking_out.id)], limit=1).reserved_availability
        self.assertEqual(aval_c_qty, 3.0, 'Wrong move quantity availability of product C (%s found instead of 3)' % (aval_c_qty))
        # Check availability for product D
        aval_d_qty = self.MoveObj.search([('product_id', '=', self.productD.id), ('picking_id', '=', picking_out.id)], limit=1).reserved_availability
        self.assertEqual(aval_d_qty, 7.0, 'Wrong move quantity availability of product D (%s found instead of 7)' % (aval_d_qty))

        # ----------------------------------------------------------------------
        # Replace pack operation of outgoing shipment.
        # ----------------------------------------------------------------------

        move_cust_a.move_line_ids.qty_done = 2.0
        move_cust_b.move_line_ids.qty_done = 3.0
        self.StockPackObj.create({
            'product_id': self.productB.id,
            'qty_done': 2,
            'product_uom_id': self.productB.uom_id.id,
            'location_id': self.stock_location,
            'location_dest_id': self.customer_location,
            'move_id': move_cust_b.id})
        # TODO care if product_qty and lot_id are set at the same times the system do 2 unreserve.
        move_cust_c.move_line_ids[0].write({
            'qty_done': 2.0,
            'lot_id': lot2_productC.id,
        })
        self.StockPackObj.create({
            'product_id': self.productC.id,
            'qty_done': 3.0,
            'product_uom_id': self.productC.uom_id.id,
            'location_id': self.stock_location,
            'location_dest_id': self.customer_location,
            'move_id': move_cust_c.id})
        move_cust_d.move_line_ids.qty_done = 6.0

        # Transfer picking.
        picking_out.action_done()

        # ----------------------------------------------------------------------
        # Check state, quantity and total moves of outgoing shipment.
        # ----------------------------------------------------------------------

        # check outgoing shipment status.
        self.assertEqual(picking_out.state, 'done', 'Wrong state of outgoing shipment.')
        # check outgoing shipment total moves and and its state.
        self.assertEqual(len(picking_out.move_lines), 4, 'Wrong number of move lines')
        for move in picking_out.move_lines:
            self.assertEqual(move.state, 'done', 'Wrong state of move line.')
        back_order_out = self.PickingObj.search([('backorder_id', '=', picking_out.id)])

        # ------------------
        # Check back order.
        # -----------------

        self.assertEqual(len(back_order_out), 1, 'Back order should be created.')
        # Check total move lines of back order.
        self.assertEqual(len(back_order_out.move_lines), 2, 'Wrong number of move lines')
        # Check back order should be created with 8 quantity of product A.
        product_a_qty = self.MoveObj.search([('product_id', '=', self.productA.id), ('picking_id', '=', back_order_out.id)], limit=1).product_uom_qty
        self.assertEqual(product_a_qty, 8.0, 'Wrong move quantity of product A (%s found instead of 8)' % (product_a_qty))
        # Check back order should be created with 4 quantity of product D.
        product_d_qty = self.MoveObj.search([('product_id', '=', self.productD.id), ('picking_id', '=', back_order_out.id)], limit=1).product_uom_qty
        self.assertEqual(product_d_qty, 4.0, 'Wrong move quantity of product D (%s found instead of 4)' % (product_d_qty))

        # -----------------------------------------------------------------------
        # Check stock location quant quantity and quantity available
        # of product A, B, C, D
        # -----------------------------------------------------------------------

        # Check quants and available quantity for product A
        quants = self.StockQuantObj.search([('product_id', '=', self.productA.id), ('location_id', '=', self.stock_location)])
        total_qty = [quant.quantity for quant in quants]

        self.assertEqual(sum(total_qty), 2.0, 'Expecting 2.0 Unit , got %.4f Unit on location stock!' % (sum(total_qty)))
        self.assertEqual(self.productA.qty_available, 2.0, 'Wrong quantity available (%s found instead of 2.0)' % (self.productA.qty_available))
        # Check quants and available quantity for product B
        quants = self.StockQuantObj.search([('product_id', '=', self.productB.id), ('location_id', '=', self.stock_location), ('quantity', '!=', 0)])
        self.assertFalse(quants, 'No quant should found as outgoing shipment took everything out of stock.')
        self.assertEqual(self.productB.qty_available, 0.0, 'Product B should have zero quantity available.')
        # Check quants and available quantity for product C
        quants = self.StockQuantObj.search([('product_id', '=', self.productC.id), ('location_id', '=', self.stock_location), ('quantity', '!=', 0)])
        total_qty = [quant.quantity for quant in quants]
        self.assertEqual(sum(total_qty), 2.0, 'Expecting 2.0 Unit, got %.4f Unit on location stock!' % (sum(total_qty)))
        self.assertEqual(self.productC.qty_available, 2.0, 'Wrong quantity available (%s found instead of 2.0)' % (self.productC.qty_available))
        # Check quants and available quantity for product D
        quant = self.StockQuantObj.search([('product_id', '=', self.productD.id), ('location_id', '=', self.stock_location), ('quantity', '!=', 0)], limit=1)
        self.assertEqual(quant.quantity, 1.0, 'Expecting 1.0 Unit , got %.4f Unit on location stock!' % (quant.quantity))
        self.assertEqual(self.productD.qty_available, 1.0, 'Wrong quantity available (%s found instead of 1.0)' % (self.productD.qty_available))

        # -----------------------------------------------------------------------
        # Back Order of Incoming shipment
        # -----------------------------------------------------------------------

        lot3_productC = LotObj.create({'name': 'Lot 3', 'product_id': self.productC.id})
        lot4_productC = LotObj.create({'name': 'Lot 4', 'product_id': self.productC.id})
        lot5_productC = LotObj.create({'name': 'Lot 5', 'product_id': self.productC.id})
        lot6_productC = LotObj.create({'name': 'Lot 6', 'product_id': self.productC.id})
        lot1_productD = LotObj.create({'name': 'Lot 1', 'product_id': self.productD.id})
        LotObj.create({'name': 'Lot 2', 'product_id': self.productD.id})

        # Confirm back order of incoming shipment.
        back_order_in.action_confirm()
        self.assertEqual(back_order_in.state, 'assigned', 'Wrong state of incoming shipment back order: %s instead of %s' % (back_order_in.state, 'assigned'))
        for move in back_order_in.move_lines:
            self.assertEqual(move.state, 'assigned', 'Wrong state of move line.')

        # ----------------------------------------------------------------------
        # Replace pack operation (Back order of Incoming shipment)
        # ----------------------------------------------------------------------

        packD = self.StockPackObj.search([('product_id', '=', self.productD.id), ('picking_id', '=', back_order_in.id)], order='product_qty')
        self.assertEqual(len(packD), 1, 'Wrong number of pack operation.')
        packD[0].write({
            'qty_done': 8,
            'lot_id': lot1_productD.id,
        })
        packCs = self.StockPackObj.search([('product_id', '=', self.productC.id), ('picking_id', '=', back_order_in.id)], limit=1)
        packCs.write({
            'qty_done': 1,
            'lot_id': lot3_productC.id,
        })
        self.StockPackObj.create({
            'product_id': self.productC.id,
            'qty_done': 1,
            'product_uom_id': self.productC.uom_id.id,
            'location_id': self.supplier_location,
            'location_dest_id': self.stock_location,
            'picking_id': back_order_in.id,
            'lot_id': lot4_productC.id,
        })
        self.StockPackObj.create({
            'product_id': self.productC.id,
            'qty_done': 2,
            'product_uom_id': self.productC.uom_id.id,
            'location_id': self.supplier_location,
            'location_dest_id': self.stock_location,
            'picking_id': back_order_in.id,
            'lot_id': lot5_productC.id,
        })
        self.StockPackObj.create({
            'product_id': self.productC.id,
            'qty_done': 2,
            'product_uom_id': self.productC.uom_id.id,
            'location_id': self.supplier_location,
            'location_dest_id': self.stock_location,
            'picking_id': back_order_in.id,
            'lot_id': lot6_productC.id,
        })
        self.StockPackObj.create({
            'product_id': self.productA.id,
            'qty_done': 10,
            'product_uom_id': self.productA.uom_id.id,
            'location_id': self.supplier_location,
            'location_dest_id': self.stock_location,
            'picking_id': back_order_in.id
        })
        back_order_in.action_done()

        # ----------------------------------------------------------------------
        # Check state, quantity and total moves (Back order of Incoming shipment).
        # ----------------------------------------------------------------------

        # Check total no of move lines.
        self.assertEqual(len(back_order_in.move_lines), 3, 'Wrong number of move lines')
        # Check incoming shipment state must be 'Done'.
        self.assertEqual(back_order_in.state, 'done', 'Wrong state of picking.')
        # Check incoming shipment move lines state must be 'Done'.
        for move in back_order_in.move_lines:
            self.assertEqual(move.state, 'done', 'Wrong state of move lines.')
        # Check product A done quantity must be 10
        movesA = self.MoveObj.search([('product_id', '=', self.productA.id), ('picking_id', '=', back_order_in.id)])
        self.assertEqual(movesA.product_uom_qty, 10, "Wrong move quantity of product A (%s found instead of 10)" % (movesA.product_uom_qty))
        # Check product C done quantity must be 3.0, 1.0, 2.0
        movesC = self.MoveObj.search([('product_id', '=', self.productC.id), ('picking_id', '=', back_order_in.id)])
        self.assertEqual(movesC.product_uom_qty, 6.0, 'Wrong quantity of moves product C.')
        # Check product D done quantity must be 5.0 and 3.0
        movesD = self.MoveObj.search([('product_id', '=', self.productD.id), ('picking_id', '=', back_order_in.id)])
        d_done_qty = [move.product_uom_qty for move in movesD]
        self.assertEqual(set(d_done_qty), set([8.0]), 'Wrong quantity of moves product D.')
        # Check no back order is created.
        self.assertFalse(self.PickingObj.search([('backorder_id', '=', back_order_in.id)]), "Should not create any back order.")

        # -----------------------------------------------------------------------
        # Check stock location quant quantity and quantity available
        # of product A, B, C, D
        # -----------------------------------------------------------------------

        # Check quants and available quantity for product A.
        quants = self.StockQuantObj.search([('product_id', '=', self.productA.id), ('location_id', '=', self.stock_location), ('quantity', '!=', 0)])
        total_qty = [quant.quantity for quant in quants]
        self.assertEqual(sum(total_qty), 12.0, 'Wrong total stock location quantity (%s found instead of 12)' % (sum(total_qty)))
        self.assertEqual(self.productA.qty_available, 12.0, 'Wrong quantity available (%s found instead of 12)' % (self.productA.qty_available))
        # Check quants and available quantity for product B.
        quants = self.StockQuantObj.search([('product_id', '=', self.productB.id), ('location_id', '=', self.stock_location), ('quantity', '!=', 0)])
        self.assertFalse(quants, 'No quant should found as outgoing shipment took everything out of stock')
        self.assertEqual(self.productB.qty_available, 0.0, 'Total quantity in stock should be 0 as the backorder took everything out of stock')
        # Check quants and available quantity for product C.
        quants = self.StockQuantObj.search([('product_id', '=', self.productC.id), ('location_id', '=', self.stock_location), ('quantity', '!=', 0)])
        total_qty = [quant.quantity for quant in quants]
        self.assertEqual(sum(total_qty), 8.0, 'Wrong total stock location quantity (%s found instead of 8)' % (sum(total_qty)))
        self.assertEqual(self.productC.qty_available, 8.0, 'Wrong quantity available (%s found instead of 8)' % (self.productC.qty_available))
        # Check quants and available quantity for product D.
        quants = self.StockQuantObj.search([('product_id', '=', self.productD.id), ('location_id', '=', self.stock_location), ('quantity', '!=', 0)])
        total_qty = [quant.quantity for quant in quants]
        self.assertEqual(sum(total_qty), 9.0, 'Wrong total stock location quantity (%s found instead of 9)' % (sum(total_qty)))
        self.assertEqual(self.productD.qty_available, 9.0, 'Wrong quantity available (%s found instead of 9)' % (self.productD.qty_available))

        # -----------------------------------------------------------------------
        # Back order of Outgoing shipment
        # ----------------------------------------------------------------------

        back_order_out.action_done()

        # Check stock location quants and available quantity for product A.
        quants = self.StockQuantObj.search([('product_id', '=', self.productA.id), ('location_id', '=', self.stock_location), ('quantity', '!=', 0)])
        total_qty = [quant.quantity for quant in quants]
        self.assertGreaterEqual(float_round(sum(total_qty), precision_rounding=0.0001), 1, 'Total stock location quantity for product A should not be nagative.')

    def test_10_pickings_transfer_with_different_uom(self):
        """ Picking transfer with diffrent unit of meassure. """

        # ----------------------------------------------------------------------
        # Create incoming shipment of products DozA, SDozA, SDozARound, kgB, gB
        # ----------------------------------------------------------------------
        #   DozA ( 10 Dozen ) , SDozA ( 10.5 SuperDozen )
        #   SDozARound ( 10.5 10.5 SuperDozenRound ) , kgB ( 0.020 kg )
        #   gB ( 525.3 g )
        # ----------------------------------------------------------------------

        picking_in_A = self.PickingObj.create({
            'partner_id': self.partner_delta_id,
            'picking_type_id': self.picking_type_in,
            'location_id': self.supplier_location,
            'location_dest_id': self.stock_location})
        self.MoveObj.create({
            'name': self.DozA.name,
            'product_id': self.DozA.id,
            'product_uom_qty': 10,
            'product_uom': self.DozA.uom_id.id,
            'picking_id': picking_in_A.id,
            'location_id': self.supplier_location,
            'location_dest_id': self.stock_location})
        self.MoveObj.create({
            'name': self.SDozA.name,
            'product_id': self.SDozA.id,
            'product_uom_qty': 10.5,
            'product_uom': self.SDozA.uom_id.id,
            'picking_id': picking_in_A.id,
            'location_id': self.supplier_location,
            'location_dest_id': self.stock_location})
        self.MoveObj.create({
            'name': self.SDozARound.name,
            'product_id': self.SDozARound.id,
            'product_uom_qty': 10.5,
            'product_uom': self.SDozARound.uom_id.id,
            'picking_id': picking_in_A.id,
            'location_id': self.supplier_location,
            'location_dest_id': self.stock_location})
        self.MoveObj.create({
            'name': self.kgB.name,
            'product_id': self.kgB.id,
            'product_uom_qty': 0.020,
            'product_uom': self.kgB.uom_id.id,
            'picking_id': picking_in_A.id,
            'location_id': self.supplier_location,
            'location_dest_id': self.stock_location})
        self.MoveObj.create({
            'name': self.gB.name,
            'product_id': self.gB.id,
            'product_uom_qty': 525.3,
            'product_uom': self.gB.uom_id.id,
            'picking_id': picking_in_A.id,
            'location_id': self.supplier_location,
            'location_dest_id': self.stock_location})

        # Check incoming shipment move lines state.
        for move in picking_in_A.move_lines:
            self.assertEqual(move.state, 'draft', 'Move state must be draft.')
        # Confirm incoming shipment.
        picking_in_A.action_confirm()
        # Check incoming shipment move lines state.
        for move in picking_in_A.move_lines:
            self.assertEqual(move.state, 'assigned', 'Move state must be draft.')

        # ----------------------------------------------------
        # Check pack operation quantity of incoming shipments.
        # ----------------------------------------------------

        PackSdozAround = self.StockPackObj.search([('product_id', '=', self.SDozARound.id), ('picking_id', '=', picking_in_A.id)], limit=1)
        self.assertEqual(PackSdozAround.product_qty, 11, 'Wrong quantity in pack operation (%s found instead of 11)' % (PackSdozAround.product_qty))
        res_dict = picking_in_A.button_validate()
        wizard = self.env[(res_dict.get('res_model'))].browse(res_dict.get('res_id'))
        wizard.process()

        # -----------------------------------------------------------------------
        # Check stock location quant quantity and quantity available
        # -----------------------------------------------------------------------

        # Check quants and available quantity for product DozA
        quants = self.StockQuantObj.search([('product_id', '=', self.DozA.id), ('location_id', '=', self.stock_location)])
        total_qty = [quant.quantity for quant in quants]
        self.assertEqual(sum(total_qty), 10, 'Expecting 10 Dozen , got %.4f Dozen on location stock!' % (sum(total_qty)))
        self.assertEqual(self.DozA.qty_available, 10, 'Wrong quantity available (%s found instead of 10)' % (self.DozA.qty_available))
        # Check quants and available quantity for product SDozA
        quants = self.StockQuantObj.search([('product_id', '=', self.SDozA.id), ('location_id', '=', self.stock_location)])
        total_qty = [quant.quantity for quant in quants]
        self.assertEqual(sum(total_qty), 10.5, 'Expecting 10.5 SDozen , got %.4f SDozen on location stock!' % (sum(total_qty)))
        self.assertEqual(self.SDozA.qty_available, 10.5, 'Wrong quantity available (%s found instead of 10.5)' % (self.SDozA.qty_available))
        # Check quants and available quantity for product SDozARound
        quants = self.StockQuantObj.search([('product_id', '=', self.SDozARound.id), ('location_id', '=', self.stock_location)])
        total_qty = [quant.quantity for quant in quants]
        self.assertEqual(sum(total_qty), 11, 'Expecting 11 SDozenRound , got %.4f SDozenRound on location stock!' % (sum(total_qty)))
        self.assertEqual(self.SDozARound.qty_available, 11, 'Wrong quantity available (%s found instead of 11)' % (self.SDozARound.qty_available))
        # Check quants and available quantity for product gB
        quants = self.StockQuantObj.search([('product_id', '=', self.gB.id), ('location_id', '=', self.stock_location)])
        total_qty = [quant.quantity for quant in quants]
        self.assertEqual(sum(total_qty), 525.3, 'Expecting 525.3 gram , got %.4f gram on location stock!' % (sum(total_qty)))
        self.assertEqual(self.gB.qty_available, 525.3, 'Wrong quantity available (%s found instead of 525.3' % (self.gB.qty_available))
        # Check quants and available quantity for product kgB
        quants = self.StockQuantObj.search([('product_id', '=', self.kgB.id), ('location_id', '=', self.stock_location)])
        total_qty = [quant.quantity for quant in quants]
        self.assertEqual(sum(total_qty), 0.020, 'Expecting 0.020 kg , got %.4f kg on location stock!' % (sum(total_qty)))
        self.assertEqual(self.kgB.qty_available, 0.020, 'Wrong quantity available (%s found instead of 0.020)' % (self.kgB.qty_available))

        # ----------------------------------------------------------------------
        # Create Incoming Shipment B
        # ----------------------------------------------------------------------

        picking_in_B = self.PickingObj.create({
            'partner_id': self.partner_delta_id,
            'picking_type_id': self.picking_type_in,
            'location_id': self.supplier_location,
            'location_dest_id': self.stock_location})
        move_in_a = self.MoveObj.create({
            'name': self.DozA.name,
            'product_id': self.DozA.id,
            'product_uom_qty': 120,
            'product_uom': self.uom_unit.id,
            'picking_id': picking_in_B.id,
            'location_id': self.supplier_location,
            'location_dest_id': self.stock_location})
        self.MoveObj.create({
            'name': self.SDozA.name,
            'product_id': self.SDozA.id,
            'product_uom_qty': 1512,
            'product_uom': self.uom_unit.id,
            'picking_id': picking_in_B.id,
            'location_id': self.supplier_location,
            'location_dest_id': self.stock_location})
        self.MoveObj.create({
            'name': self.SDozARound.name,
            'product_id': self.SDozARound.id,
            'product_uom_qty': 1584,
            'product_uom': self.uom_unit.id,
            'picking_id': picking_in_B.id,
            'location_id': self.supplier_location,
            'location_dest_id': self.stock_location})
        self.MoveObj.create({
            'name': self.kgB.name,
            'product_id': self.kgB.id,
            'product_uom_qty': 20.0,
            'product_uom': self.uom_gm.id,
            'picking_id': picking_in_B.id,
            'location_id': self.supplier_location,
            'location_dest_id': self.stock_location})
        self.MoveObj.create({
            'name': self.gB.name,
            'product_id': self.gB.id,
            'product_uom_qty': 0.525,
            'product_uom': self.uom_kg.id,
            'picking_id': picking_in_B.id,
            'location_id': self.supplier_location,
            'location_dest_id': self.stock_location})

        # Check incoming shipment move lines state.
        for move in picking_in_B.move_lines:
            self.assertEqual(move.state, 'draft', 'Wrong state of move line.')
        # Confirm incoming shipment.
        picking_in_B.action_confirm()
        # Check incoming shipment move lines state.
        for move in picking_in_B.move_lines:
            self.assertEqual(move.state, 'assigned', 'Wrong state of move line.')

        # ----------------------------------------------------------------------
        # Check product quantity and unit of measure of pack operaation.
        # ----------------------------------------------------------------------

        # Check pack operation quantity and unit of measure for product DozA.
        PackdozA = self.StockPackObj.search([('product_id', '=', self.DozA.id), ('picking_id', '=', picking_in_B.id)], limit=1)
        self.assertEqual(PackdozA.product_uom_qty, 120, 'Wrong quantity in pack operation (%s found instead of 120)' % (PackdozA.product_uom_qty))
        self.assertEqual(PackdozA.product_qty, 10, 'Wrong real quantity in pack operation (%s found instead of 10)' % (PackdozA.product_qty))
        self.assertEqual(PackdozA.product_uom_id.id, self.uom_unit.id, 'Wrong uom in pack operation for product DozA.')
        # Check pack operation quantity and unit of measure for product SDozA.
        PackSdozA = self.StockPackObj.search([('product_id', '=', self.SDozA.id), ('picking_id', '=', picking_in_B.id)], limit=1)
        self.assertEqual(PackSdozA.product_uom_qty, 1512, 'Wrong quantity in pack operation (%s found instead of 1512)' % (PackSdozA.product_uom_qty))
        self.assertEqual(PackSdozA.product_uom_id.id, self.uom_unit.id, 'Wrong uom in pack operation for product SDozA.')
        # Check pack operation quantity and unit of measure for product SDozARound.
        PackSdozAround = self.StockPackObj.search([('product_id', '=', self.SDozARound.id), ('picking_id', '=', picking_in_B.id)], limit=1)
        self.assertEqual(PackSdozAround.product_uom_qty, 1584, 'Wrong quantity in pack operation (%s found instead of 1584)' % (PackSdozAround.product_uom_qty))
        self.assertEqual(PackSdozAround.product_uom_id.id, self.uom_unit.id, 'Wrong uom in pack operation for product SDozARound.')
        # Check pack operation quantity and unit of measure for product gB.
        packgB = self.StockPackObj.search([('product_id', '=', self.gB.id), ('picking_id', '=', picking_in_B.id)], limit=1)
        self.assertEqual(packgB.product_uom_qty, 0.525, 'Wrong quantity in pack operation (%s found instead of 0.525)' % (packgB.product_uom_qty))
        self.assertEqual(packgB.product_qty, 525, 'Wrong real quantity in pack operation (%s found instead of 525)' % (packgB.product_qty))
        self.assertEqual(packgB.product_uom_id.id, packgB.move_id.product_uom.id, 'Wrong uom in pack operation for product kgB.')
        # Check pack operation quantity and unit of measure for product kgB.
        packkgB = self.StockPackObj.search([('product_id', '=', self.kgB.id), ('picking_id', '=', picking_in_B.id)], limit=1)
        self.assertEqual(packkgB.product_uom_qty, 20.0, 'Wrong quantity in pack operation (%s found instead of 20)' % (packkgB.product_uom_qty))
        self.assertEqual(packkgB.product_uom_id.id, self.uom_gm.id, 'Wrong uom in pack operation for product kgB')

        # ----------------------------------------------------------------------
        # Replace pack operation of incoming shipment.
        # ----------------------------------------------------------------------

        self.StockPackObj.search([('product_id', '=', self.kgB.id), ('picking_id', '=', picking_in_B.id)]).write({
            'product_uom_qty': 0.020, 'product_uom_id': self.uom_kg.id})
        self.StockPackObj.search([('product_id', '=', self.gB.id), ('picking_id', '=', picking_in_B.id)]).write({
            'product_uom_qty': 526, 'product_uom_id': self.uom_gm.id})
        self.StockPackObj.search([('product_id', '=', self.DozA.id), ('picking_id', '=', picking_in_B.id)]).write({
            'product_uom_qty': 4, 'product_uom_id': self.uom_dozen.id})
        self.StockPackObj.create({
            'product_id': self.DozA.id,
            'product_uom_qty': 48,
            'product_uom_id': self.uom_unit.id,
            'location_id': self.supplier_location,
            'location_dest_id': self.stock_location,
            'move_id': move_in_a.id
        })

        # -----------------
        # Transfer product.
        # -----------------

        res_dict = picking_in_B.button_validate()
        wizard = self.env[(res_dict.get('res_model'))].browse(res_dict.get('res_id'))
        res_dict_for_back_order = wizard.process()
        backorder_wizard = self.env[(res_dict_for_back_order.get('res_model'))].browse(res_dict_for_back_order.get('res_id'))
        backorder_wizard.process()

        # -----------------------------------------------------------------------
        # Check incoming shipment
        # -----------------------------------------------------------------------
        # Check incoming shipment state.
        self.assertEqual(picking_in_B.state, 'done', 'Incoming shipment state should be done.')
        # Check incoming shipment move lines state.
        for move in picking_in_B.move_lines:
            self.assertEqual(move.state, 'done', 'Wrong state of move line.')
        # Check total done move lines for incoming shipment.
        self.assertEqual(len(picking_in_B.move_lines), 5, 'Wrong number of move lines')
        # Check product DozA done quantity.
        moves_DozA = self.MoveObj.search([('product_id', '=', self.DozA.id), ('picking_id', '=', picking_in_B.id)], limit=1)
        self.assertEqual(moves_DozA.product_uom_qty, 96, 'Wrong move quantity (%s found instead of 96)' % (moves_DozA.product_uom_qty))
        self.assertEqual(moves_DozA.product_uom.id, self.uom_unit.id, 'Wrong uom in move for product DozA.')
        # Check product SDozA done quantity.
        moves_SDozA = self.MoveObj.search([('product_id', '=', self.SDozA.id), ('picking_id', '=', picking_in_B.id)], limit=1)
        self.assertEqual(moves_SDozA.product_uom_qty, 1512, 'Wrong move quantity (%s found instead of 1512)' % (moves_SDozA.product_uom_qty))
        self.assertEqual(moves_SDozA.product_uom.id, self.uom_unit.id, 'Wrong uom in move for product SDozA.')
        # Check product SDozARound done quantity.
        moves_SDozARound = self.MoveObj.search([('product_id', '=', self.SDozARound.id), ('picking_id', '=', picking_in_B.id)], limit=1)
        self.assertEqual(moves_SDozARound.product_uom_qty, 1584, 'Wrong move quantity (%s found instead of 1584)' % (moves_SDozARound.product_uom_qty))
        self.assertEqual(moves_SDozARound.product_uom.id, self.uom_unit.id, 'Wrong uom in move for product SDozARound.')
        # Check product kgB done quantity.
        moves_kgB = self.MoveObj.search([('product_id', '=', self.kgB.id), ('picking_id', '=', picking_in_B.id)], limit=1)
        self.assertEqual(moves_kgB.product_uom_qty, 20, 'Wrong quantity in move (%s found instead of 20)' % (moves_kgB.product_uom_qty))
        self.assertEqual(moves_kgB.product_uom.id, self.uom_gm.id, 'Wrong uom in move for product kgB.')
        # Check two moves created for product gB with quantity (0.525 kg and 0.3 g)
        moves_gB_kg = self.MoveObj.search([('product_id', '=', self.gB.id), ('picking_id', '=', picking_in_B.id), ('product_uom', '=', self.uom_kg.id)], limit=1)
        self.assertEqual(moves_gB_kg.product_uom_qty, 0.526, 'Wrong move quantity (%s found instead of 0.526)' % (moves_gB_kg.product_uom_qty))
        self.assertEqual(moves_gB_kg.product_uom.id, self.uom_kg.id, 'Wrong uom in move for product gB.')

        # TODO Test extra move once the uom is editable in the move_lines

        # ----------------------------------------------------------------------
        # Check Back order of Incoming shipment.
        # ----------------------------------------------------------------------

        # Check back order created or not.
        bo_in_B = self.PickingObj.search([('backorder_id', '=', picking_in_B.id)])
        self.assertEqual(len(bo_in_B), 1, 'Back order should be created.')
        # Check total move lines of back order.
        self.assertEqual(len(bo_in_B.move_lines), 1, 'Wrong number of move lines')
        # Check back order created with correct quantity and uom or not.
        moves_DozA = self.MoveObj.search([('product_id', '=', self.DozA.id), ('picking_id', '=', bo_in_B.id)], limit=1)
        self.assertEqual(moves_DozA.product_uom_qty, 24.0, 'Wrong move quantity (%s found instead of 0.525)' % (moves_DozA.product_uom_qty))
        self.assertEqual(moves_DozA.product_uom.id, self.uom_unit.id, 'Wrong uom in move for product DozA.')

        # ----------------------------------------------------------------------
        # Check product stock location quantity and quantity available.
        # ----------------------------------------------------------------------

        # Check quants and available quantity for product DozA
        quants = self.StockQuantObj.search([('product_id', '=', self.DozA.id), ('location_id', '=', self.stock_location)])
        total_qty = [quant.quantity for quant in quants]
        self.assertEqual(sum(total_qty), 18, 'Expecting 18 Dozen , got %.4f Dozen on location stock!' % (sum(total_qty)))
        self.assertEqual(self.DozA.qty_available, 18, 'Wrong quantity available (%s found instead of 18)' % (self.DozA.qty_available))
        # Check quants and available quantity for product SDozA
        quants = self.StockQuantObj.search([('product_id', '=', self.SDozA.id), ('location_id', '=', self.stock_location)])
        total_qty = [quant.quantity for quant in quants]
        self.assertEqual(sum(total_qty), 21, 'Expecting 21 SDozen , got %.4f SDozen on location stock!' % (sum(total_qty)))
        self.assertEqual(self.SDozA.qty_available, 21, 'Wrong quantity available (%s found instead of 21)' % (self.SDozA.qty_available))
        # Check quants and available quantity for product SDozARound
        quants = self.StockQuantObj.search([('product_id', '=', self.SDozARound.id), ('location_id', '=', self.stock_location)])
        total_qty = [quant.quantity for quant in quants]
        self.assertEqual(sum(total_qty), 22, 'Expecting 22 SDozenRound , got %.4f SDozenRound on location stock!' % (sum(total_qty)))
        self.assertEqual(self.SDozARound.qty_available, 22, 'Wrong quantity available (%s found instead of 22)' % (self.SDozARound.qty_available))
        # Check quants and available quantity for product gB.
        quants = self.StockQuantObj.search([('product_id', '=', self.gB.id), ('location_id', '=', self.stock_location)])
        total_qty = [quant.quantity for quant in quants]
        self.assertEqual(round(sum(total_qty), 1), 1051.3, 'Expecting 1051 Gram , got %.4f Gram on location stock!' % (sum(total_qty)))
        self.assertEqual(round(self.gB.qty_available, 1), 1051.3, 'Wrong quantity available (%s found instead of 1051)' % (self.gB.qty_available))
        # Check quants and available quantity for product kgB.
        quants = self.StockQuantObj.search([('product_id', '=', self.kgB.id), ('location_id', '=', self.stock_location)])
        total_qty = [quant.quantity for quant in quants]
        self.assertEqual(sum(total_qty), 0.040, 'Expecting 0.040 kg , got %.4f kg on location stock!' % (sum(total_qty)))
        self.assertEqual(self.kgB.qty_available, 0.040, 'Wrong quantity available (%s found instead of 0.040)' % (self.kgB.qty_available))

        # ----------------------------------------------------------------------
        # Create outgoing shipment.
        # ----------------------------------------------------------------------

        before_out_quantity = self.kgB.qty_available
        picking_out = self.PickingObj.create({
            'partner_id': self.partner_agrolite_id,
            'picking_type_id': self.picking_type_out,
            'location_id': self.stock_location,
            'location_dest_id': self.customer_location})
        self.MoveObj.create({
            'name': self.kgB.name,
            'product_id': self.kgB.id,
            'product_uom_qty': 0.966,
            'product_uom': self.uom_gm.id,
            'picking_id': picking_out.id,
            'location_id': self.stock_location,
            'location_dest_id': self.customer_location})
        self.MoveObj.create({
            'name': self.kgB.name,
            'product_id': self.kgB.id,
            'product_uom_qty': 0.034,
            'product_uom': self.uom_gm.id,
            'picking_id': picking_out.id,
            'location_id': self.stock_location,
            'location_dest_id': self.customer_location})
        picking_out.action_confirm()
        picking_out.action_assign()
        res_dict = picking_out.button_validate()
        wizard = self.env[(res_dict.get('res_model'))].browse(res_dict.get('res_id'))
        wizard.process()

        # Check quantity difference after stock transfer.
        quantity_diff = before_out_quantity - self.kgB.qty_available
        self.assertEqual(float_round(quantity_diff, precision_rounding=0.0001), 0.001, 'Wrong quantity diffrence.')
        self.assertEqual(self.kgB.qty_available, 0.039, 'Wrong quantity available (%s found instead of 0.039)' % (self.kgB.qty_available))

        # ======================================================================
        # Outgoing shipments.
        # ======================================================================

        # Create Outgoing shipment with ...
        #   product DozA ( 54 Unit ) , SDozA ( 288 Unit )
        #   product SDozRound (  360 unit ) , product gB ( 0.503 kg )
        #   product kgB (  19 g )
        # ======================================================================

        picking_out = self.PickingObj.create({
            'partner_id': self.partner_agrolite_id,
            'picking_type_id': self.picking_type_out,
            'location_id': self.stock_location,
            'location_dest_id': self.customer_location})
        self.MoveObj.create({
            'name': self.DozA.name,
            'product_id': self.DozA.id,
            'product_uom_qty': 54,
            'product_uom': self.uom_unit.id,
            'picking_id': picking_out.id,
            'location_id': self.stock_location,
            'location_dest_id': self.customer_location})
        self.MoveObj.create({
            'name': self.SDozA.name,
            'product_id': self.SDozA.id,
            'product_uom_qty': 288,
            'product_uom': self.uom_unit.id,
            'picking_id': picking_out.id,
            'location_id': self.stock_location,
            'location_dest_id': self.customer_location})
        self.MoveObj.create({
            'name': self.SDozARound.name,
            'product_id': self.SDozARound.id,
            'product_uom_qty': 361,
            'product_uom': self.uom_unit.id,
            'picking_id': picking_out.id,
            'location_id': self.stock_location,
            'location_dest_id': self.customer_location})
        self.MoveObj.create({
            'name': self.gB.name,
            'product_id': self.gB.id,
            'product_uom_qty': 0.503,
            'product_uom': self.uom_kg.id,
            'picking_id': picking_out.id,
            'location_id': self.stock_location,
            'location_dest_id': self.customer_location})
        self.MoveObj.create({
            'name': self.kgB.name,
            'product_id': self.kgB.id,
            'product_uom_qty': 20,
            'product_uom': self.uom_gm.id,
            'picking_id': picking_out.id,
            'location_id': self.stock_location,
            'location_dest_id': self.customer_location})
        # Confirm outgoing shipment.
        picking_out.action_confirm()
        for move in picking_out.move_lines:
            self.assertEqual(move.state, 'confirmed', 'Wrong state of move line.')
        # Assing product to outgoing shipments
        picking_out.action_assign()
        for move in picking_out.move_lines:
            self.assertEqual(move.state, 'assigned', 'Wrong state of move line.')
        # Check product A available quantity
        DozA_qty = self.MoveObj.search([('product_id', '=', self.DozA.id), ('picking_id', '=', picking_out.id)], limit=1).product_qty
        self.assertEqual(DozA_qty, 4.5, 'Wrong move quantity availability (%s found instead of 4.5)' % (DozA_qty))
        # Check product B available quantity
        SDozA_qty = self.MoveObj.search([('product_id', '=', self.SDozA.id), ('picking_id', '=', picking_out.id)], limit=1).product_qty
        self.assertEqual(SDozA_qty, 2, 'Wrong move quantity availability (%s found instead of 2)' % (SDozA_qty))
        # Check product C available quantity
        SDozARound_qty = self.MoveObj.search([('product_id', '=', self.SDozARound.id), ('picking_id', '=', picking_out.id)], limit=1).product_qty
        self.assertEqual(SDozARound_qty, 3, 'Wrong move quantity availability (%s found instead of 3)' % (SDozARound_qty))
        # Check product D available quantity
        gB_qty = self.MoveObj.search([('product_id', '=', self.gB.id), ('picking_id', '=', picking_out.id)], limit=1).product_qty
        self.assertEqual(gB_qty, 503, 'Wrong move quantity availability (%s found instead of 503)' % (gB_qty))
        # Check product D available quantity
        kgB_qty = self.MoveObj.search([('product_id', '=', self.kgB.id), ('picking_id', '=', picking_out.id)], limit=1).product_qty
        self.assertEqual(kgB_qty, 0.020, 'Wrong move quantity availability (%s found instead of 0.020)' % (kgB_qty))

        res_dict = picking_out.button_validate()
        wizard = self.env[(res_dict.get('res_model'))].browse(res_dict.get('res_id'))
        wizard.process()

        # ----------------------------------------------------------------------
        # Check product stock location quantity and quantity available.
        # ----------------------------------------------------------------------

        # Check quants and available quantity for product DozA
        quants = self.StockQuantObj.search([('product_id', '=', self.DozA.id), ('location_id', '=', self.stock_location)])
        total_qty = [quant.quantity for quant in quants]
        self.assertEqual(sum(total_qty), 13.5, 'Expecting 13.5 Dozen , got %.4f Dozen on location stock!' % (sum(total_qty)))
        self.assertEqual(self.DozA.qty_available, 13.5, 'Wrong quantity available (%s found instead of 13.5)' % (self.DozA.qty_available))
        # Check quants and available quantity for product SDozA
        quants = self.StockQuantObj.search([('product_id', '=', self.SDozA.id), ('location_id', '=', self.stock_location)])
        total_qty = [quant.quantity for quant in quants]
        self.assertEqual(sum(total_qty), 19, 'Expecting 19 SDozen , got %.4f SDozen on location stock!' % (sum(total_qty)))
        self.assertEqual(self.SDozA.qty_available, 19, 'Wrong quantity available (%s found instead of 19)' % (self.SDozA.qty_available))
        # Check quants and available quantity for product SDozARound
        quants = self.StockQuantObj.search([('product_id', '=', self.SDozARound.id), ('location_id', '=', self.stock_location)])
        total_qty = [quant.quantity for quant in quants]
        self.assertEqual(sum(total_qty), 19, 'Expecting 19 SDozRound , got %.4f SDozRound on location stock!' % (sum(total_qty)))
        self.assertEqual(self.SDozARound.qty_available, 19, 'Wrong quantity available (%s found instead of 19)' % (self.SDozARound.qty_available))
        # Check quants and available quantity for product gB.
        quants = self.StockQuantObj.search([('product_id', '=', self.gB.id), ('location_id', '=', self.stock_location)])
        total_qty = [quant.quantity for quant in quants]
        self.assertEqual(round(sum(total_qty), 1), 548.3, 'Expecting 547.6 g , got %.4f g on location stock!' % (sum(total_qty)))
        self.assertEqual(round(self.gB.qty_available, 1), 548.3, 'Wrong quantity available (%s found instead of 547.6)' % (self.gB.qty_available))
        # Check quants and available quantity for product kgB.
        quants = self.StockQuantObj.search([('product_id', '=', self.kgB.id), ('location_id', '=', self.stock_location)])
        total_qty = [quant.quantity for quant in quants]
        self.assertEqual(sum(total_qty), 0.019, 'Expecting 0.019 kg , got %.4f kg on location stock!' % (sum(total_qty)))
        self.assertEqual(self.kgB.qty_available, 0.019, 'Wrong quantity available (%s found instead of 0.019)' % (self.kgB.qty_available))

        # ----------------------------------------------------------------------
        # Receipt back order of incoming shipment.
        # ----------------------------------------------------------------------

        res_dict = bo_in_B.button_validate()
        wizard = self.env[(res_dict.get('res_model'))].browse(res_dict.get('res_id'))
        wizard.process()
        # Check quants and available quantity for product kgB.
        quants = self.StockQuantObj.search([('product_id', '=', self.DozA.id), ('location_id', '=', self.stock_location)])
        total_qty = [quant.quantity for quant in quants]
        self.assertEqual(sum(total_qty), 15.5, 'Expecting 15.5 Dozen , got %.4f Dozen on location stock!' % (sum(total_qty)))
        self.assertEqual(self.DozA.qty_available, 15.5, 'Wrong quantity available (%s found instead of 15.5)' % (self.DozA.qty_available))

        # -----------------------------------------
        # Create product in kg and receive in ton.
        # -----------------------------------------

        productKG = self.ProductObj.create({'name': 'Product KG', 'uom_id': self.uom_kg.id, 'uom_po_id': self.uom_kg.id, 'type': 'product'})
        picking_in = self.PickingObj.create({
            'partner_id': self.partner_delta_id,
            'picking_type_id': self.picking_type_in,
            'location_id': self.supplier_location,
            'location_dest_id': self.stock_location})
        self.MoveObj.create({
            'name': productKG.name,
            'product_id': productKG.id,
            'product_uom_qty': 1.0,
            'product_uom': self.uom_tone.id,
            'picking_id': picking_in.id,
            'location_id': self.supplier_location,
            'location_dest_id': self.stock_location})
        # Check incoming shipment state.
        self.assertEqual(picking_in.state, 'draft', 'Incoming shipment state should be draft.')
        # Check incoming shipment move lines state.
        for move in picking_in.move_lines:
            self.assertEqual(move.state, 'draft', 'Wrong state of move line.')
        # Confirm incoming shipment.
        picking_in.action_confirm()
        # Check incoming shipment move lines state.
        for move in picking_in.move_lines:
            self.assertEqual(move.state, 'assigned', 'Wrong state of move line.')
        # Check pack operation quantity.
        packKG = self.StockPackObj.search([('product_id', '=', productKG.id), ('picking_id', '=', picking_in.id)], limit=1)
        self.assertEqual(packKG.product_qty, 1000, 'Wrong product real quantity in pack operation (%s found instead of 1000)' % (packKG.product_qty))
        self.assertEqual(packKG.product_uom_qty, 1, 'Wrong product quantity in pack operation (%s found instead of 1)' % (packKG.product_uom_qty))
        self.assertEqual(packKG.product_uom_id.id, self.uom_tone.id, 'Wrong product uom in pack operation.')
        # Transfer Incoming shipment.
        res_dict = picking_in.button_validate()
        wizard = self.env[(res_dict.get('res_model'))].browse(res_dict.get('res_id'))
        wizard.process()

        # -----------------------------------------------------------------------
        # Check incoming shipment after transfer.
        # -----------------------------------------------------------------------

        # Check incoming shipment state.
        self.assertEqual(picking_in.state, 'done', 'Incoming shipment state: %s instead of %s' % (picking_in.state, 'done'))
        # Check incoming shipment move lines state.
        for move in picking_in.move_lines:
            self.assertEqual(move.state, 'done', 'Wrong state of move lines.')
        # Check total done move lines for incoming shipment.
        self.assertEqual(len(picking_in.move_lines), 1, 'Wrong number of move lines')
        # Check product DozA done quantity.
        move = self.MoveObj.search([('product_id', '=', productKG.id), ('picking_id', '=', picking_in.id)], limit=1)
        self.assertEqual(move.product_uom_qty, 1, 'Wrong product quantity in done move.')
        self.assertEqual(move.product_uom.id, self.uom_tone.id, 'Wrong unit of measure in done move.')
        self.assertEqual(productKG.qty_available, 1000, 'Wrong quantity available of product (%s found instead of 1000)' % (productKG.qty_available))
        picking_out = self.PickingObj.create({
            'partner_id': self.partner_agrolite_id,
            'picking_type_id': self.picking_type_out,
            'location_id': self.stock_location,
            'location_dest_id': self.customer_location})
        self.MoveObj.create({
            'name': productKG.name,
            'product_id': productKG.id,
            'product_uom_qty': 2.5,
            'product_uom': self.uom_gm.id,
            'picking_id': picking_out.id,
            'location_id': self.stock_location,
            'location_dest_id': self.customer_location})
        picking_out.action_confirm()
        picking_out.action_assign()
        pack_opt = self.StockPackObj.search([('product_id', '=', productKG.id), ('picking_id', '=', picking_out.id)], limit=1)
        pack_opt.write({'product_uom_qty': 0.5})
        res_dict = picking_out.button_validate()
        wizard = self.env[(res_dict.get('res_model'))].browse(res_dict.get('res_id'))
        res_dict_for_back_order = wizard.process()
        backorder_wizard = self.env[(res_dict_for_back_order.get('res_model'))].browse(res_dict_for_back_order.get('res_id'))
        backorder_wizard.process()
        quants = self.StockQuantObj.search([('product_id', '=', productKG.id), ('location_id', '=', self.stock_location)])
        total_qty = [quant.quantity for quant in quants]
        # Check total quantity stock location.
        self.assertEqual(sum(total_qty), 999.9995, 'Expecting 999.9995 kg , got %.4f kg on location stock!' % (sum(total_qty)))

        # ---------------------------------
        # Check Back order created or not.
        # ---------------------------------
        bo_out_1 = self.PickingObj.search([('backorder_id', '=', picking_out.id)])
        self.assertEqual(len(bo_out_1), 1, 'Back order should be created.')
        # Check total move lines of back order.
        self.assertEqual(len(bo_out_1.move_lines), 1, 'Wrong number of move lines')
        moves_KG = self.MoveObj.search([('product_id', '=', productKG.id), ('picking_id', '=', bo_out_1.id)], limit=1)
        # Check back order created with correct quantity and uom or not.
        self.assertEqual(moves_KG.product_uom_qty, 2.0, 'Wrong move quantity (%s found instead of 2.0)' % (moves_KG.product_uom_qty))
        self.assertEqual(moves_KG.product_uom.id, self.uom_gm.id, 'Wrong uom in move for product KG.')
        bo_out_1.action_assign()
        pack_opt = self.StockPackObj.search([('product_id', '=', productKG.id), ('picking_id', '=', bo_out_1.id)], limit=1)
        pack_opt.write({'product_uom_qty': 0.5})
        res_dict = bo_out_1.button_validate()
        wizard = self.env[(res_dict.get('res_model'))].browse(res_dict.get('res_id'))
        res_dict_for_back_order = wizard.process()
        backorder_wizard = self.env[(res_dict_for_back_order.get('res_model'))].browse(res_dict_for_back_order.get('res_id'))
        backorder_wizard.process()
        quants = self.StockQuantObj.search([('product_id', '=', productKG.id), ('location_id', '=', self.stock_location)])
        total_qty = [quant.quantity for quant in quants]

        # Check total quantity stock location.
        self.assertEqual(sum(total_qty), 999.9990, 'Expecting 999.9990 kg , got %.4f kg on location stock!' % (sum(total_qty)))

        # Check Back order created or not.
        # ---------------------------------
        bo_out_2 = self.PickingObj.search([('backorder_id', '=', bo_out_1.id)])
        self.assertEqual(len(bo_out_2), 1, 'Back order should be created.')
        # Check total move lines of back order.
        self.assertEqual(len(bo_out_2.move_lines), 1, 'Wrong number of move lines')
        # Check back order created with correct move quantity and uom or not.
        moves_KG = self.MoveObj.search([('product_id', '=', productKG.id), ('picking_id', '=', bo_out_2.id)], limit=1)
        self.assertEqual(moves_KG.product_uom_qty, 1.5, 'Wrong move quantity (%s found instead of 1.5)' % (moves_KG.product_uom_qty))
        self.assertEqual(moves_KG.product_uom.id, self.uom_gm.id, 'Wrong uom in move for product KG.')
        bo_out_2.action_assign()
        pack_opt = self.StockPackObj.search([('product_id', '=', productKG.id), ('picking_id', '=', bo_out_2.id)], limit=1)
        pack_opt.write({'product_uom_qty': 0.5})
        res_dict = bo_out_2.button_validate()
        wizard = self.env[(res_dict.get('res_model'))].browse(res_dict.get('res_id'))
        res_dict_for_back_order = wizard.process()
        backorder_wizard = self.env[(res_dict_for_back_order.get('res_model'))].browse(res_dict_for_back_order.get('res_id'))
        backorder_wizard.process()
        # Check total quantity stock location of product KG.
        quants = self.StockQuantObj.search([('product_id', '=', productKG.id), ('location_id', '=', self.stock_location)])
        total_qty = [quant.quantity for quant in quants]
        self.assertEqual(sum(total_qty), 999.9985, 'Expecting 999.9985 kg , got %.4f kg on location stock!' % (sum(total_qty)))

        # Check Back order created or not.
        # ---------------------------------
        bo_out_3 = self.PickingObj.search([('backorder_id', '=', bo_out_2.id)])
        self.assertEqual(len(bo_out_3), 1, 'Back order should be created.')
        # Check total move lines of back order.
        self.assertEqual(len(bo_out_3.move_lines), 1, 'Wrong number of move lines')
        # Check back order created with correct quantity and uom or not.
        moves_KG = self.MoveObj.search([('product_id', '=', productKG.id), ('picking_id', '=', bo_out_3.id)], limit=1)
        self.assertEqual(moves_KG.product_uom_qty, 1, 'Wrong move quantity (%s found instead of 1.0)' % (moves_KG.product_uom_qty))
        self.assertEqual(moves_KG.product_uom.id, self.uom_gm.id, 'Wrong uom in move for product KG.')
        bo_out_3.action_assign()
        pack_opt = self.StockPackObj.search([('product_id', '=', productKG.id), ('picking_id', '=', bo_out_3.id)], limit=1)
        pack_opt.write({'product_uom_qty': 0.5})
        res_dict = bo_out_3.button_validate()
        wizard = self.env[(res_dict.get('res_model'))].browse(res_dict.get('res_id'))
        res_dict_for_back_order = wizard.process()
        backorder_wizard = self.env[(res_dict_for_back_order.get('res_model'))].browse(res_dict_for_back_order.get('res_id'))
        backorder_wizard.process()
        quants = self.StockQuantObj.search([('product_id', '=', productKG.id), ('location_id', '=', self.stock_location)])
        total_qty = [quant.quantity for quant in quants]
        self.assertEqual(sum(total_qty), 999.9980, 'Expecting 999.9980 kg , got %.4f kg on location stock!' % (sum(total_qty)))

        # Check Back order created or not.
        # ---------------------------------
        bo_out_4 = self.PickingObj.search([('backorder_id', '=', bo_out_3.id)])

        self.assertEqual(len(bo_out_4), 1, 'Back order should be created.')
        # Check total move lines of back order.
        self.assertEqual(len(bo_out_4.move_lines), 1, 'Wrong number of move lines')
        # Check back order created with correct quantity and uom or not.
        moves_KG = self.MoveObj.search([('product_id', '=', productKG.id), ('picking_id', '=', bo_out_4.id)], limit=1)
        self.assertEqual(moves_KG.product_uom_qty, 0.5, 'Wrong move quantity (%s found instead of 0.5)' % (moves_KG.product_uom_qty))
        self.assertEqual(moves_KG.product_uom.id, self.uom_gm.id, 'Wrong uom in move for product KG.')
        bo_out_4.action_assign()
        pack_opt = self.StockPackObj.search([('product_id', '=', productKG.id), ('picking_id', '=', bo_out_4.id)], limit=1)
        pack_opt.write({'product_uom_qty': 0.5})
        res_dict = bo_out_4.button_validate()
        wizard = self.env[(res_dict.get('res_model'))].browse(res_dict.get('res_id'))
        wizard.process()
        quants = self.StockQuantObj.search([('product_id', '=', productKG.id), ('location_id', '=', self.stock_location)])
        total_qty = [quant.quantity for quant in quants]
        self.assertEqual(sum(total_qty), 999.9975, 'Expecting 999.9975 kg , got %.4f kg on location stock!' % (sum(total_qty)))

    def test_20_create_inventory_with_different_uom(self):
        """Create inventory with different unit of measure."""

        # ------------------------------------------------
        # Test inventory with product A(Unit).
        # ------------------------------------------------

        inventory = self.InvObj.create({'name': 'Test',
                                        'product_ids': [(4, self.UnitA.id)]})
        inventory.action_start()
        self.assertFalse(inventory.line_ids, "Inventory line should not created.")
        inventory_line = self.InvLineObj.create({
            'inventory_id': inventory.id,
            'product_id': self.UnitA.id,
            'product_uom_id': self.uom_dozen.id,
            'product_qty': 10,
            'location_id': self.stock_location})
        inventory.action_validate()
        # Check quantity available of product UnitA.
        quants = self.StockQuantObj.search([('product_id', '=', self.UnitA.id), ('location_id', '=', self.stock_location)])
        total_qty = [quant.quantity for quant in quants]
        self.assertEqual(sum(total_qty), 120, 'Expecting 120 Units , got %.4f Units on location stock!' % (sum(total_qty)))
        self.assertEqual(self.UnitA.qty_available, 120, 'Expecting 120 Units , got %.4f Units of quantity available!' % (self.UnitA.qty_available))
        # Create Inventory again for product UnitA.
        inventory = self.InvObj.create({'name': 'Test',
                                        'product_ids': [(4, self.UnitA.id)]})
        inventory.action_start()
        self.assertEqual(len(inventory.line_ids), 1, "One inventory line should be created.")
        inventory_line = self.InvLineObj.search([('product_id', '=', self.UnitA.id), ('inventory_id', '=', inventory.id)], limit=1)
        self.assertEqual(inventory_line.product_qty, 120, "Wrong product quantity in inventory line.")
        # Modify the inventory line and set the quantity to 144 product on this new inventory.
        inventory_line.write({'product_qty': 144})
        inventory.action_validate()
        move = self.MoveObj.search([('product_id', '=', self.UnitA.id), ('inventory_id', '=', inventory.id)], limit=1)
        self.assertEqual(move.product_uom_qty, 24, "Wrong move quantity of product UnitA.")
        # Check quantity available of product UnitA.
        quants = self.StockQuantObj.search([('product_id', '=', self.UnitA.id), ('location_id', '=', self.stock_location)])
        total_qty = [quant.quantity for quant in quants]
        self.assertEqual(sum(total_qty), 144, 'Expecting 144 Units , got %.4f Units on location stock!' % (sum(total_qty)))
        self.UnitA._compute_quantities()
        self.assertEqual(self.UnitA.qty_available, 144, 'Expecting 144 Units , got %.4f Units of quantity available!' % (self.UnitA.qty_available))

        # ------------------------------------------------
        # Test inventory with product KG.
        # ------------------------------------------------

        productKG = self.ProductObj.create({'name': 'Product KG', 'uom_id': self.uom_kg.id, 'uom_po_id': self.uom_kg.id, 'type': 'product'})
        inventory = self.InvObj.create({'name': 'Inventory Product KG',
                                        'product_ids': [(4, productKG.id)]})
        inventory.action_start()
        self.assertFalse(inventory.line_ids, "Inventory line should not created.")
        inventory_line = self.InvLineObj.create({
            'inventory_id': inventory.id,
            'product_id': productKG.id,
            'product_uom_id': self.uom_tone.id,
            'product_qty': 5,
            'location_id': self.stock_location})
        inventory.action_validate()
        quants = self.StockQuantObj.search([('product_id', '=', productKG.id), ('location_id', '=', self.stock_location)])
        total_qty = [quant.quantity for quant in quants]
        self.assertEqual(sum(total_qty), 5000, 'Expecting 5000 kg , got %.4f kg on location stock!' % (sum(total_qty)))
        self.assertEqual(productKG.qty_available, 5000, 'Expecting 5000 kg , got %.4f kg of quantity available!' % (productKG.qty_available))
        # Create Inventory again.
        inventory = self.InvObj.create({'name': 'Test',
                                        'product_ids': [(4, productKG.id)]})
        inventory.action_start()
        self.assertEqual(len(inventory.line_ids), 1, "One inventory line should be created.")
        inventory_line = self.InvLineObj.search([('product_id', '=', productKG.id), ('inventory_id', '=', inventory.id)], limit=1)
        self.assertEqual(inventory_line.product_qty, 5000, "Wrong product quantity in inventory line.")
        # Modify the inventory line and set the quantity to 4000 product on this new inventory.
        inventory_line.write({'product_qty': 4000})
        inventory.action_validate()
        # Check inventory move quantity of product KG.
        move = self.MoveObj.search([('product_id', '=', productKG.id), ('inventory_id', '=', inventory.id)], limit=1)
        self.assertEqual(move.product_uom_qty, 1000, "Wrong move quantity of product KG.")
        # Check quantity available of product KG.
        quants = self.StockQuantObj.search([('product_id', '=', productKG.id), ('location_id', '=', self.stock_location)])
        total_qty = [quant.quantity for quant in quants]
        self.assertEqual(sum(total_qty), 4000, 'Expecting 4000 kg , got %.4f on location stock!' % (sum(total_qty)))
        productKG._compute_quantities()
        self.assertEqual(productKG.qty_available, 4000, 'Expecting 4000 kg , got %.4f of quantity available!' % (productKG.qty_available))

        # --------------------------------------------------------
        # TEST EMPTY INVENTORY WITH PACKS and LOTS
        # ---------------------------------------------------------

        packproduct = self.ProductObj.create({'name': 'Pack Product', 'uom_id': self.uom_unit.id, 'uom_po_id': self.uom_unit.id, 'type': 'product'})
        lotproduct = self.ProductObj.create({'name': 'Lot Product', 'uom_id': self.uom_unit.id, 'uom_po_id': self.uom_unit.id, 'type': 'product'})
        inventory = self.InvObj.create({'name': 'Test Partial and Pack',
                                        'start_empty': True,
                                        'location_ids': [(4, self.stock_location)]})
        inventory.action_start()
        pack_obj = self.env['stock.quant.package']
        lot_obj = self.env['stock.production.lot']
        pack1 = pack_obj.create({'name': 'PACK00TEST1'})
        pack_obj.create({'name': 'PACK00TEST2'})
        lot1 = lot_obj.create({'name': 'Lot001', 'product_id': lotproduct.id})
        move = self.MoveObj.search([('product_id', '=', productKG.id), ('inventory_id', '=', inventory.id)], limit=1)
        self.assertEqual(len(move), 0, "Partial filter should not create a lines upon prepare")

        line_vals = []
        line_vals += [{'location_id': self.stock_location, 'product_id': packproduct.id, 'product_qty': 10, 'product_uom_id': packproduct.uom_id.id}]
        line_vals += [{'location_id': self.stock_location, 'product_id': packproduct.id, 'product_qty': 20, 'product_uom_id': packproduct.uom_id.id, 'package_id': pack1.id}]
        line_vals += [{'location_id': self.stock_location, 'product_id': lotproduct.id, 'product_qty': 30, 'product_uom_id': lotproduct.uom_id.id, 'prod_lot_id': lot1.id}]
        line_vals += [{'location_id': self.stock_location, 'product_id': lotproduct.id, 'product_qty': 25, 'product_uom_id': lotproduct.uom_id.id, 'prod_lot_id': False}]
        inventory.write({'line_ids': [(0, 0, x) for x in line_vals]})
        inventory.action_validate()
        self.assertEqual(packproduct.qty_available, 30, "Wrong qty available for packproduct")
        self.assertEqual(lotproduct.qty_available, 55, "Wrong qty available for lotproduct")
        quants = self.StockQuantObj.search([('product_id', '=', packproduct.id), ('location_id', '=', self.stock_location), ('package_id', '=', pack1.id)])
        total_qty = sum([quant.quantity for quant in quants])
        self.assertEqual(total_qty, 20, 'Expecting 20 units on package 1 of packproduct, but we got %.4f on location stock!' % (total_qty))

        # Create an inventory that will put the lots without lot to 0 and check that taking without pack will not take it from the pack
        inventory2 = self.InvObj.create({'name': 'Test Partial Lot and Pack2',
                                         'start_empty': True,
                                         'location_ids': [(4, self.stock_location)]})
        inventory2.action_start()
        line_vals = []
        line_vals += [{'location_id': self.stock_location, 'product_id': packproduct.id, 'product_qty': 20, 'product_uom_id': packproduct.uom_id.id}]
        line_vals += [{'location_id': self.stock_location, 'product_id': lotproduct.id, 'product_qty': 0, 'product_uom_id': lotproduct.uom_id.id, 'prod_lot_id': False}]
        line_vals += [{'location_id': self.stock_location, 'product_id': lotproduct.id, 'product_qty': 10, 'product_uom_id': lotproduct.uom_id.id, 'prod_lot_id': lot1.id}]
        inventory2.write({'line_ids': [(0, 0, x) for x in line_vals]})
        inventory2.action_validate()
        self.assertEqual(packproduct.qty_available, 40, "Wrong qty available for packproduct")
        self.assertEqual(lotproduct.qty_available, 10, "Wrong qty available for lotproduct")
        quants = self.StockQuantObj.search([('product_id', '=', lotproduct.id), ('location_id', '=', self.stock_location), ('lot_id', '=', lot1.id)])
        total_qty = sum([quant.quantity for quant in quants])
        self.assertEqual(total_qty, 10, 'Expecting 0 units lot of lotproduct, but we got %.4f on location stock!' % (total_qty))
        quants = self.StockQuantObj.search([('product_id', '=', lotproduct.id), ('location_id', '=', self.stock_location), ('lot_id', '=', False)])
        total_qty = sum([quant.quantity for quant in quants])
        self.assertEqual(total_qty, 0, 'Expecting 0 units lot of lotproduct, but we got %.4f on location stock!' % (total_qty))

    def test_30_check_with_no_incoming_lot(self):
        """ Picking in without lots and picking out with"""
        # Change basic operation type not to get lots
        # Create product with lot tracking
        picking_in = self.env['stock.picking.type'].browse(self.picking_type_in)
        picking_in.use_create_lots = False
        self.productA.tracking = 'lot'
        picking_in = self.PickingObj.create({
            'partner_id': self.partner_delta_id,
            'picking_type_id': self.picking_type_in,
            'location_id': self.supplier_location,
            'location_dest_id': self.stock_location})
        self.MoveObj.create({
            'name': self.productA.name,
            'product_id': self.productA.id,
            'product_uom_qty': 4,
            'product_uom': self.productA.uom_id.id,
            'picking_id': picking_in.id,
            'picking_type_id': self.picking_type_in,
            'location_id': self.supplier_location,
            'location_dest_id': self.stock_location})

        # Check incoming shipment move lines state.
        for move in picking_in.move_lines:
            self.assertEqual(move.state, 'draft', 'Wrong state of move line.')
        # Confirm incoming shipment.
        picking_in.action_confirm()
        # Check incoming shipment move lines state.
        for move in picking_in.move_lines:
            self.assertEqual(move.state, 'assigned', 'Wrong state of move line.')

        res_dict = picking_in.button_validate()
        wizard = self.env[(res_dict.get('res_model'))].browse(res_dict.get('res_id'))
        wizard.process()
        picking_out = self.PickingObj.create({
            'partner_id': self.partner_agrolite_id,
            'name': 'testpicking',
            'picking_type_id': self.picking_type_out,
            'location_id': self.stock_location,
            'location_dest_id': self.customer_location})
        move_out = self.MoveObj.create({
            'name': self.productA.name,
            'product_id': self.productA.id,
            'product_uom_qty': 3,
            'product_uom': self.productA.uom_id.id,
            'picking_id': picking_out.id,
            'location_id': self.stock_location,
            'location_dest_id': self.customer_location})
        picking_out.action_confirm()
        picking_out.action_assign()
        pack_opt = self.StockPackObj.search([('picking_id', '=', picking_out.id)], limit=1)
        lot1 = self.LotObj.create({'product_id': self.productA.id, 'name': 'LOT1'})
        lot2 = self.LotObj.create({'product_id': self.productA.id, 'name': 'LOT2'})
        lot3 = self.LotObj.create({'product_id': self.productA.id, 'name': 'LOT3'})

        pack_opt.write({'lot_id': lot1.id, 'qty_done': 1.0})
        self.StockPackObj.create({'product_id': self.productA.id, 'move_id': move_out.id, 'product_uom_id': move_out.product_uom.id, 'lot_id': lot2.id, 'qty_done': 1.0, 'location_id': self.stock_location, 'location_dest_id': self.customer_location})
        self.StockPackObj.create({'product_id': self.productA.id, 'move_id': move_out.id, 'product_uom_id': move_out.product_uom.id, 'lot_id': lot3.id, 'qty_done': 2.0, 'location_id': self.stock_location, 'location_dest_id': self.customer_location})
        picking_out.action_done()
        quants = self.StockQuantObj.search([('product_id', '=', self.productA.id), ('location_id', '=', self.stock_location)])
        # TODO wait sle fix
        # self.assertFalse(quants, 'Should not have any quants in stock anymore')

    def test_40_pack_in_pack(self):
        """ Put a pack in pack"""
        picking_out = self.PickingObj.create({
            'partner_id': self.partner_agrolite_id,
            'picking_type_id': self.picking_type_out,
            'location_id': self.pack_location,
            'location_dest_id': self.customer_location})
        move_out = self.MoveObj.create({
            'name': self.productA.name,
            'product_id': self.productA.id,
            'product_uom_qty': 3,
            'product_uom': self.productA.uom_id.id,
            'picking_id': picking_out.id,
            'location_id': self.pack_location,
            'location_dest_id': self.customer_location})
        picking_pack = self.PickingObj.create({
            'partner_id': self.partner_agrolite_id,
            'picking_type_id': self.picking_type_out,
            'location_id': self.stock_location,
            'location_dest_id': self.pack_location})
        move_pack = self.MoveObj.create({
            'name': self.productA.name,
            'product_id': self.productA.id,
            'product_uom_qty': 3,
            'product_uom': self.productA.uom_id.id,
            'picking_id': picking_pack.id,
            'location_id': self.stock_location,
            'location_dest_id': self.pack_location,
            'move_dest_ids': [(4, move_out.id, 0)]})
        picking_in = self.PickingObj.create({
            'partner_id': self.partner_delta_id,
            'picking_type_id': self.picking_type_in,
            'location_id': self.supplier_location,
            'location_dest_id': self.stock_location})
        move_in = self.MoveObj.create({
            'name': self.productA.name,
            'product_id': self.productA.id,
            'product_uom_qty': 3,
            'product_uom': self.productA.uom_id.id,
            'picking_id': picking_in.id,
            'location_id': self.supplier_location,
            'location_dest_id': self.stock_location,
            'move_dest_ids': [(4, move_pack.id, 0)]})

        # Check incoming shipment move lines state.
        for move in picking_in.move_lines:
            self.assertEqual(move.state, 'draft', 'Wrong state of move line.')
        # Confirm incoming shipment.
        picking_in.action_confirm()
        # Check incoming shipment move lines state.
        for move in picking_in.move_lines:
            self.assertEqual(move.state, 'assigned', 'Wrong state of move line.')

        # Check incoming shipment move lines state.
        for move in picking_pack.move_lines:
            self.assertEqual(move.state, 'draft', 'Wrong state of move line.')
        # Confirm incoming shipment.
        picking_pack.action_confirm()
        # Check incoming shipment move lines state.
        for move in picking_pack.move_lines:
            self.assertEqual(move.state, 'waiting', 'Wrong state of move line.')

        # Check incoming shipment move lines state.
        for move in picking_out.move_lines:
            self.assertEqual(move.state, 'draft', 'Wrong state of move line.')
        # Confirm incoming shipment.
        picking_out.action_confirm()
        # Check incoming shipment move lines state.
        for move in picking_out.move_lines:
            self.assertEqual(move.state, 'waiting', 'Wrong state of move line.')

        # Set the quantity done on the pack operation
        move_in.move_line_ids.qty_done = 3.0
        # Put in a pack
        picking_in.put_in_pack()
        # Get the new package
        picking_in_package = move_in.move_line_ids.result_package_id
        # Validate picking
        picking_in.action_done()

        # Check first picking state changed to done
        for move in picking_in.move_lines:
            self.assertEqual(move.state, 'done', 'Wrong state of move line.')
        # Check next picking state changed to 'assigned'
        for move in picking_pack.move_lines:
            self.assertEqual(move.state, 'assigned', 'Wrong state of move line.')

        # Set the quantity done on the pack operation
        move_pack.move_line_ids.qty_done = 3.0
        # Get the new package
        picking_pack_package = move_pack.move_line_ids.result_package_id
        # Validate picking
        picking_pack.action_done()

        # Check second picking state changed to done
        for move in picking_pack.move_lines:
            self.assertEqual(move.state, 'done', 'Wrong state of move line.')
        # Check next picking state changed to 'assigned'
        for move in picking_out.move_lines:
            self.assertEqual(move.state, 'assigned', 'Wrong state of move line.')

        # Validate picking
        picking_out.move_line_ids.qty_done = 3.0
        picking_out_package = move_out.move_line_ids.result_package_id
        picking_out.action_done()

        # check all pickings are done
        for move in picking_in.move_lines:
            self.assertEqual(move.state, 'done', 'Wrong state of move line.')
        for move in picking_pack.move_lines:
            self.assertEqual(move.state, 'done', 'Wrong state of move line.')
        for move in picking_out.move_lines:
            self.assertEqual(move.state, 'done', 'Wrong state of move line.')

        # Check picking_in_package is in picking_pack_package
        self.assertEqual(picking_in_package.id, picking_pack_package.id, 'The package created in the picking in is not in the one created in picking pack')
        self.assertEqual(picking_pack_package.id, picking_out_package.id, 'The package created in the picking in is not in the one created in picking pack')
        # Check that we have one quant in customer location.
        quant = self.StockQuantObj.search([('product_id', '=', self.productA.id), ('location_id', '=', self.customer_location)])
        self.assertEqual(len(quant), 1, 'There should be one quant with package for customer location')
        # Check that the  parent package of the quant is the picking_in_package

    def test_50_create_in_out_with_product_pack_lines(self):
        picking_in = self.PickingObj.create({
            'partner_id': self.partner_delta_id,
            'picking_type_id': self.picking_type_in,
            'location_id': self.supplier_location,
            'location_dest_id': self.stock_location})
        self.MoveObj.create({
            'name': self.productE.name,
            'product_id': self.productE.id,
            'product_uom_qty': 10,
            'product_uom': self.productE.uom_id.id,
            'picking_id': picking_in.id,
            'location_id': self.supplier_location,
            'location_dest_id': self.stock_location})
        picking_in.action_confirm()
        pack_obj = self.env['stock.quant.package']
        pack1 = pack_obj.create({'name': 'PACKINOUTTEST1'})
        pack2 = pack_obj.create({'name': 'PACKINOUTTEST2'})
        picking_in.move_line_ids[0].result_package_id = pack1
        picking_in.move_line_ids[0].qty_done = 4
        packop2 = picking_in.move_line_ids[0].with_context(bypass_reservation_update=True).copy({'product_uom_qty': 0})
        packop2.qty_done = 6
        packop2.result_package_id = pack2
        picking_in.action_done()
        quants = self.env['stock.quant']._gather(self.productE, self.env['stock.location'].browse(self.stock_location))
        self.assertEqual(sum([x.quantity for x in quants]), 10.0, 'Expecting 10 pieces in stock')
        # Check the quants are in the package
        self.assertEqual(sum(x.quantity for x in pack1.quant_ids), 4.0, 'Pack 1 should have 4 pieces')
        self.assertEqual(sum(x.quantity for x in pack2.quant_ids), 6.0, 'Pack 2 should have 6 pieces')
        picking_out = self.PickingObj.create({
            'partner_id': self.partner_agrolite_id,
            'picking_type_id': self.picking_type_out,
            'location_id': self.stock_location,
            'location_dest_id': self.customer_location})
        self.MoveObj.create({
            'name': self.productE.name,
            'product_id': self.productE.id,
            'product_uom_qty': 3,
            'product_uom': self.productE.uom_id.id,
            'picking_id': picking_out.id,
            'location_id': self.stock_location,
            'location_dest_id': self.customer_location})
        picking_out.action_confirm()
        picking_out.action_assign()
        packout1 = picking_out.move_line_ids[0]
        packout2 = picking_out.move_line_ids[0].with_context(bypass_reservation_update=True).copy({'product_uom_qty': 0})
        packout1.qty_done = 2
        packout1.package_id = pack1
        packout2.package_id = pack2
        packout2.qty_done = 1
        picking_out.action_done()
        # Should be only 1 negative quant in supplier location
        neg_quants = self.env['stock.quant'].search([('product_id', '=', self.productE.id), ('quantity', '<', 0.0)])
        self.assertEqual(len(neg_quants), 1, 'There should be 1 negative quants for supplier!')
        self.assertEqual(neg_quants.location_id.id, self.supplier_location, 'There shoud be 1 negative quants for supplier!')

        quants = self.env['stock.quant']._gather(self.productE, self.env['stock.location'].browse(self.stock_location))
        self.assertEqual(len(quants), 2, 'We should have exactly 2 quants in the end')

    def test_60_create_in_out_with_product_pack_lines(self):
        picking_in = self.PickingObj.create({
            'partner_id': self.partner_delta_id,
            'picking_type_id': self.picking_type_in,
            'location_id': self.supplier_location,
            'location_dest_id': self.stock_location})
        self.MoveObj.create({
            'name': self.productE.name,
            'product_id': self.productE.id,
            'product_uom_qty': 200,
            'product_uom': self.productE.uom_id.id,
            'picking_id': picking_in.id,
            'location_id': self.supplier_location,
            'location_dest_id': self.stock_location})

        picking_in.action_confirm()
        pack_obj = self.env['stock.quant.package']
        pack1 = pack_obj.create({'name': 'PACKINOUTTEST1'})
        pack2 = pack_obj.create({'name': 'PACKINOUTTEST2'})
        picking_in.move_line_ids[0].result_package_id = pack1
        picking_in.move_line_ids[0].qty_done = 120
        packop2 = picking_in.move_line_ids[0].with_context(bypass_reservation_update=True).copy({'product_uom_qty': 0})
        packop2.qty_done = 80
        packop2.result_package_id = pack2
        picking_in.action_done()
        quants = self.env['stock.quant']._gather(self.productE, self.env['stock.location'].browse(self.stock_location))
        self.assertEqual(sum([x.quantity for x in quants]), 200.0, 'Expecting 200 pieces in stock')
        # Check the quants are in the package
        self.assertEqual(sum(x.quantity for x in pack1.quant_ids), 120, 'Pack 1 should have 120 pieces')
        self.assertEqual(sum(x.quantity for x in pack2.quant_ids), 80, 'Pack 2 should have 80 pieces')
        picking_out = self.PickingObj.create({
            'partner_id': self.partner_agrolite_id,
            'picking_type_id': self.picking_type_out,
            'location_id': self.stock_location,
            'location_dest_id': self.customer_location})
        self.MoveObj.create({
            'name': self.productE.name,
            'product_id': self.productE.id,
            'product_uom_qty': 200,
            'product_uom': self.productE.uom_id.id,
            'picking_id': picking_out.id,
            'location_id': self.stock_location,
            'location_dest_id': self.customer_location})
        picking_out.action_confirm()
        picking_out.action_assign()
        # Convert entire packs into taking out of packs
        packout0 = picking_out.move_line_ids[0]
        packout1 = picking_out.move_line_ids[1]
        packout0.write({
            'package_id': pack1.id,
            'product_id': self.productE.id,
            'qty_done': 120.0,
            'product_uom_id': self.productE.uom_id.id,
        })
        packout1.write({
            'package_id': pack2.id,
            'product_id': self.productE.id,
            'qty_done': 80.0,
            'product_uom_id': self.productE.uom_id.id,
        })
        picking_out.action_done()
        # Should be only 1 negative quant in supplier location
        neg_quants = self.env['stock.quant'].search([('product_id', '=', self.productE.id), ('quantity', '<', 0.0)])
        self.assertEqual(len(neg_quants), 1, 'There should be 1 negative quants for supplier!')
        self.assertEqual(neg_quants.location_id.id, self.supplier_location, 'There shoud be 1 negative quants for supplier!')
        # We should also make sure that when matching stock moves with pack operations, it takes the correct
        quants = self.env['stock.quant']._gather(self.productE, self.env['stock.location'].browse(self.stock_location))
        self.assertEqual(sum(quants.mapped('quantity')), 0, 'We should have no quants in the end')

    def test_70_picking_state_all_at_once_reserve(self):
        """ This test will check that the state of the picking is correctly computed according
        to the state of its move lines and its move type.
        """
        # move_type: direct == partial, one == all at once
        # picking: confirmed == waiting availability

        # -----------------------------------------------------------
        # "all at once" and "reserve" scenario
        # -----------------------------------------------------------
        # get one product in stock
        inventory = self.env['stock.inventory'].create({
            'name': 'Inventory Product Table',
            'line_ids': [(0, 0, {
                'product_id': self.productA.id,
                'product_uom_id': self.productA.uom_id.id,
                'product_qty': 1,
                'location_id': self.stock_location
            })]
        })
        inventory.action_start()
        inventory.action_validate()

        # create a "all at once" delivery order for two products
        picking_out = self.PickingObj.create({
            'partner_id': self.partner_agrolite_id,
            'picking_type_id': self.picking_type_out,
            'location_id': self.stock_location,
            'location_dest_id': self.customer_location})
        picking_out.move_type = 'one'

        self.MoveObj.create({
            'name': self.productA.name,
            'product_id': self.productA.id,
            'product_uom_qty': 2,
            'product_uom': self.productA.uom_id.id,
            'picking_id': picking_out.id,
            'location_id': self.stock_location,
            'location_dest_id': self.customer_location})
        # validate this delivery order, it should be in the waiting state
        picking_out.action_assign()
        self.assertEquals(picking_out.state, "confirmed")

        # receive one product in stock
        inventory = self.env['stock.inventory'].create({
            'name': 'Inventory Product Table',
            'line_ids': [(0, 0, {
                'product_id': self.productA.id,
                'product_uom_id': self.productA.uom_id.id,
                'product_qty': 2,
                'location_id': self.stock_location
            })]
        })
        inventory.action_start()
        inventory.action_validate()
        # recheck availability of the delivery order, it should be assigned
        picking_out.action_assign()
        self.assertEquals(len(picking_out.move_lines), 1.0)
        self.assertEquals(picking_out.move_lines.product_qty, 2.0)
        self.assertEquals(picking_out.state, "assigned")

    def test_71_picking_state_all_at_once_force_assign(self):
        """ This test will check that the state of the picking is correctly computed according
        to the state of its move lines and its move type.
        """
        # move_type: direct == partial, one == all at once
        # picking: confirmed == waiting availability, partially_available = partially available

        # -----------------------------------------------------------
        # "all at once" and "force assign" scenario
        # -----------------------------------------------------------
        # create a "all at once" delivery order for two products
        picking_out = self.PickingObj.create({
            'partner_id': self.partner_agrolite_id,
            'picking_type_id': self.picking_type_out,
            'location_id': self.stock_location,
            'location_dest_id': self.customer_location})
        picking_out.move_type = 'direct'

        self.MoveObj.create({
            'name': self.productA.name,
            'product_id': self.productA.id,
            'product_uom_qty': 2,
            'product_uom': self.productA.uom_id.id,
            'picking_id': picking_out.id,
            'location_id': self.stock_location,
            'location_dest_id': self.customer_location})

        # validate this delivery order, it should be in the waiting state
        picking_out.action_assign()
        self.assertEquals(picking_out.state, "confirmed")

    def test_72_picking_state_partial_reserve(self):
        """ This test will check that the state of the picking is correctly computed according
        to the state of its move lines and its move type.
        """
        # move_type: direct == partial, one == all at once
        # picking: confirmed == waiting availability, partially_available = partially available

        # -----------------------------------------------------------
        # "partial" and "reserve" scenario
        # -----------------------------------------------------------
        # get one product in stock
        inventory = self.env['stock.inventory'].create({
            'name': 'Inventory Product Table',
            'line_ids': [(0, 0, {
                'product_id': self.productA.id,
                'product_uom_id': self.productA.uom_id.id,
                'product_qty': 1,
                'location_id': self.stock_location
            })]
        })
        inventory.action_start()
        inventory.action_validate()

        # create a "partial" delivery order for two products
        picking_out = self.PickingObj.create({
            'partner_id': self.partner_agrolite_id,
            'picking_type_id': self.picking_type_out,
            'location_id': self.stock_location,
            'location_dest_id': self.customer_location})
        picking_out.move_type = 'direct'

        self.MoveObj.create({
            'name': self.productA.name,
            'product_id': self.productA.id,
            'product_uom_qty': 2,
            'product_uom': self.productA.uom_id.id,
            'picking_id': picking_out.id,
            'location_id': self.stock_location,
            'location_dest_id': self.customer_location})

        # validate this delivery order, it should be in partially available
        picking_out.action_assign()
        self.assertEquals(picking_out.state, "assigned")

        # receive one product in stock
        inventory = self.env['stock.inventory'].create({
            'name': 'Inventory Product Table',
            'line_ids': [(0, 0, {
                'product_id': self.productA.id,
                'product_uom_id': self.productA.uom_id.id,
                'product_qty': 2,
                'location_id': self.stock_location
            })]
        })
        inventory.action_start()
        inventory.action_validate()

        # recheck availability of the delivery order, it should be assigned
        picking_out.action_assign()
        self.assertEquals(picking_out.state, "assigned")

    def test_73_picking_state_partial_force_assign(self):
        """ This test will check that the state of the picking is correctly computed according
        to the state of its move lines and its move type.
        """
        # move_type: direct == partial, one == all at once
        # picking: confirmed == waiting availability, partially_available = partially available

        # -----------------------------------------------------------
        # "partial" and "force assign" scenario
        # -----------------------------------------------------------
        picking_out = self.PickingObj.create({
            'partner_id': self.partner_agrolite_id,
            'picking_type_id': self.picking_type_out,
            'location_id': self.stock_location,
            'location_dest_id': self.customer_location})
        picking_out.move_type = 'direct'

        self.MoveObj.create({
            'name': self.productA.name,
            'product_id': self.productA.id,
            'product_uom_qty': 2,
            'product_uom': self.productA.uom_id.id,
            'picking_id': picking_out.id,
            'location_id': self.stock_location,
            'location_dest_id': self.customer_location})

        # validate this delivery order, it should be in the waiting state
        picking_out.action_assign()
        self.assertEquals(picking_out.state, "confirmed")

    def test_74_move_state_waiting_mto(self):
        """ This test will check that when a move is unreserved, its state changes to 'waiting' if
        it has ancestors or if it has a 'procure_method' equal to 'make_to_order' else the state
        changes to 'confirmed'.
        """
        picking_out = self.PickingObj.create({
            'partner_id': self.partner_agrolite_id,
            'picking_type_id': self.picking_type_out,
            'location_id': self.stock_location,
            'location_dest_id': self.customer_location})
        move_mto_alone = self.MoveObj.create({
            'name': self.productA.name,
            'product_id': self.productA.id,
            'product_uom_qty': 2,
            'product_uom': self.productA.uom_id.id,
            'picking_id': picking_out.id,
            'location_id': self.stock_location,
            'location_dest_id': self.customer_location,
            'procure_method': 'make_to_order'})
        move_with_ancestors = self.MoveObj.create({
            'name': self.productB.name,
            'product_id': self.productB.id,
            'product_uom_qty': 2,
            'product_uom': self.productB.uom_id.id,
            'picking_id': picking_out.id,
            'location_id': self.stock_location,
            'location_dest_id': self.customer_location})
        self.MoveObj.create({
            'name': self.productB.name,
            'product_id': self.productB.id,
            'product_uom_qty': 2,
            'product_uom': self.productB.uom_id.id,
            'picking_id': picking_out.id,
            'location_id': self.stock_location,
            'location_dest_id': self.customer_location,
            'move_dest_ids': [(4, move_with_ancestors.id, 0)]})
        other_move = self.MoveObj.create({
            'name': self.productC.name,
            'product_id': self.productC.id,
            'product_uom_qty': 2,
            'product_uom': self.productC.uom_id.id,
            'picking_id': picking_out.id,
            'location_id': self.stock_location,
            'location_dest_id': self.customer_location})

        with self.assertRaises(UserError):
            move_mto_alone._action_confirm()
        move_with_ancestors._action_confirm()
        other_move._action_confirm()

        move_mto_alone._do_unreserve()
        move_with_ancestors._do_unreserve()
        other_move._do_unreserve()

        self.assertEquals(move_mto_alone.state, "draft")
        self.assertEquals(move_with_ancestors.state, "waiting")
        self.assertEquals(other_move.state, "confirmed")

    def test_80_partial_picking_without_backorder(self):
        """ This test will create a picking with an initial demand for a product
        then process a lesser quantity than the expected quantity to be processed.
        When the wizard ask for a backorder, the 'NO BACKORDER' option will be selected
        and no backorder should be created afterwards
        """

        picking = self.PickingObj.create({
            'partner_id': self.partner_delta_id,
            'picking_type_id': self.picking_type_in,
            'location_id': self.supplier_location,
            'location_dest_id': self.stock_location})
        move_a = self.MoveObj.create({
            'name': self.productA.name,
            'product_id': self.productA.id,
            'product_uom_qty': 10,
            'product_uom': self.productA.uom_id.id,
            'picking_id': picking.id,
            'location_id': self.supplier_location,
            'location_dest_id': self.stock_location})

        picking.action_confirm()

        # Only 4 items are processed
        move_a.move_line_ids.qty_done = 4
        backorder_wizard = self.env['stock.backorder.confirmation'].create({'pick_ids': [(4, picking.id)]})
        backorder_wizard.process_cancel_backorder()

        # Checking that no backorders were attached to the picking
        self.assertFalse(picking.backorder_id)

        # Checking that the original move is still in the same picking
        self.assertEquals(move_a.picking_id.id, picking.id)

        move_lines = picking.move_lines
        move_done = move_lines.browse(move_a.id)
        move_canceled = move_lines - move_done

        # Checking that the original move was set to done
        self.assertEquals(move_done.product_uom_qty, 4)
        self.assertEquals(move_done.state, 'done')

        # Checking that the new move created was canceled
        self.assertEquals(move_canceled.product_uom_qty, 6)
        self.assertEquals(move_canceled.state, 'cancel')

        # Checking that the canceled move is in the original picking
        self.assertIn(move_canceled.id, picking.move_lines.mapped('id'))

    def test_transit_multi_companies(self):
        """ Ensure that inter company rules set the correct company on picking
        and their moves.
        """
        grp_multi_loc = self.env.ref('stock.group_stock_multi_locations')
        grp_multi_routes = self.env.ref('stock.group_adv_location')
        grp_multi_companies = self.env.ref('base.group_multi_company')
        self.env.user.write({'groups_id': [(4, grp_multi_loc.id)]})
        self.env.user.write({'groups_id': [(4, grp_multi_routes.id)]})
        self.env.user.write({'groups_id': [(4, grp_multi_companies.id)]})

        company_2 = self.company
        # Need to add a new company on user.
        self.env.user.write({'company_ids': [(4, company_2.id)]})

        warehouse_company_1 = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1)

        f = Form(self.env['stock.location.route'])
        f.name = 'From Company 1 to InterCompany'
        f.company_id = self.env.company
        with f.rule_ids.new() as rule:
            rule.name = 'From Company 1 to InterCompany'
            rule.action = 'pull'
            rule.picking_type_id = warehouse_company_1.in_type_id
            rule.location_src_id = self.env.ref('stock.stock_location_inter_wh')
            rule.procure_method = 'make_to_order'
        route_a = f.save()
        warehouse_company_2 = self.env['stock.warehouse'].search([('company_id', '=', company_2.id)], limit=1)
        f = Form(self.env['stock.location.route'])
        f.name = 'From InterCompany to Company 2'
        f.company_id = company_2
        with f.rule_ids.new() as rule:
            rule.name = 'From InterCompany to Company 2'
            rule.action = 'pull'
            rule.picking_type_id = warehouse_company_2.out_type_id
            rule.location_id = self.env.ref('stock.stock_location_inter_wh')
            rule.procure_method = 'make_to_stock'
        route_b = f.save()

        product = self.env['product.product'].create({
            'name': 'The product from the other company that I absolutely want',
            'type': 'product',
            'route_ids': [(4, route_a.id), (4, route_b.id)]
        })

        replenish_wizard = self.env['product.replenish'].create({
            'product_id': product.id,
            'product_tmpl_id': product.product_tmpl_id.id,
            'product_uom_id': self.uom_unit.id,
            'quantity': '5',
            'warehouse_id': warehouse_company_1.id,
        })
        replenish_wizard.launch_replenishment()
        incoming_picking = self.env['stock.picking'].search([('product_id', '=', product.id), ('picking_type_id', '=', warehouse_company_1.in_type_id.id)])
        outgoing_picking = self.env['stock.picking'].search([('product_id', '=', product.id), ('picking_type_id', '=', warehouse_company_2.out_type_id.id)])

        self.assertEqual(incoming_picking.company_id, self.env.company)
        self.assertEqual(incoming_picking.move_lines.company_id, self.env.company)
        self.assertEqual(outgoing_picking.company_id, company_2)
        self.assertEqual(outgoing_picking.move_lines.company_id, company_2)

    def test_transit_multi_companies_ultimate(self):
        """ Ensure that inter company rules set the correct company on picking
        and their moves. This test validate a picking with make_to_order moves.
        Moves are created in batch with a force_company. This test should create
        moves for company_2 and company_3 at the same time. Ensure they are not
        create in the same batch.
        """
        grp_multi_loc = self.env.ref('stock.group_stock_multi_locations')
        grp_multi_routes = self.env.ref('stock.group_adv_location')
        grp_multi_companies = self.env.ref('base.group_multi_company')
        self.env.user.write({'groups_id': [(4, grp_multi_loc.id)]})
        self.env.user.write({'groups_id': [(4, grp_multi_routes.id)]})
        self.env.user.write({'groups_id': [(4, grp_multi_companies.id)]})

        company_2 = self.company
        # Need to add a new company on user.
        self.env.user.write({'company_ids': [(4, company_2.id)]})

        warehouse_company_1 = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1)

        f = Form(self.env['stock.location.route'])
        f.name = 'From Company 1 to InterCompany'
        f.company_id = self.env.company
        with f.rule_ids.new() as rule:
            rule.name = 'From Company 1 to InterCompany'
            rule.action = 'pull'
            rule.picking_type_id = warehouse_company_1.in_type_id
            rule.location_src_id = self.env.ref('stock.stock_location_inter_wh')
            rule.procure_method = 'make_to_order'
        route_a = f.save()

        warehouse_company_2 = self.env['stock.warehouse'].search([('company_id', '=', company_2.id)], limit=1)
        f = Form(self.env['stock.location.route'])
        f.name = 'From InterCompany to Company 2'
        f.company_id = company_2
        with f.rule_ids.new() as rule:
            rule.name = 'From InterCompany to Company 2'
            rule.action = 'pull'
            rule.picking_type_id = warehouse_company_2.out_type_id
            rule.location_id = self.env.ref('stock.stock_location_inter_wh')
            rule.procure_method = 'make_to_stock'
        route_b = f.save()

        company_3 = self.env['res.company'].create({
            'name': 'Alaska Company'
        })

        warehouse_company_3 = self.env['stock.warehouse'].search([('company_id', '=', company_3.id)], limit=1)
        f = Form(self.env['stock.location.route'])
        f.name = 'From InterCompany to Company 3'
        f.company_id = company_3
        with f.rule_ids.new() as rule:
            rule.name = 'From InterCompany to Company 3'
            rule.action = 'pull'
            rule.picking_type_id = warehouse_company_3.out_type_id
            rule.location_id = self.env.ref('stock.stock_location_inter_wh')
            rule.procure_method = 'make_to_stock'
        route_c = f.save()

        product_from_company_2 = self.env['product.product'].create({
            'name': 'The product from the other company that I absolutely want',
            'type': 'product',
            'route_ids': [(4, route_a.id), (4, route_b.id)]
        })

        product_from_company_3 = self.env['product.product'].create({
            'name': 'Ice',
            'type': 'product',
            'route_ids': [(4, route_a.id), (4, route_c.id)]
        })

        f = Form(self.env['stock.picking'], view='stock.view_picking_form')
        f.picking_type_id = warehouse_company_1.out_type_id
        with f.move_ids_without_package.new() as move:
            move.product_id = product_from_company_2
            move.product_uom_qty = 5
        with f.move_ids_without_package.new() as move:
            move.product_id = product_from_company_3
            move.product_uom_qty = 5
        picking = f.save()

        picking.move_ids_without_package.write({'procure_method': 'make_to_order'})
        picking.action_confirm()

        incoming_picking = self.env['stock.picking'].search([('product_id', '=', product_from_company_2.id), ('picking_type_id', '=', warehouse_company_1.in_type_id.id)])
        outgoing_picking = self.env['stock.picking'].search([('product_id', '=', product_from_company_2.id), ('picking_type_id', '=', warehouse_company_2.out_type_id.id)])

        self.assertEqual(incoming_picking.company_id, self.env.company)
        self.assertEqual(incoming_picking.move_lines.mapped('company_id'), self.env.company)
        self.assertEqual(outgoing_picking.company_id, company_2)
        self.assertEqual(outgoing_picking.move_lines.company_id, company_2)

        incoming_picking = self.env['stock.picking'].search([('product_id', '=', product_from_company_3.id), ('picking_type_id', '=', warehouse_company_1.in_type_id.id)])
        outgoing_picking = self.env['stock.picking'].search([('product_id', '=', product_from_company_3.id), ('picking_type_id', '=', warehouse_company_3.out_type_id.id)])

        self.assertEqual(incoming_picking.company_id, self.env.company)
        self.assertEqual(incoming_picking.move_lines.mapped('company_id'), self.env.company)
        self.assertEqual(outgoing_picking.company_id, company_3)
        self.assertEqual(outgoing_picking.move_lines.company_id, company_3)
