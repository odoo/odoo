import unittest

from odoo.tests.common import TransactionCase, tagged

from odoo.addons.od19_approval_center.hooks import post_init_hook


@tagged("post_install", "-at_install")
class TestApprovalSeed(TransactionCase):
    def test_seed_is_idempotent(self):
        Source = self.env["od19.approval.source"]
        # Seed once (the DB starts empty: ``-u`` is an upgrade, so the install
        # hook never ran at module load), then a second run must be a no-op.
        post_init_hook(self.env)
        before = Source.search_count([])
        self.assertGreater(before, 0)
        post_init_hook(self.env)
        self.assertEqual(Source.search_count([]), before)

    def test_expense_source_has_two_steps(self):
        post_init_hook(self.env)
        source = self.env["od19.approval.source"].search(
            [("model_name", "=", "hr.expense")], limit=1
        )
        self.assertTrue(source, "hr.expense source should be seeded")
        self.assertEqual(len(source.step_ids), 2)
        self.assertEqual(source.sla_days, 3)

    def test_missing_models_are_skipped(self):
        post_init_hook(self.env)
        Source = self.env["od19.approval.source"]
        for source in Source.search([]):
            self.assertIn(
                source.model_name, self.env,
                "seeded source points at a model not installed: %s" % source.model_name,
            )
