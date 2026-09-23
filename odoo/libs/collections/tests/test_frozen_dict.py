import copy
import pickle
import unittest
from collections.abc import Iterable, Mapping
from typing import Any

from odoo.libs.collections.frozen_dict import freehash, frozendict


class TestFrozendictImmutability(unittest.TestCase):
    def test_ior_rejected(self):
        fd = frozendict({"a": 1})
        with self.assertRaises(NotImplementedError):
            fd |= {"b": 2}
        self.assertEqual(dict(fd), {"a": 1})

    def test_ior_does_not_stale_cached_hash(self):
        fd = frozendict({"a": 1})
        h = hash(fd)
        with self.assertRaises(NotImplementedError):
            fd |= {"b": 2}
        self.assertEqual(hash(fd), h)

    def test_setitem_rejected(self):
        fd = frozendict({"a": 1})
        with self.assertRaises(NotImplementedError):
            fd["b"] = 2

    def test_update_rejected(self):
        fd = frozendict({"a": 1})
        with self.assertRaises(NotImplementedError):
            fd.update({"b": 2})


class TestFrozendictCopyAndPickle(unittest.TestCase):
    def test_copy(self):
        fd = frozendict({"a": 1, "b": 2})
        clone = copy.copy(fd)
        self.assertIsInstance(clone, frozendict)
        self.assertEqual(dict(clone), {"a": 1, "b": 2})

    def test_deepcopy(self):
        fd = frozendict({"a": 1})
        clone = copy.deepcopy(fd)
        self.assertIsInstance(clone, frozendict)
        self.assertEqual(dict(clone), {"a": 1})

    def test_deepcopy_recurses_into_mutable_values(self):
        fd = frozendict({"a": [1, 2]})
        clone = copy.deepcopy(fd)
        self.assertEqual(clone["a"], [1, 2])
        self.assertIsNot(clone["a"], fd["a"])
        clone["a"].append(3)
        self.assertEqual(fd["a"], [1, 2])

    def test_copy_shares_mutable_values(self):
        fd = frozendict({"a": [1, 2]})
        self.assertIs(copy.copy(fd)["a"], fd["a"])

    def test_pickle_roundtrip(self):
        fd = frozendict({"a": 1, "b": "two"})
        restored = pickle.loads(pickle.dumps(fd))
        self.assertIsInstance(restored, frozendict)
        self.assertEqual(dict(restored), {"a": 1, "b": "two"})

    def test_copy_is_still_immutable(self):
        clone = copy.deepcopy(frozendict({"a": 1}))
        with self.assertRaises(NotImplementedError):
            clone["b"] = 2

    def test_copy_preserves_hash(self):
        fd = frozendict({"a": 1, "b": 2})
        self.assertEqual(hash(copy.deepcopy(fd)), hash(fd))
        self.assertEqual(hash(pickle.loads(pickle.dumps(fd))), hash(fd))

    def test_nested_in_a_deepcopied_structure(self):
        payload = {"ctx": frozendict({"lang": "en_US"}), "other": [1]}
        clone = copy.deepcopy(payload)
        self.assertIsInstance(clone["ctx"], frozendict)
        self.assertEqual(clone["ctx"]["lang"], "en_US")  # type: ignore[index]


if __name__ == "__main__":
    unittest.main()


class TestFrozendictRejectsEveryMutator(unittest.TestCase):
    def setUp(self):
        self.frozen = frozendict({"name": "Joe", "age": 42})

    def test_delitem_rejected(self):
        with self.assertRaises(Exception):
            del self.frozen["name"]

    def test_setdefault_rejected(self):
        with self.assertRaises(Exception):
            self.frozen.setdefault("surname", "Jack")

    def test_pop_rejected(self):
        with self.assertRaises(Exception):
            self.frozen.pop("name", "Jack")
        with self.assertRaises(Exception):
            self.frozen.pop("surname", "Jack")

    def test_popitem_rejected(self):
        with self.assertRaises(Exception):
            self.frozen.popitem()

    def test_clear_rejected(self):
        with self.assertRaises(Exception):
            self.frozen.clear()


class TestFrozendictHashesNestedValues(unittest.TestCase):
    def test_hash_of_a_flat_mapping(self):
        hash(frozendict({"name": "Joe", "age": 42}))

    def test_hash_reaches_into_lists_and_tuples(self):
        hash(
            frozendict(
                {
                    "user_id": (42, "Joe"),
                    "line_ids": [(0, 0, {"values": [42]})],
                }
            )
        )


def _acyclic_freehash(arg: Any) -> int:
    try:
        return hash(arg)
    except TypeError:
        if isinstance(arg, Mapping):
            return hash(
                frozenset((key, _acyclic_freehash(val)) for key, val in arg.items())
            )
        if isinstance(arg, Iterable):
            return hash(frozenset(_acyclic_freehash(item) for item in arg))
        return id(arg)


class TestFreehashCycles(unittest.TestCase):
    def test_a_dict_that_holds_itself_hashes(self):
        localdict: dict[str, Any] = {"BASIC": 1000.0}
        localdict["localdict"] = localdict
        context = frozendict({"force_payslip_localdict": localdict})
        self.assertEqual(
            hash(context), hash(frozendict({"force_payslip_localdict": localdict}))
        )

    def test_equal_cycles_hash_equal(self):
        first: dict[str, Any] = {"a": 1}
        first["self"] = first
        second: dict[str, Any] = {"a": 1}
        second["self"] = second
        self.assertEqual(freehash(first), freehash(second))

    def test_a_list_that_holds_itself_hashes(self):
        items: list[Any] = [1]
        items.append(items)
        self.assertIsInstance(freehash(items), int)

    def test_a_cycle_through_a_frozendict_hashes(self):
        inner: dict[str, Any] = {}
        outer = frozendict({"inner": inner})
        inner["outer"] = outer
        self.assertIsInstance(hash(outer), int)

    def test_acyclic_values_hash_as_before(self):
        values = [
            {"a": 1, "b": [1, 2, {"c": {3, 4}}]},
            [{"x": [1, [2, [3]]]}, frozendict({"y": 2})],
            {"nested": frozendict({"z": [1, 2]})},
        ]
        for value in values:
            with self.subTest(value=value):
                self.assertEqual(freehash(value), _acyclic_freehash(value))
                self.assertEqual(
                    hash(frozendict({"v": value})),
                    hash(frozenset({("v", _acyclic_freehash(value))})),
                )


class TestHashFollowsMutableValues(unittest.TestCase):
    def test_a_mutated_list_value_hashes_like_its_new_content(self):
        frozen = frozendict(ids=[1])
        hash(frozen)
        frozen["ids"].append(2)
        self.assertEqual(hash(frozen), hash(frozendict(ids=[1, 2])))
        self.assertEqual({frozendict(ids=[1, 2]): "found"}.get(frozen), "found")

    def test_a_hashable_content_keeps_its_cached_hash(self):
        frozen = frozendict(lang="en_US", ids=(1, 2))
        hash(frozen)
        self.assertIsNotNone(getattr(frozen, "_hash", None))

    def test_a_plain_dict_value_hashes_like_an_equal_frozendict_value(self):
        self.assertEqual(
            hash(frozendict(a={"x": "s"})), hash(frozendict(a=frozendict(x="s")))
        )
