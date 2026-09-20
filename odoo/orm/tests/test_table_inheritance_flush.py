from odoo import api, fields, models
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


class CountedRoot(models.Model):
    _name = "counted.root"
    _module = _MOD
    _description = "root whose leaf computes a stored field"
    _table = "counted_root"
    _table_inheritance_root = "counted_root"
    _log_access = False

    name = fields.Char()
    loud = fields.Char(compute="_compute_loud", store=True, recursive=True)
    hint = fields.Char(compute="_compute_hint", inverse="_inverse_hint")

    computed_ids: list = []
    hints_seen_through_root: list = []

    @api.depends("name")
    def _compute_loud(self):
        for record in self:
            type(self).computed_ids.append(record.id)
            record.loud = (record.name or "").upper()

    @api.depends("name")
    def _compute_hint(self):
        for record in self:
            record.hint = f"computed {record.name}"

    def _inverse_hint(self):
        through_root = self.env["counted.root"].browse(self.ids)
        type(self).hints_seen_through_root.extend(through_root.mapped("hint"))


class CountedLeaf(models.Model):
    _name = "counted.leaf"
    _module = _MOD
    _description = "leaf sharing the counted root's table"
    _inherit = ["counted.root"]
    _table = "counted_leaf"
    _table_inheritance_root = "counted_root"


def test_a_fetch_flushes_only_the_fetched_rows_of_the_siblings():
    # a compute pending on another row of the tree is not this fetch's
    # business: recomputing every pending sibling row on each fetch turned a
    # recursive compute over a chain of rows into a recursion over the whole
    # pending set, which is what took the production copy down
    with model_test_env(CountedRoot, CountedLeaf) as env:
        CountedRoot.computed_ids = []
        one = env["counted.leaf"].create({"name": "one"})
        other = env["counted.leaf"].create({"name": "other"})
        env.flush_all()
        one.name = "uno"
        other.name = "otro"
        leaf_loud = env["counted.leaf"]._fields["loud"]
        assert set(env.core.get_pending_ids(leaf_loud)) == {one.id, other.id}
        CountedRoot.computed_ids = []
        # inside a compute (something is protected) a recompute must not
        # expand to the pending set, and the fetch's tree flush must not either
        with env.protecting([leaf_loud], other):
            env["counted.root"].browse(one.id).fetch(["loud"])
        # a fetch computes nothing: a pending row keeps its mark and is
        # computed when it is read, so the compute of a batch never nests a
        # fetch that recomputes the batch
        assert CountedRoot.computed_ids == []
        assert one.id in env.core.get_pending_ids(leaf_loud)
        assert other.id in env.core.get_pending_ids(leaf_loud)
        assert env["counted.leaf"].browse(one.id).loud == "UNO"
        assert one.id not in env.core.get_pending_ids(leaf_loud)


def test_a_compute_done_through_one_model_is_done_for_its_siblings():
    # the row is one, so once the root computed it the leaf must not compute
    # it again on its own pending mark: with nine subtypes that repetition
    # nested one tree flush per sibling per row
    with model_test_env(CountedRoot, CountedLeaf) as env:
        root = env["counted.root"].create({"name": "one"})
        leaf = env["counted.leaf"].create({"name": "one"})
        env.flush_all()
        assert root.id == leaf.id
        CountedRoot.computed_ids = []
        root_loud = env["counted.root"]._fields["loud"]
        leaf_loud = env["counted.leaf"]._fields["loud"]
        env.add_to_compute(root_loud, root)
        env.add_to_compute(leaf_loud, leaf)
        leaf.invalidate_recordset(["loud"])
        assert leaf.loud == "ONE"
        assert leaf.id not in env.core.get_pending_ids(leaf_loud)
        assert root.id not in env.core.get_pending_ids(root_loud)
        assert CountedRoot.computed_ids == [leaf.id]


def test_a_protection_through_one_model_covers_its_siblings():
    # while the leaf computes a row, the root's read of the same row must see
    # the value as in progress, not go to storage for a stale one
    with model_test_env(CountedRoot, CountedLeaf) as env:
        root = env["counted.root"].create({"name": "one"})
        leaf = env["counted.leaf"].create({"name": "one"})
        env.flush_all()
        root_loud = env["counted.root"]._fields["loud"]
        leaf_loud = env["counted.leaf"]._fields["loud"]
        assert root_loud.tree_siblings == (leaf_loud,)
        with env.protecting([leaf_loud], leaf):
            assert env.is_protected(root_loud, root)
        assert not env.is_protected(root_loud, root)


def test_a_read_through_a_sibling_computes_where_the_row_is_scheduled():
    # the trigger scheduled the row on the root; the leaf reading it must
    # not compute a row it does not own, the root computes it and the mark
    # is done for both
    with model_test_env(CountedRoot, CountedLeaf) as env:
        root = env["counted.root"].create({"name": "one"})
        leaf = env["counted.leaf"].create({"name": "one"})
        env.flush_all()
        root_loud = env["counted.root"]._fields["loud"]
        leaf_loud = env["counted.leaf"]._fields["loud"]
        CountedRoot.computed_ids = []
        env.add_to_compute(root_loud, root)
        assert not env.core.is_pending(leaf_loud, leaf.id)
        assert env.core.is_pending_in_tree(leaf_loud, leaf.id)
        leaf.invalidate_recordset(["loud"])
        leaf.loud
        assert CountedRoot.computed_ids == [root.id]
        assert not env.core.is_pending(root_loud, root.id)


def test_a_compute_through_one_model_evicts_the_value_the_others_cached():
    # the root recomputed the row: the leaf's cached copy of that stored
    # value is stale and must be re-read, as after a write through the root
    with model_test_env(CountedRoot, CountedLeaf) as env:
        root = env["counted.root"].create({"name": "one"})
        leaf = env["counted.leaf"].create({"name": "one"})
        env.flush_all()
        leaf.invalidate_recordset(["loud"])
        leaf.loud
        assert "loud" in leaf._cache
        root_loud = env["counted.root"]._fields["loud"]
        root.name = "uno"
        env.add_to_compute(root_loud, root)
        assert root.loud == "UNO"
        assert "loud" not in leaf._cache, "the leaf must re-read what the root computed"


def test_a_protected_read_through_a_sibling_sees_the_value_being_written():
    # the leaf's write holds the new value in the leaf's cache and evicts the
    # root's copy; the inverse, protected, reads the row through the root and
    # must see that value, not the False a protected miss falls back to
    with model_test_env(CountedRoot, CountedLeaf) as env:
        leaf = env["counted.leaf"].create({"name": "one"})
        env.flush_all()
        CountedRoot.hints_seen_through_root = []
        leaf.hint = "written"
        assert CountedRoot.hints_seen_through_root == ["written"]
        root = env["counted.root"].browse(leaf.id)
        assert root.hint == "written"
