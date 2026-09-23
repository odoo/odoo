from odoo import Command, fields
from odoo.exceptions import AccessError
from odoo.tests import common, new_test_user

from odoo.addons.base.tests.common import make_access_row


class TestPrivateReadGroup(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.base_user = new_test_user(
            cls.env, login="Base User", groups="base.group_user"
        )

    def _create_related_fixtures(self):
        RelatedBar = self.env["test_read_group.related_bar"]
        RelatedFoo = self.env["test_read_group.related_foo"]
        RelatedBase = self.env["test_read_group.related_base"]

        bars = RelatedBar.create(
            [
                {"name": "bar_a"},
                {"name": False},
            ]
        )
        foos = RelatedFoo.create(
            [
                {"name": "foo_a_bar_a", "bar_id": bars[0].id},
                {"name": "foo_b_bar_false", "bar_id": bars[1].id},
                {"name": False, "bar_id": bars[0].id},
                {"name": False},
            ]
        )
        RelatedBase.create(
            [
                {"name": "base_foo_a_1", "foo_id": foos[0].id},
                {"name": "base_foo_a_2", "foo_id": foos[0].id},
                {"name": "base_foo_b_bar_false", "foo_id": foos[1].id},
                {"name": "base_false_foo_bar_a", "foo_id": foos[2].id},
                {"name": "base_false_foo", "foo_id": foos[3].id},
            ]
        )
        return bars, foos

    def test_simple_private_read_group(self):
        Model = self.env["test_read_group.aggregate"]
        partner_1 = self.env["res.partner"].create({"name": "z_one"})
        partner_2 = self.env["res.partner"].create({"name": "a_two"})
        Model.create({"key": 1, "partner_id": partner_1.id, "value": 1})
        Model.create({"key": 1, "partner_id": partner_1.id, "value": 2})
        Model.create({"key": 1, "partner_id": partner_2.id, "value": 3})
        Model.create({"key": 2, "partner_id": partner_2.id, "value": 4})
        Model.create({"key": 2, "partner_id": partner_2.id})
        Model.create({"key": 2, "value": 5})
        Model.create({"partner_id": partner_2.id, "value": 5})
        Model.create({"value": 6})
        Model.create({})

        with self.assertQueries(
            [
                """
            SELECT "test_read_group_aggregate"."key",
                   SUM("test_read_group_aggregate"."value")
            FROM "test_read_group_aggregate"
            GROUP BY "test_read_group_aggregate"."key"
            ORDER BY "test_read_group_aggregate"."key" ASC
        """
            ]
        ):
            self.assertEqual(
                Model._read_group([], groupby=["key"], aggregates=["value:sum"]),
                [
                    (1, 1 + 2 + 3),
                    (2, 4 + 5),
                    (False, 5 + 6),
                ],
            )

        with self.assertQueries(
            [
                """
            SELECT "test_read_group_aggregate"."key",
                   "test_read_group_aggregate"."partner_id",
                   SUM("test_read_group_aggregate"."value")
            FROM "test_read_group_aggregate"
            LEFT JOIN "res_partner" AS "test_read_group_aggregate__partner_id"
                ON ("test_read_group_aggregate"."partner_id" = "test_read_group_aggregate__partner_id"."id")
            GROUP BY "test_read_group_aggregate"."key",
                     "test_read_group_aggregate"."partner_id"
            ORDER BY "test_read_group_aggregate"."key" ASC,
                     ANY_VALUE("test_read_group_aggregate__partner_id"."complete_name") ASC,
                     ANY_VALUE("test_read_group_aggregate__partner_id"."id") DESC
        """
            ]
        ):
            self.assertEqual(
                Model._read_group(
                    [],
                    groupby=["key", "partner_id"],
                    aggregates=["value:sum"],
                    order="key, partner_id",
                ),
                [
                    (1, partner_2, 3),
                    (1, partner_1, 1 + 2),
                    (2, partner_2, 4),
                    (2, self.env["res.partner"], 5),
                    (False, partner_2, 5),
                    (False, self.env["res.partner"], 6),
                ],
            )

        with self.assertQueries(
            [
                """
            SELECT "test_read_group_aggregate"."key",
                   "test_read_group_aggregate"."partner_id",
                   SUM("test_read_group_aggregate"."value")
            FROM "test_read_group_aggregate"
            GROUP BY "test_read_group_aggregate"."key",
                     "test_read_group_aggregate"."partner_id"
            ORDER BY "test_read_group_aggregate"."key" ASC,
                     "test_read_group_aggregate"."partner_id" ASC
        """
            ]
        ):
            self.assertEqual(
                Model._read_group(
                    [], groupby=["key", "partner_id"], aggregates=["value:sum"]
                ),
                [
                    (1, partner_1, 1 + 2),
                    (1, partner_2, 3),
                    (2, partner_2, 4),
                    (2, self.env["res.partner"], 5),
                    (False, partner_2, 5),
                    (False, self.env["res.partner"], 6),
                ],
            )

    def test_limit_offset(self):
        Model = self.env["test_read_group.aggregate"]
        Model.create({"key": 1, "value": 1})
        Model.create({"key": 1, "value": 2})
        Model.create({"key": 1, "value": 3})
        Model.create({"key": 2, "value": 4})
        Model.create({"key": 2})
        Model.create({"key": 2, "value": 5})
        Model.create({})
        Model.create({"value": 6})

        self.assertEqual(
            Model._read_group([], groupby=["key"], aggregates=["value:sum"], limit=2),
            [
                (1, 1 + 2 + 3),
                (2, 4 + 5),
            ],
        )

        self.assertEqual(
            Model._read_group([], groupby=["key"], aggregates=["value:sum"], offset=1),
            [
                (2, 4 + 5),
                (False, 6),
            ],
        )

        self.assertEqual(
            Model._read_group(
                [],
                groupby=["key"],
                aggregates=["value:sum"],
                offset=1,
                limit=2,
                order="key DESC",
            ),
            [
                (2, 4 + 5),
                (1, 1 + 2 + 3),
            ],
        )

    def test_falsy_domain(self):
        Model = self.env["test_read_group.aggregate"]

        with self.assertQueryCount(0):
            result = Model._read_group(
                [("id", "in", [])], groupby=["partner_id"], aggregates=[]
            )
            self.assertEqual(result, [])

        with self.assertQueryCount(0):
            result = Model._read_group(
                [("id", "in", [])],
                groupby=[],
                aggregates=[
                    "__count",
                    "partner_id:count",
                    "partner_id:count_distinct",
                ],
            )
            self.assertEqual(result, [(0, 0, 0)])

    def test_prefetch_for_records(self):
        Model = self.env["test_read_group.aggregate"]
        Partner = self.env["res.partner"]
        partner_1 = Partner.create({"name": "z_one"})
        partner_2 = Partner.create({"name": "a_two"})
        Model.create({"key": 1, "partner_id": partner_1.id})
        Model.create({"key": 2, "partner_id": partner_2.id})

        self.env.invalidate_all()

        result = Model._read_group([], ["partner_id"], [])

        self.assertEqual(result, [(partner_1,), (partner_2,)])
        [[value1], [value2]] = result
        value1.name
        with self.assertQueryCount(0):
            value2.name

        self.env.invalidate_all()

        result = Model._read_group([], ["key"], ["partner_id:recordset"])
        self.assertEqual(result, [(1, partner_1), (2, partner_2)])
        [[__, value1], [__, value2]] = result
        value1.name
        with self.assertQueryCount(0):
            value2.name

    def test_ambiguous_field_name(self):
        Model = self.env["test_read_group.aggregate"]
        partner_1 = self.env["res.partner"].create({"name": "z_one"})
        Model.create(
            {
                "key": 1,
                "partner_id": partner_1.id,
                "value": 1,
                "display_name": "blabla",
            }
        )

        with self.assertQueries(
            [
                """
            SELECT NULLIF("test_read_group_aggregate"."display_name", ''),
                   "test_read_group_aggregate"."partner_id",
                   COUNT(*)
            FROM "test_read_group_aggregate"
            LEFT JOIN "res_partner" AS "test_read_group_aggregate__partner_id"
                ON ("test_read_group_aggregate"."partner_id" = "test_read_group_aggregate__partner_id"."id")
            GROUP BY NULLIF("test_read_group_aggregate"."display_name", ''),
                     "test_read_group_aggregate"."partner_id"
            ORDER BY ANY_VALUE("test_read_group_aggregate__partner_id"."complete_name") DESC,
                     ANY_VALUE("test_read_group_aggregate__partner_id"."id") ASC
        """
            ]
        ):
            result = Model._read_group(
                [],
                groupby=["display_name", "partner_id"],
                aggregates=["__count"],
                order="partner_id DESC",
            )
            self.assertEqual(result, [("blabla", partner_1, 1)])

    def test_bool_read_groups(self):
        Model = self.env["test_read_group.aggregate.boolean"]
        Model.create({"key": 1, "bool_and": True})
        Model.create({"key": 1, "bool_and": True})

        Model.create({"key": 2, "bool_and": True})
        Model.create({"key": 2, "bool_and": False})

        Model.create({"key": 3, "bool_and": False})
        Model.create({"key": 3, "bool_and": False})

        Model.create({"key": 4, "bool_and": True, "bool_or": True, "bool_array": True})
        Model.create({"key": 4})

        result = Model._read_group(
            [],
            groupby=["key"],
            aggregates=[
                "bool_and:bool_and",
                "bool_and:bool_or",
                "bool_and:array_agg",
            ],
        )
        self.assertEqual(
            result,
            [
                (1, True, True, [True, True]),
                (2, False, True, [True, False]),
                (3, False, False, [False, False]),
                (4, False, True, [True, False]),
            ],
        )

    def test_count_read_groups(self):
        Model = self.env["test_read_group.aggregate"]
        Model.create({"key": 1})
        Model.create({"key": 1})
        Model.create({})

        self.assertEqual(
            Model._read_group([], aggregates=["key:count"]),
            [(2,)],
        )

        self.assertEqual(
            Model._read_group([], aggregates=["key:count_distinct"]),
            [(1,)],
        )

    def test_array_read_groups(self):
        Model = self.env["test_read_group.aggregate"]
        Partner = self.env["res.partner"]
        partner_1 = Partner.create({"name": "test_array_read_groups_1"})
        partner_2 = Partner.create({"name": "test_array_read_groups_2"})
        Model.create({"partner_id": partner_1.id})
        Model.create({"partner_id": partner_1.id})
        Model.create({"partner_id": partner_2.id})

        self.assertEqual(
            Model._read_group([], aggregates=["partner_id:array_agg"]),
            [([partner_1.id, partner_1.id, partner_2.id],)],
        )

        self.assertEqual(
            Model._read_group([], aggregates=["partner_id:recordset"]),
            [(partner_1 + partner_2,)],
        )

    def test_flush_read_group(self):
        Model = self.env["test_read_group.aggregate"]
        a = Model.create({"key": 1, "value": 5})
        b = Model.create({"key": 1, "value": 5})

        self.assertEqual(
            Model._read_group([], groupby=["key"], aggregates=["value:sum"]),
            [(1, 5 + 5)],
        )

        a.key = 2
        self.assertEqual(
            Model._read_group(
                [("key", ">", 1)], groupby=["key"], aggregates=["value:sum"]
            ),
            [
                (2, 5),
            ],
        )

        a.key = 3
        self.assertEqual(
            Model._read_group([], groupby=["key"], aggregates=["value:sum"]),
            [
                (1, 5),
                (3, 5),
            ],
        )

        b.value = 8
        self.assertEqual(
            Model._read_group([], groupby=["key"], aggregates=["value:sum"]),
            [
                (1, 8),
                (3, 5),
            ],
        )

    def test_flush_read_group_company_dependent_groupby(self):
        Model = self.env["test_read_group.order"]
        record = Model.create({"name": "a", "company_dependent_name": "before"})
        self.assertEqual(
            Model._read_group(
                [("id", "=", record.id)], ["company_dependent_name"], ["__count"]
            ),
            [("before", 1)],
        )

        record.company_dependent_name = "after"
        self.assertEqual(
            Model._read_group(
                [("id", "=", record.id)], ["company_dependent_name"], ["__count"]
            ),
            [("after", 1)],
        )

    def test_having_clause(self):
        Model = self.env["test_read_group.aggregate"]
        Model.create({"key": 1, "value": 8})
        Model.create({"key": 1, "value": 2})
        Model.create({"key": 2, "value": 5})
        Model.create({"key": 3, "value": 2})
        Model.create({"key": 3, "value": 4})
        Model.create({"key": 3, "value": 1})

        with self.assertQueries(
            [
                """
            SELECT "test_read_group_aggregate"."key",
                   SUM("test_read_group_aggregate"."value")
            FROM "test_read_group_aggregate"
            GROUP BY "test_read_group_aggregate"."key"
            HAVING SUM("test_read_group_aggregate"."value") > %s
            ORDER BY "test_read_group_aggregate"."key" ASC
        """
            ]
        ):
            self.assertEqual(
                Model._read_group(
                    [],
                    groupby=["key"],
                    aggregates=["value:sum"],
                    having=[("value:sum", ">", 8)],
                ),
                [(1, 2 + 8)],
            )

        with self.assertQueries(
            [
                """
            SELECT "test_read_group_aggregate"."key",
                   SUM("test_read_group_aggregate"."value"),
                   COUNT(*)
            FROM "test_read_group_aggregate"
            GROUP BY "test_read_group_aggregate"."key"
            HAVING (COUNT(*) < %s AND SUM("test_read_group_aggregate"."value") > %s)
            ORDER BY "test_read_group_aggregate"."key" ASC
        """
            ]
        ):
            self.assertEqual(
                Model._read_group(
                    [],
                    groupby=["key"],
                    aggregates=["value:sum", "__count"],
                    having=[("__count", "<", 3), ("value:sum", ">", 4)],
                ),
                [
                    (1, 2 + 8, 2),
                    (2, 5, 1),
                ],
            )

    def test_having_without_groupby(self):
        Model = self.env["test_read_group.aggregate"]
        Model.create({"key": 1, "value": 8})
        Model.create({"key": 1, "value": 2})

        self.assertEqual(Model._read_group([], [], ["value:sum"]), [(10,)])
        self.assertEqual(
            Model._read_group([], [], ["value:sum"], having=[("value:sum", ">", 10)]),
            [],
        )
        self.assertEqual(
            Model._read_group([], [], ["value:sum"], having=[("value:sum", ">", 5)]),
            [(10,)],
        )

    def test_having_without_groupby_falsy_domain(self):
        Model = self.env["test_read_group.aggregate"]
        Model.create({"key": 1, "value": 8})

        for having, expected in [
            ([("value:sum", ">", 1000)], []),
            ([("value:sum", "=", 0)], []),
            ([("__count", "=", 0)], [(0, False)]),
        ]:
            with self.subTest(having=having):
                self.assertEqual(
                    Model._read_group(
                        [("id", "in", [])],
                        [],
                        ["__count", "value:sum"],
                        having=having,
                    ),
                    expected,
                )
                self.assertEqual(
                    Model._read_group(
                        [("id", "=", -1)],
                        [],
                        ["__count", "value:sum"],
                        having=having,
                    ),
                    expected,
                )

    def test_malformed_params(self):
        Model = self.env["test_read_group.order.line"]
        with self.assertRaisesRegex(
            ValueError, "Granularity specification isn't correct: 'bad_granularity'"
        ):
            Model._read_group([], ["create_date:bad_granularity"])

        with self.assertRaisesRegex(
            ValueError,
            "Invalid aggregate/groupby specification 'Other stuff create_date:week'",
        ):
            Model._read_group([], ["Other stuff create_date:week"])

        with self.assertRaisesRegex(
            ValueError, r"Granularity not set on a date\(time\) field: 'create_date'"
        ):
            Model._read_group([], ["create_date"])

        with self.assertRaisesRegex(
            ValueError,
            "Invalid aggregate/groupby specification '\"create_date:week'",
        ):
            Model._read_group([], ['"create_date:week'])

        with self.assertRaisesRegex(
            ValueError,
            "Invalid aggregate/groupby specification '\"create_date:unknown_number'",
        ):
            Model._read_group([], ['"create_date:unknown_number'])

        with self.assertRaisesRegex(
            ValueError, "Aggregate method is mandatory for 'value'"
        ):
            Model._read_group([], aggregates=["value"])

        with self.assertRaisesRegex(ValueError, "Invalid field '__count_'"):
            Model._read_group([], aggregates=["__count_"])

        with self.assertRaisesRegex(ValueError, "Invalid aggregate method '__count'"):
            Model._read_group([], aggregates=["value:__count"])

        with self.assertRaisesRegex(
            ValueError, "Invalid aggregate/groupby specification 'other value:sum'"
        ):
            Model._read_group([], aggregates=["other value:sum"])

        with self.assertRaisesRegex(
            ValueError,
            "Invalid aggregate/groupby specification 'value:array_agg OR'",
        ):
            Model._read_group([], aggregates=["value:array_agg OR"])

        with self.assertRaisesRegex(
            ValueError,
            "Invalid aggregate/groupby specification '\"value:sum'",
        ):
            Model._read_group([], aggregates=['"value:sum'])

        with self.assertRaisesRegex(
            ValueError,
            r"Invalid aggregate/groupby specification 'label:sum\(value\)'",
        ):
            Model._read_group([], aggregates=["label:sum(value)"])

        with self.assertRaisesRegex(
            ValueError,
            r"Invalid 'order_id\.create_date:min', this dot notation is not supported",
        ):
            Model._read_group([], aggregates=["order_id.create_date:min"])

        with self.assertRaisesRegex(
            ValueError,
            "Invalid field 'not_another_field' on model 'test_read_group.order.line' for 'not_another_field:sum'.",
        ):
            Model._read_group([], aggregates=["value:sum", "not_another_field:sum"])

        with self.assertRaisesRegex(
            ValueError, r"Invalid having clause \('__count', '>'\)"
        ):
            Model._read_group([], ["value"], having=[("__count", ">")])

        with self.assertRaisesRegex(
            ValueError, r"Invalid having clause 'COUNT\(\*\) > 2'"
        ):
            Model._read_group([], ["value"], having=["COUNT(*) > 2"])

        with self.assertRaisesRegex(ValueError, "Invalid having clause '\"=\"'"):
            Model._read_group([], ["value"], having=['"="'])

        with self.assertRaisesRegex(
            ValueError, "Invalid order '__count DESC other' for _read_group\\(\\)"
        ):
            Model._read_group([], ["value"], order="__count DESC other")

        with self.assertRaisesRegex(
            ValueError, "Invalid order 'value\" DESC' for _read_group\\(\\)"
        ):
            Model._read_group([], ["value"], order='value" DESC')

        with self.assertRaisesRegex(
            ValueError, "Invalid order 'value ASCCC' for _read_group\\(\\)"
        ):
            Model._read_group([], ["value"], order="value ASCCC")

    def test_groupby_date(self):
        Model = self.env["test_read_group.fill_temporal"]
        Model.create({})
        Model.create({"date": "2022-01-29"})
        Model.create({"date": "2022-01-29"})
        Model.create({"date": "2022-01-30"})
        Model.create({"date": "2022-01-31"})
        Model.create({"date": "2022-02-01"})
        Model.create({"date": "2022-05-29"})
        Model.create({"date": "2023-01-29"})

        result = Model._read_group([], [], ["date:array_agg"])
        self.assertEqual(
            result,
            [
                (
                    [
                        None,
                        fields.Date.to_date("2022-01-29"),
                        fields.Date.to_date("2022-01-29"),
                        fields.Date.to_date("2022-01-30"),
                        fields.Date.to_date("2022-01-31"),
                        fields.Date.to_date("2022-02-01"),
                        fields.Date.to_date("2022-05-29"),
                        fields.Date.to_date("2023-01-29"),
                    ],
                ),
            ],
        )

        result = Model._read_group([], ["date:day"], ["__count"])
        self.assertEqual(
            result,
            [
                (fields.Date.to_date("2022-01-29"), 2),
                (fields.Date.to_date("2022-01-30"), 1),
                (fields.Date.to_date("2022-01-31"), 1),
                (fields.Date.to_date("2022-02-01"), 1),
                (fields.Date.to_date("2022-05-29"), 1),
                (fields.Date.to_date("2023-01-29"), 1),
                (False, 1),
            ],
        )

        result = Model._read_group([], ["date:week"], ["__count"])
        self.assertEqual(
            result,
            [
                (fields.Date.to_date("2022-01-23"), 2),
                (fields.Date.to_date("2022-01-30"), 3),
                (fields.Date.to_date("2022-05-29"), 1),
                (fields.Date.to_date("2023-01-29"), 1),
                (False, 1),
            ],
        )

        result = Model._read_group([], ["date:month"], ["__count"])
        self.assertEqual(
            result,
            [
                (fields.Date.to_date("2022-01-01"), 4),
                (fields.Date.to_date("2022-02-01"), 1),
                (fields.Date.to_date("2022-05-01"), 1),
                (fields.Date.to_date("2023-01-01"), 1),
                (False, 1),
            ],
        )

        result = Model._read_group([], ["date:quarter"], ["__count"])
        self.assertEqual(
            result,
            [
                (fields.Date.to_date("2022-01-01"), 5),
                (fields.Date.to_date("2022-04-01"), 1),
                (fields.Date.to_date("2023-01-01"), 1),
                (False, 1),
            ],
        )

        result = Model._read_group([], ["date:year"], ["__count"])
        self.assertEqual(
            result,
            [
                (fields.Date.to_date("2022-01-01"), 6),
                (fields.Date.to_date("2023-01-01"), 1),
                (False, 1),
            ],
        )
        result = Model._read_group(
            [], ["date:year"], ["__count"], order="date:year DESC"
        )
        self.assertEqual(
            result,
            [
                (False, 1),
                (fields.Date.to_date("2023-01-01"), 1),
                (fields.Date.to_date("2022-01-01"), 6),
            ],
        )

        result = Model._read_group([], ["date:year"], [], order="__count, date:year")
        self.assertEqual(
            result,
            [
                (fields.Date.to_date("2023-01-01"),),
                (False,),
                (fields.Date.to_date("2022-01-01"),),
            ],
        )

    def test_groupby_date_part_number(self):
        Model = self.env["test_read_group.fill_temporal"]
        Model.create({})
        Model.create({"date": "2022-01-29", "datetime": "2022-01-29 13:55:12"})
        Model.create({"date": "2022-01-29", "datetime": "2022-01-29 15:55:13"})
        Model.create({"date": "2022-01-30", "datetime": "2022-01-30 13:54:14"})
        Model.create({"date": "2022-01-31", "datetime": "2022-01-31 15:55:14"})
        Model.create({"date": "2022-02-01", "datetime": "2022-02-01 14:54:13"})
        Model.create({"date": "2022-05-29", "datetime": "2022-05-29 14:55:13"})
        Model.create({"date": "2023-01-29", "datetime": "2023-01-29 15:55:13"})

        result = Model._read_group([], ["datetime:second_number"], ["__count"])
        self.assertEqual(
            result,
            [
                (12, 1),
                (13, 4),
                (14, 2),
                (False, 1),
            ],
        )

        result = Model._read_group([], ["datetime:minute_number"], ["__count"])
        self.assertEqual(
            result,
            [
                (54, 2),
                (55, 5),
                (False, 1),
            ],
        )

        result = Model._read_group([], ["datetime:hour_number"], ["__count"])
        self.assertEqual(
            result,
            [
                (13, 2),
                (14, 2),
                (15, 3),
                (False, 1),
            ],
        )

        result = Model._read_group([], ["date:day_of_year"], ["__count"])
        self.assertEqual(
            result,
            [
                (29, 3),
                (30, 1),
                (31, 1),
                (32, 1),
                (149, 1),
                (False, 1),
            ],
        )

        result = Model._read_group([], ["date:day_of_month"], ["__count"])
        self.assertEqual(
            result,
            [
                (1, 1),
                (29, 4),
                (30, 1),
                (31, 1),
                (False, 1),
            ],
        )

        result = Model._read_group([], ["date:day_of_week"], ["__count"])
        self.assertEqual(
            result,
            [
                (0, 3),
                (1, 1),
                (2, 1),
                (6, 2),
                (False, 1),
            ],
        )

        result = Model._read_group([], ["date:iso_week_number"], ["__count"])
        self.assertEqual(
            result,
            [
                (4, 4),
                (5, 2),
                (21, 1),
                (False, 1),
            ],
        )

        result = Model._read_group([], ["date:month_number"], ["__count"])
        self.assertEqual(
            result,
            [
                (1, 5),
                (2, 1),
                (5, 1),
                (False, 1),
            ],
        )

        result = Model._read_group([], ["date:quarter_number"], ["__count"])
        self.assertEqual(
            result,
            [
                (1, 6),
                (2, 1),
                (False, 1),
            ],
        )

        result = Model._read_group(
            [],
            ["datetime:quarter_number"],
            ["__count"],
            order="datetime:quarter_number DESC",
        )
        self.assertEqual(
            result,
            [
                (False, 1),
                (2, 1),
                (1, 6),
            ],
        )

        result = Model._read_group([], ["date:year_number"], ["__count"])
        self.assertEqual(
            result,
            [
                (2022, 6),
                (2023, 1),
                (False, 1),
            ],
        )

    def test_groupby_datetime(self):
        Model = self.env["test_read_group.fill_temporal"]
        records = Model.create(
            [
                {"datetime": False, "value": 13},
                {"datetime": "1916-08-18 12:30:00", "value": 1},
                {"datetime": "1916-08-18 12:50:00", "value": 3},
                {"datetime": "1916-08-19 01:30:00", "value": 7},
                {"datetime": "1916-10-18 23:30:00", "value": 5},
            ]
        )

        Model = Model.with_context(tz="UTC")

        self.assertEqual(
            Model._read_group(
                [("id", "in", records.ids)], ["datetime:day"], ["value:sum"]
            ),
            [
                (
                    fields.Datetime.to_datetime("1916-08-18 00:00:00"),
                    3 + 1,
                ),
                (
                    fields.Datetime.to_datetime("1916-08-19 00:00:00"),
                    7,
                ),
                (
                    fields.Datetime.to_datetime("1916-10-18 00:00:00"),
                    5,
                ),
                (
                    False,
                    13,
                ),
            ],
        )
        self.assertEqual(
            Model._read_group(
                [("id", "in", records.ids)], ["datetime:hour"], ["value:sum"]
            ),
            [
                (
                    fields.Datetime.to_datetime("1916-08-18 12:00:00"),
                    3 + 1,
                ),
                (
                    fields.Datetime.to_datetime("1916-08-19 01:00:00"),
                    7,
                ),
                (
                    fields.Datetime.to_datetime("1916-10-18 23:00:00"),
                    5,
                ),
                (
                    False,
                    13,
                ),
            ],
        )

        Model = Model.with_context(tz="Europe/Brussels")
        self.assertEqual(
            Model._read_group(
                [("id", "in", records.ids)], ["datetime:day"], ["value:sum"]
            ),
            [
                (
                    fields.Datetime.to_datetime("1916-08-18 00:00:00"),
                    3 + 1,
                ),
                (
                    fields.Datetime.to_datetime("1916-08-19 00:00:00"),
                    7,
                ),
                (
                    fields.Datetime.to_datetime("1916-10-19 00:00:00"),
                    5,
                ),
                (
                    False,
                    13,
                ),
            ],
        )
        self.assertEqual(
            Model._read_group(
                [("id", "in", records.ids)], ["datetime:hour"], ["value:sum"]
            ),
            [
                (
                    fields.Datetime.to_datetime("1916-08-18 14:00:00"),
                    3 + 1,
                ),
                (
                    fields.Datetime.to_datetime("1916-08-19 03:00:00"),
                    7,
                ),
                (
                    fields.Datetime.to_datetime("1916-10-19 00:00:00"),
                    5,
                ),
                (
                    False,
                    13,
                ),
            ],
        )

        Model = Model.with_context(tz="America/Anchorage")
        self.assertEqual(
            Model._read_group(
                [("id", "in", records.ids)], ["datetime:day"], ["value:sum"]
            ),
            [
                (
                    fields.Datetime.to_datetime("1916-08-18 00:00:00"),
                    7 + 3 + 1,
                ),
                (
                    fields.Datetime.to_datetime("1916-10-18 00:00:00"),
                    5,
                ),
                (
                    False,
                    13,
                ),
            ],
        )
        self.assertEqual(
            Model._read_group(
                [("id", "in", records.ids)], ["datetime:hour"], ["value:sum"]
            ),
            [
                (
                    fields.Datetime.to_datetime("1916-08-18 02:00:00"),
                    3 + 1,
                ),
                (
                    fields.Datetime.to_datetime("1916-08-18 15:00:00"),
                    7,
                ),
                (
                    fields.Datetime.to_datetime("1916-10-18 13:00:00"),
                    5,
                ),
                (
                    False,
                    13,
                ),
            ],
        )

    def test_aggregate_datetime(self):
        Model = self.env["test_read_group.fill_temporal"]
        records = Model.create(
            [
                {"datetime": False, "value": 13},
                {"datetime": "1916-08-18 01:50:00", "value": 3},
                {"datetime": "1916-08-19 01:30:00", "value": 7},
                {"datetime": "1916-10-18 02:30:00", "value": 5},
            ]
        )
        self.assertEqual(
            Model._read_group([("id", "in", records.ids)], [], ["datetime:max"]),
            [
                (fields.Datetime.to_datetime("1916-10-18 02:30:00"),),
            ],
        )

        self.assertEqual(
            Model._read_group([("id", "in", records.ids)], [], ["datetime:array_agg"]),
            [
                (
                    [
                        None,
                        fields.Datetime.to_datetime("1916-08-18 01:50:00"),
                        fields.Datetime.to_datetime("1916-08-19 01:30:00"),
                        fields.Datetime.to_datetime("1916-10-18 02:30:00"),
                    ],
                )
            ],
        )

    def test_field_bypass_search_access(self):
        model = self.env["test_read_group.order"]
        records = model.create(
            [
                {
                    "line_ids": [
                        Command.create({"value": 1}),
                        Command.create({"value": 2}),
                    ],
                },
                {
                    "line_ids": [Command.create({"value": 1})],
                },
            ]
        )

        domain1 = [("id", "in", records.ids), ("line_ids.value", "=", 1)]
        domain2 = [("id", "in", records.ids), ("line_ids.value", ">", 0)]

        self.assertEqual(len(model.search(domain1)), 2)
        self.assertEqual(len(model.search(domain2)), 2)

        result1 = model._read_group(domain1, aggregates=["__count"])
        self.assertEqual(result1, [(2,)])

        result2 = model._read_group(domain2, aggregates=["__count"])
        self.assertEqual(result2, [(2,)])

        self.patch(type(model).line_ids, "bypass_search_access", True)

        self.assertEqual(len(model.search(domain1)), 2)
        self.assertEqual(len(model.search(domain2)), 2)

        result1 = model._read_group(domain1, aggregates=["__count"])
        self.assertEqual(result1, [(2,)])

        result2 = model._read_group(domain2, aggregates=["__count"])
        self.assertEqual(result2, [(2,)])

    def test_groupby_many2many_field_access(self):
        Task = self.env["test_read_group.task"]
        Task.create({"name": "Super Mario Bros."})
        group_user = self.env.ref("base.group_user")
        for model in ("test_read_group.task", "test_read_group.user"):
            make_access_row(self.env, model, group_user, operation="r")
        task_as_user = Task.with_user(self.base_user)

        task_as_user._read_group([], groupby=["user_ids"], aggregates=["__count"])

        self.patch(type(Task).user_ids, "groups", "base.group_system")

        with self.assertRaises(AccessError):
            task_as_user._read_group([], groupby=["user_ids"], aggregates=["__count"])

        self.assertEqual(
            Task._read_group([], groupby=["user_ids"], aggregates=["__count"]),
            [(self.env["test_read_group.user"], 1)],
        )

    def test_groupby_many2many(self):
        User = self.env["test_read_group.user"]
        mario, luigi = User.create([{"name": "Mario"}, {"name": "Luigi"}])
        tasks = self.env["test_read_group.task"].create(
            [
                {
                    "name": "Super Mario Bros.",
                    "user_ids": [Command.set((mario + luigi).ids)],
                },
                {
                    "name": "Paper Mario",
                    "user_ids": [Command.set(mario.ids)],
                },
                {
                    "name": "Luigi's Mansion",
                    "user_ids": [Command.set(luigi.ids)],
                },
                {
                    "name": "Donkey Kong",
                },
            ]
        )

        expected = """
            SELECT
                "test_read_group_task__user_ids"."user_id",
                ARRAY_AGG("test_read_group_task"."name" ORDER BY "test_read_group_task"."id")
            FROM "test_read_group_task"
                LEFT JOIN "test_read_group_task_user_rel" AS "test_read_group_task__user_ids"
                    ON ("test_read_group_task"."id" = "test_read_group_task__user_ids"."task_id")
            WHERE "test_read_group_task"."id" IN (%s)
            GROUP BY "test_read_group_task__user_ids"."user_id"
            ORDER BY "test_read_group_task__user_ids"."user_id" ASC
        """
        with self.assertQueries([expected]):
            self.assertEqual(
                tasks._read_group(
                    [("id", "in", tasks.ids)],
                    ["user_ids"],
                    ["name:array_agg"],
                ),
                [
                    (
                        mario,
                        ["Super Mario Bros.", "Paper Mario"],
                    ),
                    (
                        luigi,
                        ["Super Mario Bros.", "Luigi's Mansion"],
                    ),
                    (User, ["Donkey Kong"]),
                ],
            )

        expected = """
            SELECT
                "test_read_group_task__user_ids"."user_id",
                ARRAY_AGG("test_read_group_task"."name" ORDER BY "test_read_group_task"."id")
            FROM "test_read_group_task"
                LEFT JOIN "test_read_group_task_user_rel" AS "test_read_group_task__user_ids"
                    ON ("test_read_group_task"."id" = "test_read_group_task__user_ids"."task_id")
            WHERE "test_read_group_task"."id" IN (%s)
            GROUP BY "test_read_group_task__user_ids"."user_id"
            ORDER BY "test_read_group_task__user_ids"."user_id" DESC
        """
        with self.assertQueries([expected]):
            self.assertEqual(
                tasks._read_group(
                    [("id", "in", tasks.ids)],
                    ["user_ids"],
                    ["name:array_agg"],
                    order="user_ids DESC",
                ),
                [
                    (User, ["Donkey Kong"]),
                    (
                        luigi,
                        ["Super Mario Bros.", "Luigi's Mansion"],
                    ),
                    (
                        mario,
                        ["Super Mario Bros.", "Paper Mario"],
                    ),
                ],
            )

        users_model = self.env["ir.model"]._get(mario._name)
        self.env["ir.access"].create(
            {
                "name": "Only The Lone Wanderer allowed",
                "kind": "guard",
                "group_id": self.env.ref("base.group_everyone").id,
                "operation": "crud",
                "model_id": users_model.id,
                "domain": str([("id", "=", mario.id)]),
            }
        )
        tasks = tasks.with_user(self.base_user)

        tasks._read_group([], groupby=["user_ids"], aggregates=["name:array_agg"])

        expected = """
            SELECT
                "test_read_group_task__user_ids"."user_id",
                ARRAY_AGG("test_read_group_task"."name" ORDER BY "test_read_group_task"."id")
            FROM "test_read_group_task"
            LEFT JOIN "test_read_group_task_user_rel" AS "test_read_group_task__user_ids"
                ON (
                    "test_read_group_task"."id" = "test_read_group_task__user_ids"."task_id"
                    AND "test_read_group_task__user_ids"."user_id" IN (
                        SELECT "test_read_group_user"."id"
                        FROM "test_read_group_user"
                        WHERE "test_read_group_user"."id" IN (%s)
                    )
                )
            GROUP BY "test_read_group_task__user_ids"."user_id"
            ORDER BY "test_read_group_task__user_ids"."user_id" ASC
        """
        with self.assertQueries([expected]):
            self.assertEqual(
                tasks._read_group(
                    [], groupby=["user_ids"], aggregates=["name:array_agg"]
                ),
                [
                    (mario, ["Super Mario Bros.", "Paper Mario"]),
                    (User, ["Luigi's Mansion", "Donkey Kong"]),
                ],
            )

    def test_groupby_many2many_active_test_domain(self):
        Tag = self.env["test_read_group.tag"]
        active_tag, archive_tag = Tag.create(
            [
                {"name": "Active tag", "active": True},
                {"name": "Archive tag", "active": False},
            ]
        )
        tasks = self.env["test_read_group.task"].create(
            [
                {
                    "name": "Both tags",
                    "tag_ids": [Command.set((active_tag + archive_tag).ids)],
                },
                {
                    "name": "Active tag",
                    "tag_ids": [Command.set(active_tag.ids)],
                },
                {
                    "name": "Archive tag",
                    "tag_ids": [Command.set(archive_tag.ids)],
                },
                {
                    "name": "No tag",
                },
            ]
        )

        with self.assertQueries(
            [
                """
            SELECT "test_read_group_task__tag_ids"."tag_id",
                ARRAY_AGG("test_read_group_task"."name" ORDER BY "test_read_group_task"."id")
            FROM "test_read_group_task"
            LEFT JOIN "test_read_group_task_tag_rel" AS "test_read_group_task__tag_ids"
                ON (
                    "test_read_group_task"."id" = "test_read_group_task__tag_ids"."task_id"
                    AND "test_read_group_task__tag_ids"."tag_id" IN (
                        SELECT
                            "test_read_group_tag"."id"
                        FROM
                            "test_read_group_tag"
                        WHERE
                            "test_read_group_tag"."active" IS TRUE
                    )
                )
            WHERE "test_read_group_task"."id" IN (%s)
            GROUP BY "test_read_group_task__tag_ids"."tag_id"
            ORDER BY "test_read_group_task__tag_ids"."tag_id" ASC
            """,
            ]
        ):
            self.assertEqual(
                tasks._read_group(
                    [("id", "in", tasks.ids)],
                    ["tag_ids"],
                    ["name:array_agg"],
                ),
                [
                    (active_tag, ["Both tags", "Active tag"]),
                    (Tag, ["Archive tag", "No tag"]),
                ],
            )

        with self.assertQueries(
            [
                """
            SELECT "test_read_group_task__active_tag_ids"."tag_id",
                ARRAY_AGG("test_read_group_task"."name" ORDER BY "test_read_group_task"."id")
            FROM "test_read_group_task"
            LEFT JOIN "test_read_group_task_tag_rel" AS "test_read_group_task__active_tag_ids"
                ON (
                    "test_read_group_task"."id" = "test_read_group_task__active_tag_ids"."task_id"
                    AND "test_read_group_task__active_tag_ids"."tag_id" IN (
                        SELECT
                            "test_read_group_tag"."id"
                        FROM
                            "test_read_group_tag"
                        WHERE
                            "test_read_group_tag"."active" IS TRUE
                    )
                )
            WHERE "test_read_group_task"."id" IN (%s)
            GROUP BY "test_read_group_task__active_tag_ids"."tag_id"
            ORDER BY "test_read_group_task__active_tag_ids"."tag_id" ASC
            """,
            ]
        ):
            self.assertEqual(
                tasks._read_group(
                    [("id", "in", tasks.ids)],
                    ["active_tag_ids"],
                    ["name:array_agg"],
                ),
                [
                    (active_tag, ["Both tags", "Active tag"]),
                    (Tag, ["Archive tag", "No tag"]),
                ],
            )

        with self.assertQueries(
            [
                """
            SELECT "test_read_group_task__all_tag_ids"."tag_id",
                ARRAY_AGG("test_read_group_task"."name" ORDER BY "test_read_group_task"."id")
            FROM "test_read_group_task"
            LEFT JOIN "test_read_group_task_tag_rel" AS "test_read_group_task__all_tag_ids"
                ON (
                    "test_read_group_task"."id" = "test_read_group_task__all_tag_ids"."task_id"
                )
            WHERE "test_read_group_task"."id" IN (%s)
            GROUP BY "test_read_group_task__all_tag_ids"."tag_id"
            ORDER BY "test_read_group_task__all_tag_ids"."tag_id" ASC
            """,
            ]
        ):
            self.assertEqual(
                tasks._read_group(
                    [("id", "in", tasks.ids)],
                    ["all_tag_ids"],
                    ["name:array_agg"],
                ),
                [
                    (active_tag, ["Both tags", "Active tag"]),
                    (archive_tag, ["Both tags", "Archive tag"]),
                    (Tag, ["No tag"]),
                ],
            )

    def test_float_aggregate(self):
        records = self.env["test_read_group.aggregate"].create({"numeric_value": 42.42})
        [[result]] = records._read_group(
            [("id", "in", records.ids)], [], ["numeric_value:array_agg"]
        )
        self.assertIsInstance(result, list)
        self.assertIsInstance(result[0], float)

    def test_related(self):
        RelatedBar = self.env["test_read_group.related_bar"]
        RelatedBase = self.env["test_read_group.related_base"]
        self._create_related_fixtures()

        RelatedBase = RelatedBase.with_user(self.base_user)

        field_info = RelatedBase.fields_get(
            [
                "foo_id_name",
                "foo_id_name_sudo",
                "foo_id_bar_id_name",
                "foo_id_bar_name",
                "foo_id_bar_name_sudo",
            ],
            ["groupable", "aggregator"],
        )
        self.assertFalse(field_info["foo_id_name"]["groupable"])
        self.assertNotIn("aggregator", field_info["foo_id_name"])

        self.assertTrue(field_info["foo_id_name_sudo"]["groupable"])
        self.assertNotIn("aggregator", field_info["foo_id_name_sudo"])

        self.assertTrue(field_info["foo_id_bar_id_name"]["groupable"])
        self.assertEqual(
            field_info["foo_id_bar_id_name"]["aggregator"], "count_distinct"
        )

        self.assertTrue(field_info["foo_id_bar_name"]["groupable"])
        self.assertEqual(field_info["foo_id_bar_name"]["aggregator"], "count_distinct")

        self.assertTrue(field_info["foo_id_bar_name_sudo"]["groupable"])
        self.assertEqual(
            field_info["foo_id_bar_name_sudo"]["aggregator"], "count_distinct"
        )

        RelatedBase._read_group([], ["foo_id_name_sudo"], ["__count"])
        with self.assertQueries(
            [
                """
            SELECT NULLIF("test_read_group_related_base__foo_id"."name", ''),
                    COUNT(*)
            FROM "test_read_group_related_base"
            LEFT JOIN "test_read_group_related_foo" AS "test_read_group_related_base__foo_id"
                ON ("test_read_group_related_base"."foo_id" = "test_read_group_related_base__foo_id"."id")
            GROUP BY NULLIF("test_read_group_related_base__foo_id"."name", '')
            ORDER BY NULLIF("test_read_group_related_base__foo_id"."name", '') ASC
        """
            ]
        ):
            self.assertEqual(
                RelatedBase._read_group([], ["foo_id_name_sudo"], ["__count"]),
                [("foo_a_bar_a", 2), ("foo_b_bar_false", 1), (False, 2)],
            )

        foo_bar_name_query = """
            SELECT NULLIF("test_read_group_related_base__foo_id__bar_id"."name", ''),
                    COUNT(*)
            FROM "test_read_group_related_base"
            LEFT JOIN "test_read_group_related_foo" AS "test_read_group_related_base__foo_id"
                ON ("test_read_group_related_base"."foo_id" = "test_read_group_related_base__foo_id"."id")
            LEFT JOIN "test_read_group_related_bar" AS "test_read_group_related_base__foo_id__bar_id"
                ON ("test_read_group_related_base__foo_id"."bar_id" = "test_read_group_related_base__foo_id__bar_id"."id")
            GROUP BY NULLIF("test_read_group_related_base__foo_id__bar_id"."name", '')
            ORDER BY NULLIF("test_read_group_related_base__foo_id__bar_id"."name", '') ASC
        """

        with self.assertQueries([foo_bar_name_query] * 3):
            self.assertEqual(
                RelatedBase._read_group([], ["foo_id_bar_id_name"], ["__count"]),
                [("bar_a", 3), (False, 2)],
            )
            self.assertEqual(
                RelatedBase._read_group([], ["foo_id_bar_name"], ["__count"]),
                [("bar_a", 3), (False, 2)],
            )
            self.assertEqual(
                RelatedBase._read_group([], ["foo_id_bar_name_sudo"], ["__count"]),
                [("bar_a", 3), (False, 2)],
            )

        with self.assertQueries(
            [
                """
            SELECT COUNT(DISTINCT "test_read_group_related_base__foo_id__bar_id"."name")
            FROM "test_read_group_related_base"
            LEFT JOIN "test_read_group_related_foo" AS "test_read_group_related_base__foo_id"
                ON ("test_read_group_related_base"."foo_id" = "test_read_group_related_base__foo_id"."id")
            LEFT JOIN "test_read_group_related_bar" AS "test_read_group_related_base__foo_id__bar_id"
                ON ("test_read_group_related_base__foo_id"."bar_id" = "test_read_group_related_base__foo_id__bar_id"."id")
        """
            ]
        ):
            self.assertEqual(
                RelatedBase._read_group(
                    [], aggregates=["foo_id_bar_id_name:count_distinct"]
                ),
                [(1,)],
            )

        with self.assertRaises(ValueError):
            RelatedBar._read_group([], ["foo_names_sudo"])

    def test_inherited(self):
        RelatedBase = self.env["test_read_group.related_base"]
        RelatedInherits = self.env["test_read_group.related_inherits"]

        bases = RelatedBase.create(
            [
                {"name": "a", "value": 1},
                {"name": "a", "value": 2},
                {"name": "b", "value": 3},
                {"name": False, "value": 4},
            ]
        )
        RelatedInherits.create(
            [
                {"base_id": bases[0].id},
                {"base_id": bases[0].id},
                {"base_id": bases[1].id},
                {"base_id": bases[2].id},
                {"base_id": bases[3].id},
            ]
        )

        RelatedInherits = RelatedInherits.with_user(self.base_user)

        field_info = RelatedInherits.fields_get(
            ["name", "foo_id_name", "foo_id_name_sudo", "value"],
            ["groupable", "aggregator"],
        )
        self.assertTrue(field_info["name"]["groupable"])
        self.assertFalse(field_info["foo_id_name"]["groupable"])
        self.assertTrue(field_info["foo_id_name_sudo"]["groupable"])
        self.assertEqual(field_info["value"]["aggregator"], "sum")

        RelatedInherits._read_group([], ["name"], ["__count"])
        with self.assertQueries(
            [
                """
            SELECT NULLIF("test_read_group_related_inherits__base_id"."name", ''),
                    COUNT(*)
            FROM "test_read_group_related_inherits"
            LEFT JOIN "test_read_group_related_base" AS "test_read_group_related_inherits__base_id"
                ON ("test_read_group_related_inherits"."base_id" = "test_read_group_related_inherits__base_id"."id")
            GROUP BY NULLIF("test_read_group_related_inherits__base_id"."name", '')
            ORDER BY NULLIF("test_read_group_related_inherits__base_id"."name", '') ASC
        """
            ]
        ):
            self.assertEqual(
                RelatedInherits._read_group([], ["name"], ["__count"]),
                [("a", 3), ("b", 1), (False, 1)],
            )

        with self.assertQueries(
            [
                """
            SELECT NULLIF("test_read_group_related_inherits__base_id"."name", ''),
                    SUM("test_read_group_related_inherits__base_id"."value")
            FROM "test_read_group_related_inherits"
            LEFT JOIN "test_read_group_related_base" AS "test_read_group_related_inherits__base_id"
                ON ("test_read_group_related_inherits"."base_id" = "test_read_group_related_inherits__base_id"."id")
            GROUP BY NULLIF("test_read_group_related_inherits__base_id"."name", '')
            ORDER BY NULLIF("test_read_group_related_inherits__base_id"."name", '') ASC
        """
            ]
        ):
            self.assertEqual(
                RelatedInherits._read_group([], ["name"], ["value:sum"]),
                [("a", 1 + 1 + 2), ("b", 3), (False, 4)],
            )

        with self.assertQueries(
            [
                """
            SELECT NULLIF("test_read_group_related_inherits__base_id__foo_id"."name", ''),
                    COUNT(*)
            FROM "test_read_group_related_inherits"
            LEFT JOIN "test_read_group_related_base" AS "test_read_group_related_inherits__base_id"
                ON ("test_read_group_related_inherits"."base_id" = "test_read_group_related_inherits__base_id"."id")
            LEFT JOIN "test_read_group_related_foo" AS "test_read_group_related_inherits__base_id__foo_id"
                ON ("test_read_group_related_inherits__base_id"."foo_id" = "test_read_group_related_inherits__base_id__foo_id"."id")
            GROUP BY NULLIF("test_read_group_related_inherits__base_id__foo_id"."name", '')
            ORDER BY NULLIF("test_read_group_related_inherits__base_id__foo_id"."name", '') ASC
        """
            ]
        ):
            self.assertEqual(
                RelatedInherits._read_group([], ["foo_id_name_sudo"], ["__count"]),
                [(False, 5)],
            )

        with self.assertRaises(ValueError):
            RelatedInherits._read_group([], ["foo_id_name"])

    def test_related_many2many_groupby(self):
        RelatedBase = self.env["test_read_group.related_base"]
        RelatedBar = self.env["test_read_group.related_bar"]
        RelatedFoo = self.env["test_read_group.related_foo"]

        base_1, base_2 = RelatedBase.create(
            [
                {"name": "test_related_many2many_groupby_base_1"},
                {"name": "test_related_many2many_groupby_base_2"},
            ]
        )
        bar = RelatedBar.create({"base_ids": [Command.set((base_1 + base_2).ids)]})
        RelatedFoo.create({"bar_id": bar.id})

        RelatedFoo = RelatedFoo.with_user(self.base_user)

        RelatedFoo._read_group([], ["bar_base_ids"], ["__count"])
        with self.assertQueries(
            [
                """
            SELECT "test_read_group_related_foo__bar_id__base_ids"."test_read_group_related_base_id",
                    COUNT(*)
            FROM "test_read_group_related_foo"
            LEFT JOIN "test_read_group_related_bar" AS "test_read_group_related_foo__bar_id"
                ON ("test_read_group_related_foo"."bar_id" = "test_read_group_related_foo__bar_id"."id")
            LEFT JOIN "test_read_group_related_bar_test_read_group_related_base_rel" AS "test_read_group_related_foo__bar_id__base_ids"
                ON ("test_read_group_related_foo__bar_id"."id" = "test_read_group_related_foo__bar_id__base_ids"."test_read_group_related_bar_id")
            GROUP BY "test_read_group_related_foo__bar_id__base_ids"."test_read_group_related_base_id"
            ORDER BY "test_read_group_related_foo__bar_id__base_ids"."test_read_group_related_base_id" ASC
        """
            ]
        ):
            RelatedFoo._read_group([], ["bar_base_ids"], ["__count"])

        self.assertEqual(
            RelatedFoo._read_group([], ["bar_base_ids"], ["__count"]),
            [(base_1, 1), (base_2, 1)],
        )

        field_info = RelatedFoo.fields_get(["bar_base_ids"], ["groupable"])
        self.assertTrue(field_info["bar_base_ids"]["groupable"])

        related_base_model = self.env["ir.model"]._get("test_read_group.related_base")
        self.env["ir.access"].create(
            {
                "name": "Only The Lone Wanderer allowed",
                "kind": "guard",
                "group_id": self.env.ref("base.group_everyone").id,
                "operation": "crud",
                "model_id": related_base_model.id,
                "domain": str([("id", "=", 161)]),
            }
        )

        RelatedFoo._read_group([], ["bar_base_ids"], ["__count"])
        with self.assertQueries(
            [
                """
            SELECT "test_read_group_related_foo__bar_id__base_ids"."test_read_group_related_base_id", COUNT(*)
            FROM "test_read_group_related_foo"
            LEFT JOIN "test_read_group_related_bar" AS "test_read_group_related_foo__bar_id"
                ON ("test_read_group_related_foo"."bar_id" = "test_read_group_related_foo__bar_id"."id")
            LEFT JOIN "test_read_group_related_bar_test_read_group_related_base_rel" AS "test_read_group_related_foo__bar_id__base_ids"
                ON ("test_read_group_related_foo__bar_id"."id" = "test_read_group_related_foo__bar_id__base_ids"."test_read_group_related_bar_id"
                    AND "test_read_group_related_foo__bar_id__base_ids"."test_read_group_related_base_id" IN (
                        SELECT "test_read_group_related_base"."id"
                        FROM "test_read_group_related_base"
                        WHERE "test_read_group_related_base"."id" IN (%s)
                    )
                )
            GROUP BY "test_read_group_related_foo__bar_id__base_ids"."test_read_group_related_base_id"
            ORDER BY "test_read_group_related_foo__bar_id__base_ids"."test_read_group_related_base_id" ASC
        """
            ]
        ):
            RelatedFoo._read_group([], ["bar_base_ids"], ["__count"])

        self.assertEqual(
            RelatedFoo._read_group([], ["bar_base_ids"], ["__count"]),
            [(RelatedBase, 1)],
        )
        self.assertEqual(
            RelatedFoo._read_group([], ["bar_base_ids"], ["__count"]),
            RelatedFoo._read_group([], ["bar_id.base_ids"], ["__count"]),
        )

    def test_many2many_aggregate(self):
        Model = self.env["test_read_group.task"]

        Model._read_group([], [], ["name:array_agg"])

        with self.assertRaises(ValueError):
            Model._read_group([], [], ["user_ids:array_agg"])

    def test_many2many_compute_not_groupable(self):
        Model = self.env["test_read_group.related_bar"]
        field_info = Model.fields_get(["computed_base_ids"], ["groupable"])
        self.assertFalse(field_info["computed_base_ids"]["groupable"])

    def test_duplicate_arguments(self):
        Model = self.env["test_read_group.aggregate"]
        Model.create({"key": 1, "value": 5})
        self.assertEqual(
            Model._read_group(
                [],
                groupby=["key", "key"],
                aggregates=["value:sum", "value:sum", "key:sum"],
            ),
            [
                (1, 1, 5, 5, 1),
            ],
        )

    def test_groupby_chain_fnames_many2one(self):
        RelatedBar = self.env["test_read_group.related_bar"]
        RelatedFoo = self.env["test_read_group.related_foo"]
        RelatedBase = self.env["test_read_group.related_base"]
        bars, foos = self._create_related_fixtures()

        RelatedBase._read_group([], ["foo_id.bar_id"], ["__count"])

        expected_query = """
            SELECT "test_read_group_related_base__foo_id"."bar_id",
                    COUNT(*)
            FROM "test_read_group_related_base"
            LEFT JOIN "test_read_group_related_foo" AS "test_read_group_related_base__foo_id"
                ON ("test_read_group_related_base"."foo_id" = "test_read_group_related_base__foo_id"."id")
            GROUP BY "test_read_group_related_base__foo_id"."bar_id"
            ORDER BY "test_read_group_related_base__foo_id"."bar_id" ASC
        """
        with self.assertQueries([expected_query]):
            self.assertEqual(
                RelatedBase._read_group([], ["foo_id.bar_id"], ["__count"]),
                [(bars[0], 3), (bars[1], 1), (RelatedBar, 1)],
            )

        RelatedBase = RelatedBase.with_user(self.base_user)

        RelatedBase._read_group([], ["foo_id.bar_id"], ["__count"])

        with self.assertQueries([expected_query]):
            self.assertEqual(
                RelatedBase._read_group([], ["foo_id.bar_id"], ["__count"]),
                [(bars[0], 3), (bars[1], 1), (RelatedBar, 1)],
            )

        users_model = self.env["ir.model"]._get(RelatedFoo._name)
        self.env["ir.access"].create(
            {
                "name": "Only The Lone Wanderer allowed",
                "kind": "guard",
                "group_id": self.env.ref("base.group_everyone").id,
                "operation": "crud",
                "model_id": users_model.id,
                "domain": str([("id", "in", foos[1:].ids)]),
            }
        )
        RelatedBase = RelatedBase.with_user(self.base_user)

        RelatedBase._read_group([], ["foo_id.bar_id"], ["__count"])

        alias_join = f"test_read_group_related_base__foo_id__{self.base_user.id}"
        with self.assertQueries(
            [
                f"""
            SELECT "{alias_join}"."bar_id",
                   COUNT(*)
            FROM "test_read_group_related_base"
            LEFT JOIN (
                SELECT "test_read_group_related_foo".*
                FROM "test_read_group_related_foo"
                WHERE "test_read_group_related_foo"."id" IN (%s)
            ) AS "{alias_join}"
            ON (
                "test_read_group_related_base"."foo_id" = "{alias_join}"."id"
            )
            GROUP BY "{alias_join}"."bar_id"
            ORDER BY "{alias_join}"."bar_id" ASC
        """
            ]
        ):
            self.assertEqual(
                RelatedBase._read_group([], ["foo_id.bar_id"], ["__count"]),
                [(bars[0], 1), (bars[1], 1), (RelatedBar, 3)],
            )

    def test_groupby_chain_fnames_char(self):
        RelatedBar = self.env["test_read_group.related_bar"]
        RelatedFoo = self.env["test_read_group.related_foo"]
        RelatedBase = self.env["test_read_group.related_base"]
        _bars, foos = self._create_related_fixtures()

        RelatedBase._read_group([], ["foo_id.bar_id.name"], ["__count"])

        query_expected = """
            SELECT NULLIF("test_read_group_related_base__foo_id__bar_id"."name", ''),
                    COUNT(*)
            FROM "test_read_group_related_base"
            LEFT JOIN "test_read_group_related_foo" AS "test_read_group_related_base__foo_id"
                ON ("test_read_group_related_base"."foo_id" = "test_read_group_related_base__foo_id"."id")
            LEFT JOIN "test_read_group_related_bar" AS "test_read_group_related_base__foo_id__bar_id"
                ON ("test_read_group_related_base__foo_id"."bar_id" = "test_read_group_related_base__foo_id__bar_id"."id")
            GROUP BY NULLIF("test_read_group_related_base__foo_id__bar_id"."name", '')
            ORDER BY NULLIF("test_read_group_related_base__foo_id__bar_id"."name", '') ASC
        """
        with self.assertQueries([query_expected] * 3):
            for fname_chain in [
                "foo_id.bar_id.name",
                "foo_id.bar_name_sudo",
                "foo_id.bar_name",
            ]:
                self.assertEqual(
                    RelatedBase._read_group([], [fname_chain], ["__count"]),
                    [("bar_a", 3), (False, 2)],
                )

        with self.assertRaises(ValueError):
            RelatedBar._read_group([], ["foo_ids.name"])

        RelatedBase = RelatedBase.with_user(self.base_user)

        RelatedBase._read_group([], ["foo_id.bar_id.name"], ["__count"])

        expected_query = """
            SELECT NULLIF("test_read_group_related_base__foo_id__bar_id"."name", ''),
                    COUNT(*)
            FROM "test_read_group_related_base"
            LEFT JOIN "test_read_group_related_foo" AS "test_read_group_related_base__foo_id"
                ON ("test_read_group_related_base"."foo_id" = "test_read_group_related_base__foo_id"."id")
            LEFT JOIN "test_read_group_related_bar" AS "test_read_group_related_base__foo_id__bar_id"
                ON ("test_read_group_related_base__foo_id"."bar_id" = "test_read_group_related_base__foo_id__bar_id"."id")
            GROUP BY NULLIF("test_read_group_related_base__foo_id__bar_id"."name", '')
            ORDER BY NULLIF("test_read_group_related_base__foo_id__bar_id"."name", '') ASC
        """
        for fname_chain in ["foo_id.bar_id.name", "foo_id.bar_name_sudo"]:
            with self.assertQueries([expected_query]):
                self.assertEqual(
                    RelatedBase._read_group([], [fname_chain], ["__count"]),
                    [("bar_a", 3), (False, 2)],
                )

        with self.assertRaises(ValueError):
            RelatedBase._read_group([], ["foo_id.bar_name"], ["__count"])

        users_model = self.env["ir.model"]._get(RelatedFoo._name)
        self.env["ir.access"].create(
            {
                "name": "Only The Lone Wanderer allowed",
                "kind": "guard",
                "group_id": self.env.ref("base.group_everyone").id,
                "operation": "crud",
                "model_id": users_model.id,
                "domain": str([("id", "in", foos[1:].ids)]),
            }
        )

        RelatedBase._read_group([], ["foo_id.bar_id.name"], ["__count"])

        alias_join = f"test_read_group_related_base__foo_id__{self.base_user.id}"
        expected_query = f"""
            SELECT NULLIF("{alias_join}__bar_id"."name", ''),
                   COUNT(*)
            FROM "test_read_group_related_base"
            LEFT JOIN (
                SELECT "test_read_group_related_foo".*
                FROM "test_read_group_related_foo"
                WHERE "test_read_group_related_foo"."id" IN (%s)
            ) AS "{alias_join}" ON (
                "test_read_group_related_base"."foo_id" = "{alias_join}"."id"
            )
            LEFT JOIN "test_read_group_related_bar" AS "{alias_join}__bar_id" ON (
                "{alias_join}"."bar_id" = "{alias_join}__bar_id"."id"
            )
            GROUP BY NULLIF("{alias_join}__bar_id"."name", '')
            ORDER BY NULLIF("{alias_join}__bar_id"."name", '') ASC
        """

        with self.assertQueries([expected_query] * 2):
            for fname_chain in ["foo_id.bar_id.name", "foo_id.bar_name_sudo"]:
                self.assertEqual(
                    RelatedBase._read_group([], [fname_chain], ["__count"]),
                    [("bar_a", 1), (False, 4)],
                )
