"""Tests for ORM primitives: NewId and Command classes.

These are Layer 0 of the ORM — foundational types with zero ORM dependencies.
Testing them directly ensures the building blocks are solid before higher layers
depend on them.
"""

from odoo.fields import Command
from odoo.orm.helpers import OriginIds
from odoo.orm.primitives import NewId
from odoo.tests.common import TransactionCase


class TestNewId(TransactionCase):
    """Test NewId pseudo-identifier behavior.

    NewId is used for records that haven't been persisted to the database yet.
    It supports optional origin (the real DB id this virtual record came from)
    and ref (an arbitrary reference for tracking).
    """

    def test_bool_is_false(self):
        """NewId is always falsy — this is how the ORM detects 'new' records."""
        self.assertFalse(NewId())
        self.assertFalse(NewId(origin=42))
        self.assertFalse(NewId(ref="abc"))
        self.assertIs(bool(NewId()), False)

    def test_eq_same_origin(self):
        """Two NewIds with the same origin are equal."""
        a = NewId(origin=1)
        b = NewId(origin=1)
        self.assertEqual(a, b)

    def test_eq_same_ref(self):
        """Two NewIds with the same ref are equal."""
        a = NewId(ref="abc")
        b = NewId(ref="abc")
        self.assertEqual(a, b)

    def test_eq_no_match(self):
        """Two bare NewIds (no origin, no ref) are never equal — identity-based."""
        a = NewId()
        b = NewId()
        self.assertNotEqual(a, b)

    def test_eq_different_origin(self):
        """NewIds with different origins are not equal."""
        self.assertNotEqual(NewId(origin=1), NewId(origin=2))

    def test_eq_origin_vs_ref(self):
        """A NewId with origin is not equal to one with only ref, even if values match."""
        # origin=1 matches on origin field, ref=1 matches on ref field — different semantics
        a = NewId(origin=1)
        b = NewId(ref=1)
        # Both have truthy origin/ref but they compare on different attributes
        # a has origin=1, ref=None; b has origin=None, ref=1
        # __eq__ checks: (self.origin and other.origin and ...) or (self.ref and other.ref and ...)
        # a.origin=1 and b.origin=None → first branch fails
        # a.ref=None → second branch fails
        self.assertNotEqual(a, b)

    def test_eq_not_newid(self):
        """NewId is not equal to non-NewId types."""
        self.assertNotEqual(NewId(origin=1), 1)
        self.assertNotEqual(NewId(), None)
        self.assertNotEqual(NewId(ref="x"), "x")

    def test_hash_consistency(self):
        """Equal NewIds must have equal hashes (hash contract)."""
        a = NewId(origin=42)
        b = NewId(origin=42)
        self.assertEqual(a, b)
        self.assertEqual(hash(a), hash(b))

    def test_hash_in_set(self):
        """NewIds work correctly as set elements."""
        a = NewId(origin=1)
        b = NewId(origin=1)
        c = NewId(origin=2)
        s = {a, b, c}
        # a and b are equal, so set should deduplicate
        self.assertEqual(len(s), 2)

    def test_hash_in_dict(self):
        """NewIds work correctly as dict keys."""
        a = NewId(origin=1)
        b = NewId(origin=1)
        d = {a: "first"}
        d[b] = "second"
        # b overwrites a since they're equal
        self.assertEqual(len(d), 1)
        self.assertEqual(d[a], "second")

    def test_hash_bare_unique(self):
        """Bare NewIds get unique hashes based on id()."""
        a = NewId()
        b = NewId()
        # Very unlikely to collide, but they should at least be usable
        s = {a, b}
        self.assertEqual(len(s), 2)

    def test_lt_with_int(self):
        """NewId with origin compares with integers."""
        self.assertLess(NewId(origin=1), 2)
        self.assertFalse(NewId(origin=2) < 1)

    def test_lt_between_newids(self):
        """NewIds compare by origin values."""
        self.assertLess(NewId(origin=1), NewId(origin=2))
        self.assertFalse(NewId(origin=2) < NewId(origin=1))

    def test_lt_no_origin_vs_int(self):
        """NewId without origin is not less than any integer."""
        # No origin means origin is None → bool(self.origin) is False
        self.assertFalse(NewId() < 100)

    def test_lt_origin_vs_none_origin(self):
        """NewId with origin compared to NewId without origin must not crash.

        Regression test: previously raised TypeError because the code
        evaluated ``None > self.origin`` when other.origin was None.
        """
        # NewId(origin=5) < NewId(origin=None) — should return False, not crash
        self.assertFalse(NewId(origin=5) < NewId())

    def test_lt_none_origin_vs_origin(self):
        """NewId without origin compared to NewId with origin."""
        # NewId(origin=None) < NewId(origin=5)
        # Line 72: other = other.origin → 5 (int)
        # Line 73: if other is None → False (other=5)
        # Line 75: isinstance(other, int) → True
        # Line 76: bool(self.origin) is False → returns False
        self.assertFalse(NewId() < NewId(origin=5))

    def test_lt_both_none_origins(self):
        """Two NewIds without origins — neither is less than the other."""
        a = NewId()
        b = NewId()
        # a.origin=None, b.origin=None
        # Line 72: other = b.origin → None
        # Line 73: other is None → True
        # Line 74: other > self.origin if self.origin → self.origin is None/falsy → False
        self.assertFalse(a < b)

    def test_lt_returns_not_implemented(self):
        """Comparison with incompatible types returns NotImplemented."""
        result = NewId(origin=1).__lt__("string")
        self.assertIs(result, NotImplemented)

    def test_repr_with_origin(self):
        """repr shows origin when set."""
        n = NewId(origin=42)
        self.assertEqual(repr(n), "<NewId origin=42>")

    def test_repr_with_ref(self):
        """repr shows ref when origin is not set."""
        n = NewId(ref="abc")
        self.assertEqual(repr(n), "<NewId ref='abc'>")

    def test_repr_bare(self):
        """repr shows hex address for bare NewIds."""
        n = NewId()
        r = repr(n)
        self.assertTrue(r.startswith("<NewId 0x"))
        self.assertTrue(r.endswith(">"))

    def test_str_with_origin(self):
        """str format with origin."""
        n = NewId(origin=42)
        self.assertEqual(str(n), "NewId_42")

    def test_str_with_ref(self):
        """str format with ref."""
        n = NewId(ref="abc")
        self.assertEqual(str(n), "NewId_'abc'")

    def test_str_bare(self):
        """str format for bare NewId shows hex address."""
        n = NewId()
        s = str(n)
        self.assertTrue(s.startswith("NewId_0x"))

    def test_total_ordering(self):
        """NewId supports all comparison operators via @total_ordering."""
        a = NewId(origin=1)
        b = NewId(origin=2)
        self.assertTrue(a < b)
        self.assertTrue(a <= b)
        self.assertTrue(b > a)
        self.assertTrue(b >= a)
        self.assertTrue(a <= NewId(origin=1))
        self.assertTrue(a >= NewId(origin=1))


