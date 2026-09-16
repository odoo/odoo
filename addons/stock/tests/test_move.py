from dateutil.relativedelta import relativedelta
from freezegun import freeze_time

from odoo import Command, fields
from odoo.exceptions import UserError
from odoo.tests import Form, new_test_user

from odoo.addons.stock.tests.common import TestStockCommon


def _aggregated(aggregate_values, key):
    matches = [
        value
        for line_key, value in aggregate_values.items()
        if line_key == key or line_key.startswith(key + "_")
    ]
    assert len(matches) == 1, (key, list(aggregate_values))
    return matches[0]


class TestStockMove(TestStockCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        group_stock_multi_locations = cls.env.ref("stock.group_stock_multi_locations")
        group_production_lot = cls.env.ref("stock.group_production_lot")
        cls.env.user.write(
            {
                "group_ids": [
                    (4, group_stock_multi_locations.id),
                    (4, group_production_lot.id),
                ]
            }
        )
        cls.product_serial = cls.env["product.product"].create(
            {
                "name": "Product A",
                "is_storable": True,
                "tracking": "serial",
            }
        )
        cls.product_lot = cls.env["product.product"].create(
            {
                "name": "Product A",
                "is_storable": True,
                "tracking": "lot",
            }
        )
        cls.product_consu = cls.env["product.product"].create(
            {
                "name": "Product A",
                "type": "consu",
            }
        )
        cls.partner_2 = cls.env["res.partner"].create({"name": "Partner 2"})
        cls.picking_type_out.reservation_method = "at_confirm"

    def gather_relevant(
        self,
        product_id,
        location_id,
        lot_id=None,
        package_id=None,
        owner_id=None,
        strict=False,
    ):
        quants = self.env["stock.quant"]._gather(
            product_id,
            location_id,
            lot_id=lot_id,
            package_id=package_id,
            owner_id=owner_id,
            strict=strict,
        )
        return quants.filtered(
            lambda q: not (q.quantity == 0 and q.reserved_quantity == 0)
        )

    def test_set_lot_ids_on_several_moves(self):
        lot_a = self.env["stock.lot"].create(
            {"product_id": self.product_lot.id, "name": "REG-LOT-A"}
        )
        lot_b = self.env["stock.lot"].create(
            {"product_id": self.product_lot.id, "name": "REG-LOT-B"}
        )
        self.env["stock.quant"]._update_available_quantity(
            self.product_lot, self.stock_location, 50, lot_id=lot_a
        )
        self.env["stock.quant"]._update_available_quantity(
            self.product_lot, self.stock_location, 50, lot_id=lot_b
        )

        def _confirmed_out_move():
            move = self.env["stock.move"].create(
                {
                    "location_id": self.stock_location.id,
                    "location_dest_id": self.customer_location.id,
                    "product_id": self.product_lot.id,
                    "product_uom_id": self.uom_unit.id,
                    "product_uom_qty": 5.0,
                }
            )
            move._action_confirm()
            move._action_assign()
            return move

        moves = _confirmed_out_move() | _confirmed_out_move()

        moves.write({"lot_ids": [(4, lot_a.id), (4, lot_b.id)]})

        for move in moves:
            self.assertEqual(set(move.move_line_ids.lot_id.ids), {lot_a.id, lot_b.id})
            self.assertAlmostEqual(move.quantity, move._get_move_line_quantity())

    def test_in_1(self):
        move1 = self.env["stock.move"].create(
            {
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 100.0,
            }
        )
        self.assertEqual(move1.state, "draft")

        move1._action_confirm()
        self.assertEqual(move1.state, "assigned")
        self.assertEqual(len(move1.move_line_ids), 1)

        move_line = move1.move_line_ids[0]
        self.assertEqual(move_line.quantity_product_uom, 100.0)
        self.assertEqual(move_line.quantity, 100.0)

        move1.picked = True
        move1._action_done()
        self.assertEqual(move1.state, "done")
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.supplier_location
            ),
            0.0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.supplier_location, allow_negative=True
            ),
            -100.0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location
            ),
            100.0,
        )
        self.assertEqual(
            len(self.gather_relevant(self.productA, self.supplier_location)), 1.0
        )
        self.assertEqual(
            len(self.gather_relevant(self.productA, self.stock_location)), 1.0
        )

    def test_in_2(self):
        move1 = self.env["stock.move"].create(
            {
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
                "product_id": self.product_lot.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 5.0,
                "picking_type_id": self.picking_type_in.id,
            }
        )
        self.assertEqual(move1.state, "draft")

        move1._action_confirm()
        self.assertEqual(move1.state, "assigned")
        self.assertEqual(len(move1.move_line_ids), 1)
        move_line = move1.move_line_ids[0]
        self.assertEqual(move_line.quantity_product_uom, 5)
        move_line.lot_name = "lot1"
        move_line.picked = True
        self.assertEqual(move_line.quantity_product_uom, 5)

        move1.picked = True
        move1._action_done()
        self.assertEqual(move_line.quantity_product_uom, 5)
        self.assertEqual(move_line.state, "done")
        self.assertEqual(move1.state, "done")

        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.product_lot, self.supplier_location
            ),
            0.0,
        )
        supplier_quants = self.gather_relevant(self.product_lot, self.supplier_location)
        self.assertEqual(sum(supplier_quants.mapped("quantity")), -5.0)

        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.product_lot, self.stock_location
            ),
            5.0,
        )
        self.assertEqual(
            len(self.gather_relevant(self.product_lot, self.supplier_location)), 1.0
        )
        quants = self.gather_relevant(self.product_lot, self.stock_location)
        self.assertEqual(len(quants), 1.0)
        for quant in quants:
            self.assertNotEqual(quant.in_date, False)

    def test_in_3(self):
        move1 = self.env["stock.move"].create(
            {
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
                "product_id": self.product_serial.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 5.0,
                "picking_type_id": self.picking_type_in.id,
            }
        )
        self.assertEqual(move1.state, "draft")

        move1._action_confirm()
        self.assertEqual(move1.state, "assigned")
        self.assertEqual(len(move1.move_line_ids), 5)
        move_line = move1.move_line_ids[0]
        self.assertEqual(move1.quantity, 5)

        for i, move_line in enumerate(move1.move_line_ids):
            move_line.lot_name = "sn%s" % i
            move_line.quantity = 1
        self.assertEqual(move1.quantity, 5.0)
        self.assertEqual(move1.product_qty, 5)

        move1.picked = True
        move1._action_done()

        self.assertEqual(move1.quantity, 5.0)
        self.assertEqual(move1.product_qty, 5)
        self.assertEqual(move1.state, "done")

        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.product_serial, self.supplier_location
            ),
            0.0,
        )
        supplier_quants = self.gather_relevant(
            self.product_serial, self.supplier_location
        )
        self.assertEqual(sum(supplier_quants.mapped("quantity")), -5.0)
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.product_serial, self.stock_location
            ),
            5.0,
        )

        self.assertEqual(
            len(self.gather_relevant(self.product_serial, self.supplier_location)), 5.0
        )
        quants = self.gather_relevant(self.product_serial, self.stock_location)
        self.assertEqual(len(quants), 5.0)
        for quant in quants:
            self.assertNotEqual(quant.in_date, False)

    def test_out_1(self):
        self.env["stock.quant"]._update_available_quantity(
            self.productA, self.stock_location, 100
        )
        self.assertEqual(
            len(self.gather_relevant(self.productA, self.stock_location)), 1.0
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location
            ),
            100.0,
        )

        move1 = self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 100.0,
            }
        )
        self.assertEqual(move1.state, "draft")

        move1._action_confirm()
        self.assertEqual(move1.state, "confirmed")

        move1._action_assign()
        self.assertEqual(move1.state, "assigned")
        self.assertEqual(len(move1.move_line_ids), 1)
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location
            ),
            0.0,
        )
        self.assertEqual(
            len(self.gather_relevant(self.productA, self.stock_location)), 1.0
        )

        move_line = move1.move_line_ids[0]
        self.assertEqual(move_line.quantity_product_uom, 100.0)
        self.assertEqual(move_line.quantity, 100.0)

        move1.picked = True
        move1._action_done()
        self.assertEqual(move1.state, "done")
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.customer_location
            ),
            100.0,
        )
        self.assertEqual(
            len(self.gather_relevant(self.productA, self.customer_location)), 1.0
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location
            ),
            0.0,
        )
        self.assertEqual(
            len(self.gather_relevant(self.productA, self.stock_location)), 0.0
        )

    def test_out_2(self):
        self.productA.is_storable = False
        self.assertEqual(
            len(self.gather_relevant(self.productA, self.stock_location)), 0.0
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location
            ),
            0.0,
        )

        move1 = self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 100.0,
            }
        )
        self.assertEqual(move1.state, "draft")

        move1._action_confirm()
        self.assertEqual(move1.state, "assigned")
        self.assertEqual(len(move1.move_line_ids), 1)
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location
            ),
            0.0,
        )
        self.assertEqual(
            len(self.gather_relevant(self.productA, self.stock_location)), 0.0
        )

        move_line = move1.move_line_ids[0]
        self.assertEqual(move_line.quantity_product_uom, 100.0)
        self.assertEqual(move_line.quantity, 100.0)

        move1.picked = True
        move1._action_done()
        self.assertEqual(move1.state, "done")
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.customer_location
            ),
            0.0,
        )
        self.assertEqual(
            len(self.gather_relevant(self.productA, self.customer_location)), 0.0
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location
            ),
            0.0,
        )
        self.assertEqual(
            len(self.gather_relevant(self.productA, self.stock_location)), 0.0
        )

    def test_out_3(self):
        productA, productB, productC = self.env["product.product"].create(
            [
                {"name": "Product A", "is_storable": True},
                {"name": "Product B", "is_storable": True},
                {"name": "Product C (out of stock)", "is_storable": True},
            ]
        )
        self.env["stock.quant"]._update_available_quantity(
            productA, self.stock_location, 1
        )
        self.env["stock.quant"]._update_available_quantity(
            productB, self.stock_location, 1
        )

        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": self.picking_type_out.id,
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "move_type": "one",
                "move_ids": [
                    Command.create(
                        {
                            "product_id": productA.id,
                            "product_uom_id": self.uom_unit.id,
                            "product_uom_qty": 1.0,
                            "location_id": self.stock_location.id,
                            "location_dest_id": self.customer_location.id,
                        }
                    ),
                    Command.create(
                        {
                            "product_id": productB.id,
                            "product_uom_id": self.uom_unit.id,
                            "product_uom_qty": 1.0,
                            "location_id": self.stock_location.id,
                            "location_dest_id": self.customer_location.id,
                        }
                    ),
                    Command.create(
                        {
                            "product_id": productC.id,
                            "product_uom_id": self.uom_unit.id,
                            "product_uom_qty": 1.0,
                            "location_id": self.stock_location.id,
                            "location_dest_id": self.customer_location.id,
                        }
                    ),
                ],
            }
        )
        move1, move2, move3 = picking.move_ids
        self.assertEqual(move1.state, "draft")
        self.assertEqual(move2.state, "draft")
        self.assertEqual(move3.state, "draft")
        picking.action_confirm()
        picking.action_assign()
        self.assertEqual(move1.state, "assigned")
        self.assertEqual(move2.state, "assigned")
        self.assertEqual(move3.state, "confirmed")
        self.assertEqual(picking.state, "confirmed")
        move1.product_uom_qty = 0
        self.assertEqual(move1.state, "confirmed")
        self.assertEqual(move2.state, "assigned")
        self.assertEqual(move3.state, "confirmed")
        self.assertEqual(picking.state, "confirmed")

    def test_mixed_tracking_reservation_1(self):
        lot1 = self.env["stock.lot"].create(
            {
                "name": "lot1",
                "product_id": self.product_lot.id,
            }
        )
        self.env["stock.quant"]._update_available_quantity(
            self.product_lot, self.stock_location, 2
        )
        self.env["stock.quant"]._update_available_quantity(
            self.product_lot, self.stock_location, 3, lot_id=lot1
        )

        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.product_lot, self.stock_location
            ),
            5.0,
        )
        move1 = self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "product_id": self.product_lot.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 5.0,
            }
        )
        move1._action_confirm()
        move1._action_assign()

        self.assertEqual(len(move1.move_line_ids), 2)

    def test_mixed_tracking_reservation_2(self):
        lot1 = self.env["stock.lot"].create(
            {
                "name": "lot1",
                "product_id": self.product_serial.id,
            }
        )
        lot2 = self.env["stock.lot"].create(
            {
                "name": "lot2",
                "product_id": self.product_serial.id,
            }
        )
        self.env["stock.quant"]._update_available_quantity(
            self.product_serial, self.stock_location, 2
        )
        self.env["stock.quant"]._update_available_quantity(
            self.product_serial, self.stock_location, 1, lot_id=lot1
        )
        self.env["stock.quant"]._update_available_quantity(
            self.product_serial, self.stock_location, 1, lot_id=lot2
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.product_serial, self.stock_location
            ),
            4.0,
        )
        picking = self.env["stock.picking"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "picking_type_id": self.picking_type_out.id,
                "state": "draft",
            }
        )

        move1 = self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "product_id": self.product_serial.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 4.0,
                "picking_id": picking.id,
            }
        )
        move1._action_confirm()
        move1._action_assign()
        self.assertEqual(len(move1.move_line_ids), 4)
        for ml in move1.move_line_ids:
            self.assertEqual(ml.quantity_product_uom, 1.0)

        lot3 = self.env["stock.lot"].create(
            {
                "name": "lot3",
                "product_id": self.product_serial.id,
            }
        )
        lot4 = self.env["stock.lot"].create(
            {
                "name": "lot4",
                "product_id": self.product_serial.id,
            }
        )
        untracked_move_line = move1.move_line_ids.filtered(lambda ml: not ml.lot_id)
        untracked_move_line[0].lot_id = lot3
        untracked_move_line[1].lot_id = lot4
        for ml in move1.move_line_ids:
            self.assertEqual(ml.quantity_product_uom, 1.0)

        self.assertEqual(
            len(
                self.gather_relevant(
                    self.product_serial, self.stock_location, strict=True
                )
            ),
            1.0,
        )
        self.assertEqual(
            len(
                self.gather_relevant(
                    self.product_serial, self.stock_location, lot_id=lot1, strict=True
                ).filtered(lambda q: q.lot_id)
            ),
            1.0,
        )
        self.assertEqual(
            len(
                self.gather_relevant(
                    self.product_serial, self.stock_location, lot_id=lot2, strict=True
                ).filtered(lambda q: q.lot_id)
            ),
            1.0,
        )
        self.assertEqual(
            len(
                self.gather_relevant(
                    self.product_serial, self.stock_location, lot_id=lot3, strict=True
                ).filtered(lambda q: q.lot_id)
            ),
            0,
        )
        self.assertEqual(
            len(
                self.gather_relevant(
                    self.product_serial, self.stock_location, lot_id=lot4, strict=True
                ).filtered(lambda q: q.lot_id)
            ),
            0,
        )

        move1.move_line_ids.write({"quantity": 1.0})
        move1.picked = True
        move1._action_done()

        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.product_serial, self.stock_location
            ),
            0.0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.product_serial, self.stock_location, lot_id=lot1, strict=True
            ),
            0.0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.product_serial, self.stock_location, lot_id=lot2, strict=True
            ),
            0.0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.product_serial, self.stock_location, lot_id=lot3, strict=True
            ),
            0.0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.product_serial, self.stock_location, lot_id=lot4, strict=True
            ),
            0.0,
        )

    def test_mixed_tracking_reservation_3(self):
        lot1 = self.env["stock.lot"].create(
            {
                "name": "lot1",
                "product_id": self.product_serial.id,
            }
        )
        lot2 = self.env["stock.lot"].create(
            {
                "name": "lot2",
                "product_id": self.product_serial.id,
            }
        )
        self.env["stock.quant"]._update_available_quantity(
            self.product_serial, self.stock_location, 1, lot_id=lot1
        )
        self.env["stock.quant"]._update_available_quantity(
            self.product_serial, self.stock_location, 1, lot_id=lot2
        )

        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.product_serial, self.stock_location
            ),
            2.0,
        )
        move1 = self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "product_id": self.product_serial.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 2.0,
            }
        )
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.write({"quantity": 1.0})
        move1.picked = True
        move1._action_done()

        self.env["stock.quant"]._update_available_quantity(
            self.product_serial, self.stock_location, 2
        )
        lot3 = self.env["stock.lot"].create(
            {
                "name": "lot3",
                "product_id": self.product_serial.id,
            }
        )
        lot4 = self.env["stock.lot"].create(
            {
                "name": "lot4",
                "product_id": self.product_serial.id,
            }
        )

        self.env["stock.move.line"].create(
            {
                "move_id": move1.id,
                "product_id": move1.product_id.id,
                "quantity": 1,
                "product_uom_id": move1.product_uom_id.id,
                "location_id": move1.location_id.id,
                "location_dest_id": move1.location_dest_id.id,
                "lot_id": lot3.id,
            }
        )
        self.env["stock.move.line"].create(
            {
                "move_id": move1.id,
                "product_id": move1.product_id.id,
                "quantity": 1,
                "product_uom_id": move1.product_uom_id.id,
                "location_id": move1.location_id.id,
                "location_dest_id": move1.location_dest_id.id,
                "lot_id": lot4.id,
            }
        )

        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.product_serial, self.stock_location
            ),
            0.0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.product_serial, self.stock_location, lot_id=lot1, strict=True
            ),
            0.0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.product_serial, self.stock_location, lot_id=lot2, strict=True
            ),
            0.0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.product_serial, self.stock_location, lot_id=lot3, strict=True
            ),
            0.0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.product_serial, self.stock_location, lot_id=lot4, strict=True
            ),
            0.0,
        )

    def test_mixed_tracking_reservation_4(self):
        lot1 = self.env["stock.lot"].create(
            {
                "name": "lot1",
                "product_id": self.product_serial.id,
            }
        )
        lot2 = self.env["stock.lot"].create(
            {
                "name": "lot2",
                "product_id": self.product_serial.id,
            }
        )
        self.env["stock.quant"]._update_available_quantity(
            self.product_serial, self.stock_location, 1, lot_id=lot1
        )
        self.env["stock.quant"]._update_available_quantity(
            self.product_serial, self.stock_location, 1, lot_id=lot2
        )

        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.product_serial, self.stock_location
            ),
            2.0,
        )
        move1 = self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "product_id": self.product_serial.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 2.0,
            }
        )
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.write({"quantity": 1.0})
        move1.picked = True
        move1._action_done()

        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.product_serial, self.stock_location
            ),
            0.0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.product_serial, self.stock_location, lot_id=lot1, strict=True
            ),
            0.0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.product_serial, self.stock_location, lot_id=lot2, strict=True
            ),
            0.0,
        )

        self.env["stock.quant"]._update_available_quantity(
            self.product_serial, self.stock_location, 1
        )
        lot3 = self.env["stock.lot"].create(
            {
                "name": "lot3",
                "product_id": self.product_serial.id,
            }
        )

        move1.move_line_ids[1].lot_id = lot3

        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.product_serial, self.stock_location
            ),
            1.0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.product_serial, self.stock_location, lot_id=lot1, strict=True
            ),
            0.0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.product_serial, self.stock_location, lot_id=lot2, strict=True
            ),
            1.0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.product_serial, self.stock_location, lot_id=lot3, strict=True
            ),
            0.0,
        )

    def test_mixed_tracking_reservation_5(self):
        move1 = self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "product_id": self.product_serial.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 1.0,
            }
        )
        move1._action_confirm()
        move1._action_assign()
        self.assertEqual(move1.state, "confirmed")

        self.env["stock.quant"]._update_available_quantity(
            self.product_serial, self.stock_location, 1.0
        )
        lot1 = self.env["stock.lot"].create(
            {
                "name": "lot1",
                "product_id": self.product_serial.id,
            }
        )

        self.env["stock.move.line"].create(
            {
                "move_id": move1.id,
                "product_id": move1.product_id.id,
                "quantity": 1,
                "product_uom_id": move1.product_uom_id.id,
                "location_id": move1.location_id.id,
                "location_dest_id": move1.location_dest_id.id,
                "lot_id": lot1.id,
            }
        )
        self.assertEqual(len(move1.move_line_ids), 1)
        self.assertEqual(move1.quantity, 1)

        move1.picked = True
        move1._action_done()
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.product_serial, self.stock_location
            ),
            0.0,
        )
        self.assertEqual(
            len(self.gather_relevant(self.product_serial, self.stock_location)), 0.0
        )

    def test_mixed_tracking_reservation_6(self):
        self.env["stock.quant"]._update_available_quantity(
            self.product_serial, self.stock_location, 1.0
        )
        move1 = self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "product_id": self.product_serial.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 1.0,
            }
        )
        move1._action_confirm()
        move1._action_assign()
        self.assertEqual(move1.state, "assigned")

        lot1 = self.env["stock.lot"].create(
            {
                "name": "lot1",
                "product_id": self.product_serial.id,
            }
        )
        lot2 = self.env["stock.lot"].create(
            {
                "name": "lot2",
                "product_id": self.product_serial.id,
            }
        )

        move_line = move1.move_line_ids
        move_line.lot_id = lot1
        self.assertEqual(move_line.quantity_product_uom, 1.0)
        move_line.lot_id = lot2
        self.assertEqual(move_line.quantity_product_uom, 1.0)
        move_line.quantity = 1

        move1.picked = True
        move1._action_done()
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.product_serial, self.stock_location
            ),
            0.0,
        )
        self.assertEqual(
            len(self.gather_relevant(self.product_serial, self.stock_location)), 0.0
        )

    def test_mixed_tracking_reservation_7(self):
        lot1 = self.env["stock.lot"].create(
            {
                "name": "lot1",
                "product_id": self.product_serial.id,
            }
        )
        lot2 = self.env["stock.lot"].create(
            {
                "name": "lot2",
                "product_id": self.product_serial.id,
            }
        )
        self.env["stock.quant"]._update_available_quantity(
            self.product_serial, self.stock_location, 1, lot_id=lot1
        )
        self.env["stock.quant"]._update_available_quantity(
            self.product_serial, self.stock_location, 1
        )

        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.product_serial, self.stock_location
            ),
            2.0,
        )
        move1 = self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "product_id": self.product_serial.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 2.0,
            }
        )
        move1._action_confirm()
        move1._action_assign()
        self.assertEqual(len(move1.move_line_ids), 2)
        for ml in move1.move_line_ids:
            self.assertEqual(ml.quantity_product_uom, 1.0)

        move1.move_line_ids.filtered(lambda ml: not ml.lot_id).lot_id = lot2
        for ml in move1.move_line_ids:
            self.assertEqual(ml.quantity_product_uom, 1.0)

        move1.move_line_ids.write({"quantity": 1.0})
        move1.picked = True
        move1._action_done()

        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.product_serial, self.stock_location
            ),
            0.0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.product_serial, self.stock_location, lot_id=lot1, strict=True
            ),
            0.0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.product_serial, self.stock_location, lot_id=lot2, strict=True
            ),
            0.0,
        )
        quants = self.gather_relevant(self.product_serial, self.stock_location)
        self.assertEqual(len(quants), 0)

    def test_multi_step_update(self):
        self.warehouse_1.reception_steps = "two_steps"

        move_input = self.env["stock.move"].create(
            {
                "location_id": self.supplier_location.id,
                "location_dest_id": self.warehouse_1.wh_input_stock_loc_id.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 1.0,
                "warehouse_id": self.warehouse_1.id,
            }
        )
        move_input._action_confirm()
        move_input.move_line_ids.quantity = 9
        move_input.picked = True
        move_input._action_done()

        self.assertEqual(move_input.move_dest_ids.product_uom_qty, 9)

    def test_mixed_tracking_reservation_8(self):
        lot1 = self.env["stock.lot"].create(
            {
                "name": "lot1",
                "product_id": self.product_serial.id,
            }
        )

        self.env["stock.quant"]._update_available_quantity(
            self.product_serial, self.stock_location, 1, lot_id=lot1
        )

        move1 = self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "product_id": self.product_serial.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 1.0,
            }
        )
        move1._action_confirm()
        move1._action_assign()

        self.assertEqual(move1.quantity, 1.0)
        self.assertEqual(move1.move_line_ids.lot_id.id, lot1.id)

        self.env["stock.quant"]._update_available_quantity(
            self.product_serial, self.stock_location, 1
        )
        lot2 = self.env["stock.lot"].create(
            {
                "name": "lot2",
                "product_id": self.product_serial.id,
            }
        )
        move1.move_line_ids.lot_id = lot2
        self.assertEqual(move1.quantity, 1.0)
        self.assertEqual(move1.move_line_ids.lot_id.id, lot2.id)
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.product_serial, self.stock_location, strict=True
            ),
            0.0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.product_serial, self.stock_location, lot_id=lot1, strict=True
            ),
            1.0,
        )

        move1._unreserve()

        self.assertEqual(move1.quantity, 0.0)
        self.assertEqual(len(move1.move_line_ids), 0)
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.product_serial, self.stock_location, strict=True
            ),
            1.0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.product_serial, self.stock_location, lot_id=lot1, strict=False
            ),
            2.0,
        )

    def test_mixed_tracking_reservation_9(self):
        lot1 = self.env["stock.lot"].create(
            {"name": "lot1", "product_id": self.product_serial.id}
        )
        lot2 = self.env["stock.lot"].create(
            {"name": "lot2", "product_id": self.product_serial.id}
        )
        self.env["stock.quant"]._update_available_quantity(
            self.product_serial, self.stock_location, 10, lot_id=lot1
        )
        self.env["stock.quant"]._update_available_quantity(
            self.product_serial, self.stock_location, 1
        )
        self.env["stock.quant"]._update_available_quantity(
            self.product_serial, self.stock_location, -1
        )
        move_out = self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "product_id": self.product_serial.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 1.0,
            }
        )
        move_out._action_confirm()
        move_out._action_assign()
        move_out.move_line_ids.lot_id = lot2
        move_out.picked = True
        move_out._action_done()
        quants = self.gather_relevant(self.product_serial, self.stock_location)
        self.assertEqual(quants.filtered(lambda q: q.lot_id == lot1).quantity, 10)
        self.assertEqual(quants.filtered(lambda q: q.lot_id == lot2).quantity, -1)

    def test_putaway_1(self):
        putaway = self.env["stock.putaway.rule"].create(
            {
                "location_in_id": self.stock_location.id,
                "location_out_id": self.shelf_1.id,
            }
        )
        self.stock_location.write({"putaway_rule_ids": [(4, putaway.id, 0)]})

        move1 = self.env["stock.move"].create(
            {
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 100.0,
            }
        )
        move1._action_confirm()
        self.assertEqual(move1.state, "assigned")
        self.assertEqual(len(move1.move_line_ids), 1)

        self.assertEqual(move1.move_line_ids.location_dest_id.id, self.shelf_1.id)

    def test_putaway_2(self):
        putaway = self.env["stock.putaway.rule"].create(
            {
                "product_id": self.productA.id,
                "location_in_id": self.stock_location.id,
                "location_out_id": self.shelf_1.id,
            }
        )
        self.stock_location.write(
            {
                "putaway_rule_ids": [(4, putaway.id, 0)],
            }
        )

        move1 = self.env["stock.move"].create(
            {
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 100.0,
            }
        )
        move1._action_confirm()
        self.assertEqual(move1.state, "assigned")
        self.assertEqual(len(move1.move_line_ids), 1)

        self.assertEqual(move1.move_line_ids.location_dest_id.id, self.shelf_1.id)

    def test_putaway_3(self):
        putaway_category = self.env["stock.putaway.rule"].create(
            {
                "location_in_id": self.supplier_location.id,
                "location_out_id": self.shelf_1.id,
            }
        )
        putaway_product = self.env["stock.putaway.rule"].create(
            {
                "product_id": self.productA.id,
                "location_in_id": self.supplier_location.id,
                "location_out_id": self.shelf_2.id,
            }
        )
        self.stock_location.write(
            {
                "putaway_rule_ids": [(6, 0, [putaway_category.id, putaway_product.id])],
            }
        )

        move1 = self.env["stock.move"].create(
            {
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 100.0,
            }
        )
        move1._action_confirm()
        self.assertEqual(move1.state, "assigned")
        self.assertEqual(len(move1.move_line_ids), 1)

        self.assertEqual(move1.move_line_ids.location_dest_id.id, self.shelf_2.id)

    def test_putaway_4(self):
        putaway_category = self.env["stock.putaway.rule"].create(
            {
                "location_in_id": self.stock_location.id,
                "location_out_id": self.shelf_1.id,
            }
        )
        putaway_product = self.env["stock.putaway.rule"].create(
            {
                "product_id": self.product_consu.id,
                "location_in_id": self.stock_location.id,
                "location_out_id": self.shelf_2.id,
            }
        )
        self.stock_location.write(
            {
                "putaway_rule_ids": [
                    (
                        6,
                        0,
                        [
                            putaway_category.id,
                            putaway_product.id,
                        ],
                    )
                ],
            }
        )

        move1 = self.env["stock.move"].create(
            {
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 100.0,
            }
        )
        move1._action_confirm()
        self.assertEqual(move1.state, "assigned")
        self.assertEqual(len(move1.move_line_ids), 1)

        self.assertEqual(move1.move_line_ids.location_dest_id.id, self.shelf_1.id)

    def test_putaway_5(self):
        putaway = self.env["stock.putaway.rule"].create(
            {
                "location_in_id": self.supplier_location.id,
                "location_out_id": self.shelf_1.id,
            }
        )
        self.stock_location.write(
            {
                "putaway_rule_ids": [
                    (
                        6,
                        0,
                        [
                            putaway.id,
                        ],
                    )
                ],
            }
        )
        move1 = self.env["stock.move"].create(
            {
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 100.0,
            }
        )
        move1._action_confirm()
        self.assertEqual(move1.state, "assigned")
        self.assertEqual(len(move1.move_line_ids), 1)

        self.assertEqual(move1.move_line_ids.location_dest_id.id, self.shelf_1.id)

    def test_putaway_6(self):
        child_category = self.env["product.category"].create(
            {
                "name": "child_category",
                "parent_id": self.ref("product.product_category_goods"),
            }
        )
        putaway_category_all = self.env["stock.putaway.rule"].create(
            {
                "location_in_id": self.supplier_location.id,
                "location_out_id": self.shelf_1.id,
            }
        )
        putaway_category_office_furn = self.env["stock.putaway.rule"].create(
            {
                "category_id": child_category.id,
                "location_in_id": self.supplier_location.id,
                "location_out_id": self.shelf_2.id,
            }
        )
        self.stock_location.write(
            {
                "putaway_rule_ids": [
                    (
                        6,
                        0,
                        [
                            putaway_category_all.id,
                            putaway_category_office_furn.id,
                        ],
                    )
                ],
            }
        )
        self.productA.categ_id = child_category

        move1 = self.env["stock.move"].create(
            {
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 100.0,
            }
        )
        move1._action_confirm()
        self.assertEqual(move1.state, "assigned")
        self.assertEqual(len(move1.move_line_ids), 1)

        self.assertEqual(move1.move_line_ids.location_dest_id.id, self.shelf_2.id)

    def test_putaway_7(self):
        self.warehouse_1.reception_steps = "two_steps"
        child_loc = self.stock_location.child_ids[0]

        package_type = self.env["stock.package.type"].create(
            {
                "name": "Super Package Type",
            }
        )

        package = self.env["stock.package"].create({"package_type_id": package_type.id})

        self.env["stock.putaway.rule"].create(
            {
                "product_id": self.productA.id,
                "package_type_ids": [(6, 0, package_type.ids)],
                "location_in_id": self.stock_location.id,
                "location_out_id": child_loc.id,
            }
        )

        move_input = self.env["stock.move"].create(
            {
                "location_id": self.supplier_location.id,
                "location_dest_id": self.warehouse_1.wh_input_stock_loc_id.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 1.0,
                "warehouse_id": self.warehouse_1.id,
            }
        )
        move_input._action_confirm()
        move_input.move_line_ids.quantity = 1
        move_input.move_line_ids.result_package_id = package
        move_input.picked = True
        move_input._action_done()

        move_stock = move_input.move_dest_ids
        self.assertEqual(move_stock.move_line_ids.location_dest_id, child_loc)

    def test_putaway_8(self):
        self.warehouse_1.reception_steps = "two_steps"
        child_loc = self.stock_location.child_ids[0]

        package_type = self.env["stock.package.type"].create(
            {
                "name": "Super Package Type",
            }
        )

        package = self.env["stock.package"].create({"package_type_id": package_type.id})

        self.env["stock.putaway.rule"].create(
            {
                "product_id": self.productA.id,
                "location_in_id": self.stock_location.id,
                "location_out_id": child_loc.id,
            }
        )

        move_input = self.env["stock.move"].create(
            {
                "location_id": self.supplier_location.id,
                "location_dest_id": self.warehouse_1.wh_input_stock_loc_id.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 1.0,
                "warehouse_id": self.warehouse_1.id,
            }
        )
        move_input._action_confirm()
        move_input.move_line_ids.quantity = 1
        move_input.move_line_ids.result_package_id = package
        move_input.picked = True
        move_input._action_done()

        move_stock = move_input.move_dest_ids
        self.assertEqual(move_stock.move_line_ids.location_dest_id, child_loc)

    def test_putaway_9(self):
        self.warehouse_1.reception_steps = "two_steps"

        basic_category = self.env.ref("product.product_category_goods")
        child_locations = self.env["stock.location"]
        categs = self.env["product.category"]

        for i in range(3):
            loc = self.env["stock.location"].create(
                {
                    "name": "shelf %s" % i,
                    "usage": "internal",
                    "location_id": self.stock_location.id,
                }
            )
            child_locations |= loc

            categ = self.env["product.category"].create(
                {"name": "Category %s" % i, "parent_id": basic_category.id}
            )
            categs |= categ

            self.env["stock.putaway.rule"].create(
                {
                    "category_id": categ.id,
                    "location_in_id": self.stock_location.id,
                    "location_out_id": loc.id,
                }
            )

        second_child_location = child_locations[1]
        second_categ = categs[1]
        self.productA.categ_id = second_categ

        package_type = self.env["stock.package.type"].create(
            {
                "name": "Super Package Type",
            }
        )
        package = self.env["stock.package"].create(
            {
                "package_type_id": package_type.id,
            }
        )

        move_input = self.env["stock.move"].create(
            {
                "location_id": self.supplier_location.id,
                "location_dest_id": self.warehouse_1.wh_input_stock_loc_id.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 1.0,
                "warehouse_id": self.warehouse_1.id,
            }
        )
        move_input._action_confirm()
        move_input.move_line_ids.quantity = 1
        move_input.move_line_ids.result_package_id = package
        move_input.picked = True
        move_input._action_done()

        move_stock = move_input.move_dest_ids
        self.assertEqual(
            move_stock.move_line_ids.location_dest_id, second_child_location
        )

    def test_putaway_with_packaging(self):
        package_type = self.env["stock.package.type"].create(
            {
                "name": "Super Package Type",
            }
        )

        child_loc = self.stock_location.child_ids[:1]
        self.uom_dozen.package_type_id = package_type

        self.env["stock.putaway.rule"].create(
            {
                "location_in_id": self.stock_location.id,
                "location_out_id": child_loc.id,
                "package_type_ids": [(6, 0, package_type.ids)],
            }
        )

        sm = self.env["stock.move"].create(
            {
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 12.0,
            }
        )
        sm.packaging_uom_id = self.uom_dozen
        sm._action_confirm()

        self.assertEqual(sm.move_line_ids.location_dest_id, child_loc)

    def test_putaway_with_storage_category_1(self):
        storage_category = self.env["stock.storage.category"].create(
            {"name": "storage category"}
        )

        self.shelf_2.storage_category_id = storage_category
        self.env["stock.quant"]._update_available_quantity(
            self.productA, self.shelf_1, 1.0
        )

        putaway = self.env["stock.putaway.rule"].create(
            {
                "product_id": self.productA.id,
                "location_in_id": self.stock_location.id,
                "location_out_id": self.stock_location.id,
                "storage_category_id": storage_category.id,
                "sublocation": "closest_location",
            }
        )
        self.stock_location.write(
            {
                "putaway_rule_ids": [(4, putaway.id, 0)],
            }
        )

        move1 = self.env["stock.move"].create(
            {
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 100.0,
            }
        )
        move1._action_confirm()
        self.assertEqual(move1.state, "assigned")
        self.assertEqual(len(move1.move_line_ids), 1)

        self.assertEqual(move1.move_line_ids.location_dest_id.id, self.shelf_2.id)

    def test_putaway_with_storage_category_2(self):
        storage_category = self.env["stock.storage.category"].create(
            {"name": "storage category"}
        )
        storage_category_form = Form(
            storage_category, view="stock.view_stock_storage_category_form"
        )
        with storage_category_form.product_capacity_ids.new() as line:
            line.product_id = self.productA
            line.quantity = 100
        storage_category = storage_category_form.save()

        self.shelf_1.storage_category_id = storage_category
        putaway = self.env["stock.putaway.rule"].create(
            {
                "product_id": self.productA.id,
                "location_in_id": self.stock_location.id,
                "location_out_id": self.stock_location.id,
                "storage_category_id": storage_category.id,
                "sublocation": "closest_location",
            }
        )
        self.stock_location.write(
            {
                "putaway_rule_ids": [(4, putaway.id, 0)],
            }
        )

        move1 = self.env["stock.move"].create(
            {
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 100.0,
            }
        )
        move1._action_confirm()
        self.assertEqual(move1.state, "assigned")
        self.assertEqual(len(move1.move_line_ids), 1)

        self.assertEqual(move1.move_line_ids.location_dest_id.id, self.shelf_1.id)

        move2 = self.env["stock.move"].create(
            {
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 100.0,
            }
        )
        move2._action_confirm()
        self.assertEqual(move1.state, "assigned")
        self.assertEqual(len(move2.move_line_ids), 1)

        self.assertEqual(
            move2.move_line_ids.location_dest_id.id, self.stock_location.id
        )

    def test_putaway_storage_category_multi_inbound_same_uom(self):
        storage_category = self.env["stock.storage.category"].create(
            {"name": "storage category"}
        )
        storage_category_form = Form(
            storage_category, view="stock.view_stock_storage_category_form"
        )
        with storage_category_form.product_capacity_ids.new() as line:
            line.product_id = self.productA
            line.quantity = 100
        storage_category = storage_category_form.save()

        self.shelf_1.storage_category_id = storage_category
        putaway = self.env["stock.putaway.rule"].create(
            {
                "product_id": self.productA.id,
                "location_in_id": self.stock_location.id,
                "location_out_id": self.stock_location.id,
                "storage_category_id": storage_category.id,
                "sublocation": "closest_location",
            }
        )
        self.stock_location.write({"putaway_rule_ids": [(4, putaway.id, 0)]})

        def receive(qty):
            move = self.env["stock.move"].create(
                {
                    "location_id": self.supplier_location.id,
                    "location_dest_id": self.stock_location.id,
                    "product_id": self.productA.id,
                    "product_uom_id": self.uom_unit.id,
                    "product_uom_qty": qty,
                }
            )
            move._action_confirm()
            return move

        move1 = receive(40)
        move2 = receive(40)
        self.assertEqual(move1.move_line_ids.location_dest_id.id, self.shelf_1.id)
        self.assertEqual(move2.move_line_ids.location_dest_id.id, self.shelf_1.id)

        move3 = receive(40)
        self.assertEqual(
            move3.move_line_ids.location_dest_id.id,
            self.stock_location.id,
            "both 40-unit inbound lines on shelf_1 must be counted (80); a third "
            "40 exceeds the capacity of 100 and must not be put away there",
        )

    def test_putaway_with_storage_category_3(self):
        storage_category = self.env["stock.storage.category"].create(
            {
                "name": "storage category",
                "allow_new_product": "empty",
            }
        )

        self.shelf_1.storage_category_id = storage_category
        putaway = self.env["stock.putaway.rule"].create(
            {
                "product_id": self.productA.id,
                "location_in_id": self.stock_location.id,
                "location_out_id": self.stock_location.id,
                "storage_category_id": storage_category.id,
                "sublocation": "closest_location",
            }
        )
        self.stock_location.write(
            {
                "putaway_rule_ids": [(4, putaway.id, 0)],
            }
        )

        move1 = self.env["stock.move"].create(
            {
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 100.0,
            }
        )
        move1._action_confirm()
        self.assertEqual(move1.state, "assigned")
        self.assertEqual(len(move1.move_line_ids), 1)
        move_line = move1.move_line_ids[0]
        move_line.quantity = 100
        move1.picked = True
        move1._action_done()
        self.assertEqual(move1.state, "done")

        self.assertEqual(move1.move_line_ids.location_dest_id.id, self.shelf_1.id)

        move2 = self.env["stock.move"].create(
            {
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 100.0,
            }
        )
        move2._action_confirm()
        self.assertEqual(move2.state, "assigned")
        self.assertEqual(len(move2.move_line_ids), 1)

        self.assertEqual(
            move2.move_line_ids.location_dest_id.id, self.stock_location.id
        )

    def test_putaway_with_storage_category_4(self):
        storage_category = self.env["stock.storage.category"].create(
            {
                "name": "storage category",
                "allow_new_product": "same",
            }
        )

        self.shelf_1.storage_category_id = storage_category
        putaway = self.env["stock.putaway.rule"].create(
            {
                "product_id": self.productA.id,
                "location_in_id": self.stock_location.id,
                "location_out_id": self.stock_location.id,
                "storage_category_id": storage_category.id,
                "sublocation": "closest_location",
            }
        )
        self.stock_location.write(
            {
                "putaway_rule_ids": [(4, putaway.id, 0)],
            }
        )

        product2 = self.env["product.product"].create(
            {
                "name": "Product 2",
                "is_storable": True,
            }
        )
        self.env["stock.quant"].create(
            {
                "product_id": product2.id,
                "product_uom_id": self.uom_unit.id,
                "location_id": self.shelf_1.id,
                "quantity": 1,
                "reserved_quantity": 0,
            }
        )

        move1 = self.env["stock.move"].create(
            {
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 100.0,
            }
        )
        move1._action_confirm()
        self.assertEqual(move1.state, "assigned")
        self.assertEqual(len(move1.move_line_ids), 1)
        move_line = move1.move_line_ids[0]
        move_line.quantity = 100
        move1.picked = True
        move1._action_done()
        self.assertEqual(move1.state, "done")

        self.assertEqual(
            move1.move_line_ids.location_dest_id.id, self.stock_location.id
        )

    def test_putaway_with_storage_category_5(self):
        self.env.user.group_ids += self.env.ref("stock.group_tracking_lot")
        storage_category = self.env["stock.storage.category"].create(
            {"name": "storage category"}
        )

        package_type = self.env["stock.package.type"].create(
            {
                "name": "package type",
            }
        )

        self.shelf_2.storage_category_id = storage_category

        putaway = self.env["stock.putaway.rule"].create(
            {
                "product_id": self.productA.id,
                "location_in_id": self.stock_location.id,
                "location_out_id": self.stock_location.id,
                "storage_category_id": storage_category.id,
                "package_type_ids": [(4, package_type.id, 0)],
                "sublocation": "closest_location",
            }
        )
        self.stock_location.write(
            {
                "putaway_rule_ids": [(4, putaway.id, 0)],
            }
        )

        package = self.env["stock.package"].create(
            {
                "name": "package",
                "package_type_id": package_type.id,
            }
        )

        move1 = self.env["stock.move"].create(
            {
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 100.0,
            }
        )
        move1._action_confirm()
        self.assertEqual(move1.state, "assigned")
        self.assertEqual(len(move1.move_line_ids), 1)
        move_form = Form(move1, view="stock.view_stock_move_form_operations")
        with move_form.move_line_ids.edit(0) as line:
            line.result_package_id = package
        move1 = move_form.save()
        move1.picked = True
        move1._action_done()

        self.assertEqual(package.location_id.id, self.shelf_2.id)

    def test_putaway_with_storage_category_6(self):
        self.env.user.group_ids += self.env.ref("stock.group_tracking_lot")
        storage_category = self.env["stock.storage.category"].create(
            {"name": "storage category"}
        )

        package_type = self.env["stock.package.type"].create(
            {
                "name": "package type",
            }
        )

        storage_category_form = Form(
            storage_category, view="stock.view_stock_storage_category_form"
        )
        with storage_category_form.package_capacity_ids.new() as line:
            line.package_type_id = package_type
            line.quantity = 1
        storage_category = storage_category_form.save()

        self.shelf_2.storage_category_id = storage_category

        putaway = self.env["stock.putaway.rule"].create(
            {
                "product_id": self.productA.id,
                "location_in_id": self.stock_location.id,
                "location_out_id": self.stock_location.id,
                "storage_category_id": storage_category.id,
                "package_type_ids": [(4, package_type.id, 0)],
                "sublocation": "closest_location",
            }
        )
        self.stock_location.write(
            {
                "putaway_rule_ids": [(4, putaway.id, 0)],
            }
        )

        package1 = self.env["stock.package"].create(
            {
                "name": "package 1",
                "package_type_id": package_type.id,
            }
        )

        move1 = self.env["stock.move"].create(
            {
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 100.0,
            }
        )
        move1._action_confirm()
        self.assertEqual(move1.state, "assigned")
        self.assertEqual(len(move1.move_line_ids), 1)

        move_form = Form(move1, view="stock.view_stock_move_form_operations")
        with move_form.move_line_ids.new() as line:
            line.result_package_id = package1
            line.quantity = 100
        move1 = move_form.save()
        move1.picked = True
        move1._action_done()

        self.assertEqual(package1.location_id.id, self.shelf_2.id)

        package2 = self.env["stock.package"].create(
            {
                "name": "package 2",
                "package_type_id": package_type.id,
            }
        )

        move2 = self.env["stock.move"].create(
            {
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 100.0,
            }
        )
        move2._action_confirm()
        self.assertEqual(move2.state, "assigned")
        self.assertEqual(len(move2.move_line_ids), 1)

        move_form = Form(move2, view="stock.view_stock_move_form_operations")
        with move_form.move_line_ids.new() as line:
            line.result_package_id = package2
            line.quantity = 100
        move2 = move_form.save()
        move2.picked = True
        move2._action_done()

        self.assertEqual(package2.location_id.id, self.stock_location.id)

    def test_putaway_with_storage_category_7(self):
        self.env.user.group_ids += self.env.ref("stock.group_tracking_lot")
        storage_category = self.env["stock.storage.category"].create(
            {
                "name": "storage category",
                "allow_new_product": "empty",
            }
        )

        package_type = self.env["stock.package.type"].create(
            {
                "name": "package type",
            }
        )

        storage_category_form = Form(
            storage_category, view="stock.view_stock_storage_category_form"
        )
        with storage_category_form.package_capacity_ids.new() as line:
            line.package_type_id = package_type
            line.quantity = 100
        storage_category = storage_category_form.save()

        self.shelf_2.storage_category_id = storage_category

        putaway = self.env["stock.putaway.rule"].create(
            {
                "product_id": self.productA.id,
                "location_in_id": self.stock_location.id,
                "location_out_id": self.stock_location.id,
                "storage_category_id": storage_category.id,
                "package_type_ids": [(4, package_type.id, 0)],
                "sublocation": "closest_location",
            }
        )
        self.stock_location.write(
            {
                "putaway_rule_ids": [(4, putaway.id, 0)],
            }
        )

        package1 = self.env["stock.package"].create(
            {
                "name": "package 1",
                "package_type_id": package_type.id,
            }
        )

        move1 = self.env["stock.move"].create(
            {
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 100.0,
            }
        )
        move1._action_confirm()
        self.assertEqual(move1.state, "assigned")
        self.assertEqual(len(move1.move_line_ids), 1)

        move_form = Form(move1, view="stock.view_stock_move_form_operations")
        with move_form.move_line_ids.new() as line:
            line.result_package_id = package1
            line.quantity = 100
        move1 = move_form.save()
        move1.picked = True
        move1._action_done()

        self.assertEqual(package1.location_id.id, self.shelf_2.id)

        package2 = self.env["stock.package"].create(
            {
                "name": "package 2",
                "package_type_id": package_type.id,
            }
        )

        move2 = self.env["stock.move"].create(
            {
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 100.0,
            }
        )
        move2._action_confirm()
        self.assertEqual(move2.state, "assigned")
        self.assertEqual(len(move2.move_line_ids), 1)

        move_form = Form(move2, view="stock.view_stock_move_form_operations")
        with move_form.move_line_ids.new() as line:
            line.result_package_id = package2
            line.quantity = 100
        move2 = move_form.save()
        move2.picked = True
        move2._action_done()

        self.assertEqual(package2.location_id.id, self.stock_location.id)

    def test_putaway_with_storage_category_8(self):
        self.env.user.group_ids += self.env.ref("stock.group_tracking_lot")
        storage_category = self.env["stock.storage.category"].create(
            {
                "name": "storage category",
                "allow_new_product": "same",
            }
        )

        package_type = self.env["stock.package.type"].create(
            {
                "name": "package type",
            }
        )

        storage_category_form = Form(
            storage_category, view="stock.view_stock_storage_category_form"
        )
        with storage_category_form.package_capacity_ids.new() as line:
            line.package_type_id = package_type
            line.quantity = 100
        storage_category = storage_category_form.save()

        self.shelf_2.storage_category_id = storage_category

        putaway = self.env["stock.putaway.rule"].create(
            {
                "location_in_id": self.stock_location.id,
                "location_out_id": self.stock_location.id,
                "storage_category_id": storage_category.id,
                "package_type_ids": [(4, package_type.id, 0)],
                "sublocation": "closest_location",
            }
        )
        self.stock_location.write(
            {
                "putaway_rule_ids": [(4, putaway.id, 0)],
            }
        )

        package1 = self.env["stock.package"].create(
            {
                "name": "package 1",
                "package_type_id": package_type.id,
            }
        )

        move1 = self.env["stock.move"].create(
            {
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 100.0,
            }
        )
        move1._action_confirm()
        self.assertEqual(move1.state, "assigned")
        self.assertEqual(len(move1.move_line_ids), 1)

        move_form = Form(move1, view="stock.view_stock_move_form_operations")
        with move_form.move_line_ids.new() as line:
            line.result_package_id = package1
            line.quantity = 100
        move1 = move_form.save()
        move1.picked = True
        move1._action_done()

        self.assertEqual(package1.location_id.id, self.shelf_2.id)

        package2 = self.env["stock.package"].create(
            {
                "name": "package 2",
                "package_type_id": package_type.id,
            }
        )

        product2 = self.env["product.product"].create(
            {
                "name": "Product 2",
                "is_storable": True,
            }
        )

        move2 = self.env["stock.move"].create(
            {
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
                "product_id": product2.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 100.0,
            }
        )
        move2._action_confirm()
        self.assertEqual(move2.state, "assigned")
        self.assertEqual(len(move2.move_line_ids), 1)

        move_form = Form(move2, view="stock.view_stock_move_form_operations")
        with move_form.move_line_ids.new() as line:
            line.result_package_id = package2
            line.quantity = 100
        move2 = move_form.save()
        move2.picked = True
        move2._action_done()

        self.assertEqual(package2.location_id.id, self.stock_location.id)

    def test_putaway_with_storage_category_9(self):
        self.productA.weight = 1
        storage_category = self.env["stock.storage.category"].create(
            {
                "name": "storage category",
                "max_weight": 100,
            }
        )

        self.shelf_1.storage_category_id = storage_category
        putaway = self.env["stock.putaway.rule"].create(
            {
                "product_id": self.productA.id,
                "location_in_id": self.stock_location.id,
                "location_out_id": self.stock_location.id,
                "storage_category_id": storage_category.id,
                "sublocation": "closest_location",
            }
        )
        self.stock_location.write(
            {
                "putaway_rule_ids": [(4, putaway.id, 0)],
            }
        )

        move1 = self.env["stock.move"].create(
            {
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 100.0,
            }
        )
        move1._action_confirm()
        self.assertEqual(move1.state, "assigned")
        self.assertEqual(len(move1.move_line_ids), 1)

        self.assertEqual(move1.move_line_ids.location_dest_id.id, self.shelf_1.id)

        move2 = self.env["stock.move"].create(
            {
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 100.0,
            }
        )
        move2._action_confirm()
        self.assertEqual(move1.state, "assigned")
        self.assertEqual(len(move2.move_line_ids), 1)

        self.assertEqual(
            move2.move_line_ids.location_dest_id.id, self.stock_location.id
        )

    def test_putaway_rule_with_last_used_sublocation(self):
        putaway = self.env["stock.putaway.rule"].create(
            {
                "product_id": self.productA.id,
                "location_in_id": self.stock_location.id,
                "location_out_id": self.stock_location.id,
            }
        )

        self.stock_location.write(
            {
                "putaway_rule_ids": [(4, putaway.id, 0)],
            }
        )

        move1 = self.env["stock.move"].create(
            {
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 1.0,
            }
        )
        move1._action_confirm()
        self.assertEqual(move1.move_line_ids[0].location_dest_id, self.stock_location)
        move1.move_line_ids[0].location_dest_id = self.shelf_1
        self.assertEqual(move1.state, "assigned")
        self.assertEqual(len(move1.move_line_ids), 1)
        move1._action_done()

        move2 = self.env["stock.move"].create(
            {
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 1.0,
            }
        )
        move2._action_confirm()
        self.assertEqual(move1.state, "assigned")
        self.assertEqual(len(move2.move_line_ids), 1)

        self.assertEqual(
            move2.move_line_ids.location_dest_id.id, self.stock_location.id
        )

    def test_availability_1(self):
        self.env["stock.quant"]._update_available_quantity(
            self.productA, self.stock_location, 150.0
        )
        self.assertEqual(
            len(self.gather_relevant(self.productA, self.stock_location)), 1.0
        )

        move1 = self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.supplier_location.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 100.0,
            }
        )

        self.assertEqual(move1.state, "draft")
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location
            ),
            150.0,
        )
        self.assertEqual(
            len(self.gather_relevant(self.productA, self.stock_location)), 1.0
        )

    def test_availability_2(self):
        self.env["stock.quant"]._update_available_quantity(
            self.productA, self.stock_location, 50.0
        )
        self.assertEqual(
            len(self.gather_relevant(self.productA, self.stock_location)), 1.0
        )

        move1 = self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.supplier_location.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 100.0,
            }
        )

        self.assertEqual(move1.state, "draft")
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location
            ),
            50.0,
        )
        self.assertEqual(
            len(self.gather_relevant(self.productA, self.stock_location)), 1.0
        )

    def test_availability_3(self):
        lot1 = self.env["stock.lot"].create(
            {
                "name": "lot1",
                "product_id": self.product_serial.id,
            }
        )
        lot2 = self.env["stock.lot"].create(
            {
                "name": "lot2",
                "product_id": self.product_serial.id,
            }
        )
        self.env["stock.quant"]._update_available_quantity(
            self.product_serial, self.stock_location, -1.0, lot_id=lot1
        )
        self.env["stock.quant"]._update_available_quantity(
            self.product_serial, self.stock_location, 1.0, lot_id=lot2
        )
        move1 = self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "product_id": self.product_serial.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 1.0,
            }
        )
        move1._action_confirm()
        move1._action_assign()
        self.assertEqual(move1.state, "assigned")
        self.assertEqual(move1.quantity, 1.0)

    def test_availability_4(self):
        self.env["stock.quant"]._update_available_quantity(
            self.productA, self.stock_location, 30.0
        )
        move1 = self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 15.0,
            }
        )
        move1._action_confirm()
        move1._action_assign()
        self.assertEqual(move1.state, "assigned")

        move2 = self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 15.0,
            }
        )
        move2._action_confirm()
        move2._action_assign()

        move1.move_line_ids.quantity = 15
        move2.move_line_ids.quantity = 30
        move2.picked = True

        move2._action_done()

        self.assertEqual(move1.state, "confirmed")
        self.assertEqual(move1.move_line_ids.quantity, 0)
        self.assertEqual(move2.state, "done")

        stock_quants = self.gather_relevant(self.productA, self.stock_location)
        self.assertEqual(len(stock_quants), 0)
        customer_quants = self.gather_relevant(self.productA, self.customer_location)
        self.assertEqual(customer_quants.quantity, 30)
        self.assertEqual(customer_quants.reserved_quantity, 0)

    def test_availability_5(self):
        self.env["stock.quant"]._update_available_quantity(
            self.product_serial, self.stock_location, 2.0
        )
        picking = self.env["stock.picking"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "picking_type_id": self.picking_type_out.id,
                "state": "draft",
            }
        )

        move = self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "product_id": self.product_serial.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 4.0,
                "picking_id": picking.id,
            }
        )
        move._action_confirm()
        move._action_assign()

        self.env["stock.quant"]._update_available_quantity(
            self.product_serial, self.stock_location, 4.0
        )
        move._action_assign()

        self.assertEqual(len(move.move_line_ids), 4.0)

    def test_availability_6(self):
        self.env["decimal.precision"].search([("name", "=", "Product Unit")]).digits = 0

        self.env["stock.quant"]._update_available_quantity(
            self.productA, self.stock_location, 6.0
        )
        self.productA.write({"uom_ids": [(4, self.uom_dozen.id)]})

        move = self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_dozen.id,
                "product_uom_qty": 1,
            }
        )
        move._action_confirm()
        move._action_assign()
        self.assertEqual(move.state, "confirmed")

        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location
            ),
            6.0,
        )

        self.env["stock.quant"]._update_available_quantity(
            self.productA, self.stock_location, 2.0
        )
        move._action_assign()
        self.assertEqual(move.state, "confirmed")
        self.assertAlmostEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location
            ),
            8.0,
        )

        self.env["stock.quant"]._update_available_quantity(
            self.productA, self.stock_location, 4.0
        )
        move._action_assign()
        self.assertEqual(move.state, "assigned")
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location
            ),
            0.0,
        )
        move.picked = True
        move.quantity = 1
        move._action_done()
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.customer_location
            ),
            12.0,
        )

    def test_availability_7(self):
        for i in range(1, 13):
            lot_id = self.env["stock.lot"].create(
                {
                    "name": "lot%s" % str(i),
                    "product_id": self.product_serial.id,
                }
            )
            self.env["stock.quant"]._update_available_quantity(
                self.product_serial, self.stock_location, 1.0, lot_id=lot_id
            )

        move = self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "product_id": self.product_serial.id,
                "product_uom_id": self.uom_dozen.id,
                "product_uom_qty": 1,
            }
        )
        move._action_confirm()
        move._action_assign()
        self.assertEqual(move.state, "assigned")
        self.assertEqual(len(move.move_line_ids.mapped("product_uom_id")), 1)
        self.assertEqual(move.move_line_ids.mapped("product_uom_id"), self.uom_unit)

        for move_line in move.move_line_ids:
            move_line.quantity = 1
        move.picked = True
        move._action_done()

        self.assertEqual(move.product_uom_qty, 1)
        self.assertEqual(move.product_uom_id.id, self.uom_dozen.id)
        self.assertEqual(move.state, "done")
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.product_serial, self.customer_location
            ),
            12.0,
        )
        self.assertEqual(
            len(self.gather_relevant(self.product_serial, self.customer_location)), 12
        )

    def test_availability_8(self):
        self.env["stock.quant"]._update_available_quantity(
            self.productA, self.stock_location, 3.0
        )
        self.assertAlmostEqual(self.productA.qty_available, 3.0)

        move_partial = self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 5.0,
            }
        )

        move_partial._action_confirm()
        move_partial._action_assign()
        self.assertAlmostEqual(self.productA.qty_available_virtual, -2.0)
        self.assertEqual(move_partial.state, "partially_available")
        move_partial.product_uom_qty = 3.0
        move_partial._action_assign()
        self.assertEqual(move_partial.state, "assigned")

    def test_availability_10(self):
        lot1, lot2, lot3 = self.env["stock.lot"].create(
            [
                {
                    "name": "lot%s" % str(i),
                    "product_id": self.product_lot.id,
                }
                for i in range(1, 4)
            ]
        )
        pack = self.env["stock.package"].create({"name": "pack"})
        self.env["stock.quant"]._update_available_quantity(
            self.product_lot, self.shelf_1, 3, lot_id=lot1
        )
        self.env["stock.quant"]._update_available_quantity(
            self.product_lot, self.shelf_2, 3, lot_id=lot2
        )
        self.env["stock.quant"]._update_available_quantity(
            self.product_lot, self.shelf_1, 1, lot_id=lot3
        )
        self.env["stock.quant"]._update_available_quantity(
            self.product_lot, self.shelf_2, 3, lot_id=lot2, package_id=pack
        )

        move = self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "product_id": self.product_lot.id,
                "product_uom_id": self.product_lot.uom_id.id,
                "product_uom_qty": 1.0,
            }
        )

        move._action_confirm()
        move._action_assign()
        self.assertRecordValues(
            move.move_line_ids,
            [
                {
                    "quantity": 1.0,
                    "location_id": self.shelf_1.id,
                    "lot_id": lot1.id,
                    "package_id": False,
                },
            ],
        )

        move.quantity = 8.0
        self.assertRecordValues(
            move.move_line_ids,
            [
                {
                    "quantity": 3.0,
                    "location_id": self.shelf_1.id,
                    "lot_id": lot1.id,
                    "package_id": False,
                },
                {
                    "quantity": 3.0,
                    "location_id": self.shelf_2.id,
                    "lot_id": lot2.id,
                    "package_id": False,
                },
                {
                    "quantity": 1.0,
                    "location_id": self.shelf_1.id,
                    "lot_id": lot3.id,
                    "package_id": False,
                },
                {
                    "quantity": 1.0,
                    "location_id": self.shelf_2.id,
                    "lot_id": lot2.id,
                    "package_id": pack.id,
                },
            ],
        )

        move.quantity = 3.0
        self.assertRecordValues(
            move.move_line_ids,
            [
                {
                    "quantity": 3.0,
                    "location_id": self.shelf_1.id,
                    "lot_id": lot1.id,
                    "package_id": False,
                },
            ],
        )

    def test_past_quantity(self):
        self.env["stock.quant"].create(
            {
                "product_id": self.productA.id,
                "location_id": self.stock_location.id,
                "inventory_quantity": 15.0,
            }
        ).action_apply_inventory()
        product_in_past = self.productA.with_context(
            to_date=fields.Date.add(fields.Date.today(), days=-7)
        )
        self.assertAlmostEqual(self.productA.qty_available, 15.0)
        self.assertAlmostEqual(product_in_past.qty_available, 0)

        move_partial = self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 2.0,
            }
        )
        move_partial._action_confirm()
        move_partial._action_assign()
        self.assertEqual(len(move_partial.move_line_ids), 1)

        move_partial.move_line_ids[0].quantity = 1
        move_partial.picked = True
        move_partial._action_done(cancel_backorder=True)
        self.assertEqual(move_partial.state, "done")
        self.assertAlmostEqual(move_partial.product_qty, 2)
        self.assertAlmostEqual(move_partial.quantity, 1)

        self.assertAlmostEqual(self.productA.qty_available, 14.0)
        self.assertAlmostEqual(product_in_past.qty_available, 0)

        move = self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_dozen.id,
                "product_uom_qty": 1.0,
            }
        )
        move._action_confirm()
        move._action_assign()
        move.picked = True
        move._action_done()

        self.assertAlmostEqual(self.productA.qty_available, 2.0)
        self.assertAlmostEqual(product_in_past.qty_available, 0)

    def test_past_availability_in_strict_mode(self):
        today = fields.Date.today()
        self.product.is_storable = True
        self.env["stock.quant"]._update_available_quantity(
            self.product, self.stock_location, 10.0
        )
        moves = self.env["stock.move"].create(
            [
                {
                    "location_id": self.customer_location.id,
                    "location_dest_id": self.stock_location.id,
                    "product_id": self.product.id,
                    "product_uom_qty": 3.0,
                },
                {
                    "location_id": self.stock_location.id,
                    "location_dest_id": self.customer_location.id,
                    "product_id": self.product.id,
                    "product_uom_qty": 2.0,
                },
            ]
        )
        moves._action_confirm()
        moves._action_assign()
        moves.picked = True
        moves._action_done()
        moves[0].date = fields.Date.add(today, days=-7)
        moves[1].date = fields.Date.add(today, days=-5)
        product = self.product.with_context(
            strict=True, location=self.stock_location.id
        )
        self.assertAlmostEqual(
            product.with_context(to_date=fields.Date.add(today, days=-8)).qty_available,
            10.0,
        )
        self.assertAlmostEqual(
            product.with_context(to_date=fields.Date.add(today, days=-6)).qty_available,
            13.0,
        )
        self.assertAlmostEqual(
            product.with_context(to_date=fields.Date.add(today, days=-4)).qty_available,
            11.0,
        )

    def test_product_tree_views(self):
        self.env["stock.quant"]._update_available_quantity(
            self.productA, self.stock_location, 3.0
        )
        user = new_test_user(self.env, login="test-basic-user")
        product_view = Form(
            self.env["product.product"].with_user(user).browse(self.productA.id),
            view="product.view_product_product_list",
        )
        self.assertEqual(product_view.name, self.productA.name)
        template_view = Form(
            self.env["product.template"]
            .with_user(user)
            .browse(self.productA.product_tmpl_id.id),
            view="product.view_product_template_list",
        )
        self.assertEqual(template_view.name, self.productA.product_tmpl_id.name)

    def test_availability_9(self):
        move_receipt = self.env["stock.move"].create(
            {
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_dozen.id,
                "product_uom_qty": 1.0,
            }
        )

        move_receipt._action_confirm()
        move_receipt._action_assign()
        self.assertEqual(move_receipt.state, "assigned")
        move_receipt.product_uom_qty = 3.0
        move_receipt._action_assign()
        self.assertEqual(move_receipt.state, "assigned")
        self.assertEqual(move_receipt.move_line_ids.quantity, 3)

    def test_unreserve_1(self):
        self.env["stock.quant"]._update_available_quantity(
            self.productA, self.stock_location, 150.0
        )

        move1 = self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.supplier_location.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_dozen.id,
                "product_uom_qty": 10.0,
            }
        )

        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location
            ),
            150.0,
        )

        move1._action_confirm()
        self.assertEqual(move1.state, "confirmed")

        move1._action_assign()
        self.assertEqual(move1.state, "assigned")
        self.assertEqual(len(move1.move_line_ids), 1)
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location
            ),
            30.0,
        )

        move1._unreserve()
        self.assertEqual(len(move1.move_line_ids), 0)
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location
            ),
            150.0,
        )
        self.assertEqual(move1.state, "confirmed")

    def test_unreserve_2(self):
        package1 = self.env["stock.package"].create({"name": "test_unreserve_2_pack"})

        self.env["stock.quant"]._update_available_quantity(
            self.productA, self.stock_location, 150.0, package_id=package1
        )

        move1 = self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.supplier_location.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 100.0,
            }
        )

        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location, package_id=package1
            ),
            150.0,
        )

        move1._action_confirm()
        self.assertEqual(move1.state, "confirmed")

        move1._action_assign()
        self.assertEqual(move1.state, "assigned")
        self.assertEqual(len(move1.move_line_ids), 1)
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location, package_id=package1
            ),
            50.0,
        )

        move1._unreserve()
        self.assertEqual(len(move1.move_line_ids), 0)
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location, package_id=package1
            ),
            150.0,
        )
        self.assertEqual(move1.state, "confirmed")

    def test_unreserve_3(self):
        self.env["stock.quant"]._update_available_quantity(
            self.productA, self.stock_location, 2
        )
        self.assertEqual(
            len(self.gather_relevant(self.productA, self.stock_location)), 1.0
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location
            ),
            2,
        )

        move1 = self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 2.0,
            }
        )
        self.assertEqual(move1.state, "draft")

        move1._action_confirm()
        self.assertEqual(move1.state, "confirmed")

        move1._action_assign()
        self.assertEqual(move1.state, "assigned")
        self.assertEqual(len(move1.move_line_ids), 1)

        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location
            ),
            0.0,
        )
        quants = self.gather_relevant(self.productA, self.stock_location)
        self.assertEqual(len(quants), 1.0)
        self.assertEqual(quants.quantity, 2.0)
        self.assertEqual(quants.reserved_quantity, 2.0)

        move1._unreserve()
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location
            ),
            2.0,
        )
        self.assertEqual(len(quants), 1.0)
        self.assertEqual(quants.quantity, 2.0)
        self.assertEqual(quants.reserved_quantity, 0.0)
        self.assertEqual(len(move1.move_line_ids), 0.0)

    def test_unreserve_4(self):
        self.env["stock.quant"]._update_available_quantity(
            self.productA, self.stock_location, 2
        )
        self.assertEqual(
            len(self.gather_relevant(self.productA, self.stock_location)), 1.0
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location
            ),
            2,
        )

        move1 = self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 3.0,
            }
        )
        self.assertEqual(move1.state, "draft")

        move1._action_confirm()
        self.assertEqual(move1.state, "confirmed")

        move1._action_assign()
        self.assertEqual(move1.state, "partially_available")
        self.assertEqual(len(move1.move_line_ids), 1)

        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location
            ),
            0.0,
        )
        quants = self.gather_relevant(self.productA, self.stock_location)
        self.assertEqual(len(quants), 1.0)
        self.assertEqual(quants.quantity, 2.0)
        self.assertEqual(quants.reserved_quantity, 2.0)

        move1._unreserve()
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location
            ),
            2.0,
        )
        self.assertEqual(len(quants), 1.0)
        self.assertEqual(quants.quantity, 2.0)
        self.assertEqual(quants.reserved_quantity, 0.0)
        self.assertEqual(len(move1.move_line_ids), 0.0)

    def test_unreserve_5(self):
        self.env["stock.quant"]._update_available_quantity(
            self.productA, self.stock_location, 3
        )
        self.env["stock.quant"].create(
            {
                "product_id": self.productA.id,
                "location_id": self.stock_location.id,
                "quantity": 2,
            }
        )
        self.assertEqual(
            len(self.gather_relevant(self.productA, self.stock_location)), 2
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location
            ),
            5,
        )

        move1 = self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 5.0,
            }
        )
        self.assertEqual(move1.state, "draft")

        move1._action_confirm()
        self.assertEqual(move1.state, "confirmed")

        move1._action_assign()
        self.assertEqual(move1.state, "assigned")
        self.assertEqual(len(move1.move_line_ids), 1)
        move1._unreserve()

        quants = self.gather_relevant(self.productA, self.stock_location)
        self.assertEqual(len(quants), 2.0)
        for quant in quants:
            self.assertEqual(quant.reserved_quantity, 0)

    def test_unreserve_6(self):
        q1 = self.env["stock.quant"].create(
            {
                "product_id": self.productA.id,
                "location_id": self.stock_location.id,
                "quantity": -10,
                "reserved_quantity": 0,
            }
        )

        q2 = self.env["stock.quant"].create(
            {
                "product_id": self.productA.id,
                "location_id": self.stock_location.id,
                "quantity": 30.0,
                "reserved_quantity": 10.0,
            }
        )

        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location
            ),
            10.0,
        )

        move1 = self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 10.0,
            }
        )
        move1._action_confirm()
        move1._action_assign()
        self.assertEqual(move1.state, "assigned")
        self.assertEqual(len(move1.move_line_ids), 1)
        self.assertEqual(move1.move_line_ids.quantity_product_uom, 10)
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location
            ),
            0.0,
        )
        self.assertEqual(q1.reserved_quantity + q2.reserved_quantity, 20)

        move1._unreserve()
        self.assertEqual(move1.state, "confirmed")
        self.assertEqual(len(move1.move_line_ids), 0)
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location
            ),
            10.0,
        )
        self.assertEqual(q1.reserved_quantity + q2.reserved_quantity, 10)

    def test_link_assign_1(self):
        self.env["stock.quant"]._update_available_quantity(
            self.productA, self.stock_location, 1.0
        )
        self.assertEqual(
            len(self.gather_relevant(self.productA, self.stock_location)), 1.0
        )

        move_stock_pack = self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.pack_location.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 1.0,
            }
        )
        move_pack_cust = self.env["stock.move"].create(
            {
                "location_id": self.pack_location.id,
                "location_dest_id": self.customer_location.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 1.0,
            }
        )
        move_stock_pack.write({"move_dest_ids": [(4, move_pack_cust.id, 0)]})
        move_pack_cust.write({"move_orig_ids": [(4, move_stock_pack.id, 0)]})

        (move_stock_pack + move_pack_cust)._action_confirm()
        move_stock_pack._action_assign()
        move_stock_pack.move_line_ids[0].quantity = 1.0
        move_stock_pack.picked = True
        move_stock_pack._action_done()
        self.assertEqual(len(move_pack_cust.move_line_ids), 1)
        move_line = move_pack_cust.move_line_ids[0]
        self.assertEqual(move_line.location_id.id, self.pack_location.id)
        self.assertEqual(move_line.location_dest_id.id, self.customer_location.id)
        self.assertEqual(move_pack_cust.state, "assigned")

    def test_link_assign_2(self):
        lot1 = self.env["stock.lot"].create(
            {
                "name": "lot1",
                "product_id": self.productA.id,
            }
        )

        self.env["stock.quant"]._update_available_quantity(
            self.productA, self.stock_location, 1.0, lot_id=lot1
        )
        self.assertEqual(
            len(self.gather_relevant(self.productA, self.stock_location, lot1)), 1.0
        )

        move_stock_pack = self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.pack_location.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 1.0,
            }
        )
        move_pack_cust = self.env["stock.move"].create(
            {
                "location_id": self.pack_location.id,
                "location_dest_id": self.customer_location.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 1.0,
            }
        )
        move_stock_pack.write({"move_dest_ids": [(4, move_pack_cust.id, 0)]})
        move_pack_cust.write({"move_orig_ids": [(4, move_stock_pack.id, 0)]})

        (move_stock_pack + move_pack_cust)._action_confirm()
        move_stock_pack._action_assign()

        move_line_stock_pack = move_stock_pack.move_line_ids[0]
        self.assertEqual(move_line_stock_pack.lot_id.id, lot1.id)
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location, lot_id=lot1
            ),
            0.0,
        )
        self.assertEqual(
            len(self.gather_relevant(self.productA, self.stock_location, lot1)), 1.0
        )
        self.assertEqual(
            len(self.gather_relevant(self.productA, self.pack_location, lot1)), 0.0
        )

        move_line_stock_pack.quantity = 1.0
        move_stock_pack.picked = True
        move_stock_pack._action_done()
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location, lot_id=lot1
            ),
            0.0,
        )
        self.assertEqual(
            len(self.gather_relevant(self.productA, self.stock_location, lot1)), 0.0
        )

        move_line_pack_cust = move_pack_cust.move_line_ids[0]
        self.assertEqual(move_line_pack_cust.lot_id.id, lot1.id)
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.pack_location, lot_id=lot1
            ),
            0.0,
        )
        self.assertEqual(
            len(self.gather_relevant(self.productA, self.pack_location, lot1)), 1.0
        )

    def test_link_assign_3(self):
        self.env["stock.quant"]._update_available_quantity(
            self.productA, self.stock_location, 2.0
        )
        self.assertEqual(
            len(self.gather_relevant(self.productA, self.stock_location)), 1.0
        )

        move_stock_pack_1 = self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.pack_location.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 1.0,
            }
        )
        move_stock_pack_2 = self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.pack_location.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 1.0,
            }
        )
        move_pack_cust = self.env["stock.move"].create(
            {
                "location_id": self.pack_location.id,
                "location_dest_id": self.customer_location.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 2.0,
            }
        )
        move_stock_pack_1.write({"move_dest_ids": [(4, move_pack_cust.id, 0)]})
        move_stock_pack_2.write({"move_dest_ids": [(4, move_pack_cust.id, 0)]})
        move_pack_cust.write(
            {
                "move_orig_ids": [
                    (4, move_stock_pack_1.id, 0),
                    (4, move_stock_pack_2.id, 0),
                ]
            }
        )

        (move_stock_pack_1 + move_stock_pack_2 + move_pack_cust)._action_confirm()

        move_stock_pack_1._action_assign()
        self.assertEqual(move_stock_pack_1.state, "assigned")
        self.assertEqual(len(move_stock_pack_1.move_line_ids), 1)
        move_stock_pack_1.move_line_ids[0].quantity = 1.0
        move_stock_pack_1.picked = True
        move_stock_pack_1._action_done()
        self.assertEqual(move_stock_pack_1.state, "done")

        self.assertEqual(move_pack_cust.state, "partially_available")
        self.assertEqual(len(move_pack_cust.move_line_ids), 1)
        self.assertEqual(
            len(self.gather_relevant(self.productA, self.stock_location)), 1.0
        )
        self.assertEqual(
            len(self.gather_relevant(self.productA, self.pack_location)), 1.0
        )

        move_stock_pack_2._action_assign()
        self.assertEqual(move_stock_pack_2.state, "assigned")
        self.assertEqual(len(move_stock_pack_2.move_line_ids), 1)
        move_stock_pack_2.move_line_ids[0].quantity = 1.0
        move_stock_pack_2.picked = True
        move_stock_pack_2._action_done()
        self.assertEqual(move_stock_pack_2.state, "done")

        self.assertEqual(
            len(self.gather_relevant(self.productA, self.stock_location)), 0.0
        )
        self.assertEqual(
            len(self.gather_relevant(self.productA, self.pack_location)), 1.0
        )

        self.assertEqual(move_pack_cust.state, "assigned")
        self.assertEqual(len(move_pack_cust.move_line_ids), 1)
        move_line_1 = move_pack_cust.move_line_ids[0]
        self.assertEqual(move_line_1.location_id.id, self.pack_location.id)
        self.assertEqual(move_line_1.location_dest_id.id, self.customer_location.id)
        self.assertEqual(move_line_1.quantity_product_uom, 2.0)
        self.assertEqual(move_pack_cust.state, "assigned")

    def test_link_assign_4(self):
        lot1 = self.env["stock.lot"].create(
            {
                "name": "lot1",
                "product_id": self.productA.id,
            }
        )

        self.env["stock.quant"]._update_available_quantity(
            self.productA, self.stock_location, 2.0, lot_id=lot1
        )
        self.assertEqual(
            len(self.gather_relevant(self.productA, self.stock_location, lot1)), 1.0
        )

        move_stock_pack_1 = self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.pack_location.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 1.0,
            }
        )
        move_stock_pack_2 = self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.pack_location.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 1.0,
            }
        )
        move_pack_cust = self.env["stock.move"].create(
            {
                "location_id": self.pack_location.id,
                "location_dest_id": self.customer_location.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 2.0,
            }
        )
        move_stock_pack_1.write({"move_dest_ids": [(4, move_pack_cust.id, 0)]})
        move_stock_pack_2.write({"move_dest_ids": [(4, move_pack_cust.id, 0)]})
        move_pack_cust.write(
            {
                "move_orig_ids": [
                    (4, move_stock_pack_1.id, 0),
                    (4, move_stock_pack_2.id, 0),
                ]
            }
        )

        (move_stock_pack_1 + move_stock_pack_2 + move_pack_cust)._action_confirm()

        move_stock_pack_1._action_assign()
        self.assertEqual(len(move_stock_pack_1.move_line_ids), 1)
        self.assertEqual(move_stock_pack_1.move_line_ids[0].lot_id.id, lot1.id)
        move_stock_pack_1.move_line_ids[0].quantity = 1.0
        move_stock_pack_1.picked = True
        move_stock_pack_1._action_done()

        self.assertEqual(len(move_pack_cust.move_line_ids), 1)

        move_stock_pack_2._action_assign()
        self.assertEqual(len(move_stock_pack_2.move_line_ids), 1)
        self.assertEqual(move_stock_pack_2.move_line_ids[0].lot_id.id, lot1.id)
        move_stock_pack_2.move_line_ids[0].quantity = 1.0
        move_stock_pack_2.picked = True
        move_stock_pack_2._action_done()

        self.assertEqual(len(move_pack_cust.move_line_ids), 1)
        move_line_1 = move_pack_cust.move_line_ids[0]
        self.assertEqual(move_line_1.location_id.id, self.pack_location.id)
        self.assertEqual(move_line_1.location_dest_id.id, self.customer_location.id)
        self.assertEqual(move_line_1.quantity_product_uom, 2.0)
        self.assertEqual(move_line_1.lot_id.id, lot1.id)
        self.assertEqual(move_pack_cust.state, "assigned")

    def test_link_assign_5(self):
        self.env["stock.quant"]._update_available_quantity(
            self.productA, self.stock_location, 2.0
        )

        move_stock_pack = self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.pack_location.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 2.0,
            }
        )
        move_pack_cust_1 = self.env["stock.move"].create(
            {
                "location_id": self.pack_location.id,
                "location_dest_id": self.customer_location.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 1.0,
            }
        )
        move_pack_cust_2 = self.env["stock.move"].create(
            {
                "location_id": self.pack_location.id,
                "location_dest_id": self.customer_location.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 1.0,
            }
        )
        move_stock_pack.write(
            {
                "move_dest_ids": [
                    (4, move_pack_cust_1.id, 0),
                    (4, move_pack_cust_2.id, 0),
                ]
            }
        )
        move_pack_cust_1.write({"move_orig_ids": [(4, move_stock_pack.id, 0)]})
        move_pack_cust_2.write({"move_orig_ids": [(4, move_stock_pack.id, 0)]})

        (move_stock_pack + move_pack_cust_1 + move_pack_cust_2)._action_confirm()

        move_stock_pack._action_assign()
        self.assertEqual(len(move_stock_pack.move_line_ids), 1)
        move_stock_pack.move_line_ids[0].quantity = 2.0
        move_stock_pack.picked = True
        move_stock_pack._action_done()

        self.assertEqual(len(move_pack_cust_1.move_line_ids), 1)
        self.assertEqual(len(move_pack_cust_2.move_line_ids), 1)

        move_pack_cust_1.move_line_ids[0].quantity = 1.0
        move_pack_cust_2.move_line_ids[0].quantity = 1.0
        (move_pack_cust_1 + move_pack_cust_2).picked = True
        (move_pack_cust_1 + move_pack_cust_2)._action_done()

    def test_link_assign_6(self):
        move_supp_stock_1 = self.env["stock.move"].create(
            {
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 3.0,
            }
        )
        move_supp_stock_2 = self.env["stock.move"].create(
            {
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 2.0,
            }
        )
        move_stock_stock_1 = self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.stock_location.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 3.0,
            }
        )
        move_stock_stock_1.write(
            {
                "move_orig_ids": [
                    (4, move_supp_stock_1.id, 0),
                    (4, move_supp_stock_2.id, 0),
                ]
            }
        )
        move_stock_stock_2 = self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.stock_location.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 3.0,
            }
        )
        move_stock_stock_2.write(
            {
                "move_orig_ids": [
                    (4, move_supp_stock_1.id, 0),
                    (4, move_supp_stock_2.id, 0),
                ]
            }
        )

        (
            move_supp_stock_1
            + move_supp_stock_2
            + move_stock_stock_1
            + move_stock_stock_2
        )._action_confirm()
        move_supp_stock_1._action_assign()
        self.assertEqual(move_supp_stock_1.state, "assigned")
        self.assertEqual(move_supp_stock_2.state, "assigned")
        self.assertEqual(move_stock_stock_1.state, "waiting")
        self.assertEqual(move_stock_stock_2.state, "waiting")
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location
            ),
            0.0,
        )

        move_supp_stock_1.move_line_ids.quantity = 3.0
        move_supp_stock_1.picked = True
        move_supp_stock_1._action_done()
        self.assertEqual(move_supp_stock_1.state, "done")
        self.assertEqual(move_supp_stock_2.state, "assigned")
        self.assertEqual(move_stock_stock_1.state, "assigned")
        self.assertEqual(move_stock_stock_2.state, "waiting")

    def test_link_assign_7(self):
        picking_stock_pack = self.env["stock.picking"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.pack_location.id,
                "picking_type_id": self.picking_type_int.id,
                "state": "draft",
            }
        )
        move_stock_pack = self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.pack_location.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_dozen.id,
                "product_uom_qty": 1.0,
                "picking_id": picking_stock_pack.id,
            }
        )
        picking_pack_cust = self.env["stock.picking"].create(
            {
                "location_id": self.pack_location.id,
                "location_dest_id": self.customer_location.id,
                "picking_type_id": self.picking_type_out.id,
                "state": "draft",
            }
        )
        move_pack_cust = self.env["stock.move"].create(
            {
                "location_id": self.pack_location.id,
                "location_dest_id": self.customer_location.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_dozen.id,
                "product_uom_qty": 1.0,
                "picking_id": picking_pack_cust.id,
            }
        )
        move_stock_pack.write({"move_dest_ids": [(4, move_pack_cust.id, 0)]})
        move_pack_cust.write({"move_orig_ids": [(4, move_stock_pack.id, 0)]})
        (move_stock_pack + move_pack_cust)._action_confirm()

        move_stock_pack._action_assign()
        self.assertEqual(move_stock_pack.state, "confirmed")
        move_pack_cust._action_assign()
        self.assertEqual(move_pack_cust.state, "waiting")

        move_stock_pack.write(
            {
                "move_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.productA.id,
                            "product_uom_id": self.uom_unit.id,
                            "quantity": 6,
                            "lot_id": False,
                            "package_id": False,
                            "result_package_id": False,
                            "location_id": move_stock_pack.location_id.id,
                            "location_dest_id": move_stock_pack.location_dest_id.id,
                            "picking_id": picking_stock_pack.id,
                        },
                    )
                ]
            }
        )

        self.assertEqual(move_stock_pack.quantity, 0.5)
        move_stock_pack.picked = True

        Form.from_action(
            self.env, picking_stock_pack.button_validate()
        ).save().process()
        self.assertEqual(move_stock_pack.state, "done")
        self.assertEqual(move_stock_pack.quantity, 0.5)
        self.assertEqual(move_stock_pack.product_uom_qty, 0.5)

        move_pack_cust._action_assign()
        self.assertEqual(move_pack_cust.state, "partially_available")
        move_line_pack_cust = move_pack_cust.move_line_ids
        self.assertEqual(move_line_pack_cust.quantity, 0.5)
        self.assertEqual(move_line_pack_cust.product_uom_id.id, self.uom_dozen.id)

        backorder = self.env["stock.picking"].search(
            [("backorder_id", "=", picking_stock_pack.id)]
        )
        backorder.move_ids.write(
            {
                "move_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.productA.id,
                            "product_uom_id": self.uom_dozen.id,
                            "quantity": 1,
                            "lot_id": False,
                            "package_id": False,
                            "result_package_id": False,
                            "location_id": backorder.location_id.id,
                            "location_dest_id": backorder.location_dest_id.id,
                            "picking_id": backorder.id,
                        },
                    )
                ]
            }
        )
        backorder.move_ids.picked = True
        backorder.button_validate()
        backorder_move = backorder.move_ids
        self.assertEqual(backorder_move.state, "done")
        self.assertEqual(backorder_move.quantity, 1)
        self.assertEqual(backorder_move.product_uom_qty, 0.5)
        self.assertEqual(backorder_move.product_uom_id, self.uom_dozen)

        move_pack_cust._action_assign()
        self.assertEqual(move_pack_cust.state, "assigned")
        self.assertEqual(move_line_pack_cust.quantity, 1)
        self.assertEqual(move_line_pack_cust.product_uom_id.id, self.uom_dozen.id)
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, move_stock_pack.location_dest_id
            ),
            6,
        )

    def test_link_assign_8(self):
        for i in range(1, 13):
            lot_id = self.env["stock.lot"].create(
                {
                    "name": "lot%s" % str(i),
                    "product_id": self.product_serial.id,
                }
            )
            self.env["stock.quant"]._update_available_quantity(
                self.product_serial, self.stock_location, 1.0, lot_id=lot_id
            )

        picking_stock_pack = self.env["stock.picking"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.pack_location.id,
                "picking_type_id": self.picking_type_int.id,
                "state": "draft",
            }
        )
        move_stock_pack = self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.pack_location.id,
                "product_id": self.product_serial.id,
                "product_uom_id": self.uom_dozen.id,
                "product_uom_qty": 1.0,
                "picking_id": picking_stock_pack.id,
            }
        )
        picking_pack_cust = self.env["stock.picking"].create(
            {
                "location_id": self.pack_location.id,
                "location_dest_id": self.customer_location.id,
                "picking_type_id": self.picking_type_out.id,
                "state": "draft",
            }
        )
        move_pack_cust = self.env["stock.move"].create(
            {
                "location_id": self.pack_location.id,
                "location_dest_id": self.customer_location.id,
                "product_id": self.product_serial.id,
                "product_uom_id": self.uom_dozen.id,
                "product_uom_qty": 1.0,
                "picking_id": picking_pack_cust.id,
            }
        )
        move_stock_pack.write({"move_dest_ids": [(4, move_pack_cust.id, 0)]})
        move_pack_cust.write({"move_orig_ids": [(4, move_stock_pack.id, 0)]})
        (move_stock_pack + move_pack_cust)._action_confirm()

        move_stock_pack._action_assign()
        self.assertEqual(move_stock_pack.state, "assigned")
        move_pack_cust._action_assign()
        self.assertEqual(move_pack_cust.state, "waiting")

        for ml in move_stock_pack.move_line_ids:
            ml.quantity = 1
        move_stock_pack.picked = True
        picking_stock_pack.button_validate()
        self.assertEqual(move_pack_cust.state, "assigned")
        for ml in move_pack_cust.move_line_ids:
            self.assertEqual(ml.quantity, 1)
            self.assertEqual(ml.product_uom_id.id, self.uom_unit.id)
            self.assertTrue(bool(ml.lot_id.id))

    def test_link_assign_9(self):
        uom_3units = self.env["uom.uom"].create(
            {
                "name": "3 units",
                "relative_factor": 3,
                "relative_uom_id": self.uom_unit.id,
            }
        )
        for i in range(1, 4):
            lot_id = self.env["stock.lot"].create(
                {
                    "name": "lot%s" % str(i),
                    "product_id": self.product_serial.id,
                }
            )
            self.env["stock.quant"]._update_available_quantity(
                self.product_serial, self.stock_location, 1.0, lot_id=lot_id
            )

        picking_stock_pack = self.env["stock.picking"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.pack_location.id,
                "picking_type_id": self.picking_type_int.id,
                "state": "draft",
            }
        )
        move_stock_pack = self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.pack_location.id,
                "product_id": self.product_serial.id,
                "product_uom_id": uom_3units.id,
                "product_uom_qty": 1.0,
                "picking_id": picking_stock_pack.id,
            }
        )
        picking_pack_cust = self.env["stock.picking"].create(
            {
                "location_id": self.pack_location.id,
                "location_dest_id": self.customer_location.id,
                "picking_type_id": self.picking_type_out.id,
                "state": "draft",
            }
        )
        move_pack_cust = self.env["stock.move"].create(
            {
                "location_id": self.pack_location.id,
                "location_dest_id": self.customer_location.id,
                "product_id": self.product_serial.id,
                "product_uom_id": uom_3units.id,
                "product_uom_qty": 1.0,
                "picking_id": picking_pack_cust.id,
            }
        )
        move_stock_pack.write({"move_dest_ids": [(4, move_pack_cust.id, 0)]})
        move_pack_cust.write({"move_orig_ids": [(4, move_stock_pack.id, 0)]})
        (move_stock_pack + move_pack_cust)._action_confirm()

        picking_stock_pack.action_assign()
        picking_stock_pack.move_ids.picked = True
        picking_stock_pack.button_validate()
        self.assertEqual(picking_pack_cust.state, "assigned")
        for ml in picking_pack_cust.move_ids.move_line_ids:
            if ml.lot_id.name == "lot3":
                ml.quantity = 0
        picking_pack_cust.move_ids.picked = True
        res_dict_for_back_order = picking_pack_cust.button_validate()
        backorder_wizard = (
            self.env[(res_dict_for_back_order.get("res_model"))]
            .browse(res_dict_for_back_order.get("res_id"))
            .with_context(res_dict_for_back_order["context"])
        )
        backorder_wizard.process()
        backorder = self.env["stock.picking"].search(
            [("backorder_id", "=", picking_pack_cust.id)]
        )
        backordered_move = backorder.move_ids

        backordered_move._action_assign()
        self.assertEqual(backordered_move.quantity, 0)

        lot3 = self.env["stock.lot"].search([("name", "=", "lot3")])
        backorder.write(
            {
                "move_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product_serial.id,
                            "product_uom_id": self.uom_unit.id,
                            "quantity": 1,
                            "lot_id": lot3.id,
                            "package_id": False,
                            "result_package_id": False,
                            "location_id": backordered_move.location_id.id,
                            "location_dest_id": backordered_move.location_dest_id.id,
                            "move_id": backordered_move.id,
                        },
                    )
                ]
            }
        )
        backorder.move_ids.picked = True
        backorder.button_validate()

        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.product_serial, self.customer_location
            ),
            3,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.product_serial, self.pack_location
            ),
            0,
        )

    def test_link_assign_10(self):
        self.env["stock.quant"]._update_available_quantity(
            self.productA, self.stock_location, 2.0
        )
        self.assertEqual(
            len(self.gather_relevant(self.productA, self.stock_location)), 1.0
        )

        move_out = self.env["stock.move"].create(
            {
                "location_id": self.pack_location.id,
                "location_dest_id": self.customer_location.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 1.0,
            }
        )
        move_out._action_confirm()
        move_out._action_assign()
        move_out.quantity = 1.0
        move_out.picked = True
        move_out._action_done()
        self.assertEqual(
            len(self.gather_relevant(self.productA, self.pack_location)), 1.0
        )

        move_stock_pack = self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.pack_location.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 2.0,
            }
        )
        move_pack_cust = self.env["stock.move"].create(
            {
                "location_id": self.pack_location.id,
                "location_dest_id": self.customer_location.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 2.0,
            }
        )
        move_stock_pack.write({"move_dest_ids": [(4, move_pack_cust.id, 0)]})
        move_pack_cust.write({"move_orig_ids": [(4, move_stock_pack.id, 0)]})

        (move_stock_pack + move_pack_cust)._action_confirm()
        move_stock_pack._action_assign()
        move_stock_pack.quantity = 2.0
        move_stock_pack.picked = True
        move_stock_pack._action_done()
        self.assertEqual(len(move_pack_cust.move_line_ids), 1)

        self.assertAlmostEqual(move_pack_cust.quantity, 1.0)
        self.assertEqual(move_pack_cust.state, "partially_available")

    def test_use_reserved_move_line_1(self):
        self.env["stock.quant"]._update_available_quantity(
            self.productA, self.stock_location, 10.0
        )
        move1 = self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 5.0,
            }
        )
        move2 = self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 5.0,
            }
        )
        move1._action_confirm()
        move1._action_assign()
        move2._action_confirm()
        move2._action_assign()
        move3 = self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 0.0,
                "quantity": 1.0,
            }
        )
        move3._action_confirm()
        move3._action_assign()
        move3.picked = True
        move3._action_done()
        self.assertEqual(move3.state, "done")
        quant = self.env["stock.quant"]._gather(self.productA, self.stock_location)
        self.assertEqual(quant.quantity, 9.0)
        self.assertEqual(quant.reserved_quantity, 9.0)

    def test_use_reserved_move_line_2(self):
        self.env["stock.quant"]._update_available_quantity(
            self.productA, self.stock_location, 12.0
        )

        move1 = self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 12,
            }
        )
        move1._action_confirm()
        move1._action_assign()
        self.assertEqual(move1.state, "assigned")
        quant = self.env["stock.quant"]._gather(self.productA, self.stock_location)
        self.assertEqual(quant.quantity, 12)
        self.assertEqual(quant.reserved_quantity, 12)

        move2 = self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_dozen.id,
                "product_uom_qty": 1,
            }
        )
        move2._action_confirm()
        move2._action_assign()
        self.assertEqual(move2.state, "confirmed")
        move2.quantity = 1
        move2.picked = True
        move2._action_done()

        self.assertEqual(move1.state, "confirmed")
        quant = self.env["stock.quant"]._gather(self.productA, self.stock_location)
        self.assertEqual(quant.quantity, 0)
        self.assertEqual(quant.reserved_quantity, 0)

    def test_use_unreserved_move_line_1(self):
        self.env["stock.quant"]._update_available_quantity(
            self.productA, self.stock_location, 1.0
        )

        move1 = self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 1.0,
            }
        )
        move2 = self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 1.0,
            }
        )

        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location
            ),
            1.0,
        )
        move1._action_confirm()
        move1._action_assign()
        self.assertEqual(move1.state, "assigned")
        move2._action_confirm()
        move2._action_assign()
        self.assertEqual(move2.state, "confirmed")

        move2.write(
            {
                "move_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.productA.id,
                            "product_uom_id": self.uom_unit.id,
                            "quantity": 1,
                            "lot_id": False,
                            "package_id": False,
                            "result_package_id": False,
                            "location_id": move2.location_id.id,
                            "location_dest_id": move2.location_dest_id.id,
                        },
                    )
                ]
            }
        )
        move2.picked = True
        move2._action_done()

        self.assertEqual(move1.state, "confirmed")
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location
            ),
            0.0,
        )

    def test_use_unreserved_move_line_2(self):
        lot1 = self.env["stock.lot"].create(
            {
                "name": "lot1",
                "product_id": self.productA.id,
            }
        )

        self.env["stock.quant"]._update_available_quantity(
            self.productA, self.stock_location, 1.0, lot_id=lot1
        )

        move1 = self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 1.0,
            }
        )
        move2 = self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 1.0,
            }
        )

        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location, lot_id=lot1
            ),
            1.0,
        )
        move1._action_confirm()
        move1._action_assign()
        self.assertEqual(move1.state, "assigned")
        move2._action_confirm()
        move2._action_assign()
        self.assertEqual(move2.state, "confirmed")

        move2.write(
            {
                "move_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.productA.id,
                            "product_uom_id": self.uom_unit.id,
                            "quantity": 1,
                            "lot_id": lot1.id,
                            "package_id": False,
                            "result_package_id": False,
                            "location_id": move2.location_id.id,
                            "location_dest_id": move2.location_dest_id.id,
                        },
                    )
                ]
            }
        )
        move2.picked = True
        move2._action_done()

        self.assertEqual(move1.state, "confirmed")
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location, lot_id=lot1
            ),
            0.0,
        )

    def test_use_unreserved_move_line_3(self):
        self.env["stock.quant"]._update_available_quantity(
            self.productA, self.stock_location, 1.0
        )

        move1 = self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 3.0,
            }
        )
        move1._action_confirm()
        move1._action_assign()
        move1.quantity = 1

        move1.write(
            {
                "move_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.productA.id,
                            "product_uom_id": self.uom_unit.id,
                            "quantity": 2,
                            "lot_id": False,
                            "package_id": False,
                            "result_package_id": False,
                            "location_id": move1.location_id.id,
                            "location_dest_id": move1.location_dest_id.id,
                        },
                    )
                ]
            }
        )
        move1.picked = True
        move1._action_done()

        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.customer_location
            ),
            3.0,
        )

    def test_use_unreserved_move_line_4(self):
        product_01 = self.env["product.product"].create(
            {
                "name": "Product 01",
                "is_storable": True,
            }
        )
        product_02 = self.env["product.product"].create(
            {
                "name": "Product 02",
                "is_storable": True,
            }
        )
        self.env["stock.quant"]._update_available_quantity(
            product_01, self.stock_location, 1
        )
        self.env["stock.quant"]._update_available_quantity(
            product_02, self.stock_location, 1
        )

        picking = self.env["stock.picking"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "partner_id": self.partner_1.id,
                "picking_type_id": self.picking_type_out.id,
                "state": "draft",
            }
        )

        p01_move = self.env["stock.move"].create(
            {
                "location_id": picking.location_id.id,
                "location_dest_id": picking.location_dest_id.id,
                "picking_id": picking.id,
                "product_id": product_01.id,
                "product_uom_qty": 1,
                "product_uom_id": product_01.uom_id.id,
            }
        )
        self.env["stock.move"].create(
            {
                "location_id": picking.location_id.id,
                "location_dest_id": picking.location_dest_id.id,
                "picking_id": picking.id,
                "product_id": product_02.id,
                "product_uom_qty": 1,
                "product_uom_id": product_02.uom_id.id,
            }
        )

        picking.action_confirm()
        picking.action_assign()
        p01_move.product_uom_qty = 0
        picking.action_unreserve()
        picking.action_assign()
        p01_move.product_uom_qty = 1
        self.assertEqual(p01_move.state, "confirmed")

    def test_edit_reserved_move_line_1(self):
        self.env["stock.quant"]._update_available_quantity(
            self.productA, self.shelf_1, 1.0
        )
        self.env["stock.quant"]._update_available_quantity(
            self.productA, self.shelf_2, 1.0
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.shelf_1
            ),
            1.0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.shelf_2
            ),
            1.0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location
            ),
            2.0,
        )

        move1 = self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 1.0,
            }
        )
        move1._action_confirm()
        move1._action_assign()

        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.shelf_1
            ),
            0.0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.shelf_2
            ),
            1.0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location
            ),
            1.0,
        )

        move1.move_line_ids.location_id = self.shelf_2

        self.assertEqual(move1.quantity, 1.0)
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.shelf_1
            ),
            1.0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.shelf_2
            ),
            0.0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location
            ),
            1.0,
        )

    def test_edit_reserved_move_line_2(self):
        lot1 = self.env["stock.lot"].create(
            {
                "name": "lot1",
                "product_id": self.productA.id,
            }
        )
        lot2 = self.env["stock.lot"].create(
            {
                "name": "lot2",
                "product_id": self.productA.id,
            }
        )
        self.env["stock.quant"]._update_available_quantity(
            self.productA, self.stock_location, 1.0, lot_id=lot1
        )
        self.env["stock.quant"]._update_available_quantity(
            self.productA, self.stock_location, 1.0, lot_id=lot2
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location
            ),
            2.0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location, lot_id=lot1
            ),
            1.0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location, lot_id=lot2
            ),
            1.0,
        )

        move1 = self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 1.0,
            }
        )
        move1._action_confirm()
        move1._action_assign()

        self.assertEqual(move1.quantity, 1.0)
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location
            ),
            1.0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location, lot_id=lot1
            ),
            0.0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location, lot_id=lot2
            ),
            1.0,
        )

        move1.move_line_ids.lot_id = lot2.id

        self.assertEqual(move1.quantity, 1.0)
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location
            ),
            1.0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location, lot_id=lot1
            ),
            1.0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location, lot_id=lot2
            ),
            0.0,
        )

    def test_edit_reserved_move_line_3(self):
        package1 = self.env["stock.package"].create(
            {"name": "test_edit_reserved_move_line_3"}
        )
        package2 = self.env["stock.package"].create(
            {"name": "test_edit_reserved_move_line_3"}
        )

        self.env["stock.quant"]._update_available_quantity(
            self.productA, self.stock_location, 1.0, package_id=package1
        )
        self.env["stock.quant"]._update_available_quantity(
            self.productA, self.stock_location, 1.0, package_id=package2
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location
            ),
            2.0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location, package_id=package1
            ),
            1.0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location, package_id=package2
            ),
            1.0,
        )

        move1 = self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 1.0,
            }
        )
        move1._action_confirm()
        move1._action_assign()

        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location
            ),
            1.0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location, package_id=package1
            ),
            0.0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location, package_id=package2
            ),
            1.0,
        )

        move1.move_line_ids.package_id = package2.id

        self.assertEqual(move1.quantity, 1.0)
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location
            ),
            1.0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location, package_id=package1
            ),
            1.0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location, package_id=package2
            ),
            0.0,
        )

    def test_edit_reserved_move_line_4(self):
        self.env["stock.quant"]._update_available_quantity(
            self.productA, self.stock_location, 1.0, owner_id=self.partner_1
        )
        self.env["stock.quant"]._update_available_quantity(
            self.productA, self.stock_location, 1.0, owner_id=self.partner_2
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location
            ),
            2.0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location, owner_id=self.partner_1
            ),
            1.0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location, owner_id=self.partner_2
            ),
            1.0,
        )

        move1 = self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 1.0,
            }
        )
        move1._action_confirm()
        move1._action_assign()

        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location
            ),
            1.0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location, owner_id=self.partner_1
            ),
            0.0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location, owner_id=self.partner_2
            ),
            1.0,
        )

        move1.move_line_ids.owner_id = self.partner_2.id

        self.assertEqual(move1.quantity, 1.0)
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location
            ),
            1.0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location, owner_id=self.partner_1
            ),
            1.0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location, owner_id=self.partner_2
            ),
            0.0,
        )

    def test_edit_reserved_move_line_5(self):
        lot1 = self.env["stock.lot"].create(
            {
                "name": "lot1",
                "product_id": self.productA.id,
            }
        )
        lot2 = self.env["stock.lot"].create(
            {
                "name": "lot2",
                "product_id": self.productA.id,
            }
        )
        package1 = self.env["stock.package"].create(
            {"name": "test_edit_reserved_move_line_5"}
        )

        self.env["stock.quant"]._update_available_quantity(
            self.productA, self.stock_location, 1.0, lot_id=lot1, package_id=package1
        )
        self.env["stock.quant"]._update_available_quantity(
            self.productA, self.stock_location, 1.0, lot_id=lot2
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location
            ),
            2.0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location, lot_id=lot1, package_id=package1
            ),
            1.0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location, lot_id=lot2
            ),
            1.0,
        )

        move1 = self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 1.0,
            }
        )
        move1._action_confirm()
        move1._action_assign()

        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location
            ),
            1.0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location, lot_id=lot1, package_id=package1
            ),
            0.0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location, lot_id=lot2
            ),
            1.0,
        )
        move_line = move1.move_line_ids[0]
        move_line.write({"package_id": False, "lot_id": lot2.id})

        self.assertEqual(move1.quantity, 1.0)
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location
            ),
            1.0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location, lot_id=lot1, package_id=package1
            ),
            1.0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location, lot_id=lot2
            ),
            0.0,
        )

    def test_edit_reserved_move_line_6(self):
        self.env["stock.quant"]._update_available_quantity(
            self.productA, self.shelf_1, 1.0
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location
            ),
            1.0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.shelf_1
            ),
            1.0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.shelf_2
            ),
            0.0,
        )

        move1 = self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 1.0,
            }
        )
        move1._action_confirm()
        move1._action_assign()

        self.assertEqual(move1.move_line_ids.state, "assigned")
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.shelf_1
            ),
            0.0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.shelf_2
            ),
            0.0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location
            ),
            0.0,
        )

        move1.move_line_ids.location_id = self.shelf_2

        self.assertEqual(move1.move_line_ids.state, "assigned")
        self.assertEqual(move1.quantity, 1.0)
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location
            ),
            0.0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.shelf_1
            ),
            1.0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.shelf_2, allow_negative=True
            ),
            -1.0,
        )

    def test_edit_reserved_move_line_7(self):
        lot1 = self.env["stock.lot"].create(
            {
                "name": "lot1",
                "product_id": self.product_lot.id,
            }
        )
        self.env["stock.quant"]._update_available_quantity(
            self.product_lot, self.stock_location, 5
        )

        move1 = self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "product_id": self.product_lot.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 5.0,
            }
        )
        self.assertEqual(move1.state, "draft")

        move1._action_confirm()
        self.assertEqual(move1.state, "confirmed")

        move1._action_assign()
        self.assertEqual(move1.state, "assigned")
        self.assertEqual(len(move1.move_line_ids), 1)
        move_line = move1.move_line_ids[0]
        self.assertEqual(move_line.quantity_product_uom, 5)
        move_line.quantity = 5.0
        self.assertEqual(move_line.quantity_product_uom, 5)
        move_line.lot_id = lot1
        self.assertEqual(move_line.quantity_product_uom, 5)
        move1.picked = True
        move1._action_done()
        self.assertEqual(move_line.quantity_product_uom, 5)
        self.assertEqual(move_line.picked, True)
        self.assertEqual(move1.state, "done")

        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.product_lot, self.stock_location
            ),
            0.0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.product_lot, self.stock_location, lot_id=lot1, strict=True
            ),
            0.0,
        )
        self.assertEqual(
            len(self.gather_relevant(self.product_lot, self.stock_location)), 0.0
        )
        self.assertEqual(
            len(
                self.gather_relevant(
                    self.product_lot, self.stock_location, lot_id=lot1, strict=True
                )
            ),
            0.0,
        )

    def test_edit_reserved_move_line_8(self):
        lot1 = self.env["stock.lot"].create(
            {
                "name": "lot1",
                "product_id": self.product_lot.id,
            }
        )
        lot2 = self.env["stock.lot"].create(
            {
                "name": "lot2",
                "product_id": self.product_lot.id,
            }
        )
        self.env["stock.quant"]._update_available_quantity(
            self.product_lot, self.stock_location, 3
        )
        self.env["stock.quant"]._update_available_quantity(
            self.product_lot, self.stock_location, 2, lot_id=lot1
        )

        move1 = self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "product_id": self.product_lot.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 5.0,
            }
        )
        self.assertEqual(move1.state, "draft")

        move1._action_confirm()
        self.assertEqual(move1.state, "confirmed")

        move1._action_assign()
        self.assertEqual(move1.state, "assigned")
        self.assertEqual(len(move1.move_line_ids), 2)

        tracked_move_line = None
        untracked_move_line = None
        for move_line in move1.move_line_ids:
            if move_line.lot_id:
                tracked_move_line = move_line
            else:
                untracked_move_line = move_line

        self.assertEqual(tracked_move_line.quantity_product_uom, 2)
        tracked_move_line.quantity = 2

        self.assertEqual(untracked_move_line.quantity_product_uom, 3)
        untracked_move_line.lot_id = lot2
        self.assertEqual(untracked_move_line.quantity_product_uom, 3)
        untracked_move_line.quantity = 3
        self.assertEqual(untracked_move_line.quantity_product_uom, 3)
        move1.picked = True
        move1._action_done()
        self.assertEqual(untracked_move_line.quantity_product_uom, 3)
        self.assertEqual(tracked_move_line.quantity_product_uom, 2)
        self.assertEqual(move1.state, "done")

        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.product_lot, self.stock_location
            ),
            0.0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.product_lot, self.stock_location, lot_id=lot1, strict=True
            ),
            0.0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.product_lot, self.stock_location, lot_id=lot2, strict=True
            ),
            0.0,
        )
        self.assertEqual(
            len(self.gather_relevant(self.product_lot, self.stock_location)), 0.0
        )
        self.assertEqual(
            len(
                self.gather_relevant(
                    self.product_lot, self.stock_location, lot_id=lot1, strict=True
                )
            ),
            0.0,
        )
        self.assertEqual(
            len(
                self.gather_relevant(
                    self.product_lot, self.stock_location, lot_id=lot2, strict=True
                )
            ),
            0.0,
        )

    def test_edit_reserved_move_line_9(self):
        self.env["stock.quant"]._update_available_quantity(
            self.productA, self.stock_location, 1.0
        )

        out_move = self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "product_id": self.productA.id,
                "product_uom_qty": 1,
                "product_uom_id": self.productA.uom_id.id,
            }
        )
        out_move._action_confirm()
        out_move._action_assign()

        out_move.move_line_ids.quantity = 2

        self.assertTrue(out_move.move_line_ids)
        self.assertEqual(
            out_move.move_line_ids.quantity, 2, "There is no maximum on reservation"
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location, allow_negative=True
            ),
            -1.0,
        )

    def test_edit_done_move_line_1(self):
        self.env["stock.quant"]._update_available_quantity(
            self.productA, self.shelf_1, 1.0
        )
        self.env["stock.quant"]._update_available_quantity(
            self.productA, self.shelf_2, 1.0
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.shelf_1
            ),
            1.0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.shelf_2
            ),
            1.0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location
            ),
            2.0,
        )

        move1 = self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 1.0,
            }
        )
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.quantity = 1
        move1.picked = True
        move1._action_done()

        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.shelf_1
            ),
            0.0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.shelf_2
            ),
            1.0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location
            ),
            1.0,
        )

        move1.move_line_ids.location_id = self.shelf_2

        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.shelf_1
            ),
            1.0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.shelf_2
            ),
            0.0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location
            ),
            1.0,
        )

    def test_edit_done_move_line_preserves_in_date(self):
        old_date = fields.Datetime.to_datetime("2020-01-01 00:00:00")
        self.env["stock.quant"]._update_available_quantity(
            self.productA, self.shelf_1, 10.0, in_date=old_date
        )
        move = self.env["stock.move"].create(
            {
                "location_id": self.shelf_1.id,
                "location_dest_id": self.shelf_2.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 10.0,
            }
        )
        move._action_confirm()
        move._action_assign()
        move.move_line_ids.quantity = 10.0
        move.picked = True
        move._action_done()

        def dest_quant():
            return (
                self.env["stock.quant"]
                ._gather(self.productA, self.shelf_2)
                .filtered(lambda q: q.quantity > 0)
            )

        self.assertEqual(dest_quant().in_date, old_date)

        move.move_line_ids.quantity = 5.0

        self.assertEqual(dest_quant().quantity, 5.0)
        self.assertEqual(
            dest_quant().in_date,
            old_date,
            "Editing a done move line must preserve the destination quant's incoming date.",
        )

    def test_edit_done_move_line_2(self):
        lot1 = self.env["stock.lot"].create(
            {
                "name": "lot1",
                "product_id": self.productA.id,
            }
        )
        lot2 = self.env["stock.lot"].create(
            {
                "name": "lot2",
                "product_id": self.productA.id,
            }
        )
        self.env["stock.quant"]._update_available_quantity(
            self.productA, self.stock_location, 1.0, lot_id=lot1
        )
        self.env["stock.quant"]._update_available_quantity(
            self.productA, self.stock_location, 1.0, lot_id=lot2
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location
            ),
            2.0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location, lot_id=lot1
            ),
            1.0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location, lot_id=lot2
            ),
            1.0,
        )

        move1 = self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 1.0,
            }
        )
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.quantity = 1
        move1.picked = True
        move1._action_done()

        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location
            ),
            1.0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location, lot_id=lot1
            ),
            0.0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location, lot_id=lot2
            ),
            1.0,
        )

        move1.move_line_ids.lot_id = lot2.id

        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location
            ),
            1.0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location, lot_id=lot1
            ),
            1.0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location, lot_id=lot2
            ),
            0.0,
        )

    def test_edit_done_move_line_3(self):
        package1 = self.env["stock.package"].create(
            {"name": "test_edit_reserved_move_line_3"}
        )
        package2 = self.env["stock.package"].create(
            {"name": "test_edit_reserved_move_line_3"}
        )

        self.env["stock.quant"]._update_available_quantity(
            self.productA, self.stock_location, 1.0, package_id=package1
        )
        self.env["stock.quant"]._update_available_quantity(
            self.productA, self.stock_location, 1.0, package_id=package2
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location
            ),
            2.0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location, package_id=package1
            ),
            1.0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location, package_id=package2
            ),
            1.0,
        )

        move1 = self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 1.0,
            }
        )
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.quantity = 1
        move1.picked = True
        move1._action_done()

        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location
            ),
            1.0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location, package_id=package1
            ),
            0.0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location, package_id=package2
            ),
            1.0,
        )

        move1.move_line_ids.package_id = package2.id

        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location
            ),
            1.0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location, package_id=package1
            ),
            1.0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location, package_id=package2
            ),
            0.0,
        )

    def test_edit_done_move_line_4(self):
        self.env["stock.quant"]._update_available_quantity(
            self.productA, self.stock_location, 1.0, owner_id=self.partner_1
        )
        self.env["stock.quant"]._update_available_quantity(
            self.productA, self.stock_location, 1.0, owner_id=self.partner_2
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location
            ),
            2.0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location, owner_id=self.partner_1
            ),
            1.0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location, owner_id=self.partner_2
            ),
            1.0,
        )

        move1 = self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 1.0,
            }
        )
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.quantity = 1
        move1.picked = True
        move1._action_done()

        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location
            ),
            1.0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location, owner_id=self.partner_1
            ),
            0.0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location, owner_id=self.partner_2
            ),
            1.0,
        )

        move1.move_line_ids.owner_id = self.partner_2.id

        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location
            ),
            1.0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location, owner_id=self.partner_1
            ),
            1.0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location, owner_id=self.partner_2
            ),
            0.0,
        )

    def test_edit_done_move_line_5(self):
        lot1 = self.env["stock.lot"].create(
            {
                "name": "lot1",
                "product_id": self.productA.id,
            }
        )
        lot2 = self.env["stock.lot"].create(
            {
                "name": "lot2",
                "product_id": self.productA.id,
            }
        )
        package1 = self.env["stock.package"].create(
            {"name": "test_edit_reserved_move_line_5"}
        )

        self.env["stock.quant"]._update_available_quantity(
            self.productA, self.stock_location, 1.0, lot_id=lot1, package_id=package1
        )
        self.env["stock.quant"]._update_available_quantity(
            self.productA, self.stock_location, 1.0, lot_id=lot2
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location
            ),
            2.0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location, lot_id=lot1, package_id=package1
            ),
            1.0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location, lot_id=lot2
            ),
            1.0,
        )

        move1 = self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 1.0,
            }
        )
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.quantity = 1
        move1.picked = True
        move1._action_done()

        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location
            ),
            1.0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location, lot_id=lot1, package_id=package1
            ),
            0.0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location, lot_id=lot2
            ),
            1.0,
        )
        move_line = move1.move_line_ids[0]
        move_line.write({"package_id": False, "lot_id": lot2.id})

        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location
            ),
            1.0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location, lot_id=lot1, package_id=package1
            ),
            1.0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location, lot_id=lot2
            ),
            0.0,
        )

    def test_edit_done_move_line_6(self):
        self.env["stock.quant"]._update_available_quantity(
            self.productA, self.shelf_1, 1.0
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location
            ),
            1.0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.shelf_1
            ),
            1.0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.shelf_2
            ),
            0.0,
        )

        move1 = self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 1.0,
            }
        )
        move1._action_confirm()
        move1._action_assign()
        move1.picked = True
        move1._action_done()

        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.shelf_1
            ),
            0.0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.shelf_2
            ),
            0.0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location
            ),
            0.0,
        )

        move1.move_line_ids.location_id = self.shelf_2

        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location
            ),
            0.0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.shelf_1
            ),
            1.0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.shelf_2
            ),
            0.0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.shelf_2, allow_negative=True
            ),
            -1.0,
        )

    def test_edit_done_move_line_7(self):
        self.env["stock.quant"]._update_available_quantity(
            self.productA, self.shelf_1, 1.0
        )
        self.env["stock.quant"]._update_available_quantity(
            self.productA, self.shelf_2, 1.0
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location
            ),
            2.0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.shelf_1
            ),
            1.0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.shelf_2
            ),
            1.0,
        )

        move1 = self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 1.0,
            }
        )
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.quantity = 1
        move1.picked = True
        move1._action_done()

        move2 = self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 1.0,
            }
        )
        move2._action_confirm()
        move2._action_assign()

        self.assertEqual(move2.state, "assigned")
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.shelf_1
            ),
            0.0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.shelf_2
            ),
            0.0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location
            ),
            0.0,
        )

        move1.move_line_ids.location_id = self.shelf_2

        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location
            ),
            0.0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.shelf_1
            ),
            0.0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.shelf_2
            ),
            0.0,
        )
        self.assertEqual(move2.state, "assigned")
        self.assertEqual(move2.move_line_ids.location_id, self.shelf_1)

    def test_edit_done_move_line_8(self):
        self.env["stock.quant"]._update_available_quantity(
            self.productA, self.shelf_1, 1.0
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.shelf_1
            ),
            1.0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location
            ),
            1.0,
        )

        move1 = self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 1.0,
            }
        )
        move1._action_confirm()
        move1._action_assign()
        move1.picked = True
        move1._action_done()

        self.assertEqual(move1.product_uom_qty, 1.0)
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.shelf_1
            ),
            0.0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location
            ),
            0.0,
        )

        move1.move_line_ids.quantity = 2

        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.shelf_1
            ),
            0.0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.shelf_1, allow_negative=True
            ),
            -1.0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location
            ),
            0.0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location, allow_negative=True
            ),
            -1.0,
        )
        self.assertEqual(move1.quantity, 2.0)
        self.assertEqual(move1.product_uom_qty, 1.0)

    def test_edit_done_move_line_9(self):
        self.env["stock.quant"]._update_available_quantity(
            self.productA, self.shelf_1, 1.0
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.shelf_1
            ),
            1.0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location
            ),
            1.0,
        )

        move1 = self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 1.0,
            }
        )
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.quantity = 1
        move1.picked = True
        move1._action_done()

        self.assertEqual(move1.product_uom_qty, 1.0)
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.shelf_1
            ),
            0.0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location
            ),
            0.0,
        )

        move1.move_line_ids.quantity = 0

        self.assertEqual(move1.product_uom_qty, 1.0)
        self.assertEqual(move1.quantity, 0.0)
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.shelf_1
            ),
            1.0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location
            ),
            1.0,
        )

    def test_edit_done_move_line_10(self):
        move1 = self.env["stock.move"].create(
            {
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 10.0,
            }
        )
        move1._action_confirm()
        move1._action_assign()
        move1.picked = True
        move1._action_done()

        quant = self.gather_relevant(self.productA, self.stock_location)
        self.assertEqual(len(quant), 1.0)

        move1.move_line_ids.quantity = 0

        quant = self.gather_relevant(self.productA, self.stock_location)
        self.assertEqual(len(quant), 0.0)
        self.assertEqual(move1.product_uom_qty, 10.0)

    def test_edit_done_move_line_11(self):
        picking = self.env["stock.picking"].create(
            {
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
                "partner_id": self.partner_1.id,
                "picking_type_id": self.picking_type_in.id,
                "state": "draft",
            }
        )
        move1 = self.env["stock.move"].create(
            {
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
                "picking_id": picking.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 10.0,
            }
        )
        picking.action_confirm()
        picking.action_assign()
        picking.move_ids.picked = True
        picking._action_done()
        self.assertEqual(move1.product_uom_qty, 10.0)
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location
            ),
            10.0,
        )
        self.env["stock.move.line"].create(
            {
                "picking_id": move1.move_line_ids.picking_id.id,
                "move_id": move1.move_line_ids.move_id.id,
                "product_id": move1.move_line_ids.product_id.id,
                "quantity": move1.move_line_ids.quantity,
                "product_uom_id": move1.product_uom_id.id,
                "location_id": move1.move_line_ids.location_id.id,
                "location_dest_id": move1.move_line_ids.location_dest_id.id,
            }
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location
            ),
            20.0,
        )
        move1.move_line_ids[1].quantity = 5
        self.assertEqual(move1.quantity, 15.0)
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location
            ),
            15.0,
        )

    def test_edit_done_move_line_12(self):
        lot1 = self.env["stock.lot"].create(
            {
                "name": "lot1",
                "product_id": self.product_lot.id,
            }
        )
        self.env["stock.lot"].create(
            {
                "name": "lot2",
                "product_id": self.product_lot.id,
            }
        )
        self.env["stock.package"].create({"name": "test_edit_done_move_line_12"})
        move1 = self.env["stock.move"].create(
            {
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
                "product_id": self.product_lot.id,
                "product_uom_id": self.uom_dozen.id,
                "product_uom_qty": 1.0,
            }
        )
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.quantity = 1
        move1.move_line_ids.lot_id = lot1.id
        move1.picked = True
        move1._action_done()
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.product_lot, self.stock_location, lot_id=lot1
            ),
            12.0,
        )

        move1.move_line_ids.quantity = 2
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.product_lot, self.stock_location, lot_id=lot1
            ),
            24.0,
        )

    def test_edit_done_move_line_13(self):
        lot1 = self.env["stock.lot"].create(
            {
                "name": "lot1",
                "product_id": self.product_lot.id,
            }
        )
        lot2 = self.env["stock.lot"].create(
            {
                "name": "lot2",
                "product_id": self.product_lot.id,
            }
        )
        package1 = self.env["stock.package"].create(
            {"name": "test_edit_reserved_move_line_5"}
        )

        move1 = self.env["stock.move"].create(
            {
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
                "product_id": self.product_lot.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 1.0,
            }
        )
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.quantity = 1
        move1.move_line_ids.lot_id = lot1.id
        move1.move_line_ids.result_package_id = package1.id
        move1.picked = True
        move1._action_done()

        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.product_lot, self.stock_location
            ),
            1.0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.product_lot, self.stock_location, lot_id=lot1, package_id=package1
            ),
            1.0,
        )

        move1.move_line_ids.write({"lot_id": lot2})

        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.product_lot, self.stock_location
            ),
            1.0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.product_lot, self.stock_location, lot_id=lot1
            ),
            0.0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.product_lot, self.stock_location, lot_id=lot1, package_id=package1
            ),
            0.0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.product_lot, self.stock_location, lot_id=lot2, package_id=package1
            ),
            1.0,
        )

    def test_edit_done_move_line_14(self):
        move1 = self.env["stock.move"].create(
            {
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 12.0,
            }
        )
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.product_uom_id = self.uom_dozen
        move1.move_line_ids.quantity = 1
        move1.picked = True
        move1._action_done()
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location
            ),
            12.0,
        )

        move1.move_line_ids.quantity = 2
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location
            ),
            24.0,
        )
        self.assertEqual(move1.product_uom_qty, 12.0)
        self.assertEqual(move1.product_qty, 12.0)

        move1.move_line_ids.product_uom_id = self.uom_unit
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location
            ),
            2.0,
        )
        self.assertEqual(move1.product_uom_qty, 12.0)
        self.assertEqual(move1.product_qty, 12.0)

        with self.assertRaises(UserError):
            move1.product_uom_id = self.uom_dozen

    def test_immediate_validate_1(self):
        picking = self.env["stock.picking"].create(
            {
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
                "partner_id": self.partner_1.id,
                "picking_type_id": self.picking_type_in.id,
                "state": "draft",
            }
        )
        self.env["stock.move"].create(
            {
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
                "picking_id": picking.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 10.0,
            }
        )
        picking.action_confirm()
        picking.action_assign()
        picking.button_validate()
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location
            ),
            10.0,
        )

    def test_immediate_validate_2(self):
        self.env["stock.quant"]._update_available_quantity(
            self.productA, self.stock_location, 5.0
        )
        picking = self.env["stock.picking"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "partner_id": self.partner_1.id,
                "picking_type_id": self.picking_type_out.id,
                "state": "draft",
            }
        )
        self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "picking_id": picking.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 10.0,
            }
        )
        picking.action_confirm()
        picking.action_assign()
        res_dict_for_back_order = picking.button_validate()
        self.assertEqual(
            res_dict_for_back_order.get("res_model"), "stock.backorder.confirmation"
        )
        backorder_wizard = (
            self.env[(res_dict_for_back_order.get("res_model"))]
            .browse(res_dict_for_back_order.get("res_id"))
            .with_context(res_dict_for_back_order["context"])
        )
        backorder_wizard.process()

        self.assertEqual(picking.move_ids.state, "done")
        self.assertEqual(picking.move_ids.quantity, 5.0)
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location
            ),
            0.0,
        )
        self.assertEqual(
            len(self.gather_relevant(self.productA, self.stock_location)), 0.0
        )

        backorder = self.env["stock.picking"].search(
            [("backorder_id", "=", picking.id)]
        )
        self.assertEqual(len(backorder), 1.0)
        self.assertEqual(backorder.move_ids.product_uom_qty, 5.0)

    def test_immediate_validate_3(self):
        product5 = self.env["product.product"].create(
            {
                "name": "Product 5",
                "is_storable": True,
            }
        )

        self.env["stock.quant"]._update_available_quantity(
            self.productA, self.stock_location, 1
        )

        picking = self.env["stock.picking"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.pack_location.id,
                "picking_type_id": self.picking_type_int.id,
                "state": "draft",
            }
        )
        product1_move = self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.pack_location.id,
                "picking_id": picking.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 100,
            }
        )
        product5_move = self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.pack_location.id,
                "picking_id": picking.id,
                "product_id": product5.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 100,
            }
        )
        picking.action_confirm()
        picking.action_assign()

        self.assertEqual(product1_move.state, "partially_available")
        self.assertEqual(product5_move.state, "confirmed")

        action = picking.button_validate()
        self.assertTrue(isinstance(action, dict), "Should open backorder wizard")
        self.assertEqual(action.get("res_model"), "stock.backorder.confirmation")
        wizard = (
            self.env[(action.get("res_model"))]
            .browse(action.get("res_id"))
            .with_context(action.get("context"))
        )
        wizard.process()
        backorder = self.env["stock.picking"].search(
            [("backorder_id", "=", picking.id)]
        )
        self.assertEqual(len(backorder), 1.0)

        for backorder_move in backorder.move_ids:
            if backorder_move.product_id.id == self.productA.id:
                self.assertEqual(backorder_move.product_qty, 99)
            elif backorder_move.product_id.id == product5.id:
                self.assertEqual(backorder_move.product_qty, 100)

    def test_immediate_validate_4(self):
        lot1 = self.env["stock.lot"].create(
            {
                "name": "lot1",
                "product_id": self.product_lot.id,
            }
        )
        self.env["stock.quant"]._update_available_quantity(
            self.product_lot, self.stock_location, 5.0, lot_id=lot1
        )
        picking = self.env["stock.picking"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "partner_id": self.partner_1.id,
                "picking_type_id": self.picking_type_out.id,
                "state": "draft",
            }
        )
        self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "picking_id": picking.id,
                "product_id": self.product_lot.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 5.0,
            }
        )
        picking.action_confirm()
        picking.action_assign()
        picking.button_validate()

        self.assertEqual(picking.move_ids.quantity, 5.0)
        self.assertEqual(len(picking.move_ids.move_line_ids), 1)
        self.assertEqual(picking.move_ids.move_line_ids.lot_id, lot1)
        self.assertEqual(picking.move_ids.move_line_ids.quantity, 5.0)
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location
            ),
            0.0,
        )
        self.assertEqual(
            len(self.gather_relevant(self.productA, self.stock_location)), 0.0
        )

    def _create_picking_test_immediate_validate_5(self, picking_type, product_id):
        picking = self.env["stock.picking"].create(
            {
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
                "picking_type_id": picking_type.id,
            }
        )
        self.env["stock.move"].create(
            {
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
                "picking_id": picking.id,
                "picking_type_id": picking_type.id,
                "product_id": product_id.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 5.0,
            }
        )

        picking.action_confirm()

        picking.move_ids.write({"picked": True})

        return picking

    def test_immediate_validate_5(self):
        product_id = self.product_serial
        self.assertTrue(
            self.picking_type_in.use_create_lots
            or self.picking_type_in.use_existing_lots
        )
        self.assertEqual(product_id.tracking, "serial")

        picking = self._create_picking_test_immediate_validate_5(
            self.picking_type_in, product_id
        )
        self.assertRaises(UserError, picking.button_validate)

        self.picking_type_in.use_create_lots = False
        self.picking_type_in.use_existing_lots = False
        picking = self._create_picking_test_immediate_validate_5(
            self.picking_type_in, product_id
        )
        picking.button_validate()
        self.assertEqual(picking.state, "done")

    def test_immediate_validate_6(self):
        self.picking_type_in.use_create_lots = True
        self.picking_type_in.use_existing_lots = False
        picking = self.env["stock.picking"].create(
            {
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
                "picking_type_id": self.picking_type_in.id,
                "state": "draft",
            }
        )
        self.env["stock.move"].create(
            {
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
                "picking_id": picking.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 1,
            }
        )
        product3_move = self.env["stock.move"].create(
            {
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
                "picking_id": picking.id,
                "product_id": self.product_lot.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 1,
            }
        )
        picking.action_confirm()
        picking.action_assign()

        with self.assertRaises(UserError):
            picking.button_validate()
        product3_move.picked = True
        with self.assertRaises(UserError):
            picking.button_validate()
        product3_move.move_line_ids[0].lot_name = "271828"
        action = picking.button_validate()

        self.assertTrue(isinstance(action, dict), "Should open backorder wizard")
        self.assertEqual(action.get("res_model"), "stock.backorder.confirmation")

    def test_immediate_validate_7(self):
        picking = self.env["stock.picking"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "partner_id": self.partner_1.id,
                "picking_type_id": self.picking_type_out.id,
                "state": "draft",
            }
        )
        self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "picking_id": picking.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 10.0,
            }
        )
        picking.action_confirm()
        picking.action_assign()
        scrap = self.env["stock.scrap"].create(
            {
                "picking_id": picking.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "scrap_qty": 5.0,
            }
        )
        scrap._action_done()

        with self.assertRaises(UserError):
            picking.button_validate()

    def test_immediate_validate_8(self):
        receipt1 = self.env["stock.picking"].create(
            {
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
                "partner_id": self.partner_1.id,
                "picking_type_id": self.picking_type_in.id,
                "state": "draft",
            }
        )
        self.env["stock.move"].create(
            {
                "location_id": receipt1.location_id.id,
                "location_dest_id": receipt1.location_dest_id.id,
                "picking_id": receipt1.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 10.0,
            }
        )
        receipt1.action_confirm()
        receipt2 = self.env["stock.picking"].create(
            {
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
                "partner_id": self.partner_1.id,
                "picking_type_id": self.picking_type_in.id,
                "state": "draft",
            }
        )
        self.env["stock.move"].create(
            {
                "location_id": receipt2.location_id.id,
                "location_dest_id": receipt2.location_dest_id.id,
                "picking_id": receipt2.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 10.0,
            }
        )
        receipt2.action_confirm()

        (receipt1 + receipt2).button_validate()
        self.assertEqual(receipt1.state, "done")
        self.assertEqual(receipt2.state, "done")

    def test_immediate_validate_9_tracked_move_with_0_quantity(self):
        self.picking_type_in.use_create_lots = False
        self.picking_type_in.use_existing_lots = False

        receipt_transfer = self.env["stock.picking"].create(
            {
                "state": "draft",
                "picking_type_id": self.picking_type_in.id,
            }
        )
        picking_form = Form(receipt_transfer)
        with picking_form.move_ids.new() as move:
            move.product_id = self.product_serial
            move.product_uom_qty = 4
        with picking_form.move_ids.new() as move:
            move.product_id = self.product_lot
            move.product_uom_qty = 20
        receipt = picking_form.save()
        receipt.action_confirm()

        receipt.button_validate()
        self.assertEqual(receipt.state, "done")

    def test_immediate_validate_10_tracked_move_without_backorder(self):
        self.picking_type_int.use_create_lots = True
        self.picking_type_int.use_existing_lots = True
        lot = self.env["stock.lot"].create(
            {
                "name": "Lot 1",
                "product_id": self.product_lot.id,
            }
        )
        self.env["stock.quant"]._update_available_quantity(
            self.product_lot, self.stock_location, 10, lot_id=lot
        )
        internal_transfer = self.env["stock.picking"].create(
            {
                "state": "draft",
                "picking_type_id": self.picking_type_int.id,
            }
        )
        picking_form = Form(internal_transfer)
        with picking_form.move_ids.new() as move:
            move.product_id = self.product_lot
            move.product_uom_qty = 4
        internal_transfer = picking_form.save()
        internal_transfer.action_confirm()

        internal_transfer.button_validate()
        self.assertEqual(internal_transfer.state, "done")

    def test_validate_picking_wihtout_picked_reservations(self):
        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": self.ref("stock.picking_type_out"),
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "move_type": "one",
                "move_ids": [
                    Command.create(
                        {
                            "product_id": self.product_consu.id,
                            "product_uom_id": self.product_consu.uom_id.id,
                            "product_uom_qty": 1.0,
                            "location_id": self.stock_location.id,
                            "location_dest_id": self.customer_location.id,
                        }
                    ),
                    Command.create(
                        {
                            "product_id": self.productA.id,
                            "product_uom_id": self.productA.uom_id.id,
                            "product_uom_qty": 1.0,
                            "location_id": self.stock_location.id,
                            "location_dest_id": self.customer_location.id,
                        }
                    ),
                ],
            }
        )
        picking.action_confirm()
        picking.move_ids[1].picked = True
        self.assertRecordValues(
            picking.move_ids,
            [
                {"quantity": 1.0, "picked": False, "state": "assigned"},
                {"quantity": 0.0, "picked": True, "state": "confirmed"},
            ],
        )
        with self.assertRaises(UserError):
            picking.button_validate()

    def test_set_quantity_1(self):
        move1 = self.env["stock.move"].create(
            {
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 2.0,
            }
        )
        move2 = self.env["stock.move"].create(
            {
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 2.0,
            }
        )
        (move1 + move2)._action_confirm()
        (move1 + move2).write({"quantity": 1})
        self.assertEqual(move1.quantity, 1)
        self.assertEqual(move2.quantity, 1)

    def test_initial_demand_1(self):
        move1 = self.env["stock.move"].create(
            {
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
            }
        )
        self.assertEqual(move1.state, "draft")
        self.assertEqual(move1.product_uom_qty, 0)
        move1.product_uom_qty = 100
        move1.product_id = self.product_serial
        self.assertEqual(move1.product_uom_qty, 100)

    def test_scrap_1(self):
        self.env["stock.quant"]._update_available_quantity(
            self.productA, self.stock_location, 1
        )
        scrap_form = Form(self.env["stock.scrap"])
        scrap_form.product_id = self.productA
        scrap_form.location_id = self.stock_location
        scrap_form.scrap_qty = 1
        scrap = scrap_form.save()
        scrap._action_done()
        self.assertEqual(scrap.state, "done")
        move = scrap.move_ids[0]
        self.assertEqual(move.state, "done")
        self.assertEqual(move.quantity, 1)
        self.assertEqual(move.location_dest_usage, "inventory")
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location
            ),
            0,
        )

    def test_scrap_2(self):
        scrap = self.env["stock.scrap"].create(
            {
                "product_id": self.product_consu.id,
                "product_uom_id": self.product_consu.uom_id.id,
                "location_id": self.stock_location.id,
                "scrap_qty": 1,
            }
        )
        self.assertEqual(scrap.name, "New", "Name should be New in draft state")
        scrap._action_done()
        self.assertTrue(
            scrap.name.startswith("SP/"),
            "Sequence should be Changed after _action_done",
        )
        self.assertEqual(scrap.state, "done")
        move = scrap.move_ids[0]
        self.assertEqual(move.state, "done")
        self.assertEqual(move.quantity, 1)
        self.assertEqual(move.location_dest_usage, "inventory")
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.product_consu, self.stock_location
            ),
            0,
        )

    def test_scrap_3(self):
        self.env["stock.quant"]._update_available_quantity(
            self.productA, self.stock_location, 1
        )
        move1 = self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 1.0,
            }
        )
        move1._action_confirm()
        move1._action_assign()
        self.assertEqual(move1.state, "assigned")
        self.assertEqual(len(move1.move_line_ids), 1)

        scrap = self.env["stock.scrap"].create(
            {
                "product_id": self.productA.id,
                "product_uom_id": self.productA.uom_id.id,
                "location_id": self.stock_location.id,
                "scrap_qty": 1,
            }
        )
        scrap._action_done()
        self.assertEqual(move1.state, "confirmed")
        self.assertEqual(len(move1.move_line_ids), 0)

    def test_scrap_4(self):
        self.env["stock.quant"]._update_available_quantity(
            self.productA, self.stock_location, 10
        )
        picking = self.env["stock.picking"].create(
            {
                "name": "A single picking with one move to scrap",
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "partner_id": self.partner_1.id,
                "picking_type_id": self.picking_type_out.id,
                "state": "draft",
            }
        )
        move1 = self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 1.0,
                "picking_id": picking.id,
            }
        )
        move1._action_confirm()
        move1._action_assign()

        self.assertEqual(move1.state, "assigned")
        scrap = self.env["stock.scrap"].create(
            {
                "product_id": self.productA.id,
                "product_uom_id": self.productA.uom_id.id,
                "scrap_qty": 5,
                "picking_id": picking.id,
            }
        )

        scrap.action_validate()
        self.assertEqual(len(picking.move_ids), 2)
        scrapped_move = picking.move_ids.filtered(lambda m: m.state == "done")
        self.assertTrue(scrapped_move, "No scrapped move created.")
        self.assertEqual(
            scrapped_move.scrap_id.id, scrap.id, "Wrong scrap linked to the move."
        )
        self.assertEqual(
            scrap.scrap_qty,
            5,
            "Scrap quantity has been modified and is not correct anymore.",
        )

        scrapped_move.quantity = 8
        self.assertEqual(scrap.scrap_qty, 8, "Scrap quantity is not updated.")

    def test_scrap_5(self):
        self.env["stock.quant"]._update_available_quantity(
            self.productA, self.stock_location, 4
        )

        picking = self.env["stock.picking"].create(
            {
                "name": "A single picking with one move to scrap",
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "partner_id": self.partner_1.id,
                "picking_type_id": self.picking_type_out.id,
                "state": "draft",
            }
        )
        move1 = self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_dozen.id,
                "product_uom_qty": 1.0,
                "picking_id": picking.id,
            }
        )
        move1._action_confirm()
        move1._action_assign()
        self.assertEqual(move1.quantity, 0.33)

        scrap = self.env["stock.scrap"].create(
            {
                "product_id": self.productA.id,
                "product_uom_id": self.productA.uom_id.id,
                "location_id": self.stock_location.id,
                "scrap_qty": 1,
                "picking_id": picking.id,
            }
        )
        scrap.action_validate()

        self.assertEqual(scrap.state, "done")
        self.assertEqual(move1.quantity, 0.25)

    def test_scrap_6(self):
        self.env["stock.quant"]._update_available_quantity(
            self.productA, self.stock_location, 1
        )
        scrap = self.env["stock.scrap"].create(
            {
                "product_id": self.productA.id,
                "product_uom_id": self.uom_dozen.id,
                "location_id": self.stock_location.id,
                "scrap_qty": 1,
            }
        )
        warning_message = scrap.action_validate()
        self.assertEqual(
            warning_message.get("res_model", "Wrong Model"),
            "stock.warn.insufficient.qty.scrap",
        )
        insufficient_qty_wizard = (
            self.env["stock.warn.insufficient.qty.scrap"]
            .with_context(warning_message["context"])
            .create({})
        )
        insufficient_qty_wizard.action_done()
        self.assertEqual(
            self.env["stock.quant"]
            ._gather(self.productA, self.stock_location)
            .quantity,
            -11,
        )
        self.assertEqual(scrap.scrap_qty, 1)
        self.assertEqual(scrap.product_uom_id, self.uom_dozen)
        self.assertEqual(scrap.state, "done")

    def test_scrap_7_sn_warning(self):
        lot1 = self.env["stock.lot"].create(
            {
                "name": "serial1",
                "product_id": self.product_serial.id,
            }
        )

        self.env["stock.quant"]._update_available_quantity(
            self.product_serial, self.shelf_1, 1, lot_id=lot1
        )

        scrap = self.env["stock.scrap"].create(
            {
                "product_id": self.product_serial.id,
                "product_uom_id": self.uom_unit.id,
                "location_id": self.shelf_2.id,
                "lot_id": lot1.id,
            }
        )

        warning = False
        warning = scrap._onchange_serial_number()
        self.assertTrue(warning, "Use of wrong serial number location not detected")
        self.assertEqual(
            list(warning.keys())[0], "warning", "Warning message was not returned"
        )
        self.assertEqual(
            scrap.location_id, self.shelf_1, "Location was not auto-corrected"
        )

    def test_scrap_8(self):
        self.picking_type_int.active = True

        product01 = self.productA
        product02 = self.env["product.product"].create(
            {
                "name": "SuperProduct",
                "is_storable": True,
            }
        )

        self.env["stock.quant"]._update_available_quantity(
            product01, self.stock_location, 3
        )
        self.env["stock.quant"]._update_available_quantity(
            product02, self.stock_location, 1
        )

        scrap_picking01, scrap_picking02, scrap_picking03 = self.env[
            "stock.picking"
        ].create(
            [
                {
                    "location_id": self.stock_location.id,
                    "location_dest_id": self.scrap_location.id,
                    "picking_type_id": self.picking_type_int.id,
                    "state": "draft",
                    "move_ids": [
                        (
                            0,
                            0,
                            {
                                "location_id": self.stock_location.id,
                                "location_dest_id": self.scrap_location.id,
                                "product_id": product.id,
                                "product_uom_id": product.uom_id.id,
                                "product_uom_qty": 1.0,
                                "picking_type_id": self.picking_type_int.id,
                            },
                        )
                        for product in products
                    ],
                }
                for products in [(product01,), (product01,), (product01, product02)]
            ]
        )

        (scrap_picking01 + scrap_picking02 + scrap_picking03).action_confirm()

        scrap_picking01.move_ids.quantity = 1
        scrap_picking01.move_ids.picked = True
        scrap_picking01.button_validate()

        scrap_picking02.action_cancel()

        pick03_prod01_move = scrap_picking03.move_ids.filtered(
            lambda sm: sm.product_id == product01
        )
        pick03_prod02_move = scrap_picking03.move_ids - pick03_prod01_move
        pick03_prod01_move.quantity = 1
        pick03_prod02_move._action_cancel()
        scrap_picking03.move_ids.picked = True
        scrap_picking03.button_validate()

        self.assertEqual(scrap_picking01.move_ids.state, "done")
        self.assertEqual(scrap_picking01.state, "done")

        self.assertEqual(scrap_picking02.move_ids.state, "cancel")
        self.assertEqual(scrap_picking02.state, "cancel")

        self.assertEqual(pick03_prod01_move.state, "done")
        self.assertEqual(pick03_prod02_move.state, "cancel")
        self.assertEqual(scrap_picking03.state, "done")

        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                product01, self.stock_location
            ),
            1,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                product02, self.stock_location
            ),
            1,
        )

    def test_scrap_9_with_delivery(self):
        self.env["stock.quant"]._update_available_quantity(
            self.productA, self.stock_location, 10
        )
        picking = self.env["stock.picking"].create(
            {
                "name": "A single picking with one move to scrap",
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "picking_type_id": self.picking_type_out.id,
            }
        )
        move1 = self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "product_id": self.productA.id,
                "product_uom_qty": 9.0,
                "picking_id": picking.id,
            }
        )
        move1._action_confirm()
        move1._action_assign()
        self.assertEqual(move1.quantity, 9)

        scrap = self.env["stock.scrap"].create(
            {
                "product_id": self.productA.id,
                "product_uom_id": self.productA.uom_id.id,
                "scrap_qty": 1,
                "picking_id": picking.id,
            }
        )
        scrap.action_validate()

        self.assertEqual(scrap.state, "done")
        picking.button_validate()
        self.assertEqual(picking.state, "done")

    def test_scrap_10(self):
        self.env["stock.quant"]._update_available_quantity(
            self.productA, self.stock_location, 10
        )
        picking = self.env["stock.picking"].create(
            {
                "name": "A single picking with one move to scrap",
                "location_id": self.stock_location.id,
                "location_dest_id": self.scrap_location.id,
                "picking_type_id": self.picking_type_out.id,
            }
        )
        move1 = self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.scrap_location.id,
                "product_id": self.productA.id,
                "product_uom_qty": 10.0,
                "picking_id": picking.id,
            }
        )
        move1._action_confirm()
        move1._action_assign()

        self.assertEqual(move1.quantity, 10)
        picking.button_validate()
        self.assertEqual(picking.state, "done")

    def test_scrap_11(self):
        self.env["stock.quant"]._update_available_quantity(
            self.productA, self.stock_location, 10
        )
        self.env["stock.quant"]._update_available_quantity(
            self.productA, self.scrap_location, 10
        )
        picking = self.env["stock.picking"].create(
            {
                "name": "A single picking with one move to scrap",
                "location_id": self.stock_location.id,
                "location_dest_id": self.stock_location.id,
                "picking_type_id": self.picking_type_out.id,
            }
        )
        move = self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.stock_location.id,
                "product_id": self.productA.id,
                "product_uom_qty": 10.0,
                "picking_id": picking.id,
            }
        )
        picking.action_confirm()

        self.assertEqual(move.quantity, 10)
        move.move_line_ids.location_id = self.scrap_location

        picking.button_validate()
        self.assertEqual(picking.state, "done")

        quant = self.env["stock.quant"]._gather(
            self.productA, self.stock_location, strict=True
        )
        quant_scrap = self.env["stock.quant"]._gather(
            self.productA, self.scrap_location
        )
        self.assertEqual(quant.quantity, 20)
        self.assertFalse(quant_scrap.reserved_quantity)
        self.assertFalse(quant_scrap.quantity)

    def test_scrap_12_qty_in_sublocation(self):
        self.env["stock.quant"]._update_available_quantity(
            self.productA, self.shelf_1, 10
        )

        with Form(self.env["stock.scrap"]) as scrap_form:
            scrap_form.product_id = self.productA
            scrap_form.scrap_qty = 5
            scrap_form.location_id = self.stock_location
            scrap = scrap_form.save()

        warning = scrap.action_validate()
        self.assertEqual(
            warning.get("res_model"),
            "stock.warn.insufficient.qty.scrap",
            "Should trigger the warning as no qty in location",
        )

    def test_in_date_1(self):
        move1 = self.env["stock.move"].create(
            {
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
                "product_id": self.product_lot.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 1.0,
                "picking_type_id": self.picking_type_in.id,
            }
        )
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.lot_name = "lot1"
        move1.picked = True
        move1._action_done()

        quant = self.gather_relevant(self.product_lot, self.stock_location)
        self.assertEqual(len(quant), 1.0)
        self.assertNotEqual(quant.in_date, False)

        initial_incoming_date = quant.in_date

        move2 = self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.pack_location.id,
                "product_id": self.product_lot.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 1.0,
            }
        )
        move2._action_confirm()
        move2._action_assign()
        move2.picked = True
        move2._action_done()

        quant = self.gather_relevant(self.product_lot, self.pack_location)
        self.assertEqual(len(quant), 1.0)
        self.assertEqual(quant.in_date, initial_incoming_date)

    def test_in_date_2(self):
        lot1 = self.env["stock.lot"].create(
            {
                "name": "lot1",
                "product_id": self.product_lot.id,
            }
        )
        lot2 = self.env["stock.lot"].create(
            {
                "name": "lot2",
                "product_id": self.product_lot.id,
            }
        )
        move1 = self.env["stock.move"].create(
            {
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
                "product_id": self.product_lot.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 1.0,
                "picking_type_id": self.picking_type_in.id,
            }
        )
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.lot_id = lot1
        move1.picked = True
        move1._action_done()

        move2 = self.env["stock.move"].create(
            {
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
                "product_id": self.product_lot.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 1.0,
                "picking_type_id": self.picking_type_in.id,
            }
        )
        move2._action_confirm()
        move2._action_assign()
        move2.move_line_ids.lot_id = lot2
        move2.picked = True
        move2._action_done()

        initial_in_date_lot2 = (
            self.env["stock.quant"]
            .search(
                [
                    ("location_id", "=", self.stock_location.id),
                    ("product_id", "=", self.product_lot.id),
                    ("lot_id", "=", lot2.id),
                ]
            )
            .in_date
        )

        quant_lot1 = self.env["stock.quant"].search(
            [
                ("location_id", "=", self.stock_location.id),
                ("product_id", "=", self.product_lot.id),
                ("lot_id", "=", lot1.id),
            ]
        )
        from datetime import timedelta

        from odoo.fields import Datetime

        initial_in_date_lot1 = Datetime.now() - timedelta(days=5)
        quant_lot1.in_date = initial_in_date_lot1

        move3 = self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.pack_location.id,
                "product_id": self.product_lot.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 1.0,
            }
        )
        move3._action_confirm()
        move3._action_assign()
        move3.move_line_ids.quantity = 1
        move3.picked = True
        move3._action_done()
        quant_in_pack = self.env["stock.quant"].search(
            [
                ("product_id", "=", self.product_lot.id),
                ("location_id", "=", self.pack_location.id),
            ]
        )
        self.assertEqual(len(quant_in_pack), 1)
        self.assertAlmostEqual(
            quant_in_pack.in_date, initial_in_date_lot1, delta=timedelta(seconds=1)
        )
        self.assertEqual(quant_in_pack.lot_id, lot1)

        move3.move_line_ids.lot_id = lot2

        quant_lot1 = self.env["stock.quant"].search(
            [
                ("location_id.usage", "=", "internal"),
                ("product_id", "=", self.product_lot.id),
                ("lot_id", "=", lot1.id),
                ("quantity", "!=", 0),
            ]
        )
        self.assertEqual(quant_lot1.location_id, self.stock_location)
        self.assertAlmostEqual(
            quant_lot1.in_date, initial_in_date_lot1, delta=timedelta(seconds=1)
        )

        quant_lot2 = self.env["stock.quant"].search(
            [
                ("location_id.usage", "=", "internal"),
                ("product_id", "=", self.product_lot.id),
                ("lot_id", "=", lot2.id),
                ("quantity", "!=", 0),
            ]
        )
        self.assertEqual(quant_lot2.location_id, self.pack_location)
        self.assertAlmostEqual(
            quant_lot2.in_date, initial_in_date_lot2, delta=timedelta(seconds=1)
        )

    def test_in_date_3(self):
        lot1 = self.env["stock.lot"].create(
            {
                "name": "lot1",
                "product_id": self.product_lot.id,
            }
        )
        lot2 = self.env["stock.lot"].create(
            {
                "name": "lot2",
                "product_id": self.product_lot.id,
            }
        )
        move1 = self.env["stock.move"].create(
            {
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
                "product_id": self.product_lot.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 1.0,
                "picking_type_id": self.picking_type_in.id,
            }
        )
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.lot_id = lot1
        move1.move_line_ids.quantity = 1
        move1.picked = True
        move1._action_done()

        move2 = self.env["stock.move"].create(
            {
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
                "product_id": self.product_lot.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 1.0,
                "picking_type_id": self.picking_type_in.id,
            }
        )
        move2._action_confirm()
        move2._action_assign()
        move2.move_line_ids.lot_id = lot2
        move2.move_line_ids.quantity = 1
        move2.picked = True
        move2._action_done()

        initial_in_date_lot2 = (
            self.env["stock.quant"]
            .search(
                [
                    ("location_id", "=", self.stock_location.id),
                    ("product_id", "=", self.product_lot.id),
                    ("lot_id", "=", lot2.id),
                    ("quantity", "!=", 0),
                ]
            )
            .in_date
        )

        quant_lot1 = self.env["stock.quant"].search(
            [
                ("location_id.usage", "=", "internal"),
                ("product_id", "=", self.product_lot.id),
                ("lot_id", "=", lot1.id),
                ("quantity", "!=", 0),
            ]
        )
        from datetime import timedelta

        from odoo.fields import Datetime

        initial_in_date_lot1 = Datetime.now() - timedelta(days=5)
        quant_lot1.in_date = initial_in_date_lot1

        move3 = self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.pack_location.id,
                "product_id": self.product_lot.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 1.0,
            }
        )
        move3._action_confirm()
        move3._action_assign()
        move3.move_line_ids.quantity = 1
        move3.picked = True
        move3._action_done()

        self.env["stock.move.line"].create(
            {
                "move_id": move3.id,
                "product_id": move3.product_id.id,
                "quantity": 1,
                "product_uom_id": move3.product_uom_id.id,
                "location_id": move3.location_id.id,
                "location_dest_id": move3.location_dest_id.id,
                "lot_id": lot2.id,
            }
        )

        quants = self.env["stock.quant"].search(
            [
                ("location_id.usage", "=", "internal"),
                ("product_id", "=", self.product_lot.id),
                ("quantity", "!=", 0),
            ]
        )
        self.assertEqual(len(quants), 2)
        for quant in quants:
            if quant.lot_id == lot1:
                self.assertAlmostEqual(
                    quant.in_date, initial_in_date_lot1, delta=timedelta(seconds=1)
                )
            elif quant.lot_id == lot2:
                self.assertAlmostEqual(
                    quant.in_date, initial_in_date_lot2, delta=timedelta(seconds=1)
                )

    def test_edit_initial_demand_1(self):
        move1 = self.env["stock.move"].create(
            {
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 10.0,
                "picking_type_id": self.picking_type_in.id,
            }
        )
        move1._action_confirm()
        move1._action_assign()
        move1.product_uom_qty = 15
        self.assertEqual(move1.state, "assigned")
        self.assertEqual(move1.product_uom_qty, 15)
        self.assertEqual(len(move1.move_line_ids), 1)

    def test_edit_initial_demand_2(self):
        move1 = self.env["stock.move"].create(
            {
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 10.0,
                "picking_type_id": self.picking_type_in.id,
            }
        )
        move1._action_confirm()
        move1._action_assign()
        self.assertEqual(move1.state, "assigned")
        move1.product_uom_qty = 5
        self.assertEqual(move1.state, "assigned")
        self.assertEqual(move1.product_uom_qty, 5)
        self.assertEqual(len(move1.move_line_ids), 1)

    def test_initial_demand_3(self):
        picking = self.env["stock.picking"].create(
            {
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
                "picking_type_id": self.picking_type_in.id,
            }
        )
        move1 = self.env["stock.move"].create(
            {
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "quantity": 10.0,
                "picking_id": picking.id,
            }
        )
        picking._autoconfirm_picking()
        self.assertEqual(picking.state, "assigned")
        move1.quantity = 12
        self.assertEqual(picking.state, "assigned")

    def test_initial_demand_4(self):
        self.env["stock.quant"]._update_available_quantity(
            self.productA, self.stock_location, 12
        )
        picking = self.env["stock.picking"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "picking_type_id": self.picking_type_in.id,
                "state": "draft",
            }
        )
        move1 = self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 10.0,
                "picking_id": picking.id,
            }
        )
        picking.action_confirm()
        picking.action_assign()
        self.assertEqual(picking.state, "assigned")
        move1.product_uom_qty = 12
        self.assertEqual(picking.state, "assigned")
        self.assertEqual(move1.state, "partially_available")
        picking.action_assign()
        self.assertEqual(move1.state, "assigned")

    def test_change_product_type(self):
        self.productA.is_storable = False
        move_in = self.env["stock.move"].create(
            {
                "location_id": self.customer_location.id,
                "location_dest_id": self.stock_location.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 5,
                "picking_type_id": self.picking_type_out.id,
            }
        )
        move_in._action_confirm()
        move_in._action_assign()

        self.productA.is_storable = True
        move_in._action_done()

        self.env["stock.quant"]._update_available_quantity(
            self.productA, self.stock_location, 10
        )
        self.productA.qty_available = 10
        self.assertEqual(self.productA.tracking, "none")

        move_out = self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": self.productA.qty_available,
                "picking_type_id": self.picking_type_out.id,
            }
        )
        move_out._action_confirm()
        move_out._action_assign()

        self.productA.tracking = "lot"

        lot_1 = self.env["stock.lot"].create(
            {
                "product_id": self.productA.id,
                "name": "lot 1",
            }
        )

        move_out.move_line_ids[0].lot_id = lot_1
        move_out.quantity = self.productA.qty_available
        move_out.picked = True
        move_out._action_done()

        self.productA.tracking = "serial"
        sn_01, sn_02, sn_03, sn_04, sn_05 = self.env["stock.lot"].create(
            [
                {
                    "product_id": self.productA.id,
                    "name": name,
                }
                for name in ["SN01", "SN02", "SN03", "SN04", "SN05"]
            ]
        )
        self.env["stock.quant"]._update_available_quantity(
            self.productA, self.stock_location, 1, lot_id=sn_01
        )
        self.env["stock.quant"]._update_available_quantity(
            self.productA, self.stock_location, 1, lot_id=sn_02
        )
        self.env["stock.quant"]._update_available_quantity(
            self.productA, self.stock_location, 1, lot_id=sn_03
        )
        self.env["stock.quant"]._update_available_quantity(
            self.productA, self.stock_location, 1, lot_id=sn_04
        )
        self.env["stock.quant"]._update_available_quantity(
            self.productA, self.stock_location, 1, lot_id=sn_05
        )

        move2 = self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 5,
                "picking_type_id": self.picking_type_out.id,
            }
        )

        move2._action_confirm()
        move2._action_assign()

        self.assertRecordValues(
            move2.move_line_ids,
            [
                {"lot_id": sn_01.id},
                {"lot_id": sn_02.id},
                {"lot_id": sn_03.id},
                {"lot_id": sn_04.id},
                {"lot_id": sn_05.id},
            ],
        )

        self.productA.is_storable = False

        self.assertRecordValues(
            move2.move_line_ids,
            [
                {"lot_id": sn_01.id},
                {"lot_id": sn_02.id},
                {"lot_id": sn_03.id},
                {"lot_id": sn_04.id},
                {"lot_id": sn_05.id},
            ],
        )
        move_out.picked = True
        move_out._action_done()

    def test_edit_done_picking_1(self):
        self.env["stock.quant"]._update_available_quantity(
            self.productA, self.stock_location, 12
        )
        picking = self.env["stock.picking"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "picking_type_id": self.picking_type_in.id,
                "state": "draft",
            }
        )
        move1 = self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 10.0,
                "picking_id": picking.id,
            }
        )
        picking.action_confirm()
        picking.action_assign()
        move1.quantity = 10
        move1.picked = True
        picking._action_done()

        self.assertEqual(
            len(picking.move_ids), 1, "One move should exist for the picking."
        )
        self.assertEqual(
            len(picking.move_line_ids), 1, "One move line should exist for the picking."
        )

        ml = self.env["stock.move.line"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "quantity": 2.0,
                "picking_id": picking.id,
            }
        )

        self.assertEqual(
            len(picking.move_ids),
            2,
            "The new move associated to the move line does not exist.",
        )
        self.assertEqual(
            len(picking.move_line_ids), 2, "It should be 2 move lines for the picking."
        )
        self.assertTrue(
            ml.move_id in picking.move_ids,
            "Links are not correct between picking, moves and move lines.",
        )
        self.assertEqual(
            picking.state,
            "done",
            "Picking should still done after adding a new move line.",
        )
        self.assertTrue(
            all(move.state == "done" for move in picking.move_ids),
            "Wrong state for move.",
        )

    def test_put_in_pack_1(self):
        self.env["stock.quant"]._update_available_quantity(
            self.productA, self.stock_location, 2
        )
        picking = self.env["stock.picking"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "picking_type_id": self.picking_type_out.id,
                "state": "draft",
            }
        )
        move1 = self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 2.0,
                "picking_id": picking.id,
                "picking_type_id": self.picking_type_out.id,
            }
        )
        picking.action_confirm()
        picking.action_assign()
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location
            ),
            0,
        )
        move1.quantity = 1
        picking.action_put_in_pack()
        picking.action_assign()

        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location
            ),
            0,
        )
        self.assertEqual(len(picking.move_line_ids), 2)
        not_packed_ml = picking.move_line_ids.filtered(
            lambda ml: not ml.result_package_id
        )
        self.assertEqual(not_packed_ml.quantity_product_uom, 1)
        not_packed_ml.quantity = 1
        picking.action_put_in_pack()
        self.assertEqual(len(picking.move_line_ids), 2)
        self.assertNotEqual(
            picking.move_line_ids[0].result_package_id,
            picking.move_line_ids[1].result_package_id,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location
            ),
            0,
        )
        picking.move_ids.picked = True
        picking.button_validate()
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location
            ),
            0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.customer_location
            ),
            2,
        )

    def test_put_in_pack_2(self):
        product1 = self.env["product.product"].create(
            {
                "name": "Product B",
                "is_storable": True,
            }
        )
        self.env["stock.quant"]._update_available_quantity(
            self.productA, self.stock_location, 1
        )
        self.env["stock.quant"]._update_available_quantity(
            product1, self.stock_location, 2
        )
        picking = self.env["stock.picking"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "picking_type_id": self.picking_type_out.id,
                "state": "draft",
            }
        )
        self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 1.0,
                "picking_id": picking.id,
            }
        )
        self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "product_id": product1.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 2.0,
                "picking_id": picking.id,
            }
        )
        picking.action_confirm()
        picking.action_assign()
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location
            ),
            0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                product1, self.stock_location
            ),
            0,
        )
        picking.action_put_in_pack()
        self.assertEqual(len(picking.move_line_ids), 2)
        self.assertEqual(
            picking.move_line_ids[0].quantity,
            1,
            "Stock move line should have 1 quantity as a done quantity.",
        )
        self.assertEqual(
            picking.move_line_ids[1].quantity,
            2,
            "Stock move line should have 2 quantity as a done quantity.",
        )
        line1_result_package = picking.move_line_ids[0].result_package_id
        line2_result_package = picking.move_line_ids[1].result_package_id
        self.assertEqual(
            line1_result_package,
            line2_result_package,
            "Product and Product1 should be in a same package.",
        )

    def test_put_in_pack_3(self):
        product1 = self.env["product.product"].create(
            {
                "name": "Product B",
                "is_storable": True,
            }
        )
        self.env["stock.quant"]._update_available_quantity(
            self.productA, self.stock_location, 1
        )
        self.env["stock.quant"]._update_available_quantity(
            product1, self.stock_location, 2
        )
        picking = self.env["stock.picking"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "picking_type_id": self.picking_type_out.id,
                "state": "draft",
            }
        )
        move1 = self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 1.0,
                "picking_id": picking.id,
                "picking_type_id": self.picking_type_out.id,
            }
        )
        move2 = self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "product_id": product1.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 2.0,
                "picking_id": picking.id,
                "picking_type_id": self.picking_type_out.id,
            }
        )
        picking.action_confirm()
        picking.action_assign()
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location
            ),
            0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                product1, self.stock_location
            ),
            0,
        )
        move1.quantity = 1
        move1.picked = True
        picking.action_put_in_pack()
        move2.quantity = 2
        move2.picked = True
        picking.action_put_in_pack()
        self.assertEqual(len(picking.move_line_ids), 2)
        line1_result_package = picking.move_line_ids[0].result_package_id
        line2_result_package = picking.move_line_ids[1].result_package_id
        self.assertNotEqual(
            line1_result_package,
            line2_result_package,
            "Product and Product1 should be in a different package.",
        )

    def test_move_line_aggregated_product_quantities(self):
        product2 = self.env["product.product"].create(
            {
                "name": "Product B",
                "is_storable": True,
            }
        )
        product3 = self.env["product.product"].create(
            {
                "name": "Product C",
                "is_storable": True,
            }
        )
        self.env["stock.quant"].with_context(inventory_mode=True).create(
            [
                {
                    "product_id": self.productA.id,
                    "inventory_quantity": 100,
                    "location_id": self.stock_location.id,
                },
                {
                    "product_id": product2.id,
                    "inventory_quantity": 100,
                    "location_id": self.stock_location.id,
                },
                {
                    "product_id": product3.id,
                    "inventory_quantity": 100,
                    "location_id": self.stock_location.id,
                },
            ]
        ).action_apply_inventory()

        product4 = self.env["product.product"].create(
            {
                "name": "Product D",
                "is_storable": True,
            }
        )

        delivery_form = self.env["stock.picking"].create(
            {
                "state": "draft",
                "picking_type_id": self.picking_type_out.id,
            }
        )
        delivery_form = Form(delivery_form)
        with delivery_form.move_ids.new() as move:
            move.product_id = self.productA
            move.product_uom_qty = 10
        with delivery_form.move_ids.new() as move:
            move.product_id = product2
            move.product_uom_qty = 10
            move.description_picking = f"{product2.name}\nDescription2"
        with delivery_form.move_ids.new() as move:
            move.product_id = product3
            move.product_uom_qty = 10
            move.description_picking = f"{product3.display_name}\nDescription3"
        with delivery_form.move_ids.new() as move:
            move.product_id = product4
            move.product_uom_qty = 10
        delivery = delivery_form.save()
        delivery.action_confirm()

        delivery.move_line_ids.filtered(
            lambda ml: ml.product_id == self.productA
        ).quantity = 6
        delivery.move_line_ids.filtered(
            lambda ml: ml.product_id == product2
        ).quantity = 2
        delivery.move_ids.filtered(lambda ml: ml.product_id == product4).quantity = 2
        (delivery.move_ids[:2] | delivery.move_ids[3]).picked = True
        backorder_wizard_dict = delivery.button_validate()
        backorder_wizard_form = Form.from_action(self.env, backorder_wizard_dict)
        backorder_wizard_form.save().process()

        first_backorder = self.env["stock.picking"].search(
            [("backorder_id", "=", delivery.id)], limit=1
        )
        aggregate_values = delivery.move_line_ids._get_aggregated_product_quantities()
        self.assertEqual(len(aggregate_values), 3)
        sml1 = delivery.move_line_ids.filtered(
            lambda ml: ml.product_id == self.productA
        )
        sml2 = delivery.move_line_ids.filtered(lambda ml: ml.product_id == product2)
        sml3 = delivery.move_line_ids.filtered(lambda ml: ml.product_id == product4)
        aggregate_val_1 = _aggregated(
            aggregate_values,
            f"{self.productA.id}_{self.productA.name}__{sml1.product_uom_id.id}_{sml1.move_id.packaging_uom_id.id}",
        )
        aggregate_val_2 = _aggregated(
            aggregate_values,
            f"{product2.id}_{product2.name}_Description2_{sml2.product_uom_id.id}_{sml2.move_id.packaging_uom_id.id}",
        )
        aggregate_val_3 = _aggregated(
            aggregate_values,
            f"{product4.id}_{product4.name}__{sml3.product_uom_id.id}_{sml3.move_id.packaging_uom_id.id}",
        )
        self.assertEqual(aggregate_val_1["qty_ordered"], 10)
        self.assertEqual(aggregate_val_1["quantity"], 6)
        self.assertEqual(aggregate_val_2["qty_ordered"], 10)
        self.assertEqual(aggregate_val_2["quantity"], 2)
        self.assertEqual(aggregate_val_3["qty_ordered"], 10)
        self.assertEqual(aggregate_val_3["quantity"], 2)

        first_backorder.move_line_ids.filtered(
            lambda ml: ml.product_id == self.productA
        ).quantity = 4
        first_backorder.move_line_ids.filtered(
            lambda ml: ml.product_id == product2
        ).quantity = 6
        first_backorder.move_line_ids.filtered(
            lambda ml: ml.product_id == product3
        ).quantity = 7
        first_backorder.move_ids.filtered(
            lambda ml: ml.product_id == product4
        ).quantity = 8
        first_backorder.move_ids.picked = True
        backorder_wizard_dict = first_backorder.button_validate()
        backorder_wizard_form = Form.from_action(self.env, backorder_wizard_dict)
        backorder_wizard_form.save().process()

        second_backorder = self.env["stock.picking"].search(
            [("backorder_id", "=", first_backorder.id)], limit=1
        )
        aggregate_values = delivery.move_line_ids._get_aggregated_product_quantities()
        self.assertEqual(len(aggregate_values), 3)
        sml1 = delivery.move_line_ids.filtered(
            lambda ml: ml.product_id == self.productA
        )
        sml2 = delivery.move_line_ids.filtered(lambda ml: ml.product_id == product2)
        sml3 = delivery.move_line_ids.filtered(lambda ml: ml.product_id == product4)
        aggregate_val_1 = _aggregated(
            aggregate_values,
            f"{self.productA.id}_{self.productA.name}__{sml1.product_uom_id.id}_{sml1.move_id.packaging_uom_id.id}",
        )
        aggregate_val_2 = _aggregated(
            aggregate_values,
            f"{product2.id}_{product2.name}_Description2_{sml2.product_uom_id.id}_{sml2.move_id.packaging_uom_id.id}",
        )
        aggregate_val_3 = _aggregated(
            aggregate_values,
            f"{product4.id}_{product4.name}__{sml3.product_uom_id.id}_{sml3.move_id.packaging_uom_id.id}",
        )
        self.assertEqual(aggregate_val_1["qty_ordered"], 10)
        self.assertEqual(aggregate_val_1["quantity"], 6)
        self.assertEqual(aggregate_val_2["qty_ordered"], 10)
        self.assertEqual(aggregate_val_2["quantity"], 2)
        self.assertEqual(aggregate_val_3["qty_ordered"], 10)
        self.assertEqual(aggregate_val_3["quantity"], 2)
        aggregate_values = (
            first_backorder.move_line_ids._get_aggregated_product_quantities()
        )
        self.assertEqual(len(aggregate_values), 4)
        sml1 = first_backorder.move_line_ids.filtered(
            lambda ml: ml.product_id == self.productA
        )
        sml2 = first_backorder.move_line_ids.filtered(
            lambda ml: ml.product_id == product2
        )
        sml3 = first_backorder.move_line_ids.filtered(
            lambda ml: ml.product_id == product3
        )
        sml4 = first_backorder.move_line_ids.filtered(
            lambda ml: ml.product_id == product4
        )
        aggregate_val_1 = _aggregated(
            aggregate_values,
            f"{self.productA.id}_{self.productA.name}__{sml1.product_uom_id.id}_{sml1.move_id.packaging_uom_id.id}",
        )
        aggregate_val_2 = _aggregated(
            aggregate_values,
            f"{product2.id}_{product2.name}_Description2_{sml2.product_uom_id.id}_{sml2.move_id.packaging_uom_id.id}",
        )
        aggregate_val_3 = _aggregated(
            aggregate_values,
            f"{product3.id}_{product3.name}_Description3_{sml3.product_uom_id.id}_{sml3.move_id.packaging_uom_id.id}",
        )
        aggregate_val_4 = _aggregated(
            aggregate_values,
            f"{product4.id}_{product4.name}__{sml4.product_uom_id.id}_{sml4.move_id.packaging_uom_id.id}",
        )
        self.assertEqual(aggregate_val_1["qty_ordered"], 4)
        self.assertEqual(aggregate_val_1["quantity"], 4)
        self.assertEqual(aggregate_val_2["qty_ordered"], 8)
        self.assertEqual(aggregate_val_2["quantity"], 6)
        self.assertEqual(aggregate_val_3["qty_ordered"], 10)
        self.assertEqual(aggregate_val_3["quantity"], 7)
        self.assertEqual(aggregate_val_4["qty_ordered"], 8)
        self.assertEqual(aggregate_val_4["quantity"], 8)
        self.assertFalse(aggregate_val_1["description"])
        self.assertEqual(aggregate_val_2["description"], "Description2")
        self.assertEqual(aggregate_val_3["description"], "Description3")
        self.assertFalse(aggregate_val_4["description"])

        second_backorder.move_line_ids.filtered(
            lambda ml: ml.product_id == product2
        ).unlink()
        second_backorder.move_ids.picked = True
        backorder_wizard_dict = second_backorder.button_validate()
        backorder_wizard_form = Form.from_action(self.env, backorder_wizard_dict)
        backorder_wizard_form.save().action_cancel_backorder()

        aggregate_values = delivery.move_line_ids._get_aggregated_product_quantities()
        self.assertEqual(len(aggregate_values), 3)
        sml1 = delivery.move_line_ids.filtered(
            lambda ml: ml.product_id == self.productA
        )
        sml2 = delivery.move_line_ids.filtered(lambda ml: ml.product_id == product2)
        sml3 = delivery.move_line_ids.filtered(lambda ml: ml.product_id == product4)
        aggregate_val_1 = _aggregated(
            aggregate_values,
            f"{self.productA.id}_{self.productA.name}__{sml1.product_uom_id.id}_{sml1.move_id.packaging_uom_id.id}",
        )
        aggregate_val_2 = _aggregated(
            aggregate_values,
            f"{product2.id}_{product2.name}_Description2_{sml2.product_uom_id.id}_{sml2.move_id.packaging_uom_id.id}",
        )
        aggregate_val_3 = _aggregated(
            aggregate_values,
            f"{product4.id}_{product4.name}__{sml3.product_uom_id.id}_{sml3.move_id.packaging_uom_id.id}",
        )
        self.assertEqual(aggregate_val_1["qty_ordered"], 10)
        self.assertEqual(aggregate_val_1["quantity"], 6)
        self.assertEqual(aggregate_val_2["qty_ordered"], 10)
        self.assertEqual(aggregate_val_2["quantity"], 2)
        self.assertEqual(aggregate_val_3["qty_ordered"], 10)
        self.assertEqual(aggregate_val_3["quantity"], 2)
        aggregate_values = (
            first_backorder.move_line_ids._get_aggregated_product_quantities()
        )
        self.assertEqual(len(aggregate_values), 4)
        sml1 = first_backorder.move_line_ids.filtered(
            lambda ml: ml.product_id == self.productA
        )
        sml2 = first_backorder.move_line_ids.filtered(
            lambda ml: ml.product_id == product2
        )
        sml3 = first_backorder.move_line_ids.filtered(
            lambda ml: ml.product_id == product3
        )
        sml4 = first_backorder.move_line_ids.filtered(
            lambda ml: ml.product_id == product4
        )
        aggregate_val_1 = _aggregated(
            aggregate_values,
            f"{self.productA.id}_{self.productA.name}__{sml1.product_uom_id.id}_{sml1.move_id.packaging_uom_id.id}",
        )
        aggregate_val_2 = _aggregated(
            aggregate_values,
            f"{product2.id}_{product2.name}_Description2_{sml2.product_uom_id.id}_{sml2.move_id.packaging_uom_id.id}",
        )
        aggregate_val_3 = _aggregated(
            aggregate_values,
            f"{product3.id}_{product3.name}_Description3_{sml3.product_uom_id.id}_{sml3.move_id.packaging_uom_id.id}",
        )
        aggregate_val_4 = _aggregated(
            aggregate_values,
            f"{product4.id}_{product4.name}__{sml4.product_uom_id.id}_{sml4.move_id.packaging_uom_id.id}",
        )
        self.assertEqual(aggregate_val_1["qty_ordered"], 4)
        self.assertEqual(aggregate_val_1["quantity"], 4)
        self.assertEqual(aggregate_val_2["qty_ordered"], 8)
        self.assertEqual(aggregate_val_2["quantity"], 6)
        self.assertEqual(aggregate_val_3["qty_ordered"], 10)
        self.assertEqual(aggregate_val_3["quantity"], 7)
        self.assertEqual(aggregate_val_4["qty_ordered"], 8)
        self.assertEqual(aggregate_val_4["quantity"], 8)
        aggregate_values = (
            second_backorder.move_line_ids._get_aggregated_product_quantities()
        )
        self.assertEqual(len(aggregate_values), 2)
        sml1 = second_backorder.move_line_ids.filtered(
            lambda ml: ml.product_id == product3
        )
        sm2 = second_backorder.move_ids.filtered(lambda ml: ml.product_id == product2)
        aggregate_val_1 = _aggregated(
            aggregate_values,
            f"{product3.id}_{product3.name}_Description3_{sml1.product_uom_id.id}_{sml1.move_id.packaging_uom_id.id}",
        )
        aggregate_val_2 = _aggregated(
            aggregate_values,
            f"{product2.id}_{product2.name}_Description2_{sm2.product_uom_id.id}_{sml2.move_id.packaging_uom_id.id}",
        )
        self.assertEqual(aggregate_val_1["qty_ordered"], 3)
        self.assertEqual(aggregate_val_1["quantity"], 3)
        self.assertEqual(aggregate_val_2["qty_ordered"], 2)
        self.assertEqual(aggregate_val_2["quantity"], 0)

    def test_move_line_aggregated_product_quantities_duplicate_stock_move(self):
        self.env["stock.quant"]._update_available_quantity(
            self.productA, self.stock_location, 25
        )
        picking = self.env["stock.picking"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "picking_type_id": self.picking_type_out.id,
                "state": "draft",
            }
        )
        move1 = self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 10.0,
                "picking_id": picking.id,
                "picking_type_id": self.picking_type_out.id,
            }
        )
        move2 = self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 5.0,
                "picking_id": picking.id,
                "picking_type_id": self.picking_type_out.id,
            }
        )
        self.env["stock.move.line"].create(
            {
                "move_id": move1.id,
                "product_id": move1.product_id.id,
                "quantity": 10,
                "product_uom_id": move1.product_uom_id.id,
                "picking_id": picking.id,
                "location_id": move1.location_id.id,
                "location_dest_id": move1.location_dest_id.id,
            }
        )
        self.env["stock.move.line"].create(
            {
                "move_id": move2.id,
                "product_id": move2.product_id.id,
                "quantity": 5,
                "product_uom_id": move2.product_uom_id.id,
                "picking_id": picking.id,
                "location_id": move2.location_id.id,
                "location_dest_id": move2.location_dest_id.id,
            }
        )
        aggregate_values = picking.move_line_ids._get_aggregated_product_quantities()
        aggregated_val = _aggregated(
            aggregate_values,
            f"{self.productA.id}_{self.productA.name}__{self.productA.uom_id.id}_{self.productA.uom_id.id}",
        )
        self.assertEqual(aggregated_val["qty_ordered"], 15)
        picking.move_ids.picked = True
        picking.button_validate()
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location
            ),
            10,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.customer_location
            ),
            15,
        )

    def test_move_line_aggregated_product_quantities_two_packages(self):
        self.env["stock.quant"]._update_available_quantity(
            self.productA, self.stock_location, 25
        )
        picking = self.env["stock.picking"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "picking_type_id": self.picking_type_out.id,
                "state": "draft",
            }
        )
        move1 = self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 15.0,
                "picking_id": picking.id,
                "picking_type_id": self.picking_type_out.id,
            }
        )
        picking.action_confirm()
        picking.action_assign()
        move1.quantity = 5
        self.assertEqual(len(picking.move_line_ids), 1)

        picking.action_put_in_pack()
        picking.action_assign()
        self.assertEqual(len(picking.move_line_ids), 2)

        unpacked_ml = picking.move_line_ids.filtered(
            lambda ml: not ml.result_package_id
        )
        self.assertEqual(unpacked_ml.quantity_product_uom, 10)
        unpacked_ml.quantity = 10

        picking.action_put_in_pack()
        self.assertEqual(len(picking.move_line_ids), 2)

        picking.move_ids.picked = True
        picking.button_validate()
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location
            ),
            10,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.customer_location
            ),
            15,
        )

        qty_ordered_by_line_qty = {}
        for move_line in picking.move_line_ids:
            aggregate_values = move_line._get_aggregated_product_quantities(strict=True)
            aggregated_val = _aggregated(
                aggregate_values,
                f"{self.productA.id}_{self.productA.name}__{self.productA.uom_id.id}_{self.productA.uom_id.id}_{move_line.result_package_id.id}",
            )
            qty_ordered_by_line_qty[move_line.quantity_product_uom] = aggregated_val[
                "qty_ordered"
            ]
        self.assertEqual(qty_ordered_by_line_qty, {5: 5, 10: 10})

    def test_move_line_aggregated_product_quantities_incomplete_package(self):
        self.env["stock.quant"]._update_available_quantity(
            self.productA, self.stock_location, 25
        )
        picking = self.env["stock.picking"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "picking_type_id": self.picking_type_out.id,
                "state": "draft",
            }
        )
        move1 = self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 15.0,
                "picking_id": picking.id,
                "picking_type_id": self.picking_type_out.id,
            }
        )
        move1.quantity = 5
        move1.picked = True
        picking.action_put_in_pack()
        package = picking.move_line_ids.result_package_id

        delivery_form = Form(picking)
        delivery = delivery_form.save()
        delivery.action_confirm()

        backorder_wizard_dict = delivery.button_validate()
        backorder_wizard_form = Form.from_action(self.env, backorder_wizard_dict)
        backorder_wizard_form.save().process()
        picking.backorder_ids.action_cancel()

        aggregate_values = picking.move_line_ids._get_aggregated_product_quantities()
        aggregated_val = _aggregated(
            aggregate_values,
            f"{self.productA.id}_{self.productA.name}__{self.productA.uom_id.id}_{self.productA.uom_id.id}_{package.id}",
        )
        self.assertEqual(aggregated_val["qty_ordered"], 15)
        self.assertEqual(aggregated_val["quantity"], 5)

        aggregate_values = picking.move_line_ids._get_aggregated_product_quantities(
            strict=True
        )
        aggregated_val = _aggregated(
            aggregate_values,
            f"{self.productA.id}_{self.productA.name}__{self.productA.uom_id.id}_{self.productA.uom_id.id}_{package.id}",
        )
        self.assertEqual(aggregated_val["qty_ordered"], 5)
        self.assertEqual(aggregated_val["quantity"], 5)

        aggregate_values = picking.move_line_ids._get_aggregated_product_quantities(
            except_package=True
        )
        aggregated_val = _aggregated(
            aggregate_values,
            f"{self.productA.id}_{self.productA.name}__{self.productA.uom_id.id}_{self.productA.uom_id.id}",
        )
        self.assertEqual(aggregated_val["qty_ordered"], 10)
        self.assertEqual(aggregated_val["quantity"], False)

        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location
            ),
            20,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.customer_location
            ),
            5,
        )

    def test_move_sn_warning(self):
        lot1 = self.env["stock.lot"].create(
            {
                "name": "serial1",
                "product_id": self.product_serial.id,
            }
        )

        self.env["stock.quant"]._update_available_quantity(
            self.product_serial, self.pack_location, 1, lot_id=lot1
        )

        move = self.env["stock.move"].create(
            {
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
                "product_id": self.product_serial.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 1.0,
            }
        )

        move_line = self.env["stock.move.line"].create(
            {
                "move_id": move.id,
                "product_id": move.product_id.id,
                "quantity": 1,
                "product_uom_id": move.product_uom_id.id,
                "location_id": move.location_id.id,
                "location_dest_id": move.location_dest_id.id,
                "lot_name": lot1.name,
            }
        )

        warning = False
        warning = move_line._onchange_serial_number()
        self.assertTrue(warning, "Reuse of existing serial number (name) not detected")
        self.assertEqual(
            list(warning.keys())[0], "warning", "Warning message was not returned"
        )

        move_line.write({"lot_name": False, "lot_id": lot1.id})

        warning = False
        warning = move_line._onchange_serial_number()
        self.assertTrue(
            warning, "Reuse of existing serial number (record) not detected"
        )
        self.assertEqual(
            list(warning.keys())[0], "warning", "Warning message was not returned"
        )
        self.assertEqual(
            move_line.location_id, self.pack_location, "Location was not auto-corrected"
        )

        move_line.write({"lot_name": False, "lot_id": False})
        warning = move.onchange(
            {"lot_ids": [Command.link(lot1.id)]},
            ["lot_ids"],
            {"lot_ids": {"context": {}}},
        )
        self.assertTrue(
            warning, "Reuse of existing serial number (record) not detected"
        )
        self.assertIn(
            "Unavailable Serial numbers. Please correct the serial numbers encoded",
            warning.get("warning", {}).get("message", ""),
        )

    def test_forecast_availability(self):
        self.env["stock.quant"]._update_available_quantity(
            self.productA, self.stock_location, 36.0
        )
        picking_out = self.env["stock.picking"].create(
            {
                "picking_type_id": self.picking_type_out.id,
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "state": "draft",
            }
        )
        move = self.env["stock.move"].create(
            {
                "product_id": self.productA.id,
                "product_uom_id": self.uom_dozen.id,
                "product_uom_qty": 2.0,
                "picking_id": picking_out.id,
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
            }
        )
        picking_out.action_confirm()
        picking_out.action_assign()
        self.assertEqual(move.quantity, 2)
        self.assertEqual(move.forecast_availability, 24)

    def test_SML_location_selection(self):
        self.env.user.write(
            {"group_ids": [(3, self.env.ref("stock.group_stock_multi_locations").id)]}
        )

        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": self.picking_type_int.id,
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "state": "draft",
            }
        )
        self.env["stock.move"].create(
            {
                "product_id": self.product_consu.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 2.0,
                "picking_id": picking.id,
                "location_id": picking.location_id.id,
                "location_dest_id": picking.location_dest_id.id,
            }
        )

        picking.action_confirm()

        with Form(
            picking.move_ids, view="stock.view_stock_move_form_operations"
        ) as form:
            with form.move_line_ids.edit(0) as line:
                line.location_dest_id = self.stock_location.child_ids[0]
                line.quantity = 1

        self.assertEqual(
            picking.move_line_ids.location_dest_id, self.stock_location.child_ids[0]
        )

    def test_inter_wh_and_forecast_availability(self):
        dest_wh = self.env["stock.warehouse"].create(
            {
                "name": "Second Warehouse",
                "code": "WH02",
            }
        )

        move = self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": dest_wh.lot_stock_id.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 1.0,
            }
        )
        self.assertEqual(move.forecast_availability, -1)
        move._action_confirm()
        self.assertEqual(move.forecast_availability, -1)

    def test_move_compute_uom(self):
        move = self.env["stock.move"].create(
            {
                "product_id": self.productA.id,
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "move_line_ids": [(0, 0, {})],
            }
        )
        self.assertEqual(move.product_uom_id, self.productA.uom_id)
        self.assertEqual(move.move_line_ids.product_uom_id, self.productA.uom_id)
        uom_kg = self.env.ref("uom.product_uom_kgm")
        product1 = self.env["product.product"].create(
            {
                "name": "product1",
                "is_storable": True,
                "uom_id": uom_kg.id,
            }
        )
        move.product_id = product1
        self.assertEqual(move.product_uom_id, product1.uom_id)

    def test_move_line_compute_locations(self):
        move = self.env["stock.move"].create(
            {
                "product_id": self.productA.id,
                "location_id": self.stock_location.id,
                "location_dest_id": self.shelf_1.id,
                "move_line_ids": [(0, 0, {})],
            }
        )
        self.assertEqual(move.move_line_ids.location_id, self.stock_location)
        self.assertEqual(move.move_line_ids.location_dest_id, self.shelf_1)

        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": self.picking_type_int.id,
                "location_id": self.stock_location.id,
                "location_dest_id": self.shelf_1.id,
                "state": "draft",
                "move_line_ids": [
                    Command.create({"product_id": self.productA.id, "quantity": 1.0})
                ],
            }
        )
        self.assertEqual(picking.move_line_ids.location_id.id, self.stock_location.id)
        self.assertEqual(picking.move_line_ids.location_dest_id.id, self.shelf_1.id)

    def test_receive_more_and_in_child_location(self):
        move = self.env["stock.move"].create(
            {
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
                "product_id": self.productA.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 1.0,
            }
        )
        move._action_confirm()
        move.move_line_ids.write(
            {
                "location_dest_id": self.stock_location.child_ids[0].id,
                "quantity": 3,
            }
        )
        move.picked = True
        move._action_done()
        self.assertEqual(move.move_line_ids.quantity, 3)
        self.assertEqual(
            move.move_line_ids.location_dest_id, self.stock_location.child_ids[0]
        )

    def test_serial_tracking(self):
        sn = self.env["stock.lot"].create(
            {
                "name": "test_lot_001",
                "product_id": self.product_serial.id,
            }
        )

        internal_transfer = self.env["stock.picking"].create(
            {
                "state": "draft",
                "picking_type_id": self.picking_type_in.id,
            }
        )
        picking_form = Form(internal_transfer)
        with picking_form.move_ids.new() as move:
            move.product_id = self.product_serial
            move.product_uom_qty = 1
        receipt = picking_form.save()
        receipt.action_confirm()

        receipt_form = Form(receipt)
        with receipt_form.move_ids.edit(0) as move:
            move.lot_ids.add(sn)
        receipt = receipt_form.save()
        receipt.move_ids.picked = True
        receipt.button_validate()

        self.assertEqual(receipt.state, "done")
        self.assertEqual(len(receipt.move_line_ids), 1)
        self.assertEqual(receipt.move_line_ids.quantity, 1)

    def test_skip_putaway_if_dest_loc_set_by_user(self):
        self.env.user.write(
            {"group_ids": [(4, self.env.ref("stock.group_stock_multi_locations").id)]}
        )

        child_location = self.stock_location.child_ids[0]
        self.picking_type_in.show_operations = True

        receipt = self.env["stock.picking"].create(
            {
                "location_id": self.customer_location.id,
                "location_dest_id": self.stock_location.id,
                "picking_type_id": self.picking_type_in.id,
                "move_ids": [
                    (
                        0,
                        0,
                        {
                            "location_id": self.customer_location.id,
                            "location_dest_id": self.stock_location.id,
                            "product_id": self.productA.id,
                            "product_uom_id": self.productA.uom_id.id,
                            "product_uom_qty": 2.0,
                        },
                    )
                ],
            }
        )
        receipt.action_confirm()

        with Form(
            receipt.move_ids, view="stock.view_stock_move_form_operations"
        ) as move_form:
            with move_form.move_line_ids.edit(0) as line:
                line.location_dest_id = child_location
                line.quantity = 2

        self.assertRecordValues(
            receipt.move_ids.move_line_ids[-1],
            [
                {
                    "location_dest_id": child_location.id,
                    "product_id": self.productA.id,
                    "quantity": 2,
                },
            ],
        )

    def test_date_planned_after_backorder(self):
        today = fields.Datetime.today()
        with Form(self.env["stock.picking"]) as picking_form:
            picking_form.picking_type_id = self.picking_type_out
            with picking_form.move_ids.new() as move:
                move.product_id = self.productA
                move.product_uom_qty = 1
                move.date = today + relativedelta(day=5)
            with picking_form.move_ids.new() as move:
                move.product_id = self.product_consu
                move.product_uom_qty = 1
                move.date = today + relativedelta(day=10)
            picking = picking_form.save()

        move_product = picking.move_ids.filtered(
            lambda m: m.product_id == self.productA
        )
        move_product.date = today + relativedelta(day=5)
        move_consu = picking.move_ids.filtered(
            lambda m: m.product_id == self.product_consu
        )
        move_consu.date = today + relativedelta(day=10)
        self.assertEqual(picking.date_planned, today + relativedelta(day=5))
        picking.action_confirm()

        move_product.quantity = 1
        move_consu.quantity = 0
        Form.from_action(self.env, picking.button_validate()).save().with_user(
            self.user_stock_user
        ).process()
        backorder = self.env["stock.picking"].search(
            [("backorder_id", "=", picking.id)]
        )

        self.assertEqual(picking.date_planned, today + relativedelta(day=5))
        self.assertEqual(backorder.date_planned, today + relativedelta(day=10))

    def test_internal_transfer_with_tracked_product(self):
        sn01 = self.env["stock.lot"].create(
            {
                "name": "sn_1",
                "product_id": self.product_serial.id,
            }
        )
        self.env["stock.quant"]._update_available_quantity(
            self.product_serial, self.stock_location, 1.0, lot_id=sn01
        )
        with Form(self.env["stock.picking"]) as picking_form:
            picking_form.picking_type_id = self.picking_type_int
            with picking_form.move_ids.new() as move:
                move.product_id = self.product_serial
                move.product_uom_qty = 1
            picking = picking_form.save()

        picking.action_confirm()
        self.assertEqual(picking.state, "assigned")

        with Form(picking) as picking_form:
            with picking_form.move_ids.edit(0) as line_form:
                line_form.lot_ids.add(sn01)
            picking = picking_form.save()
        self.assertEqual(picking.move_ids.lot_ids, sn01)

    def test_change_move_line_uom(self):
        Quant = self.env["stock.quant"]
        Quant._update_available_quantity(self.productA, self.stock_location, 100)
        quant = Quant._gather(self.productA, self.stock_location)
        move = self.env["stock.move"].create(
            {
                "product_id": self.productA.id,
                "product_uom_qty": 1,
                "product_uom_id": self.productA.uom_id.id,
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
            }
        )
        move._action_confirm()
        move._action_assign()
        ml = move.move_line_ids

        self.assertEqual(quant.reserved_quantity, 1)

        ml.write({"quantity": 2, "product_uom_id": self.uom_dozen.id})
        self.assertEqual(quant.reserved_quantity, 24)
        ml.write({"product_uom_id": self.uom_unit.id})
        self.assertEqual(quant.reserved_quantity, 2)
        self.assertEqual(ml.quantity * self.uom_unit.factor, 2)

    def test_move_line_qty_with_quant_in_different_uom(self):
        Quant = self.env["stock.quant"]
        lot1 = self.env["stock.lot"].create(
            {
                "name": "lot1",
                "product_id": self.product_lot.id,
            }
        )
        move = self.env["stock.move"].create(
            {
                "product_id": self.product_lot.id,
                "product_uom_qty": 1,
                "product_uom_id": self.uom_dozen.id,
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
            }
        )
        move._action_confirm()
        Quant._update_available_quantity(
            self.product_lot, self.stock_location, 100, lot_id=lot1
        )
        quant = Quant._gather(self.product_lot, self.stock_location)
        move_form = Form(move, view="stock.view_stock_move_form_operations")
        with move_form.move_line_ids.new() as ml:
            ml.quant_id = quant
        move = move_form.save()
        self.assertEqual(quant.reserved_quantity, 12)

    def test_storage_category_restriction(self):
        product = self.productA

        storage_category = self.env["stock.storage.category"].create(
            {
                "name": "test_storage_category_restriction storage categ",
                "product_capacity_ids": [
                    Command.create(
                        {
                            "product_id": product.id,
                            "quantity": 5,
                        }
                    )
                ],
            }
        )
        self.shelf_1.storage_category_id = storage_category
        self.env["stock.putaway.rule"].create(
            {
                "product_id": product.id,
                "location_in_id": self.stock_location.id,
                "location_out_id": self.shelf_1.id,
                "storage_category_id": storage_category.id,
            }
        )

        receipt1 = self.env["stock.picking"].create(
            {
                "picking_type_id": self.picking_type_in.id,
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
                "move_ids": [
                    Command.create(
                        {
                            "product_id": product.id,
                            "product_uom_qty": 2.0,
                            "product_uom_id": product.uom_id.id,
                            "location_id": self.supplier_location.id,
                            "location_dest_id": self.stock_location.id,
                        }
                    )
                ],
            }
        )
        receipt1.action_confirm()

        receipt2 = self.env["stock.picking"].create(
            {
                "picking_type_id": self.picking_type_in.id,
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
                "move_ids": [
                    Command.create(
                        {
                            "product_id": product.id,
                            "product_uom_qty": 200.0,
                            "product_uom_id": product.uom_id.id,
                            "location_id": self.supplier_location.id,
                            "location_dest_id": self.stock_location.id,
                        }
                    )
                ],
            }
        )
        receipt2.action_confirm()
        receipt2.move_line_ids.quantity = 200.0
        receipt2.button_validate()

        total_qty = sum(self.shelf_1.quant_ids.mapped("quantity"))
        self.assertTrue(
            total_qty <= storage_category.product_capacity_ids.quantity,
            f"On-hand quantity = {total_qty}",
        )

    def test_correct_quantity_autofilled(self):
        self.productA.uom_id = self.env.ref("uom.product_uom_gram")
        quant = self.env["stock.quant"].create(
            {
                "product_id": self.productA.id,
                "location_id": self.stock_location.id,
                "quantity": 1000000,
            }
        )
        move = self.env["stock.move"].create(
            {
                "product_id": self.productA.id,
                "product_uom_qty": 2,
                "product_uom_id": self.env.ref("uom.product_uom_kgm").id,
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
            }
        )
        move._action_confirm()
        move.move_line_ids.unlink()
        line1 = self.env["stock.move.line"].create(
            {
                "move_id": move.id,
            }
        )
        line1.quant_id = quant
        self.assertEqual(move.move_line_ids.quantity, 2.0)
        line1.quantity = 1.0
        line2 = self.env["stock.move.line"].create(
            {
                "move_id": move.id,
            }
        )
        line2.quant_id = quant
        self.assertEqual(move.move_line_ids[1].quantity, 1.0)

    @freeze_time("2025-10-10")
    def test_free_reservation(self):
        self.env["stock.quant"]._update_available_quantity(
            self.productA, self.stock_location, 5
        )
        move_1, move_2 = self.env["stock.move"].create(
            [
                {
                    "product_id": self.productA.id,
                    "product_uom_qty": qty,
                    "product_uom_id": self.productA.uom_id.id,
                    "location_id": self.stock_location.id,
                    "location_dest_id": self.customer_location.id,
                }
                for qty in [2, 3]
            ]
        )
        (move_1 | move_2)._action_confirm()
        (move_1 | move_2)._action_assign()

        self.assertEqual(move_1.date, move_2.date)
        self.assertEqual(move_1.state, "assigned")
        self.assertEqual(move_2.state, "assigned")

        with Form(self.env["stock.scrap"]) as scrap_form:
            scrap_form.product_id = self.productA
            scrap_form.scrap_qty = 2
            scrap_form.location_id = self.stock_location
            scrap = scrap_form.save()
        scrap.action_validate()

        self.assertEqual(move_1.state, "assigned")
        self.assertEqual(move_2.state, "partially_available")

    def test_compute_show_info(self):
        self.picking_type_in.use_create_lots = True
        self.picking_type_in.use_existing_lots = True
        move1 = self.env["stock.move"].create(
            {
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
                "product_id": self.product_lot.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 5.0,
                "picking_type_id": self.picking_type_in.id,
            }
        )
        self.assertFalse(move1.show_lots_text)
        self.assertFalse(move1.show_lots_m2o)
        self.assertTrue(move1.show_quant)

    def test_recompute_stock_reference(self):
        receipt = self.env["stock.picking"].create(
            {
                "location_id": self.customer_location.id,
                "location_dest_id": self.stock_location.id,
                "picking_type_id": self.picking_type_in.id,
                "move_ids": [
                    (
                        0,
                        0,
                        {
                            "location_id": self.customer_location.id,
                            "location_dest_id": self.stock_location.id,
                            "product_id": self.productA.id,
                            "product_uom_id": self.productA.uom_id.id,
                            "product_uom_qty": 2.0,
                        },
                    )
                ],
            }
        )
        old_reference = receipt.move_ids.reference
        receipt.write(
            {
                "picking_type_id": self.picking_type_int.id,
            }
        )
        receipt.action_confirm()
        self.assertNotEqual(old_reference, receipt.move_ids.reference)

    def test_internal_picking_uses_shipping_policy_from_picking_type(self):
        for move_type in ["direct", "one"]:
            self.picking_type_int.move_type = move_type

            picking = self.env["stock.picking"].create(
                {
                    "picking_type_id": self.picking_type_int.id,
                }
            )

            self.assertEqual(picking.move_type, move_type)

    def test_autocomplete_sml_location_based_on_sm_lot_ids(self):
        lots = self.env["stock.lot"].create(
            [
                {
                    "name": name,
                    "product_id": self.product_serial.id,
                }
                for name in ["sn01", "sn02", "sn03"]
            ]
        )

        pack = self.env["stock.package"].create(
            {
                "name": "Pack A",
            }
        )

        self.env["stock.quant"]._update_available_quantity(
            self.product_serial, self.stock_location, 1, lot_id=lots[0]
        )
        self.env["stock.quant"]._update_available_quantity(
            self.product_serial, self.shelf_1, 1, lot_id=lots[1], package_id=pack
        )
        self.env["stock.quant"]._update_available_quantity(
            self.product_serial, self.pack_location, 1, lot_id=lots[2]
        )
        sm = self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "product_id": self.product_serial.id,
                "product_uom_id": self.uom_unit.id,
                "product_uom_qty": 3.0,
            }
        )
        sm._action_confirm()

        sm.lot_ids = [(6, 0, lots.ids)]

        self.assertRecordValues(
            sm.move_line_ids,
            [
                {
                    "location_id": self.stock_location.id,
                    "lot_id": lots[0].id,
                    "package_id": False,
                },
                {
                    "location_id": self.shelf_1.id,
                    "lot_id": lots[1].id,
                    "package_id": pack.id,
                },
                {
                    "location_id": self.stock_location.id,
                    "lot_id": lots[2].id,
                    "package_id": False,
                },
            ],
        )

    def test_change_dest_loc_after_sm_creation(self):
        form = Form(
            self.env["stock.picking"].with_context(
                restricted_picking_type_code="incoming"
            )
        )
        with form.move_ids.new() as move:
            move.product_id = self.productA
            move.product_uom_qty = 1
        form.location_dest_id = self.customer_location
        self.assertEqual(form.move_ids.edit(0).location_dest_id, self.customer_location)

        picking = form.save()
        self.assertEqual(picking.move_ids.location_dest_id, self.customer_location)

        form = Form(picking)
        with form.move_ids.new() as move:
            move.product_id = self.product_consu
            move.product_uom_qty = 1
        form.location_dest_id = self.stock_location
        self.assertEqual(form.move_ids.edit(0).location_dest_id, self.stock_location)
        self.assertEqual(form.move_ids.edit(1).location_dest_id, self.stock_location)

        picking = form.save()
        self.assertEqual(picking.move_ids.location_dest_id, self.stock_location)

    def test_set_quantity_done_with_rounding_issues(self):
        gram_uom = self.env.ref("uom.product_uom_gram")
        oz_uom = self.env.ref("uom.product_uom_oz")

        self.productA.write({"uom_id": oz_uom.id})
        self.env["stock.quant"]._update_available_quantity(
            self.productA, self.stock_location, 10
        )

        delivery = self.env["stock.picking"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "picking_type_id": self.picking_type_out.id,
                "move_ids": [
                    (
                        0,
                        0,
                        {
                            "location_id": self.stock_location.id,
                            "location_dest_id": self.customer_location.id,
                            "product_id": self.productA.id,
                            "product_uom_id": gram_uom.id,
                            "product_uom_qty": 150.0,
                        },
                    )
                ],
            }
        )
        delivery.action_confirm()
        delivery.action_assign()

        self.assertEqual(delivery.move_ids.quantity, 149.97)
        delivery.move_ids.write({"quantity": 150})

        self.assertEqual(delivery.move_ids.quantity, 150)
        delivery.button_validate()
        self.assertEqual(delivery.state, "done")
        lines = delivery.move_line_ids
        self.assertRecordValues(lines, [{"quantity": 149.97}, {"quantity": 0.03}])
        for line in lines:
            self.assertAlmostEqual(
                line.quantity_product_uom,
                gram_uom._get_quantity_in_unit(line.quantity, oz_uom, round=False),
            )
        self.assertAlmostEqual(
            sum(lines.mapped("quantity_product_uom")),
            gram_uom._get_quantity_in_unit(150.0, oz_uom, round=False),
        )

    def test_in_sub_precision_quantity_is_not_dropped(self):
        gram_uom = self.env.ref("uom.product_uom_gram")
        kg_uom = self.env.ref("uom.product_uom_kgm")
        self.productA.write({"uom_id": kg_uom.id, "is_storable": True})

        move = self.env["stock.move"].create(
            {
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
                "product_id": self.productA.id,
                "product_uom_id": gram_uom.id,
                "product_uom_qty": 2.0,
                "picking_type_id": self.picking_type_in.id,
            }
        )
        move._action_confirm()

        self.assertEqual(len(move.move_line_ids), 1)
        self.assertEqual(move.move_line_ids.quantity, 2.0)
        self.assertAlmostEqual(move.move_line_ids.quantity_product_uom, 0.002)

        move.picked = True
        move._action_done()

        self.assertEqual(move.state, "done")
        self.assertEqual(move.quantity, 2.0)
        self.assertAlmostEqual(self.productA.qty_available, 0.002)
        self.assertFalse(kg_uom._is_zero_aggregate(self.productA.qty_available))

    def test_move_state_after_split(self):
        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": self.env.ref("stock.picking_type_out").id,
                "location_id": self.stock_location.id,
                "location_dest_id": self.supplier_location.id,
                "move_ids": [
                    Command.create(
                        {
                            "product_id": self.product.id,
                            "product_uom_qty": 10,
                            "location_id": self.stock_location.id,
                            "location_dest_id": self.supplier_location.id,
                        }
                    )
                ],
            }
        )
        self.product.is_storable = True
        self.env["stock.quant"]._update_available_quantity(
            self.product, self.stock_location, 10
        )
        picking.action_confirm()
        self.assertEqual(picking.move_ids.state, "assigned")
        picking.move_ids.quantity = 4
        self.assertEqual(picking.move_ids.state, "partially_available")
        picking.action_split_transfer()
        self.assertEqual(len(picking.move_ids), 1)
        self.assertEqual(picking.move_ids.product_uom_qty, 4)
        self.assertEqual(picking.move_ids.state, "assigned")
        backorder = picking.backorder_ids
        self.assertEqual(backorder.move_ids.product_uom_qty, 6)
        self.assertEqual(backorder.move_ids.quantity, 6)
        self.assertEqual(backorder.move_ids.state, "assigned")

    def test_edit_serial_number_from_move(self):
        lot1 = self.env["stock.lot"].create(
            {
                "product_id": self.product_serial.id,
            }
        )
        lot2 = self.env["stock.lot"].create(
            {
                "product_id": self.product_serial.id,
            }
        )
        self.env["stock.quant"]._update_available_quantity(
            self.product_serial, self.stock_location, 1, lot_id=lot1
        )
        self.env["stock.quant"]._update_available_quantity(
            self.product_serial, self.stock_location, 1, lot_id=lot2
        )
        picking = self.env["stock.picking"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "picking_type_id": self.picking_type_out.id,
                "move_ids": [
                    Command.create(
                        {
                            "location_id": self.stock_location.id,
                            "location_dest_id": self.customer_location.id,
                            "product_id": self.product_serial.id,
                            "product_uom_qty": 1,
                        }
                    )
                ],
            }
        )
        picking.action_confirm()
        self.assertEqual(picking.move_ids.state, "assigned")
        self.assertEqual(picking.move_ids.lot_ids, lot1)
        picking.move_ids.lot_ids = lot2
        self.assertEqual(picking.move_ids.lot_ids, lot2)
        self.assertEqual(picking.move_line_ids.lot_id, lot2)
        picking.button_validate()
        self.assertEqual(picking.move_ids.lot_ids, lot2)

    def test_delivery_slip_aggregated_lines_with_canceled_move_and_packaging(self):
        pack_of_6 = self.env.ref("uom.product_uom_pack_6")
        self.env["stock.quant"]._update_available_quantity(
            self.productA, self.stock_location, 6
        )
        picking = self.env["stock.picking"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "picking_type_id": self.picking_type_out.id,
                "move_ids": [
                    Command.create(
                        {
                            "product_id": self.productA.id,
                            "product_uom_qty": 1,
                            "product_uom_id": pack_of_6.id,
                            "location_id": self.stock_location.id,
                            "location_dest_id": self.customer_location.id,
                        }
                    ),
                    Command.create(
                        {
                            "product_id": self.productB.id,
                            "product_uom_qty": 1,
                            "product_uom_id": pack_of_6.id,
                            "location_id": self.stock_location.id,
                            "location_dest_id": self.customer_location.id,
                        }
                    ),
                ],
            }
        )
        picking.action_confirm()
        self.assertEqual(picking.move_ids.mapped("quantity"), [1.0, 0])
        picking.action_split_transfer()
        backorder = picking.backorder_ids
        backorder.action_cancel()
        picking.button_validate()
        self.assertEqual(backorder.state, "cancel")
        self.assertEqual(picking.state, "done")
        aggregate_values = picking.move_line_ids._get_aggregated_product_quantities()
        self.assertEqual(len(aggregate_values), 2)
        aggregate_val_1 = _aggregated(
            aggregate_values,
            f"{self.productA.id}_{self.productA.name}__{pack_of_6.id}_{pack_of_6.id}",
        )
        aggregate_val_2 = _aggregated(
            aggregate_values,
            f"{self.productB.id}_{self.productB.name}__{pack_of_6.id}_{pack_of_6.id}",
        )
        self.assertEqual(aggregate_val_1["qty_ordered"], 1.0)
        self.assertEqual(aggregate_val_1["quantity"], 1.0)
        self.assertEqual(aggregate_val_1["packaging_qty_ordered"], 1.0)
        self.assertEqual(aggregate_val_2["qty_ordered"], 1.0)
        self.assertEqual(aggregate_val_2["quantity"], 0)
        self.assertEqual(aggregate_val_2["packaging_qty_ordered"], 0.0)

    def test_newly_added_move_line_is_picked_if_move_is_picked(self):
        lot_1, lot_2 = self.env["stock.lot"].create(
            [
                {
                    "name": "lot_1",
                    "product_id": self.product_lot.id,
                },
                {
                    "name": "lot_2",
                    "product_id": self.product_lot.id,
                },
            ]
        )
        for lot_id in [lot_1, lot_2]:
            self.env["stock.quant"]._update_available_quantity(
                self.product_lot, self.stock_location, 3, lot_id=lot_id
            )
        with Form(self.env["stock.picking"]) as delivery_form:
            delivery_form.picking_type_id = self.picking_type_out
            with delivery_form.move_ids.new() as move:
                move.product_id = self.product_lot
                move.product_uom_qty = 3
            delivery = delivery_form.save()
        delivery.action_confirm()
        self.assertEqual(delivery.move_ids.move_line_ids.lot_id, lot_1)
        delivery.move_ids.picked = True
        self.assertTrue(delivery.move_ids.move_line_ids.picked)
        action = delivery.move_ids.action_show_details()
        with Form(
            delivery.move_ids.with_context(action["context"]), view=action["view_id"]
        ) as form:
            with form.move_line_ids.edit(0) as existing_move_line:
                existing_move_line.quantity = 2
            with form.move_line_ids.new() as new_move_line:
                new_move_line.lot_id = lot_2
                new_move_line.quantity = 1

        self.assertTrue(delivery.move_ids.picked)
        for move_line in delivery.move_ids.move_line_ids:
            self.assertTrue(move_line.picked)

    def test_show_lot_actions_follows_state(self):
        picking_type = self.env.ref("stock.picking_type_in")
        self.assertTrue(picking_type.use_create_lots)
        product = self.env["product.product"].create(
            {"name": "SN product", "is_storable": True, "tracking": "serial"}
        )
        receipt = self.env["stock.picking"].create(
            {
                "picking_type_id": picking_type.id,
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
                "move_ids": [
                    Command.create(
                        {
                            "product_id": product.id,
                            "product_uom_id": product.uom_id.id,
                            "product_uom_qty": 1.0,
                        }
                    )
                ],
            }
        )
        move = receipt.move_ids
        receipt.action_confirm()
        self.assertTrue(move.show_lot_actions)

        self.assertEqual(len(move.move_line_ids), 1)
        move.move_line_ids.lot_name = "sn-1"
        move.picked = True
        receipt.button_validate()

        self.assertEqual(move.state, "done")
        self.assertFalse(
            move.show_lot_actions,
            "a done move must not offer the lot buttons any more",
        )

    def test_show_lot_actions_follows_origin_returned_move(self):
        picking_type = self.env.ref("stock.picking_type_in")
        product = self.env["product.product"].create(
            {"name": "SN product 2", "is_storable": True, "tracking": "serial"}
        )
        receipt = self.env["stock.picking"].create(
            {
                "picking_type_id": picking_type.id,
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
                "move_ids": [
                    Command.create(
                        {
                            "product_id": product.id,
                            "product_uom_id": product.uom_id.id,
                            "product_uom_qty": 1.0,
                        }
                    )
                ],
            }
        )
        move = receipt.move_ids
        receipt.action_confirm()
        self.assertTrue(move.show_lot_actions)

        origin = self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.supplier_location.id,
                "product_id": product.id,
                "product_uom_id": product.uom_id.id,
                "product_uom_qty": 1.0,
            }
        )
        move.origin_returned_move_id = origin
        self.assertFalse(
            move.show_lot_actions,
            "a return move must not offer to create new lots",
        )
