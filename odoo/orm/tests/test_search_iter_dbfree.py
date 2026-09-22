import sys

import pytest

from odoo import fields, models
from odoo.orm.model_test_env import model_test_env

_MOD = "test_search_iter_dbfree"


class Job(models.Model):
    _name = "iter.job"
    _module = _MOD
    _description = "job"

    name = fields.Char()
    done = fields.Boolean()


def test_search_iter_walks_the_domain_in_id_order_by_batches():
    with model_test_env(Job) as env:
        jobs = env["iter.job"].create([{"name": f"j{i}"} for i in range(7)])
        batches = list(
            env["iter.job"].search_iter([("done", "=", False)], batch_size=3)
        )
        assert [len(b) for b in batches] == [3, 3, 1]
        assert [r.id for b in batches for r in b] == jobs.ids


def test_search_iter_reads_each_batch_fresh_so_a_shrinking_domain_ends():
    with model_test_env(Job) as env:
        env["iter.job"].create([{"name": f"j{i}"} for i in range(5)])
        seen = 0
        for batch in env["iter.job"].search_iter([("done", "=", False)], batch_size=2):
            batch.done = True
            seen += len(batch)
        assert seen == 5
        assert not env["iter.job"].search([("done", "=", False)])


def test_search_iter_yields_nothing_for_an_empty_domain_and_refuses_a_bad_size():
    with model_test_env(Job) as env:
        assert list(env["iter.job"].search_iter([("done", "=", True)])) == []
        with pytest.raises(ValueError, match="batch_size"):
            next(env["iter.job"].search_iter([], batch_size=0))


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
