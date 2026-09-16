from psycopg import IntegrityError

from odoo.exceptions import UserError
from odoo.tools import mute_logger

from odoo.addons.uom.tests.common import UomCommon


class TestUom(UomCommon):
    def test_10_conversion(self):
        qty = self.uom_gram._get_quantity_in_unit(1020000, self.uom_ton)
        self.assertEqual(qty, 1.02, "Converted quantity does not correspond.")

        price = self.uom_gram._get_price_in_unit(2, self.uom_ton)
        self.assertEqual(price, 2000000.0, "Converted price does not correspond.")

        # If the conversion factor for Dozens (1/12) is not stored with sufficient precision,
        # the conversion of 1 Dozen into Units will give e.g. 12.00000000000047 Units
        # and the Unit rounding will round that up to 13.
        # This is a partial regression test for rev. 311c77bb, which is further improved
        # by rev. fa2f7b86.
        qty = self.uom_dozen._get_quantity_in_unit(1, self.uom_unit)
        self.assertEqual(qty, 12.0, "Converted quantity does not correspond.")

        # Regression test for side-effect of commit 311c77bb - converting 1234 Grams
        # into Kilograms should work even if grams are rounded to 1.
        qty = self.uom_gram._get_quantity_in_unit(1234, self.uom_kgm)
        self.assertEqual(qty, 1.24, "Converted quantity does not correspond.")

    def test_20_rounding(self):
        product_uom_id = self.env["uom.uom"].create(
            {
                "name": "Score",
                "relative_factor": 20,
                "relative_uom_id": self.uom_unit.id,
            }
        )
        self.env["decimal.precision"].search([("name", "=", "Product Unit")]).digits = 0

        qty = self.uom_unit._get_quantity_in_unit(2, product_uom_id)
        self.assertEqual(qty, 1, "Converted quantity should be rounded up.")

    def test_30_quantity(self):
        """_round_to_packaging_multiple rounds the available quantity of a
        product. To prevent rounding issues there should be no rounding when
        the product uom is the same as the package uom.
        """
        uom = self.uom_unit
        quantity = 22.43
        rounding_method = "DOWN"

        result = self.uom_unit._round_to_packaging_multiple(
            quantity, uom, rounding_method
        )

        self.assertEqual(result, quantity, "Quantity should not be rounded.")

    def test_round_to_packaging_multiple_multiples(self):
        """_round_to_packaging_multiple must round to exact multiples of the packaging, without
        distortion from pre-rounding the packaging factor (12 Units used to
        come back as 11.97 because 1/12 was rounded to 0.09 first)."""
        # 12 dozens = 144 units: already a whole multiple of one Unit
        self.assertEqual(
            self.uom_unit._round_to_packaging_multiple(12, self.uom_dozen), 12.0
        )
        self.assertEqual(
            self.uom_unit._round_to_packaging_multiple(11, self.uom_dozen, "DOWN"), 11.0
        )
        # 1.04 dozen = 12.48 units -> 12 units (DOWN) / 13 units (UP)
        self.assertEqual(
            self.uom_unit._round_to_packaging_multiple(1.04, self.uom_dozen, "DOWN"),
            1.0,
        )
        self.assertEqual(
            self.uom_unit._round_to_packaging_multiple(1.04, self.uom_dozen, "UP"), 1.08
        )
        # packaging expressed in the product uom (stock reservation direction)
        pack_6 = self.quick_ref("uom.product_uom_pack_6")
        self.assertEqual(
            pack_6._round_to_packaging_multiple(14, self.uom_unit, "DOWN"), 12.0
        )
        self.assertEqual(
            pack_6._round_to_packaging_multiple(14, self.uom_unit, "UP"), 18.0
        )

    def test_minute_hour_roundtrip(self):
        """The Minutes factor must be exactly 1/60: with the historical
        0.0166667, 60 minutes converted (rounding UP) to 1.01 hours."""
        uom_minute = self.quick_ref("uom.product_uom_minute")
        self.assertEqual(uom_minute._get_quantity_in_unit(60, self.uom_hour), 1.0)
        self.assertEqual(self.uom_hour._get_quantity_in_unit(1, uom_minute), 60.0)

    def test_cross_reference_conversion(self):
        """Converting between units without a common reference unit raises,
        unless the caller opts out with raise_if_failure=False."""
        self.assertFalse(self.uom_gram._has_common_reference(self.uom_hour))
        self.assertTrue(self.uom_gram._has_common_reference(self.uom_ton))
        self.assertTrue(self.uom_gram._has_common_reference(self.uom_gram))

        with self.assertRaises(UserError):
            self.uom_gram._get_quantity_in_unit(1000, self.uom_hour)
        self.assertEqual(
            self.uom_gram._get_quantity_in_unit(
                1000, self.uom_hour, raise_if_failure=False
            ),
            1000,
            "Failed conversions must return the initial quantity",
        )

    def test_compute_quantity_wrappers_degrade(self):
        """The report/estimate/reconcile wrappers force raise_if_failure=False:
        incompatible UoMs return the unconverted quantity, and the opt-out
        cannot be overridden by a caller passing raise_if_failure=True."""
        self.assertFalse(self.uom_gram._has_common_reference(self.uom_hour))
        for wrapper in (
            self.uom_gram._get_quantity_report,
            self.uom_gram._get_quantity_estimate,
            self.uom_gram._get_quantity_reconcile,
        ):
            with self.subTest(wrapper=wrapper.__name__):
                self.assertEqual(
                    wrapper(1000, self.uom_hour),
                    1000,
                    "Incompatible conversion must return the initial quantity",
                )
                self.assertEqual(
                    wrapper(1000, self.uom_hour, raise_if_failure=True),
                    1000,
                    "The forced opt-out must not be overridable by the caller",
                )

    def test_compute_quantity_wrappers_forward_kwargs(self):
        """The wrappers forward round/rounding_method through to the base
        _get_quantity_in_unit. Uses the same controlled setup as test_20_rounding
        (Product Unit precision 0 + a Score unit worth 20 units) so the
        assertions do not depend on the reference UoMs' stored rounding."""
        self.env["decimal.precision"].search([("name", "=", "Product Unit")]).digits = 0
        score = self.env["uom.uom"].create(
            {
                "name": "Score",
                "relative_factor": 20,
                "relative_uom_id": self.uom_unit.id,
            }
        )
        for wrapper_name in (
            "_get_quantity_report",
            "_get_quantity_estimate",
            "_get_quantity_reconcile",
        ):
            with self.subTest(wrapper=wrapper_name):
                wrapper = getattr(self.uom_unit, wrapper_name)
                # 2 units = 0.1 score: round=False keeps 0.1, default rounds up to 1
                self.assertEqual(
                    wrapper(2, score, round=False),
                    self.uom_unit._get_quantity_in_unit(2, score, round=False),
                )
                self.assertNotEqual(
                    wrapper(2, score, round=False),
                    wrapper(2, score),
                    "round=False must differ from the rounded default",
                )
                # rounding_method forwarded: DOWN rounds 0.1 score to 0, matching base
                self.assertEqual(
                    wrapper(2, score, rounding_method="DOWN"),
                    self.uom_unit._get_quantity_in_unit(
                        2, score, rounding_method="DOWN"
                    ),
                )

    def test_compute_quantity_wrappers_match_base_for_compatible(self):
        """For compatible UoMs the wrappers are byte-identical to the base
        _get_quantity_in_unit — they only differ when conversion is impossible."""
        cases = [
            (self.uom_gram, 1020000, self.uom_ton),
            (self.uom_dozen, 1, self.uom_unit),
        ]
        for wrapper_name in (
            "_get_quantity_report",
            "_get_quantity_estimate",
            "_get_quantity_reconcile",
        ):
            for src, qty, dst in cases:
                with self.subTest(wrapper=wrapper_name, src=src.name, dst=dst.name):
                    self.assertEqual(
                        getattr(src, wrapper_name)(qty, dst),
                        src._get_quantity_in_unit(qty, dst),
                    )

    def test_get_quantity_reconcile_strict_posting_context(self):
        """`_get_quantity_reconcile` degrades while an order is browsed but
        escalates to a raising conversion under the `uom_reconcile_strict`
        context, so a delivered/received quantity is never posted unconverted.
        Only the reconcile wrapper escalates — report/estimate stay lenient."""
        self.assertFalse(self.uom_gram._has_common_reference(self.uom_hour))
        # Default (browse): degrades to the unconverted quantity.
        self.assertEqual(
            self.uom_gram._get_quantity_reconcile(1000, self.uom_hour),
            1000,
        )
        # Posting boundary: escalates to strict and raises.
        with self.assertRaises(UserError):
            self.uom_gram.with_context(
                uom_reconcile_strict=True
            )._get_quantity_reconcile(1000, self.uom_hour)
        # A caller-passed raise_if_failure=False cannot re-open the escape hatch
        # once the posting context asked for strictness.
        with self.assertRaises(UserError):
            self.uom_gram.with_context(
                uom_reconcile_strict=True
            )._get_quantity_reconcile(1000, self.uom_hour, raise_if_failure=False)
        # The escalation is reconcile-only: report/estimate still degrade.
        for wrapper in ("_get_quantity_report", "_get_quantity_estimate"):
            with self.subTest(wrapper=wrapper):
                self.assertEqual(
                    getattr(
                        self.uom_gram.with_context(uom_reconcile_strict=True), wrapper
                    )(1000, self.uom_hour),
                    1000,
                    "Only the reconcile wrapper escalates under posting context",
                )

    def test_conversion_degenerate_recordsets(self):
        empty_uom = self.env["uom.uom"]
        self.assertEqual(empty_uom._get_quantity_in_unit(5.0, self.uom_gram), 5.0)
        self.assertEqual(self.uom_gram._get_quantity_in_unit(5.0, empty_uom), 5.0)
        self.assertEqual(self.uom_gram._get_quantity_in_unit(0.0, self.uom_ton), 0.0)

    def test_compute_price(self):
        self.assertEqual(self.uom_gram._get_price_in_unit(5.0, self.uom_gram), 5.0)
        self.assertEqual(self.uom_gram._get_price_in_unit(0.0, self.uom_ton), 0.0)
        self.assertEqual(self.uom_ton._get_price_in_unit(2000000.0, self.uom_gram), 2.0)
        self.assertEqual(
            self.uom_gram._get_price_in_unit(5.0, self.env["uom.uom"]), 5.0
        )

    def test_factor_must_be_strictly_positive(self):
        for factor in (0, -5):
            with (
                self.subTest(factor=factor),
                mute_logger("odoo.db"),
                self.assertRaises(IntegrityError),
                self.cr.savepoint(),
            ):
                self.env["uom.uom"].create(
                    {
                        "name": "Broken",
                        "relative_factor": factor,
                        "relative_uom_id": self.uom_unit.id,
                    }
                )

    def test_reference_uom_must_have_factor_one(self):
        with self.assertRaises(UserError):
            self.env["uom.uom"].create(
                {
                    "name": "Rootless",
                    "relative_factor": 2.0,
                }
            )

    def test_recursive_reference_rejected(self):
        pack_6 = self.quick_ref("uom.product_uom_pack_6")
        with self.assertRaises(UserError), self.cr.savepoint():
            self.uom_unit.relative_uom_id = pack_6

    def test_protected_uom_unlink(self):
        with self.assertRaises(UserError):
            self.uom_kgm.unlink()

    def test_unlink_cannot_cascade_onto_protected_children(self):
        """Hours is deliberately unprotected, but Days and Minutes are defined
        against it and *are* protected. `relative_uom_id` is ON DELETE CASCADE,
        so deleting Hours used to take both with it without either passing
        through `unlink()` -- leaving their `ir.model.data` rows dangling, so
        `env.ref("uom.product_uom_day")` raised for every module built on it.
        """
        hour = self.quick_ref("uom.product_uom_hour")
        day = self.quick_ref("uom.product_uom_day")
        minute = self.quick_ref("uom.product_uom_minute")
        self.assertFalse(hour._filter_protected_uoms(), "Hours is unprotected")
        self.assertEqual(day | minute, (day | minute)._filter_protected_uoms())

        with self.assertRaises(UserError):
            hour.unlink()

        # Nothing was removed, and the xml ids still resolve.
        self.assertTrue(day.exists() and minute.exists())
        self.assertEqual(self.env.ref("uom.product_uom_day"), day)
        self.assertEqual(self.env.ref("uom.product_uom_minute"), minute)

    def test_unlink_cannot_silently_take_descendants(self):
        """Deleting a user-made reference unit used to cascade-delete the whole
        family defined against it, with no warning and no way to notice."""
        root = self.env["uom.uom"].create({"name": "Root", "relative_factor": 1})
        mid = self.env["uom.uom"].create(
            {"name": "Mid", "relative_factor": 10, "relative_uom_id": root.id}
        )
        leaf = self.env["uom.uom"].create(
            {"name": "Leaf", "relative_factor": 10, "relative_uom_id": mid.id}
        )

        with self.assertRaises(UserError):
            root.unlink()
        self.assertTrue((mid | leaf).exists())

        # Deleting the family explicitly is unambiguous, so it stays allowed.
        (root | mid | leaf).unlink()
        self.assertFalse((root | mid | leaf).exists())

    def test_unlink_descendant_check_sees_archived_children(self):
        """An archived child is cascade-deleted exactly like an active one, so
        the guard must look for it with `active_test=False`."""
        root = self.env["uom.uom"].create({"name": "ARoot", "relative_factor": 1})
        child = self.env["uom.uom"].create(
            {
                "name": "AChild",
                "relative_factor": 4,
                "relative_uom_id": root.id,
                "active": False,
            }
        )
        with self.assertRaises(UserError):
            root.unlink()
        self.assertTrue(child.exists())

    def test_unlink_leaf_is_still_allowed(self):
        """The guard must not turn into a blanket ban: a unit nothing is
        defined against is still deletable."""
        leaf = self.env["uom.uom"].create(
            {
                "name": "Lonely",
                "relative_factor": 3,
                "relative_uom_id": self.uom_unit.id,
            }
        )
        leaf.unlink()
        self.assertFalse(leaf.exists())

    def test_sequence_defaults(self):
        uom = self.env["uom.uom"].create(
            {
                "name": "Triple",
                "relative_factor": 3,
                "relative_uom_id": self.uom_unit.id,
            }
        )
        self.assertEqual(uom.sequence, 300)
        uom.relative_factor = 5
        self.assertEqual(uom.sequence, 300, "An existing sequence must be preserved")
        big = self.env["uom.uom"].create(
            {
                "name": "Big",
                "relative_factor": 5000,
                "relative_uom_id": self.uom_unit.id,
            }
        )
        self.assertEqual(big.sequence, 1000, "Sequence is capped at 1000")

    def test_factor_chain(self):
        """`factor` is the product of relative factors up to the reference unit
        and follows updates anywhere in the chain."""
        self.assertEqual(self.uom_ton.factor, 1000000.0)
        kiloton = self.env["uom.uom"].create(
            {
                "name": "Kiloton",
                "relative_factor": 1000,
                "relative_uom_id": self.uom_ton.id,
            }
        )
        self.assertEqual(kiloton.factor, 1e9)
        self.uom_kgm.relative_factor = 500
        self.assertEqual(kiloton.factor, 5e8, "Factor must follow chain updates")

    def test_compare_and_is_zero_accept_an_unset_unit(self):
        """Both round at the 'Product Unit' precision and never read the unit, so an
        empty recordset is a legitimate receiver -- callers compare quantities on
        records whose unit is not resolved yet (a new orderpoint built from a list
        view's defaults has no product, hence no unit, and all-zero quantities).
        """
        no_uom = self.env["uom.uom"]
        self.assertEqual(no_uom.compare(0.0, 0.0), 0)
        self.assertEqual(no_uom.compare(2.0, 1.0), 1)
        self.assertEqual(no_uom.compare(1.0, 2.0), -1)
        self.assertTrue(no_uom.is_zero(0.0))
        self.assertFalse(no_uom.is_zero(1.0))
        # ...and the answer is identical to the one a real unit gives, since the
        # unit is not part of the computation.
        for value1, value2 in ((0.0, 0.0), (2.0, 1.0), (1.0, 2.0), (1.0, 1.0)):
            self.assertEqual(
                no_uom.compare(value1, value2),
                self.uom_unit.compare(value1, value2),
            )

    def test_compare_still_rejects_several_units(self):
        """An ambiguous receiver stays a caller error."""
        several = self.uom_unit | self.uom_dozen
        with self.assertRaises(ValueError):
            several.compare(1.0, 2.0)
        with self.assertRaises(ValueError):
            several.is_zero(0.0)

    def test_rounding_follows_the_precision_within_a_transaction(self):
        """`rounding` is a compute with no `@api.depends` (it reads a
        `decimal.precision` row, not a field), so nothing invalidated it when
        the precision changed. A cached `rounding` then disagreed with
        `get_precision` for the rest of the transaction: `_get_quantity_in_unit`
        (reads `rounding`) and `round` (reads the precision) returned different
        numbers for the same input, and which one you got depended on whether
        the unit was already in cache.
        """
        precision = self.env["decimal.precision"].search(
            [("name", "=", "Product Unit")]
        )
        # Warm the cache at the current precision, as any earlier read would.
        self.assertEqual(self.uom_unit.rounding, 0.01)

        precision.digits = 4

        self.assertEqual(self.uom_unit.rounding, 0.0001)
        self.assertEqual(self.uom_unit._precision_digits(), 4)
        self.assertEqual(self.uom_unit.round(1.234567), 1.2346)
        # The two paths agree: both round at 4 digits now.
        self.assertEqual(
            self.uom_gram._get_quantity_in_unit(1234.5678, self.uom_kgm), 1.2346
        )

    def test_has_common_reference_accepts_an_unset_unit(self):
        """An unset unit shares a reference with nothing -- including another
        unset one. It is not a caller error: the call sites reach a
        `product_uom_id`/`uom_id` that is legitimately empty on a half-filled
        record, and each had to pre-guard to avoid a bare ValueError."""
        no_uom = self.env["uom.uom"]
        self.assertFalse(self.uom_gram._has_common_reference(no_uom))
        self.assertFalse(no_uom._has_common_reference(self.uom_gram))
        self.assertFalse(no_uom._has_common_reference(no_uom))
        # More than one unit stays ambiguous, hence still an error.
        several = self.uom_unit | self.uom_dozen
        with self.assertRaises(ValueError):
            several._has_common_reference(self.uom_gram)
        with self.assertRaises(ValueError):
            self.uom_gram._has_common_reference(several)

    def test_compute_price_accepts_an_unset_unit(self):
        """`_compute_price` `check_singleton()`d before its degenerate-input guard,
        so an unset source unit raised where `_get_quantity_in_unit` returned
        quietly. The two are now symmetric."""
        no_uom = self.env["uom.uom"]
        self.assertEqual(no_uom._get_price_in_unit(5.0, self.uom_gram), 5.0)
        self.assertEqual(self.uom_gram._get_price_in_unit(5.0, no_uom), 5.0)
        self.assertEqual(
            no_uom._get_price_in_unit(5.0, self.uom_gram),
            no_uom._get_quantity_in_unit(5.0, self.uom_gram),
        )

    def test_get_reference_uom_reads_the_stored_dimension(self):
        """The root is a stored, indexed column (`reference_uom_id`), not a
        walk up `relative_uom_id` (one query per level) nor a `parent_path`
        prefix. The answer is unchanged, including for a new record."""
        chain = self.uom_unit
        for i in range(4):
            chain = self.env["uom.uom"].create(
                {"name": f"Link{i}", "relative_factor": 2, "relative_uom_id": chain.id}
            )
        self.assertEqual(chain._get_reference_uom(), self.uom_unit)
        self.assertEqual(chain.reference_uom_id, self.uom_unit)
        self.assertEqual(self.uom_unit._get_reference_uom(), self.uom_unit)
        self.assertEqual(self.uom_ton._get_reference_uom(), self.uom_gram)
        # A root is its own dimension.
        self.assertEqual(self.uom_gram.reference_uom_id, self.uom_gram)

        # One query, whatever the depth of the chain. `browse` on its own is
        # what makes this measure anything: a recordset carried over from the
        # creations above prefetches its whole batch, which hides the walk's
        # one-query-per-level behind a single warm fetch.
        self.env.invalidate_all()
        cold = self.env["uom.uom"].browse(chain.id)
        with self.assertQueryCount(1):
            cold._get_reference_uom().id

        # The dimension is a plain domain now, which is the point of storing it.
        self.assertIn(
            self.uom_ton,
            self.env["uom.uom"].search([("reference_uom_id", "=", self.uom_gram.id)]),
        )
        self.assertNotIn(
            self.uom_hour,
            self.env["uom.uom"].search([("reference_uom_id", "=", self.uom_gram.id)]),
        )

        # New records are computed in memory and resolve the same way.
        draft = self.env["uom.uom"].new(
            {"name": "Draft", "relative_factor": 3, "relative_uom_id": self.uom_ton.id}
        )
        self.assertEqual(draft._get_reference_uom(), self.uom_gram)
        self.assertTrue(draft._has_common_reference(self.uom_kgm))
        self.assertFalse(draft._has_common_reference(self.uom_hour))

    def test_reference_uom_follows_a_reparent(self):
        """`reference_uom_id` is recursive and stored, so moving a unit to
        another dimension has to move its whole subtree with it."""
        root = self.env["uom.uom"].create({"name": "NewRoot", "relative_factor": 1})
        mid = self.env["uom.uom"].create(
            {"name": "NewMid", "relative_factor": 10, "relative_uom_id": root.id}
        )
        leaf = self.env["uom.uom"].create(
            {"name": "NewLeaf", "relative_factor": 10, "relative_uom_id": mid.id}
        )
        self.assertEqual(leaf.reference_uom_id, root)

        mid.relative_uom_id = self.uom_gram
        self.assertEqual(mid.reference_uom_id, self.uom_gram)
        self.assertEqual(leaf.reference_uom_id, self.uom_gram, "the subtree moves too")
        self.assertTrue(leaf._has_common_reference(self.uom_ton))

    def test_display_name_follows_a_parent_rename(self):
        """`display_name` interpolates the *parent's* name but did not depend
        on it, so renaming a reference unit left every child stale."""
        ctx = {"formatted_display_name": True}
        self.assertEqual(
            self.uom_dozen.with_context(**ctx).display_name, "Dozens\t--12 Units--"
        )
        self.uom_unit.name = "Pieces"
        self.assertEqual(
            self.uom_dozen.with_context(**ctx).display_name, "Dozens\t--12 Pieces--"
        )


