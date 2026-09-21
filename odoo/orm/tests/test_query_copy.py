"""A `Query` handed to a domain is the caller's argument, not a workspace."""

import typing

from odoo.tools import SQL, Query


class _Env:
    """A Query only keeps its env; copy() never touches it."""


def _query():
    query = Query(typing.cast("typing.Any", _Env()), "t")
    query.add_where(SQL("t.a = %s", 1))
    query._joins["j"] = (SQL("x"), SQL("y"), SQL("z"))
    query._order_groupby.append(SQL("t.b"))
    query._limit = 5
    return query


def test_a_copy_carries_the_state():
    original = _query()
    other = original.copy()
    assert other._where_clauses == original._where_clauses
    assert other._tables == original._tables
    assert other._joins == original._joins
    assert other._limit == original._limit
    assert other.table == original.table


def test_a_copy_shares_no_mutable_part():
    original = _query()
    other = original.copy()
    for slot in ("_where_clauses", "_tables", "_joins", "_order_groupby"):
        assert getattr(other, slot) is not getattr(original, slot), slot


def test_narrowing_the_copy_leaves_the_original_alone():
    original = _query()
    other = original.copy()
    other.add_where(SQL("t.b = %s", 2))
    assert len(other._where_clauses) == 2
    assert len(original._where_clauses) == 1


def test_every_slot_is_carried():
    original = _query()
    other = original.copy()
    for slot in Query.__slots__:
        assert hasattr(other, slot), slot
