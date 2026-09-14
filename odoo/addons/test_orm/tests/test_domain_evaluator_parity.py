import random
from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.orm.domain import Domain
from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger


class TestDomainEvaluatorParity(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Partner = cls.env["res.partner"]
        cls.records = cls.Partner.create(
            [
                {"name": "P-null"},
                {"name": "P-empty", "comment": "", "ref": "", "color": 0},
                {
                    "name": "P-note",
                    "comment": "note",
                    "ref": "R1",
                    "color": 3,
                    "type": "invoice",
                    "partner_latitude": 10.5,
                },
                {
                    "name": "P-abc",
                    "comment": "abc",
                    "ref": "r2",
                    "color": 5,
                    "is_company": True,
                    "partner_latitude": 0.0,
                },
            ]
        )
        cls.env.flush_all()

    def assertParity(self, domain, msg=""):
        scoped = [("id", "in", self.records.ids), *domain]
        sql_ids = set(self.Partner.with_context(active_test=False).search(scoped).ids)
        py_ids = set(self.records.filtered_domain(domain).ids)
        self.assertEqual(
            sql_ids,
            py_ids,
            f"search() and filtered_domain() disagree on {domain!r} {msg}",
        )
        return sql_ids

    def test_inequality_string_comparand_on_integer_field(self):
        for operator in (">", ">=", "<", "<="):
            with self.subTest(operator=operator):
                self.assertParity([("color", operator, "3")])
        self.assertEqual(
            self.assertParity([("color", ">", "3")]),
            self.assertParity([("color", ">", 3)]),
            "a string comparand must select the same rows as its int form",
        )

    def test_inequality_comparand_on_html_field(self):
        for operator in (">", ">=", "<", "<="):
            with self.subTest(operator=operator):
                self.assertParity([("comment", operator, "note")])
        self.assertEqual(
            self.assertParity([("comment", ">=", "note")]),
            {self.records[2].id},
        )

    def test_inequality_on_relational_field_rejects_non_id(self):
        for value in ([1, 2], ["a"], True, "5", self.records[:1]):
            for operator in (">", ">=", "<", "<="):
                with self.subTest(value=value, operator=operator):
                    domain = [("parent_id", operator, value)]
                    with mute_logger("odoo.domains"):
                        with self.assertRaises(TypeError):
                            self.Partner.search(domain)
                        with self.assertRaises(TypeError):
                            self.records.filtered_domain(domain)

    def test_inequality_on_relational_field_accepts_numbers(self):
        pivot = self.records[1].id
        for value in (pivot, float(pivot)):
            for operator in (">", ">=", "<", "<="):
                with self.subTest(value=value, operator=operator):
                    self.assertParity([("parent_id", operator, value)])

    def test_parity_sweep(self):
        values = {
            "ref": ["R1", "", False, None, "r", 3],
            "color": [0, 3, "3", False, None, 2.0],
            "comment": ["note", "", False, None],
            "name": ["P-note", "", False, None, "P", 7],
            "active": [True, False, None],
            "is_company": [True, False, None],
            "type": ["contact", "other", False, None],
            "partner_latitude": [0.0, 10.5, "10.5", False, None],
            "create_date": ["2020-01-15 00:00:00", False, None],
            "parent_id": [False, None],
        }
        operators = [
            "=",
            "!=",
            "in",
            "not in",
            "like",
            "not like",
            "ilike",
            "not ilike",
            "=like",
            ">",
            "<",
            ">=",
            "<=",
        ]
        for fname, vals in values.items():
            for operator in operators:
                for value in vals:
                    domain = [(fname, operator, value)]
                    with self.subTest(domain=domain):
                        self._assert_same_outcome(domain)
                    if operator in ("in", "not in"):
                        domain = [(fname, operator, [value])]
                        with self.subTest(domain=domain):
                            self._assert_same_outcome(domain)

    def test_null_alias_inside_in_collection(self):
        cases = {
            "ref": [[None], [""], [False]],
            "comment": [[None], [""], [False]],
            "color": [[None], [0], [False]],
            "partner_latitude": [[None], [0.0], [False]],
            "type": [[None], [False]],
            "parent_id": [[None], [False]],
        }
        for fname, collections in cases.items():
            baseline_in = baseline_not_in = None
            for collection in collections:
                for operator in ("in", "not in"):
                    domain = [(fname, operator, collection)]
                    with self.subTest(domain=domain):
                        self.assertParity(domain)
                        scoped = [("id", "in", self.records.ids), *domain]
                        got = set(
                            self.Partner.with_context(active_test=False)
                            .search(scoped)
                            .ids
                        )
                        if operator == "in":
                            if baseline_in is None:
                                baseline_in = got
                            self.assertEqual(
                                got,
                                baseline_in,
                                f"{fname}: {collection!r} disagrees with the "
                                f"other null spellings",
                            )
                        else:
                            if baseline_not_in is None:
                                baseline_not_in = got
                            self.assertEqual(got, baseline_not_in)
            self.assertEqual(baseline_in | baseline_not_in, set(self.records.ids))
            self.assertFalse(baseline_in & baseline_not_in)

    def test_display_name_null_comparand(self):
        cases = [
            ([("display_name", "=", False)], set()),
            ([("display_name", "in", [False])], set()),
            ([("display_name", "in", [None])], set()),
            ([("display_name", "!=", False)], set(self.records.ids)),
            ([("display_name", "not in", [False])], set(self.records.ids)),
        ]
        for domain, expected in cases:
            with self.subTest(domain=domain):
                self.assertParity(domain)
                scoped = [("id", "in", self.records.ids), *domain]
                got = set(
                    self.Partner.with_context(active_test=False).search(scoped).ids
                )
                self.assertEqual(got, expected, f"wrong records for {domain!r}")

    def test_display_name_mixed_null_and_match_comparand(self):
        named = self.records.filtered(lambda r: r.display_name == "P-note")
        self.assertTrue(named, "fixture must contain the record being matched")
        for domain, expected in (
            ([("display_name", "in", ["P-note", False])], set(named.ids)),
            (
                [("display_name", "not in", ["P-note", False])],
                set(self.records.ids) - set(named.ids),
            ),
        ):
            with self.subTest(domain=domain):
                self.assertParity(domain)
                scoped = [("id", "in", self.records.ids), *domain]
                got = set(
                    self.Partner.with_context(active_test=False).search(scoped).ids
                )
                self.assertEqual(got, expected, f"wrong records for {domain!r}")

    def test_display_name_null_comparand_relational_rec_name(self):
        country = self.env["res.country"].search([], limit=1)
        self.assertTrue(country, "base data must provide a country")
        self.records[1].country_id = country.id
        self.env.flush_all()
        model_cls = type(self.env["res.partner"])
        for rec_names in (["name", "country_id"], ["name", "country_id.name"]):
            with (
                self.subTest(rec_names=rec_names),
                patch.object(model_cls, "_rec_names_search", rec_names),
            ):
                self.assertParity([("display_name", "!=", False)])
                self.assertParity([("display_name", "=", False)])
                scoped = [("id", "in", self.records.ids)]
                Partner = self.Partner.with_context(active_test=False)
                self.assertEqual(
                    set(Partner.search([*scoped, ("display_name", "!=", False)]).ids),
                    set(self.records.ids),
                    "every named record must satisfy 'display_name is set'",
                )
                self.assertFalse(
                    Partner.search([*scoped, ("display_name", "=", False)]),
                    "no named record may satisfy 'display_name is unset'",
                )

    def _assert_same_outcome(self, domain):
        scoped = [("id", "in", self.records.ids), *domain]
        sql_error = py_error = None
        try:
            with self.env.cr.savepoint():
                sql_ids = set(
                    self.Partner.with_context(active_test=False).search(scoped).ids
                )
        except (TypeError, ValueError, UserError) as exc:
            sql_error = exc
        try:
            py_ids = set(self.records.filtered_domain(domain).ids)
        except (TypeError, ValueError, UserError) as exc:
            py_error = exc

        if sql_error is not None or py_error is not None:
            self.assertEqual(
                sql_error is not None,
                py_error is not None,
                f"only one evaluator rejected {domain!r}: "
                f"sql={sql_error!r} python={py_error!r}",
            )
            return
        self.assertEqual(sql_ids, py_ids, f"evaluators disagree on {domain!r}")


class TestDomainComparandTypeParity(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Partner = cls.env["res.partner"].with_context(active_test=False)
        cls.country = cls.env["res.country"].search([], limit=1)
        cls.assertTrue(cls, cls.country, "base data must provide a country")
        cls.records = cls.env["res.partner"].create(
            [
                {"name": "T-plain"},
                {"name": "T-country", "country_id": cls.country.id},
                {"name": "0", "ref": "0"},
            ]
        )
        cls.env.flush_all()

    def assertSameOutcome(self, domain, msg=""):
        scoped = [("id", "in", self.records.ids), *domain]
        sql_error = py_error = None
        try:
            with self.env.cr.savepoint(flush=False):
                sql_ids = set(self.Partner.search(scoped).ids)
        except (TypeError, ValueError, UserError) as exc:
            sql_error = exc
        try:
            py_ids = set(self.records.filtered_domain(domain).ids)
        except (TypeError, ValueError, UserError) as exc:
            py_error = exc
        if sql_error is not None or py_error is not None:
            self.assertEqual(
                sql_error is not None,
                py_error is not None,
                f"only one evaluator rejected {domain!r} {msg}: "
                f"sql={sql_error!r} python={py_error!r}",
            )
            return None
        self.assertEqual(sql_ids, py_ids, f"evaluators disagree on {domain!r} {msg}")
        return sql_ids

    def test_number_comparand_on_textual_field(self):
        named_zero = self.records[2]
        self.assertEqual(
            self.assertSameOutcome([("name", "=", 0)]),
            {named_zero.id},
            "an integer comparand must match the record named '0'",
        )
        self.assertEqual(
            self.assertSameOutcome([("ref", "=", 0)]),
            {named_zero.id},
            "an integer comparand must not be read as 'ref is unset'",
        )
        self.assertEqual(
            self.assertSameOutcome([("name", "!=", 0)]),
            set(self.records.ids) - {named_zero.id},
        )
        self.assertSameOutcome([("name", "=", 7)])

    def test_falsy_id_comparand_on_many2one(self):
        no_country = self.records.filtered(lambda r: not r.country_id)
        self.assertEqual(
            self.assertSameOutcome([("country_id", "=", 0)]),
            set(no_country.ids),
        )
        self.assertEqual(
            self.assertSameOutcome([("country_id", "!=", 0)]),
            set(self.records.ids) - set(no_country.ids),
        )
        for operator in (">", ">=", "<", "<="):
            with self.subTest(operator=operator):
                self.assertFalse(self.assertSameOutcome([("country_id", operator, 0)]))
        self.assertEqual(
            self.assertSameOutcome([("country_id", "=", self.country.id)]),
            set((self.records - no_country).ids),
        )

    def test_ordering_comparand_against_collection(self):
        for domain in (
            [("color", ">", [0, 1])],
            [("id", "<", ["1"])],
            [("type", ">", ["contact", "invoice"])],
            [("name", ">", ["a", "b"])],
        ):
            with self.subTest(domain=domain):
                self.assertSameOutcome(domain)
                with self.assertRaises(TypeError):
                    self.Partner.search(domain)
                with self.assertRaises(TypeError):
                    self.records.filtered_domain(domain)

    def test_ordering_against_empty_collection_is_rejected(self):
        for fname in ("create_date", "color", "name"):
            for domain in ([(fname, ">=", [])], ["!", (fname, ">=", [])]):
                with self.subTest(domain=domain):
                    self.assertSameOutcome(domain)
                    with self.assertRaises(TypeError):
                        self.Partner.search(domain)
                    with self.assertRaises(TypeError):
                        self.records.filtered_domain(domain)

    def test_ordering_on_x2many_is_rejected(self):
        for fname in ("child_ids", "tag_ids"):
            for operator in (">", ">=", "<", "<="):
                for value in (1, 0):
                    with self.subTest(fname=fname, operator=operator, value=value):
                        domain = [(fname, operator, value)]
                        with self.assertRaises(TypeError):
                            self.Partner.search(domain)
                        with self.assertRaises(TypeError):
                            self.records.filtered_domain(domain)

    def test_validation_does_not_depend_on_sibling_order(self):
        malformed = ("child_ids", ">", [1])
        domain = ["|", ("ref", "=?", []), malformed]
        self.assertEqual(
            self.assertSameOutcome(domain),
            set(self.records.ids),
            "a TRUE sibling must discard the malformed leaf in both evaluators",
        )
        with self.assertRaises(TypeError):
            self.Partner.search([malformed])
        with self.assertRaises(TypeError):
            self.records.filtered_domain([malformed])

    def test_unrepresentable_id_comparand_matches_nothing(self):
        good = self.records[0].id
        self.assertFalse(
            self.Partner.search([("id", "=", "fz-a")]),
            "an unrepresentable id must select nothing, not raise",
        )
        self.assertTrue(self.Partner.search([("id", "!=", "fz-a")]))
        self.assertFalse(self.Partner.search([("id", "in", ["fz-a"])]))
        self.assertEqual(
            set(self.Partner.search([("id", "in", ["fz-a", good])]).ids), {good}
        )
        for domain, expected in (
            ([("child_ids", "any", [("id", "=", "fz-a")])], set()),
            ([("id", "=", "fz-a")], set()),
            ([("id", "in", ["fz-a"])], set()),
            ([("id", "!=", "fz-a")], set(self.records.ids)),
            ([("id", "not in", ["fz-a"])], set(self.records.ids)),
            ([("id", "in", ["fz-a", good])], {good}),
            ([("id", "not in", ["fz-a", good])], set(self.records.ids) - {good}),
            ([("id", "=", str(good))], {good}),
        ):
            with self.subTest(domain=domain):
                self.assertEqual(self.assertSameOutcome(domain), expected)
        for operator in (">", ">=", "<", "<="):
            with self.subTest(operator=operator):
                domain = [("id", operator, "fz-a")]
                self.assertSameOutcome(domain)
                with self.assertRaises(ValueError):
                    self.Partner.search(domain)

    def test_display_name_null_comparand_survives_a_search_override(self):
        State = self.env["res.country.state"]
        for domain in (
            [("display_name", "=", False)],
            [("display_name", "!=", False)],
            [("display_name", "in", [False])],
        ):
            with self.subTest(domain=domain):
                State.search(domain)
        for domain in (
            [("state_id", "any", [("display_name", "=", False)])],
            [("state_id", "not any", [("display_name", "=", False)])],
        ):
            with self.subTest(domain=domain):
                self.assertSameOutcome(domain)

    def test_cyclic_rec_names_search_stays_searchable(self):
        model_cls = type(self.env["res.partner"])
        with (
            patch.object(model_cls, "_rec_names_search", ["name", "parent_id"]),
            self.assertLogs("odoo.models", level="WARNING") as logs,
        ):
            self.assertEqual(
                set(
                    self.Partner.search(
                        [
                            ("id", "in", self.records.ids),
                            ("display_name", "=", "T-plain"),
                        ]
                    ).ids
                ),
                {self.records[0].id},
                "the non-cyclic entry must still resolve the name",
            )
            for operator, value in (
                ("ilike", "T-"),
                ("=", False),
                ("!=", False),
                ("not ilike", "zzz"),
            ):
                with self.subTest(operator=operator, value=value):
                    self.Partner.search([("display_name", operator, value)])
        self.assertTrue(
            all("Dropping cyclic _rec_names_search" in line for line in logs.output),
            logs.output,
        )

    def test_display_name_ordering_uses_the_primary_name(self):
        for operator in ("<", "<=", ">", ">="):
            for value in ("T-country", "T-plain"):
                with self.subTest(operator=operator, value=value):
                    self.assertSameOutcome([("display_name", operator, value)])


class TestDomainComparandExactness(TransactionCase):
    def assertSelects(self, model, records, domain, expected, msg=""):
        scoped = [("id", "in", records.ids), *domain]
        sql = model.with_context(active_test=False).search(scoped)
        python = records.filtered_domain(domain)
        self.assertEqual(
            set(sql.ids),
            set(python.ids),
            f"search() and filtered_domain() disagree on {domain!r} {msg}",
        )
        self.assertEqual(
            set(sql.ids),
            set(expected.ids),
            f"wrong records for {domain!r} {msg}",
        )

    def test_integer_fractional_comparand(self):
        Model = self.env["test_orm.empty_int"]
        one, two, three, null = Model.create(
            [{"number": 1}, {"number": 2}, {"number": 3}, {}]
        )
        self.env.flush_all()
        records = one + two + three + null
        self.assertSelects(Model, records, [("number", "<", 2.5)], one + two + null)
        self.assertSelects(Model, records, [("number", "<=", 2.5)], one + two + null)
        self.assertSelects(Model, records, [("number", ">", 2.5)], three)
        self.assertSelects(Model, records, [("number", ">=", 2.5)], three)
        self.assertSelects(Model, records, [("number", "=", 2.5)], Model)
        self.assertSelects(Model, records, [("number", "!=", 2.5)], records)
        self.assertSelects(Model, records, [("number", "in", [2.5, 3])], three)
        self.assertSelects(Model, records, [("number", "not in", [2.5])], records)
        self.assertSelects(Model, records, [("number", ">=", -0.5)], records)

    def test_integer_string_comparand(self):
        Model = self.env["test_orm.empty_int"]
        one, two, three = Model.create([{"number": 1}, {"number": 2}, {"number": 3}])
        self.env.flush_all()
        records = one + two + three
        self.assertSelects(Model, records, [("number", "=", "2")], two)
        self.assertSelects(Model, records, [("number", "<", "2.5")], one + two)
        self.assertSelects(Model, records, [("number", "=", "2.5")], Model)
        self.assertSelects(Model, records, [("number", "=", "abc")], Model)
        self.assertSelects(Model, records, [("number", "!=", "abc")], records)
        for operator in (">", ">=", "<", "<="):
            with self.subTest(operator=operator):
                domain = [("number", operator, "abc")]
                with self.assertRaises(ValueError):
                    Model.search(domain)
                with self.assertRaises(ValueError):
                    records.filtered_domain(domain)

    def test_float_digits_comparand(self):
        Model = self.env["decimal.precision.test"]
        low, mid, high = Model.create(
            [{"float_2": 9.99}, {"float_2": 10.00}, {"float_2": 10.01}]
        )
        self.env.flush_all()
        records = low + mid + high
        self.assertSelects(Model, records, [("float_2", "<", 10.004)], low + mid)
        self.assertSelects(Model, records, [("float_2", "<=", 10.004)], low + mid)
        self.assertSelects(Model, records, [("float_2", ">", 10.004)], high)
        self.assertSelects(Model, records, [("float_2", ">=", 10.004)], high)
        self.assertSelects(Model, records, [("float_2", "=", 10.004)], Model)
        self.assertSelects(Model, records, [("float_2", "!=", 10.004)], records)
        self.assertSelects(Model, records, [("float_2", ">", 9.996)], mid + high)
        self.assertSelects(Model, records, [("float_2", "=", 10.00)], mid)


class TestDomainWildcardOnlyPattern(TransactionCase):
    def test_wildcard_only_pattern_on_char(self):
        Model = self.env["test_orm.empty_char"]
        null, empty, abc = Model.create([{}, {"name": ""}, {"name": "abc"}])
        self.env.flush_all()
        records = null + empty + abc
        for pattern in ("%", "%%"):
            for operator in ("like", "ilike", "=like", "=ilike"):
                with self.subTest(operator=operator, pattern=pattern):
                    domain = [("name", operator, pattern)]
                    self.assertEqual(
                        set(Model.search([("id", "in", records.ids), *domain]).ids),
                        set(records.ids),
                        f"{domain!r} must match every record",
                    )
                    self.assertEqual(
                        set(records.filtered_domain(domain).ids), set(records.ids)
                    )
                negative = [("name", f"not {operator}", pattern)]
                self.assertFalse(
                    Model.search([("id", "in", records.ids), *negative]),
                    f"{negative!r} must match no record",
                )
                self.assertFalse(records.filtered_domain(negative))
        for domain, expected in (
            ([("name", "ilike", "_")], abc),
            ([("name", "=ilike", "_")], Model),
        ):
            self.assertEqual(
                set(Model.search([("id", "in", records.ids), *domain]).ids),
                set(expected.ids),
            )
            self.assertEqual(
                set(records.filtered_domain(domain).ids), set(expected.ids)
            )

    def test_wildcard_only_pattern_on_many2one(self):
        Model = self.env["test_orm.team"]
        parent = Model.create({"name": "root"})
        with_parent = Model.create({"name": "child", "parent_id": parent.id})
        self.env.flush_all()
        records = parent + with_parent
        for domain, expected in (
            ([("parent_id", "ilike", "%")], with_parent),
            ([("parent_id", "not ilike", "%")], parent),
        ):
            self.assertEqual(
                set(Model.search([("id", "in", records.ids), *domain]).ids),
                set(expected.ids),
                f"wrong records for {domain!r}",
            )
            self.assertEqual(
                set(records.filtered_domain(domain).ids),
                set(expected.ids),
                f"filtered_domain disagrees on {domain!r}",
            )


class TestDomainIdComparand(TransactionCase):
    def setUp(self):
        super().setUp()
        self.Model = self.env["test_orm.empty_int"]
        self.records = self.Model.create([{"number": n} for n in (1, 2, 3, 4)])
        self.env.flush_all()

    def assertParity(self, domain, expected):
        scoped = [("id", "in", self.records.ids), *domain]
        sql = set(self.Model.with_context(active_test=False).search(scoped).ids)
        python = set(self.records.filtered_domain(domain).ids)
        self.assertEqual(sql, python, f"evaluators disagree on {domain!r}")
        self.assertEqual(sql, set(expected.ids), f"wrong records for {domain!r}")

    def test_string_id_comparand(self):
        second = self.records[1]
        self.assertParity([("id", "=", str(second.id))], second)
        self.assertParity([("id", "in", [str(second.id)])], second)
        self.assertParity([("id", "!=", str(second.id))], self.records - second)
        self.assertParity([("id", ">=", str(second.id))], self.records[1:])
        self.assertParity([("id", "<", str(second.id))], self.records[0])

    def test_string_id_merged_with_sibling_condition(self):
        first, second = self.records[0], self.records[1]
        self.assertParity(
            [("id", "in", [str(second.id), first.id]), ("id", "in", self.records.ids)],
            first + second,
        )
        self.assertParity(
            [("id", "not in", [str(second.id)]), ("id", "in", self.records.ids)],
            self.records - second,
        )
        self.assertParity([("number", "in", ["2"]), ("number", "in", [2, 3])], second)

    def test_non_id_string_comparand(self):
        self.assertParity([("id", "in", ["abc"])], self.Model)
        self.assertParity(
            [("id", "in", ["abc"]), ("id", "in", self.records.ids)], self.Model
        )
        for operator in (">", ">=", "<", "<="):
            with self.subTest(operator=operator):
                domain = [("id", operator, "abc")]
                with self.assertRaises(ValueError):
                    self.Model.search(domain)
                with self.assertRaises(ValueError):
                    self.records.filtered_domain(domain)

    def test_fractional_id_comparand(self):
        second, third = self.records[1], self.records[2]
        for value in (float(third.id) - 0.5, str(float(third.id) - 0.5)):
            with self.subTest(value=value):
                self.assertParity([("id", ">=", value)], self.records[2:])
                self.assertParity([("id", "<", value)], self.records[:2])
                self.assertParity([("id", "=", value)], self.Model)
        self.assertParity([("id", ">", str(float(second.id)))], self.records[2:])

    def test_text_id_model_is_left_alone(self):
        View = self.env["test_orm.view.str.id"]
        rows = View.search([])
        self.assertEqual(rows.ids, ["hello"])
        for domain in (
            [("id", "=", "hello")],
            [("id", "in", ["hello"])],
            [("id", "in", ["hello"]), ("id", "in", ["hello", "other"])],
            [("id", ">", "a")],
        ):
            with self.subTest(domain=domain):
                self.assertEqual(View.search(domain).ids, ["hello"])
                self.assertEqual(rows.filtered_domain(domain).ids, ["hello"])


class _DomainGeneratorMixin:
    SEED = 20260726
    DOMAINS = 400

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Partner = cls.env["res.partner"]
        cls.records = cls.Partner.create(
            [
                {"name": "G-null"},
                {"name": "G-empty", "comment": "", "ref": "", "color": 0},
                {"name": "G-zero", "color": 0, "partner_latitude": 0.0, "ref": "0"},
                {"name": "G-neg", "color": -3, "partner_latitude": -1.5, "ref": "-1"},
                {"name": "G-one", "color": 1, "partner_latitude": 1.0, "ref": "1"},
                {"name": "G-two", "color": 2, "partner_latitude": 2.5, "ref": "2"},
                {"name": "G-three", "color": 3, "partner_latitude": 3.0, "ref": "R3"},
                {"name": "G-ten", "color": 10, "partner_latitude": 10.5, "ref": "r10"},
                {"name": "G-type", "color": 5, "type": "invoice", "is_company": True},
                {"name": "G-dup", "color": 5, "ref": "R3", "comment": "note"},
                {"name": "G-uni", "color": 7, "ref": "Ünïcøde", "comment": "nöte"},
                {"name": "G-pct", "color": 8, "ref": "50%_off", "comment": "a_b%c"},
            ]
        )
        cls.env.flush_all()

    def _specs(self):
        num_ops = ["=", "!=", "<", "<=", ">", ">="]
        text_ops = [
            "=",
            "!=",
            "in",
            "not in",
            "like",
            "not like",
            "ilike",
            "=like",
            *num_ops,
        ]
        return [
            (
                "color",
                num_ops + ["in", "not in"],
                [0, 1, 2, 3, -3, 2.5, -1.5, "2", "0", False],
            ),
            ("partner_latitude", num_ops, [0.0, 1.0, 2.5, -1.5, 3, "1", False]),
            ("ref", text_ops, ["R3", "r10", "", "0", "%", "_", "Ünïcøde", False, 3]),
            ("comment", text_ops, ["note", "nöte", "a_b%c", "", False]),
            ("name", text_ops, ["G-one", "g-", "%", "", False]),
            ("type", ["=", "!=", "in", "not in"], ["invoice", "contact", "", False]),
            ("is_company", ["=", "!=", "in", "not in"], [True, False]),
            ("active", ["=", "!=", "in", "not in"], [True, False]),
        ]

    def _condition(self, rng, specs):
        fname, ops, values = rng.choice(specs)
        op = rng.choice(ops)
        if op in ("in", "not in"):
            value = rng.sample(values, rng.randint(1, min(3, len(values))))
        else:
            value = rng.choice(values)
        return Domain(fname, op, value)

    def _domain(self, rng, specs, depth=0):
        if depth >= 2 or rng.random() < 0.5:
            return self._condition(rng, specs)
        roll = rng.random()
        if roll < 0.8:
            parts = [
                self._domain(rng, specs, depth + 1) for _ in range(rng.randint(2, 3))
            ]
            return Domain.AND(parts) if roll < 0.4 else Domain.OR(parts)
        return ~self._domain(rng, specs, depth + 1)

    def _evaluate(self, model, records, domain):
        try:
            if model is not None:
                with self.env.cr.savepoint(flush=False):
                    scoped = Domain("id", "in", records.ids) & domain
                    return None, set(model.search(scoped).ids)
            return None, set(records.filtered_domain(domain).ids)
        except Exception as error:
            return type(error).__name__, None


class TestDomainEvaluatorParityGenerated(_DomainGeneratorMixin, TransactionCase):
    def test_generated_domains_agree_between_evaluators(self):
        rng = random.Random(self.SEED)
        specs = self._specs()
        records = self.records.with_context(active_test=False)
        model = self.Partner.with_context(active_test=False)
        refused = 0
        for index in range(self.DOMAINS):
            domain = self._domain(rng, specs)
            with self.subTest(index=index, domain=list(domain)):
                sql_error, sql_ids = self._evaluate(model, records, domain)
                py_error, py_ids = self._evaluate(None, records, domain)
                context = f"on {list(domain)!r} (seed={self.SEED}, index={index})"
                self.assertEqual(
                    sql_error is None,
                    py_error is None,
                    f"one evaluator refused and the other did not {context}: "
                    f"search={sql_error or 'ok'} filtered_domain={py_error or 'ok'}",
                )
                if sql_error is None:
                    self.assertEqual(sql_ids, py_ids, f"evaluators disagree {context}")
                else:
                    refused += 1
        self.assertLess(
            refused,
            self.DOMAINS // 2,
            "most generated domains were refused — the generator stopped "
            "exercising the evaluators",
        )


class TestDomainPartition(_DomainGeneratorMixin, TransactionCase):
    SEED = 20260727

    def test_generated_domains_partition_the_record_set(self):
        rng = random.Random(self.SEED)
        specs = self._specs()
        records = self.records.with_context(active_test=False)
        model = self.Partner.with_context(active_test=False)
        all_ids = set(records.ids)
        checked = 0
        for index in range(self.DOMAINS):
            domain = self._domain(rng, specs)
            with self.subTest(index=index, domain=list(domain)):
                error, ids = self._evaluate(model, records, domain)
                if error is not None:
                    continue
                neg_error, neg_ids = self._evaluate(model, records, ~domain)
                context = f"for {list(domain)!r} (seed={self.SEED}, index={index})"
                self.assertIsNone(
                    neg_error,
                    f"search accepted a domain but refused its negation {context}: "
                    f"{neg_error}",
                )
                self.assertFalse(
                    ids & neg_ids,
                    f"records satisfy both a domain and its negation {context}: "
                    f"{sorted(ids & neg_ids)[:5]}",
                )
                self.assertEqual(
                    ids | neg_ids,
                    all_ids,
                    f"records satisfy neither a domain nor its negation {context}: "
                    f"{sorted(all_ids - (ids | neg_ids))[:5]}",
                )
                checked += 1
        self.assertGreater(
            checked,
            self.DOMAINS // 2,
            "most generated domains were refused — the generator stopped "
            "exercising the partition law",
        )

    def test_search_count_agrees_with_search(self):
        rng = random.Random(self.SEED + 1)
        specs = self._specs()
        records = self.records.with_context(active_test=False)
        model = self.Partner.with_context(active_test=False)
        for index in range(self.DOMAINS):
            domain = self._domain(rng, specs)
            with self.subTest(index=index, domain=list(domain)):
                error, ids = self._evaluate(model, records, domain)
                if error is not None:
                    continue
                scoped = Domain("id", "in", records.ids) & domain
                self.assertEqual(
                    model.search_count(scoped),
                    len(ids),
                    f"search_count disagrees with search on {list(domain)!r} "
                    f"(seed={self.SEED + 1}, index={index})",
                )


class TestSearchDefinedPredicateQueries(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        discussion = cls.env["test_orm.discussion"].create(
            {"name": "sizes", "participants": [(4, cls.env.user.id)]}
        )
        cls.messages = cls.env["test_orm.message"].create(
            [
                {"discussion": discussion.id, "body": body}
                for body in ("ab", "abcd", "abcdef")
            ]
        )
        cls.env.flush_all()

    def test_an_id_set_from_the_search_method_is_not_queried_again(self):
        messages = self.messages.sudo()
        domain = [("size", ">", 3)]
        expected = messages.search([("id", "in", messages.ids), *domain])
        messages.invalidate_recordset()
        with self.assertQueryCount(1):
            self.assertEqual(messages.filtered_domain(domain), expected)

    def test_a_search_method_answer_is_still_limited_to_the_filtered_records(self):
        messages = self.messages.sudo()
        subset = messages[:2]
        self.assertEqual(subset.filtered_domain([("size", ">", 1)]), subset)


class TestFieldTypeMatrixParity(TransactionCase):
    # every (field, operator, value) triple the generator above cannot reach:
    # Reference, Binary, Html, Datetime, Selection, x2many and Properties
    OPERATORS = (
        "=",
        "!=",
        "in",
        "not in",
        "like",
        "ilike",
        "not like",
        "not ilike",
        "=like",
        "=ilike",
        "<",
        "<=",
        ">",
        ">=",
    )

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "Matrix partner"})
        cls.currency = cls.env.ref("base.EUR")
        cls.mixed = cls.env["test_orm.mixed"].create(
            [
                {
                    "foo": "Alpha",
                    "text": "first line",
                    "truth": True,
                    "count": 3,
                    "number": 1.5,
                    "date": "2026-01-15",
                    "moment": "2026-01-15 23:30:00",
                    "lang": "en_US",
                    "reference": f"res.partner,{cls.partner.id}",
                    "comment0": "<p>Hello <b>world</b></p>",
                    "currency_id": cls.currency.id,
                    "amount": 10.0,
                },
                {
                    "foo": "beta",
                    "text": "",
                    "truth": False,
                    "count": 0,
                    "number": 0.0,
                    "date": False,
                    "moment": False,
                    "lang": False,
                    "reference": False,
                    "comment0": "",
                    "currency_id": False,
                    "amount": 0.0,
                },
                {
                    "foo": "",
                    "text": False,
                    "count": -2,
                    "number": 3.14,
                    "date": "2026-03-01",
                    "moment": "2026-03-01 00:00:00",
                    "lang": "fr_FR",
                    "reference": f"res.currency,{cls.currency.id}",
                    "comment0": "<p>Accent</p>",
                    "currency_id": cls.currency.id,
                    "amount": 0.005,
                },
                {"foo": False, "text": "x", "truth": True, "count": 7},
            ]
        )
        bars = cls.env["test_orm.related_bar"].create(
            [{"name": "bar one"}, {"name": False}]
        )
        cls.bars = bars
        cls.foos = cls.env["test_orm.related_foo"].create(
            [
                {
                    "name": "f1",
                    "bar_id": bars[0].id,
                    "bar_ids": [(6, 0, bars.ids)],
                    "binary_bin": b"Ymlu",
                },
                {"name": "f2", "bar_id": bars[1].id, "bar_ids": [(6, 0, bars[1].ids)]},
                {"name": False},
            ]
        )
        discussion = cls.env["test_orm.discussion"].create(
            {
                "name": "matrix",
                "participants": [(4, cls.env.user.id)],
                "attributes_definition": [
                    {"name": "color", "type": "char"},
                    {"name": "size", "type": "integer"},
                    {
                        "name": "tag",
                        "type": "selection",
                        "selection": [["a", "A"], ["b", "B"]],
                    },
                    {"name": "flag", "type": "boolean"},
                    {
                        "name": "labels",
                        "type": "tags",
                        "tags": [["x", "X", 1], ["y", "Y", 2]],
                    },
                ],
            }
        )
        cls.messages = cls.env["test_orm.message"].create(
            [
                {
                    "discussion": discussion.id,
                    "body": "one",
                    "attributes": {
                        "color": "red",
                        "size": 3,
                        "tag": "a",
                        "flag": True,
                        "labels": ["x", "y"],
                    },
                },
                {
                    "discussion": discussion.id,
                    "body": "two",
                    "attributes": {
                        "color": False,
                        "size": 0,
                        "tag": False,
                        "flag": False,
                        "labels": ["y"],
                    },
                },
                {
                    "discussion": discussion.id,
                    "body": "three",
                    "attributes": {"color": "false", "size": False, "labels": []},
                },
                {"discussion": discussion.id, "body": "four"},
            ]
        )
        cls.env.flush_all()
        cls.env.invalidate_all()

    def _specs(self):
        partner, currency = self.partner, self.currency
        bar_one, bar_none = self.bars
        return [
            (
                self.mixed,
                {
                    "foo": ["Alpha", "alpha", "", False, "%pha", "a"],
                    "text": ["first line", "", False, "line"],
                    "truth": [True, False, "True", "false", "1", "0"],
                    "count": [0, 3, False, -2, "3", 2.5],
                    "number": [0.0, 1.5, 3.14, False, 0, "1.5", 1.4999999],
                    "date": [
                        "2026-01-15",
                        False,
                        "2026-01-15 10:00:00",
                        "2026-02-01",
                    ],
                    "moment": [
                        "2026-01-15",
                        "2026-01-15 23:30:00",
                        False,
                        "2026-01-16",
                    ],
                    "lang": ["en_US", "fr_FR", False, "en"],
                    "reference": [
                        f"res.partner,{partner.id}",
                        False,
                        "res.partner",
                        f"res.currency,{currency.id}",
                        "res.partner,%",
                        "res",
                    ],
                    "comment0": [
                        "<p>Hello <b>world</b></p>",
                        "Hello",
                        "",
                        False,
                        "world",
                    ],
                    "currency_id": [
                        currency.id,
                        False,
                        "EUR",
                        [currency.id, False],
                        "E",
                    ],
                    "amount": [10.0, 0.0, False, 0.005, 0.01],
                    "id": [
                        self.mixed[0].id,
                        False,
                        [self.mixed[0].id, self.mixed[1].id],
                    ],
                },
            ),
            (
                self.foos,
                {
                    "bar_id": [bar_one.id, bar_none.id, False, "bar one", "bar", ""],
                    "bar_id.name": ["bar one", False, "", "one"],
                    "bar_ids": [bar_one.id, False, self.bars.ids, "bar one", "", "bar"],
                    "bar_ids.name": ["bar one", False, ""],
                    "bar_name": ["bar one", False, "", "bar"],
                    "bar_alias": [bar_one.id, False, "bar"],
                    "binary_bin": [False, "Ymlu"],
                    "name": ["f1", False, "", "f"],
                },
            ),
            (
                self.messages,
                {
                    "attributes.color": ["red", False, "", "re", "RED", "false", "als"],
                    "attributes.size": [3, 0, False, 2, 0.0, [0, 3]],
                    "attributes.tag": ["a", "b", False, ["a", False]],
                    "attributes.flag": [True, False],
                    "attributes.labels": ["x", "y", False, ["x", "y"], ["y", False]],
                },
            ),
        ]

    def _triples(self):
        for records, values in self._specs():
            for field_expr, candidates in values.items():
                for operator in self.OPERATORS:
                    for value in candidates:
                        if operator in ("in", "not in") and not isinstance(value, list):
                            value = [value]
                        if operator.endswith("like") and not isinstance(value, str):
                            continue
                        if operator in ("<", "<=", ">", ">=") and (
                            isinstance(value, list | bool) or field_expr == "binary_bin"
                        ):
                            continue
                        yield records, field_expr, operator, value

    def _evaluate(self, records, domain):
        model = records.with_context(active_test=False)
        scoped = [("id", "in", records.ids), *domain]
        try:
            with self.env.cr.savepoint(), mute_logger("odoo.db.cursor"):
                sql_ids = set(model.search(scoped).ids)
        except Exception as exc:  # the pair of outcomes is the finding
            sql_ids = type(exc).__name__
        try:
            with self.env.cr.savepoint():
                py_ids = set(records.filtered_domain(domain).ids)
        except Exception as exc:
            py_ids = type(exc).__name__
        return sql_ids, py_ids

    def test_search_and_filtered_domain_agree_on_every_triple(self):
        compared = 0
        for records, field_expr, operator, value in self._triples():
            domain = [(field_expr, operator, value)]
            with self.subTest(model=records._name, domain=domain):
                sql_ids, py_ids = self._evaluate(records, domain)
                compared += 1
                self.assertEqual(
                    sql_ids,
                    py_ids,
                    f"search() and filtered_domain() disagree on {domain!r}",
                )
        self.assertGreater(compared, 1000)
