from odoo.exceptions import ValidationError
from odoo.tests import tagged

from odoo.addons.stock.tests.common import TestStockCommon

# A stored computed field whose recompute legitimately disagrees with storage,
# with the reason it does. `test_no_stored_derivation_disagrees_with_its_own_
# compute` reads this, so a new exception is argued for here or not at all.
DELIBERATE_RECOMPUTE_DRIFT = {
    # the drift IS the feature: `is_outdated` and the inventory conflict wizard
    # detect a count taken against an on-hand that has since moved by comparing
    # `inventory_quantity - inventory_diff_quantity` with `quantity`. Adding
    # `quantity` to this field's depends would make every conflict invisible.
    ("stock.quant", "inventory_diff_quantity"),
}


@tagged("post_install", "-at_install")
class TestDerivedDefaults(TestStockCommon):
    """The stored fields this module derives rather than stores outright.

    Each one is a compute with `store=True, readonly=False`: the compute is a
    default, and the stored value is the truth once anything has set it. The
    two ways that contract breaks are a compute that assigns when it should
    have kept, and a depends that omits an input the compute reads.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.warehouse_1.write(
            {"reception_steps": "two_steps", "delivery_steps": "pick_pack_ship"}
        )
        cls.pick_type = cls.warehouse_1.pick_type_id
        cls.pack_type = cls.warehouse_1.pack_type_id
        cls.store_type = cls.warehouse_1.store_type_id
        cls.product = cls.env["product.product"].create(
            {"name": "Derived defaults probe", "is_storable": True}
        )

    def _force_recompute(self, records, field_name):
        """Run the field's own compute again over rows that already hold a value."""
        records.invalidate_recordset([field_name])
        records.env.add_to_compute(records._fields[field_name], records)
        records.flush_recordset([field_name])
        records.invalidate_recordset([field_name])

    def _recomputed(self, record, field_name):
        record.check_singleton()
        self._force_recompute(record, field_name)
        return record[field_name]

    # -- the compute is a default, not a definition -------------------------

    def test_a_no_op_code_write_keeps_a_multi_step_warehouse_intact(self):
        """The defect: `code` is the only trigger of the derivation, and the
        derivation used to assign unconditionally. Writing `code` -- even to
        the value it already holds -- reset Pack from (Packing Zone -> Output)
        to (Stock -> Stock), and did the same to every other type of the
        warehouse, silently undoing a multi-step configuration."""
        before = {
            picking_type: (
                picking_type.default_location_src_id,
                picking_type.default_location_dest_id,
            )
            for picking_type in (self.pick_type, self.pack_type, self.store_type)
        }
        self.assertNotEqual(
            self.pack_type.default_location_src_id,
            self.pack_type.default_location_dest_id,
            "the premise: Pack moves between two distinct locations",
        )

        for picking_type in before:
            picking_type.write({"code": picking_type.code})
        self.env.flush_all()

        for picking_type, (source, destination) in before.items():
            self.assertEqual(
                picking_type.default_location_src_id,
                source,
                f"{picking_type.name}: a no-op code write moved the source",
            )
            self.assertEqual(
                picking_type.default_location_dest_id,
                destination,
                f"{picking_type.name}: a no-op code write moved the destination",
            )

    def test_a_real_code_change_re_derives_only_what_the_new_code_contradicts(self):
        receipts = self.picking_type_in
        self.assertEqual(receipts.default_location_src_id.usage, "supplier")
        warehouse_destination = receipts.default_location_dest_id

        receipts.write({"code": "internal"})
        self.env.flush_all()

        self.assertNotEqual(
            receipts.default_location_src_id.usage,
            "supplier",
            "an internal type may not keep a vendor location as its source",
        )
        self.assertEqual(
            receipts.default_location_dest_id,
            warehouse_destination,
            "the destination did not contradict the new code, so it is kept",
        )

    def test_an_internal_type_turned_outgoing_re_derives_its_destination(self):
        self.assertEqual(self.pack_type.code, "internal")
        source = self.pack_type.default_location_src_id

        self.pack_type.write({"code": "outgoing"})
        self.env.flush_all()

        self.assertEqual(
            self.pack_type.default_location_dest_id.usage,
            "customer",
            "an outgoing type delivers to a customer location",
        )
        self.assertEqual(self.pack_type.default_location_src_id, source)

    # -- the depends names every input the compute reads --------------------

    def test_a_picking_state_follows_the_usage_of_its_source_location(self):
        """`_compute_state` asks `location_id.is_reservation_bypass_required()`,
        which reads `usage`. Declaring only `location_id` left a picking out of
        a location that had become a bypass one stuck in `confirmed`."""
        source = self.StockLocationObj.create(
            {
                "name": "Reclassified",
                "usage": "internal",
                "location_id": self.warehouse_1.view_location_id.id,
            }
        )
        picking = self.PickingObj.create(
            {
                "picking_type_id": self.picking_type_out.id,
                "location_id": source.id,
                "location_dest_id": self.customer_location.id,
                "move_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "product_uom_qty": 5,
                            "location_id": source.id,
                            "location_dest_id": self.customer_location.id,
                        },
                    )
                ],
            }
        )
        picking.action_confirm()
        self.env.flush_all()
        self.assertEqual(picking.state, "confirmed")

        source.usage = "customer"
        self.env.flush_all()

        self.assertEqual(
            picking.state,
            "assigned",
            "the stored state did not follow the location's usage",
        )
        self.assertEqual(picking.state, self._recomputed(picking, "state"))

    def test_a_picking_follows_its_operation_type_default_locations(self):
        picking = self.PickingObj.create({"picking_type_id": self.picking_type_int.id})
        self.env.flush_all()
        relocated = self.StockLocationObj.create(
            {"name": "Relocated", "location_id": self.stock_location.id}
        )

        self.picking_type_int.write(
            {
                "default_location_src_id": relocated.id,
                "default_location_dest_id": relocated.id,
            }
        )
        self.env.flush_all()

        self.assertEqual(picking.location_id, relocated)
        self.assertEqual(picking.location_dest_id, relocated)

    def test_a_done_picking_does_not_follow_its_operation_type(self):
        picking = self.PickingObj.create(
            {
                "picking_type_id": self.picking_type_in.id,
                "move_ids": [
                    (0, 0, {"product_id": self.product.id, "product_uom_qty": 1})
                ],
            }
        )
        picking.action_confirm()
        picking.move_ids.picked = True
        picking.button_validate()
        self.env.flush_all()
        frozen = picking.location_dest_id
        self.assertEqual(picking.state, "done")

        relocated = self.StockLocationObj.create(
            {"name": "Too late", "location_id": self.stock_location.id}
        )
        self.picking_type_in.default_location_dest_id = relocated
        self.env.flush_all()

        self.assertEqual(
            picking.location_dest_id,
            frozen,
            "a validated transfer records where the goods went, not a default",
        )

    def test_a_move_follows_its_operation_type_destination(self):
        move = self.MoveObj.create(
            {
                "product_id": self.product.id,
                "product_uom_qty": 1,
                "picking_type_id": self.picking_type_int.id,
            }
        )
        self.env.flush_all()
        relocated = self.StockLocationObj.create(
            {"name": "Move dest", "location_id": self.stock_location.id}
        )

        self.picking_type_int.default_location_dest_id = relocated
        self.env.flush_all()

        self.assertEqual(move.location_dest_id, relocated)

    def test_a_scrap_follows_the_state_of_the_transfer_it_hangs_off(self):
        """A draft scrap on an in-progress receipt takes the receipt's source.
        Once the receipt is validated the goods are at its destination, and
        scrapping from the vendor location would drive that location negative."""
        receipt = self.PickingObj.create(
            {
                "picking_type_id": self.picking_type_in.id,
                "move_ids": [
                    (0, 0, {"product_id": self.product.id, "product_uom_qty": 2})
                ],
            }
        )
        receipt.action_confirm()
        scrap = self.env["stock.scrap"].create(
            {
                "product_id": self.product.id,
                "product_uom_id": self.product.uom_id.id,
                "scrap_qty": 1,
                "picking_id": receipt.id,
            }
        )
        self.env.flush_all()
        self.assertEqual(scrap.location_id, receipt.location_id)

        receipt.move_ids.picked = True
        receipt.button_validate()
        self.env.flush_all()

        self.assertEqual(
            scrap.location_id,
            receipt.location_dest_id,
            "the scrap still points at where the goods were before the receipt",
        )

    # -- a copied move still derives coherent locations ---------------------

    def test_a_copied_move_without_an_explicit_type_derives_its_locations(self):
        """`picking_type_id` is precomputed so that the precomputed location
        fields can declare it. A copy whose vals carry no operation type must
        still land on the same locations as its original."""
        move = self.MoveObj.create(
            {
                "product_id": self.product.id,
                "product_uom_qty": 4,
                "picking_type_id": self.pick_type.id,
            }
        )
        self.env.flush_all()

        vals = move.copy_data()[0]
        self.assertIn("picking_type_id", vals)
        vals.pop("location_id", None)
        vals.pop("location_dest_id", None)
        copied = self.MoveObj.create(vals)
        self.env.flush_all()

        self.assertEqual(copied.picking_type_id, move.picking_type_id)
        self.assertEqual(copied.location_id, move.location_id)
        self.assertEqual(copied.location_dest_id, move.location_dest_id)

    # -- the general guard --------------------------------------------------

    def test_no_stored_derivation_disagrees_with_its_own_compute(self):
        """The guard that would have caught the picking-type clobber.

        A stored compute that, run again over an untouched row, produces a
        different value is a clobber waiting for its trigger: the value is
        right today only because nothing has recomputed it yet.
        """
        drifted = []
        for model_name in (
            "stock.picking.type",
            "stock.picking",
            "stock.move",
            "stock.move.line",
            "stock.quant",
            "stock.warehouse",
            "stock.location",
        ):
            model = self.env[model_name]
            records = model.with_context(active_test=False).search([])
            if not records:
                continue
            for field in model._fields.values():
                if not (field.compute and field.store) or field.related:
                    continue
                if (model_name, field.name) in DELIBERATE_RECOMPUTE_DRIFT:
                    continue
                before = {record.id: record[field.name] for record in records}
                try:
                    self._force_recompute(records, field.name)
                except Exception as error:
                    self.env.invalidate_all()
                    drifted.append(
                        f"{model_name}.{field.name}: recompute raised {error!r}"
                    )
                    continue
                for record in records:
                    if before[record.id] != record[field.name]:
                        drifted.append(
                            f"{model_name}.{field.name} id={record.id}: "
                            f"{before[record.id]!r} -> {record[field.name]!r}"
                        )
                        break
        self.assertEqual(drifted, [], "stored values a recompute would overwrite")


