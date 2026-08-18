"""RAG corpus tests (v0.10): `_build_rag_document` and the vendor-doc upsert.

Two layers:

1. ``account.move._build_rag_document()`` — deterministic rendering of a
   posted vendor bill into the compact one-document-per-bill RAG text. The
   render must be stable and self-describing (``Vendor:``, ``Date:``,
   ``Total:``, ``Lines:``) so the future RAG tool can reason over it.
2. ``invoice.agent.vendor.doc.upsert_embedding()`` — the pgvector upsert is
   idempotent per move_id: embedding the same bill twice must never create
   a second row (the milestone's "no duplicate draft" guard lives on the
   unique move_id constraint).

The pgvector extension/column/index are installed by the model's own
``init()`` (via ``CREATE EXTENSION IF NOT EXISTS vector``), so this suite
runs on the CI service container exactly like compose.
"""

from unittest.mock import patch

from odoo.tests import TransactionCase, tagged


def ensure_chart_of_accounts(env):
    """Load a COA so invoice lines resolve real account codes."""
    company = env.company
    if not company.chart_template:
        env["account.chart.template"].try_loading(
            "generic_coa",
            company=company,
            install_demo=False,
        )
    env.flush_all()


@tagged("post_install", "-at_install")
class TestRagDocument(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        ensure_chart_of_accounts(cls.env)
        cls.vendor = cls.env["res.partner"].create(
            {"name": "ACME Supplies LLC", "company_id": False},
        )
        cls.purchase_journal = cls.env["account.journal"].search(
            [("type", "=", "purchase"), ("company_id", "=", cls.env.company.id)],
            limit=1,
        )
        if not cls.purchase_journal:
            cls.purchase_journal = cls.env["account.journal"].create(
                {
                    "name": "Test Purchase Journal",
                    "type": "purchase",
                    "code": "TPJ",
                },
            )
        cls.env.flush_all()

    def _posted_bill(self):
        """Draft vendor bill -> two lines -> posted."""
        bill = self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": self.vendor.id,
                "journal_id": self.purchase_journal.id,
                "invoice_date": "2026-07-01",
                "ref": "ACME-2026-07",
                "invoice_line_ids": [
                    (0, 0, {"name": "Server hosting", "quantity": 1.0, "price_unit": 850.0}),
                    (0, 0, {"name": "Setup fee", "quantity": 1.0, "price_unit": 500.0}),
                ],
            }
        )
        bill.action_post()
        return bill

    def test_build_rag_document_shape(self):
        """The render is compact, self-describing and includes the lines."""
        bill = self._posted_bill()
        doc = bill._build_rag_document()
        self.assertIn("Vendor: ACME Supplies LLC", doc)
        self.assertIn("Date: 2026-07-01", doc)
        self.assertIn("Ref: ACME-2026-07", doc)
        self.assertIn("Total: 1350.0", doc)
        # Both product lines travel with the bill.
        self.assertIn("Server hosting", doc)
        self.assertIn("Setup fee", doc)
        # The render is a single compact text, not a multi-paragraph blob.
        self.assertLess(len(doc), 512)

    def test_write_resets_ai_indexed(self):
        """A header change invalidates the stored embedding."""
        bill = self._posted_bill()
        bill.write({"ai_indexed": True})
        self.assertTrue(bill.ai_indexed)
        bill.write({"ref": "ACME-2026-07-REVISED"})
        self.assertFalse(bill.ai_indexed)

    def test_action_post_marks_indexed_when_embedding_succeeds(self):
        """Live embed on post: ai_indexed flips True when the service OKs it."""
        with patch.object(
            self.env["invoice.llm.service"].__class__,
            "embed_texts",
            return_value=[[0.1] * 1024],
        ):
            bill = self._posted_bill()
        self.assertTrue(bill.ai_indexed)
        doc = self.env["invoice.agent.vendor.doc"].search(
            [("move_id", "=", bill.id)],
        )
        self.assertEqual(len(doc), 1)

    def test_upsert_embedding_is_idempotent(self):
        """Embedding the same bill twice yields exactly one vendor-doc row."""
        bill = self._posted_bill()
        service = self.env["invoice.llm.service"]
        embedding_a = [0.1] * 1024
        embedding_b = [0.9] * 1024

        with patch.object(service.__class__, "embed_texts", return_value=[embedding_a]):
            bill._embed_on_post()

        # A redelivered/retried embed with a different vector replaces in place.
        with patch.object(service.__class__, "embed_texts", return_value=[embedding_b]):
            bill._embed_on_post()

        rows = self.env["invoice.agent.vendor.doc"].search(
            [("move_id", "=", bill.id)],
        )
        self.assertEqual(len(rows), 1)

        # The visible content reflects the LAST write (upsert, not insert).
        self.env.cr.execute(
            "SELECT embedding::text FROM invoice_agent_vendor_doc "
            "WHERE move_id = %s",
            [bill.id],
        )
        stored = self.env.cr.fetchone()[0]
        self.assertEqual(stored, "[" + ",".join(["0.9"] * 1024) + "]")
