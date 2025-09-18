"""Tests for recordset set operations, iteration, and container semantics.

The IterationMixin provides set algebra (union, intersection, difference),
comparison operators (subset/superset), iteration with prefetch optimization,
and container protocols (__contains__, __len__, __getitem__).

These operations are used pervasively in Odoo code but were never directly
tested — only exercised implicitly through higher-level tests.
"""

import copy

from odoo.tests.common import TransactionCase


class TestRecordsetSetOperations(TransactionCase):
    """Test union, intersection, difference, and concatenation of recordsets."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Category = cls.env["test_orm.category"]
        cls.cat_a = Category.create({"name": "Alpha"})
        cls.cat_b = Category.create({"name": "Beta"})
        cls.cat_c = Category.create({"name": "Gamma"})
        cls.cat_d = Category.create({"name": "Delta"})
        cls.all_cats = cls.cat_a | cls.cat_b | cls.cat_c | cls.cat_d

    def test_union_basic(self):
        """Union of two disjoint recordsets contains all records."""
        r1 = self.cat_a | self.cat_b
        r2 = self.cat_c | self.cat_d
        result = r1 | r2
        self.assertEqual(len(result), 4)
        self.assertEqual(set(result.ids), set(self.all_cats.ids))

    def test_union_preserves_order(self):
        """Union preserves first occurrence order."""
        r1 = self.cat_b | self.cat_a
        r2 = self.cat_d | self.cat_c
        result = r1 | r2
        self.assertEqual(
            list(result._ids),
            [self.cat_b.id, self.cat_a.id, self.cat_d.id, self.cat_c.id],
        )

    def test_union_removes_duplicates(self):
        """Union deduplicates overlapping records."""
        r1 = self.cat_a | self.cat_b | self.cat_c
        r2 = self.cat_b | self.cat_c | self.cat_d
        result = r1 | r2
        self.assertEqual(len(result), 4)

    def test_union_empty(self):
        """Union with empty recordset returns the non-empty one."""
        empty = self.env["test_orm.category"]
        result = self.cat_a | empty
        self.assertEqual(result, self.cat_a)
        result = empty | self.cat_a
        self.assertEqual(result, self.cat_a)

    def test_union_self(self):
        """Union of recordset with itself returns deduplicated (same records)."""
        r = self.cat_a | self.cat_b
        result = r | r
        self.assertEqual(len(result), 2)
        self.assertEqual(result, r)

    def test_union_multiple(self):
        """union() method accepts multiple arguments."""
        result = self.cat_a.union(self.cat_b, self.cat_c, self.cat_d)
        self.assertEqual(len(result), 4)
        self.assertEqual(result, self.all_cats)

    def test_intersection_basic(self):
        """Intersection returns records present in both sets."""
        r1 = self.cat_a | self.cat_b | self.cat_c
        r2 = self.cat_b | self.cat_c | self.cat_d
        result = r1 & r2
        self.assertEqual(len(result), 2)
        self.assertEqual(result, self.cat_b | self.cat_c)

    def test_intersection_preserves_order(self):
        """Intersection preserves first occurrence order from left operand."""
        r1 = self.cat_c | self.cat_b | self.cat_a
        r2 = self.cat_a | self.cat_c
        result = r1 & r2
        self.assertEqual(list(result._ids), [self.cat_c.id, self.cat_a.id])

    def test_intersection_empty(self):
        """Intersection with empty recordset returns empty."""
        empty = self.env["test_orm.category"]
        result = self.all_cats & empty
        self.assertFalse(result)

    def test_intersection_disjoint(self):
        """Intersection of disjoint sets returns empty."""
        r1 = self.cat_a | self.cat_b
        r2 = self.cat_c | self.cat_d
        result = r1 & r2
        self.assertFalse(result)
        self.assertEqual(len(result), 0)

    def test_difference_basic(self):
        """Difference removes records present in the right operand."""
        r1 = self.cat_a | self.cat_b | self.cat_c
        r2 = self.cat_b | self.cat_d
        result = r1 - r2
        self.assertEqual(len(result), 2)
        self.assertEqual(result, self.cat_a | self.cat_c)

    def test_difference_preserves_order(self):
        """Difference preserves order of left operand."""
        r1 = self.cat_c | self.cat_b | self.cat_a
        r2 = self.cat_b
        result = r1 - r2
        self.assertEqual(list(result._ids), [self.cat_c.id, self.cat_a.id])

    def test_difference_empty(self):
        """Difference with empty recordset returns self."""
        empty = self.env["test_orm.category"]
        result = self.all_cats - empty
        self.assertEqual(result, self.all_cats)

    def test_difference_self(self):
        """Subtracting a recordset from itself returns empty."""
        result = self.all_cats - self.all_cats
        self.assertFalse(result)
        self.assertEqual(len(result), 0)

    def test_concat_basic(self):
        """Concatenation (+) joins recordsets."""
        r1 = self.cat_a | self.cat_b
        r2 = self.cat_c | self.cat_d
        result = r1 + r2
        self.assertEqual(len(result), 4)

    def test_concat_preserves_duplicates(self):
        """Unlike union, concatenation preserves duplicates."""
        r1 = self.cat_a | self.cat_b
        r2 = self.cat_b | self.cat_c
        result = r1 + r2
        self.assertEqual(len(result), 4)  # cat_b appears twice
        self.assertEqual(
            list(result._ids),
            [self.cat_a.id, self.cat_b.id, self.cat_b.id, self.cat_c.id],
        )

    def test_concat_multiple(self):
        """concat() accepts multiple arguments."""
        result = self.cat_a.concat(self.cat_b, self.cat_c)
        self.assertEqual(len(result), 3)

    def test_type_error_different_models(self):
        """Set operations between different models raise TypeError."""
        partner = self.env["res.partner"].search([], limit=1)
        with self.assertRaises(TypeError):
            self.cat_a | partner
        with self.assertRaises(TypeError):
            self.cat_a & partner
        with self.assertRaises(TypeError):
            self.cat_a - partner
        with self.assertRaises(TypeError):
            self.cat_a + partner

    def test_type_error_non_recordset(self):
        """Set operations with non-recordset types raise TypeError."""
        with self.assertRaises(TypeError):
            self.cat_a | "string"
        with self.assertRaises(TypeError):
            self.cat_a & 42
        with self.assertRaises(TypeError):
            self.cat_a - [1, 2, 3]
        with self.assertRaises(TypeError):
            self.cat_a + None


class TestRecordsetComparison(TransactionCase):
    """Test recordset comparison operators (==, <, <=, >, >=).

    Equality is set-based (order-independent). Subset/superset operators
    use proper set semantics.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Category = cls.env["test_orm.category"]
        cls.cat_a = Category.create({"name": "Cmp A"})
        cls.cat_b = Category.create({"name": "Cmp B"})
        cls.cat_c = Category.create({"name": "Cmp C"})

    def test_eq_same_records(self):
        """Recordsets with the same ids are equal."""
        r1 = self.cat_a | self.cat_b
        r2 = self.cat_a | self.cat_b
        self.assertEqual(r1, r2)

    def test_eq_different_order(self):
        """Equality is order-independent (set semantics)."""
        r1 = self.cat_a | self.cat_b
        r2 = self.cat_b | self.cat_a
        self.assertEqual(r1, r2)

    def test_eq_different_records(self):
        """Recordsets with different ids are not equal."""
        r1 = self.cat_a | self.cat_b
        r2 = self.cat_a | self.cat_c
        self.assertNotEqual(r1, r2)

    def test_eq_empty(self):
        """Two empty recordsets of the same model are equal."""
        empty1 = self.env["test_orm.category"]
        empty2 = self.env["test_orm.category"]
        self.assertEqual(empty1, empty2)

    def test_lt_proper_subset(self):
        """< tests for proper subset."""
        r1 = self.cat_a | self.cat_b
        r2 = self.cat_a | self.cat_b | self.cat_c
        self.assertTrue(r1 < r2)
        self.assertFalse(r2 < r1)

    def test_lt_equal_sets(self):
        """Equal sets are not proper subsets."""
        r1 = self.cat_a | self.cat_b
        r2 = self.cat_a | self.cat_b
        self.assertFalse(r1 < r2)

    def test_le_subset_or_equal(self):
        """<= tests for subset or equal."""
        r1 = self.cat_a | self.cat_b
        r2 = self.cat_a | self.cat_b | self.cat_c
        self.assertTrue(r1 <= r2)
        self.assertFalse(r2 <= r1)

    def test_le_self(self):
        """A recordset is a subset of itself."""
        r = self.cat_a | self.cat_b
        self.assertTrue(r <= r)

    def test_le_empty(self):
        """Empty recordset is a subset of any recordset."""
        empty = self.env["test_orm.category"]
        self.assertTrue(empty <= self.cat_a)

    def test_gt_proper_superset(self):
        """> tests for proper superset."""
        r1 = self.cat_a | self.cat_b | self.cat_c
        r2 = self.cat_a | self.cat_b
        self.assertTrue(r1 > r2)
        self.assertFalse(r2 > r1)

    def test_ge_superset_or_equal(self):
        """>= tests for superset or equal."""
        r1 = self.cat_a | self.cat_b | self.cat_c
        r2 = self.cat_a | self.cat_b
        self.assertTrue(r1 >= r2)
        self.assertTrue(r1 >= r1)

    def test_ne_different(self):
        """!= works correctly."""
        r1 = self.cat_a | self.cat_b
        r2 = self.cat_b | self.cat_c
        self.assertTrue(r1 != r2)
        self.assertFalse(r1 != r1)

    def test_comparison_different_model(self):
        """Comparison with different model returns NotImplemented."""
        partner = self.env["res.partner"].search([], limit=1)
        result = self.cat_a.__lt__(partner)
        self.assertIs(result, NotImplemented)

    def test_singleton_in_recordset(self):
        """Singleton in larger recordset uses optimized path."""
        r = self.cat_a | self.cat_b | self.cat_c
        self.assertTrue(self.cat_a <= r)
        self.assertTrue(self.cat_a in r)


