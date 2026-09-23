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


class IrAccess(models.AbstractModel):
    _name = "ir.access"
    _module = _MOD + "_access"
    _description = "ir.access (test stub): no row narrows anything"

    def _policy_signature(self):
        return (self.env.uid, *self._get_access_context())

    def _get_access_context(self):
        company_ids = self.env.context.get("allowed_company_ids")
        yield tuple(company_ids) if company_ids else company_ids

    def _bound_access_rows(self, model_name, operation):
        return [Domain.TRUE], []


def test_a_write_on_what_an_undeclared_search_reads_empties_the_user_slot():
    with model_test_env(Box, Line, Block, IrAccess) as env:
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
