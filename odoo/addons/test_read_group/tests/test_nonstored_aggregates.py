from odoo import Command
from odoo.tests import common


class TestNonStoredAggregates(common.TransactionCase):
    """A non-stored compute aggregates through the group's records: the SELECT
    carries the ids and the fold happens in Python, which is what a model used
    to spell as its own `_read_group_select` override."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Task = cls.env["test_read_group.task"]
        cls.tasks = cls.Task.create(
            [
                {"name": "a", "key": "x", "integer": 1},
                {"name": "b", "key": "x", "integer": 2},
                {"name": "c", "key": "y", "integer": 4},
                {"name": "d", "key": "y", "integer": 8},
                {"name": "e", "key": "z", "integer": 0},
            ]
        )
        cls.domain = [("id", "in", cls.tasks.ids)]

    def test_numeric_folds_match_python(self):
        groups = self.Task._read_group(
            self.domain,
            ["key"],
            [
                "integer_doubled:sum",
                "integer_doubled:avg",
                "integer_doubled:min",
                "integer_doubled:max",
                "integer_doubled:count",
                "integer_doubled:array_agg",
            ],
            order="key",
        )
        self.assertEqual(
            groups,
            [
                ("x", 6, 3.0, 2, 4, 2, [2, 4]),
                ("y", 24, 12.0, 8, 16, 2, [8, 16]),
                ("z", 0, 0.0, 0, 0, 1, [0]),
            ],
        )

    def test_boolean_folds_and_the_whole_table(self):
        groups = self.Task._read_group(
            self.domain, ["key"], ["is_big:bool_and", "is_big:bool_or"], order="key"
        )
        self.assertEqual(
            groups, [("x", False, False), ("y", True, True), ("z", False, False)]
        )
        [(total, biggest)] = self.Task._read_group(
            self.domain, [], ["integer_doubled:sum", "integer_doubled:max"]
        )
        self.assertEqual((total, biggest), (30, 16))

    def test_an_empty_group_folds_to_the_empty_value(self):
        # the aggregate of a group whose records have no value is the aggregate's
        # empty value, as a column of NULLs gives
        [(count, total)] = self.Task._read_group(
            [("id", "in", [])], [], ["integer_doubled:count", "integer_doubled:sum"]
        )
        self.assertEqual((count, total), (0, False))

    def test_sum_currency_converts_each_record(self):
        Model = self.env["test_read_group.aggregate.monetary"]
        eur, usd = self.env.ref("base.EUR"), self.env.ref("base.USD")
        self.env.company.currency_id = usd
        eur.rate_ids = [Command.clear()]
        eur.rate_ids = [
            Command.create(
                {
                    "name": "2000-01-01",
                    "rate": 0.5,
                    "company_id": self.env.company.id,
                }
            )
        ]
        records = Model.create(
            [
                {"name": "a", "currency_id": usd.id, "total_in_currency_id": 10.0},
                {"name": "a", "currency_id": eur.id, "total_in_currency_id": 5.0},
            ]
        )
        [(total,)] = Model._read_group(
            [("id", "in", records.ids)], [], ["total_twice:sum_currency"]
        )
        # 20 USD stays 20; 10 EUR at 0.5 EUR per USD is 20 USD
        self.assertEqual(total, 40.0)

    def test_a_related_non_stored_field_is_still_refused(self):
        # the fold is for a compute of the model's own; a non-stored related
        # field keeps its rule, which reads through the target under sudo only
        Model = self.env["test_read_group.aggregate.monetary"].with_user(
            self.env.ref("base.user_admin")
        )
        self.assertFalse(Model.env.su)
        with self.assertRaisesRegex(ValueError, "not stored|not a sudoed"):
            Model._read_group([], [], ["related_non_stored_currency_id:count"])
