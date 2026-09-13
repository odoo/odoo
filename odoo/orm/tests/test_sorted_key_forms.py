import pytest

from odoo import fields, models
from odoo.orm.model_test_env import model_test_env

_MOD = "test_sorted_key_forms"


class Item(models.Model):
    _name = "sorted.item"
    _module = _MOD
    _description = "records to sort by their default order and by a named field"
    _order = "rank desc, id"

    name = fields.Char()
    rank = fields.Integer()


def _records(env):
    model = env["sorted.item"]
    return model.create(
        [
            {"name": "b", "rank": 1},
            {"name": "a", "rank": 3},
            {"name": "c", "rank": 2},
        ]
    )


def test_no_key_sorts_by_the_model_order():
    with model_test_env(Item) as env:
        recs = _records(env)
        assert recs.sorted().mapped("name") == ["a", "c", "b"]
        assert recs.sorted(key=None, reverse=True).mapped("name") == ["b", "c", "a"]


def test_a_named_field_sorts_by_that_field():
    with model_test_env(Item) as env:
        recs = _records(env)
        assert recs.sorted("name").mapped("name") == ["a", "b", "c"]
        assert recs.sorted("rank desc").mapped("rank") == [3, 2, 1]


def test_an_empty_order_string_is_refused_not_defaulted():
    with model_test_env(Item) as env:
        recs = _records(env)
        with pytest.raises(ValueError, match="Invalid order"):
            recs.sorted(key="")
