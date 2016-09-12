# coding: utf-8
from openerp.tests.common import TransactionCase


class TestDummyStockTest(TransactionCase):

    def setUp(self):
        super(TestDummyStockTest, self).setUp()
        self.move = self.env['stock.move']
        self.quant = self.env['stock.quant']
        self.prod = self.env.ref('stock_dummy_test.'
                                 'product_product_19')
        self.stock = self.env.ref('stock.stock_location_stock')
        self.production = self.env.ref('stock.location_production')
        self.supplier = self.env.ref('stock.location_production')
        self.customer = self.env.ref('stock.stock_location_customers')

    def create_move(self, src_location, dest_loctation, qty):
        """Create the moves in specific location
        to validate the quants used and moved to
        verify expected behavior

        @param src_location: Source location where the product will be moved
        @type src_location: integer
        @param dest_location: Destiny location where the product will be
                              received
        @type dest_location: integer
        @param qty: Quantity of product that you want to move
        @type qty: float

        @return: New move created
        @rtpy: stock_move RecordSet
        """
        values = self.move.onchange_product_id(prod_id=self.prod.id,
                                               loc_id=src_location,
                                               loc_dest_id=dest_loctation)
        values = values.get('value')
        uos_id = self.prod.uos_id and self.prod.uos_id.id or False
        values.update({
            'product_id': self.prod.id,
            'product_uom_qty': qty,
            'product_uos_qty': self.move.
                      onchange_quantity(self.prod.id, qty,
                                        self.prod.uom_id.id,
                                        uos_id)['value']
                      ['product_uos_qty']})
        return self.move.create(values)

    def verify_locations_and_quantities(self, quants, quantities, locations):
        """Verify the location and the quantity of the quants sent
        @param quants: Quants to verify their locations and quantities
        @type quants: stock_quant RecordSet
        @param quantites: Quantities
        @type quantites: lits or tuple
        @param locations:A Locations that the quants must have
        @type locations: lits or tuple
        """
        for quant in quants:
            self.assertIn(quant.qty, quantities,
                          'The quantities are not the '
                          'corresponding for the move made')
            self.assertIn(quant.location_id.id,
                          locations,
                          'The location for the quant is not '
                          'according to the move made')

    def test_01_normal_moves(self):
        """Test to verify the normal behavior for moves from different types of
        locations
        """
        # Creating first move between stock and customer locations
        move_brw = self.create_move(self.stock.id, self.customer.id,
                                    4)

        # Searching the current quant before to validate the firs move
        current_quant = self.quant.\
            search([('product_id', '=', self.prod.id)])

        # Validating the number of quant found and its quantity
        self.assertEqual(len(current_quant), 1,
                         'There are more than one quant '
                         'in stock for this product')
        self.assertEqual(current_quant.qty, 12,
                         'The quantity in stock for this '
                         'product is different to initial inventory created')

        # Validating move
        move_brw.action_done()

        # Searching the current quant
        current_quants = self.quant.\
            search([('product_id', '=', self.prod.id)])

        # Validating the number of quants found and
        self.assertEqual(len(current_quants), 2,
                         'There are more than one quant '
                         'in stock for this product')

        # Checking the quantities and locations in the quants
        self.verify_locations_and_quantities(current_quants, (4, 8),
                                             (self.stock.id, self.customer.id))

        # Move from supplier to stock to create new quant
        move_brw = self.create_move(self.supplier.id, self.stock.id,
                                    6)
        # Validating move
        move_brw.action_done()

        # Searching the current quant
        current_quants = self.quant.\
            search([('product_id', '=', self.prod.id)])

        # Validating the number of quants found and
        self.assertEqual(len(current_quants), 3,
                         'There are more than one quant '
                         'in stock for this product')

        # Checking the quantities and locations in the quants
        self.verify_locations_and_quantities(current_quants, (4, 8, 6),
                                             (self.stock.id, self.customer.id))

        # Move from stock to customer to verify the FIFO
        move_brw = self.create_move(self.stock.id, self.customer.id,
                                    9)
        # Validating move
        move_brw.action_done()

        # Searching the current quant
        current_quants = self.quant.\
            search([('product_id', '=', self.prod.id)])

        # Validating the number of quants found and
        self.assertEqual(len(current_quants), 4,
                         'There are more than one quant '
                         'in stock for this product')

        # Checking the quantities and locations in the quants
        self.verify_locations_and_quantities(current_quants, (4, 8, 1, 5),
                                             (self.stock.id, self.customer.id))

        # Move from stock to production
        move_brw = self.create_move(self.stock.id, self.production.id,
                                    2)
        # Validating move
        move_brw.action_done()

        # Searching the current quant
        current_quants = self.quant.\
            search([('product_id', '=', self.prod.id)])

        # Validating the number of quants found and
        self.assertEqual(len(current_quants), 5,
                         'There are more than one quant '
                         'in stock for this product')

        # Checking the quantities and locations in the quants
        self.verify_locations_and_quantities(current_quants, (4, 8, 1, 2, 3),
                                             (self.stock.id, self.customer.id,
                                              self.production.id))

        # Move from production to stock
        move_brw = self.create_move(self.production.id, self.stock.id,
                                    2)
        # Validating move
        move_brw.action_done()

        # Searching the current quant
        current_quants = self.quant.\
            search([('product_id', '=', self.prod.id)])

        # Validating the number of quants found and
        self.assertEqual(len(current_quants), 6,
                         'There are more than one quant '
                         'in stock for this product')

        # Checking the quantities and locations in the quants
        self.verify_locations_and_quantities(current_quants, (4, 8, 1, 2, 3),
                                             (self.stock.id, self.customer.id,
                                              self.production.id))

        # Move from stock to customer with negative quant
        move_brw = self.create_move(self.stock.id, self.customer.id,
                                    8)
        # Validating move
        move_brw.action_done()

        # Searching the current quant
        current_quants = self.quant.\
            search([('product_id', '=', self.prod.id)])

        # Validating the number of quants found and
        self.assertEqual(len(current_quants), 8,
                         'There are more than one quant '
                         'in stock for this product')

        # Checking the quantities and locations in the quants
        self.verify_locations_and_quantities(current_quants,
                                             (4, 8, 1, 2, 3, -3),
                                             (self.stock.id, self.customer.id,
                                              self.production.id))

    def test_02_set_quants(self):
        """Test to verify if the specified quant is used and moved
        """
        # Creating first move between stock and customer locations
        move_brw = self.create_move(self.stock.id, self.production.id,
                                    1)

        # Searching the current quant before to validate the firs move
        current_quant = self.quant.\
            search([('product_id', '=', self.prod.id)])

        # Validating the number of quant found and its quantity
        self.assertEqual(len(current_quant), 1,
                         'There are more than one quant '
                         'in stock for this product')
        self.assertEqual(current_quant.qty, 12,
                         'The quantity in stock for this '
                         'product is different to initial inventory created')

        # Validating move
        move_brw.action_done()

        # Searching the current quant
        current_quants = self.quant.\
            search([('product_id', '=', self.prod.id)])

        # Validating the number of quants found and
        self.assertEqual(len(current_quants), 2,
                         'There are more than one quant '
                         'in stock for this product')

        # Checking the quantities and locations in the quants
        self.verify_locations_and_quantities(current_quants, (1, 11),
                                             (self.stock.id,
                                              self.production.id))

        quant_moved = current_quants.\
            filtered(lambda a: a.location_id.id == self.production.id)

        # Validating that we only have one move in production
        self.assertEqual(len(quant_moved), 1,
                         'There are more than one quant '
                         'in production for this product')

        # Move from production to stock to create new quant
        move_brw = self.create_move(self.production.id, self.stock.id,
                                    1)
        # Validating move with specific quant
        move_brw.with_context({'force_quant': [(quant_moved, 1)]}).\
            action_done()

        # Searching the current quant
        current_quants = self.quant.\
            search([('product_id', '=', self.prod.id)])

        # Validating the number of quants found and
        self.assertEqual(len(current_quants), 2,
                         'There are more than one quant '
                         'in stock for this product')

        # Validating the the quant sent in the context was used
        self.assertIn(quant_moved.id, current_quants.ids,
                      'The quant moved before was not used for the '
                      'move validated before')
