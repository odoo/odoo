# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import functools

from odoo.tests.common import BaseCase
from odoo.tools import frozendict, lazy
from odoo import Command


class TestFrozendict(BaseCase):
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
            'line_ids': [Command.create({'values': [42]})],
        }))


class TestLazy(BaseCase):
    def test_lazy_compare(self):
        """ Ensure that a lazy can be compared with an other lazy. """
        self.assertEqual(lazy(lambda: 1) <= lazy(lambda: 42), True)
        self.assertEqual(lazy(lambda: 42) <= lazy(lambda: 1), False)
        self.assertEqual(lazy(lambda: 42) == lazy(lambda: 42), True)
        self.assertEqual(lazy(lambda: 1) == lazy(lambda: 42), False)
        self.assertEqual(lazy(lambda: 42) != lazy(lambda: 42), False)
        self.assertEqual(lazy(lambda: 1) != lazy(lambda: 42), True)

        # Object like recordset implement __eq__
        class Obj:
            def __init__(self, num):
                self.num = num

            def __eq__(self, other):
                if isinstance(other, Obj):
                    return self.num == other.num
                raise ValueError('Object does not have the correct type')

        self.assertEqual(lazy(lambda: Obj(42)) == lazy(lambda: Obj(42)), True)
        self.assertEqual(lazy(lambda: Obj(1)) == lazy(lambda: Obj(42)), False)
        self.assertEqual(lazy(lambda: Obj(42)) != lazy(lambda: Obj(42)), False)
        self.assertEqual(lazy(lambda: Obj(1)) != lazy(lambda: Obj(42)), True)
