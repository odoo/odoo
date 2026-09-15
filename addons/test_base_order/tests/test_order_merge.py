from datetime import timedelta
from unittest.mock import patch

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestOrderMergeMixin(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.SaleOrder = cls.env["sale.order"]
        cls.PurchaseOrder = cls.env["purchase.order"]
        cls.partner_a = cls.env["res.partner"].create({"name": "Partner A"})
        cls.partner_b = cls.env["res.partner"].create({"name": "Partner B"})
        cls.product = cls.env["product.product"].create({"name": "Merge Product"})

    def _order(self, partner, date_order=None):
        vals = {"partner_id": partner.id}
        if date_order:
            vals["date_order"] = date_order
        return self.SaleOrder.create(vals)

    def test_validate_selection_requires_at_least_two(self):
        one = self._order(self.partner_a)
        with self.assertRaises(UserError):
            self.SaleOrder._merge_check_selection(one)
        self.SaleOrder._merge_check_selection(one + self._order(self.partner_a))

    def test_validate_groups_requires_a_group(self):
        with self.assertRaises(UserError):
            self.SaleOrder._merge_check_groups([])
        self.SaleOrder._merge_check_groups([self._order(self.partner_a)])

    def test_group_orders_groups_by_partner(self):
        same = self._order(self.partner_a) + self._order(self.partner_a)
        groups = self.SaleOrder._merge_group_orders(same)
        self.assertEqual(len(groups), 1)
        self.assertEqual(len(groups[0]), 2)

        distinct = self._order(self.partner_a) + self._order(self.partner_b)
        self.assertEqual(self.SaleOrder._merge_group_orders(distinct), [])

    def test_eligible_orders_are_draft(self):
        orders = self._order(self.partner_a) + self._order(self.partner_a)
        self.assertEqual(orders._filtered_merge_eligible_orders(), orders)

    def test_merge_target_is_the_oldest_order(self):
        old = self._order(self.partner_a, date_order="2020-01-01 00:00:00")
        new = self._order(self.partner_a, date_order="2024-01-01 00:00:00")
        self.assertEqual(self.SaleOrder._merge_get_target(old + new), old)

    def test_action_merge_logs_excluded_non_draft_orders(self):
        draft_a = self._order(self.partner_a)
        draft_b = self._order(self.partner_a)
        confirmed = self._order(self.partner_a)
        confirmed.line_ids = [
            (0, 0, {"product_id": self.env["product.product"].create({"name": "P"}).id})
        ]
        confirmed.action_confirm()

        with self.assertLogs(
            "odoo.addons.base_order.models.mixin_order_merge", level="INFO"
        ) as captured:
            (draft_a + draft_b + confirmed).action_merge()

        self.assertTrue(
            any(confirmed.name in line for line in captured.output),
            "the excluded confirmed order's name must appear in the log",
        )

    def test_collapse_matches_does_not_bridge_non_matching_lines(self):
        """Two lines that individually match a third line's date, but not
        each other's, must not be folded together through it."""
        now = fields.Datetime.now()
        date_a = now
        date_b = now + timedelta(hours=36)  # outside the 24h threshold of a
        date_source = now + timedelta(hours=18)  # inside threshold of both

        target = self.PurchaseOrder.create({"partner_id": self.partner_a.id})
        Line = self.env["purchase.order.line"]
        line_a = Line.create(
            {
                "order_id": target.id,
                "product_id": self.product.id,
                "product_qty": 1.0,
                "price_unit": 100.0,
                "date_commitment": date_a,
            }
        )
        line_b = Line.create(
            {
                "order_id": target.id,
                "product_id": self.product.id,
                "product_qty": 1.0,
                "price_unit": 100.0,
                "date_commitment": date_b,
            }
        )
        self.assertFalse(
            target._merge_lines_match_date(line_a, line_b),
            "test setup invalid: line_a and line_b must not match each other",
        )

        source = self.PurchaseOrder.create({"partner_id": self.partner_a.id})
        Line.create(
            {
                "order_id": source.id,
                "product_id": self.product.id,
                "product_qty": 1.0,
                "price_unit": 100.0,
                "date_commitment": date_source,
            }
        )

        (target | source).action_merge()

        remaining = target.line_ids.filtered(lambda ln: not ln.display_type)
        self.assertEqual(
            len(remaining),
            2,
            "line_a and line_b must stay distinct; only one may absorb the "
            "source line's quantity",
        )
        self.assertEqual(sorted(remaining.mapped("product_qty")), [1.0, 2.0])

    def test_collapse_matches_routes_through_the_merge_line_hook(self):
        """Multi-candidate collapse must fold through `_merge_order_line`,
        the same overridable hook the single-match path already uses --
        not a second, independently-maintained aggregation policy."""
        target = self._order(self.partner_a)
        line_1 = self.env["sale.order.line"].create(
            {
                "order_id": target.id,
                "product_id": self.product.id,
                "product_qty": 1.0,
                "price_unit": 100.0,
            }
        )
        self.env["sale.order.line"].create(
            {
                "order_id": target.id,
                "product_id": self.product.id,
                "product_qty": 1.0,
                "price_unit": 100.0,
            }
        )
        source = self._order(self.partner_a)
        self.env["sale.order.line"].create(
            {
                "order_id": source.id,
                "product_id": self.product.id,
                "product_qty": 1.0,
                "price_unit": 100.0,
            }
        )

        original = type(line_1)._merge_order_line
        calls = []

        def tracked(self, source_line):
            calls.append((self.id, source_line.id))
            return original(self, source_line)

        with patch.object(type(line_1), "_merge_order_line", tracked):
            (target | source).action_merge()

        self.assertTrue(calls, "the multi-match fold must call _merge_order_line")
        self.assertEqual(
            {c[0] for c in calls},
            {line_1.id},
            "the surviving keeper must always be the first candidate",
        )
        self.assertEqual(
            len(calls),
            2,
            "one call folding the duplicate target line, one folding the source line",
        )

    def test_merge_metadata_deduplicates_repeated_origin(self):
        """Merging the same target again must not keep piling up duplicate
        origin/partner_ref values from a source that was already folded
        in once before."""
        target = self._order(self.partner_a)
        target.write({"origin": "SO001", "partner_ref": "REF001"})
        source = self._order(self.partner_a)
        source.write({"origin": "SO001", "partner_ref": "REF001"})

        self.SaleOrder._merge_metadata(target, source)

        self.assertEqual(target.origin, "SO001")
        self.assertEqual(target.partner_ref, "REF001")
