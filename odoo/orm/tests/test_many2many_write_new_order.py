"""`write_new` compared the old and new relations with `OrderedSet.__eq__`,
which ignores order -- while the field carries the commands' order into the
cache (`_apply_relation_delta` stores `tuple(...)`). A `set()` that only
reorders was therefore judged unchanged and dropped."""

from odoo import api, fields, models
from odoo.fields import Command
from odoo.orm.model_test_env import model_test_env

_MOD = "test_many2many_write_new_order"


class Tag(models.Model):
    _name = "m2wn.tag"
    _module = _MOD
    _description = "tag"
    _log_access = False

    name = fields.Char()


class Doc(models.Model):
    _name = "m2wn.doc"
    _module = _MOD
    _description = "doc"
    _log_access = False

    name = fields.Char()
    tag_ids = fields.Many2many("m2wn.tag")
    computed_tag_ids = fields.Many2many(
        "m2wn.tag",
        relation="m2wn_doc_computed_tag_rel",
        compute="_compute_tags",
        readonly=False,
    )

    @api.depends("name")
    def _compute_tags(self):
        for record in self:
            record.computed_tag_ids = record.computed_tag_ids


def _tags(env):
    return env["m2wn.tag"].create([{"name": n} for n in "ab"])


def test_a_reorder_on_a_new_record_is_applied():
    with model_test_env(Tag, Doc) as env:
        a, b = _tags(env)
        record = env["m2wn.doc"].new({"name": "n"})
        record.write({"tag_ids": [Command.set([a.id, b.id])]})
        assert record.tag_ids.mapped("name") == ["a", "b"]

        record.write({"tag_ids": [Command.set([b.id, a.id])]})
        assert record.tag_ids.mapped("name") == ["b", "a"]


def test_a_reorder_of_a_non_stored_many2many_is_applied():
    # the shape where the commands' order is observable on a read: a stored
    # one is re-sorted into the comodel's order when it is fetched
    with model_test_env(Tag, Doc) as env:
        a, b = _tags(env)
        record = env["m2wn.doc"].new({"name": "n"})
        record.write({"computed_tag_ids": [Command.set([a.id, b.id])]})
        assert record.computed_tag_ids.mapped("name") == ["a", "b"]

        record.write({"computed_tag_ids": [Command.set([b.id, a.id])]})
        assert record.computed_tag_ids.mapped("name") == ["b", "a"]


def test_the_same_order_written_twice_is_still_unchanged():
    with model_test_env(Tag, Doc) as env:
        a, b = _tags(env)
        record = env["m2wn.doc"].new({"name": "n"})
        record.write({"tag_ids": [Command.set([a.id, b.id])]})
        record.write({"tag_ids": [Command.set([a.id, b.id])]})
        assert record.tag_ids.mapped("name") == ["a", "b"]


def test_a_membership_change_is_still_applied():
    with model_test_env(Tag, Doc) as env:
        a, b = _tags(env)
        record = env["m2wn.doc"].new({"name": "n"})
        record.write({"tag_ids": [Command.set([a.id])]})
        record.write({"tag_ids": [Command.set([a.id, b.id])]})
        assert set(record.tag_ids.mapped("name")) == {"a", "b"}
