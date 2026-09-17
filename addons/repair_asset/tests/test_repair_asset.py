from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestRepairAsset(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.vehicle = cls.env.ref("resource_asset.kind_vehicle")
        cls.position = cls.env["resource.asset.kind.position"].create(
            {
                "kind_id": cls.vehicle.id,
                "name": "Water pump",
                "code": "repair_water_pump",
                "expected_life_days": 365,
            }
        )
        cls.pickup = cls.env["product.product"].create(
            {
                "name": "Repaired Pickup",
                "is_storable": True,
                "tracking": "serial",
                "asset_kind_id": cls.vehicle.id,
            }
        )
        cls.pump = cls.env["product.product"].create(
            {"name": "Water pump", "is_storable": True}
        )
        cls.warehouse = cls.env["stock.warehouse"].search(
            [("company_id", "=", cls.env.company.id)], limit=1
        )
        cls.stock = cls.warehouse.lot_stock_id
        cls.lot = cls.env["stock.lot"].create(
            {
                "name": "PU-900",
                "product_id": cls.pickup.id,
                "company_id": cls.env.company.id,
            }
        )
        Quant = cls.env["stock.quant"]
        Quant._update_available_quantity(cls.pickup, cls.stock, 1, lot_id=cls.lot)
        Quant._update_available_quantity(cls.pump, cls.stock, 5)

    def _repair(self, lines):
        repair = self.env["repair.order"].create(
            {
                "product_id": self.pickup.id,
                "lot_id": self.lot.id,
                "picking_type_id": self.warehouse.repair_type_id.id,
                "move_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.pump.id,
                            "product_uom_qty": 1.0,
                            "repair_line_type": line_type,
                            "asset_position_id": self.position.id,
                            "company_id": self.env.company.id,
                        },
                    )
                    for line_type in lines
                ],
            }
        )
        repair._action_repair_confirm()
        repair.action_repair_start()
        repair.action_repair_end()
        return repair

    def test_a_repair_on_an_asset_records_the_part_it_installs(self):
        repair = self._repair(["add", "remove"])

        self.assertEqual(repair.asset_id, self.lot.asset_id)
        part = repair.part_ids
        self.assertEqual(
            (part.state, part.position_id, part.product_id, part.source),
            ("installed", self.position, self.pump, "repair"),
        )
        self.assertTrue(part.removed_returned)
        self.assertEqual(part.asset_id, self.lot.asset_id)

    def test_repeating_the_repair_flags_the_replacement(self):
        self._repair(["add", "remove"])
        second = self._repair(["add", "remove"])

        self.assertEqual(second.part_ids.flag_ids.reason, "within_life")

    def test_a_repair_without_a_position_records_nothing(self):
        repair = self.env["repair.order"].create(
            {
                "product_id": self.pickup.id,
                "lot_id": self.lot.id,
                "picking_type_id": self.warehouse.repair_type_id.id,
                "move_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.pump.id,
                            "product_uom_qty": 1.0,
                            "repair_line_type": "add",
                            "company_id": self.env.company.id,
                        },
                    )
                ],
            }
        )
        repair._action_repair_confirm()
        repair.action_repair_start()
        repair.action_repair_end()

        self.assertFalse(repair.part_ids)
