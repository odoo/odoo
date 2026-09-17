from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestMaintenanceStock(TransactionCase):
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
        cls.kind = cls.env["resource.asset.kind"].create(
            {"name": "Stocked Truck", "code": "stocked_truck"}
        )
        cls.position = cls.env["resource.asset.kind.position"].create(
            {"kind_id": cls.kind.id, "name": "Starter", "code": "starter"}
        )
        cls.starter = cls.env["product.product"].create(
            {"name": "Starter motor", "is_storable": True, "tracking": "serial"}
        )
        cls.truck = cls.env["resource.asset"].create(
            {"name": "Truck 40", "kind_id": cls.kind.id}
        )
        cls.stock = cls.env.ref("stock.stock_location_stock")
        cls.removed_parts = cls.env["stock.location"].create(
            {"name": "Removed Parts", "usage": "internal", "location_id": cls.stock.id}
        )
        cls.lot = cls.env["stock.lot"].create(
            {
                "name": "ST-100",
                "product_id": cls.starter.id,
                "company_id": cls.env.company.id,
            }
        )
        cls.env["stock.quant"]._update_available_quantity(
            cls.starter, cls.stock, 1, lot_id=cls.lot
        )
        cls.vendor = cls.env["res.partner"].create({"name": "Electric Shop"})

    def _order_with_part(self, **vals):
        order = self.env["maintenance.order"].create(
            {
                "name": "Starter replacement",
                "resource_ids": [(6, 0, self.truck.resource_id.ids)],
                "block_resource": False,
                "vendor_id": self.vendor.id,
            }
        )
        part = self.env["resource.asset.part"].create(
            {
                "maintenance_order_id": order.id,
                "asset_id": self.truck.id,
                "position_id": self.position.id,
                "product_id": self.starter.id,
                "serial": "ST-100",
                **vals,
            }
        )
        return order, part

    def _qty(self, location, lot=None):
        return self.env["stock.quant"]._get_available_quantity(
            self.starter, location, lot_id=lot, strict=True
        )

    def test_a_part_taken_from_stock_is_consumed_at_closing(self):
        order, part = self._order_with_part(stock_location_id=self.stock.id)

        order.action_confirm()
        order.action_done()

        self.assertEqual(part.move_id.state, "done")
        self.assertEqual(part.move_id.move_line_ids.lot_id, self.lot)
        self.assertEqual(self._qty(self.stock, self.lot), 0)

    def test_a_vendor_supplied_part_moves_no_stock(self):
        order, part = self._order_with_part()

        order.action_confirm()
        order.action_done()

        self.assertFalse(part.move_id)
        self.assertEqual(self._qty(self.stock, self.lot), 1)

    def test_receiving_the_removed_part_resolves_its_flag(self):
        order, part = self._order_with_part(
            removed_serial="ST-OLD", removed_location_id=self.removed_parts.id
        )
        order.action_confirm()
        order.action_done()
        self.assertEqual(part.flag_ids.reason, "not_returned")

        part.action_receive_removed_part()

        self.assertTrue(part.removed_returned)
        self.assertEqual(part.review_state, "cleared")
        received = part.removed_move_id.move_line_ids.lot_id
        self.assertEqual(received.name, "ST-OLD")
        self.assertEqual(self._qty(self.removed_parts, received), 1)
        with self.assertRaises(UserError):
            part.action_receive_removed_part()

    def test_a_tracked_part_needs_its_serial(self):
        order, part = self._order_with_part(removed_location_id=self.removed_parts.id)
        order.action_confirm()
        order.action_done()

        with self.assertRaises(UserError):
            part.action_receive_removed_part()
