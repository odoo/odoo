from datetime import timedelta

from odoo import Command, fields
from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.stock.tests.common import TestStockCommon


@tagged("post_install", "-at_install")
class TestStockMoveReviewFixes(TestStockCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.picking_type_out.write(
            {"use_existing_lots": True, "use_create_lots": True},
        )
        cls.lot_product = cls.env["product.product"].create(
            {
                "name": "Review Lot Product",
                "type": "consu",
                "is_storable": True,
                "tracking": "lot",
            },
        )

    def _create_out_picking(self):
        return self.env["stock.picking"].create(
            {
                "picking_type_id": self.picking_type_out.id,
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
            },
        )

    def test_create_keeps_lot_ids_like_write(self):
        lot = self.env["stock.lot"].create(
            {"name": "REVIEW-NOSTOCK", "product_id": self.lot_product.id},
        )

        picking_c = self._create_out_picking()
        move_c = self.env["stock.move"].create(
            {
                "product_id": self.lot_product.id,
                "product_uom_qty": 3,
                "product_uom_id": self.lot_product.uom_id.id,
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "picking_id": picking_c.id,
                "quantity": 3.0,
                "lot_ids": [Command.set(lot.ids)],
            },
        )

        picking_w = self._create_out_picking()
        move_w = self.env["stock.move"].create(
            {
                "product_id": self.lot_product.id,
                "product_uom_qty": 3,
                "product_uom_id": self.lot_product.uom_id.id,
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "picking_id": picking_w.id,
            },
        )
        picking_w.action_confirm()
        move_w.write({"quantity": 3.0, "lot_ids": [Command.set(lot.ids)]})

        self.assertEqual(
            move_c.lot_ids,
            lot,
            "create dropped lot_ids when quantity was also supplied",
        )
        self.assertEqual(move_w.lot_ids, lot)
        self.assertEqual(
            move_c.lot_ids,
            move_w.lot_ids,
            "create and write disagree on quantity+lot_ids handling",
        )

    def test_create_drops_lot_ids_when_explicit_move_lines(self):
        lot = self.env["stock.lot"].create(
            {"name": "REVIEW-EXPLICIT", "product_id": self.lot_product.id},
        )
        picking = self._create_out_picking()
        move = self.env["stock.move"].create(
            {
                "product_id": self.lot_product.id,
                "product_uom_qty": 1,
                "product_uom_id": self.lot_product.uom_id.id,
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "picking_id": picking.id,
                "move_line_ids": [
                    Command.create(
                        {
                            "product_id": self.lot_product.id,
                            "product_uom_id": self.lot_product.uom_id.id,
                            "location_id": self.stock_location.id,
                            "location_dest_id": self.customer_location.id,
                            "quantity": 1,
                        },
                    ),
                ],
                "lot_ids": [Command.set(lot.ids)],
            },
        )
        self.assertFalse(
            move.lot_ids,
            "explicit move_line_ids should take precedence over lot_ids on create",
        )

    def test_generate_lot_line_vals_missing_tracking_raises_usererror(self):
        with self.assertRaises(UserError):
            self.env["stock.move"].action_generate_lot_line_vals(
                {
                    "default_product_id": self.lot_product.id,
                    "default_location_dest_id": self.customer_location.id,
                },
                "generate",
                "SN001",
                2,
                "",
            )

    def test_generate_lot_line_vals_invalid_mode_raises_usererror(self):
        with self.assertRaises(UserError):
            self.env["stock.move"].action_generate_lot_line_vals(
                {
                    "default_product_id": self.lot_product.id,
                    "default_tracking": "serial",
                    "default_location_dest_id": self.customer_location.id,
                },
                "not-a-mode",
                "SN001",
                2,
                "",
            )

    def test_get_merge_key_single_non_float_field(self):
        Move = self.env["stock.move"]
        picking = self._create_out_picking()
        move = Move.create(
            {
                "product_id": self.lot_product.id,
                "product_uom_qty": 1,
                "product_uom_id": self.lot_product.uom_id.id,
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "picking_id": picking.id,
            },
        )
        key_fn = Move._get_merge_key(["product_id"])
        key = key_fn(move)
        self.assertIsInstance(key, tuple)
        self.assertEqual(key, (move.product_id,))

        key_fn2 = Move._get_merge_key(["product_id", "price_unit"])
        key2 = key_fn2(move)
        self.assertIsInstance(key2, tuple)
        self.assertEqual(len(key2), 2)

        key_fn3 = Move._get_merge_key(["price_unit"])
        self.assertIsInstance(key_fn3(move), tuple)

    def test_internal_move_forecast_still_computed(self):
        storable = self.env["product.product"].create(
            {"name": "Review Storable", "type": "consu", "is_storable": True},
        )
        self.env["stock.quant"]._update_available_quantity(
            storable,
            self.stock_location,
            10,
        )
        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": self.picking_type_int.id,
                "location_id": self.stock_location.id,
                "location_dest_id": self.shelf_1.id,
            },
        )
        move = self.env["stock.move"].create(
            {
                "product_id": storable.id,
                "product_uom_qty": 4,
                "product_uom_id": storable.uom_id.id,
                "location_id": self.stock_location.id,
                "location_dest_id": self.shelf_1.id,
                "picking_id": picking.id,
            },
        )
        picking.action_confirm()
        move.invalidate_recordset(["forecast_availability"])
        self.assertAlmostEqual(move.forecast_availability, 4.0)

    def _done_receipt(self, product, qty, lot=None):
        move = self.MoveObj.create(
            {
                "product_id": product.id,
                "product_uom_qty": qty,
                "product_uom_id": product.uom_id.id,
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
            },
        )
        move._action_confirm()
        ml_vals = {
            "move_id": move.id,
            "product_id": product.id,
            "product_uom_id": product.uom_id.id,
            "location_id": self.supplier_location.id,
            "location_dest_id": self.stock_location.id,
            "quantity": qty,
            "picked": True,
        }
        if lot:
            ml_vals["lot_id"] = lot.id
        self.env["stock.move.line"].create(ml_vals)
        move._action_done()
        self.assertEqual(move.state, "done")
        return move

    def test_unlink_confirmed_receipt_refreshes_orderpoint(self):
        product = self.env["product.product"].create(
            {
                "name": "Review Orderpoint Product",
                "type": "consu",
                "is_storable": True,
            },
        )
        orderpoint = self.env["stock.warehouse.orderpoint"].create(
            {
                "product_id": product.id,
                "location_id": self.stock_location.id,
                "product_min_qty": 10,
                "product_max_qty": 10,
                "trigger": "manual",
            },
        )
        self.assertAlmostEqual(orderpoint.qty_to_order, 10)

        move = self.MoveObj.create(
            {
                "product_id": product.id,
                "product_uom_qty": 10,
                "product_uom_id": product.uom_id.id,
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
            },
        )
        move._action_confirm()
        self.assertAlmostEqual(
            orderpoint.qty_to_order,
            0,
            msg="the confirmed receipt should cover the orderpoint",
        )

        move.unlink()
        self.assertAlmostEqual(
            orderpoint.qty_to_order,
            10,
            msg="deleting the receipt must invalidate the orderpoint forecast",
        )

    def test_chained_assign_update_take_marks_move_assigned(self):
        lot_1, lot_2 = self.LotObj.create(
            [
                {"name": "REVIEW-CHAIN-1", "product_id": self.lot_product.id},
                {"name": "REVIEW-CHAIN-2", "product_id": self.lot_product.id},
            ],
        )
        parent_a = self._done_receipt(self.lot_product, 3, lot=lot_2)
        parent_b = self._done_receipt(self.lot_product, 7, lot=lot_1)

        move = self.MoveObj.create(
            {
                "product_id": self.lot_product.id,
                "product_uom_qty": 10,
                "product_uom_id": self.lot_product.uom_id.id,
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
            },
        )
        move._action_confirm()
        move.move_orig_ids = [Command.set((parent_a | parent_b).ids)]
        self.env["stock.move.line"].create(
            {
                "move_id": move.id,
                "product_id": self.lot_product.id,
                "product_uom_id": self.lot_product.uom_id.id,
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "lot_id": lot_1.id,
                "quantity": 4,
            },
        )

        move._action_assign()

        self.assertAlmostEqual(move.quantity, 10)
        self.assertEqual(
            move.state,
            "assigned",
            "a fully reserved chained move must not be written back as"
            " partially available",
        )

    def test_generate_lot_line_vals_without_company(self):
        vals_list = self.env["stock.move"].action_generate_lot_line_vals(
            {
                "default_product_id": self.lot_product.id,
                "default_tracking": "lot",
                "default_location_dest_id": self.customer_location.id,
                "default_quantity": 4,
                "default_picking_type_id": self.picking_type_out.id,
            },
            "generate",
            "REVIEW-NOCOMPANY-01",
            2,
            "",
        )
        self.assertEqual(len(vals_list), 2)
        self.assertTrue(all(vals.get("lot_id") for vals in vals_list))

    def test_inventory_reference_follows_quantity(self):
        product = self.env["product.product"].create(
            {
                "name": "Review Inventory Product",
                "type": "consu",
                "is_storable": True,
            },
        )
        self.env["stock.quant"]._update_available_quantity(
            product,
            self.stock_location,
            5,
        )
        move = self.MoveObj.create(
            {
                "product_id": product.id,
                "product_uom_qty": 0,
                "product_uom_id": product.uom_id.id,
                "location_id": self.stock_location.id,
                "location_dest_id": product.property_stock_inventory.id,
                "is_inventory": True,
            },
        )
        self.assertIn("Confirmed", move.reference)
        move.quantity = 5
        self.assertIn(
            "Updated",
            move.reference,
            "the inventory reference must follow the quantity",
        )

    def test_key_assign_picking_includes_company(self):
        picking = self._create_out_picking()
        move = self.MoveObj.create(
            {
                "product_id": self.lot_product.id,
                "product_uom_qty": 1,
                "product_uom_id": self.lot_product.uom_id.id,
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "picking_id": picking.id,
            },
        )
        self.assertIn(move.company_id, move._get_picking_assignation_key())

    def test_compute_dependencies_locked(self):
        registry = self.env.registry
        Move = self.env["stock.move"]
        packaging_deps = registry.field_depends[Move._fields["quantity_packaging_uom"]]
        self.assertIn("product_uom_id", packaging_deps)
        package_ids_deps = registry.field_depends[Move._fields["package_ids"]]
        self.assertIn("state", package_ids_deps)
        self.assertIn("move_line_ids.package_history_id", package_ids_deps)

    def test_date_deadline_propagates_through_chain(self):
        parent = self.MoveObj.create(
            {
                "product_id": self.lot_product.id,
                "product_uom_qty": 2,
                "product_uom_id": self.lot_product.uom_id.id,
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
            },
        )
        child = self.MoveObj.create(
            {
                "product_id": self.lot_product.id,
                "product_uom_qty": 2,
                "product_uom_id": self.lot_product.uom_id.id,
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "move_orig_ids": [Command.set(parent.ids)],
            },
        )
        (parent | child)._action_confirm()
        deadline = fields.Datetime.now() + timedelta(days=2)
        child.date_deadline = deadline
        self.assertEqual(parent.date_deadline, deadline)

    def test_trigger_assign_reserves_waiting_moves(self):
        self.picking_type_out.reservation_method = "at_confirm"
        product = self.env["product.product"].create(
            {
                "name": "Review Trigger Product",
                "type": "consu",
                "is_storable": True,
            },
        )
        picking = self._create_out_picking()
        out_move = self.MoveObj.create(
            {
                "product_id": product.id,
                "product_uom_qty": 5,
                "product_uom_id": product.uom_id.id,
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "picking_id": picking.id,
            },
        )
        picking.action_confirm()
        self.assertEqual(out_move.state, "confirmed")

        receipt = self._done_receipt(product, 10)
        receipt._trigger_assign()
        self.assertEqual(out_move.state, "assigned")

    def test_date_deadline_cleared_through_chain(self):
        parent = self.MoveObj.create(
            {
                "product_id": self.lot_product.id,
                "product_uom_qty": 2,
                "product_uom_id": self.lot_product.uom_id.id,
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
            },
        )
        child = self.MoveObj.create(
            {
                "product_id": self.lot_product.id,
                "product_uom_qty": 2,
                "product_uom_id": self.lot_product.uom_id.id,
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "move_orig_ids": [Command.set(parent.ids)],
            },
        )
        (parent | child)._action_confirm()
        deadline = fields.Datetime.now() + timedelta(days=2)
        child.date_deadline = deadline
        self.assertEqual(parent.date_deadline, deadline)

        child.write({"date_deadline": False})
        self.assertFalse(child.date_deadline)
        self.assertFalse(parent.date_deadline)

    def test_location_dest_follows_location_final(self):
        registry = self.env.registry
        deps = registry.field_depends[
            self.env["stock.move"]._fields["location_dest_id"]
        ]
        self.assertIn("location_final_id", deps)

        sub = self.env["stock.location"].create(
            {
                "name": "Review Final Sub",
                "location_id": self.stock_location.id,
                "usage": "internal",
            },
        )
        move = self.MoveObj.create(
            {
                "product_id": self.lot_product.id,
                "product_uom_qty": 5,
                "product_uom_id": self.lot_product.uom_id.id,
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
            },
        )
        self.assertEqual(move.location_dest_id, self.stock_location)

        move.location_final_id = sub
        self.assertEqual(
            move.location_dest_id,
            sub,
            "writing location_final_id must re-derive location_dest_id",
        )

        created = self.MoveObj.create(
            {
                "product_id": self.lot_product.id,
                "product_uom_qty": 5,
                "product_uom_id": self.lot_product.uom_id.id,
                "picking_type_id": self.picking_type_in.id,
                "location_final_id": sub.id,
            },
        )
        self.assertEqual(created.picking_type_id, self.picking_type_in)
        self.assertEqual(created.location_dest_id, sub)

    def test_force_qty_honoured_on_chained_move(self):
        product = self.env["product.product"].create(
            {"name": "Force Qty Product", "type": "consu", "is_storable": True},
        )
        inbound = self._done_receipt(product, 10)
        chained = self.MoveObj.create(
            {
                "product_id": product.id,
                "product_uom_qty": 10,
                "product_uom_id": product.uom_id.id,
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "picking_type_id": self.picking_type_out.id,
                "move_orig_ids": [Command.set(inbound.ids)],
            },
        )
        chained._action_confirm()
        chained.move_line_ids.unlink()
        self.assertTrue(chained.move_orig_ids, "the move must be chained")

        chained._action_assign(force_qty=3)
        self.assertEqual(
            chained.quantity,
            3,
            "force_qty must bound the reservation on the chained branch too",
        )

    def test_write_skips_orderpoint_refresh_when_scope_unchanged(self):
        move = self.MoveObj.create(
            {
                "product_id": self.lot_product.id,
                "product_uom_qty": 1,
                "product_uom_id": self.lot_product.uom_id.id,
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
            },
        )
        self.env.flush_all()

        calls = []
        Move = type(self.env["stock.move"])
        original = Move._get_orderpoints_to_update

        def counting(records):
            calls.append(len(records))
            return original(records)

        self.patch(Move, "_get_orderpoints_to_update", counting)

        move.write({"location_id": self.stock_location.id})
        self.env.flush_all()
        unchanged_calls = len(calls)

        calls.clear()
        move.write({"location_id": self.customer_location.id})
        self.env.flush_all()
        changed_calls = len(calls)

        self.assertEqual(
            unchanged_calls,
            1,
            "an unchanged source location must not search orderpoints twice",
        )
        self.assertEqual(
            changed_calls,
            2,
            "a real location change must refresh both the old and the new scope",
        )

    def test_pasted_lot_list_may_repeat_a_name(self):
        vals_list = [
            {"lot_name": "REVIEW-DUP-A", "quantity": 1},
            {"lot_name": "REVIEW-DUP-B", "quantity": 1},
            {"lot_name": "REVIEW-DUP-A", "quantity": 1},
        ]
        Lot = self.env["stock.lot"]
        before = Lot.search_count([("product_id", "=", self.lot_product.id)])

        self.env["stock.move"]._create_lot_ids_from_move_line_vals(
            vals_list,
            self.lot_product.id,
            self.env.company.id,
        )
        self.env.flush_all()

        created = Lot.search_count([("product_id", "=", self.lot_product.id)]) - before
        self.assertEqual(created, 2, "one lot per distinct name, not per line")
        self.assertEqual(
            vals_list[0]["lot_id"],
            vals_list[2]["lot_id"],
            "both lines carrying the same name must point at the same lot",
        )
        self.assertNotEqual(vals_list[0]["lot_id"], vals_list[1]["lot_id"])
        self.assertTrue(all(v["lot_name"] is False for v in vals_list))

    def test_generate_lot_line_vals_import_tolerates_a_repeated_name(self):
        self.picking_type_in.write(
            {"use_create_lots": True, "use_existing_lots": True},
        )
        context_data = {
            "default_product_id": self.lot_product.id,
            "default_tracking": "lot",
            "default_location_dest_id": self.stock_location.id,
            "default_company_id": self.env.company.id,
            "default_picking_type_id": self.picking_type_in.id,
            "default_quantity": 3,
        }
        vals = self.env["stock.move"].action_generate_lot_line_vals(
            context_data,
            "import",
            "",
            0,
            "REVIEW-PASTE-1\nREVIEW-PASTE-2\nREVIEW-PASTE-1",
        )
        self.assertEqual(len(vals), 3, "every pasted line still yields a move line")
        self.assertEqual(
            vals[0]["lot_id"]["id"],
            vals[2]["lot_id"]["id"],
            "the repeated name must resolve to the one lot",
        )

    def test_generated_lot_split_rejects_non_numeric_quantity(self):
        with self.assertRaises(UserError):
            self.env["stock.move"]._prepare_lot_generation_split("not-a-number", 2)
        with self.assertRaises(UserError):
            self.env["stock.move"]._prepare_lot_generation_split(10, None)

    def test_boolean_computes_assign_booleans(self):
        move = self.MoveObj.create(
            {
                "product_id": self.lot_product.id,
                "product_uom_qty": 1,
                "product_uom_id": self.lot_product.uom_id.id,
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
            },
        )
        for fname in (
            "is_quantity_done_editable",
            "show_lot_actions",
            "has_partial_result_packages",
        ):
            self.assertIsInstance(
                move[fname],
                bool,
                f"{fname} should hold a bool, not {type(move[fname]).__name__}",
            )

    def test_required_location_fields_stay_precomputed(self):
        Move = self.env["stock.move"]
        for fname in ("location_id", "location_dest_id"):
            field = Move._fields[fname]
            self.assertTrue(field.required, f"{fname} is expected to be required")
            self.assertTrue(
                field.precompute,
                f"{fname} lost precompute=True; a required field that is not "
                f"precomputed cannot be inserted. Check whether a dependency was "
                f"added that is a stored compute without precompute=True.",
            )


