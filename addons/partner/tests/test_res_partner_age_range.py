from unittest.mock import patch

from odoo.exceptions import AccessError, ValidationError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestPartnerAgeRange(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.AgeRange = cls.env["res.partner.age.range"]
        cls.Partner = cls.env["res.partner"]
        cls.AgeRange.search([]).active = False

    def test_01_cohort_bounds_are_validated(self):
        with self.assertRaises(ValidationError):
            self.AgeRange.create(
                {"min_value": 1800, "max_value": 1800, "name": "empty cohort"}
            )
        first = self.AgeRange.create(
            {"min_value": 1800, "max_value": 1806, "name": "cohort A"}
        )
        self.assertEqual(first.min_value, 1800)

        with self.assertRaises(ValidationError):
            self.AgeRange.create({"max_value": 1806, "name": "cohort B"})
        second = self.AgeRange.create({"max_value": 1809, "name": "cohort B"})
        self.assertEqual(
            second.min_value,
            1806,
            "a new cohort must start where the latest existing one ends",
        )

        with self.assertRaises(ValidationError):
            self.AgeRange.create(
                {"min_value": 1807, "max_value": 1810, "name": "cohort C"}
            )
        self.AgeRange.create({"min_value": 1810, "max_value": 1816, "name": "cohort C"})
        with self.assertRaises(ValidationError):
            self.AgeRange.create(
                {"min_value": 1809, "max_value": 1814, "name": "cohort D"}
            )

    def test_02_adjacent_cohorts_do_not_overlap(self):
        self.AgeRange.create({"min_value": 1820, "max_value": 1830, "name": "adj low"})
        self.AgeRange.create({"min_value": 1830, "max_value": 1840, "name": "adj high"})

    def test_03_the_shared_bound_belongs_to_the_later_cohort(self):
        low = self.AgeRange.create(
            {"min_value": 1850, "max_value": 1860, "name": "edge low"}
        )
        high = self.AgeRange.create(
            {"min_value": 1860, "max_value": 1870, "name": "edge high"}
        )
        self.assertFalse(low._is_covering(1860), "the upper bound is exclusive")
        self.assertTrue(high._is_covering(1860), "the lower bound is inclusive")

    def test_04_the_cohort_follows_birth_year_not_current_age(self):
        cohort = self.AgeRange.create(
            {"min_value": 1870, "max_value": 1880, "name": "birth-year cohort"}
        )
        january = self.Partner.create(
            {"name": "Born January", "birthdate": "1875-01-01"}
        )
        december = self.Partner.create(
            {"name": "Born December", "birthdate": "1875-12-31"}
        )

        self.assertEqual(january.age_range_id, cohort)
        self.assertEqual(
            december.age_range_id,
            january.age_range_id,
            "two partners born in the same year landed in different cohorts, "
            "so the band is keyed on current age again and will drift every "
            "time one of them has a birthday",
        )

    def test_05_a_partner_without_a_birthdate_carries_no_cohort(self):
        self.AgeRange.create(
            {"min_value": 1890, "max_value": 1900, "name": "unused cohort"}
        )
        partner = self.Partner.create({"name": "No Birthdate Co", "is_company": True})
        self.assertFalse(
            partner.age_range_id,
            "a cohort was assigned with nothing to derive it from",
        )

    def test_06_rebounding_a_cohort_reclassifies_its_partners(self):
        cohort = self.AgeRange.create(
            {"min_value": 1910, "max_value": 1920, "name": "rebound me"}
        )
        partner = self.Partner.create({"name": "Born 1915", "birthdate": "1915-06-01"})
        self.assertEqual(partner.age_range_id, cohort)

        cohort.min_value = 1916
        self.env.flush_all()
        self.assertFalse(
            partner.age_range_id,
            "the cohort no longer covers 1915, but the partner still carries it: "
            "editing the scale left every stored classification stale",
        )

        cohort.min_value = 1910
        self.env.flush_all()
        self.assertEqual(partner.age_range_id, cohort)

    def test_07_archiving_and_deleting_a_cohort_releases_its_partners(self):
        cohort = self.AgeRange.create(
            {"min_value": 1930, "max_value": 1940, "name": "archive me"}
        )
        partner = self.Partner.create({"name": "Born 1935", "birthdate": "1935-06-01"})
        self.assertEqual(partner.age_range_id, cohort)

        cohort.active = False
        self.env.flush_all()
        self.assertFalse(partner.age_range_id, "an archived cohort still classifies")

        cohort.active = True
        self.env.flush_all()
        self.assertEqual(partner.age_range_id, cohort)

        cohort.unlink()
        self.env.flush_all()
        self.assertFalse(partner.age_range_id, "a deleted cohort still classifies")

    def test_08_renaming_a_cohort_does_not_reclassify(self):
        cohort = self.AgeRange.create(
            {"min_value": 1940, "max_value": 1946, "name": "rename me"}
        )
        partner = self.Partner.create({"name": "Born 1942", "birthdate": "1942-06-01"})
        self.assertEqual(partner.age_range_id, cohort)

        cohort.name = "renamed"
        self.env.flush_all()
        self.assertEqual(partner.age_range_id, cohort)

    def test_09_an_open_ended_cohort_still_reclassifies(self):
        cohort = self.AgeRange.create(
            {"min_value": 2200, "max_value": 0, "name": "open ended"}
        )
        partner = self.Partner.create({"name": "Born 2400", "birthdate": "2400-06-01"})
        self.assertEqual(partner.age_range_id, cohort)

        cohort.min_value = 2500
        self.env.flush_all()
        self.assertFalse(
            partner.age_range_id,
            "max_value 0 means unbounded, so the sweep must reach a birth year "
            "with no upper bound above it",
        )

    def test_10_a_cohort_open_on_its_lower_side_still_reclassifies(self):
        cohort = self.AgeRange.create(
            {"min_value": 0, "max_value": 1600, "name": "open below"}
        )
        partner = self.Partner.create({"name": "Born 1500", "birthdate": "1500-06-01"})
        self.assertEqual(partner.age_range_id, cohort)

        cohort.max_value = 1450
        self.env.flush_all()
        self.assertFalse(
            partner.age_range_id,
            "min_value 0 is no lower bound at all -- year 0 is not a date, and "
            "treating it as one would drop the whole span from the sweep",
        )

    def test_11_a_drifted_partner_is_repaired_by_touching_its_own_band(self):
        cohort = self.AgeRange.create(
            {"min_value": 1700, "max_value": 1710, "name": "drift home"}
        )
        stranger = self.Partner.create(
            {"name": "Born 1850 elsewhere", "birthdate": "1850-06-01"}
        )
        self.env.flush_all()
        self.env.cr.execute(
            "UPDATE res_partner SET age_range_id = %s WHERE id = %s",
            (cohort.id, stranger.id),
        )
        self.env.invalidate_all()
        self.assertEqual(stranger.age_range_id, cohort, "fixture did not take")

        cohort.max_value = 1711
        self.env.flush_all()
        self.assertFalse(
            stranger.age_range_id,
            "a partner pointing at the edited band must be swept even though "
            "its birth year lies outside every bound the write moved",
        )

    def test_12_an_untouched_span_is_not_swept(self):
        near = self.AgeRange.create(
            {"min_value": 1750, "max_value": 1760, "name": "near"}
        )
        far = self.AgeRange.create(
            {"min_value": 1770, "max_value": 1780, "name": "far"}
        )
        stranger = self.Partner.create({"name": "Born 1775", "birthdate": "1775-06-01"})
        self.assertEqual(stranger.age_range_id, far)

        self.env.flush_all()
        self.env.cr.execute(
            "UPDATE res_partner SET age_range_id = NULL WHERE id = %s", (stranger.id,)
        )
        self.env.invalidate_all()

        near.max_value = 1761
        self.env.flush_all()
        self.assertFalse(
            stranger.age_range_id,
            "editing a band 15 years away re-derived a partner it cannot "
            "reclassify, so the sweep is no longer narrowed",
        )

        far.max_value = 1781
        self.env.flush_all()
        self.assertEqual(far, stranger.age_range_id, "its own band must repair it")

    def test_13_an_archived_partner_is_reclassified_like_any_other(self):
        cohort = self.AgeRange.create(
            {"min_value": 1960, "max_value": 1970, "name": "archived member"}
        )
        partner = self.Partner.create({"name": "Born 1965", "birthdate": "1965-06-01"})
        self.assertEqual(partner.age_range_id, cohort)

        partner.active = False
        cohort.min_value = 1966
        self.env.flush_all()
        partner.invalidate_recordset(["age_range_id"])
        self.assertFalse(
            partner.age_range_id,
            "the sweep searched res.partner with the default active_test, so an "
            "archived partner kept a cohort whose bounds no longer reach it",
        )

        cohort.min_value = 1960
        self.env.flush_all()
        partner.invalidate_recordset(["age_range_id"])
        self.assertEqual(
            partner.age_range_id, cohort, "an archived partner must also be re-covered"
        )

    def test_14_a_new_cohort_chains_onto_the_highest_closed_bound(self):
        self.assertEqual(
            self.AgeRange.default_get(["min_value"])["min_value"],
            0.0,
            "with no cohorts at all there is nothing to chain onto",
        )
        self.AgeRange.create({"min_value": 1500, "max_value": 1600, "name": "closed"})
        self.assertEqual(self.AgeRange.default_get(["min_value"])["min_value"], 1600)

        self.AgeRange.create({"min_value": 1600, "max_value": 0, "name": "open top"})
        self.assertEqual(
            self.AgeRange.default_get(["min_value"])["min_value"],
            1600,
            "the open cohort's max_value of 0 means no upper limit; chaining "
            "onto it would propose 0 as a LOWER bound, which means the opposite",
        )

    def test_15_a_cohort_name_is_unique_regardless_of_casing(self):
        """UNIQUE(name) let "Baby boomer" and "baby boomer" both exist.

        The rule is a unique index over lower(name) rather than a constraint,
        which is a conversion the framework refused to perform until
        2c60f5f3d33: it left the old constraint in force and the database
        unupgradable afterwards.
        """
        self.AgeRange.create({"min_value": 1400, "max_value": 1410, "name": "Casing"})
        with self.assertRaises(Exception):
            with self.env.cr.savepoint():
                self.AgeRange.create(
                    {"min_value": 1410, "max_value": 1420, "name": "casing"}
                )

    def test_16_an_overlap_inside_one_batch_is_still_rejected(self):
        """The scale is searched once for the batch, so the batch's own members
        have to be compared in memory or two overlapping cohorts created
        together would both pass."""
        with self.assertRaises(ValidationError):
            self.AgeRange.create(
                [
                    {"name": "batch a", "min_value": 1200, "max_value": 1210},
                    {"name": "batch b", "min_value": 1205, "max_value": 1215},
                ]
            )

    def test_17_checking_a_scale_does_not_cost_a_query_per_band(self):
        """`_check_band` ran one sibling search per record, from a constraint.

        The assertion is on scaling rather than on a number: what matters is
        that a wider batch does not buy more queries, and an exact count would
        pin every incidental search the create path happens to make today.
        """
        AgeRange = type(self.AgeRange)
        original = AgeRange.search
        counted = []

        def counting_search(records, domain, *args, **kwargs):
            counted.append(domain)
            return original(records, domain, *args, **kwargs)

        def searches_for(count, first_year):
            counted.clear()
            with patch.object(AgeRange, "search", counting_search):
                self.AgeRange.create(
                    [
                        {
                            "name": f"scale {first_year} {index}",
                            "min_value": first_year + index * 10,
                            "max_value": first_year + index * 10 + 10,
                        }
                        for index in range(count)
                    ]
                )
                self.env.flush_all()
            return len(counted)

        few = searches_for(3, 2600)
        many = searches_for(12, 2700)

        self.assertEqual(
            few,
            many,
            f"{few} searches for 3 bands and {many} for 12: the sibling lookup "
            "still scales with the size of the batch",
        )


@tagged("post_install", "-at_install")
class TestPartnerAgeRangeScale(TransactionCase):
    """What the configuration screen has to be able to answer.

    A scale is not only a set of bands: it is a claim to classify every
    contact. The bands enforce that they do not overlap, and nothing enforced
    -- or even showed -- that together they leave no year uncovered, or that a
    band was reaching anyone at all.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.AgeRange = cls.env["res.partner.age.range"]
        cls.Partner = cls.env["res.partner"]
        cls.AgeRange.search([]).active = False

    def test_the_display_name_names_the_years_the_cohort_contains(self):
        """The bounds are half-open, which is the module's oldest trap.

        ``max_value`` is the first year *after* the cohort, so the last year it
        contains is one less. A name that repeats the stored bound would teach
        the mistake instead of settling it.
        """
        closed = self.AgeRange.create(
            {"name": "Closed", "min_value": 1965, "max_value": 1981}
        )
        self.assertEqual(closed.display_name, "Closed (1965-1980)")

        open_top = self.AgeRange.create(
            {"name": "Open top", "min_value": 2010, "max_value": 0}
        )
        self.assertEqual(open_top.display_name, "Open top (2010 and later)")

        open_bottom = self.AgeRange.create(
            {"name": "Open bottom", "min_value": 0, "max_value": 1900}
        )
        self.assertEqual(open_bottom.display_name, "Open bottom (up to 1899)")

    def test_a_cohort_counts_the_contacts_it_holds(self):
        cohort = self.AgeRange.create(
            {"name": "Counted", "min_value": 1300, "max_value": 1310}
        )
        empty = self.AgeRange.create(
            {"name": "Uncounted", "min_value": 1310, "max_value": 1320}
        )
        self.Partner.create(
            [
                {"name": "Born 1302", "birthdate": "1302-04-04"},
                {"name": "Born 1305", "birthdate": "1305-04-04"},
            ]
        )
        self.env.flush_all()
        cohort.invalidate_recordset(["partner_count"])

        self.assertEqual(cohort.partner_count, 2)
        self.assertEqual(empty.partner_count, 0)

    def test_a_gap_in_the_scale_is_reported(self):
        """A contact born in a gap classifies into nothing, silently.

        ``mixin.band`` rejects overlaps and says nothing about the space
        between two bands, so a scale can look finished while dropping a decade.
        """
        self.AgeRange.create({"name": "Low", "min_value": 1000, "max_value": 1010})
        high = self.AgeRange.create(
            {"name": "High", "min_value": 1020, "max_value": 1030}
        )
        stranded = self.Partner.create(
            {"name": "Born in the gap", "birthdate": "1015-06-01"}
        )

        self.assertFalse(stranded.age_range_id, "the gap is real")
        self.assertEqual(high.gap_before, "1010-1019")

    def test_adjacent_cohorts_report_no_gap(self):
        self.AgeRange.create({"name": "First", "min_value": 1100, "max_value": 1110})
        second = self.AgeRange.create(
            {"name": "Second", "min_value": 1110, "max_value": 1120}
        )

        self.assertFalse(second.gap_before)

    def test_the_oldest_cohort_is_not_a_gap(self):
        """Nothing below the oldest band is intended, not uncovered."""
        oldest = self.AgeRange.create(
            {"name": "Oldest", "min_value": 1200, "max_value": 1210}
        )

        self.assertFalse(oldest.gap_before)

    def test_an_empty_cohort_still_appears_in_the_group_by(self):
        """The group-by is where a distribution is read, so a hole in it reads
        as "nobody was born then" rather than as an unused band."""
        used = self.AgeRange.create(
            {"name": "Used", "min_value": 1400, "max_value": 1410}
        )
        unused = self.AgeRange.create(
            {"name": "Unused", "min_value": 1410, "max_value": 1420}
        )
        self.Partner.create({"name": "Born 1405", "birthdate": "1405-02-02"})
        self.env.flush_all()

        # web_read_group, not formatted_read_group: group_expand is gated on
        # the read_group_expand context key that web/model/relational_model
        # sets on every grouped view, so only the client's own entry point
        # exercises it.
        grouped = self.Partner.with_context(read_group_expand=True).web_read_group(
            [], ["age_range_id"], ["__count"]
        )
        offered = {
            group["age_range_id"] and group["age_range_id"][0]
            for group in grouped["groups"]
        }

        self.assertIn(used.id, offered)
        self.assertIn(unused.id, offered, "an empty cohort vanished from the group-by")

    def test_a_cohort_opens_the_contacts_it_classified(self):
        cohort = self.AgeRange.create(
            {"name": "Openable", "min_value": 1500, "max_value": 1510}
        )
        partner = self.Partner.create({"name": "Born 1505", "birthdate": "1505-01-01"})
        self.env.flush_all()

        action = cohort.action_open_partners()
        found = self.Partner.search(action["domain"])

        self.assertEqual(action["res_model"], "res.partner")
        self.assertIn(partner, found)

    def test_an_unnamed_cohort_does_not_render_its_missing_name(self):
        """`display_name` is read before the name is typed.

        The form defaults the bounds, so a brand-new record already has a span
        to render and would otherwise show it beside the string "False".
        """
        draft = self.AgeRange.new({"min_value": 1600, "max_value": 0})

        self.assertFalse(draft.display_name)

    def test_closing_a_gap_from_the_neighbour_clears_it(self):
        """`gap_before` reads the whole scale, which no @api.depends can say.

        Moving the band *below* leaves the reported gap untouched unless the
        cache is dropped where the scale changes, so a cohort goes on reporting
        years the edit just covered.
        """
        below = self.AgeRange.create(
            {"name": "below", "min_value": 1000, "max_value": 1010}
        )
        above = self.AgeRange.create(
            {"name": "above", "min_value": 1020, "max_value": 1030}
        )
        self.assertEqual(above.gap_before, "1010-1019")

        below.max_value = 1020
        self.env.flush_all()

        self.assertFalse(
            above.gap_before,
            "the band below now reaches this one, but the gap is still reported",
        )

    def test_archiving_a_middle_band_opens_a_gap_above_it(self):
        """An archived band classifies nobody, so it covers nothing either.

        Three bands, not two: archiving the *lowest* one only moves the open
        lower edge of the scale, which is intended and no gap at all. It takes
        a band with something still below it to leave a hole behind.
        """
        self.AgeRange.create({"name": "arch low", "min_value": 1030, "max_value": 1040})
        middle = self.AgeRange.create(
            {"name": "arch middle", "min_value": 1040, "max_value": 1050}
        )
        top = self.AgeRange.create(
            {"name": "arch top", "min_value": 1050, "max_value": 1060}
        )
        self.assertFalse(top.gap_before)

        middle.active = False
        self.env.flush_all()

        self.assertEqual(top.gap_before, "1040-1049")

    def test_archiving_the_lowest_band_is_not_a_gap(self):
        """It becomes the scale's open lower edge, which the oldest band owns."""
        lowest = self.AgeRange.create(
            {"name": "edge low", "min_value": 1070, "max_value": 1080}
        )
        above = self.AgeRange.create(
            {"name": "edge above", "min_value": 1080, "max_value": 1090}
        )

        lowest.active = False
        self.env.flush_all()

        self.assertFalse(above.gap_before)

    def test_the_contact_count_follows_a_reclassification(self):
        cohort = self.AgeRange.create(
            {"name": "counted live", "min_value": 1100, "max_value": 1110}
        )
        self.Partner.create({"name": "In 1105", "birthdate": "1105-01-01"})
        self.env.flush_all()
        self.assertEqual(cohort.partner_count, 1)

        cohort.min_value = 1106
        self.env.flush_all()

        self.assertEqual(
            cohort.partner_count, 0, "the count survived the reclassification"
        )


@tagged("post_install", "-at_install")
class TestPartnerAgeRangeClassificationRights(TransactionCase):
    """Classifying a contact must not need the writer to see the cohorts.

    ``age_range_id`` is a stored compute, so it runs as whoever wrote the
    contact. The cohorts are reference data whose ACL admits internal users
    only, which couples the right to save a contact to the right to read a
    configuration model the user never asked about. The sibling sweep in
    ``_add_partners_to_compute`` already spells ``sudo()`` for the same reason.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.AgeRange = cls.env["res.partner.age.range"]
        cls.AgeRange.search([]).active = False
        cls.cohort = cls.AgeRange.create(
            {"name": "Reachable by anyone", "min_value": 1970, "max_value": 1980}
        )
        cls.env["ir.access"].create(
            {
                "name": "res.partner portal write (test fixture)",
                "model_id": cls.env["ir.model"]._get_id("res.partner"),
                "group_id": cls.env.ref("base.group_portal").id,
                "kind": "permission",
                "operation": "cru",
            }
        )
        cls.env.registry.clear_cache()
        cls.outsider = cls.env["res.users"].create(
            {
                "name": "Outsider",
                "login": "age_range_outsider",
                "group_ids": [(6, 0, [cls.env.ref("base.group_portal").id])],
            }
        )

    def test_the_writer_cannot_read_the_cohorts(self):
        """The fixture is only meaningful while this holds."""
        with self.assertRaises(AccessError):
            self.AgeRange.with_user(self.outsider).search([])

    def test_a_contact_is_classified_anyway(self):
        partner = self.env["res.partner"].create({"name": "Written by an outsider"})
        self.env.flush_all()

        partner.with_user(self.outsider).write({"birthdate": "1975-03-03"})
        self.env.flush_all()

        self.assertEqual(partner.age_range_id, self.cohort)
