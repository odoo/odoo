"""An x2many whose comodel narrows its search by code nobody declared.

A comodel with an overridden ``_search`` and no ``_search_visibility_fields``
may read anything, so a user's slot of it is only as good as the last write of
the transaction: a write anywhere empties it. Before, only a write on the
comodel did, and a write on a model the override read left the slot stale.
"""

from odoo import fields, models
from odoo.orm.domain import Domain
from odoo.orm.model_test_env import model_test_env

_MOD = "test_x2many_scope_untracked_search"


class Box(models.Model):
    _name = "unt.box"
    _module = _MOD
    _description = "a box"

    name = fields.Char()
    line_ids = fields.One2many("unt.line", "box_id")


class Line(models.Model):
    _name = "unt.line"
    _module = _MOD
    _description = "a line whose search hides what a block names"

    name = fields.Char()
    box_id = fields.Many2one("unt.box")

    def _search(self, domain, *args, bypass_access=False, **kwargs):
        if not (self.env.su or bypass_access):
            blocks = self.env["unt.block"].sudo().search([])
            blocked = [line.id for line in blocks.mapped("line_id")]
            domain = Domain(domain) & Domain("id", "not in", blocked)
        return super()._search(domain, *args, bypass_access=bypass_access, **kwargs)


class Block(models.Model):
    _name = "unt.block"
    _module = _MOD
    _description = "a block"

    line_id = fields.Many2one("unt.line")


class IrModelAccess(models.AbstractModel):
    _name = "ir.model.access"
    _module = _MOD + "_access"
    _description = "ir.model.access (test stub)"

    def check(self, model, mode="read", raise_exception=True):
        return True


class IrRule(models.AbstractModel):
    _name = "ir.rule"
    _module = _MOD + "_rules"
    _description = "ir.rule (test stub): no rule"

    def _get_domain_accessible_records(self, model_name, mode="read"):
        return Domain.TRUE


def test_a_write_on_what_an_undeclared_search_reads_empties_the_user_slot():
    with model_test_env(Box, Line, Block, IrModelAccess, IrRule) as env:
        user = env["res.users"].create({"name": "reader"})
        box = env["unt.box"].create({"name": "box"})
        first, second = env["unt.line"].create(
            [{"name": "l1", "box_id": box.id}, {"name": "l2", "box_id": box.id}]
        )
        block = env["unt.block"].create({"line_id": second.id})
        env.invalidate_all()

        user_box = box.with_env(env(user=user.id, su=False))
        assert user_box.line_ids == first.with_env(user_box.env)
        block.line_id = first
        assert user_box.line_ids.ids == [second.id]
