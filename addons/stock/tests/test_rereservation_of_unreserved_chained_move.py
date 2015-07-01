from openerp.addons.stock.tests.common import TestStockCommon


class TestChainedMoveRereservation(TestStockCommon):

    def setUp(self):
        super(TestChainedMoveRereservation, self).setUp()

        self.productA.type = 'product'

        self.picking_out = self.env['stock.picking'].create({
            'picking_type_id': self.ref('stock.picking_type_out')})
        self.move_MTS = self.env['stock.move'].create({
            'name': 'a move',
            'state': 'assigned',  # Available
            'product_id': self.productA.id,
            'product_uom_qty': 5.0,
            'product_uom': self.productA.uom_id.id,
            'picking_id': self.picking_out.id,
            'location_id': self.stock_location,
            'location_dest_id': self.customer_location})
        self.move_MTO = self.env['stock.move'].create({
            'name': 'b move',
            'state': 'assigned',  # Available
            'procure_method': 'make_to_order',  # MTO move
            'product_id': self.productA.id,
            'product_uom_qty': 2.0,
            'product_uom': self.productA.uom_id.id,
            'picking_id': self.picking_out.id,
            'location_id': self.stock_location,
            'location_dest_id': self.customer_location})

        self.move_MTO_source = self.env['stock.move'].create({
            'name': 'c move',
            'product_id': self.productA.id,
            'product_uom_qty': 2.0,
            'product_uom': self.productA.uom_id.id,
            'location_id': self.supplier_location,
            'location_dest_id': self.stock_location,
            'state': 'done',
            'move_dest_id': self.move_MTO.id})  # chain: move_MTO_source -> move_MTO

        self.earliest_quant = self.env['stock.quant'].create({
            'product_id': self.productA.id,
            'location_id': self.stock_location,
            'qty': 2.0,
            'reservation_id': self.move_MTO.id,  # move_MTO was reserved before move_MTS (earliest_quant)
            'history_ids': [(6, False, [self.move_MTO_source.id])]})  # move_MTO_source belongs to quant's history
        self.latest_quant = self.env['stock.quant'].create({
            'product_id': self.productA.id,
            'location_id': self.stock_location,
            'qty': 5.0,
            'reservation_id': self.move_MTS.id})  # move_MTS was reserved after move_MTO (latest_quant)

    def test_rereservation_of_unreserved_MTO_move_after_it_was_manually_changed_to_MTS(self):
        """ Unreserved MTO move whose quants were overtaken by some other move should only be re-reserved again if
        the user decides it is OK for this MTO to re-reserve from stock and user switches the move manually to MTS.
        """
        self.assertEquals(2, self.env['stock.quant'].search_count([('product_id', '=', self.productA.id)]))
        self.assertAlmostEqual(5.0, self.move_MTS.reserved_availability)
        self.assertAlmostEqual(2.0, self.move_MTO.reserved_availability)

        # Unreserve move_MTO, exposing its quant to reservation by other moves (e.g. deliberately, for urgent orders)
        self.move_MTO.do_unreserve()
        # Re-check availability after a while.
        self.picking_out.rereserve_pick()
        # Re-checking of picking does the following:
        # 1) drop reservation for the whole picking (both MTS and MTO)
        # 2) MTO's quant (earliest_quant) is this time reserved by MTS (first move in picking) due to FIFO strategy
        # 3) MTO remains forever unreserved, for its allowed quants are restricted to their history now overtaken by MTS
        self.assertAlmostEqual(5.0, self.move_MTS.reserved_availability)
        self.assertAlmostEqual(0.0, self.move_MTO.reserved_availability)

        # When MTS was reserving MTO's quant, it first reserved the earliest_quant (2.0) and then
        # has split 5.0 quant into 3.0 and 2.0. Let's check this:
        updated_quants = self.env['stock.quant'].search([('product_id', '=', self.productA.id)])
        updated_quants = sorted([q for q in updated_quants], key=lambda x: x.qty)
        self.assertEquals(3, len(updated_quants))
        self.assertAlmostEqual(2.0, updated_quants[0].qty)
        self.assertAlmostEqual(2.0, updated_quants[1].qty)
        self.assertAlmostEqual(3.0, updated_quants[2].qty)

        # Manually change MTO => MTS
        self.move_MTO.procure_method = 'make_to_stock'

        # Now MTO should be successfully re-reserved
        self.picking_out.rereserve_pick()
        self.assertAlmostEqual(5.0, self.move_MTS.reserved_availability)
        self.assertAlmostEqual(2.0, self.move_MTO.reserved_availability)

    def test_automatic_rereservation_of_unreserved_chained_MTS(self):
        """ Contrary to MTO, when a chained MTS is unreserved it should be automatically rereserved on the next scheduler
        run or on manual check for availability - i.e. no user interaction is needed to change move's state to MTS.
        It is because MTS was initially set as MTS that it is assumed auto-reserving from stock should be OK, even
        despite being a chained move - main thing is that the move will reserve in the location it was chained from.
        """
        # Let's turn move_MTO into a chained MTS:
        self.move_MTO.procure_method = 'make_to_stock'
        self.move_MTS_chained = self.move_MTO

        self.assertEquals(2, self.env['stock.quant'].search_count([('product_id', '=', self.productA.id)]))
        self.assertAlmostEqual(5.0, self.move_MTS.reserved_availability)
        self.assertAlmostEqual(2.0, self.move_MTS_chained.reserved_availability)

        # Unreserve move_MTS_chained, exposing its quant to reservation by other moves (e.g. deliberately)
        self.move_MTS_chained.do_unreserve()
        # Re-check availability after a while.
        self.picking_out.rereserve_pick()
        # Re-checking of picking does the following:
        # 1) drop reservation for the whole picking (both MTS and MTS_chained)
        # 2) MTS_chained's quant (earliest_quant) is this time reserved by MTS (first move in picking) due to FIFO
        # 3) MTS_chained is re-reserved automatically (w/o user interaction), for it is already in MTS state
        self.assertAlmostEqual(5.0, self.move_MTS.reserved_availability)
        self.assertAlmostEqual(2.0, self.move_MTS_chained.reserved_availability)
