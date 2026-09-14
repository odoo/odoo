import pytest

from odoo import fields, models
from odoo.orm.model_test_env import model_test_env
from odoo.orm.runtime.recordset_cache import CacheInvalidError

_MOD = "test_cache_check_dbfree"


class Item(models.Model):
    _name = "cc.item"
    _module = _MOD
    _description = "an item whose cache the checker compares with its row"
    _log_access = False

    name = fields.Char()
    amount = fields.Float(digits=(16, 2))
    data = fields.Binary(attachment=False)


def test_the_checker_reads_the_rows_through_the_column_store():
    with model_test_env(Item, check_cache=False) as env:
        item = env["cc.item"].create({"name": "a", "amount": 1.23, "data": b"x" * 2048})
        env.flush_all()
        assert env.cache.check(env) == []
        # a numeric column loads as a float, a binary under bin_size as its size
        assert item.with_context(bin_size=True).data == "2048 bytes"
        assert env.cache.check(env) == []
        item.amount = 4.56
        assert env.cache.check(env) == [], "a dirty value is not compared"
        env.flush_all()
        assert env.cache.check(env) == []
        env.cr.storage.update_rows(item._table, [(item.id, {"name": "b"})])
        [(record, field, values)] = env.cache.check(env, raise_on_invalid=False)
        assert (record, field.name, values) == (
            item,
            "name",
            {"cached": "a", "fetched": "b"},
        )
        with pytest.raises(CacheInvalidError, match="does not match"):
            env.cache.check(env)


def test_the_harness_checks_the_cache_when_the_test_ends():
    with pytest.raises(CacheInvalidError), model_test_env(Item) as env:
        item = env["cc.item"].create({"name": "a"})
        env.flush_all()
        env.cr.storage.update_rows(item._table, [(item.id, {"name": "b"})])