class TestUomConversionScale(UomCommon):
    """The conversion result is quantised at the destination unit's precision,
    with no reference to how fine the source unit is.

    None of this was covered: the only large-ratio test converts 1020000 g into
    1.02 Ton, comfortably above the floor, so it passes whatever the floor does.
    These are characterisation tests -- they pin today's behaviour so that any
    change to the rounding rule has to state its intent rather than discover it.
    """

    def test_conversion_floor_is_the_destination_unit(self):
        """A quantity below one quantum of the destination unit cannot be
        represented, and the default `rounding_method="UP"` (taken by 295 of
        the 308 call sites) turns that floor into inflation, not loss."""
        self.assertEqual(self.uom_kgm._get_quantity_in_unit(1, self.uom_ton), 0.01)
        self.assertEqual(
            self.uom_kgm._get_quantity_in_unit(1, self.uom_ton, round=False), 0.001
        )
        # The floor is flat: every order of magnitude under it collapses onto
        # the same value, so a comparison against it cannot separate them.
        for qty in (0.5, 1, 5, 9.9):
            with self.subTest(qty=qty):
                self.assertEqual(
                    self.uom_kgm._get_quantity_in_unit(qty, self.uom_ton), 0.01
                )

    def test_conversion_is_not_round_trip_stable(self):
        """Converting out and back does not return the original quantity.
        `stock.tests.test_move.TestStockMove.test_set_quantity_done_with_rounding_issues`
        depends on it: a 150 g delivery of an oz-measured product reserves
        149.97 g."""
        oz = self.quick_ref("uom.product_uom_oz")
        in_oz = self.uom_gram._get_quantity_in_unit(150, oz, rounding_method="HALF-UP")
        self.assertEqual(in_oz, 5.29)
        self.assertEqual(
            oz._get_quantity_in_unit(in_oz, self.uom_gram, rounding_method="HALF-UP"),
            149.97,
        )
        # The wider the ratio, the wider the drift.
        self.assertEqual(self.uom_gram._get_quantity_in_unit(4999, self.uom_ton), 0.01)
        self.assertEqual(
            self.uom_ton._get_quantity_in_unit(0.01, self.uom_gram), 10000.0
        )

    def test_conversion_down_annihilates_below_the_floor(self):
        """DOWN loses the quantity outright instead of inflating it."""
        self.assertEqual(
            self.uom_gram._get_quantity_in_unit(
                0.966, self.uom_kgm, rounding_method="DOWN"
            ),
            0.0,
        )
        self.assertEqual(
            self.uom_gram._get_quantity_in_unit(0.966, self.uom_kgm, round=False),
            0.000966,
        )

    def test_round_false_is_the_escape_hatch(self):
        """A conversion whose result feeds a comparison rather than a stored
        quantity has to opt out of rounding, or the floor decides the
        comparison for it. `product.pricelist._get_price_rule` did not, and
        priced a 0.5 kg order at a 10 kg bulk tier."""
        for qty, expected in ((0.5, 0.0005), (1, 0.001), (9.9, 0.0099)):
            with self.subTest(qty=qty):
                self.assertEqual(
                    self.uom_kgm._get_quantity_in_unit(qty, self.uom_ton, round=False),
                    expected,
                )

    def test_compute_quantity_always_returns_a_float(self):
        """The degenerate-input guard handed its argument straight back, so a
        `False` read off a half-filled record came out as `False`."""
        for qty in (0, 0.0, False, None):
            with self.subTest(qty=qty):
                self.assertEqual(
                    self.uom_gram._get_quantity_in_unit(qty, self.uom_kgm), 0.0
                )
                self.assertIsInstance(
                    self.uom_gram._get_quantity_in_unit(qty, self.uom_kgm), float
                )
        self.assertEqual(
            self.env["uom.uom"]._get_quantity_in_unit(5.0, self.uom_gram), 5.0
        )


