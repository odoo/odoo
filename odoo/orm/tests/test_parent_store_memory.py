from odoo import fields, models
from odoo.orm.model_test_env import model_test_env

_MOD = "test_parent_store_memory"


class Node(models.Model):
    _name = "ps.node"
    _module = _MOD
    _description = "node"
    _parent_store = True
    _log_access = False

    name = fields.Char()
    parent_id = fields.Many2one("ps.node")
    parent_path = fields.Char(index=True)


def _tree(env):
    Node = env["ps.node"]
    root = Node.create({"name": "root"})
    child = Node.create({"name": "child", "parent_id": root.id})
    grand = Node.create({"name": "grand", "parent_id": child.id})
    return root, child, grand


def test_create_sets_the_path_from_the_parent():
    with model_test_env(Node) as env:
        root, child, grand = _tree(env)
        assert root.parent_path == f"{root.id}/"
        assert child.parent_path == f"{root.id}/{child.id}/"
        assert grand.parent_path == f"{root.id}/{child.id}/{grand.id}/"


def test_moving_a_subtree_rewrites_every_descendant():
    with model_test_env(Node) as env:
        root, child, grand = _tree(env)
        other = env["ps.node"].create({"name": "other"})
        child.write({"parent_id": other.id})
        env.invalidate_all()
        assert child.parent_path == f"{other.id}/{child.id}/"
        assert grand.parent_path == f"{other.id}/{child.id}/{grand.id}/"
        assert root.parent_path == f"{root.id}/"


def test_writing_the_same_parent_rewrites_nothing():
    with model_test_env(Node) as env:
        root, child, grand = _tree(env)
        before = grand.parent_path
        child.write({"parent_id": root.id})
        env.invalidate_all()
        assert grand.parent_path == before


def test_child_of_uses_the_maintained_path():
    with model_test_env(Node) as env:
        root, child, grand = _tree(env)
        found = env["ps.node"].search([("id", "child_of", root.id)])
        assert set(found.ids) == {root.id, child.id, grand.id}
