from odoo.exceptions import UserError, ValidationError
from odoo.tests import TransactionCase, tagged

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


@tagged("post_install", "-at_install")
class TestLotCompanyIsNotDecidedByTheReader(TestStockCommon):
    """`stock.lot.company_id` is stored and its compute reads `self.env`.

    That makes the stored value a function of who last recomputed it, and
    `company_id` drives record-rule visibility and `check_company` on the lot's
    quants and move lines.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Company = cls.env["res.company"]
        cls.parent_co = Company.create({"name": "Lot parent co"})
        cls.child_co = Company.create(
            {"name": "Lot child co", "parent_id": cls.parent_co.id}
        )
        cls.unrelated_co = Company.create({"name": "Lot unrelated co"})
        cls.owned = (
            cls.env["product.product"]
            .with_company(cls.parent_co)
            .create(
                {
                    "name": "Lot owned product",
                    "is_storable": True,
                    "tracking": "lot",
                    "company_id": cls.parent_co.id,
                }
            )
        )

    def _as_child(self, model):
        return model.with_company(self.child_co).with_context(
            allowed_company_ids=[self.child_co.id]
        )

    def _recompute_as(self, lot, companies):
        scoped = lot.with_company(companies[0]).with_context(
            allowed_company_ids=[company.id for company in companies]
        )
        scoped.invalidate_recordset(["company_id"])
        self.env.add_to_compute(scoped._fields["company_id"], scoped)
        scoped.flush_recordset(["company_id"])
        scoped.invalidate_recordset(["company_id"])

    def test_a_lot_does_not_move_company_because_someone_else_recomputed_it(self):
        lot = self._as_child(self.LotObj).create(
            {"name": "LOT-WHO", "product_id": self.owned.id}
        )
        self.env.flush_all()
        self.assertEqual(
            lot.company_id,
            self.child_co,
            "the premise: a child-only user places the lot in the child company",
        )

        self._recompute_as(lot, [self.parent_co, self.child_co])

        self.assertEqual(
            lot.company_id,
            self.child_co,
            "a recompute by a user allowed in one more company moved the lot",
        )

    def test_a_lot_still_follows_its_product_to_an_unrelated_company(self):
        lot = self._as_child(self.LotObj).create(
            {"name": "LOT-MOVE", "product_id": self.owned.id}
        )
        self.env.flush_all()
        self.assertEqual(lot.company_id, self.child_co)

        self.owned.company_id = self.unrelated_co
        self.env.flush_all()

        self.assertEqual(
            lot.company_id,
            self.unrelated_co,
            "the kept value must not survive its product leaving the tree",
        )

    def test_clearing_a_products_company_still_clears_its_lots(self):
        lot = self.LotObj.create({"name": "LOT-CLEAR", "product_id": self.owned.id})
        self.env.flush_all()

        self.owned.company_id = False
        self.env.flush_all()

        self.assertFalse(
            lot.company_id, "a shared product's lot is no longer company-bound"
        )


@tagged("post_install", "-at_install")
class TestEditableDefaultsSurviveANoOpTrigger(TestStockCommon):
    """`store=True, readonly=False, precompute=True` is an editable default.

    `modified()` fires on the key a write carries, not on a change, so a
    compute that assigns unconditionally resets whatever the user chose on any
    write that merely mentions its trigger.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product = cls.env["product.product"].create(
            {"name": "Editable default probe", "is_storable": True}
        )

    def test_a_shipping_policy_survives_a_no_op_operation_type_write(self):
        picking = self.PickingObj.create(
            {
                "picking_type_id": self.picking_type_out.id,
                "move_ids": [
                    (0, 0, {"product_id": self.product.id, "product_uom_qty": 1})
                ],
            }
        )
        self.env.flush_all()
        picking.move_type = "one" if picking.move_type == "direct" else "direct"
        self.env.flush_all()
        chosen = picking.move_type

        picking.write({"picking_type_id": picking.picking_type_id.id})
        self.env.flush_all()

        self.assertEqual(
            picking.move_type,
            chosen,
            "a write of the operation type it already had reset the policy",
        )

    def test_a_new_picking_still_takes_the_policy_from_its_type(self):
        self.picking_type_out.move_type = "one"
        picking = self.PickingObj.create({"picking_type_id": self.picking_type_out.id})
        self.env.flush_all()
        self.assertEqual(picking.move_type, "one", "the default must still be derived")

    def test_a_reordering_rule_keeps_the_shelf_it_was_pointed_at(self):
        orderpoint = self.env["stock.warehouse.orderpoint"].create(
            {"product_id": self.product.id, "warehouse_id": self.warehouse_1.id}
        )
        self.env.flush_all()
        shelf = self.StockLocationObj.create(
            {"name": "Reorder shelf", "location_id": self.stock_location.id}
        )
        orderpoint.location_id = shelf
        self.env.flush_all()

        orderpoint.write({"warehouse_id": self.warehouse_1.id})
        self.env.flush_all()

        self.assertEqual(
            orderpoint.location_id,
            shelf,
            "a write of the warehouse it already had reset the location",
        )

    def test_a_real_warehouse_change_still_moves_the_rule(self):
        """The guard keeps a location that is still inside the warehouse. One
        that is not is exactly what a genuine warehouse change invalidates."""
        other = self.env["stock.warehouse"].create(
            {"name": "Reorder other WH", "code": "ROW"}
        )
        orderpoint = self.env["stock.warehouse.orderpoint"].create(
            {"product_id": self.product.id, "warehouse_id": self.warehouse_1.id}
        )
        self.env.flush_all()
        self.assertEqual(orderpoint.location_id, self.warehouse_1.lot_stock_id)

        orderpoint.warehouse_id = other
        self.env.flush_all()

        self.assertEqual(
            orderpoint.location_id,
            other.lot_stock_id,
            "the rule kept a location belonging to the previous warehouse",
        )


