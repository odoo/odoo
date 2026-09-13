import pytest

from odoo import api, fields, models
from odoo.orm.model_test_env import model_test_env

_MOD = "test_unlink_sweeps_fresh_marks"


class AggNode(models.Model):
    _name = "agg.node"
    _module = _MOD
    _description = "Aggregating Node"

    name = fields.Char()
    parent_id = fields.Many2one("agg.node")
    child_ids = fields.One2many("agg.node", "parent_id")
    weight = fields.Integer(default=1)
    total = fields.Integer(compute="_compute_total", store=True, recursive=True)

    @api.depends("weight", "child_ids.total")
    def _compute_total(self):
        for node in self:
            node.total = node.weight + sum(child["total"] for child in node.child_ids)


class _IrModelData(models.Model):
    _name = "ir.model.data"
    _module = _MOD
    _description = "ir.model.data stub for the unlink flow"

    name = fields.Char()
    module = fields.Char()
    model = fields.Char()
    res_id = fields.Integer()
    noupdate = fields.Boolean()


class _IrAttachment(models.Model):
    _name = "ir.attachment"
    _module = _MOD
    _description = "ir.attachment stub for the unlink flow"

    name = fields.Char()
    res_model = fields.Char()
    res_id = fields.Integer()


@pytest.fixture
def env():
    gen = model_test_env(AggNode, _IrModelData, _IrAttachment)
    yield gen.__enter__()
    gen.__exit__(None, None, None)


def test_unlink_leaves_no_pending_compute_on_the_deleted_ids(env):
    Node = env["agg.node"]
    root = Node.create([{"name": "root"}])
    mid = Node.create([{"name": "mid", "parent_id": root.id}])
    Node.create([{"name": "leaf", "parent_id": mid.id}])
    env.flush_all()

    deleted_ids = set(mid._ids)
    mid.unlink()

    field = Node._fields["total"]
    pending = set(env.core.get_pending_ids(field))
    assert not (pending & deleted_ids), (
        f"unlink left {pending & deleted_ids} pending for {field} -- the "
        f"trigger walk re-marked the deleted ids after the sweep ran"
    )
