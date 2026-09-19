import typing
from contextlib import contextmanager

import pytest

from odoo.db import FunctionStatus
from odoo.libs import sql
from odoo.orm.runtime.registry import Registry


class _Field:
    column_type = ("varchar", "varchar")
    store = True
    translate = False
    company_dependent = False
    manual = False

    def __init__(self, name, index, *, company_dependent=False):
        self.name = name
        self.index = index
        self.company_dependent = company_dependent

    def __repr__(self):
        return f"fake.model.{self.name}"


def _make_registry(*fields):
    class _Model:
        _table = "fake_model"
        _auto = True
        _abstract = False
        _fields = {f.name: f for f in fields}

    reg = object.__new__(Registry)
    reg.models = {"fake.model": typing.cast("typing.Any", _Model)}
    reg.has_trigram = False
    reg.has_unaccent = FunctionStatus.MISSING
    return reg


class _IdxCursor:
    def __init__(self, existing_rows):
        self._rows = existing_rows
        self.executed = []
        self.rowcount = 0

    def execute(self, query, params=None, **kwargs):
        self.executed.append(getattr(query, "code", query))

    def fetchall(self):
        return self._rows

    @contextmanager
    def savepoint(self, flush=True):
        yield


_IDX = sql.get_index_name("fake_model", "state")


def test_btree_to_btree_not_null_marks_stale():
    reg = _make_registry(_Field("state", "btree_not_null"))
    cr = _IdxCursor([(_IDX, "fake_model", "btree", False, False)])

    reg.check_indexes(cr, ["fake.model"])

    executed = "\n".join(cr.executed)
    assert "DROP INDEX" in executed
    assert "CREATE INDEX" in executed
    assert "IS NOT NULL" in executed


def test_btree_not_null_to_btree_marks_stale():
    reg = _make_registry(_Field("state", True))
    cr = _IdxCursor([(_IDX, "fake_model", "btree", True, False)])

    reg.check_indexes(cr, ["fake.model"])

    executed = "\n".join(cr.executed)
    assert "DROP INDEX" in executed
    creates = [q for q in cr.executed if "CREATE INDEX" in q]
    assert creates
    assert all("WHERE" not in q for q in creates)


def test_company_dependent_btree_not_null_expects_predicate():
    reg = _make_registry(_Field("state", "btree_not_null", company_dependent=True))
    cr = _IdxCursor([(_IDX, "fake_model", "btree", False, False)])

    reg.check_indexes(cr, ["fake.model"])

    executed = "\n".join(cr.executed)
    assert "DROP INDEX" in executed
    assert "IS NOT NULL" in executed


def test_matching_partial_index_not_rebuilt():
    reg = _make_registry(_Field("state", "btree_not_null"))
    cr = _IdxCursor([(_IDX, "fake_model", "btree", True, False)])

    reg.check_indexes(cr, ["fake.model"])

    assert len(cr.executed) == 1


def test_matching_plain_index_not_rebuilt():
    reg = _make_registry(_Field("state", True))
    cr = _IdxCursor([(_IDX, "fake_model", "btree", False, False)])

    reg.check_indexes(cr, ["fake.model"])

    assert len(cr.executed) == 1


def test_access_method_mismatch_still_stale():
    reg = _make_registry(_Field("state", True))
    cr = _IdxCursor([(_IDX, "fake_model", "gin", False, False)])

    reg.check_indexes(cr, ["fake.model"])

    executed = "\n".join(cr.executed)
    assert "DROP INDEX" in executed
    assert "CREATE INDEX" in executed


def test_invalid_index_value_raises_value_error():
    reg = _make_registry(_Field("state", "bogus"))
    cr = _IdxCursor([])

    with pytest.raises(ValueError, match="bogus"):
        reg.check_indexes(cr, ["fake.model"])


def test_model_names_may_be_an_iterator():
    reg = _make_registry(_Field("state", True))
    cr = _IdxCursor([])

    reg.check_indexes(cr, iter(["fake.model"]))

    executed = "\n".join(cr.executed)
    assert "CREATE INDEX" in executed


def test_unique_index_is_created_unique_and_partial():
    reg = _make_registry(_Field("state", "unique"))
    cr = _IdxCursor([])

    reg.check_indexes(cr, ["fake.model"])

    executed = "\n".join(cr.executed)
    assert "CREATE UNIQUE INDEX" in executed
    assert "IS NOT NULL" in executed


def test_btree_not_null_to_unique_marks_stale():
    reg = _make_registry(_Field("state", "unique"))
    cr = _IdxCursor([(_IDX, "fake_model", "btree", True, False)])

    reg.check_indexes(cr, ["fake.model"])

    executed = "\n".join(cr.executed)
    assert "DROP INDEX" in executed
    assert "CREATE UNIQUE INDEX" in executed


def test_unique_to_btree_not_null_marks_stale():
    reg = _make_registry(_Field("state", "btree_not_null"))
    cr = _IdxCursor([(_IDX, "fake_model", "btree", True, True)])

    reg.check_indexes(cr, ["fake.model"])

    executed = "\n".join(cr.executed)
    assert "DROP INDEX" in executed
    assert "CREATE UNIQUE INDEX" not in executed
