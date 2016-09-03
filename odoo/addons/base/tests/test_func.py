# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import functools
import unittest

from odoo.tools import frozendict
from odoo.tools.func import compose


class TestCompose(unittest.TestCase):
    def test_basic(self):
        str_add = compose(str, lambda a, b: a + b)
        self.assertEqual(str_add(1, 2), "3")

    def test_decorator(self):
        """ ensure compose() can be partially applied as a decorator
        """
        @functools.partial(compose, unicode)
        def mul(a, b):
            return a * b

        self.assertEqual(mul(5, 42), u"210")


class TestFrozendict(unittest.TestCase):
    def test_frozendict_immutable(self):
        """ Ensure that a frozendict is immutable. """
        vals = {'name': 'Joe', 'age': 42}
        frozen_vals = frozendict(vals)

        # check __setitem__, __delitem__
        with self.assertRaises(Exception):
            frozen_vals['surname'] = 'Jack'
        with self.assertRaises(Exception):
            frozen_vals['name'] = 'Jack'
        with self.assertRaises(Exception):
            del frozen_vals['name']

        # check update, setdefault, pop, popitem, clear
        with self.assertRaises(Exception):
            frozen_vals.update({'surname': 'Jack'})
        with self.assertRaises(Exception):
            frozen_vals.update({'name': 'Jack'})
        with self.assertRaises(Exception):
            frozen_vals.setdefault('surname', 'Jack')
        with self.assertRaises(Exception):
            frozen_vals.pop('surname', 'Jack')
        with self.assertRaises(Exception):
            frozen_vals.pop('name', 'Jack')
        with self.assertRaises(Exception):
            frozen_vals.popitem()
        with self.assertRaises(Exception):
            frozen_vals.clear()

    def test_frozendict_hash(self):
        """ Ensure that a frozendict is hashable. """
        # dict with simple values
        hash(frozendict({'name': 'Joe', 'age': 42}))

        # dict with tuples, lists, and embedded dicts
        hash(frozendict({
            'user_id': (42, 'Joe'),
            'line_ids': [(0, 0, {'values': [42]})],
        }))