class TestCommand(TransactionCase):
    """Test Command enum and factory methods.

    Commands are the API for manipulating One2many and Many2many fields.
    Each factory method returns a 3-element tuple (command_id, record_id, value).
    """

    def test_create_tuple(self):
        """Command.create returns (CREATE, 0, values)."""
        vals = {"name": "test"}
        result = Command.create(vals)
        self.assertEqual(result, (0, 0, vals))
        self.assertEqual(result[0], Command.CREATE)

    def test_update_tuple(self):
        """Command.update returns (UPDATE, id, values)."""
        vals = {"name": "updated"}
        result = Command.update(1, vals)
        self.assertEqual(result, (1, 1, vals))
        self.assertEqual(result[0], Command.UPDATE)

    def test_delete_tuple(self):
        """Command.delete returns (DELETE, id, 0)."""
        result = Command.delete(5)
        self.assertEqual(result, (2, 5, 0))
        self.assertEqual(result[0], Command.DELETE)

    def test_unlink_tuple(self):
        """Command.unlink returns (UNLINK, id, 0)."""
        result = Command.unlink(5)
        self.assertEqual(result, (3, 5, 0))
        self.assertEqual(result[0], Command.UNLINK)

    def test_link_tuple(self):
        """Command.link returns (LINK, id, 0)."""
        result = Command.link(5)
        self.assertEqual(result, (4, 5, 0))
        self.assertEqual(result[0], Command.LINK)

    def test_clear_tuple(self):
        """Command.clear returns (CLEAR, 0, 0)."""
        result = Command.clear()
        self.assertEqual(result, (5, 0, 0))
        self.assertEqual(result[0], Command.CLEAR)

    def test_set_tuple(self):
        """Command.set returns (SET, 0, ids)."""
        result = Command.set([1, 2, 3])
        self.assertEqual(result, (6, 0, [1, 2, 3]))
        self.assertEqual(result[0], Command.SET)

    def test_set_empty(self):
        """Command.set with empty list."""
        result = Command.set([])
        self.assertEqual(result, (6, 0, []))

    def test_enum_values(self):
        """Command enum members have expected integer values."""
        self.assertEqual(Command.CREATE, 0)
        self.assertEqual(Command.UPDATE, 1)
        self.assertEqual(Command.DELETE, 2)
        self.assertEqual(Command.UNLINK, 3)
        self.assertEqual(Command.LINK, 4)
        self.assertEqual(Command.CLEAR, 5)
        self.assertEqual(Command.SET, 6)

    def test_command_is_int_enum(self):
        """Commands are IntEnum, so they work as integers."""
        self.assertIsInstance(Command.CREATE, int)
        self.assertEqual(Command.CREATE + 1, 1)

    def test_command_in_orm_write(self):
        """Commands work in actual ORM write operations."""
        cat1 = self.env["test_orm.category"].create({"name": "Cat 1"})
        cat2 = self.env["test_orm.category"].create({"name": "Cat 2"})
        discussion = self.env["test_orm.discussion"].create(
            {
                "name": "Test Discussion",
                "categories": [Command.link(cat1.id)],
            }
        )
        self.assertEqual(discussion.categories, cat1)

        # Add cat2 via link command
        discussion.write({"categories": [Command.link(cat2.id)]})
        self.assertEqual(discussion.categories, cat1 | cat2)

        # Replace all with set command
        discussion.write({"categories": [Command.set(cat2.ids)]})
        self.assertEqual(discussion.categories, cat2)

        # Clear all
        discussion.write({"categories": [Command.clear()]})
        self.assertFalse(discussion.categories)


