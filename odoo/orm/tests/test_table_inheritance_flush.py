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
        assert env._table_inheritance_tree("tree.leaf") == ()
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
        assert collector.fields_by_model == {"tree.leaf": {"kind"}}


def test_a_query_on_the_root_writes_the_leaf_rows_first():
    with model_test_env(Root, Leaf, Apart) as env:
        leaf = env["tree.leaf"].create({"name": "l", "kind": "old"})
        env.flush_all()
        leaf.kind = "new"
        assert env.cr.storage.get_row(leaf._table, leaf.id)["kind"] == "old"
        env.flush_query(SQL("SELECT 1", to_flush=[env["tree.root"]._fields["kind"]]))
        assert env.cr.storage.get_row(leaf._table, leaf.id)["kind"] == "new"
