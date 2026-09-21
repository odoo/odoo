"""Tests for the partner res.partner overrides."""

import datetime

from dateutil.relativedelta import relativedelta
from lxml import etree

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged
from odoo.tools.safe_eval import safe_eval


@tagged("post_install", "-at_install")
class TestResPartner(TransactionCase):
    def test_get_backend_root_menu_ids_includes_partner_menu(self):
        """res.partner's backend root menu includes partner's own menu."""
        menu_ids = self.env["res.partner"]._get_backend_root_menu_ids()
        self.assertIn(self.env.ref("partner.partner_menu_root").id, menu_ids)


@tagged("post_install", "-at_install")
class TestSearchAge(TransactionCase):
    """`age` is computed, not stored, and must still be answerable in SQL.

    The mapping runs backwards -- an older contact was born earlier -- so every
    operator inverts, and the strict forms shift a year because "older than 30"
    means "has completed 31".
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Partner = cls.env["res.partner"]
        today = fields.Date.today()
        cls.ages = {}
        for age in (17, 18, 19, 40):
            cls.ages[age] = cls.Partner.create(
                {
                    "name": f"Aged {age}",
                    # Half a year in, so no test sits on a birthday boundary.
                    "birthdate": today - relativedelta(years=age, months=6),
                }
            )
        cls.undated = cls.Partner.create({"name": "No birthdate"})
        cls.newborn = cls.Partner.create(
            {"name": "Newborn", "birthdate": today - relativedelta(months=1)}
        )

    def _found(self, operator, value):
        ids = [partner.id for partner in self.ages.values()] + self.undated.ids
        found = self.Partner.search([("id", "in", ids), ("age", operator, value)])
        return {partner.age for partner in found}

    def test_the_computed_age_is_what_it_claims(self):
        for age, partner in self.ages.items():
            self.assertEqual(partner.age, age)
        self.assertFalse(self.undated.age)

    def test_at_least_and_strictly_older(self):
        self.assertEqual(self._found(">=", 18), {18, 19, 40})
        self.assertEqual(self._found(">", 18), {19, 40})

    def test_at_most_and_strictly_younger(self):
        self.assertEqual(self._found("<", 18), {17})
        self.assertEqual(self._found("<=", 18), {17, 18})

    def test_an_exact_age_is_a_one_year_window(self):
        self.assertEqual(self._found("=", 18), {18})
        self.assertEqual(self._found("!=", 18), {17, 19, 40})

    def test_a_partner_without_a_birthdate_matches_no_comparison(self):
        """It has no age, so it is absent from a comparison and its negation.

        ``=`` and ``!=`` are not comparisons here and are asserted separately:
        the ORM folds ``0`` into ``False`` on an Integer field before the
        search method sees it, so ``age = 0`` is not a question about zero.
        """
        for operator, value in ((">=", 0), ("<", 200), (">", 1), ("<=", 199)):
            self.assertNotIn(
                self.undated,
                self.Partner.search([("age", operator, value)]),
                f"a partner with no birthdate was returned by age {operator} {value}",
            )

    def test_an_unsupported_operator_says_so(self):
        with self.assertRaises(NotImplementedError):
            self.Partner.search([("age", "like", "18")])

    def test_equality_against_nothing_asks_whether_an_age_is_set(self):
        """`= False` is the framework's spelling of "not set", and `= 0` is it.

        The ORM folds ``0`` into ``False`` on an Integer field before a search
        method is reached, so ``age = 0`` and ``age = False`` are one domain
        and no implementation can separate "aged zero" from "has no age". The
        fold decides which of the two the pair must mean, and it is the one
        every generic tool asks: ``isinstance(False, int)`` is True, so an
        unguarded numeric path answers "is not set" with the contacts born in
        the last twelve months. Exactly-zero is still reachable as
        ``age >= 0`` intersected with ``age < 1``.
        """
        candidates = [partner.id for partner in self.ages.values()]
        candidates += self.undated.ids + self.newborn.ids

        unset = self.Partner.search([("id", "in", candidates), ("age", "=", False)])
        self.assertEqual(unset, self.undated)
        self.assertNotIn(self.newborn, unset, "a newborn is not a contact without age")

        aged = self.Partner.search([("id", "in", candidates), ("age", "!=", False)])
        self.assertNotIn(self.undated, aged)
        self.assertIn(self.newborn, aged, "a newborn has an age, and it is zero")

    def test_an_integral_float_is_still_a_whole_number_of_years(self):
        """JSON has one number type, so a filter can hand this method 18.0."""
        self.assertEqual(self._found(">=", 18.0), {18, 19, 40})

    def test_a_fractional_age_is_a_user_error_not_a_crash(self):
        """Only NotImplementedError and UserError survive domain optimization.

        Anything else escapes ``_optimize_field_search_method`` and reaches the
        client as an Internal Server Error.
        """
        for value in (18.5, -0.25):
            with self.assertRaises(UserError):
                self.Partner.search([("age", ">", value)])

    def test_age_declares_no_aggregator_and_folds_through_records_when_asked(self):
        """`web/static/src/model/relational_model/field_values.js` asks the
        server for `<field>:<aggregator>` for every aggregatable field a view
        holds; Integer defaults to `sum`, which is meaningless for ages, so the
        field declares none. Asked for explicitly, an aggregate of this
        non-stored compute folds through the group's records (odoo
        1700ca96ddc1), so a grouped list that wants an average gets one.
        """
        self.assertFalse(self.Partner._fields["age"].aggregator)
        adults = self.Partner.browse(
            [self.ages[18].id, self.ages[19].id, self.ages[40].id]
        )
        groups = self.Partner._read_group(
            [("id", "in", adults.ids)], ["age_range_id"], ["age:avg"]
        )
        self.assertTrue(groups)
        for age_range, average in groups:
            members = adults.filtered(lambda p, r=age_range: p.age_range_id == r)
            self.assertTrue(members)
            self.assertAlmostEqual(average, sum(members.mapped("age")) / len(members))


@tagged("post_install", "-at_install")
class TestBirthdayFilters(TransactionCase):
    """The birthday filters are answered in SQL by the field's date parts.

    ``birthdate.month_number`` and ``birthdate.day_of_month`` are resolved by
    the ORM into ``date_part()``, so the filters need no stored field and
    nothing to recompute. The assertions run the domain the search view really
    carries rather than a copy of it: a filter that stops matching is the
    failure worth catching, and a restated domain cannot see it.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Partner = cls.env["res.partner"]
        today = datetime.date.today()
        cls.today_born = cls.Partner.create(
            {"name": "Born today", "birthdate": today - relativedelta(years=30)}
        )
        cls.same_month = cls.Partner.create(
            {
                "name": "Born same month",
                "birthdate": (today - relativedelta(years=25)).replace(day=1)
                if today.day != 1
                else (today - relativedelta(years=25)).replace(day=28),
            }
        )
        cls.other_month = cls.Partner.create(
            {
                "name": "Born another month",
                "birthdate": today - relativedelta(years=25, months=5),
            }
        )
        cls.undated = cls.Partner.create({"name": "No birthdate at all"})
        cls.everyone = cls.today_born + cls.same_month + cls.other_month + cls.undated

    def _filter_domain(self, name):
        arch = etree.fromstring(
            self.env.ref("base.view_res_partner_filter").get_combined_arch()
        )
        nodes = arch.xpath(f"//filter[@name='{name}']")
        self.assertTrue(nodes, f"the search view offers no {name} filter")
        return safe_eval(nodes[0].get("domain"), {"context_today": datetime.date.today})

    def _matching(self, name):
        return self.Partner.search(
            [("id", "in", self.everyone.ids)] + self._filter_domain(name)
        )

    def test_birthday_today_finds_only_today(self):
        self.assertEqual(self._matching("birthday_today"), self.today_born)

    def test_birthday_this_month_spans_the_month(self):
        found = self._matching("birthday_this_month")
        self.assertIn(self.today_born, found)
        self.assertIn(self.same_month, found)
        self.assertNotIn(self.other_month, found)
        self.assertNotIn(self.undated, found)

    def test_without_birthdate_finds_the_undated(self):
        self.assertEqual(self._matching("without_birthdate"), self.undated)

    def test_the_month_is_a_group_by(self):
        groups = self.Partner._read_group(
            [("id", "in", (self.today_born + self.other_month).ids)],
            groupby=["birthdate:month_number"],
            aggregates=["__count"],
        )
        self.assertEqual(len(groups), 2, "two birth months grouped into one bucket")

    def test_the_date_parts_are_indexed(self):
        """A filter every contact list offers must not be a sequential scan."""
        self.env.cr.execute(
            "SELECT indexdef FROM pg_indexes "
            "WHERE tablename = 'res_partner' AND indexdef ILIKE %s",
            ("%date_part%birthdate%",),
        )
        self.assertTrue(
            self.env.cr.fetchall(),
            "no index covers date_part(birthdate), so the birthday filters "
            "scan the whole contact table",
        )