@tagged("post_install", "-at_install")
class TestConstraintTriggers(TestStockCommon):
    """Each of these refuses one invalid state through one write path.

    A constraint declares the fields that re-run it, and every one of these
    reads a field it did not declare -- so the same invalid pair was refused
    when written from one side and accepted when written from the other.

    `stock.warehouse._check_sub_locations_are_inside_the_warehouse` has the
    same gap and is deliberately NOT closed here: it refuses
    `warehouse.lot_stock_id = <outside the view>` but accepts the same state
    reached by `warehouse.view_location_id = <a foreign subtree>`, and
    `write` does not repoint the sub-locations after such a write.
    `test_a_warehouse_adopting_a_view_repoints_the_whole_subtree` and
    `test_repointing_a_warehouse_view_repoints_the_whole_subtree` pin that as
    supported. Whether a warehouse may have its stock location outside its own
    view is a decision about the model, not a missing trigger.
    """

    def _assert_refused(self, message, write):
        with self.assertRaises(ValidationError, msg=message):
            write()
            self.env.flush_all()

    def test_a_rule_cannot_join_a_route_of_another_company(self):
        other = self.env["res.company"].create({"name": "Rule trigger co"})
        warehouse = self.warehouse_1
        own_route, foreign_route = self.env["stock.route"].create(
            [
                {"name": "Own", "company_id": warehouse.company_id.id},
                {"name": "Foreign", "company_id": other.id},
            ]
        )
        rule = self.env["stock.rule"].create(
            {
                "name": "Trigger rule",
                "route_id": own_route.id,
                "company_id": warehouse.company_id.id,
                "action": "pull",
                "picking_type_id": warehouse.int_type_id.id,
                "location_src_id": warehouse.lot_stock_id.id,
                "location_dest_id": warehouse.lot_stock_id.id,
            }
        )
        self.env.flush_all()

        self._assert_refused(
            "moving the rule to a foreign route was accepted",
            lambda: rule.write({"route_id": foreign_route.id}),
        )

    def test_a_route_cannot_adopt_a_rule_of_another_company(self):
        other = self.env["res.company"].create({"name": "Route trigger co"})
        warehouse = self.warehouse_1
        own_route, foreign_route = self.env["stock.route"].create(
            [
                {"name": "Own r", "company_id": warehouse.company_id.id},
                {"name": "Foreign r", "company_id": other.id},
            ]
        )
        rule = self.env["stock.rule"].create(
            {
                "name": "Adopted rule",
                "route_id": own_route.id,
                "company_id": warehouse.company_id.id,
                "action": "pull",
                "picking_type_id": warehouse.int_type_id.id,
                "location_src_id": warehouse.lot_stock_id.id,
                "location_dest_id": warehouse.lot_stock_id.id,
            }
        )
        self.env.flush_all()

        self._assert_refused(
            "adopting a foreign rule from the route side was accepted",
            lambda: foreign_route.write({"rule_ids": [(4, rule.id)]}),
        )

    def test_a_quant_cannot_be_re_producted_away_from_its_lot(self):
        tracked, other = self.env["product.product"].create(
            [
                {"name": "Lot owner", "is_storable": True, "tracking": "lot"},
                {"name": "Lot stranger", "is_storable": True, "tracking": "lot"},
            ]
        )
        lot = self.LotObj.create({"name": "TRIGGER-LOT", "product_id": tracked.id})
        self.StockQuantObj._update_available_quantity(
            tracked, self.stock_location, 3, lot_id=lot
        )
        self.env.flush_all()
        quant = self.StockQuantObj.search([("lot_id", "=", lot.id)], limit=1)
        self.assertTrue(quant)

        self._assert_refused(
            "the product moved out from under the lot",
            lambda: quant.write({"product_id": other.id}),
        )