@tagged("post_install", "-at_install")
class TestStockMoveLotInvariants(TestStockCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        for picking_type in (cls.picking_type_in, cls.picking_type_out):
            picking_type.write({"use_create_lots": True, "use_existing_lots": True})

    def _product(self, name, tracking):
        return self.env["product.product"].create(
            {
                "name": name,
                "type": "consu",
                "is_storable": True,
                "tracking": tracking,
            },
        )

    def _stock_in(self, product, qty, lot_name):
        lot = self.env["stock.lot"].search(
            [("product_id", "=", product.id), ("name", "=", lot_name)],
            limit=1,
        ) or self.env["stock.lot"].create(
            {"product_id": product.id, "name": lot_name},
        )
        self.env["stock.quant"]._update_available_quantity(
            product,
            self.stock_location,
            qty,
            lot_id=lot,
        )
        return lot

    def _outgoing(self, product, qty):
        move = self.MoveObj.create(
            {
                "product_id": product.id,
                "product_uom_qty": qty,
                "product_uom_id": product.uom_id.id,
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "picking_type_id": self.picking_type_out.id,
            },
        )
        move._action_confirm()
        return move

    def _assert_invariants(self, move, label):
        move.invalidate_recordset()
        lines = move.move_line_ids
        summed = sum(
            ml.product_uom_id._get_quantity_in_unit(
                ml.quantity,
                move.product_uom_id,
                round=False,
            )
            for ml in lines
        )
        self.assertEqual(
            move.product_uom_id.compare(move.quantity, summed),
            0,
            f"{label}: quantity {move.quantity} != sum of lines {summed}",
        )
        self.assertEqual(
            move.lot_ids,
            lines.filtered(lambda ml: ml.quantity).lot_id,
            f"{label}: lot_ids disagrees with the lots the lines carry",
        )
        if move.product_id.tracking == "serial":
            names = [ml.lot_id.name for ml in lines if ml.lot_id]
            self.assertEqual(
                len(names),
                len(set(names)),
                f"{label}: a serial number is carried by two lines: {names}",
            )

    def test_lot_reservation_paths_hold_the_invariants(self):
        product = self._product("Invariant Lot", "lot")
        lot_a = self._stock_in(product, 6, "INV-A")
        lot_b = self._stock_in(product, 6, "INV-B")

        move = self._outgoing(product, 8)
        move._action_assign()
        self._assert_invariants(move, "assign across two lots")

        move.lot_ids = lot_a | lot_b
        self._assert_invariants(move, "lot_ids set to both lots")

        move.lot_ids = lot_a
        self._assert_invariants(move, "lot_ids narrowed to one")

    def test_a_lot_without_stock_still_leaves_the_invariants_standing(self):
        product = self._product("Invariant Ghost", "lot")
        self._stock_in(product, 5, "INV-HAS")
        ghost = self.env["stock.lot"].create(
            {"product_id": product.id, "name": "INV-GHOST"},
        )
        move = self._outgoing(product, 3)
        move._action_assign()
        move.lot_ids = ghost
        self._assert_invariants(move, "lot_ids set to a lot with no stock")

    def test_serial_reservation_paths_hold_the_invariants(self):
        product = self._product("Invariant Serial", "serial")
        serials = [self._stock_in(product, 1, f"INV-S{i}") for i in range(3)]

        move = self._outgoing(product, 2)
        move._action_assign()
        self._assert_invariants(move, "serial assign")

        move.lot_ids = serials[0] | serials[1]
        self._assert_invariants(move, "lot_ids set to the reserved serials")

        move.lot_ids = serials[0] | serials[2]
        self._assert_invariants(move, "one serial swapped for another")

    def test_a_bypassing_move_holds_the_invariants(self):
        product = self._product("Invariant Incoming", "lot")
        move = self.MoveObj.create(
            {
                "product_id": product.id,
                "product_uom_qty": 5,
                "product_uom_id": product.uom_id.id,
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
                "picking_type_id": self.picking_type_in.id,
            },
        )
        move._action_confirm()
        move._action_assign()
        self._assert_invariants(move, "incoming assign")

        move.lot_ids = self.env["stock.lot"].create(
            {"product_id": product.id, "name": "INV-IN"},
        )
        self._assert_invariants(move, "incoming lot_ids set")
