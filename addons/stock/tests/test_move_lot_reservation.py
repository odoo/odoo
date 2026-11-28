# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.stock.tests.common import TestStockCommon


class TestMoveLotReservation(TestStockCommon):
    _test_user_groups = (
        'product.group_product_manager',
        'stock.group_stock_manager',
    )

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.group_ids += cls.env.ref('stock.group_production_lot')
        cls.product_lot = cls.env['product.product'].create({
            'name': 'Lot Tracked Product',
            'is_storable': True,
            'tracking': 'lot',
        })
        cls.lot_a, cls.lot_b = cls.env['stock.lot'].create([
            {'name': 'LOT-A', 'product_id': cls.product_lot.id},
            {'name': 'LOT-B', 'product_id': cls.product_lot.id},
        ])

    def _create_lot_move(self, location, location_dest, quantity):
        return self.env['stock.move'].create({
            'product_id': self.product_lot.id,
            'location_id': location.id,
            'location_dest_id': location_dest.id,
            'uom_id': self.product_lot.uom_id.id,
            'product_uom_qty': quantity,
        })

    def _set_stock(self, location, quantity, lot):
        self.env['stock.quant']._update_available_quantity(self.product_lot, location, quantity, lot_id=lot)

    def test_assign_lot_only_reserves_that_lot(self):
        """ The missing demand is only reserved on the given lot, never more than its stock. """
        self._set_stock(self.stock_location, 2, self.lot_a)
        self._set_stock(self.stock_location, 5, self.lot_b)
        move = self._create_lot_move(self.stock_location, self.customer_location, 4)
        move._action_confirm()

        move._action_assign(lot_id=self.lot_a)

        self.assertRecordValues(move.move_line_ids, [{'lot_id': self.lot_a.id, 'quantity': 2}])
        self.assertEqual(move.state, 'partially_available')
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product_lot, self.stock_location, lot_id=self.lot_b, strict=True), 5)

    def test_assign_lot_only_applies_to_the_call(self):
        """ A later reservation without lot takes any lot: the restriction is not stored. """
        self._set_stock(self.stock_location, 2, self.lot_a)
        self._set_stock(self.stock_location, 5, self.lot_b)
        move = self._create_lot_move(self.stock_location, self.customer_location, 4)
        move._action_confirm()
        move._action_assign(lot_id=self.lot_a)

        move._action_assign()

        self.assertRecordValues(move.move_line_ids, [
            {'lot_id': self.lot_a.id, 'quantity': 2},
            {'lot_id': self.lot_b.id, 'quantity': 2},
        ])
        self.assertEqual(move.state, 'assigned')

    def test_assign_lot_chained_move(self):
        """ A chained move only takes what its origin brought on the given lot. """
        self._set_stock(self.stock_location, 2, self.lot_a)
        self._set_stock(self.stock_location, 2, self.lot_b)
        move_pick = self._create_lot_move(self.stock_location, self.pack_location, 4)
        move_out = self._create_lot_move(self.pack_location, self.customer_location, 4)
        move_pick.move_dest_ids = move_out
        (move_pick + move_out)._action_confirm()
        move_pick._action_assign()
        move_pick.picked = True
        move_pick._action_done()
        move_out._do_unreserve()

        move_out._action_assign(lot_id=self.lot_a)

        self.assertRecordValues(move_out.move_line_ids, [{'lot_id': self.lot_a.id, 'quantity': 2}])
        self.assertEqual(move_out.state, 'partially_available')

    def test_assign_lot_bypass_reservation(self):
        """ Without reservation (e.g. a receipt), the created move lines get the given lot. """
        move = self._create_lot_move(self.supplier_location, self.stock_location, 3)
        move._action_confirm()
        move._do_unreserve()

        move._action_assign(lot_id=self.lot_a)

        self.assertRecordValues(move.move_line_ids, [{'lot_id': self.lot_a.id, 'quantity': 3}])
        self.assertEqual(move.state, 'assigned')

    def test_assign_lot_misuse(self):
        move = self._create_lot_move(self.stock_location, self.customer_location, 4)
        other_lot = self.env['stock.lot'].create({'name': 'OTHER', 'product_id': self.productA.id})
        move._action_confirm()
        with self.assertRaises(ValueError):
            move._action_assign(lot_id=other_lot)
        with self.assertRaises(ValueError):
            move._action_assign(force_qty=1, lot_id=self.lot_a)

    def test_force_lot_quantity(self):
        """ The remainder the stock cannot cover is forced on the lot, other lots stay untouched. """
        self._set_stock(self.stock_location, 2, self.lot_a)
        self._set_stock(self.stock_location, 5, self.lot_b)
        move = self._create_lot_move(self.stock_location, self.customer_location, 5)
        move._action_confirm()

        move._force_lot_quantity(self.lot_a)

        self.assertRecordValues(move.move_line_ids, [{'lot_id': self.lot_a.id, 'quantity': 5}])
        self.assertEqual(move.state, 'assigned')
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product_lot, self.stock_location, lot_id=self.lot_b, strict=True), 5)

    def test_force_lot_quantity_several_lots(self):
        """ A move fulfilled from several lots gets the given quantity on each lot. """
        self._set_stock(self.stock_location, 2, self.lot_a)
        self._set_stock(self.stock_location, 5, self.lot_b)
        move = self._create_lot_move(self.stock_location, self.customer_location, 5)
        move._action_confirm()

        move._force_lot_quantity(self.lot_a, quantity=3)
        move._force_lot_quantity(self.lot_b, quantity=2)

        self.assertRecordValues(move.move_line_ids, [
            {'lot_id': self.lot_a.id, 'quantity': 3},
            {'lot_id': self.lot_b.id, 'quantity': 2},
        ])
        self.assertEqual(move.state, 'assigned')
