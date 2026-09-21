from unittest.mock import patch

from odoo.fields import Command
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install", "partner_scoring")
class TestScoreCeilingCascade(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Partner = cls.env["res.partner"]
        cls.Attribute = cls.env["res.partner.attribute"]
        cls.Value = cls.env["res.partner.attribute.value"]
        cls.env["partner.tier"].search([]).write({"active": False})
        cls.Value.search([("score_value", ">", 0)]).write({"score_value": 0.0})

        cls.attribute = cls.Attribute.create(
            {
                "name": "Cascade Attr",
                "value_type": "multi",
                "aggregation_mode": "sum",
            }
        )
        cls.value = cls.Value.create(
            {"name": "Held", "attribute_id": cls.attribute.id, "score_value": 10.0}
        )
        cls.holder = cls.Partner.create({"name": "Cascade Holder", "is_company": True})
        cls.env["res.partner.attribute.line"].create(
            {
                "partner_id": cls.holder.id,
                "attribute_id": cls.attribute.id,
                "value_ids": [Command.set(cls.value.ids)],
            }
        )
        cls.bystander = cls.Partner.create(
            {"name": "Cascade Bystander", "is_company": True}
        )
        cls.bystander._update_scores()

    def _refresh_queued(self):
        self.Partner.search([("score_line_ids", "!=", False)])._update_scores()
        self.env.flush_all()

    def test_a_new_weighted_value_moves_the_denominator(self):
        before = self.Partner._get_score_max_points()
        self.Value.create(
            {"name": "Added", "attribute_id": self.attribute.id, "score_value": 5.0}
        )
        self.assertEqual(self.Partner._get_score_max_points(), before + 5.0)

        self._refresh_queued()
        self.assertEqual(self.holder.score_max_points, before + 5.0)
        self.assertEqual(self.bystander.score_max_points, before + 5.0)

    def test_deleting_a_weighted_value_moves_the_denominator(self):
        extra = self.Value.create(
            {"name": "Doomed", "attribute_id": self.attribute.id, "score_value": 4.0}
        )
        with_extra = self.Partner._get_score_max_points()
        extra.unlink()
        self.assertEqual(self.Partner._get_score_max_points(), with_extra - 4.0)

        self._refresh_queued()
        self.assertEqual(self.bystander.score_max_points, with_extra - 4.0)

    def test_a_weight_edit_restales_the_non_holders_too(self):
        self.value.score_value = 20.0
        self._refresh_queued()
        self.assertEqual(self.holder.score_points, 20.0)
        self.assertEqual(
            self.bystander.score_max_points, self.Partner._get_score_max_points()
        )

    def test_a_new_attribute_moves_the_denominator(self):
        before = self.Partner._get_score_max_points()
        new_attribute = self.Attribute.create(
            {"name": "Cascade Second", "value_type": "single"}
        )
        self.Value.create(
            {"name": "Only", "attribute_id": new_attribute.id, "score_value": 6.0}
        )
        self.assertEqual(self.Partner._get_score_max_points(), before + 6.0)

        self._refresh_queued()
        self.assertEqual(self.bystander.score_max_points, before + 6.0)
        keys = self.bystander.score_line_ids.mapped("source_key")
        self.assertIn(f"partner_attr:{new_attribute.id}:none", keys)

    def test_archiving_a_weighted_value_moves_the_denominator(self):
        spare = self.Value.create(
            {"name": "Spare", "attribute_id": self.attribute.id, "score_value": 7.0}
        )
        with_spare = self.Partner._get_score_max_points()
        spare.action_archive()
        self.assertEqual(self.Partner._get_score_max_points(), with_spare - 7.0)

        spare.action_unarchive()
        self.assertEqual(self.Partner._get_score_max_points(), with_spare)

    def test_renaming_a_value_rewrites_the_breakdown_label(self):
        self._refresh_queued()
        self.value.name = "Renamed"
        self._refresh_queued()
        row = self.holder.score_line_ids.filtered(
            lambda line: line.source_key.endswith(f":{self.value.id}")
        )
        self.assertEqual(row.source_ref, f"{self.attribute.name}: Renamed")

    def test_rehoming_a_value_moves_both_ceilings(self):
        other = self.Attribute.create(
            {"name": "Cascade Target", "value_type": "single"}
        )
        spare = self.Value.create(
            {"name": "Movable", "attribute_id": self.attribute.id, "score_value": 3.0}
        )
        before = self.Partner._get_score_max_points()
        spare.attribute_id = other
        self.assertEqual(self.Partner._get_score_max_points(), before)

        self._refresh_queued()
        self.assertEqual(self.bystander.score_max_points, before)
        keys = self.bystander.score_line_ids.mapped("source_key")
        self.assertIn(f"partner_attr:{other.id}:none", keys)

    def test_the_ceiling_ignores_the_callers_active_test(self):
        """An archived-partners list recomputing one partner must not widen
        everybody's denominator: the ceiling is the catalog's, not the caller's."""
        spare = self.Value.create(
            {
                "name": "Archived Spare",
                "attribute_id": self.attribute.id,
                "score_value": 7.0,
            }
        )
        spare.action_archive()
        as_default = self.Partner._get_score_max_points()
        # Nothing may be remembered between the two readings: a cached ceiling
        # would hand the second caller the first one's answer and hide the
        # very context leak this test exists to catch.
        self.env.registry.clear_cache()
        as_archived_list = self.Partner.with_context(
            active_test=False
        )._get_score_max_points()
        self.assertEqual(as_archived_list, as_default)
        self.assertNotIn(
            spare.id, dict(self.Partner._score_ceiling_partner_attr()["attributes"])
        )
        self.assertEqual(self.Partner._get_score_max_points(), as_default)

    def test_a_bare_attribute_create_queues_nothing(self):
        """An attribute with no values moves no ceiling and rewrites no row."""
        partner_class = type(self.Partner)
        with patch.object(partner_class, "_notify_score_ceiling_changed") as notified:
            self.Attribute.create({"name": "Cascade Bare", "value_type": "single"})
        self.assertFalse(notified.called)

    def test_an_irrelevant_attribute_write_does_not_requeue(self):
        partner_class = type(self.Partner)
        with patch.object(partner_class, "_notify_score_ceiling_changed") as notified:
            self.attribute.sequence = 42
            self.assertFalse(notified.called)

            self.attribute.aggregation_mode = "max"
            self.assertTrue(notified.called)

    def test_the_requeue_reaches_partners_the_editor_cannot_see(self):
        """A shared weight makes every partner stale, not just the visible ones."""
        company = self.env["res.company"].create({"name": "Cascade Other Co"})
        editor = self.env["res.users"].create(
            {
                "name": "Cascade Editor",
                "login": "cascade_editor",
                "company_id": company.id,
                "company_ids": [Command.set(company.ids)],
                "group_ids": [
                    Command.set(
                        [
                            self.env.ref("base.group_user").id,
                            self.env.ref(
                                "partner_scoring.group_partner_scoring_manager"
                            ).id,
                        ]
                    )
                ],
            }
        )
        hidden = self.Partner.create(
            {
                "name": "Cascade Hidden",
                "is_company": True,
                "company_id": self.env.ref("base.main_company").id,
            }
        )
        hidden._update_scores()
        archived = self.Partner.create({"name": "Cascade Archived", "is_company": True})
        archived._update_scores()
        archived.action_archive()

        partner_class = type(self.Partner)
        with patch.object(
            partner_class, "_delay_scores_recompute", autospec=True
        ) as delayed:
            self.value.with_user(editor).score_value = 21.0
        requeued = delayed.call_args[0][0]
        self.assertIn(hidden, requeued)
        self.assertIn(archived, requeued)

    def test_a_second_wave_collapses_onto_the_queued_job(self):
        """Ten weight edits in one sitting must not queue ten full rescores."""
        job_model = self.env["ir.job"]
        queued = [("identity_key", "=like", "partner_scoring.recompute:%")]
        before = job_model.search_count(queued)

        scored = self.Partner.search([("score_line_ids", "!=", False)])
        self.assertTrue(scored)
        scored._delay_scores_recompute()
        after_first = job_model.search_count(queued)
        self.assertEqual(after_first, before + 1)

        scored._delay_scores_recompute()
        self.assertEqual(job_model.search_count(queued), after_first)
