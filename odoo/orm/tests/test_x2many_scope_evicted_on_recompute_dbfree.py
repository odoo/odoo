"""A recompute of a rule-tested stored computed evicts user x2many slots.

The eviction of x2many user scopes whose read rule tests a written field
used to run only from write(). A stored computed field is written through
the protected branch of Field.__set__ during recompute, which bypasses
write(): a recompute that moves a record in or out of a user's rule left
that user's cached x2many slots stale (same family as the write-path
eviction, reached through the compute instead of a direct write).
"""

from odoo import api, fields, models
from odoo.exceptions import AccessError
from odoo.orm.domain import Domain
from odoo.orm.model_test_env import model_test_env

_MOD = "test_x2many_scope_evicted_on_recompute"


class Order(models.Model):
    _name = "sre.order"
    _module = _MOD
    _description = "order"

    name = fields.Char()
    line_ids = fields.One2many("sre.line", "order_id")


class Line(models.Model):
    _name = "sre.line"
    _module = _MOD
    _description = "line"

    order_id = fields.Many2one("sre.order")
    value = fields.Integer()
    hidden = fields.Boolean(compute="_compute_hidden", store=True)

    @api.depends("value")
    def _compute_hidden(self):
        for line in self:
            line.hidden = line.value < 0


class IrModelAccess(models.AbstractModel):
    _name = "ir.model.access"
    _module = _MOD + "_access"
    _description = "ir.model.access (test stub): everything allowed"

    def check(self, model, mode="read", raise_exception=True):
        return True


class IrRule(models.AbstractModel):
    _name = "ir.rule"
    _module = _MOD + "_rules"
    _description = "ir.rule (test stub): hidden lines are unreadable"

    def _get_domain_accessible_records(self, model_name, mode="read"):
        if mode == "read" and model_name == "sre.line":
            return Domain("hidden", "=", False)
        return Domain.TRUE

    def _prepare_access_error(self, operation, records):
        return AccessError(f"{operation} denied on {records}")


def test_a_recompute_of_the_rule_field_evicts_the_user_slot():
    with model_test_env(Order, Line, IrModelAccess, IrRule) as env:
        user = env["res.users"].create({"name": "u"})
        order = env["sre.order"].create({"name": "o"})
        keep = env["sre.line"].create({"order_id": order.id, "value": 1})
        flip = env["sre.line"].create({"order_id": order.id, "value": 2})
        env.flush_all()

        uenv = env(user=user.id, su=False)
        uorder = uenv["sre.order"].browse(order.id)
        assert set(uorder.line_ids._ids) == {keep.id, flip.id}  # warm the slot

        # write the DEPENDENCY, not the rule field: hidden recomputes to True
        # through the protected Field.__set__ branch, never through write()
        flip.write({"value": -5})
        env.flush_all()
        assert flip.hidden is True

        assert set(uorder.line_ids._ids) == {keep.id}, (
            "the user's slot still lists the line its read rule now hides"
        )


def test_a_recompute_that_hides_nothing_still_matches_the_search():
    with model_test_env(Order, Line, IrModelAccess, IrRule) as env:
        user = env["res.users"].create({"name": "u"})
        order = env["sre.order"].create({"name": "o"})
        line = env["sre.line"].create({"order_id": order.id, "value": -3})
        env.flush_all()

        uenv = env(user=user.id, su=False)
        uorder = uenv["sre.order"].browse(order.id)
        assert set(uorder.line_ids._ids) == set()  # hidden from the start

        line.write({"value": 4})  # hidden recomputes to False
        env.flush_all()
        assert set(uorder.line_ids._ids) == {line.id}, (
            "the user's slot still hides the line its read rule now shows"
        )
