import pytest

from odoo import Command, fields, models
from odoo.orm.model_test_env import model_test_env

_MOD = "test_read_grouping_sets_dbfree"


class Person(models.Model):
    _name = "gs.person"
    _module = _MOD
    _description = "a person"
    _order = "name"

    name = fields.Char()


class Task(models.Model):
    _name = "gs.task"
    _module = _MOD
    _description = "a task"

    name = fields.Char()
    key = fields.Integer()
    integer = fields.Integer()
    date = fields.Date()
    owner_id = fields.Many2one("gs.person")
    user_ids = fields.Many2many("gs.person", "gs_task_user_rel", "task_id", "person_id")
    customer_ids = fields.Many2many(
        "gs.person", "gs_task_customer_rel", "task_id", "person_id"
    )


def _seed(env):
    mario, luigi = env["gs.person"].create([{"name": "Mario"}, {"name": "Luigi"}])
    env["gs.task"].create(
        [
            {
                "name": "Super Mario Bros.",
                "key": 1,
                "integer": 1,
                "date": "2024-01-15",
                "owner_id": mario.id,
                "user_ids": [Command.set((mario + luigi).ids)],
            },
            {
                "name": "Paper Mario",
                "key": 1,
                "integer": 2,
                "date": "2024-02-03",
                "owner_id": luigi.id,
                "user_ids": [Command.set(mario.ids)],
                "customer_ids": [Command.set(luigi.ids)],
            },
            {
                "name": "Luigi's Mansion",
                "key": 2,
                "integer": 3,
                "date": "2024-02-20",
                "owner_id": luigi.id,
                "user_ids": [Command.set(luigi.ids)],
                "customer_ids": [Command.set(mario.ids)],
            },
            {
                "name": "Donkey Kong",
                "key": 2,
                "customer_ids": [Command.set((mario + luigi).ids)],
            },
            {"name": "Untitled"},
        ]
    )
    return mario, luigi


CASES = [
    (
        [["key", "owner_id"], ["key"], ["owner_id"], []],
        ["__count", "integer:sum"],
        None,
        None,
    ),
    (
        [["user_ids", "customer_ids"], ["key"], ["user_ids"], ["customer_ids"], []],
        ["__count", "integer:sum"],
        None,
        None,
    ),
    (
        [["user_ids", "key"], ["key"], ["user_ids"], []],
        ["__count"],
        None,
        None,
    ),
    (
        [["user_ids", "customer_ids"], ["key"], ["user_ids"], []],
        ["__count", "integer:min", "integer:max", "integer:count_distinct"],
        "__count, user_ids, customer_ids, key",
        [
            "__count, user_ids, customer_ids",
            "__count, key",
            "__count, user_ids",
            "__count",
        ],
    ),
    (
        [["date:month", "key"], ["date:month"], ["key"], []],
        ["integer:sum", "__count"],
        "key, __count DESC, date:month",
        [
            "key, __count DESC, date:month",
            "__count DESC, date:month",
            "key, __count DESC",
            "__count DESC",
        ],
    ),
    (
        [["owner_id", "key"], ["key", "owner_id"], ["owner_id"]],
        ["integer:array_agg", "__count"],
        "owner_id DESC, key",
        ["owner_id DESC, key", "owner_id DESC, key", "owner_id DESC"],
    ),
]


@pytest.mark.parametrize(("grouping_sets", "aggregates", "order", "set_orders"), CASES)
def test_grouping_sets_answer_what_one_read_group_per_set_answers(
    grouping_sets, aggregates, order, set_orders
):
    # the same equivalence test_read_group asserts on PostgreSQL: one
    # _read_group per set, each with the order terms that set carries
    with model_test_env(Person, Task) as env:
        _seed(env)
        Tasks = env["gs.task"]
        set_orders = set_orders or [None] * len(grouping_sets)
        expected = [
            Tasks._read_group([], groupby, aggregates, order=set_order)
            for groupby, set_order in zip(grouping_sets, set_orders, strict=True)
        ]
        assert (
            Tasks._read_grouping_sets([], grouping_sets, aggregates, order) == expected
        )
        assert any(rows for rows in expected)


def test_a_domain_matching_nothing_answers_an_empty_list_per_set():
    with model_test_env(Person, Task) as env:
        _seed(env)
        result = env["gs.task"]._read_grouping_sets(
            [("key", "=", 99)], [["key"], []], ["__count", "integer:sum"]
        )
        assert result == [[], []]


class TestEmptyHaving:
    def test_the_aggregate_row_over_no_record_obeys_the_having_clause(self):
        with model_test_env(Person, Task) as env:
            _seed(env)
            Tasks = env["gs.task"]
            none = [("key", "=", 99)]
            assert Tasks._read_group(
                none, [], ["__count"], having=[("__count", "=", 0)]
            ) == [(0,)]
            assert (
                Tasks._read_group(none, [], ["__count"], having=[("__count", ">", 0)])
                == []
            )
            # SUM over no row is NULL: it equals nothing, and the row goes
            assert (
                Tasks._read_group(
                    none,
                    [],
                    ["__count", "integer:sum"],
                    having=[("integer:sum", "=", 0)],
                )
                == []
            )
            assert Tasks._read_group(
                none, [], ["__count", "integer:sum"], having=[("__count", "=", 0)]
            ) == [(0, False)]
