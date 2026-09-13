from odoo import Command, fields, models
from odoo.orm.model_test_env import model_test_env

_MOD = "test_new_record_sibling_one2many"


class Line(models.Model):
    _name = "sib.line"
    _module = _MOD
    _description = "line"

    move_id = fields.Many2one("sib.move")
    kind = fields.Char()
    amount = fields.Float()


class Move(models.Model):
    _name = "sib.move"
    _module = _MOD
    _description = "two one2many over one many2one, one narrower than the other"

    name = fields.Char()
    line_ids = fields.One2many("sib.line", "move_id")
    product_line_ids = fields.One2many(
        "sib.line", "move_id", domain=[("kind", "=", "product")]
    )
    total = fields.Float(compute="_compute_total")

    def _compute_total(self):
        for move in self:
            move.total = sum(move.line_ids.mapped("amount"))


def test_lines_given_to_one_one2many_of_a_new_record_stay_out_of_its_sibling():
    # the contract the onchange protocol stands on: a new record mirrors what
    # it was given, so the server only ever reports diffs on the lists the
    # client holds; a line echoed under a second list gets a fresh virtual id
    # there and comes back as a duplicate on the next round-trip
    with model_test_env(Line, Move) as env:
        move = env["sib.move"].new(
            {
                "name": "m",
                "product_line_ids": [
                    Command.create({"kind": "product", "amount": 200.0}),
                    Command.create({"kind": "product", "amount": 50.0}),
                ],
            }
        )
        assert len(move.product_line_ids) == 2
        assert move.product_line_ids.mapped("move_id") == move
        assert not move.line_ids
        assert move.total == 0.0


def test_lines_given_to_the_wide_one2many_stay_out_of_the_narrow_one():
    with model_test_env(Line, Move) as env:
        move = env["sib.move"].new(
            {"line_ids": [Command.create({"kind": "product", "amount": 1.0})]}
        )
        assert len(move.line_ids) == 1
        assert not move.product_line_ids
        assert move.total == 1.0


def test_a_new_line_pointing_at_a_new_move_respects_each_one2many_domain():
    with model_test_env(Line, Move) as env:
        move = env["sib.move"].new({"name": "m"})
        note = env["sib.line"].new({"move_id": move, "kind": "note"})
        product = env["sib.line"].new({"move_id": move, "kind": "product"})
        assert move.line_ids == note + product
        assert move.product_line_ids == product


def test_the_domain_holds_when_the_one2many_was_read_before_the_line_arrived():
    with model_test_env(Line, Move) as env:
        move = env["sib.move"].new({"name": "m"})
        assert not move.product_line_ids
        assert not move.line_ids
        note = env["sib.line"].new({"move_id": move, "kind": "note"})
        assert move.line_ids == note
        assert not move.product_line_ids