class TestOriginIds(TransactionCase):
    """Characterization tests for OriginIds.

    OriginIds is a reversible iterable that extracts origin IDs from a
    collection of mixed int/NewId IDs. Real int IDs pass through unchanged;
    NewId objects yield their .origin; IDs without origins are filtered out.
    """

    def test_regular_ints_pass_through(self):
        """Regular integer IDs are yielded unchanged."""
        result = list(OriginIds((1, 2, 3)))
        self.assertEqual(result, [1, 2, 3])

    def test_newid_with_origin_yields_origin(self):
        """NewId with origin yields the origin integer.

        NewId.__bool__ is always False, so the `or` branch in the walrus
        evaluates getattr(id_, 'origin', None) which returns the origin int.
        """
        ids = (NewId(origin=10), NewId(origin=20))
        result = list(OriginIds(ids))
        self.assertEqual(result, [10, 20])

    def test_newid_without_origin_filtered_out(self):
        """NewId without origin (origin=None) is filtered out."""
        ids = (NewId(), NewId(ref="some_ref"))
        result = list(OriginIds(ids))
        self.assertEqual(result, [])

    def test_mixed_ids(self):
        """Mixed ints and NewIds — ints pass through, NewIds yield origins."""
        ids = (1, NewId(origin=5), NewId(), 3, NewId(origin=7))
        result = list(OriginIds(ids))
        self.assertEqual(result, [1, 5, 3, 7])

    def test_empty_sequence(self):
        """Empty input yields nothing."""
        self.assertEqual(list(OriginIds(())), [])

    def test_reversed_preserves_semantics(self):
        """__reversed__ applies the same filtering in reverse order."""
        ids = (1, NewId(origin=5), NewId(), 3)
        result = list(reversed(OriginIds(ids)))
        self.assertEqual(result, [3, 5, 1])

    def test_iterable_not_iterator(self):
        """OriginIds can be iterated multiple times (it's an iterable, not an iterator)."""
        oids = OriginIds((1, 2, 3))
        first = list(oids)
        second = list(oids)
        self.assertEqual(first, second)
