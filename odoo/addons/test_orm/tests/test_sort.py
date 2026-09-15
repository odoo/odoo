from odoo.api import NewId
from odoo.fields import Command
from odoo.tests import TransactionCase


class TestSort(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.countries = cls.env["test_orm.country"].create(
            [
                {"name": "B"},
                {"name": "A"},
                {"name": "C"},
            ]
        )
        b, a, c = cls.countries
        cls.cities = cls.env["test_orm.city"].create(
            [
                {"name": "c2", "country_id": c.id},
                {"name": "b1", "country_id": b.id},
                {"name": "b2", "country_id": b.id},
                {"name": "c1", "country_id": c.id},
                {"name": "a1", "country_id": a.id},
                {"name": "a2", "country_id": a.id},
            ]
        )

    def test_basic(self):
        db_result = self.env["test_orm.country"].search([])
        with self.assertQueryCount(0):
            self.assertEqual(db_result.ids, self.countries.sorted().ids)
        with self.assertQueryCount(0):
            self.assertEqual(
                db_result[::-1].ids, self.countries.sorted(reverse=True).ids
            )
        self.assertEqual(self.countries.sorted().mapped("name"), ["A", "B", "C"])

    def test_stable(self):
        self.assertEqual(
            self.cities.sorted("name", reverse=True).sorted("country_id.id"),
            self.cities.sorted(lambda c: (-c.country_id.id, c.name), reverse=True),
        )

    def test_basic_m2o(self):
        db_result = self.env["test_orm.city"].search([])
        with self.assertQueryCount(2):
            self.assertEqual(db_result.ids, self.cities.sorted().ids)
        with self.assertQueryCount(0):
            self.assertEqual(db_result[::-1].ids, self.cities.sorted(reverse=True).ids)
        self.assertEqual(
            self.cities.sorted().mapped("name"),
            ["a1", "a2", "b1", "b2", "c1", "c2"],
        )

    def test_basic_boolean(self):
        records = self.env["test_orm.model_active_field"].create(
            [{"name": v} for v in "abc"]
        )
        records[1].active = False
        t_records = records.filtered("active")
        f_records = records - t_records
        with self.assertQueryCount(0):
            records.sorted("active, name")
        self.assertEqual(f_records + t_records, records.sorted("active, name"))
        self.assertEqual(t_records + f_records, records.sorted("active DESC, name"))

    def test_custom_m2o(self):
        order = "country_id DESC, id ASC"
        db_result = self.env["test_orm.city"].search([], order=order)
        with self.assertQueryCount(2):
            self.assertEqual(db_result.ids, self.cities.sorted(order).ids)
        with self.assertQueryCount(0):
            self.assertEqual(
                db_result[::-1].ids, self.cities.sorted(order, reverse=True).ids
            )
        self.assertEqual(
            self.cities.sorted(order).mapped("name"),
            ["c2", "c1", "b1", "b2", "a1", "a2"],
        )

    def test_nulls(self):
        cities = self.env["test_orm.city"].create(
            [
                {"name": "not null 2", "country_id": self.countries[2].id},
                {"name": "not null 0", "country_id": self.countries[0].id},
                {"name": False, "country_id": self.countries[1].id},
                {"name": "", "country_id": False},
                {"name": False, "country_id": False},
                {"name": "not null 1", "country_id": self.countries[1].id},
            ]
        )

        for order in [
            "country_id ASC, id",
            "country_id DESC, id",
            "country_id ASC NULLS FIRST, id",
            "country_id DESC NULLS FIRST, id",
            "country_id ASC NULLS LAST, id",
            "country_id DESC NULLS LAST, id",
            "name ASC, id",
            "name DESC, id",
            "name ASC NULLS FIRST, id",
            "name DESC NULLS FIRST, id",
            "name ASC NULLS LAST, id",
            "name DESC NULLS LAST, id",
        ]:
            with self.subTest(order=order):
                self.assertEqual(
                    self.env["test_orm.city"]
                    .search([("id", "in", cities.ids)], order=order)
                    .mapped("name"),
                    cities.sorted(order).mapped("name"),
                )

    def test_nulls_single_field(self):
        countries = self.env["test_orm.country"].create(
            [
                {"name": "B"},
                {"name": False},
                {"name": "A"},
                {"name": "C"},
            ]
        )
        for order in [
            "name ASC",
            "name DESC",
            "name ASC NULLS FIRST",
            "name DESC NULLS FIRST",
            "name ASC NULLS LAST",
            "name DESC NULLS LAST",
        ]:
            with self.subTest(order=order):
                self.assertEqual(
                    self.env["test_orm.country"]
                    .search([("id", "in", countries.ids)], order=order)
                    .mapped("name"),
                    countries.sorted(order).mapped("name"),
                )
        for order in [
            "name ASC",
            "name DESC",
            "name ASC NULLS FIRST",
            "name DESC NULLS FIRST",
            "name ASC NULLS LAST",
            "name DESC NULLS LAST",
        ]:
            with self.subTest(order=order, reverse=True):
                self.assertEqual(
                    countries.sorted(order).ids[::-1],
                    countries.sorted(order, reverse=True).ids,
                )

    def test_collation(self):
        countries = self.env["test_orm.country"].create(
            [
                {"name": "é"},
                {"name": "e"},
                {"name": "É"},
                {"name": "1.0"},
                {"name": "1,0"},
                {"name": "01"},
                {"name": "10"},
                {"name": "9"},
                {"name": "Ab"},
                {"name": "👍"},
                {"name": "AB"},
                {"name": "Aa"},
                {"name": "AA"},
            ]
        )

        for order in [
            "name DESC",
            "name ASC",
        ]:
            with self.subTest(order=order):
                self.assertEqual(
                    countries.search([("id", "in", countries.ids)], order=order).mapped(
                        "name"
                    ),
                    countries.sorted(order).mapped("name"),
                )

        ascii_countries = self.env["test_orm.country"].create(
            [{"name": "Banana"}, {"name": "apple"}, {"name": "Cherry"}]
        )
        self.assertEqual(
            ascii_countries.search(
                [("id", "in", ascii_countries.ids)], order="name ASC"
            ).mapped("name"),
            ["Banana", "Cherry", "apple"],
        )
        self.assertEqual(
            ascii_countries.search(
                [("id", "in", ascii_countries.ids)], order="name DESC"
            ).mapped("name"),
            ["apple", "Cherry", "Banana"],
        )

    def test_sorted_recursion(self):
        categories = self.env["test_orm.category"].search([])
        for order in [
            "parent ASC, id ASC",
            "parent ASC, id DESC",
            "parent DESC, id ASC",
            "parent DESC, id DESC",
        ]:
            with self.subTest(order=order):
                self.assertEqual(
                    categories.search(
                        [("id", "in", categories.ids)], order=order
                    ).mapped("name"),
                    categories.sorted(order).mapped("name"),
                )

    def test_compare_new_id(self):
        self.assertLess(5, NewId())
        self.assertLess(3, NewId(4))
        self.assertGreater(5, NewId(4))
        self.assertGreaterEqual(5, NewId(4))
        self.assertLess(4, NewId(4))
        self.assertGreater(NewId(5), NewId(4))

    def test_sorted_new_id(self):
        new_countries = self.env["test_orm.country"].concat(
            *[
                self.env["test_orm.country"].new(vals)
                for vals in [
                    {"name": "B"},
                    {"name": "A"},
                    {"name": "C"},
                ]
            ]
        )

        order = "id"
        self.assertEqual(
            (self.countries + new_countries).sorted(order),
            self.countries.sorted(order) + new_countries.sorted(order),
        )

        order = "id DESC"
        self.assertEqual(
            (self.countries + new_countries).sorted(order),
            new_countries.sorted(order) + self.countries.sorted(order),
        )

    def test_prefetch(self):
        partners_with_children = self.env["res.partner"].create(
            [
                {
                    "name": "required",
                    "child_ids": [
                        Command.create({"name": "z"}),
                        Command.create({"name": "a"}),
                    ],
                },
                {
                    "name": "required",
                    "child_ids": [
                        Command.create({"name": "z"}),
                        Command.create({"name": "a"}),
                    ],
                },
            ]
        )
        partners_with_children.invalidate_model(["name"])
        with self.assertQueryCount(1):
            for partner in partners_with_children:
                self.assertEqual(
                    partner.child_ids.sorted("id").mapped("name"), ["z", "a"]
                )


class TestSortNullPlacement(TransactionCase):
    def setUp(self):
        super().setUp()
        self.Model = self.env["test_orm.empty_int"]
        self.records = self.Model.create(
            [{"number": 5}, {}, {"number": 0}, {"number": -3}, {}]
        )
        self.env.flush_all()

    def _assert_same_order(self, order):
        scoped = [("id", "in", self.records.ids)]
        self.env.invalidate_all()
        expected = self.Model.search(scoped, order=order).ids
        self.env.invalidate_all()
        cold = self.records.sorted(order).ids
        warm_records = self.Model.browse(self.records.ids)
        warm_records.fetch(["number"])
        warm = warm_records.sorted(order).ids
        self.assertEqual(
            cold, expected, f"sorted({order!r}) disagrees with search(order=...)"
        )
        self.assertEqual(warm, cold, f"sorted({order!r}) depends on the cache state")

    def test_nulls_last_and_first(self):
        for order in (
            "number, id",
            "number DESC, id",
            "number NULLS FIRST, id",
            "number NULLS LAST, id",
            "number DESC NULLS FIRST, id",
            "number DESC NULLS LAST, id",
        ):
            with self.subTest(order=order):
                self._assert_same_order(order)

    def test_secondary_key_still_applies(self):
        null_ids = sorted((self.records[1] + self.records[4]).ids)
        self.env.invalidate_all()
        ordered = self.records.sorted("number NULLS LAST, id").ids
        self.assertEqual(ordered[-2:], null_ids)
        self.assertEqual(
            ordered[:-2],
            [self.records[3].id, self.records[2].id, self.records[0].id],
            "value rows must be ordered -3, 0, 5",
        )
