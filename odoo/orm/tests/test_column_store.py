import typing

from odoo.orm.components.storage import DictBackend
from odoo.orm.runtime.backend import (
    ColumnStore,
    InMemoryBackend,
    PostgresBackend,
    PostgresColumnStore,
)


class _Model:
    _table = "res_users"


def _model() -> typing.Any:
    return _Model()


def test_both_backends_carry_a_column_store():
    assert isinstance(PostgresBackend.columns, PostgresColumnStore)
    assert isinstance(PostgresBackend.columns, ColumnStore)
    assert isinstance(InMemoryBackend(DictBackend()).columns, ColumnStore)


def test_in_memory_column_store_writes_and_reads_outside_the_fields():
    storage = DictBackend()
    storage.put_rows("res_users", [{"id": 1, "login": "a"}, {"id": 2, "login": "b"}])
    columns = InMemoryBackend(storage).columns
    columns.write(_model(), "password", [(1, "$hash$"), (2, None)])
    assert columns.read(_model(), "password", [1, 2, 3]) == {1: "$hash$", 2: None}
    row = storage.get_row("res_users", 1)
    assert row is not None
    assert row["login"] == "a"


def test_in_memory_merge_json_layers_fallback_stored_and_value():
    storage = DictBackend()
    storage.put_rows("res_users", [{"id": 1, "name": {"en_US": "Hello"}}, {"id": 2}])
    columns = InMemoryBackend(storage).columns
    assert (
        columns.merge_json(_model(), "name", 1, {"en_US": "x"}, {"fr_FR": "Bonjour"})
        == 1
    )
    assert columns.read(_model(), "name", [1]) == {
        1: {"en_US": "Hello", "fr_FR": "Bonjour"}
    }
    # the fallback fills a missing en_US, a null entry deletes its key
    assert (
        columns.merge_json(
            _model(), "name", 2, {"en_US": "Fallback"}, {"fr_FR": "Salut"}
        )
        == 1
    )
    assert columns.read(_model(), "name", [2]) == {
        2: {"en_US": "Fallback", "fr_FR": "Salut"}
    }
    assert (
        columns.merge_json(
            _model(), "name", 2, {"en_US": None}, {"fr_FR": None, "en_US": None}
        )
        == 1
    )
    assert columns.read(_model(), "name", [2]) == {2: None}
    assert columns.merge_json(_model(), "name", 3, {}, {"fr_FR": "x"}) == 0