@tagged("post_install", "-at_install")
class TestARerateDoesNotRewriteHistory(TestStockCommon):
    """`product_uom_id.factor` is read by `_compute_product_qty` and must NOT
    be declared. The pin exists because a detector will flag the omission as a
    missing dependency, and adding it is the defect."""

    def test_a_done_move_keeps_the_quantity_it_recorded(self):
        unit = self.env.ref("uom.product_uom_unit")
        box = self.env["uom.uom"].create(
            {"name": "Rerate box", "relative_factor": 10, "relative_uom_id": unit.id}
        )
        product = self.env["product.product"].create(
            {"name": "Rerate product", "is_storable": True, "uom_id": unit.id}
        )
        self.StockQuantObj._update_available_quantity(
            product, self.stock_location, 1000
        )
        picking = self.PickingObj.create(
            {
                "picking_type_id": self.picking_type_out.id,
                "move_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": product.id,
                            "product_uom_id": box.id,
                            "product_uom_qty": 2,
                        },
                    )
                ],
            }
        )
        picking.action_confirm()
        picking.action_assign()
        picking.move_ids.picked = True
        picking.button_validate()
        self.env.flush_all()
        move = picking.move_ids
        self.assertEqual(move.state, "done")
        self.assertEqual(move.product_qty, 20.0, "2 boxes of 10 units")

        # allowed precisely because every move on this unit is done --
        # `uom.uom.write` refuses a ratio change only while moves are open
        box.relative_factor = 20
        self.env.flush_all()
        self.env.invalidate_all()

        self.assertEqual(
            move.product_qty,
            20.0,
            "a re-rated unit restated what a done move had already recorded",
        )

    def test_the_guard_still_refuses_a_rerate_while_a_move_is_open(self):
        unit = self.env.ref("uom.product_uom_unit")
        box = self.env["uom.uom"].create(
            {
                "name": "Rerate open box",
                "relative_factor": 10,
                "relative_uom_id": unit.id,
            }
        )
        product = self.env["product.product"].create(
            {"name": "Rerate open product", "is_storable": True, "uom_id": unit.id}
        )
        self.MoveObj.create(
            {
                "product_id": product.id,
                "product_uom_id": box.id,
                "product_uom_qty": 2,
                "picking_type_id": self.picking_type_int.id,
            }
        )._action_confirm()
        self.env.flush_all()

        with self.assertRaises(UserError):
            box.relative_factor = 20


