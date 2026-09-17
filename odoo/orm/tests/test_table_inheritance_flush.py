from odoo import fields, models
from odoo.libs.sql import SQL
from odoo.orm.domain import Domain
from odoo.orm.model_test_env import model_test_env
from odoo.orm.runtime._search_flush import _DependencyCollector

_MOD = "test_table_inheritance_flush"


class Root(models.Model):
    _name = "tree.root"
    _module = _MOD
    _description = "root of a table-inheritance tree"
    _table = "tree_root"
    _table_inheritance_root = "tree_root"
    _log_access = False

    name = fields.Char()
    kind = fields.Char()


class Leaf(models.Model):
    _name = "tree.leaf"
    _module = _MOD
    _description = "a table inheriting the root's"
    _inherit = ["tree.root"]
    _table = "tree_leaf"
    _table_inheritance_root = "tree_root"

    extra = fields.Char()


class Apart(models.Model):
    _name = "tree.apart"
    _module = _MOD
    _description = "a model outside the tree"
    _log_access = False

    kind = fields.Char()


def test_the_registry_indexes_the_tree_by_root_table():
    with model_test_env(Root, Leaf, Apart) as env:
        index = env.registry.model_names_by_inheritance_root
        assert set(index["tree_root"]) == {"tree.root", "tree.leaf"}
        assert env._table_inheritance_tree("tree.root") == ("tree.leaf",)
        assert env._table_inheritance_tree("tree.leaf") == ("tree.root",)
        assert env._table_inheritance_tree("tree.apart") == ()


def test_a_domain_on_the_root_flushes_the_same_field_on_every_leaf():
    with model_test_env(Root, Leaf, Apart) as env:
        collector = _DependencyCollector()
        collector.collect_domain(env["tree.root"], Domain("kind", "=", "x"))
        assert collector.fields_by_model == {
            "tree.root": {"kind"},
            "tree.leaf": {"kind"},
        }
        collector = _DependencyCollector()
        collector.collect_domain(env["tree.leaf"], Domain("kind", "=", "x"))
        assert collector.fields_by_model == {
            "tree.leaf": {"kind"},
            "tree.root": {"kind"},
        }


def test_a_query_on_the_root_writes_the_leaf_rows_first():
    with model_test_env(Root, Leaf, Apart) as env:
        leaf = env["tree.leaf"].create({"name": "l", "kind": "old"})
        env.flush_all()
        leaf.kind = "new"
        assert env.cr.storage.get_row(leaf._table, leaf.id)["kind"] == "old"
        env.flush_query(SQL("SELECT 1", to_flush=[env["tree.root"]._fields["kind"]]))
        assert env.cr.storage.get_row(leaf._table, leaf.id)["kind"] == "new"


# The DB-free storage keeps one table per model and knows nothing of
# PostgreSQL inheritance, so each pair below is a root row and a leaf row
# sharing an id: what the tree makes one row is here two rows kept in step
# by the flush and invalidation being tested.
def _root_and_leaf(env):
    root = env["tree.root"].create({"name": "r", "kind": "old"})
    leaf = env["tree.leaf"].create({"name": "l", "kind": "old", "extra": "e"})
    env.flush_all()
    assert root.id == leaf.id
    return root, leaf


def test_a_query_on_a_leaf_writes_the_root_rows_first():
    with model_test_env(Root, Leaf, Apart) as env:
        root, leaf = _root_and_leaf(env)
        root.kind = "new"
        assert env.cr.storage.get_row("tree_root", root.id)["kind"] == "old"
        env.flush_query(SQL("SELECT 1", to_flush=[leaf._fields["kind"]]))
        assert env.cr.storage.get_row("tree_root", root.id)["kind"] == "new"


def test_a_write_through_one_model_drops_the_value_the_others_cached():
    with model_test_env(Root, Leaf, Apart) as env:
        root, leaf = _root_and_leaf(env)
        assert root.kind == "old" and leaf.kind == "old"
        assert "kind" in leaf._cache

        root.write({"kind": "new"})
        assert "kind" not in leaf._cache, "the leaf must re-read the root's write"
        assert "extra" in leaf._cache, "a field the root lacks is untouched"

        leaf.kind = "newer"
        assert "kind" not in root._cache, "the root must re-read the leaf's write"


def test_a_fetch_on_a_leaf_writes_the_root_rows_first():
    with model_test_env(Root, Leaf, Apart) as env:
        root, leaf = _root_and_leaf(env)
        root.kind = "new"
        leaf.invalidate_recordset(["kind"])
        assert env.cr.storage.get_row("tree_root", root.id)["kind"] == "old"
        leaf.fetch(["kind"])
        assert env.cr.storage.get_row("tree_root", root.id)["kind"] == "new"


def test_flushing_a_leaf_model_writes_the_root_rows_too():
    # a raw query on the leaf table, preceded by the leaf's own flush_model
    # as raw callers do, must not read a row the root still holds dirty
    with model_test_env(Root, Leaf, Apart) as env:
        root, _leaf = _root_and_leaf(env)
        root.kind = "new"
        env["tree.leaf"].flush_model(["kind"])
        assert env.cr.storage.get_row("tree_root", root.id)["kind"] == "new"


def test_an_unlink_through_one_model_drops_what_the_others_cached():
    with model_test_env(Root, Leaf, Apart) as env:
        root, leaf = _root_and_leaf(env)
        assert root.kind == "old" and leaf.kind == "old"
        leaf.unlink()
        assert "kind" not in root._cache, "the root must not answer for a deleted row"