class TestUomPriceDegradeWrappers(UomCommon):
    """The price wrappers had no coverage at all, while the quantity ones had
    four tests -- including the vendor-bill call site named in their docstring."""

    def test_price_wrappers_degrade_on_incompatible_units(self):
        self.assertFalse(self.uom_gram._has_common_reference(self.uom_hour))
        for wrapper in (
            self.uom_gram._get_price_report,
            self.uom_gram._get_price_estimate,
        ):
            with self.subTest(wrapper=wrapper.__name__):
                self.assertEqual(wrapper(100.0, self.uom_hour), 100.0)
                self.assertEqual(
                    wrapper(100.0, self.uom_hour, raise_if_failure=True),
                    100.0,
                    "The forced opt-out must not be overridable by the caller",
                )

    def test_price_wrappers_match_the_base_for_compatible_units(self):
        cases = [
            (self.uom_gram, 2.0, self.uom_ton),
            (self.uom_ton, 2000000.0, self.uom_gram),
        ]
        for wrapper_name in ("_get_price_report", "_get_price_estimate"):
            for src, price, dst in cases:
                with self.subTest(wrapper=wrapper_name, src=src.name, dst=dst.name):
                    self.assertEqual(
                        getattr(src, wrapper_name)(price, dst),
                        src._get_price_in_unit(price, dst),
                    )

    def test_price_wrappers_do_not_escalate_under_the_posting_context(self):
        """Only the *quantity* reconcile wrapper escalates on
        `uom_reconcile_strict`. There is no price equivalent, and the price
        wrappers must not acquire one by accident."""
        strict = self.uom_gram.with_context(uom_reconcile_strict=True)
        for wrapper_name in ("_get_price_report", "_get_price_estimate"):
            with self.subTest(wrapper=wrapper_name):
                self.assertEqual(
                    getattr(strict, wrapper_name)(100.0, self.uom_hour), 100.0
                )


