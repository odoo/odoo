from datetime import datetime, timedelta

from odoo.exceptions import UserError, ValidationError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestMaintenanceTransfer(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["approval.category"].search(
            [
                (
                    "approval_type",
                    "in",
                    ("maintenance_preventive", "maintenance_corrective"),
                )
            ]
        ).action_archive()
        cls.warehouse = cls.env["stock.warehouse"].search(
            [("company_id", "=", cls.env.company.id)], limit=1
        )
        cls.warehouse.allow_maintenance = True
        cls.product = cls.env["product.product"].create(
            {
                "name": "Transfer probe machine",
                "is_storable": True,
                "tracking": "serial",
                "asset_kind_id": cls.env.ref("resource_asset.kind_machinery").id,
            }
        )
        cls.lot = cls._stocked_lot("TRANSFER-1")
        cls.vendor = cls.env["res.partner"].create({"name": "Transfer probe vendor"})

    @classmethod
    def _stocked_lot(cls, name, location=None):
        lot = cls.env["stock.lot"].create({"name": name, "product_id": cls.product.id})
        cls.env["stock.quant"]._update_available_quantity(
            cls.product, location or cls.warehouse.lot_stock_id, 1, lot_id=lot
        )
        lot.invalidate_recordset(["location_id"])
        return lot

    def _order(self, **vals):
        return self.env["maintenance.order"].create(
            {
                "name": "Replace hydraulic hose",
                "resource_ids": self.lot.asset_id.resource_id.ids,
                "maintenance_type": "corrective",
                "date_scheduled_start": datetime.now(),
                "duration": 24,
                "block_resource": False,
                "vendor_id": self.vendor.id,
                "state": "confirmed",
                **vals,
            }
        )

    def _send(self, order):
        picking = order._create_transfer(*order._resolve_warehouse_route())
        picking.move_ids.picked = True
        picking._action_done()
        return picking

    def _return(self, picking, lots=None):
        lots = lots or self.lot
        wizard = (
            self.env["stock.return.picking"]
            .with_context(active_id=picking.id, active_model="stock.picking")
            .create({})
        )
        by_product = lots.grouped("product_id")
        for line in wizard.product_return_moves:
            line.quantity = len(by_product[line.product_id])
        returned = self.env["stock.picking"].browse(
            wizard.action_create_returns()["res_id"]
        )
        for move in returned.move_ids:
            move.lot_ids = by_product[move.product_id]
        returned.move_ids.picked = True
        returned._action_done()
        return returned

    def test_enabling_maintenance_opens_a_location_and_two_operations(self):
        warehouse = self.warehouse
        self.assertTrue(warehouse.wh_maintenance_stock_loc_id.maintenance_location)
        self.assertTrue(warehouse.wh_maintenance_stock_loc_id.active)
        self.assertEqual(
            warehouse.maintenance_type_id.return_picking_type_id,
            warehouse.maintenance_return_type_id,
        )
        self.assertTrue(warehouse.maintenance_type_id.active)

        warehouse.allow_maintenance = False

        self.assertFalse(warehouse.maintenance_type_id.active)
        self.assertFalse(warehouse.wh_maintenance_stock_loc_id.active)

    def test_the_order_names_the_lots_of_its_assets(self):
        order = self._order()
        self.assertEqual(order.lot_ids, self.lot)
        self.assertEqual(
            self.env["maintenance.order"].search([("lot_ids", "in", self.lot.ids)]),
            order,
        )

    def test_one_transfer_sends_every_serial_of_the_order(self):
        shelf = self.env["stock.location"].create(
            {"name": "Shelf", "location_id": self.warehouse.lot_stock_id.id}
        )
        second = self._stocked_lot("TRANSFER-2", location=shelf)
        self._stocked_lot("TRANSFER-IDLE")
        order = self._order(resource_ids=(self.lot | second).asset_id.resource_id.ids)
        self.assertEqual(order._get_lot_location(), self.warehouse.lot_stock_id)

        picking = self._send(order)

        self.assertEqual(picking.move_ids.move_line_ids.lot_id, self.lot | second)
        self.assertEqual(order.state, "in_progress")

    def test_the_order_closes_once_every_serial_is_back(self):
        second = self._stocked_lot("TRANSFER-2")
        order = self._order(resource_ids=(self.lot | second).asset_id.resource_id.ids)
        picking = self._send(order)

        self._return(picking, lots=self.lot)
        self.assertEqual(order.state, "in_progress")
        self.assertFalse(order.date_returned)
        self.assertEqual(order.asset_log_ids.asset_id, self.lot.asset_id)

        last = self._return(picking, lots=second)
        self.assertEqual(order.state, "done")
        self.assertEqual(order.date_returned, last.date_done)
        self.assertEqual(order.asset_log_ids.asset_id, (self.lot | second).asset_id)

    def test_the_route_is_the_warehouse_maintenance_setup(self):
        self.assertEqual(
            self._order()._resolve_warehouse_route(),
            (
                self.warehouse.lot_stock_id,
                self.warehouse.wh_maintenance_stock_loc_id,
                self.warehouse.maintenance_type_id,
            ),
        )

    def test_sending_the_equipment_out_puts_the_order_in_progress(self):
        order = self._order()
        picking = self._send(order)
        self.assertEqual(picking.maintenance_order_id, order)
        self.assertEqual(picking.partner_id, self.vendor)
        self.assertEqual(order.state, "in_progress")

    def test_an_order_is_sent_out_once(self):
        order = self._order()
        order._create_transfer(*order._resolve_warehouse_route())
        with self.assertRaises(UserError):
            order._create_transfer(*order._resolve_warehouse_route())

    def test_the_return_closes_the_order_and_logs_the_service(self):
        order = self._order()
        returned = self._return(self._send(order))
        self.assertEqual(returned.maintenance_order_id, order)
        self.assertEqual(order.state, "done")
        self.assertEqual(order.date_returned, returned.date_done)
        self.assertTrue(order.is_returned_on_time)
        self.assertLess(order.return_delay_days, 0)
        self.assertRecordValues(
            order.asset_log_ids,
            [
                {
                    "log_type": "service",
                    "source": "maintenance",
                    "vendor_id": self.vendor.id,
                    "maintenance_order_id": order.id,
                }
            ],
        )

    def test_a_late_return_reads_as_late(self):
        order = self._order(
            date_scheduled_start=datetime.now() - timedelta(days=3), duration=24
        )
        self._return(self._send(order))
        self.assertFalse(order.is_returned_on_time)
        self.assertGreater(order.return_delay_days, 1)

    def test_returning_other_equipment_than_was_sent_is_refused(self):
        order = self._order()
        other = self.env["stock.lot"].create(
            {"name": "TRANSFER-OTHER", "product_id": self.product.id}
        )
        with self.assertRaises(ValidationError):
            self._return(self._send(order), lots=other)

    def test_the_transfer_wizard_proposes_the_warehouse_route(self):
        order = self._order()
        wizard = self.env["maintenance.transfer.wizard"].create({"order_id": order.id})
        self.assertEqual(
            wizard.location_dest_id, self.warehouse.wh_maintenance_stock_loc_id
        )
        action = wizard.action_send()
        self.assertEqual(order.picking_ids.id, action["res_id"])

    def test_a_cancelled_transfer_lets_the_order_be_sent_again(self):
        order = self._order()
        order._create_transfer(*order._resolve_warehouse_route()).action_cancel()
        self.assertFalse(order.is_sent)
        order._create_transfer(*order._resolve_warehouse_route())
        self.assertTrue(order.is_sent)

    def test_sending_the_equipment_back_again_logs_no_second_service(self):
        order = self._order()
        returned = self._return(self._send(order))
        sent_again = self._return(returned)
        self.assertFalse(sent_again._is_maintenance_return())
        back_again = self._return(sent_again)
        self.assertTrue(back_again._is_maintenance_return())
        self.assertEqual(
            self.env["resource.asset.log"].search_count(
                [("maintenance_order_id", "=", order.id)]
            ),
            1,
        )
        self.assertEqual(order.date_returned, back_again.date_done)
