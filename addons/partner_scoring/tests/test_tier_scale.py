from unittest.mock import patch

from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install", "partner_scoring")
class TestTierScale(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Profile = cls.env["partner.tier"]
        cls.Partner = cls.env["res.partner"]
        cls.Profile.search([]).write({"active": False})
        cls.company_a = cls.env.company
        cls.company_b = cls.env["res.company"].create({"name": "Scale Company B"})

    def _band(self, name, low, high, company, sequence=10):
        return self.Profile.create(
            {
                "name": name,
                "sequence": sequence,
                "min_value": low,
                "max_value": high,
                "company_id": company.id if company else False,
            }
        )

    def test_a_partner_is_not_classified_into_another_companys_band(self):
        band_b = self._band("B all", 0.0, 0.0, self.company_b, sequence=1)
        band_a = self._band("A all", 0.0, 0.0, self.company_a, sequence=5)

        partner = self.Partner.create(
            {
                "name": "Scale Probe A",
                "is_company": True,
                "company_id": self.company_a.id,
            }
        )
        self.assertEqual(partner.tier_id, band_a)
        self.assertNotEqual(partner.tier_id, band_b)

    def test_a_shared_band_classifies_every_company(self):
        shared = self._band("Shared all", 0.0, 0.0, None)
        partner = self.Partner.create(
            {
                "name": "Scale Probe Shared",
                "is_company": True,
                "company_id": self.company_b.id,
            }
        )
        self.assertEqual(partner.tier_id, shared)

    def test_a_shared_band_still_cannot_overlap_a_company_band(self):
        self._band("A all", 0.0, 0.0, self.company_a)
        with self.assertRaises(ValidationError):
            self._band("Shared overlapping", 0.0, 0.0, None)

    def test_a_top_band_ending_at_100_is_rejected(self):
        self._band("Low", 0.0, 50.0, self.company_a)
        with self.assertRaises(ValidationError):
            self._band("High closed", 50.0, 100.0, self.company_a)

    def test_a_perfect_score_classifies_with_an_open_top_band(self):
        self._band("Low", 0.0, 50.0, self.company_a)
        top = self._band("High open", 50.0, 0.0, self.company_a)
        self.assertTrue(top._is_covering(100.0))

    def test_a_scale_may_be_built_top_band_first(self):
        top = self._band("High", 50.0, 0.0, self.company_a)
        bottom = self._band("Low", 0.0, 50.0, self.company_a)
        self.assertTrue(bottom._is_covering(0.0))
        self.assertTrue(top._is_covering(100.0))

    def test_a_company_less_partner_ignores_every_company_band(self):
        """The stored classification must not follow the acting user."""
        self._band("A all", 0.0, 0.0, self.company_a, sequence=1)
        partner = self.Partner.create(
            {"name": "Scale Probe Nobody", "is_company": True, "company_id": False}
        )
        self.assertFalse(partner.tier_id)

    def test_a_company_less_partner_classifies_on_a_shared_band(self):
        shared = self._band("Shared all", 0.0, 0.0, None, sequence=1)
        partner = self.Partner.create(
            {"name": "Scale Probe Shared Only", "is_company": True, "company_id": False}
        )
        self.assertEqual(partner.tier_id, shared)

    def test_the_scale_of_a_company_less_partner_is_stable(self):
        """Same partner, two acting companies, one answer."""
        self._band("A all", 0.0, 0.0, self.company_a, sequence=1)
        self._band("B all", 0.0, 0.0, self.company_b, sequence=2)
        partner = self.Partner.create(
            {"name": "Scale Probe Stable", "is_company": True, "company_id": False}
        )
        as_a = partner.tier_id
        partner.with_company(self.company_b)._compute_tier_id()
        self.assertEqual(partner.tier_id, as_a)

    def test_a_band_starting_above_100_is_rejected(self):
        """A band no percentage can reach is a dead row, not a valid scale."""
        with self.assertRaises(ValidationError):
            self._band("Unreachable", 150.0, 0.0, self.company_a)

    def test_a_scale_edit_queues_a_reclassification(self):
        """Nothing depends on partner.tier, so the band must push."""
        band = self._band("Notify band", 0.0, 0.0, self.company_a)
        partner_class = type(self.Partner)
        with patch.object(partner_class, "_notify_tier_scale_changed") as notified:
            band.min_value = 5.0
            self.assertTrue(notified.called)

            notified.reset_mock()
            band.factor = 1.5
            self.assertFalse(notified.called)

            notified.reset_mock()
            band.action_archive()
            self.assertTrue(notified.called)

    def test_a_new_band_reaches_a_partner_nobody_had_classified(self):
        """A partner with no rows and no band is who a band covering 0 is for."""
        partner = self.Partner.create(
            {"name": "Scale Probe Orphan", "is_company": True, "company_id": False}
        )
        self.assertFalse(partner.tier_id)
        self.assertFalse(partner.score_line_ids)

        self._band("Late whole scale", 0.0, 0.0, None)
        queued = self.env["ir.job"].search(
            [("identity_key", "=like", "partner_scoring.reclassify:%")]
        )
        reached = {partner_id for job in queued for partner_id in job.record_ids}
        self.assertIn(partner.id, reached)

    def test_the_reclassification_follows_the_edited_scale(self):
        low = self._band("Move Low", 0.0, 50.0, None, sequence=1)
        self._band("Move High", 50.0, 0.0, None, sequence=2)
        partner = self.Partner.create(
            {"name": "Scale Probe Mover", "is_company": True, "company_id": False}
        )
        self.assertEqual(partner.tier_id, low)

        low.action_archive()
        partner._reclassify_tiers()
        self.assertFalse(partner.tier_id)

        low.action_unarchive()
        partner._reclassify_tiers()
        self.assertEqual(partner.tier_id, low)

        low.min_value = 10.0
        partner._reclassify_tiers()
        self.assertFalse(partner.tier_id)

    def test_the_display_name_placeholder_survives_an_unsaved_record(self):
        """_rec_name is the ORM default; the compute is not, so it stays."""
        self.assertEqual(self.Profile._rec_name, "name")
        saved = self._band("Named band", 0.0, 0.0, self.company_a)
        self.assertEqual(saved.display_name, "Named band")
        self.assertEqual(self.Profile.new({}).display_name, "New Tier")

    def test_a_foreign_company_profile_cannot_be_stored(self):
        """The classification is computed; a hand-written band does not stick."""
        band_b = self._band("Guard B", 0.0, 0.0, self.company_b)
        partner = self.Partner.create(
            {
                "name": "Scale Probe Guarded",
                "is_company": True,
                "company_id": self.company_a.id,
            }
        )
        partner.tier_id = band_b
        self.env.flush_all()
        self.assertFalse(partner.tier_id)
        self.env.cr.execute(
            "SELECT tier_id FROM res_partner WHERE id = %s", (partner.id,)
        )
        self.assertIsNone(self.env.cr.fetchone()[0])

    def test_a_company_less_contact_may_carry_a_scoped_parents_band(self):
        band_a = self._band("Guard A", 0.0, 0.0, self.company_a)
        company = self.Partner.create(
            {
                "name": "Scale Guard Parent",
                "is_company": True,
                "company_id": self.company_a.id,
            }
        )
        self.assertEqual(company.tier_id, band_a)
        contact = self.Partner.create(
            {
                "name": "Scale Guard Contact",
                "parent_id": company.id,
                "company_id": False,
            }
        )
        self.assertEqual(contact.tier_id, band_a)

    def test_a_shared_profile_is_accepted_by_the_guard(self):
        shared = self._band("Guard shared", 0.0, 0.0, None)
        partner = self.Partner.create(
            {
                "name": "Scale Probe Guarded Shared",
                "is_company": True,
                "company_id": self.company_a.id,
            }
        )
        partner.tier_id = shared
        self.assertEqual(partner.tier_id, shared)


@tagged("post_install", "-at_install", "partner_scoring")
class TestAScaleClassifiesItsPartners(TransactionCase):
    """A scale nobody can be measured against is the failure mode that hides.

    Odoo partners carry no company unless someone sets one -- 4,233 of the 4,245
    in the production dump this was measured against, 746 of them customers --
    while every band created through the UI used to default into the acting
    user's company. The two can never meet, so a complete, gapless, correct
    scale classified nobody and every downstream factor silently read 1.0.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Profile = cls.env["partner.tier"]
        cls.Partner = cls.env["res.partner"]
        cls.Profile.search([]).write({"active": False})

    def test_a_band_is_company_less_unless_someone_scopes_it(self):
        band = self.Profile.create({"name": "Unscoped", "min_value": 0.0})
        self.assertFalse(
            band.company_id,
            "a commercial scale applies to every partner unless it is "
            "deliberately narrowed; defaulting it into a company scopes a "
            "classification nobody asked to scope",
        )

    def test_a_company_less_partner_is_classified_by_a_company_less_scale(self):
        self.Profile.create(
            {"name": "Whole scale", "sequence": -1000, "min_value": 0.0, "factor": 1.5}
        )
        partner = self.Partner.create({"name": "No company"})

        self.assertFalse(partner.company_id)
        self.assertEqual(partner.tier_id.name, "Whole scale")
        self.assertEqual(partner.factor, 1.5)

    def test_a_scoped_scale_still_leaves_a_company_less_partner_alone(self):
        self.Profile.create(
            {
                "name": "Company scale",
                "sequence": -1000,
                "min_value": 0.0,
                "company_id": self.env.company.id,
            }
        )
        partner = self.Partner.create({"name": "No company either"})

        self.assertFalse(
            partner.tier_id,
            "a deliberately scoped scale measures that company's partners and "
            "no one else -- that part was always right, and is what made the "
            "accidental scoping invisible",
        )