class TestUomSmallApiGaps(UomCommon):
    def test_round_accepts_an_unset_unit_like_compare_and_is_zero(self):
        """`round` ignores `self` exactly as `compare` and `is_zero` do, so it
        takes the same receivers. It was the last of the three to raise."""
        no_uom = self.env["uom.uom"]
        self.assertEqual(no_uom.round(1.234), self.uom_unit.round(1.234))
        self.assertEqual(no_uom.round(1.235, rounding_method="DOWN"), 1.23)
        with self.assertRaises(ValueError):
            (self.uom_unit | self.uom_dozen).round(1.234)

    def test_a_hand_set_sequence_of_zero_survives_a_factor_write(self):
        """The guard read `uom.sequence` for truthiness, so the 0 the handle
        widget writes for a first row was taken to mean "unset" and recomputed
        away on the next `relative_factor` edit."""
        uom = self.env["uom.uom"].create(
            {"name": "Seq", "relative_factor": 3, "relative_uom_id": self.uom_unit.id}
        )
        self.assertEqual(uom.sequence, 300)
        uom.sequence = 0
        uom.relative_factor = 9
        self.assertEqual(uom.sequence, 0)

    def test_a_computed_sequence_is_never_zero(self):
        """...which is only unambiguous because a computed sequence has a floor
        of 1: `relative_factor < 0.01` used to land on 0 by itself."""
        tiny = self.env["uom.uom"].create(
            {
                "name": "Tiny",
                "relative_factor": 0.004,
                "relative_uom_id": self.uom_unit.id,
            }
        )
        self.assertEqual(tiny.sequence, 1)

    def test_protection_covers_master_data_from_any_module(self):
        """Sixteen modules ship `uom.uom` records. The protection query was
        pinned to `module = "uom"`, so a leaf from any of the others deleted
        cleanly and took its xml id with it."""
        foreign = self.env["uom.uom"].create({"name": "MX-KGM", "relative_factor": 1})
        self.env["ir.model.data"].create(
            {
                "module": "l10n_fake",
                "name": "product_uom_mx",
                "model": "uom.uom",
                "res_id": foreign.id,
            }
        )
        self.assertEqual(foreign._filter_protected_uoms(), foreign)
        with self.assertRaises(UserError):
            foreign.unlink()
        self.assertEqual(self.env.ref("l10n_fake.product_uom_mx"), foreign)

    def test_unprotected_units_are_still_deletable_from_another_module(self):
        """Dropping the module filter must not turn the guard into a blanket
        ban: the unprotected xml ids stay unprotected whoever declares them."""
        loose = self.env["uom.uom"].create({"name": "Loose", "relative_factor": 1})
        self.env["ir.model.data"].create(
            {
                "module": "l10n_fake",
                "name": "product_uom_dozen",
                "model": "uom.uom",
                "res_id": loose.id,
            }
        )
        self.assertFalse(loose._filter_protected_uoms())
        loose.unlink()
        self.assertFalse(loose.exists())

    def test_display_name_renders_a_non_integer_factor_for_humans(self):
        """`relative_factor` is an unlimited NUMERIC, so interpolating the raw
        float printed "Minutes --0.016666666666666666 Hours--"."""
        ctx = {"formatted_display_name": True}
        minute = self.quick_ref("uom.product_uom_minute")
        self.assertEqual(
            minute.with_context(**ctx).display_name, "Minutes\t--0.0166667 Hours--"
        )
        floz = self.quick_ref("uom.product_uom_floz")
        self.assertEqual(
            floz.with_context(**ctx).display_name, "fl oz (US)\t--0.0295735 L--"
        )