@tagged("post_install", "-at_install")
class TestBatchIsCompanyScoped(TransactionCase):
    """`stock.picking.batch` carries a required `company_id` and was the only
    company-scoped model in this module with no record rule -- the rule was
    left behind when the model moved in from `stock_picking_batch`.
    """

    def test_a_user_of_one_company_cannot_see_anothers_batches(self):
        env = self.env
        co_a, co_b = env["res.company"].create(
            [{"name": "Batch scope A"}, {"name": "Batch scope B"}]
        )
        env.flush_all()
        wh_a = env["stock.warehouse"].search([("company_id", "=", co_a.id)], limit=1)
        wh_b = env["stock.warehouse"].search([("company_id", "=", co_b.id)], limit=1)
        batch_a, batch_b = env["stock.picking.batch"].create(
            [
                {
                    "name": "SCOPE-A",
                    "company_id": co_a.id,
                    "picking_type_id": wh_a.out_type_id.id,
                },
                {
                    "name": "SCOPE-B",
                    "company_id": co_b.id,
                    "picking_type_id": wh_b.out_type_id.id,
                },
            ]
        )
        picking_a = env["stock.picking"].create(
            {"picking_type_id": wh_a.out_type_id.id}
        )
        picking_b = env["stock.picking"].create(
            {"picking_type_id": wh_b.out_type_id.id}
        )
        user_a = env["res.users"].create(
            {
                "name": "Batch scope user",
                "login": "batch_scope_user",
                "company_id": co_a.id,
                "company_ids": [(6, 0, [co_a.id])],
                "group_ids": [(4, env.ref("stock.group_stock_user").id)],
            }
        )
        env.flush_all()
        # a read that answers from the superuser's cache never reaches a rule,
        # so the cache is dropped and the check is a search
        env.invalidate_all()

        def visible(model, records):
            return (
                env[model]
                .with_user(user_a)
                .with_context(allowed_company_ids=[co_a.id])
                .search([("id", "in", records.ids)])
            )

        seen_pickings = visible("stock.picking", picking_a + picking_b)
        self.assertIn(picking_a, seen_pickings, "the control must see its own")
        self.assertNotIn(
            picking_b,
            seen_pickings,
            "the control is broken: stock.picking's own rule did not filter",
        )

        seen_batches = visible("stock.picking.batch", batch_a + batch_b)
        self.assertIn(batch_a, seen_batches)
        self.assertNotIn(
            batch_b,
            seen_batches,
            "a user of one company can search another company's batch transfers",
        )


