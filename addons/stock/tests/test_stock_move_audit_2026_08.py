from collections import Counter
from itertools import pairwise

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestStockMoveAudit202608(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.wh = cls.env["stock.warehouse"].search([], limit=1)
        cls.stock = cls.wh.lot_stock_id
        cls.supplier = cls.env.ref("stock.stock_location_suppliers")
        cls.customer = cls.env.ref("stock.stock_location_customers")

    def _product(self, name, **kw):
        return self.env["product.product"].create(
            {"name": name, "is_storable": True, **kw},
        )

    def _capped_shelves(self, product, cap=2, n=3):
        category = self.env["stock.storage.category"].create(
            {
                "name": "cap",
                "allow_new_product": "mixed",
                "product_capacity_ids": [
                    (0, 0, {"product_id": product.id, "quantity": cap}),
                ],
            },
        )
        shelves = self.env["stock.location"].create(
            [
                {
                    "name": f"shelf{i}",
                    "location_id": self.stock.id,
                    "usage": "internal",
                    "storage_category_id": category.id,
                }
                for i in range(n)
            ],
        )
        self.env["stock.putaway.rule"].create(
            {
                "location_in_id": self.stock.id,
                "location_out_id": self.stock.id,
                "product_id": product.id,
                "storage_category_id": category.id,
            },
        )
        return shelves

    def _incoming_move(self, product, qty, uom=None, **kw):
        return self.env["stock.move"].create(
            {
                "product_id": product.id,
                "product_uom_qty": qty,
                "location_id": self.supplier.id,
                "location_dest_id": self.stock.id,
                "picking_type_id": self.wh.in_type_id.id,
                **({"product_uom_id": uom.id} if uom else {}),
                **kw,
            },
        )

    def test_prefilled_serial_count_is_a_number_of_units(self):
        dozen = self.env.ref("uom.product_uom_dozen")
        units = self.env.ref("uom.product_uom_unit")
        product = self._product(
            "sn-dozen",
            tracking="serial",
            uom_id=units.id,
            uom_ids=[(4, dozen.id)],
        )
        move = self._incoming_move(product, 2, uom=dozen)
        move._action_confirm()
        move._action_assign()

        self.assertEqual(len(move.move_line_ids), 24, "sanity: 2 dozen is 24 serials")
        self.assertEqual(
            move.next_serial_count,
            24,
            "next_serial_count counts units; it was filled from the move's UoM quantity",
        )

    def test_prefilled_serial_count_generates_the_whole_demand(self):
        dozen = self.env.ref("uom.product_uom_dozen")
        units = self.env.ref("uom.product_uom_unit")
        product = self._product(
            "sn-dozen-gen",
            tracking="serial",
            uom_id=units.id,
            uom_ids=[(4, dozen.id)],
        )
        move = self._incoming_move(product, 2, uom=dozen)
        move._action_confirm()
        move._action_assign()
        move.move_line_ids.unlink()

        move._update_move_lines_for_serials("SN-0001", move.next_serial_count)
        self.assertEqual(len(move.move_line_ids), 24)

    def test_an_explicit_serial_count_survives_reservation(self):
        product = self._product("sn-explicit", tracking="serial")
        move = self._incoming_move(
            product,
            3,
            next_serial="SN-1",
            next_serial_count=7,
        )
        move._action_confirm()
        move._action_assign()

        self.assertEqual(
            move.next_serial_count,
            7,
            "reservation overwrote a count the user had already entered",
        )

    def test_generated_lot_lines_consume_capacity_as_they_are_placed(self):
        product = self._product("gen-cap", tracking="serial")
        self._capped_shelves(product, cap=2, n=3)

        vals = self.env["stock.move"].action_generate_lot_line_vals(
            {
                "default_product_id": product.id,
                "default_tracking": "serial",
                "default_location_dest_id": self.stock.id,
                "default_picking_type_id": self.wh.in_type_id.id,
                "default_company_id": self.env.company.id,
            },
            "generate",
            "GEN-0001",
            6,
            "",
        )
        placed = Counter(v["location_dest_id"]["id"] for v in vals)
        self.assertEqual(
            len(placed),
            3,
            f"6 serials, 3 shelves of capacity 2, but they were placed as {placed}",
        )

    def test_the_server_side_generator_is_the_control(self):
        product = self._product("gen-cap-ctl", tracking="serial")
        self._capped_shelves(product, cap=2, n=3)
        move = self._incoming_move(product, 6)
        move._action_confirm()
        move.move_line_ids.unlink()

        move._update_move_lines_for_serials("CTL-0001", 6)
        placed = Counter(move.move_line_ids.mapped("location_dest_id").ids)
        self.assertEqual(len(placed), 3, f"control path placed {placed}")

    def test_generation_excludes_the_lines_it_is_replacing(self):
        product = self._product("gen-stale", tracking="serial")
        shelves = self._capped_shelves(product, cap=2, n=3)
        move = self._incoming_move(product, 6)
        move._action_confirm()
        self.assertEqual(
            len(move.move_line_ids.location_dest_id & shelves),
            3,
            "sanity: confirmation already spread 6 units over the 3 shelves",
        )

        vals = self.env["stock.move"].action_generate_lot_line_vals(
            {
                "default_product_id": product.id,
                "default_tracking": "serial",
                "default_move_id": move.id,
                "default_location_dest_id": self.stock.id,
                "default_picking_type_id": self.wh.in_type_id.id,
                "default_company_id": self.env.company.id,
                "exclude_sml_ids": move.move_line_ids.ids,
            },
            "generate",
            "STALE-0001",
            6,
            "",
        )
        placed = Counter(v["location_dest_id"]["id"] for v in vals)
        self.assertNotIn(
            self.stock.id,
            placed,
            f"generated lines fell back to the parent location: {placed}",
        )
        self.assertEqual(
            len(placed), 3, f"the batch did not consume capacity as it placed: {placed}"
        )

    def test_inventory_reference_is_not_stored_in_the_writers_language(self):
        self.env["res.lang"]._activate_lang("es_ES")
        product = self._product("ref-i18n")
        quant = (
            self.env["stock.quant"]
            .with_context(inventory_mode=True, lang="es_ES")
            .create(
                {
                    "product_id": product.id,
                    "location_id": self.stock.id,
                    "inventory_quantity": 7,
                },
            )
        )
        quant.with_context(lang="es_ES").action_apply_inventory()
        move = self.env["stock.move"].search(
            [("product_id", "=", product.id), ("is_inventory", "=", True)],
            limit=1,
        )
        move.invalidate_recordset(["reference"])
        self.env.add_to_compute(self.env["stock.move"]._fields["reference"], move)
        move.with_context(lang="es_ES").flush_recordset(["reference"])

        self.env.cr.execute(
            "SELECT reference FROM stock_move WHERE id = %s", (move.id,)
        )
        stored = self.env.cr.fetchone()[0]
        self.assertNotIn(
            "Cantidad",
            stored or "",
            f"the reference column holds one language for every reader: {stored!r}",
        )

    def test_a_picked_receipt_keeps_its_state_when_demand_is_rewritten(self):
        product = self._product("picked-receipt")
        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": self.wh.in_type_id.id,
                "location_id": self.supplier.id,
                "location_dest_id": self.stock.id,
            },
        )
        move = self._incoming_move(product, 5, picking_id=picking.id)
        move._action_confirm()
        move._action_assign()
        move.picked = True
        self.assertEqual(move.state, "assigned")

        move.product_uom_qty = 5.0
        self.env.flush_all()
        self.env.invalidate_all()

        self.assertEqual(move.quantity, 5.0, "sanity: still fully reserved")
        self.assertEqual(
            move.state,
            "assigned",
            "a fully reserved, picked receipt was left partially_available",
        )

    def test_a_deep_chain_does_not_crash_the_upstream_walk(self):
        product = self._product("upstream-depth")
        inside = self.env["stock.location"].create(
            [
                {"name": f"u{i}", "location_id": self.stock.id, "usage": "internal"}
                for i in range(2)
            ],
        )
        moves = self.env["stock.move"].create(
            [
                {
                    "product_id": product.id,
                    "product_uom_qty": 1,
                    "location_id": inside[i % 2].id,
                    "location_dest_id": inside[(i + 1) % 2].id,
                    "picking_type_id": self.wh.int_type_id.id,
                }
                for i in range(300)
            ],
        )
        for previous, following in pairwise(moves):
            following.move_orig_ids = [(4, previous.id)]
        moves._action_confirm(merge=False)

        moves[-1]._get_upstream_documents_and_responsibles(self.env["stock.move"])

    def test_the_bound_cannot_fire_on_an_ordinary_chain(self):
        self.assertGreaterEqual(
            self.env["stock.move"]._MAX_UPSTREAM_DEPTH,
            100,
            "the bound must sit far above any chain a warehouse really builds",
        )

    def test_pasting_lots_from_a_windows_editor(self):
        self.assertEqual(
            self.env["stock.move"].split_lots("A1;5\r\nA2;3\r\nA3;7"),
            [
                {"lot_name": "A1", "quantity": 5.0},
                {"lot_name": "A2", "quantity": 3.0},
                {"lot_name": "A3", "quantity": 7.0},
            ],
        )

    def test_pasting_lots_is_unchanged_for_unix_line_endings(self):
        self.assertEqual(
            self.env["stock.move"].split_lots("A1;5\nA2\n\nLOT 3"),
            [
                {"lot_name": "A1", "quantity": 5.0},
                {"lot_name": "A2", "quantity": 1},
                {"lot_name": "LOT 3", "quantity": 1},
            ],
        )

    def _deadline_chain(self, length, deadline="2026-06-01 00:00:00"):
        product = self._product(f"deadline-{length}")
        moves = self.env["stock.move"].create(
            [
                {
                    "product_id": product.id,
                    "product_uom_qty": 1,
                    "location_id": self.stock.id,
                    "location_dest_id": self.customer.id,
                    "picking_type_id": self.wh.out_type_id.id,
                    "date_deadline": deadline,
                }
                for _ in range(length)
            ],
        )
        for previous, following in pairwise(moves):
            following.move_orig_ids = [(4, previous.id)]
        return moves

    def test_a_long_chain_propagates_its_deadline(self):
        moves = self._deadline_chain(300)

        moves[0].write({"date_deadline": "2026-07-01 00:00:00"})

        self.assertEqual(
            len(
                moves.filtered(lambda m: str(m.date_deadline) == "2026-07-01 00:00:00")
            ),
            300,
            "the deadline did not reach the whole chain",
        )

    def test_rewriting_the_same_deadline_does_not_cascade(self):
        moves = self._deadline_chain(4)
        writes = []
        model = type(self.env["stock.move"])
        original = model.write

        def spy(records, vals):
            if "date_deadline" in vals:
                writes.append(records.ids)
            return original(records, vals)

        self.patch(model, "write", spy)
        moves[0].write({"date_deadline": "2026-06-01 00:00:00"})

        self.assertEqual(
            len(writes),
            1,
            f"writing the deadline the chain already carries cascaded: {writes}",
        )

    def test_merging_cancelling_quantities_does_not_divide_by_zero(self):
        dozen = self.env.ref("uom.product_uom_dozen")
        units = self.env.ref("uom.product_uom_unit")
        product = self._product("merge-zero", uom_id=dozen.id, uom_ids=[(4, units.id)])
        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": self.wh.out_type_id.id,
                "location_id": self.stock.id,
                "location_dest_id": self.customer.id,
            },
        )
        common = {
            "product_id": product.id,
            "product_uom_id": units.id,
            "location_id": self.stock.id,
            "location_dest_id": self.customer.id,
            "picking_id": picking.id,
        }
        positive = self.env["stock.move"].create({**common, "product_uom_qty": 1.0})
        negative = self.env["stock.move"].create({**common, "product_uom_qty": -1.0})
        self.assertEqual(
            positive.product_qty + negative.product_qty,
            0,
            "sanity: the converted quantities cancel exactly",
        )
        self.assertFalse(
            units._is_zero_stored(positive.product_qty, product.uom_id),
            "sanity: each move carries a real quantity, so the total is a "
            "cancellation and not two zeroes",
        )

        (positive | negative)._action_confirm()

    def test_create_does_not_mutate_the_vals_it_is_given(self):
        product = self._product("vals-mutation")
        vals = {
            "product_id": product.id,
            "product_uom_qty": 1,
            "location_id": self.stock.id,
            "location_dest_id": self.customer.id,
            "state": "done",
        }
        before = dict(vals)
        self.env["stock.move"].create([vals])
        self.assertEqual(
            vals,
            before,
            "create() wrote back into the caller's dict; a reused vals template "
            "carries picked/state into the next, unrelated move",
        )

    def test_partner_of_a_transit_move_does_not_depend_on_who_is_looking(self):
        other = self.env["res.company"].create({"name": "Audit Co"})
        warehouse = self.env["stock.warehouse"].create(
            {
                "name": "AWH",
                "code": "AWH",
                "company_id": other.id,
                "partner_id": self.env["res.partner"].create({"name": "AWH addr"}).id,
            },
        )
        product = self._product("transit-partner")
        move = (
            self.env["stock.move"]
            .with_company(other)
            .create(
                {
                    "company_id": other.id,
                    "product_id": product.id,
                    "product_uom_qty": 1,
                    "location_id": other.stock_config_id.internal_transit_location_id.id,
                    "location_dest_id": warehouse.lot_stock_id.id,
                    "partner_id": self.env["res.partner"]
                    .create({"name": "Move partner"})
                    .id,
                },
            )
        )
        self.assertEqual(
            move.with_company(self.env.company)._get_partner_id(),
            move.with_company(other)._get_partner_id(),
            "_get_partner_id compares against env.company's transit location, "
            "so it answers differently depending on the active company",
        )
