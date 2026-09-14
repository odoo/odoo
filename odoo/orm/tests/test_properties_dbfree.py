import pytest

from odoo import fields, models
from odoo.orm.model_test_env import model_test_env

_MOD = "test_properties_dbfree"


class Board(models.Model):
    _name = "prp.board"
    _module = _MOD
    _description = "board holding the property definitions"
    _log_access = False

    name = fields.Char()
    defs = fields.PropertiesDefinition()


class Card(models.Model):
    _name = "prp.card"
    _module = _MOD
    _description = "card carrying property values"
    _log_access = False

    name = fields.Char()
    board_id = fields.Many2one("prp.board")
    owner_id = fields.Many2one("prp.board")
    props = fields.Properties(definition="board_id.defs")


@pytest.fixture
def env():
    with model_test_env(Board, Card) as env:
        board = env["prp.board"].create(
            {
                "name": "b",
                "defs": [
                    {"name": "prio", "type": "integer", "string": "Prio"},
                    {"name": "tag", "type": "char", "string": "Tag"},
                    {
                        "name": "state",
                        "type": "selection",
                        "string": "State",
                        "selection": [["open", "Open"], ["done", "Done"]],
                    },
                    {"name": "due", "type": "date", "string": "Due"},
                    {
                        "name": "ref",
                        "type": "many2one",
                        "string": "Ref",
                        "comodel": "prp.board",
                    },
                ],
            }
        )
        env["prp.card"].create(
            [
                {
                    "name": "a",
                    "board_id": board.id,
                    "props": {
                        "prio": 3,
                        "tag": "x",
                        "state": "open",
                        "due": "2026-01-15",
                        "ref": board.id,
                    },
                },
                {
                    "name": "b",
                    "board_id": board.id,
                    "props": {"prio": 1, "state": "done", "due": "2026-03-02"},
                },
                {
                    "name": "c",
                    "board_id": board.id,
                    "props": {"state": "bogus", "ref": 999},
                },
            ]
        )
        yield env


def test_the_definition_is_found_on_the_holder_without_sql(env):
    Card_ = env["prp.card"]
    assert Card_.get_property_definition("props.tag") == {
        "name": "tag",
        "type": "char",
        "string": "Tag",
    }
    assert Card_.get_property_definition("props.nothing") == {}


def test_a_search_on_a_property_value(env):
    Card_ = env["prp.card"]
    assert Card_.search([("props.prio", ">", 2)]).mapped("name") == ["a"]
    assert Card_.search([("props.tag", "=", "x")]).mapped("name") == ["a"]
    assert Card_.search([("props.state", "=", "done")]).mapped("name") == ["b"]


def test_read_group_by_property_shapes_each_type_as_the_sql_path(env):
    Card_ = env["prp.card"]
    rows = Card_._read_group([], ["props.tag"], ["__count"])
    assert rows == [("x", 1), (False, 2)]
    # an option the definition does not list groups as nothing, as the join answers NULL
    rows = Card_._read_group([], ["props.state"], ["__count"], order="props.state")
    assert [(r[0], r[1]) for r in rows] == [("done", 1), ("open", 1), (False, 1)]
    # a many2one property points at a record that must still exist
    board = env["prp.board"].search([], limit=1)
    rows = Card_._read_group([], ["props.ref"], ["__count"])
    assert [(r[0], r[1]) for r in rows] == [(board.id, 1), (False, 2)]
    rows = Card_._read_group([], ["props.due:month"], ["__count"])
    assert [(str(r[0]), r[1]) for r in rows] == [
        ("2026-01-01", 1),
        ("2026-03-01", 1),
        ("False", 1),
    ]
    with pytest.raises(NotImplementedError, match="tags"):
        env["prp.board"].search([], limit=1).write(
            {"defs": [{"name": "labels", "type": "tags", "string": "L", "tags": []}]}
        )
        Card_._read_group([], ["props.labels"], ["__count"])