@tagged("post_install", "-at_install")
class TestGatherPathsAgree(TestStockCommon):
    """`_gather` answers from `quants_cache` when it covers the request and
    searches otherwise. Two implementations of one question, and reservation
    correctness rests on them agreeing.
    """

    def test_the_cached_and_searched_paths_return_the_same_quants(self):
        Quant = self.StockQuantObj
        stock = self.stock_location
        shelf_a, shelf_b = self.StockLocationObj.create(
            [
                {"name": "Gather shelf A", "location_id": stock.id},
                {"name": "Gather shelf B", "location_id": stock.id},
            ]
        )
        tracked, plain = self.env["product.product"].create(
            [
                {"name": "Gather tracked", "is_storable": True, "tracking": "lot"},
                {"name": "Gather plain", "is_storable": True},
            ]
        )
        lot_1, lot_2 = self.LotObj.create(
            [
                {"name": "GATHER-1", "product_id": tracked.id},
                {"name": "GATHER-2", "product_id": tracked.id},
            ]
        )
        owner = self.env["res.partner"].create({"name": "Gather owner"})
        package = self.env["stock.package"].create({})
        Quant._update_available_quantity(tracked, shelf_a, 5, lot_id=lot_1)
        Quant._update_available_quantity(tracked, shelf_a, 3, lot_id=lot_2)
        Quant._update_available_quantity(tracked, shelf_b, 7, lot_id=lot_1)
        Quant._update_available_quantity(plain, shelf_a, 11)
        Quant._update_available_quantity(plain, shelf_b, 13, package_id=package)
        Quant._update_available_quantity(plain, stock, 17, owner_id=owner)
        self.env.flush_all()

        cache = Quant._get_quants_by_products_locations(
            tracked + plain, stock + shelf_a + shelf_b
        )

        combinations = covered = 0
        for product in (tracked, plain):
            for location in (stock, shelf_a, shelf_b):
                for lot in (None, lot_1, lot_2):
                    for pack in (None, package):
                        for holder in (None, owner):
                            for strict in (False, True):
                                combinations += 1
                                # the necessary condition for the cache path;
                                # without it both sides would search and the
                                # comparison below would compare nothing
                                if cache.is_covering(product, location, lot):
                                    covered += 1
                                self.env.invalidate_all()
                                searched = Quant._gather(
                                    product,
                                    location,
                                    lot_id=lot,
                                    package_id=pack,
                                    owner_id=holder,
                                    strict=strict,
                                )
                                cached = Quant.with_context(quants_cache=cache)._gather(
                                    product,
                                    location,
                                    lot_id=lot,
                                    package_id=pack,
                                    owner_id=holder,
                                    strict=strict,
                                )
                                self.assertEqual(
                                    set(cached.ids),
                                    set(searched.ids),
                                    f"product={product.name} location={location.name} "
                                    f"lot={lot and lot.name} package={bool(pack)} "
                                    f"owner={bool(holder)} strict={strict}",
                                )
        self.assertEqual(
            covered,
            combinations,
            "the cache did not cover every request, so some comparisons ran "
            "search against search and proved nothing",
        )
        self.assertGreaterEqual(combinations, 144)


