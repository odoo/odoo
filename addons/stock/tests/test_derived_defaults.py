from odoo.exceptions import ValidationError
from odoo.tests import tagged

from odoo.addons.stock.tests.common import TestStockCommon

# Stored computed fields whose recompute disagrees with storage, each with the
# reason it is allowed to. `test_no_stored_derivation_disagrees_with_its_own_
# compute` reads this, so a new entry is argued for here or not at all -- and
# the two below are NOT the same kind of thing.
RECOMPUTE_DRIFT_ALLOWED = {
    # BY DESIGN. The drift IS the feature: `is_outdated` and the inventory
    # conflict wizard detect a count taken against an on-hand that has since
    # moved, by comparing `inventory_quantity - inventory_diff_quantity` with
    # `quantity`. Adding `quantity` to this field's depends would make every
    # conflict invisible.
    ("stock.quant", "inventory_diff_quantity"): "conflict detection depends on it",
    # KNOWN HAZARD, not a feature and not yet decided. The compute is
    # `self.inventory_quantity_set = True` with no condition, so it is a
    # mark-on-write hook wearing a compute's clothes: any recompute sets it on
    # every quant, including those `action_clear_inventory_quantity` has just
    # cleared. Measured: a never-counted quant of 100 flips to set=True and
    # `is_outdated` True, which routes `action_apply_inventory` to the conflict
    # wizard for every quant in the database. `inventory_diff_quantity` does
    # NOT follow in the same pass -- measured 0.0, so no stock moves -- which
    # is the only reason this is an annoyance rather than a data defect.
    ("stock.quant", "inventory_quantity_set"): "unconditional compute, upstream shape",
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

    def test_a_scrap_follows_the_locations_of_the_transfer_it_hangs_off(self):
        """What the scrap's location does follow, and what it does not.

        `_compute_location_id` reads `picking_id.state` to choose between the
        transfer's source and its destination, and that read is deliberately
        NOT declared -- declaring it made every write of a picking's state
        search `stock.scrap` for dependents, which cost 3.67 queries per move
        in `mrp`'s kit explosion against a guard of 1.0. So a scrap saved
        against an in-progress transfer keeps the source it was given even
        after that transfer is validated, and the two location dependencies
        that are free are the ones declared. If that staleness is ever worth
        curing, it wants resolving where the scrap is processed rather than a
        trigger on a hot path -- and `location_id` is user-editable, so such a
        cure must not clobber a location the user chose.
        """
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

        moved = self.StockLocationObj.create(
            {"name": "Scrap follows me", "location_id": self.stock_location.id}
        )
        receipt.location_id = moved
        self.env.flush_all()

        self.assertEqual(
            scrap.location_id,
            moved,
            "the scrap did not follow the transfer's source location",
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

    def _build_sweep_fixture(self):
        """Rows for the models the sweep would otherwise not reach.

        Measured before this existed: on a fresh install `stock.picking`,
        `stock.move`, `stock.move.line` and `stock.quant` hold **no rows**, so
        33 of the 44 stored computes in the sweep's models were examined over
        an empty recordset and the test passed by having nothing to look at.
        """
        product = self.env["product.product"].create(
            {"name": "Sweep tracked", "is_storable": True, "tracking": "lot"}
        )
        plain = self.env["product.product"].create(
            {"name": "Sweep plain", "is_storable": True}
        )
        lot = self.LotObj.create({"name": "SWEEP-LOT", "product_id": product.id})
        self.StockQuantObj._update_available_quantity(
            product, self.stock_location, 12, lot_id=lot
        )
        self.StockQuantObj._update_available_quantity(plain, self.stock_location, 7)
        outgoing = self.PickingObj.create(
            {
                "picking_type_id": self.picking_type_out.id,
                "move_ids": [
                    (0, 0, {"product_id": product.id, "product_uom_qty": 3}),
                    (0, 0, {"product_id": plain.id, "product_uom_qty": 2}),
                ],
            }
        )
        outgoing.action_confirm()
        outgoing.action_assign()
        incoming = self.PickingObj.create(
            {
                "picking_type_id": self.picking_type_in.id,
                "move_ids": [(0, 0, {"product_id": plain.id, "product_uom_qty": 5})],
            }
        )
        incoming.action_confirm()
        self.env["stock.scrap"].create(
            {
                "product_id": plain.id,
                "product_uom_id": plain.uom_id.id,
                "scrap_qty": 1,
                "picking_id": incoming.id,
            }
        )
        self.env.flush_all()

    def test_no_stored_derivation_disagrees_with_its_own_compute(self):
        """The guard that would have caught the picking-type clobber.

        A stored compute that, run again over an untouched row, produces a
        different value is a clobber waiting for its trigger: the value is
        right today only because nothing has recomputed it yet.
        """
        self._build_sweep_fixture()
        drifted = []
        coverage = []
        checks = 0
        for model_name in (
            "stock.picking.type",
            "stock.picking",
            "stock.move",
            "stock.move.line",
            "stock.quant",
            "stock.scrap",
            "stock.warehouse",
            "stock.location",
        ):
            model = self.env[model_name]
            records = model.with_context(active_test=False).search([])
            swept = 0
            for field in model._fields.values():
                if not (field.compute and field.store) or field.related:
                    continue
                if (model_name, field.name) in RECOMPUTE_DRIFT_ALLOWED:
                    continue
                swept += 1
                if not records:
                    continue
                checks += len(records)
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
            coverage.append(f"{model_name}={len(records)}rows*{swept}fields")
            self.assertTrue(
                records,
                f"{model_name} has no rows, so its {swept} stored computes are "
                "examined over nothing -- the fixture must reach every model "
                "this sweep claims to cover",
            )
        self.assertEqual(drifted, [], "stored values a recompute would overwrite")
        # A sweep that stops finding rows stops being a check and says so only
        # by passing faster. Before `_build_sweep_fixture` existed this read
        # 108 comparisons over 2 of the 8 models; it now reads 270 over all 8.
        # The floor sits between the two so a collapse back to incidental
        # install data fails rather than passes.
        self.assertGreater(checks, 200, f"sweep coverage collapsed: {coverage}")


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


@tagged("post_install", "-at_install")
class TestCategoryRouteInheritance(TestStockCommon):
    """`product.category.total_route_ids`, which decides a product's routes.

    It is read through `product.template.route_from_categ_ids` on the product
    form and by route resolution in `stock_rule_selection`, `stock_orderpoint`,
    `stock_replenishment_report`, `sale_stock` and `stock_dropshipping`.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.route_sel, cls.route_other = cls.env["stock.route"].create(
            [
                {"name": "Categ inherit", "product_categ_selectable": True},
                {"name": "Categ other", "product_categ_selectable": True},
            ]
        )
        Categ = cls.env["product.category"]
        cls.categ_root = Categ.create(
            {"name": "Inherit root", "route_ids": [(6, 0, cls.route_sel.ids)]}
        )
        cls.categ_child = Categ.create(
            {"name": "Inherit child", "parent_id": cls.categ_root.id}
        )
        cls.categ_deep = Categ.create(
            {"name": "Inherit deep", "parent_id": cls.categ_child.id}
        )

    def test_a_batch_read_inherits_the_same_routes_as_a_single_one(self):
        """The regression this pins cost every descendant its ancestors' routes.

        Computing `parent_route_ids` by reading `parent_id.total_route_ids` is
        right one record at a time and wrong for a recordset: the parent's
        total is still being computed, the in-progress value is empty, and the
        descendants come back bare. `mapped()` is how route resolution reads
        this, so the batch path is the one that matters.
        """
        chain = self.categ_root | self.categ_child | self.categ_deep
        single = []
        for category in chain:
            self.env.invalidate_all()
            single.append(category.total_route_ids)

        self.env.invalidate_all()
        self.env["product.category"].search([]).mapped("total_route_ids")
        batched = [category.total_route_ids for category in chain]

        self.assertEqual(
            batched,
            single,
            "a batch read of total_route_ids disagrees with a single-record one",
        )
        for category in chain:
            self.assertIn(
                self.route_sel,
                category.total_route_ids,
                f"{category.name} lost the route its ancestor carries",
            )

    def test_the_search_does_not_re_enter_its_own_domain(self):
        """`filtered_domain` on this leaf routes back through the field's own
        `search=`. It used to, and every search raised `Domain nesting too deep
        to optimize` -- reachable from a custom filter on the product form's
        `route_from_categ_ids`."""
        found = self.env["product.category"].search(
            [("total_route_ids", "in", self.route_sel.ids)]
        )
        self.assertEqual(
            found & (self.categ_root | self.categ_child | self.categ_deep),
            self.categ_root | self.categ_child | self.categ_deep,
            "the search missed a descendant that inherits the route",
        )
        self.assertFalse(
            self.env["product.category"].search(
                [("total_route_ids", "in", self.route_other.ids)]
            )
            & self.categ_root,
        )

    def test_the_search_agrees_with_reading_the_field(self):
        Categ = self.env["product.category"]
        for operator in ("in", "not in"):
            for value in (self.route_sel.ids, self.route_other.ids, []):
                with self.subTest(operator=operator, value=value):
                    by_search = Categ.search([("total_route_ids", operator, value)])
                    wanted = set(value)
                    hit = Categ.browse(
                        [
                            category.id
                            for category in Categ.search([])
                            if wanted & set(category.total_route_ids.ids)
                        ]
                    )
                    expected = hit if operator == "in" else Categ.search([]) - hit
                    self.assertEqual(by_search, expected)

    def test_a_link_the_fields_domain_hides_stays_hidden(self):
        """`route_ids` carries `domain=[("product_categ_selectable", "=", True)]`
        and a relational field's domain is applied on READ, so a row in the
        relation table pointing at a non-selectable route is invisible to the
        field. The search bounds its candidates with that table, which
        over-approximates; the read must still decide."""
        hidden = self.env["stock.route"].create(
            {"name": "Categ hidden", "product_categ_selectable": False}
        )
        owner = self.env["product.category"].create({"name": "Inherit hidden"})
        self.env.cr.execute(
            "INSERT INTO stock_route_categ (categ_id, route_id) VALUES (%s, %s)",
            (owner.id, hidden.id),
        )
        self.env.invalidate_all()

        self.assertNotIn(hidden, owner.total_route_ids)
        self.assertNotIn(
            owner,
            self.env["product.category"].search(
                [("total_route_ids", "in", hidden.ids)]
            ),
            "the search returned a link the field's own domain hides",
        )
