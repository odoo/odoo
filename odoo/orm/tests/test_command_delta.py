from typing import Any

from odoo import fields, models
from odoo.orm.fields.relational._commands import CommandDelta
from odoo.orm.model_test_env import model_test_env
from odoo.orm.primitives import Command, NewId

_MOD = "test_command_delta"


def _fold(*commands):
    return CommandDelta.fold(list(commands))


def test_a_replacement_supersedes_what_came_before_it_and_keeps_what_follows():
    delta = _fold(
        Command.link(1),
        Command.create({"a": 1}),
        Command.unlink(2),
        Command.set([7, 8]),
        Command.link(9),
        Command.create({"b": 2}),
    )
    assert delta.replaced and delta.set_ids == (7, 8)
    assert list(delta.linked) == [9]
    assert delta.created == [(0, {"b": 2})]
    assert not delta.unlinked
    assert list(delta.get_final_ids((1, 2, 3))) == [7, 8, 9]


def test_update_and_delete_survive_a_replacement():
    delta = _fold(Command.update(4, {"x": 1}), Command.delete(5), Command.clear())
    assert delta.updated == [(4, {"x": 1})]
    assert list(delta.deleted) == [5]
    assert list(delta.get_final_ids((4, 5, 6))) == []


def test_link_and_unlink_of_one_id_resolve_in_order():
    assert list(_fold(Command.link(5), Command.unlink(5)).get_final_ids((1,))) == [1]
    assert list(_fold(Command.unlink(5), Command.link(5)).get_final_ids((1,))) == [1, 5]
    assert list(_fold(Command.link(5), Command.delete(5)).get_final_ids((1,))) == [1]


def test_without_a_replacement_the_current_ids_are_the_base():
    delta = _fold(Command.unlink(2), Command.link(4))
    assert not delta.replaced
    assert list(delta.get_final_ids((1, 2, 3), created_ids=(10,))) == [1, 3, 4, 10]


def test_a_non_superseding_fold_keeps_everything_and_still_names_the_set():
    delta = CommandDelta.fold(
        [Command.create({"a": 1}), Command.link(2), Command.set([7])],
        superseding=False,
    )
    assert delta.replaced and delta.set_ids == (7,)
    assert delta.created == [(0, {"a": 1})]
    assert list(delta.linked) == [2]


def test_bare_entries_are_links_and_dicts_are_creates():
    delta = _fold(3, {"name": "n"}, Command.link(4))
    assert list(delta.linked) == [3, 4]
    assert delta.created == [(None, {"name": "n"})]


def test_ids_are_normalised_once_including_an_int_set():
    delta = CommandDelta.fold(
        [(Command.SET, 0, 3), Command.link(4), Command.update(5, {})],
        lambda id_: id_ and NewId(id_),
    )
    assert all(isinstance(id_, NewId) for id_ in delta.set_ids)
    assert all(isinstance(id_, NewId) for id_ in delta.linked)
    assert isinstance(delta.updated[0][0], NewId)


class Tag(models.Model):
    _name = "cd.tag"
    _module = _MOD
    _description = "tag"

    name = fields.Char()


class Line(models.Model):
    _name = "cd.line"
    _module = _MOD
    _description = "line"
    _log_access = False

    name = fields.Char()
    node_id = fields.Many2one("cd.node")


class Node(models.Model):
    _name = "cd.node"
    _module = _MOD
    _description = "node"
    _log_access = False

    name = fields.Char()
    tag_ids = fields.Many2many("cd.tag")
    line_ids = fields.One2many("cd.line", "node_id")


def test_a_falsy_set_payload_clears_instead_of_raising():
    # an RPC client can send [[6, 0, false]] or [[6, 0, null]]
    payloads: tuple[Any, ...] = (False, None, [])
    for payload in payloads:
        delta = CommandDelta.fold([(Command.SET, 0, payload)])
        assert delta.replaced
        assert delta.set_ids == ()


def test_a_clear_after_a_link_leaves_the_field_empty_on_both_kinds():
    with model_test_env(Tag, Line, Node) as env:
        t1, t2 = env["cd.tag"].create([{"name": "a"}, {"name": "b"}])
        node = env["cd.node"].create({"name": "n", "tag_ids": [Command.link(t1.id)]})
        l1 = env["cd.line"].create({"name": "x", "node_id": node.id})
        node.write(
            {
                "tag_ids": [Command.link(t2.id), Command.clear()],
                "line_ids": [Command.link(l1.id), Command.clear()],
            }
        )
        assert node.tag_ids._ids == ()
        assert node.line_ids._ids == ()


def test_a_set_then_a_create_keeps_both_on_a_real_record():
    with model_test_env(Tag, Line, Node) as env:
        t1 = env["cd.tag"].create({"name": "a"})
        node = env["cd.node"].create({"name": "n"})
        node.write(
            {
                "tag_ids": [Command.set([t1.id]), Command.create({"name": "c"})],
                "line_ids": [Command.create({"name": "l"}), Command.link(0)][:1],
            }
        )
        assert set(node.tag_ids.mapped("name")) == {"a", "c"}
        assert node.line_ids.mapped("name") == ["l"]


def test_on_create_a_set_after_a_create_keeps_both_lines():
    with model_test_env(Tag, Line, Node) as env:
        orphan = env["cd.line"].create({"name": "orphan"})
        node = env["cd.node"].create(
            {"line_ids": [Command.create({"name": "c1"}), Command.set([orphan.id])]}
        )
        assert sorted(node.line_ids.mapped("name")) == ["c1", "orphan"]


def test_on_write_a_set_after_a_create_keeps_only_the_set_lines():
    with model_test_env(Tag, Line, Node) as env:
        node = env["cd.node"].create({"line_ids": [Command.create({"name": "s0"})]})
        keep = node.line_ids
        node.write(
            {"line_ids": [Command.create({"name": "new"}), Command.set(keep.ids)]}
        )
        assert node.line_ids.mapped("name") == ["s0"]


def test_new_records_fold_the_same_way():
    with model_test_env(Tag, Line, Node) as env:
        t1, t2 = env["cd.tag"].create([{"name": "a"}, {"name": "b"}])
        node = env["cd.node"].new(
            {
                "tag_ids": [
                    Command.link(t1.id),
                    Command.set([t2.id]),
                    Command.link(t1.id),
                ]
            }
        )
        assert [id_.origin for id_ in node.tag_ids._ids] == [t2.id, t1.id]
        node.line_ids = [Command.create({"name": "l1"}), Command.create({"name": "l2"})]
        assert node.line_ids.mapped("name") == ["l1", "l2"]
        node.line_ids = [Command.clear()]
        assert node.line_ids._ids == ()