class TestRecordsetIteration(TransactionCase):
    """Test iteration, reversal, container protocol, and item access."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Category = cls.env["test_orm.category"]
        cls.cat_a = Category.create({"name": "Iter Alpha"})
        cls.cat_b = Category.create({"name": "Iter Beta"})
        cls.cat_c = Category.create({"name": "Iter Gamma"})
        cls.records = cls.cat_a | cls.cat_b | cls.cat_c

    def test_iter_basic(self):
        """Iterating yields singletons in order."""
        result = list(self.records)
        self.assertEqual(len(result), 3)
        for r in result:
            self.assertEqual(len(r), 1)
        self.assertEqual(result[0], self.cat_a)
        self.assertEqual(result[1], self.cat_b)
        self.assertEqual(result[2], self.cat_c)

    def test_iter_empty(self):
        """Iterating over empty recordset yields nothing."""
        empty = self.env["test_orm.category"]
        result = list(empty)
        self.assertEqual(result, [])

    def test_iter_single(self):
        """Iterating over singleton yields self."""
        result = list(self.cat_a)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], self.cat_a)

    def test_reversed_basic(self):
        """reversed() yields singletons in reverse order."""
        result = list(reversed(self.records))
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0], self.cat_c)
        self.assertEqual(result[1], self.cat_b)
        self.assertEqual(result[2], self.cat_a)

    def test_reversed_empty(self):
        """reversed() on empty recordset yields nothing."""
        empty = self.env["test_orm.category"]
        result = list(reversed(empty))
        self.assertEqual(result, [])

    def test_reversed_single(self):
        """reversed() on singleton yields self."""
        result = list(reversed(self.cat_a))
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], self.cat_a)

    def test_contains_record(self):
        """'record in recordset' checks membership."""
        self.assertIn(self.cat_a, self.records)
        self.assertIn(self.cat_b, self.records)
        self.assertIn(self.cat_c, self.records)

    def test_contains_record_not_found(self):
        """Record not in recordset returns False."""
        other = self.env["test_orm.category"].create({"name": "Other"})
        self.assertNotIn(other, self.records)

    def test_contains_field_name(self):
        """'string in recordset' checks if field exists."""
        self.assertIn("name", self.records)
        self.assertIn("color", self.records)

    def test_contains_invalid_field(self):
        """Non-existent field name returns False."""
        self.assertNotIn("nonexistent_field_xyz", self.records)

    def test_contains_wrong_model(self):
        """Record from different model raises TypeError."""
        partner = self.env["res.partner"].search([], limit=1)
        with self.assertRaises(TypeError):
            partner in self.records

    def test_getitem_index(self):
        """records[i] returns singleton at index."""
        first = self.records[0]
        self.assertEqual(len(first), 1)
        self.assertEqual(first, self.cat_a)
        last = self.records[-1]
        self.assertEqual(last, self.cat_c)

    def test_getitem_slice(self):
        """records[i:j] returns sub-recordset."""
        result = self.records[1:3]
        self.assertEqual(len(result), 2)
        self.assertEqual(result, self.cat_b | self.cat_c)

    def test_getitem_field(self):
        """records['field'] reads the field value."""
        name = self.cat_a["name"]
        self.assertEqual(name, "Iter Alpha")

    def test_setitem_field(self):
        """records['field'] = value writes the field."""
        self.cat_a["name"] = "Modified Alpha"
        self.assertEqual(self.cat_a.name, "Modified Alpha")

    def test_len(self):
        """len() returns the number of records."""
        self.assertEqual(len(self.records), 3)
        self.assertEqual(len(self.cat_a), 1)
        self.assertEqual(len(self.env["test_orm.category"]), 0)

    def test_bool_empty(self):
        """Empty recordset is falsy."""
        empty = self.env["test_orm.category"]
        self.assertFalse(empty)
        self.assertFalse(bool(empty))

    def test_bool_nonempty(self):
        """Non-empty recordset is truthy."""
        self.assertTrue(self.records)
        self.assertTrue(self.cat_a)

    def test_int_singleton(self):
        """int(singleton) returns the record id."""
        self.assertEqual(int(self.cat_a), self.cat_a.id)

    def test_int_empty(self):
        """int(empty) returns 0."""
        empty = self.env["test_orm.category"]
        self.assertEqual(int(empty), 0)

    def test_repr(self):
        """repr shows model name and ids tuple."""
        r = repr(self.cat_a)
        self.assertIn("test_orm.category", r)
        self.assertIn(str(self.cat_a.id), r)

    def test_hash(self):
        """Recordsets are hashable and can be used in sets/dicts."""
        r1 = self.cat_a | self.cat_b
        self.cat_a | self.cat_b
        # Different recordset objects with same ids should have same hash
        # (Note: hash depends on frozenset of ids, so order doesn't matter)
        s = {r1}
        self.assertIn(r1, s)

    def test_deepcopy_returns_self(self):
        """deepcopy returns the recordset itself (no actual copy)."""
        result = copy.deepcopy(self.records)
        self.assertIs(result, self.records)

    def test_browse_single_int(self):
        """browse(int) creates a singleton recordset."""
        record = self.env["test_orm.category"].browse(self.cat_a.id)
        self.assertEqual(len(record), 1)
        self.assertEqual(record.id, self.cat_a.id)

    def test_browse_list(self):
        """browse(list) creates a multi-record recordset."""
        ids = [self.cat_a.id, self.cat_b.id]
        records = self.env["test_orm.category"].browse(ids)
        self.assertEqual(len(records), 2)

    def test_browse_empty(self):
        """browse() with no args creates an empty recordset."""
        empty = self.env["test_orm.category"].browse()
        self.assertFalse(empty)
        self.assertEqual(len(empty), 0)

    def test_ids_property(self):
        """ids property returns list of integer ids."""
        result = self.records.ids
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 3)
        self.assertTrue(all(isinstance(i, int) for i in result))
