from itertools import pairwise
from unittest.mock import patch

from odoo import Command
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestStockMoveAudit20260831(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.wh = cls.env["stock.warehouse"].search([], limit=1)
        cls.stock = cls.wh.lot_stock_id
        cls.supplier = cls.env.ref("stock.stock_location_suppliers")
        cls.customer = cls.env.ref("stock.stock_location_customers")
        cls.Move = cls.env["stock.move"]

    def _product(self, name, **kw):
        return self.env["product.product"].create(
            {"name": name, "is_storable": True, **kw},
        )

    def _internal_move(self, product, qty, **kw):
        return self.Move.create(
            {
                "product_id": product.id,
                "product_uom_qty": qty,
                "location_id": self.stock.id,
                "location_dest_id": self.wh.wh_output_stock_loc_id.id,
                "picking_type_id": self.wh.int_type_id.id,
                **kw,
            },
        )

    def _lattice(self, depth, width):
        product = self._product(f"lattice-{depth}-{width}")
        shelves = self.env["stock.location"].create(
            [
                {"name": f"l{i}", "location_id": self.stock.id, "usage": "internal"}
                for i in range(2)
            ],
        )
        layers = [
            self.Move.create(
                [
                    {
                        "product_id": product.id,
                        "product_uom_qty": 1,
                        "location_id": shelves[k % 2].id,
                        "location_dest_id": shelves[(k + 1) % 2].id,
                        "picking_type_id": self.wh.int_type_id.id,
                    }
                    for _ in range(width)
                ],
            )
            for k in range(depth)
        ]
        for upper, lower in pairwise(layers):
            upper.move_orig_ids = [Command.set(lower.ids)]
        self.Move.browse([i for layer in layers for i in layer.ids])._action_confirm(
            merge=False,
        )
        return layers[0][0], layers

    def _count_upstream_calls(self, top):
        seen = []
        original = type(self.Move)._get_upstream_documents_and_responsibles

        def counting(records, visited):
            seen.append(records.id)
            return original(records, visited)

        with patch.object(
            type(self.Move),
            "_get_upstream_documents_and_responsibles",
            counting,
        ):
            top._get_upstream_documents_and_responsibles(self.Move)
        return len(seen)

    def test_the_upstream_walk_costs_one_call_per_edge(self):
        depth, width = 8, 2
        top, __ = self._lattice(depth, width)
        entered = 1 + (depth - 2) * width
        calls = self._count_upstream_calls(top)
        self.assertLessEqual(
            calls,
            1 + entered * width,
            f"{calls} calls over a graph with {entered * width} edges: the walk "
            f"is re-entering subtrees, which is 2**depth once every level "
            f"shares its origins",
        )

    def test_the_upstream_walk_does_not_grow_exponentially_with_depth(self):
        calls = [self._count_upstream_calls(self._lattice(d, 2)[0]) for d in (6, 10)]
        self.assertLess(
            calls[1],
            3 * calls[0],
            f"depth 6 -> {calls[0]} calls, depth 10 -> {calls[1]}: four extra "
            f"levels must cost four levels of work, not sixteen times it",
        )

    def test_the_upstream_walk_still_reports_every_move_it_walked(self):
        top, layers = self._lattice(6, 2)
        walks = []

        original = type(self.Move)._walk_upstream_documents

        def recording(records, walk):
            walks.append(walk)
            return original(records, walk)

        with patch.object(type(self.Move), "_walk_upstream_documents", recording):
            top._get_upstream_documents_and_responsibles(self.Move)

        self.assertTrue(walks, "the walk must have entered at least once")
        walked = walks[0]["visited"]
        expected = self.Move.browse(
            [top.id, *[i for layer in layers[1:-1] for i in layer.ids]],
        )
        self.assertEqual(
            set(walked.ids),
            set(expected.ids),
            "every move with live origins that the walk entered must appear in "
            "`visited`, or the activity note under-reports the impacted transfers",
        )

    def test_a_plain_chain_costs_one_call_per_move(self):
        top, __ = self._lattice(20, 1)
        self.assertEqual(
            self._count_upstream_calls(top),
            20,
            "a chain with no shared origins has nothing to re-walk",
        )

    def test_dropping_short_moves_cancels_them_in_one_batch(self):
        products = self.env["product.product"].create(
            [{"name": f"drop-{i}", "is_storable": True} for i in range(12)],
        )
        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": self.wh.out_type_id.id,
                "location_id": self.stock.id,
                "location_dest_id": self.customer.id,
                "move_ids": [
                    Command.create(
                        {
                            "product_id": product.id,
                            "product_uom_qty": 5,
                            "location_id": self.stock.id,
                            "location_dest_id": self.customer.id,
                        },
                    )
                    for product in products
                ],
            },
        )
        picking.action_confirm()
        batches = []
        original = type(self.Move)._action_cancel

        def recording(records):
            batches.append(len(records))
            return original(records)

        with patch.object(type(self.Move), "_action_cancel", recording):
            picking.move_ids._action_done(cancel_backorder=True)

        self.assertTrue(batches, "the short moves must still be cancelled")
        self.assertEqual(
            max(batches),
            12,
            f"cancel batch sizes {batches}: _action_cancel is a batch method and "
            f"validating a short transfer must call it once, not once per line",
        )

    def test_generated_line_vals_survive_an_x2many_default(self):
        product = self._product("x2many-default", tracking="serial")
        MoveLine = self.env["stock.move.line"]
        x2many = next(
            name
            for name, field in MoveLine._fields.items()
            if field.type in ("one2many", "many2many")
        )
        vals_list = self.Move.action_generate_lot_line_vals(
            {
                "default_product_id": product.id,
                "default_tracking": "serial",
                "default_location_dest_id": self.stock.id,
                "default_picking_type_id": self.wh.in_type_id.id,
                f"default_{x2many}": [Command.set([])],
            },
            "generate",
            "SN001",
            2,
            "",
        )
        self.assertEqual(len(vals_list), 2)
        self.assertEqual(
            vals_list[0][x2many],
            [Command.set([])],
            f"{x2many} is not a many2one and must be passed through untouched, "
            f"not rewritten into an {{id, display_name}} pair",
        )

    def test_only_many2one_values_are_expanded_for_the_client(self):
        MoveLine = self.env["stock.move.line"]
        vals = [{"product_id": self.env["product.product"].search([], limit=1).id}]
        self.Move._format_move_line_vals_for_client(vals)
        self.assertEqual(sorted(vals[0]["product_id"]), ["display_name", "id"])
        expanded = {
            name for name, field in MoveLine._fields.items() if field.type == "many2one"
        }
        self.assertNotIn(
            "quantity",
            expanded,
            "sanity: a non-relational field is not in the expanded set",
        )

    def test_availability_reads_one_quantity_in_the_products_unit(self):
        dozens = self.env.ref("uom.product_uom_dozen")
        units = self.env.ref("uom.product_uom_unit")
        product = self._product(
            "coarse-uom",
            uom_id=dozens.id,
            uom_ids=[Command.set((units | dozens).ids)],
        )
        self.assertNotEqual(
            units._get_quantity_in_unit(7, dozens),
            units._get_quantity_stored(7, dozens),
            "sanity: this configuration is one where the two conversions differ",
        )
        origin = self._internal_move(product, 1, product_uom_id=dozens.id)
        following = self.Move.create(
            {
                "product_id": product.id,
                "product_uom_qty": 1,
                "product_uom_id": dozens.id,
                "location_id": self.wh.wh_output_stock_loc_id.id,
                "location_dest_id": self.customer.id,
                "picking_type_id": self.wh.out_type_id.id,
                "move_orig_ids": [Command.set(origin.ids)],
            },
        )
        (origin | following)._action_confirm(merge=False)
        line = self.env["stock.move.line"].create(
            {
                "move_id": origin.id,
                "product_id": product.id,
                "product_uom_id": units.id,
                "quantity": 7,
                "location_id": self.stock.id,
                "location_dest_id": self.wh.wh_output_stock_loc_id.id,
            },
        )
        origin.picked = True
        origin.state = "done"
        line.state = "done"
        self.env.flush_all()

        available = following._get_available_move_lines_in()
        self.assertEqual(
            sum(available.values()),
            line.quantity_product_uom,
            "the incoming half must read the same stored quantity the outgoing "
            "half and _deduct_own_lines read; _get_quantity_in_unit rounds coarser "
            "and the two are subtracted from each other",
        )

    def test_writing_lots_and_quantity_together_applies_lots_first(self):
        product = self._product("order-matters", tracking="lot")
        lots = self.env["stock.lot"].create(
            [{"name": f"OM{i}", "product_id": product.id} for i in range(2)],
        )
        for lot in lots:
            self.env["stock.quant"]._update_available_quantity(
                product,
                self.stock,
                5,
                lot_id=lot,
            )
        checked = self.Move._check_write_vals(
            {"quantity": 6, "lot_ids": [Command.set(lots.ids)]},
        )
        self.assertEqual(
            list(checked)[0],
            "lot_ids",
            "_check_write_vals must front lot_ids: its inverse queues `quantity` "
            "for recompute, so the order of vals decides the stored quantity",
        )

    def test_a_scrap_reports_only_the_moves_it_completed(self):
        product = self._product("scrap-return")
        inventory_loc = self.env["stock.location"].search(
            [("usage", "=", "inventory")],
            limit=1,
        )
        move = self.Move.create(
            {
                "product_id": product.id,
                "product_uom_qty": 0,
                "location_id": self.stock.id,
                "location_dest_id": inventory_loc.id,
                "picking_type_id": self.wh.int_type_id.id,
            },
        )
        move._action_confirm(merge=False)
        returned = move.with_context(is_scrap=True)._action_done()
        self.assertEqual(
            set(returned.mapped("state")) - {"done"},
            set(),
            "_action_done's return is what stock_account hands to "
            "_create_account_move; the scrap branch must promise the same set "
            "as the ordinary one",
        )

    def test_materialising_lots_follows_use_existing_lots(self):
        product = self._product("lot-naming", tracking="serial")
        creates_only = self.wh.in_type_id.copy(
            {
                "name": "creates only",
                "use_create_lots": True,
                "use_existing_lots": False,
                "sequence_code": "AUDCO",
            },
        )
        move = self.Move.new(
            {"product_id": product.id, "picking_type_id": creates_only.id}
        )
        self.assertFalse(
            move._is_lot_materialization_required(),
            "an operation type that only creates names keeps them as lot_name; "
            "the old spelling _can_create_lot read as use_create_lots and said "
            "the opposite of what it gates",
        )