@tagged("post_install", "-at_install")
class TestANoOpWriteOfQuantityMovesNoStock(TransactionCase):
    """`stock.move.quantity` is stored at 'Product Unit' precision and derived
    from move lines that are not. `_inverse_quantity` subtracts the second from
    the first, so the storage rounding used to read as a deliberate increase."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.unit = cls.env.ref("uom.product_uom_unit")
        # one unit is 0.125 of this, exactly representable in binary, so the
        # gap to the stored value is exactly half an ulp -- the one case
        # HALF-UP rounding sends away from zero
        cls.eighth = cls.env["uom.uom"].create(
            {
                "name": "Eighth of a unit",
                "relative_factor": 8,
                "relative_uom_id": cls.unit.id,
            }
        )
        cls.warehouse = cls.env["stock.warehouse"].search([], limit=1)
        cls.product = cls.env["product.product"].create(
            {"name": "Rounded move", "is_storable": True, "uom_id": cls.unit.id}
        )
        cls.env["stock.quant"]._update_available_quantity(
            cls.product, cls.warehouse.lot_stock_id, 1000
        )

    def _move_of_one_unit_measured_in_eighths(self):
        move = self.env["stock.move"].create(
            {
                "product_id": self.product.id,
                "product_uom_id": self.eighth.id,
                "product_uom_qty": 1,
                "picking_type_id": self.warehouse.out_type_id.id,
                "location_id": self.warehouse.lot_stock_id.id,
                "location_dest_id": self.env.ref("stock.stock_location_customers").id,
            }
        )
        move._action_confirm()
        move.move_line_ids.unlink()
        self.env["stock.move.line"].create(
            {
                "move_id": move.id,
                "product_id": self.product.id,
                "product_uom_id": self.unit.id,
                "quantity": 1.0,
                "location_id": self.warehouse.lot_stock_id.id,
                "location_dest_id": self.env.ref("stock.stock_location_customers").id,
            }
        )
        self.env.flush_all()
        move.invalidate_recordset(["quantity"])
        return move

    def test_the_fixture_still_sits_on_the_rounding_boundary(self):
        """Without this the test below passes for the wrong reason: a fixture
        whose sum happens to be exact would compare equal either way."""
        move = self._move_of_one_unit_measured_in_eighths()
        unrounded = sum(
            line.product_uom_id._get_quantity_in_unit(
                line.quantity, move.product_uom_id, round=False
            )
            for line in move.move_line_ids
        )
        self.assertEqual(unrounded, 0.125)
        self.assertEqual(move.quantity, 0.13)
        self.assertEqual(
            move.product_uom_id.compare(move.quantity - unrounded, 0),
            1,
            "the unrounded gap must still round away from zero, or the "
            "regression below is no longer being exercised",
        )

    def test_writing_the_displayed_quantity_back_changes_nothing(self):
        move = self._move_of_one_unit_measured_in_eighths()
        before = [(line.id, line.quantity) for line in move.move_line_ids]

        move.quantity = move.quantity
        self.env.flush_all()
        move.invalidate_recordset()

        self.assertEqual(
            [(line.id, line.quantity) for line in move.move_line_ids],
            before,
            "a no-op write of quantity must not move stock",
        )

    def test_a_real_increase_still_reaches_the_move_lines(self):
        """The rounding must not be bought by making the inverse inert."""
        move = self._move_of_one_unit_measured_in_eighths()
        move.quantity = 1.0
        self.env.flush_all()
        move.invalidate_recordset()
        self.assertEqual(move.quantity, 1.0)
        self.assertAlmostEqual(move._get_move_line_quantity(), 1.0, places=2)


@tagged("post_install", "-at_install")
class TestApplyingACountLandsOnIt(TransactionCase):
    """`stock.quant.quantity` is stored at full precision, while
    `inventory_diff_quantity` and the `stock.move` carrying it are stored at
    display precision. A quant with more decimals than the display can show
    therefore cannot be counted onto an exact figure."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.warehouse = cls.env["stock.warehouse"].search([], limit=1)
        cls.unit = cls.env.ref("uom.product_uom_unit")

    def _count_and_apply(self, on_hand, counted, name):
        product = self.env["product.product"].create(
            {"name": name, "is_storable": True, "uom_id": self.unit.id}
        )
        self.env["stock.quant"]._update_available_quantity(
            product, self.warehouse.lot_stock_id, on_hand
        )
        self.env.flush_all()
        quant = self.env["stock.quant"].search(
            [
                ("product_id", "=", product.id),
                ("location_id", "=", self.warehouse.lot_stock_id.id),
            ]
        )
        quant.invalidate_recordset()
        quant.with_context(inventory_mode=True).inventory_quantity = counted
        self.env.flush_all()
        quant.with_context(inventory_mode=True)._apply_inventory()
        self.env.flush_all()
        quant.invalidate_recordset()
        return quant

    def test_a_count_lands_exactly_when_the_gap_is_representable(self):
        quant = self._count_and_apply(10.25, 11.0, "Countable")
        self.assertEqual(quant.quantity, 11.0)

    def test_a_count_that_cannot_land_says_so_on_the_logic_channel(self):
        """The first assertion records an OPEN DECISION, not a desired outcome:
        an ordinary receipt of 1 unit of a product stocked in dozens makes a
        quant of 0.0833..., and no adjustment can count it onto a round figure
        while moves carry display precision. Until that is decided, the only
        defensible position is that the drift must not be silent."""
        with self.assertLogs("odoo.addons.stock.debug.logic", "DEBUG") as captured:
            quant = self._count_and_apply(31.0 / 3.0, 11.0, "Uncountable")
        self.assertNotEqual(quant.quantity, 11.0)
        self.assertTrue(
            any("_apply_inventory: counted" in line for line in captured.output),
            "a count that will not land must be reported, and the guard for it "
            "cannot use compare(): the gap is under half an ulp by construction",
        )


