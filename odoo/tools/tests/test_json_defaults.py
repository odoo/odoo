import dataclasses
import datetime
import json
import unittest

from odoo.libs.collections import ReadonlyDict
from odoo.libs.func import lazy
from odoo.tools.json import fast_dumps, json_default, orjson_default


@dataclasses.dataclass
class _Point:
    x: int = 1
    y: int = 2


CASES = {
    "datetime": datetime.datetime(2026, 8, 29, 12, 0, 0),
    "date": datetime.date(2026, 8, 29),
    "bytes": b"hi",
    "readonly_dict": ReadonlyDict({"a": 1}),
    "dataclass": _Point(),
}


class TestConversionPolicyIsShared(unittest.TestCase):
    def test_both_defaults_convert_every_case_identically(self):
        for name, value in CASES.items():
            with self.subTest(case=name):
                self.assertEqual(json_default(value), orjson_default(value))

    def test_a_dataclass_becomes_a_dict_not_its_repr(self):
        for fn in (json_default, orjson_default):
            with self.subTest(default=fn.__name__):
                self.assertEqual(fn(_Point()), {"x": 1, "y": 2})

    def test_a_lazy_encodes_like_its_value_through_both_encoders(self):
        cases = {**CASES, "tuple": (1, 2), "set": {3}, "native": [1, {"a": None}]}
        for name, value in cases.items():
            with self.subTest(case=name):
                expected = json.loads(json.dumps({"a": value}, default=json_default))
                for wrapped in (value, lazy(lambda v=value: v)):
                    self.assertEqual(
                        json.loads(fast_dumps({"a": wrapped}, default=orjson_default)),
                        expected,
                    )
                    self.assertEqual(
                        json.loads(json.dumps({"a": wrapped}, default=json_default)),
                        expected,
                    )

    def test_a_lazy_tuple_is_an_array_not_its_repr(self):
        self.assertEqual(
            fast_dumps({"a": lazy(lambda: (1, 2))}, default=orjson_default),
            '{"a":[1,2]}',
        )

    def test_an_unknown_object_still_falls_back_to_str(self):
        class Opaque:
            def __repr__(self):
                return "<opaque>"

        self.assertEqual(json_default(Opaque()), "<opaque>")
        self.assertEqual(orjson_default(Opaque()), "<opaque>")


if __name__ == "__main__":
    unittest.main()
