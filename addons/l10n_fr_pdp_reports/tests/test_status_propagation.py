from unittest.mock import patch

from .common import PdpTestCommon


class TestPdpStatusPropagation(PdpTestCommon):
    def test_invoice_status_moves_from_pending_to_done(self):
        """Invoice PDP status follows slice state pending -> done."""
        inv = self._create_invoice(sent=True)
        flow = self._aggregate_company().filtered(lambda f: f.report_kind == "transaction")[:1]

        with patch("odoo.addons.l10n_fr_pdp_reports.models.pdp_flow.PdpFlow._call_transport_gateway", return_value={
            "id": "X-PENDING",
            "status": "RECEIVED",
            "message": "",
            "acknowledgement": [],
        }):
            flow.action_send()
        inv.invalidate_recordset(["l10n_fr_pdp_status"])
        self.assertEqual(inv.l10n_fr_pdp_status, "pending")

        flow.slice_ids.write({"state": "ready"})
        with patch("odoo.addons.l10n_fr_pdp_reports.models.pdp_flow.PdpFlow._call_transport_gateway", return_value={
            "id": "X-DONE",
            "status": "ACCEPTED",
            "message": "",
            "acknowledgement": [],
        }):
            flow.action_send()
        inv.invalidate_recordset(["l10n_fr_pdp_status"])
        self.assertEqual(inv.l10n_fr_pdp_status, "done")

    def test_statusbar_fold_configuration(self):
        """Form view should fold statusbar on done/error states."""
        view = self.env.ref("l10n_fr_pdp_reports.l10n_fr_pdp_reports_view_flow_form")
        self.assertIn('statusbar_fold="done,error"', view.arch_db)

    def test_flow_marked_outdated_on_partner_change(self):
        """Changing partner VAT should reset open flows to draft and clear payload."""
        self._create_invoice(partner=self.partner_international, sent=True)
        flow = self._aggregate_company().filtered(lambda f: f.report_kind == "transaction")[:1]
        self.assertEqual(flow.state, "ready")
        self.assertTrue(flow.has_payload)

        self.partner_international.with_context(no_vat_validation=True).write({"vat": "BE000"})
        flow.invalidate_recordset(["state", "has_payload", "revision"])
        self.assertEqual(flow.state, "draft", "Flow should be reset to draft after partner change")
        self.assertFalse(flow.payload, "Flow payload field should be cleared when marked outdated")

    def test_error_moves_cleared_after_fix_and_rebuild(self):
        """Fixing invalid invoice and rebuilding should clear error_move_ids."""
        bad = self._create_invoice(sent=False)
        flow = self._aggregate_company().filtered(lambda f: f.report_kind == "transaction")[:1]
        self.assertIn(bad, flow.error_move_ids)

        bad.is_move_sent = True
        flow._build_payload()
        flow.invalidate_recordset(["error_move_ids", "state"])
        self.assertFalse(flow.error_move_ids, "error_move_ids should be cleared after fixing issues")
        self.assertEqual(flow.state, "ready")
