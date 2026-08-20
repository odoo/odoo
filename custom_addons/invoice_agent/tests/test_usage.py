"""Tests for the invoice.agent.usage token/cost ledger."""

from odoo.exceptions import AccessError
from odoo.tests import new_test_user, tagged

from .test_extraction import InvoiceAgentTestCommon

REVIEWER_GROUP = "invoice_agent.group_invoice_agent_user"


@tagged("post_install", "-at_install")
class TestInvoiceAgentUsage(InvoiceAgentTestCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.usage_model = cls.env["invoice.agent.usage"]

    def _sample_usage(self):
        return {
            "input_tokens": 4000,
            "cache_creation_input_tokens": 4500,
            "cache_read_input_tokens": 0,
            "output_tokens": 500,
        }

    def test_log_usage_persists_raw_tokens_and_model(self):
        usage = self.usage_model.create(
            {
                "model": "claude-opus-4-8",
                **self._sample_usage(),
            },
        )
        self.assertTrue(usage.create_date)
        self.assertEqual(usage.input_tokens, 4000)
        self.assertEqual(usage.cache_creation_input_tokens, 4500)
        self.assertEqual(usage.cache_read_input_tokens, 0)
        self.assertEqual(usage.output_tokens, 500)
        self.assertEqual(usage.model, "claude-opus-4-8")

    def test_cost_computed_at_opus_rates(self):
        usage = self.usage_model.create(
            {
                "model": "claude-opus-4-8",
                "input_tokens": 1_000_000,
                "cache_creation_input_tokens": 1_000_000,
                "cache_read_input_tokens": 1_000_000,
                "output_tokens": 1_000_000,
            },
        )
        self.assertAlmostEqual(usage.cost, 15.0 + 3.75 + 1.5 + 75.0, places=4)

    def test_llm_log_usage_writes_row(self):
        llm = self.env["invoice.llm.service"]
        llm.log_usage(False, self._sample_usage(), model="claude-opus-4-8")
        self.assertGreaterEqual(self.usage_model.search_count([]), 1)

    def test_mtd_spend_counts_current_month_rows(self):
        self.usage_model.create(
            {
                "model": "claude-opus-4-8",
                "input_tokens": 1_000_000,
                "cache_creation_input_tokens": 0,
                "cache_read_input_tokens": 0,
                "output_tokens": 0,
            },
        )
        self.assertGreaterEqual(self.usage_model.mtd_spend(), 15.0)

    def test_reviewer_cannot_create_usage(self):
        reviewer = new_test_user(
            self.env,
            name="Usage Reviewer",
            login="usage_reviewer",
            group_ids=[self.env.ref(REVIEWER_GROUP).id],
        )
        with self.assertRaises(AccessError):
            self.env["invoice.agent.usage"].with_user(reviewer).create(
                {
                    "model": "claude-opus-4-8",
                    "input_tokens": 1,
                    "cache_creation_input_tokens": 0,
                    "cache_read_input_tokens": 0,
                    "output_tokens": 1,
                },
            )
