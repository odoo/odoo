# -*- coding: utf-8 -*-
import functools

import pytest

from openerp.tools.func import compose
from openerp.tools import frozendict

def test_basic():
    str_add = compose(str, lambda a, b: a + b)
    assert str_add(1, 2) == '3'

def test_decorator():
    """ ensure compose() can be partially applied as a decorator
    """
    @functools.partial(compose, unicode)
    def mul(a, b):
        return a * b

    assert mul(5, 42) == u"210"

def test_frozendict_immutable():
    """ Ensure that a frozendict is immutable. """
    frozen_vals = frozendict({'name': 'Joe', 'age': 42})

    # check __setitem__, __delitem__
    with pytest.raises(Exception):
        frozen_vals['surname'] = 'Jack'
    with pytest.raises(Exception):
        frozen_vals['name'] = 'Jack'
    with pytest.raises(Exception):
        del frozen_vals['name']

    # check update, setdefault, pop, popitem, clear
    with pytest.raises(Exception):
        frozen_vals.update({'surname': 'Jack'})
    with pytest.raises(Exception):
        frozen_vals.update({'name': 'Jack'})
    with pytest.raises(Exception):
        frozen_vals.setdefault('surname', 'Jack')
    with pytest.raises(Exception):
        frozen_vals.pop('surname', 'Jack')
    with pytest.raises(Exception):
        frozen_vals.pop('name', 'Jack')
    with pytest.raises(Exception):
        frozen_vals.popitem()
    with pytest.raises(Exception):
        frozen_vals.clear()

def test_frozendict_hash():
    """ Ensure that a frozendict is hashable. """
    # dict with simple values
    hash(frozendict({'name': 'Joe', 'age': 42}))

    # dict with tuples, lists, and embedded dicts
    hash(frozendict({
        'user_id': (42, 'Joe'),
        'line_ids': [(0, 0, {'values': [42]})],
    }))