@tagged("post_install", "-at_install")
class TestSplittingAMoveCannotAlwaysConserve(TransactionCase):
    """`_split` keeps the remainder in the move's own unit, so when the
    remainder is not representable there the split does not conserve demand.
    Eight units of a move denominated in dozens is 0.6667, stored 0.67, which
    reads back as 8.04.

    THIS RECORDS AN OPEN DECISION, not a desired outcome. The three quantities
    involved -- what went in, what is split off, and what remains -- cannot all
    be exact while the move stays in the unit the order was placed in, and the
    only fix that conserves changes a move's unit of measure underneath the
    user. `stock_picking_batch`'s `test_wave_split_move_uom` pins the current
    behaviour explicitly (0.58 dozen where 7 units remain), so this is a
    contract to change deliberately or not at all. Until then the residual must
    not be silent.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.unit = cls.env.ref("uom.product_uom_unit")
        cls.dozen = cls.env["uom.uom"].create(
            {
                "name": "Split dozen",
                "relative_factor": 12,
                "relative_uom_id": cls.unit.id,
            }
        )
        cls.warehouse = cls.env["stock.warehouse"].search([], limit=1)
        cls.product = cls.env["product.product"].create(
            {"name": "Split probe", "is_storable": True, "uom_id": cls.unit.id}
        )
        cls.env["stock.quant"]._update_available_quantity(
            cls.product, cls.warehouse.lot_stock_id, 10000
        )

    def _confirmed_dozen_move(self):
        move = self.env["stock.move"].create(
            {
                "product_id": self.product.id,
                "product_uom_id": self.dozen.id,
                "product_uom_qty": 1.0,
                "picking_type_id": self.warehouse.out_type_id.id,
                "location_id": self.warehouse.lot_stock_id.id,
                "location_dest_id": self.env.ref("stock.stock_location_customers").id,
            }
        )
        move._action_confirm()
        return move

    def test_a_representable_remainder_conserves_exactly(self):
        """Six units of a dozen is 0.5, which the move's own unit expresses."""
        move = self._confirmed_dozen_move()
        before = move.product_qty
        new = self.env["stock.move"].create(move._split(6.0))
        self.env.flush_all()
        move.invalidate_recordset()
        new.invalidate_recordset()
        self.assertEqual(move.product_qty + sum(new.mapped("product_qty")), before)

    def test_an_unrepresentable_remainder_is_reported(self):
        move = self._confirmed_dozen_move()
        before = move.product_qty
        with self.assertLogs("odoo.addons.stock.debug.logic", "DEBUG") as captured:
            new = self.env["stock.move"].create(move._split(4.0))
            self.env.flush_all()
        move.invalidate_recordset()
        new.invalidate_recordset()
        self.assertNotEqual(
            move.product_qty + sum(new.mapped("product_qty")),
            before,
            "if this conserves, the open decision above has been taken and this "
            "test should be replaced rather than relaxed",
        )
        self.assertTrue(
            any("does NOT conserve" in line for line in captured.output),
            "a split that changes the total demanded must say so",
        )


