import typing

from odoo.orm.components.storage import DictBackend
from odoo.orm.runtime._backend_memory import InMemoryBackend
from odoo.orm.runtime.backend import (
    ColumnStore,
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


from odoo import fields, models  # noqa: E402
from odoo.orm.model_test_env import model_test_env  # noqa: E402

_MOD = "test_column_store_contract"


class Claim(models.Model):
    _name = "cs.claim"
    _module = _MOD
    _description = "a row with a unique code and a nullable qty"
    _log_access = False

    code = fields.Char()
    qty = fields.Integer()
    _code_uniq = models.Constraint("unique(code)", "code must be unique")


def test_in_memory_try_write_refuses_a_unique_duplicate_like_postgresql():
    with model_test_env(Claim, check_cache=False) as env:
        a = env["cs.claim"].create({"code": "X"})
        b = env["cs.claim"].create({"code": "Y"})
        env.flush_all()
        columns = env.backend.columns
        assert columns.try_write(env["cs.claim"], "code", b.id, "X") is False
        assert columns.read(env["cs.claim"], "code", [b.id]) == {b.id: "Y"}
        assert columns.try_write(env["cs.claim"], "code", b.id, "Z") is True
        assert columns.read(env["cs.claim"], "code", [b.id]) == {b.id: "Z"}
        # rewriting a row's own value is not a duplicate
        assert columns.try_write(env["cs.claim"], "code", a.id, "X") is True


def test_in_memory_fetch_and_add_mirrors_the_sql_twin():
    import pytest

    with model_test_env(Claim, check_cache=False) as env:
        rec = env["cs.claim"].create({"code": "X", "qty": 4})
        null = env["cs.claim"].create({"code": "Y"})
        env.flush_all()
        columns = env.backend.columns
        assert columns.fetch_and_add(env["cs.claim"], "qty", rec.id, 5) == 4
        assert columns.read(env["cs.claim"], "qty", [rec.id]) == {rec.id: 9}
        # NULL propagates: the old value is None and NULL + delta stays NULL
        assert columns.fetch_and_add(env["cs.claim"], "qty", null.id, 5) is None
        assert columns.read(env["cs.claim"], "qty", [null.id]) == {null.id: None}
        with pytest.raises(ValueError):
            columns.fetch_and_add(env["cs.claim"], "qty", 999999, 5)
