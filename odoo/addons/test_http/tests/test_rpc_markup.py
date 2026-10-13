# Part of Odoo. See LICENSE file for full copyright and licensing details.

import enum
import json
import sys
from collections import UserDict

from markupsafe import Markup

from odoo.http.dispatcher import _markup_paths
from odoo.tests.common import BaseCase, tagged
from odoo.tools import json_default, lazy


class IntE(enum.IntEnum):
    A = 3


class FloatS(float):
    def __repr__(self):
        return 'nope'


@tagged('at_install', '-post_install')
class TestMarkupPaths(BaseCase):
    def assertPaths(self, obj, expected):
        """ Checks that ``_markup_paths(obj)`` is ``expected``, and that
        every path resolves to a string in the serialized ``obj``. """
        paths = _markup_paths(obj)
        self.assertEqual(paths, expected)
        parsed = json.loads(json.dumps(obj, default=json_default))
        for path in paths:
            value = parsed
            for key in path:
                value = value[key]
            self.assertIsInstance(value, str, f"path {path} should resolve to a string")

    def test_no_markup(self):
        self.assertPaths(None, [])
        self.assertPaths("<b>", [])
        self.assertPaths({'a': ["<b>", 1, 2.5, True, None]}, [])

    def test_root(self):
        self.assertPaths(Markup("<b>"), [[]])

    def test_nested(self):
        """ Paths are in document order """
        self.assertPaths(
            {
                'a': [1, Markup("<b>"), "<i>", (Markup("<u>"),)],
                'b': {'c': Markup("<s>"), 'd': "<s>"},
                'e': Markup("x"),
            },
            [['a', 1], ['a', 3, 0], ['b', 'c'], ['e']],
        )

    def test_default(self):
        """ Values converted by ``json_default`` are walked as well """
        self.assertPaths(
            {
                'mapping': UserDict({'a': Markup("x")}),
                'lazy': lazy(lambda: [Markup("x")]),
                'lazy_markup': lazy(lambda: Markup("x")),
            },
            [['mapping', 'a'], ['lazy', 0], ['lazy_markup']],
        )

    def test_keys(self):
        """ Path keys are the keys as serialized by json """
        keys = [
            Markup('m'), 1, -1, IntE.A, 1.5, 2.0, FloatS(2.5),
            float('nan'), float('inf'), float('-inf'), True, False, None,
        ]
        for key in keys:
            with self.subTest(key=key):
                [serialized] = json.loads(json.dumps({key: Markup("x")}))
                self.assertPaths({key: Markup("x")}, [[serialized]])

    def test_keys_overlap(self):
        """ Keys which are distinct in python but identical once serialized
        produce duplicate members, of which only the last one is kept when
        parsing.
        """
        for key, serialized in [
            (1, '1'), (IntE.A, '3'), (1.5, '1.5'), (float('nan'), 'NaN'),
            (True, 'true'), (False, 'false'), (None, 'null'),
        ]:
            with self.subTest(key=key):
                self.assertPaths({key: Markup("x"), serialized: 'x'}, [])
                self.assertPaths({serialized: 'x', key: Markup("x")}, [[serialized]])
                self.assertPaths({key: 'x', serialized: Markup("x")}, [[serialized]])
                self.assertPaths({serialized: Markup("x"), key: 'x'}, [])
        # non-str keys can also overlap one another
        self.assertPaths({1: Markup("x"), IntE.A: 'x', 3: Markup("x")}, [['1'], ['3']])
        self.assertPaths({1: 'x', 1.0: Markup("x")}, [['1']])  # same python key

    def test_shared(self):
        """ The same object can appear multiple times if it's not a cycle """
        shared = [Markup("x")]
        self.assertPaths({'a': shared, 'b': [shared]}, [['a', 0], ['b', 0, 0]])

    def test_cycle(self):
        a = []
        a.append({'a': a})
        with self.assertRaisesRegex(ValueError, "Circular reference"):
            _markup_paths(a)
        d = {}
        d['l'] = lazy(lambda: d)
        with self.assertRaisesRegex(ValueError, "Circular reference"):
            _markup_paths(d)

    def test_deep(self):
        """ Nesting is not limited by the recursion limit """
        depth = sys.getrecursionlimit() * 2
        obj = Markup("x")
        for _ in range(depth):
            obj = [obj]
        self.assertEqual(_markup_paths(obj), [[0] * depth])
