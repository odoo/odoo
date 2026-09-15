from odoo import fields, models
from odoo.orm import registration
from odoo.orm.model_test_env import model_test_env

_MOD = "test_manual_model_cleanup"


class CParent(models.Model):
    _name = "c.parent"
    _module = _MOD
    _description = "Cleanup Parent"

    name = fields.Char()


class CChild(models.Model):
    _name = "c.child"
    _module = _MOD
    _description = "Cleanup Child (custom, delegating)"
    _custom = True
    _inherits = {"c.parent": "parent_id"}

    parent_id = fields.Many2one(
        "c.parent", required=True, ondelete="cascade", delegate=True
    )
    note = fields.Char()


def test_cleanup_discards_from_inherits_children():
    with model_test_env(CParent, CChild) as env:
        parent_cls = env.registry["c.parent"]
        assert "c.child" in parent_cls._inherits_children

        registration._add_manual_models(env)

        assert "c.child" not in env.registry
        assert "c.child" not in parent_cls._inherit_children
        assert "c.child" not in parent_cls._inherits_children
