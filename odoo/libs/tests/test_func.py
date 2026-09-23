import copy
import pickle
import unittest

from odoo.libs.func import lazy


class TestLazy(unittest.TestCase):
    def test_copy_of_evaluated_lazy(self):
        obj = lazy(lambda: 41 + 1)
        _ = obj + 0
        clone = copy.copy(obj)
        self.assertEqual(clone, 42)
        self.assertIsInstance(clone, lazy)

    def test_pickle_roundtrip_unevaluated(self):
        obj = lazy(lambda x: x + 1, 6)
        restored = pickle.loads(pickle.dumps(obj))
        self.assertEqual(restored, 7)
        self.assertIsInstance(restored, lazy)

    def test_round_with_ndigits(self):
        obj = lazy(lambda: 3.14159)
        self.assertEqual(round(obj, 2), 3.14)
        self.assertEqual(round(obj), 3)

    def test_next_on_iterator(self):
        obj = lazy(lambda: iter([1, 2, 3]))
        self.assertEqual(next(obj), 1)
        self.assertEqual(next(obj), 2)

    def test_three_arg_pow(self):
        obj = lazy(lambda: 3)
        self.assertEqual(pow(obj, 3, 5), 2)
        self.assertEqual(obj**2, 9)

    def test_memoized_once(self):
        calls = []

        def make():
            calls.append(1)
            return 10

        obj = lazy(make)
        self.assertEqual(obj + 0, 10)
        self.assertEqual(obj + 1, 11)
        self.assertEqual(len(calls), 1)


class TestLazyArithmetic(unittest.TestCase):
    def test_mixed_numeric_types_fall_back_to_the_reflected_operation(self):
        self.assertEqual(lazy(lambda: 1) + 1.5, 2.5)
        self.assertEqual(1.5 + lazy(lambda: 1), 2.5)
        self.assertEqual(lazy(lambda: 3) * 0.5, 1.5)
        self.assertEqual(lazy(lambda: 1) - 0.25, 0.75)
        self.assertEqual(0.25 - lazy(lambda: 1), -0.75)
        self.assertEqual(2.0 ** lazy(lambda: 3), 8.0)
        self.assertEqual(divmod(7.5, lazy(lambda: 2)), (3.0, 1.5))

    def test_two_lazies_combine(self):
        self.assertEqual(lazy(lambda: 2) * lazy(lambda: 0.5), 1.0)

    def test_in_place_operators_work_on_immutable_values(self):
        value = lazy(lambda: 1)
        value += 1
        self.assertEqual(value, 2)
        text = lazy(lambda: "a")
        text += "b"
        self.assertEqual(text, "ab")

    def test_in_place_operators_mutate_a_mutable_value(self):
        items = [1]
        value = lazy(lambda: items)
        value += [2]
        self.assertEqual(items, [1, 2])

    def test_an_unsupported_operation_still_raises_type_error(self):
        with self.assertRaises(TypeError):
            lazy(lambda: 1) + "a"


if __name__ == "__main__":
    unittest.main()


class TestLazyComparison(unittest.TestCase):
    def test_ordering_and_equality_force_the_value(self):
        self.assertTrue(lazy(lambda: 1) <= lazy(lambda: 42))
        self.assertFalse(lazy(lambda: 42) <= lazy(lambda: 1))
        self.assertTrue(lazy(lambda: 42) == lazy(lambda: 42))
        self.assertFalse(lazy(lambda: 1) == lazy(lambda: 42))
        self.assertFalse(lazy(lambda: 42) != lazy(lambda: 42))
        self.assertTrue(lazy(lambda: 1) != lazy(lambda: 42))

    def test_equality_delegates_to_an_unhashable_value(self):
        class Obj:
            __hash__ = None  # type: ignore[assignment]

            def __init__(self, num):
                self.num = num

            def __eq__(self, other):
                if isinstance(other, Obj):
                    return self.num == other.num
                msg = "Object does not have the correct type"
                raise ValueError(msg)

        self.assertTrue(lazy(lambda: Obj(42)) == lazy(lambda: Obj(42)))
        self.assertFalse(lazy(lambda: Obj(1)) == lazy(lambda: Obj(42)))
        self.assertFalse(lazy(lambda: Obj(42)) != lazy(lambda: Obj(42)))
        self.assertTrue(lazy(lambda: Obj(1)) != lazy(lambda: Obj(42)))
