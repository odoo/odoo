import pytest

from odoo import fields, models
from odoo.orm.model_test_env import model_test_env


class Node(models.Model):
    _name = "r.node"
    _module = "odoo.addons.test_backend_row_operations_harness"
    _description = "a node with a parent and peers"

    name = fields.Char()
    parent_id = fields.Many2one("r.node")
    peer_ids = fields.Many2many("r.node", "r_node_peer_rel", "left_id", "right_id")
    counter = fields.Integer()
    other = fields.Integer()


class Scratch(models.TransientModel):
    _name = "r.scratch"
    _module = "odoo.addons.test_backend_row_operations_harness"
    _description = "a transient model the vacuum trims"

    name = fields.Char()


class TestHasCycle:
    def test_a_many2one_chain_closes_into_a_cycle(self):
        with model_test_env(Node) as env:
            a = env["r.node"].create({"name": "a"})
            b = env["r.node"].create({"name": "b", "parent_id": a.id})
            c = env["r.node"].create({"name": "c", "parent_id": b.id})
            assert not (a + b + c)._has_cycle("parent_id")
            a.parent_id = c
            assert a._has_cycle("parent_id")
            assert c._has_cycle("parent_id")
            stranger = env["r.node"].create({"name": "stranger"})
            assert not stranger._has_cycle("parent_id")

    def test_a_many2many_closes_into_a_cycle_through_the_relation_table(self):
        with model_test_env(Node) as env:
            a = env["r.node"].create({"name": "a"})
            b = env["r.node"].create({"name": "b"})
            c = env["r.node"].create({"name": "c"})
            a.peer_ids = b
            b.peer_ids = c
            assert not (a + b + c)._has_cycle("peer_ids")
            c.peer_ids = a
            assert a._has_cycle("peer_ids")
            assert (a + b + c)._has_cycle("peer_ids")
            # the relation is directed: a node the cycle never reaches is clean
            d = env["r.node"].create({"name": "d", "peer_ids": [(4, a.id)]})
            assert not d._has_cycle("peer_ids")

    def test_the_relation_must_point_at_the_model_itself(self):
        with model_test_env(Node) as env:
            node = env["r.node"].create({"name": "a"})
            with pytest.raises(ValueError, match="many2one or many2many"):
                node._has_cycle("counter")
            with pytest.raises(ValueError, match="Invalid field_name"):
                node._has_cycle("nope")

    def test_an_empty_recordset_has_no_cycle(self):
        with model_test_env(Node) as env:
            assert not env["r.node"]._has_cycle("parent_id")


class TestIncrementFieldsSkipLocked:
    def test_every_named_column_of_every_row_is_incremented(self):
        with model_test_env(Node) as env:
            nodes = env["r.node"].create(
                [{"name": "a", "counter": 3}, {"name": "b", "other": 7}]
            )
            assert nodes._increment_fields_skiplock("counter", "other")
            # the cache dropped the counters: the read answers the rows
            assert nodes.mapped("counter") == [4, 1]
            assert nodes.mapped("other") == [1, 8]

    def test_a_pending_write_lands_before_the_increment(self):
        with model_test_env(Node) as env:
            node = env["r.node"].create({"name": "a", "counter": 3})
            node.counter = 10
            assert node._increment_fields_skiplock("counter")
            assert node.counter == 11

    def test_a_missing_row_is_not_counted(self):
        with model_test_env(Node) as env:
            node = env["r.node"].create({"name": "a"})
            gone = env["r.node"].browse(node.id + 100)
            assert not gone._increment_fields_skiplock("counter")
            assert (node + gone)._increment_fields_skiplock("counter")

    def test_only_integer_columns_qualify(self):
        with model_test_env(Node) as env:
            node = env["r.node"].create({"name": "a"})
            with pytest.raises(ValueError, match="not an integer"):
                node._increment_fields_skiplock("name")

    def test_an_empty_recordset_touches_nothing(self):
        with model_test_env(Node) as env:
            assert not env["r.node"]._increment_fields_skiplock("counter")


class TestTransientVacuum:
    def test_the_backlog_probe_answers_from_the_row_count(self):
        with model_test_env(Scratch) as env:
            rows = env["r.scratch"].create([{"name": str(i)} for i in range(3)])
            rows.flush_recordset()
            assert env.backend.has_rows_beyond(env["r.scratch"], 2)
            assert not env.backend.has_rows_beyond(env["r.scratch"], 3)

    def test_nothing_over_the_count_leaves_the_rows(self):
        with model_test_env(Scratch) as env:
            rows = env["r.scratch"].create([{"name": str(i)} for i in range(3)])
            assert env["r.scratch"]._remove_transient_rows_over_count(5) == 0
            assert rows.exists() == rows

    def test_over_the_count_removes_the_rows_old_enough(self):
        with model_test_env(Scratch) as env:
            rows = env["r.scratch"].create([{"name": str(i)} for i in range(3)])
            # the rows are younger than the minimum age, so the vacuum keeps them
            assert env["r.scratch"]._remove_transient_rows_over_count(1) == 0
            assert rows.exists() == rows
            old = env["r.scratch"].search([], order="id")[:2]
            # write_date is the ORM's own: aged on the rows, as time would
            env.cr.storage.update_rows(
                "r_scratch",
                [
                    (id_, {"write_date": env.cr.now().replace(year=2000)})
                    for id_ in old.ids
                ],
            )
            old.invalidate_recordset(["write_date"])
            assert env["r.scratch"]._remove_transient_rows_over_count(1) == 2
            assert rows.exists() == rows[2]
