from unittest.mock import patch

import psycopg

from odoo.fields import Command
from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger


@tagged("post_install", "-at_install", "partner_scoring")
class TestPartnerScoringEngine(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Partner = cls.env["res.partner"]
        cls.Attribute = cls.env["res.partner.attribute"]
        cls.Value = cls.env["res.partner.attribute.value"]
        cls.Profile = cls.env["partner.tier"]

        cls.Profile.search([]).write({"active": False})
        cls.Value.search([("score_value", ">", 0)]).write({"score_value": 0.0})

        cls.multi = cls.Attribute.create(
            {
                "name": "Engine Multi",
                "value_type": "multi",
                "aggregation_mode": "sum",
            }
        )
        cls.multi_a = cls.Value.create(
            {"name": "A", "attribute_id": cls.multi.id, "score_value": 8.0}
        )
        cls.multi_b = cls.Value.create(
            {"name": "B", "attribute_id": cls.multi.id, "score_value": 12.0}
        )
        cls.single = cls.Attribute.create(
            {
                "name": "Engine Best-Of",
                "value_type": "multi",
                "aggregation_mode": "max",
            }
        )
        cls.single_low = cls.Value.create(
            {"name": "Low", "attribute_id": cls.single.id, "score_value": 4.0}
        )
        cls.single_high = cls.Value.create(
            {"name": "High", "attribute_id": cls.single.id, "score_value": 10.0}
        )
        cls.own_ceiling = 30.0
        cls.denominator = cls.Partner._get_score_max_points()

        # Shared bands: these tests are about the scoring engine, not about
        # company scoping, and the partner below carries no company.
        cls.profile_low = cls.Profile.create(
            {
                "name": "Engine Low",
                "sequence": 1,
                "min_value": 0.0,
                "max_value": 50.0,
                "company_id": False,
            }
        )
        cls.profile_high = cls.Profile.create(
            {
                "name": "Engine High",
                "sequence": 2,
                "min_value": 50.0,
                "max_value": 0.0,
                "company_id": False,
            }
        )
        cls.partner = cls.Partner.create({"name": "Engine Partner", "is_company": True})

    def _set(self, attribute, values):
        self.partner.attribute_line_ids.filtered(
            lambda line, attribute=attribute: line.attribute_id == attribute
        ).unlink()
        self.env["res.partner.attribute.line"].create(
            {
                "partner_id": self.partner.id,
                "attribute_id": attribute.id,
                "value_ids": [Command.set(values.ids)],
            }
        )

    def test_the_engine_carries_its_own_dimension(self):
        self.assertIn("partner_attr", self.Partner._get_score_dimensions())
        ceiling = self.Partner._score_ceiling_partner_attr()
        self.assertEqual(ceiling["model"], "res.partner.attribute")

    def test_ceiling_is_the_sum_of_each_attributes_reachable_best(self):
        ceiling = self.Partner._score_ceiling_partner_attr()
        by_attribute = dict(ceiling["attributes"])
        self.assertEqual(by_attribute[self.multi.id], 20.0)
        self.assertEqual(by_attribute[self.single.id], 10.0)
        self.assertEqual(ceiling["total"], self.own_ceiling)

    def test_sum_mode_adds_every_selected_value(self):
        self._set(self.multi, self.multi_a | self.multi_b)
        self.assertEqual(self.partner.score_points, 20.0)
        self.assertEqual(self.partner.score_max_points, self.denominator)
        self.assertAlmostEqual(self.partner.score, 20.0 / self.denominator * 100.0)

    def test_max_mode_discards_all_but_the_best(self):
        self._set(self.single, self.single_low | self.single_high)
        self.assertEqual(self.partner.score_points, 10.0)
        discarded = self.partner.score_line_ids.filtered(lambda row: not row.applied)
        self.assertEqual(discarded.points, 4.0)
        self.assertTrue(discarded.note)

    def test_missing_data_scores_zero_but_is_audited(self):
        self._set(self.multi, self.multi_a)
        rows_by_key = {row.source_key: row for row in self.partner.score_line_ids}
        empty = rows_by_key[f"partner_attr:{self.single.id}:none"]
        self.assertEqual(empty.points, 0.0)
        self.assertEqual(empty.max_points, 10.0)
        self.assertTrue(empty.note)

    def test_percentage_selects_the_profile_band(self):
        self._set(self.multi, self.multi_a)
        self.assertLess(self.partner.score, 50.0)
        self.assertEqual(self.partner.tier_id, self.profile_low)

        self._set(self.multi, self.multi_a | self.multi_b)
        self._set(self.single, self.single_high)
        expected_pct = self.own_ceiling / self.denominator * 100.0
        self.assertAlmostEqual(self.partner.score, expected_pct)
        expected_profile = (
            self.profile_high if expected_pct >= 50.0 else self.profile_low
        )
        self.assertEqual(self.partner.tier_id, expected_profile)
        self.assertEqual(self.partner.factor, expected_profile.factor)

    def test_a_weight_edit_cascades_to_the_holders(self):
        self._set(self.multi, self.multi_a)
        self.assertEqual(self.partner.score_points, 8.0)

        self.multi_a.score_value = 16.0
        self.partner._update_scores()
        self.assertEqual(self.partner.score_points, 16.0)
        self.assertEqual(
            self.Partner._score_ceiling_partner_attr()["total"],
            self.own_ceiling + 8.0,
        )

    def test_the_audit_rows_reconcile_rather_than_churn(self):
        self._set(self.multi, self.multi_a)
        before = {row.id: row.source_key for row in self.partner.score_line_ids}
        self.partner._update_scores()
        after = {row.id: row.source_key for row in self.partner.score_line_ids}
        self.assertEqual(before, after)

    def _flush_tracking(self):
        self.env.flush_all()
        self.cr.flush()

    def test_a_profile_move_is_recorded_in_the_chatter(self):
        self._set(self.multi, self.multi_a)
        self._flush_tracking()
        low = self.partner.tier_id
        self.assertEqual(low, self.profile_low)

        self._set(self.single, self.single_high)
        self._set(self.multi, self.multi_a | self.multi_b)
        self._flush_tracking()
        high = self.partner.tier_id
        self.assertEqual(
            high,
            self.profile_high,
            "the fixture no longer moves the partner across a band boundary, "
            "so this test can no longer observe a tracked transition",
        )

        field = self.env["ir.model.fields"]._get("res.partner", "tier_id")
        tracked = (
            self.env["mail.tracking.value"]
            .sudo()
            .search(
                [
                    ("mail_message_id.model", "=", "res.partner"),
                    ("mail_message_id.res_id", "=", self.partner.id),
                    ("field_id", "=", field.id),
                ]
            )
        )
        self.assertTrue(
            tracked,
            "moving between commercial profiles left no chatter entry -- the "
            "band history partner_scoring is supposed to keep is not being kept",
        )
        self.assertIn(
            high.id,
            tracked.mapped("new_value_integer"),
            "the tracked transition does not name the profile the partner "
            "actually landed in",
        )

    def test_the_score_percentage_is_not_tracked(self):
        self._set(self.multi, self.multi_a)
        self._flush_tracking()
        self._set(self.multi, self.multi_a | self.multi_b)
        self._flush_tracking()

        field = self.env["ir.model.fields"]._get("res.partner", "score")
        self.assertFalse(
            self.env["mail.tracking.value"]
            .sudo()
            .search_count(
                [
                    ("mail_message_id.model", "=", "res.partner"),
                    ("mail_message_id.res_id", "=", self.partner.id),
                    ("field_id", "=", field.id),
                ]
            ),
            "score moves on every capture and every catalog edit; tracking "
            "it would bury the profile transitions in noise",
        )

    def test_the_percentage_is_capped_when_the_ceiling_lags(self):
        """A denominator behind the catalog must cap, not overshoot the scale."""
        self._set(self.multi, self.multi_a | self.multi_b)
        self.assertGreater(self.partner.score_points, 1.0)
        with patch.object(
            type(self.Partner), "_get_score_max_points", return_value=1.0
        ):
            self.partner._compute_score()
        self.assertEqual(self.partner.score, 100.0)

    def test_a_single_partner_is_recomputed_inline(self):
        partner_class = type(self.Partner)
        with patch.object(partner_class, "_delay_scores_recompute") as queued:
            result = self.partner.action_partner_score_recompute()
        self.assertFalse(queued.called)
        self.assertFalse(result)

    def test_a_selection_is_handed_to_the_queue(self):
        other = self.Partner.create({"name": "Engine Second", "is_company": True})
        selection = self.partner | other
        partner_class = type(self.Partner)
        with (
            patch.object(partner_class, "_update_scores") as inline,
            patch.object(partner_class, "_delay_scores_recompute") as queued,
        ):
            result = selection.action_partner_score_recompute()
        self.assertTrue(queued.called)
        self.assertFalse(inline.called)
        self.assertEqual(result["tag"], "display_notification")

    def test_a_contact_carries_its_commercial_entitys_profile(self):
        self._set(self.multi, self.multi_a | self.multi_b)
        self._set(self.single, self.single_high)
        self.assertEqual(self.partner.tier_id, self.profile_high)
        contact = self.Partner.create(
            {"name": "Engine Contact", "parent_id": self.partner.id, "type": "contact"}
        )
        self.assertEqual(contact.score, 0.0)
        self.assertEqual(contact.tier_id, self.profile_high)
        self.assertEqual(contact.factor, self.profile_high.factor)

        self._set(self.multi, self.multi_a)
        self._set(self.single, self.single_low)
        self.assertEqual(self.partner.tier_id, self.profile_low)
        self.assertEqual(contact.tier_id, self.profile_low)

    def test_the_breakdown_labels_follow_the_reader_and_the_catalog(self):
        self._set(self.single, self.single_low | self.single_high)
        rows = {row.source_key: row for row in self.partner.score_line_ids}
        high = rows[f"partner_attr:{self.single.id}:{self.single_high.id}"]
        self.assertEqual(high.source_ref, "Engine Best-Of: High")
        self.assertEqual(high.note, "")
        low = rows[f"partner_attr:{self.single.id}:{self.single_low.id}"]
        self.assertFalse(low.applied)
        self.assertTrue(low.note)
        empty = rows[f"partner_attr:{self.multi.id}:none"]
        self.assertEqual(empty.source_ref, "Engine Multi")
        self.assertTrue(empty.note)

        self.single_high.name = "Highest"
        self.assertEqual(high.source_ref, "Engine Best-Of: Highest")
        self.single_high.action_archive()
        self.assertEqual(high.source_ref, "Engine Best-Of: Highest")

    def test_a_negative_weight_is_rejected(self):
        with (
            self.assertRaises(psycopg.IntegrityError),
            mute_logger("odoo.db.cursor"),
            self.cr.savepoint(),
        ):
            self.multi_a.score_value = -1.0
            self.env.flush_all()

    def test_the_row_count_tracks_the_breakdown(self):
        """The form asks the count, so it must not lag behind the rows."""
        self._set(self.multi, self.multi_a | self.multi_b)
        self.assertEqual(
            self.partner.score_line_count, len(self.partner.score_line_ids)
        )
        self.assertTrue(self.partner.score_line_count)

        self.partner.score_line_ids.unlink()
        self.assertEqual(self.partner.score_line_count, 0)
