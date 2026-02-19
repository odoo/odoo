from .common import PdpTestCommon


class TestPdpInvoiceStatus(PdpTestCommon):
    def test_status_ready_after_send_and_aggregation(self):
        inv = self._create_invoice(sent=True)
        self._run_aggregation()
        inv.invalidate_recordset(["l10n_fr_pdp_status"])
        self.assertEqual(inv.l10n_fr_pdp_status, "ready", "Sent invoice should be ready once flow is built")

    def test_status_error_when_not_sent(self):
        inv = self._create_invoice(sent=False)
        self._run_aggregation()
        inv.invalidate_recordset(["l10n_fr_pdp_status"])
        self.assertEqual(inv.l10n_fr_pdp_status, "error", "Unsent posted invoice must be PDP error")
