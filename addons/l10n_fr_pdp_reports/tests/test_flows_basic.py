from odoo import fields
from .common import PdpTestCommon
from odoo.addons.l10n_fr_pdp_reports.models.pdp_payload import PdpPayloadBuilder


class TestPdpFlowsBasic(PdpTestCommon):
    def test_single_invoice_ready_flow(self):
        """IN transaction flow built and ready for a single sent invoice."""
        self._create_invoice(sent=True)
        flows = self._run_aggregation()
        flow = flows.filtered(lambda f: f.report_kind == "transaction")
        self.assertGreaterEqual(len(flow), 1, "Expected at least one transaction flow")
        flow = flow[:1]
        self.assertEqual(flow.state, "ready", "Flow should be ready after payload build")
        self.assertEqual(flow.transmission_type, "IN", "First flow must be IN")
        self.assertTrue(flow.slice_ids, "Flow should have slices built")
        self.assertTrue(flow.slice_ids[0].payload, "Payload must be generated")

    def test_invoice_not_sent_flags_error_status(self):
        """Posted invoice not sent -> PDP status error."""
        inv = self._create_invoice(sent=False)
        self._run_aggregation()
        inv.invalidate_recordset(["l10n_fr_pdp_status"])
        self.assertEqual(inv.l10n_fr_pdp_status, "error", "Unsent posted invoice must be in PDP error")

    def test_b2c_daily_summary_multiple_days(self):
        """B2C invoices on different days generate per-day summaries in payload."""
        day1 = fields.Date.from_string("2025-01-05")
        day2 = fields.Date.from_string("2025-01-06")
        self._create_invoice(date_val=day1, sent=True)
        self._create_invoice(date_val=day2, sent=True)
        flows = self._run_aggregation()
        tx_flows = flows.filtered(lambda f: f.report_kind == "transaction")
        self.assertTrue(tx_flows, "Transaction flow should exist")
        for flow in tx_flows:
            dates = {m.invoice_date or m.date for m in flow.move_ids}
            builder = PdpPayloadBuilder(flow)
            report_vals = builder._build_transaction_report_vals(flow.move_ids)
            summaries = report_vals.get("transaction_summaries") or []
            self.assertEqual(
                len(summaries), len(dates),
                "Flow %s expected %s summaries for dates %s, got %s" % (
                    flow.id, len(dates), dates, len(summaries)),
            )
