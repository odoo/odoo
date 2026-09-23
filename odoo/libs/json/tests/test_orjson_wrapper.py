import datetime
import json
import unittest

from odoo.libs.json.orjson_wrapper import OPT_SORT_KEYS, dumps, dumps_bytes


class TestWhatOrjsonRefuses(unittest.TestCase):
    def test_an_integer_past_64_bits_is_written_exactly(self):
        self.assertEqual(dumps(2**64), "18446744073709551616")
        self.assertEqual(json.loads(dumps_bytes({"n": -(2**70)})), {"n": -(2**70)})

    def test_a_lone_surrogate_is_escaped(self):
        self.assertEqual(json.loads(dumps({"a": "x\ud800"})), {"a": "x\ud800"})

    def test_the_fallback_keeps_orjson_shape(self):
        payload = {
            "b": [2**64, float("nan")],
            datetime.date(2024, 1, 2): 1,
            "a": 1,
        }
        self.assertEqual(
            dumps(payload, option=OPT_SORT_KEYS),
            '{"2024-01-02":1,"a":1,"b":[18446744073709551616,null]}',
        )

    def test_what_neither_can_write_still_raises(self):
        with self.assertRaises(TypeError):
            dumps({(1, 2): 1})
