from odoo import Command
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestDispatchManagement(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.warehouse = cls.env["stock.warehouse"].search([], limit=1)
        cls.stock_location = cls.warehouse.lot_stock_id
        cls.customer_location = cls.env.ref("stock.stock_location_customers")
        cls.dock = cls.env["stock.location"].create(
            {
                "name": "Dock A",
                "usage": "internal",
                "location_id": cls.warehouse.view_location_id.id,
            }
        )
        cls.out_type = cls.warehouse.out_type_id
        cls.out_type.dock_ids = [Command.set(cls.dock.ids)]
        cls.in_type = cls.warehouse.in_type_id
        cls.in_type.dock_ids = [Command.set(cls.dock.ids)]

        cls.model = cls.env["product.product"].create(
            {
                "name": "Test Van",
                "type": "consu",
                "asset_kind_id": cls.env.ref("resource_asset.kind_vehicle").id,
                "weight_capacity": 100.0,
                "volume_capacity": 20.0,
            }
        )
        cls.driver = cls.env["res.partner"].create({"name": "Driver"})
        cls.vehicle = cls.env["resource.asset"].create(
            {
                "name": "Van",
                "kind_id": cls.env.ref("resource_asset.kind_vehicle").id,
                "product_id": cls.model.id,
                "operator_id": cls.env["resource.resource"]
                .create(
                    {
                        "name": "Driver",
                        "resource_type": "user",
                        "partner_id": cls.driver.id,
                    }
                )
                .id,
            }
        )
        cls.product = cls.env["product.product"].create(
            {
                "name": "Freight",
                "is_storable": True,
                "weight": 10.0,
                "volume": 2.0,
            }
        )
        cls.env["stock.quant"]._update_available_quantity(
            cls.product, cls.stock_location, 1000
        )

    def _picking(self, picking_type=None, zip_code=False, quantity=1):
        picking_type = picking_type or self.out_type
        partner = self.env["res.partner"].create(
            {"name": f"P{zip_code or 'x'}", "zip": zip_code}
        )
        outgoing = picking_type.code == "outgoing"
        src = self.stock_location if outgoing else self.customer_location
        dest = self.customer_location if outgoing else self.stock_location
        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": picking_type.id,
                "partner_id": partner.id,
                "location_id": src.id,
                "location_dest_id": dest.id,
                "move_ids": [
                    Command.create(
                        {
                            "product_id": self.product.id,
                            "product_uom_qty": quantity,
                            "location_id": src.id,
                            "location_dest_id": dest.id,
                        }
                    )
                ],
            }
        )
        picking.action_confirm()
        return picking

    def _batch(self, pickings, picking_type=None, **vals):
        return self.env["stock.picking.batch"].create(
            {
                "picking_type_id": (picking_type or self.out_type).id,
                "picking_ids": [Command.set(pickings.ids)],
                **vals,
            }
        )

    def test_a_dock_moves_the_source_of_an_outgoing_transfer(self):
        picking = self._picking()
        original = picking.move_ids.location_id
        batch = self._batch(picking, dock_id=self.dock.id)
        self.assertEqual(batch.dock_id, self.dock)
        self.assertEqual(picking.move_ids.location_id, self.dock)
        self.assertNotEqual(picking.move_ids.location_id, original)

    def test_a_dock_moves_the_destination_of_an_incoming_transfer(self):
        picking = self._picking(picking_type=self.in_type)
        batch = self._batch(picking, picking_type=self.in_type, dock_id=self.dock.id)
        self.assertEqual(batch.dock_id, self.dock)
        self.assertEqual(picking.move_ids.location_dest_id, self.dock)

    def test_clearing_the_dock_restores_the_transfer_own_destination(self):
        picking = self._picking(picking_type=self.in_type)
        batch = self._batch(picking, picking_type=self.in_type, dock_id=self.dock.id)
        self.assertEqual(picking.move_ids.location_dest_id, self.dock)
        batch.dock_id = False
        self.assertEqual(picking.move_ids.location_dest_id, picking.location_dest_id)

    def test_transfers_are_sequenced_by_the_partner_postcode(self):
        far = self._picking(zip_code="9000")
        near = self._picking(zip_code="1000")
        middle = self._picking(zip_code="5000")
        self._batch(far | near | middle)
        self.assertEqual(near.batch_sequence, 0)
        self.assertEqual(middle.batch_sequence, 1)
        self.assertEqual(far.batch_sequence, 2)

    def test_the_load_is_measured_against_the_vehicle_model(self):
        picking = self._picking(quantity=5)
        picking.move_ids.quantity = 5
        batch = self._batch(picking, vehicle_id=self.vehicle.id)
        self.assertEqual(batch.vehicle_model_id, self.model)
        self.assertEqual(batch.driver_id, self.driver)
        self.assertEqual(batch.estimated_shipping_weight, 50.0)
        self.assertEqual(batch.used_weight_percentage, 50.0)

    def test_a_batch_with_no_vehicle_reports_no_load_percentage(self):
        picking = self._picking(quantity=5)
        picking.move_ids.quantity = 5
        batch = self._batch(picking)
        self.assertFalse(batch.vehicle_id)
        self.assertEqual(batch.used_weight_percentage, 0.0)
        self.assertEqual(batch.used_volume_percentage, 0.0)

    def test_merging_carries_the_vehicle_and_the_dock(self):
        first = self._batch(
            self._picking(), vehicle_id=self.vehicle.id, dock_id=self.dock.id
        )
        second = self._batch(self._picking())
        (first | second).action_merge()
        self.assertEqual(first.vehicle_id.id, self.vehicle.id)
        self.assertEqual(first.dock_id, self.dock)

    def test_docking_a_reserved_transfer_throws_its_reservation_away(self):
        picking = self._picking(quantity=3)
        picking.action_assign()
        self.assertEqual(picking.state, "assigned")
        self.assertTrue(picking.move_ids.move_line_ids)

        self._batch(picking, dock_id=self.dock.id)
        picking.invalidate_recordset()
        self.assertEqual(picking.move_ids.location_id, self.dock)
        self.assertFalse(
            picking.move_ids.move_line_ids,
            "Setting a dock rewrites the move source, which unreserves it. "
            "Assembling a truckload therefore drops the reservation on every "
            "outgoing transfer in the batch.",
        )
        self.assertNotEqual(picking.state, "assigned")

    def test_a_transfer_added_after_the_batch_exists_is_sequenced_too(self):
        near = self._picking(zip_code="1000")
        batch = self._batch(near)
        far = self._picking(zip_code="9000")
        middle = self._picking(zip_code="5000")
        batch.picking_ids = [Command.link(far.id), Command.link(middle.id)]
        self.assertEqual(
            [near.batch_sequence, middle.batch_sequence, far.batch_sequence],
            [0, 1, 2],
            "order_on_zip ran in create only, so a transfer joining an existing "
            "batch kept sequence 0 and the route order the map view and the "
            "report read was absent.",
        )