@tagged("post_install", "-at_install")
class TestReservationAgreesWithTheQuant(TransactionCase):
    """`stock.quant.reserved_quantity` and the move lines holding that quant are
    two records of one fact, and drift between them is what produces "not enough
    stock" on stock that is free.

    This is the counterpart to the two precision findings in this file: it holds
    because reservation works in `quantity_product_uom`, which is declared
    `min_display_digits` and therefore stored at FULL precision. The fields that
    drifted -- `stock.move.quantity` and `inventory_diff_quantity` -- are the
    ones declared `digits`.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.unit = cls.env.ref("uom.product_uom_unit")
        cls.uoms = {"unit": cls.unit}
        for name, factor in (("dozen", 12), ("third", 3), ("seventh", 7)):
            cls.uoms[name] = cls.env["uom.uom"].create(
                {
                    "name": f"Reserve {name}",
                    "relative_factor": factor,
                    "relative_uom_id": cls.unit.id,
                }
            )
        cls.warehouse = cls.env["stock.warehouse"].search([], limit=1)
        cls.location = cls.warehouse.lot_stock_id
        cls.customer_location = cls.env.ref("stock.stock_location_customers")

    def _lines_hold(self, product):
        lines = self.env["stock.move.line"].search(
            [
                ("product_id", "=", product.id),
                ("location_id", "=", self.location.id),
                ("state", "not in", ("done", "cancel")),
            ]
        )
        return sum(lines.mapped("quantity_product_uom"))

    def test_the_quant_and_its_lines_never_drift(self):
        # short stock forces PARTIAL reservations, and thirds and sevenths make
        # the reserved amounts unrepresentable at the display precision -- a
        # sweep over round numbers would agree without proving anything
        scenarios = [
            ("plenty", 240.0, (1.0, 2.0, 3.0), None),
            ("short", 10.0, (1.0, 2.0, 3.0), None),
            ("short/unreserve", 10.0, (1.0, 2.0, 3.0), "unreserve"),
            ("short/reduce", 10.0, (1.0, 2.0, 3.0), "reduce"),
            ("short/cancel", 10.0, (1.0, 2.0, 3.0), "cancel"),
            ("fractional/short", 5.0, (1.0 / 3.0, 2.0 / 7.0, 0.1), None),
            ("fractional/plenty", 240.0, (1.0 / 3.0, 2.0 / 7.0, 0.1), "unreserve"),
        ]
        disagreements = []
        awkward = checks = 0
        for uom in self.uoms.values():
            for label, stock, demands, action in scenarios:
                product = self.env["product.product"].create(
                    {
                        "name": f"Reserve {uom.name} {label}",
                        "is_storable": True,
                        "uom_id": self.unit.id,
                    }
                )
                self.env["stock.quant"]._update_available_quantity(
                    product, self.location, stock
                )
                self.env.flush_all()
                moves = self.env["stock.move"].create(
                    [
                        {
                            "product_id": product.id,
                            "product_uom_id": uom.id,
                            "product_uom_qty": demand,
                            "picking_type_id": self.warehouse.out_type_id.id,
                            "location_id": self.location.id,
                            "location_dest_id": self.customer_location.id,
                        }
                        for demand in demands
                    ]
                )
                moves = moves._action_confirm(merge=False)
                moves._action_assign()
                if action == "unreserve":
                    moves[0]._unreserve()
                elif action == "reduce":
                    moves[1].product_uom_qty = demands[1] / 2
                elif action == "cancel":
                    moves[2]._action_cancel()
                self.env.flush_all()
                self.env.invalidate_all()

                quants = self.env["stock.quant"].search(
                    [
                        ("product_id", "=", product.id),
                        ("location_id", "=", self.location.id),
                    ]
                )
                reserved = sum(quants.mapped("reserved_quantity"))
                held = self._lines_hold(product)
                checks += 1
                if round(reserved, 2) != reserved:
                    awkward += 1
                if abs(reserved - held) > 1e-9:
                    disagreements.append(
                        f"{uom.name} {label}: quant {reserved!r} vs lines {held!r}"
                    )
        self.assertGreater(checks, 25, "the sweep must exercise something")
        self.assertGreater(
            awkward,
            0,
            "no reserved amount needed more than the display precision, so this "
            "sweep would agree without testing the thing it exists to test",
        )
        self.assertEqual(disagreements, [], "\n".join(disagreements))
