import pytest

from odoo import fields, models
from odoo.fields import Domain
from odoo.orm.model_test_env import model_test_env


class Node(models.Model):
    _name = "d.node"
    _module = "odoo.addons.test_descendants_harness"
    _description = "Descendants node"

    name = fields.Char()
    kind = fields.Char()
    parent_id = fields.Many2one("d.node")
    active = fields.Boolean(default=True)


def _tree(env) -> dict:
    Nodes = env["d.node"]
    root = Nodes.create({"name": "root", "kind": "a"})
    child = Nodes.create({"name": "child", "kind": "a", "parent_id": root.id})
    return {
        "root": root,
        "child": child,
        "grand": Nodes.create({"name": "grand", "kind": "a", "parent_id": child.id}),
        "other_kind": Nodes.create(
            {"name": "other", "kind": "b", "parent_id": root.id}
        ),
        "inactive": Nodes.create(
            {"name": "off", "kind": "a", "parent_id": root.id, "active": False}
        ),
        "stranger": Nodes.create({"name": "stranger", "kind": "a"}),
    }


def _ids(tree: dict, *names: str) -> set[int]:
    return {tree[name].id for name in names}


def test_descendants_walks_the_whole_tree_from_the_roots():
    with model_test_env(Node) as env:
        tree = _tree(env)
        query = env.backend.descendants(
            env["d.node"].with_context(active_test=False),
            "parent_id",
            [tree["root"].id],
            domain=Domain.TRUE,
            step_domain=Domain.TRUE,
        )
        assert set(query.get_result_ids()) == _ids(
            tree, "root", "child", "grand", "other_kind", "inactive"
        )


def test_descendants_applies_the_domain_the_step_domain_and_same_columns():
    with model_test_env(Node) as env:
        tree = _tree(env)
        query = env.backend.descendants(
            env["d.node"].with_context(active_test=False),
            "parent_id",
            [tree["root"].id, tree["stranger"].id],
            domain=Domain("active", "=", True),
            step_domain=Domain("name", "!=", "grand"),
            same_columns=("kind",),
        )
        assert set(query.get_result_ids()) == _ids(tree, "root", "child", "stranger")


def test_child_of_uses_the_closure_on_a_model_without_parent_store():
    with model_test_env(Node) as env:
        tree = _tree(env)
        found = env["d.node"].search([("id", "child_of", tree["root"].id)])
        assert set(found.ids) == _ids(tree, "root", "child", "grand", "other_kind")


def test_has_cycle_walks_the_relation_in_memory():
    with model_test_env(Node) as env:
        tree = _tree(env)
        assert not tree["root"]._has_cycle("parent_id")
        tree["root"].parent_id = tree["grand"]
        assert tree["root"]._has_cycle("parent_id")
        assert tree["child"]._has_cycle("parent_id")
        assert not tree["stranger"]._has_cycle("parent_id")


class Leaf(models.Model):
    _name = "d.leaf"
    _module = "odoo.addons.test_descendants_harness"
    _description = "a model with no parent field"

    name = fields.Char()
    node_id = fields.Many2one("d.node")


def test_child_of_without_a_parent_field_names_what_is_missing():
    with model_test_env(Node, Leaf) as env:
        leaf = env["d.leaf"].create({"name": "leaf"})
        with pytest.raises(ValueError, match=r"d\.leaf\.parent_id: no such field"):
            env["d.leaf"].search([("id", "child_of", leaf.id)])
        # the many2one names its comodel, whose parent field exists
        tree = _tree(env)
        leaf.node_id = tree["child"]
        assert env["d.leaf"].search([("node_id", "child_of", tree["root"].id)]) == leaf


class Rank(models.Model):
    _name = "d.rank"
    _module = "odoo.addons.test_descendants_harness"
    _description = "Descendants node with an integer same-column"

    name = fields.Char()
    rank = fields.Integer()
    parent_id = fields.Many2one("d.rank")


def test_same_columns_tells_a_stored_zero_apart_from_null():
    # COALESCE(col::text, '') on the SQL side: NULL is '', 0 is '0' -- a
    # zero-ranked child of a rank-less root is NOT in the closure
    with model_test_env(Rank) as env:
        Ranks = env["d.rank"]
        root = Ranks.create({"name": "root"})  # rank is NULL
        zero = Ranks.create({"name": "zero", "rank": 0, "parent_id": root.id})
        null = Ranks.create({"name": "null", "parent_id": root.id})
        env.flush_all()
        query = env.backend.descendants(
            Ranks,
            "parent_id",
            [root.id],
            domain=Domain.TRUE,
            step_domain=Domain.TRUE,
            same_columns=("rank",),
        )
        assert set(query.get_result_ids()) == {root.id, null.id}
        assert zero.id not in set(query.get_result_ids())
