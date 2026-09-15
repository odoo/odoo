from datetime import timedelta

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged
from odoo.tools import DOMAIN_PREDICATES

from odoo.addons.stock.const import (
    CONTEXT_BLOCK_COMPLETING,
    CONTEXT_BLOCK_EXCLUDED_TYPES,
    INTERNAL_CONTEXT_FLAG,
    get_internal_payload,
    is_internal_flag,
    read_internal_payload,
)
from odoo.addons.stock.tests.common import TestStockCommon
from odoo.addons.stock.tools.reservation import QuantsCache, RemovalStrategy


@tagged("post_install", "-at_install")
class TestQuantDisplayName(TestStockCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Quant = cls.env["stock.quant"]
        cls.loc = (
            cls.env["stock.warehouse"]
            .search([("company_id", "=", cls.env.company.id)], limit=1)
            .lot_stock_id
        )
        cls.product = cls.env["product.product"].create(
            {"name": "qdn-product", "is_storable": True, "tracking": "lot"}
        )
        cls.lot = cls.env["stock.lot"].create(
            {"name": "QDN-LOT", "product_id": cls.product.id}
        )
        cls.quant = cls.Quant.create(
            {
                "product_id": cls.product.id,
                "location_id": cls.loc.id,
                "lot_id": cls.lot.id,
                "quantity": 1.0,
            }
        )

    def _both(self):
        return (
            self.quant.display_name,
            self.quant.with_context(formatted_display_name=True).display_name,
        )

    def test_display_name_does_not_depend_on_which_context_was_read_first(self):
        self.env.flush_all()
        self.env.invalidate_all()
        plain_first, formatted_after = self._both()
        self.env.invalidate_all()
        formatted_first = self.quant.with_context(
            formatted_display_name=True
        ).display_name
        plain_after = self.quant.display_name
        self.assertEqual(
            plain_first,
            plain_after,
            "the plain display_name must not change because a formatted read"
            " happened first in the same transaction",
        )
        self.assertEqual(
            formatted_after,
            formatted_first,
            "the formatted display_name must not change because a plain read"
            " happened first in the same transaction",
        )
        self.assertNotEqual(
            plain_first,
            formatted_first,
            "the fixture must actually distinguish the two renderings, or this"
            " test passes for the wrong reason",
        )

    def test_the_two_renderings_are_the_documented_ones(self):
        self.env.invalidate_all()
        self.assertEqual(
            self.quant.display_name, f"{self.loc.display_name} - {self.lot.name}"
        )
        self.env.invalidate_all()
        self.assertEqual(
            self.quant.with_context(formatted_display_name=True).display_name,
            f"{self.loc.name}\t--{self.lot.name}--",
        )

    def test_an_unsaved_quant_has_no_name_in_either_context(self):
        values = {"product_id": self.product.id, "location_id": self.loc.id}
        self.assertEqual(self.Quant.new(values).display_name, "")
        self.assertEqual(
            self.Quant.with_context(formatted_display_name=True)
            .new(values)
            .display_name,
            "",
            "an unsaved quant named itself after its location in the formatted"
            " branch only, because the guard sat inside the other one",
        )

    def test_a_formatted_read_does_not_poison_a_user_facing_error(self):
        self.env.user.group_ids = [(4, self.env.ref("stock.group_stock_user").id)]
        self.env.invalidate_all()
        self.quant.with_context(formatted_display_name=True).display_name
        line = {
            "product_id": self.product.id,
            "location_id": self.loc.id,
            "lot_id": self.lot.id,
            "inventory_quantity": 1.0,
        }
        with self.assertRaises(UserError) as caught:
            self.Quant.with_context(inventory_mode=True).create([line, dict(line)])
        message = str(caught.exception)
        self.assertNotIn(
            "\t", message, "the formatted rendering leaked into an error dialog"
        )
        self.assertIn(self.loc.display_name, message)


@tagged("post_install", "-at_install")
class TestQuantInventoryWrite(TestStockCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Quant = cls.env["stock.quant"]
        cls.inventory_loc = cls.env["stock.location"].search(
            [("usage", "=", "inventory")], limit=1
        )
        cls.product = cls.env["product.product"].create(
            {"name": "qiw-product", "is_storable": True}
        )
        cls.quant = cls.Quant.create(
            {
                "product_id": cls.product.id,
                "location_id": cls.inventory_loc.id,
                "quantity": 3.0,
            }
        )
        cls.env.user.group_ids = [(4, cls.env.ref("stock.group_stock_user").id)]

    def test_a_forbidden_field_does_not_take_the_permitted_ones_with_it(self):
        self.quant.with_context(inventory_mode=True).write(
            {"inventory_quantity": 99.0, "product_id": self.product.id}
        )
        self.env.flush_all()
        self.quant.invalidate_recordset()
        self.assertEqual(
            self.quant.inventory_quantity,
            99.0,
            "the counted quantity is the one thing inventory mode exists to"
            " set; a rejected product_id beside it must not discard it",
        )

    def test_the_forbidden_field_is_still_refused(self):
        other = self.env["product.product"].create(
            {"name": "qiw-other", "is_storable": True}
        )
        self.quant.with_context(inventory_mode=True).write(
            {"inventory_quantity": 5.0, "product_id": other.id}
        )
        self.env.flush_all()
        self.quant.invalidate_recordset()
        self.assertEqual(self.quant.product_id, self.product)

    def test_a_forbidden_only_write_is_still_a_silent_no_op(self):
        owner = self.env["res.partner"].create({"name": "qiw-owner"})
        self.assertTrue(
            self.quant.with_context(inventory_mode=True).write({"owner_id": owner.id})
        )
        self.env.invalidate_all()
        self.assertFalse(self.quant.owner_id)

    def test_the_import_path_no_longer_discards_the_count(self):
        self.quant._load_records_write(
            {"inventory_quantity": 42.0, "location_id": self.inventory_loc.id}
        )
        self.env.flush_all()
        self.quant.invalidate_recordset()
        self.assertEqual(
            self.quant.inventory_quantity,
            42.0,
            "_load_records_write forces inventory_mode, so a data file that"
            " names the location alongside the count lost the count",
        )

    def test_an_internal_location_still_raises(self):
        loc = (
            self.env["stock.warehouse"]
            .search([("company_id", "=", self.env.company.id)], limit=1)
            .lot_stock_id
        )
        quant = self.Quant.create(
            {
                "product_id": self.product.id,
                "location_id": loc.id,
                "quantity": 1.0,
            }
        )
        with self.assertRaises(UserError):
            quant.with_context(inventory_mode=True).write(
                {"product_id": self.product.id}
            )


@tagged("post_install", "-at_install")
class TestQuantDormancyBounds(TestStockCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Quant = cls.env["stock.quant"]
        cls.loc = (
            cls.env["stock.warehouse"]
            .search([("company_id", "=", cls.env.company.id)], limit=1)
            .lot_stock_id
        )

    def _quant_aged(self, **delta):
        product = self.env["product.product"].create(
            {"name": "qdb-%s" % len(delta), "is_storable": True}
        )
        quant = self.Quant.create(
            {"product_id": product.id, "location_id": self.loc.id, "quantity": 1.0}
        )
        self.env.flush_all()
        quant.sudo().write({"in_date": fields.Datetime.now() - timedelta(**delta)})
        self.env.flush_all()
        quant.invalidate_recordset()
        return quant

    def test_a_fractional_bound_snaps_the_way_the_comparison_does(self):
        quant = self._quant_aged(days=1, hours=2)
        self.assertEqual(quant.days_since_last_movement, 1)
        for bound in (1, 1.5, 2):
            with self.subTest(bound=bound):
                matched = quant in self.Quant.search(
                    [
                        ("id", "=", quant.id),
                        ("days_since_last_movement", ">=", bound),
                    ]
                )
                self.assertEqual(
                    matched,
                    quant.days_since_last_movement >= bound,
                    "the search must agree with the compute; int() truncation"
                    " made >= 1.5 match a quant sitting at 1 day",
                )

    def test_an_integer_bound_is_unchanged_on_every_operator(self):
        quant = self._quant_aged(days=5, hours=1)
        self.assertEqual(quant.days_since_last_movement, 5)
        for operator in (">=", ">", "<=", "<"):
            for bound in (4, 5, 6):
                with self.subTest(operator=operator, bound=bound):
                    matched = quant in self.Quant.search(
                        [
                            ("id", "=", quant.id),
                            ("days_since_last_movement", operator, bound),
                        ]
                    )
                    self.assertEqual(
                        matched,
                        DOMAIN_PREDICATES[operator](
                            quant.days_since_last_movement, bound
                        ),
                    )

    def test_elapsed_days_never_run_backwards(self):
        quant = self._quant_aged(days=-10)
        self.assertGreaterEqual(
            quant.days_since_last_movement,
            0,
            "an in_date ahead of now reported a negative duration on a field"
            " whose name and help both promise elapsed time",
        )


@tagged("post_install", "-at_install")
class TestQuantRemovalStrategySeam(TestStockCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Quant = cls.env["stock.quant"]

    def test_every_selectable_strategy_resolves_to_one_object(self):
        methods = self.env["product.removal"].search([]).mapped("method")
        self.assertIn("fifo", methods, "the data strategies must be installed")
        location = (
            self.env["stock.warehouse"]
            .search([("company_id", "=", self.env.company.id)], limit=1)
            .lot_stock_id
        )
        product = self.env["product.product"].create(
            {"name": "qsh-order", "is_storable": True}
        )
        quants = self.Quant.create(
            [
                {
                    "product_id": product.id,
                    "location_id": location.id,
                    "quantity": 1.0 + index,
                }
                for index in range(3)
            ]
        )
        self.env.flush_all()
        for method in sorted(set(methods)):
            with self.subTest(removal_strategy=method):
                strategy = self.Quant._get_removal_strategy_record(method)
                self.assertIsInstance(
                    strategy,
                    RemovalStrategy,
                    "a strategy an addon added resolved to None, so _gather read"
                    " both of its behaviour flags as False without saying so",
                )
                self.assertEqual(
                    strategy.order, self.Quant._get_removal_strategy_order(method)
                )
                through_accessor = self.Quant._get_removal_strategy_sort_key(method)
                self.assertEqual(
                    strategy.resolve_sorted_arguments()[1], through_accessor[1]
                )
                self.assertEqual(
                    quants.sorted(*strategy.resolve_sorted_arguments()).ids,
                    quants.sorted(*through_accessor).ids,
                    "the table and the accessor must order the same quants the"
                    " same way",
                )

    def test_the_table_is_the_seam_and_carries_the_behaviour_flags(self):
        registry_cls = type(self.Quant)
        base = registry_cls._get_removal_strategies

        def patched(records):
            strategies = base(records)
            strategies["qsh_byloc"] = RemovalStrategy(
                order=False, sort_key=lambda quant: quant.id, sorts_by_location=True
            )
            return strategies

        registry_cls._get_removal_strategies = patched
        try:
            strategy = self.Quant._get_removal_strategy_record("qsh_byloc")
            self.assertTrue(
                strategy.sorts_by_location,
                "extending the table must be enough to reach the flags",
            )
            self.assertIs(self.Quant._get_removal_strategy_order("qsh_byloc"), False)
            self.assertIsNotNone(self.Quant._get_removal_strategy_sort_key("qsh_byloc"))
        finally:
            registry_cls._get_removal_strategies = base

    def test_an_accessor_only_override_still_resolves(self):
        registry_cls = type(self.Quant)
        base_order = registry_cls._get_removal_strategy_order
        base_key = registry_cls._get_removal_strategy_sort_key

        def order(records, removal_strategy):
            if removal_strategy == "qsh_legacy":
                return "in_date DESC, id"
            return base_order(records, removal_strategy)

        def key(records, removal_strategy):
            if removal_strategy == "qsh_legacy":
                return (lambda quant: quant.id), True
            return base_key(records, removal_strategy)

        registry_cls._get_removal_strategy_order = order
        registry_cls._get_removal_strategy_sort_key = key
        try:
            strategy = self.Quant._get_removal_strategy_record("qsh_legacy")
            self.assertEqual(strategy.order, "in_date DESC, id")
            self.assertTrue(strategy.reverse)
            self.assertFalse(strategy.narrows_to_packages)
        finally:
            registry_cls._get_removal_strategy_order = base_order
            registry_cls._get_removal_strategy_sort_key = base_key

    def test_an_unknown_strategy_still_names_itself(self):
        with self.assertRaises(UserError):
            self.Quant._get_removal_strategy_record("qsh_nonexistent")

    def test_the_table_is_a_copy_not_the_shared_constant(self):
        first = self.Quant._get_removal_strategies()
        first["qsh_scribble"] = None
        self.assertNotIn(
            "qsh_scribble",
            self.Quant._get_removal_strategies(),
            "an override that adds an entry must not mutate the module constant",
        )


@tagged("post_install", "-at_install")
class TestQuantBlockedContextProtocol(TestStockCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Quant = cls.env["stock.quant"]

    def test_the_payload_round_trips_through_the_shared_helpers(self):
        context = {CONTEXT_BLOCK_EXCLUDED_TYPES: get_internal_payload(("soft_out",))}
        self.assertEqual(
            read_internal_payload(context, CONTEXT_BLOCK_EXCLUDED_TYPES),
            ("soft_out",),
        )

    def test_an_empty_payload_is_distinguishable_from_an_absent_one(self):
        context = {CONTEXT_BLOCK_EXCLUDED_TYPES: get_internal_payload(())}
        self.assertEqual(
            read_internal_payload(context, CONTEXT_BLOCK_EXCLUDED_TYPES), ()
        )
        self.assertIsNone(read_internal_payload({}, CONTEXT_BLOCK_EXCLUDED_TYPES))

    def test_a_forged_payload_is_refused(self):
        for forged in ((True, ["soft_out"]), ["soft_out"], "soft_out", True):
            with self.subTest(forged=forged):
                self.assertIsNone(
                    read_internal_payload(
                        {CONTEXT_BLOCK_EXCLUDED_TYPES: forged},
                        CONTEXT_BLOCK_EXCLUDED_TYPES,
                    ),
                    "only a value written by get_internal_payload() may be trusted",
                )

    def test_the_two_shapes_stay_distinct(self):
        flagged = {CONTEXT_BLOCK_COMPLETING: INTERNAL_CONTEXT_FLAG}
        self.assertTrue(is_internal_flag(flagged, CONTEXT_BLOCK_COMPLETING))
        self.assertIsNone(
            read_internal_payload(flagged, CONTEXT_BLOCK_COMPLETING),
            "a bare marker carries no payload and must not read as one",
        )
        carried = {CONTEXT_BLOCK_EXCLUDED_TYPES: get_internal_payload(())}
        self.assertFalse(
            is_internal_flag(carried, CONTEXT_BLOCK_EXCLUDED_TYPES),
            "a payload is deliberately not a bare marker",
        )

    def test_the_model_uses_the_shared_protocol(self):
        scoped = self.Quant._with_block_gather_context()
        self.assertEqual(
            scoped._get_block_types_excluded(),
            read_internal_payload(scoped.env.context, CONTEXT_BLOCK_EXCLUDED_TYPES),
        )
        self.assertIsNone(self.Quant._get_block_types_excluded())


@tagged("post_install", "-at_install")
class TestQuantContracts(TestStockCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Quant = cls.env["stock.quant"]
        cls.loc = (
            cls.env["stock.warehouse"]
            .search([("company_id", "=", cls.env.company.id)], limit=1)
            .lot_stock_id
        )

    def test_action_view_orderpoints_names_the_quant_when_given_several(self):
        products = self.env["product.product"].create(
            [{"name": f"qc-avo-{i}", "is_storable": True} for i in range(2)]
        )
        quants = self.Quant.create(
            [
                {"product_id": p.id, "location_id": self.loc.id, "quantity": 1.0}
                for p in products
            ]
        )
        with self.assertRaises(ValueError) as caught:
            quants.action_view_orderpoints()
        self.assertIn(
            "stock.quant",
            str(caught.exception),
            "the guard must name the receiver, not whatever field it read first",
        )
        self.assertTrue(quants[0].action_view_orderpoints())

    def test_the_serial_check_is_private(self):
        self.assertFalse(
            hasattr(self.Quant, "check_quantity"),
            "check_quantity had one caller -- stock.move._check_quantity -- and"
            " no XML reference, so a public spelling only widens the API",
        )
        self.assertTrue(hasattr(self.Quant, "_check_quantity"))

    def test_the_create_allowlist_holds_only_settable_fields(self):
        for name in self.Quant._get_inventory_fields_create():
            if name.startswith("x_"):
                continue
            field = self.Quant._fields[name]
            with self.subTest(field=name):
                self.assertTrue(
                    field.store or field.inverse,
                    f"{name} can never be persisted, so permitting it at create"
                    f" only widens the allowlist",
                )

    def test_the_aggregate_barcode_follows_the_order_it_was_given(self):
        self.env["ir.config_parameter"].sudo().set_param("stock.barcode_separator", ";")
        products = self.env["product.product"].create(
            [
                {
                    "name": f"qc-agg-{i}",
                    "is_storable": True,
                    "tracking": "serial",
                    "barcode": f"QCAGG-P{i}",
                }
                for i in range(2)
            ]
        )
        quants = self.Quant
        for index, product in enumerate(products):
            for suffix in range(2):
                lot = self.env["stock.lot"].create(
                    {"name": f"qcagg-{index}{suffix}", "product_id": product.id}
                )
                quants |= self.Quant.create(
                    {
                        "product_id": product.id,
                        "location_id": self.loc.id,
                        "lot_id": lot.id,
                        "quantity": 1.0,
                    }
                )
        self.env.flush_all()
        grouped = quants.get_aggregate_barcodes()[0]
        self.assertEqual(
            grouped.count("QCAGG-P0"),
            1,
            "a product barcode is written once per contiguous run of its quants",
        )
        interleaved = self.Quant.browse(
            [quants[0].id, quants[2].id, quants[1].id, quants[3].id]
        ).get_aggregate_barcodes()[0]
        self.assertEqual(
            interleaved.count("QCAGG-P0"),
            2,
            "an interleaved recordset repeats the product barcode -- the caller"
            " owns the order, and this is the documented consequence of not"
            " grouping by product before calling",
        )
        self.assertLess(
            grouped.index("qcagg-01"),
            grouped.index("QCAGG-P1"),
            "the emitted sequence must follow the recordset, not a re-sort",
        )

    def test_the_reservation_lock_follows_the_removal_order(self):
        lifo = self.env["product.removal"].search([("method", "=", "lifo")], limit=1)
        category = self.env["product.category"].create(
            {"name": "qc-lifo", "removal_strategy_id": lifo.id}
        )
        product = self.env["product.product"].create(
            {"name": "qc-lifo-product", "is_storable": True, "categ_id": category.id}
        )
        older = self.Quant.create(
            {"product_id": product.id, "location_id": self.loc.id, "quantity": 1.0}
        )
        self.env.flush_all()
        newer = self.Quant.create(
            {"product_id": product.id, "location_id": self.loc.id, "quantity": 1.0}
        )
        self.env.flush_all()
        older.sudo().in_date = "2020-01-01 00:00:00"
        newer.sudo().in_date = "2025-01-01 00:00:00"
        self.env.flush_all()
        gathered = self.Quant.sudo()._gather(product, self.loc, strict=True)
        self.assertEqual(
            gathered.ids[0],
            newer.id,
            "LIFO must gather the newest quant first, or the rest of this test"
            " is asserting nothing",
        )
        self.assertEqual(
            gathered._lock_one_for_reservation(0).ids,
            [newer.id],
            "the lock takes the first row of the RECORDSET, which is the"
            " removal-strategy order; if _as_query ever stopped preserving that"
            " order, reservation would silently move to the lowest id",
        )


@tagged("post_install", "-at_install")
class TestQuantsCacheScope(TransactionCase):
    def _cache(self, roots, products=(7,)):
        return QuantsCache(self.env["stock.quant"], products, roots)

    def test_a_descendant_is_covered_and_the_location_itself_is(self):
        cache = self._cache(["1/2/"])
        self.assertTrue(cache.is_covering(_Stub(7), _Stub(2, "1/2/")))
        self.assertTrue(cache.is_covering(_Stub(7), _Stub(99, "1/2/99/")))

    def test_a_sibling_whose_id_is_a_decimal_prefix_is_not_covered(self):
        cache = self._cache(["1/2/"])
        self.assertFalse(
            cache.is_covering(_Stub(7), _Stub(20, "1/20/")),
            "a sibling location must never be served from another's cache",
        )
        stripped = self._cache(["1/2"])
        self.assertTrue(
            stripped.is_covering(_Stub(7), _Stub(20, "1/20/")),
            "this asserts the FAILURE mode on purpose: without the trailing"
            " slash the sibling is covered, which is why the roots must always"
            " come from parent_path verbatim",
        )

    def test_the_roots_come_from_parent_path_verbatim(self):
        location = (
            self.env["stock.warehouse"]
            .search([("company_id", "=", self.env.company.id)], limit=1)
            .lot_stock_id
        )
        self.assertTrue(
            location.parent_path.endswith("/"),
            "parent_path is what QuantsCache scopes on; without the trailing"
            " slash its prefix test admits siblings",
        )
        cache = self.env["stock.quant"]._get_quants_by_products_locations(
            self.env["product.product"].browse(), location
        )
        self.assertEqual(cache._location_paths, (location.parent_path,))

    def test_an_unsaved_location_is_never_covered(self):
        cache = self._cache(["1/2/"])
        self.assertFalse(cache.is_covering(_Stub(7), _Stub(0, False)))

    def test_a_cache_with_no_usable_root_covers_nothing(self):
        cache = self._cache([False, "", None])
        self.assertEqual(cache._location_paths, ())
        self.assertFalse(cache.is_covering(_Stub(7), _Stub(2, "1/2/")))


class _Stub:
    __slots__ = ("id", "parent_path")

    def __init__(self, id_, parent_path=None):
        self.id = id_
        self.parent_path = parent_path
