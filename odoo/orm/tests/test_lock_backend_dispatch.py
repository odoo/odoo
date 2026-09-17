import sys

import pytest

from odoo import fields, models
from odoo.exceptions import LockError
from odoo.orm.model_test_env import model_test_env

_MOD = "test_lock_backend_dispatch"


class LockThing(models.Model):
    _name = "lock.thing"
    _module = _MOD
    _description = "row-lock model"

    name = fields.Char()


def test_lock_for_update_dispatches_to_backend():
    with model_test_env(LockThing) as env:
        recs = env["lock.thing"].create({"name": "a"}) + env["lock.thing"].create(
            {"name": "b"}
        )
        recs.lock_for_update()
        recs.lock_for_update(allow_referencing=True)


def test_lock_for_update_raises_on_missing_row():
    with model_test_env(LockThing) as env:
        with pytest.raises(LockError):
            env["lock.thing"].browse(999_999).lock_for_update()


def test_try_lock_for_update_returns_lockable_rows_in_order():
    with model_test_env(LockThing) as env:
        a = env["lock.thing"].create({"name": "a"})
        b = env["lock.thing"].create({"name": "b"})
        recs = a + b
        assert recs.try_lock_for_update()._ids == recs._ids
        assert recs.try_lock_for_update(limit=1)._ids == (a.id,)


def test_try_lock_with_new_ids_and_limit_follows_the_sql_rule():
    # the SQL twin: saturating new ids take the whole limit; otherwise the
    # limit buys real rows only and every new id rides along, in order
    with model_test_env(LockThing) as env:
        a = env["lock.thing"].create({"name": "a"})
        b = env["lock.thing"].create({"name": "b"})
        draft = env["lock.thing"].new({"name": "draft"})
        env.flush_all()
        mixed = a + b + draft
        assert mixed.try_lock_for_update(limit=2)._ids == (a.id, draft.id)
        assert mixed.try_lock_for_update(limit=1)._ids == (draft.id,)
        assert mixed.try_lock_for_update()._ids == mixed._ids


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
