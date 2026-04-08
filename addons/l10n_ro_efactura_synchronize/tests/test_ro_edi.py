from unittest.mock import patch

from odoo.addons.l10n_ro_edi.tests.common import TestROEdiCommon
from odoo.tests import tagged


@tagged("post_install_l10n", "-at_install", "post_install")
class TestRoEdi(TestROEdiCommon):
    def synchronize_with_mock(self, mock_return_value):
        """Helper to run synchronize mocking the SPV response."""
        with patch.object(
            self.env.registry.get("l10n_ro_edi.document"),
            "_request_ciusro_synchronize_invoices",
            return_value=mock_return_value,
        ):
            self.env["account.move"]._l10n_ro_edi_fetch_invoices()

    def test_ciusro_synchronize_resent_invoice_after_refusal(self):
        """ Test the full lifecycle when an invoice is sent, refused by the SPV, reset and resent
            without receiving an index (simulating a server timeout), and synchronize returns 2 messages:
            the original refusal ('AA') and the new acceptance ('BB').

            Expected outcome:
            - The acceptance 'BB' is matched by invoice name (since l10n_ro_edi_index is False after timeout)
            - The refusal 'AA' is skipped (the invoice no longer has index 'AA' and state 'invoice_sent')
            - The invoice ends up as validated with index 'BB'
            - All old documents are cleaned up by _l10n_ro_edi_create_document_invoice_validated
        """
        # Step 1: Create invoice and simulate successful first send with index 'AA'
        invoice = self.create_invoice()
        invoice._l10n_ro_edi_create_document_invoice_sent({
            "key_loading": "AA",
            "attachment_raw": b"<xml>invoice</xml>",
        })
        invoice.l10n_ro_edi_index = "AA"
        self.assertEqual(invoice.l10n_ro_edi_state, "invoice_sent")

        # Step 2: SPV refuses the invoice via individual fetch (status 'nok')
        with patch.object(
            self.env.registry.get("l10n_ro_edi.document"),
            "_request_ciusro_fetch_status",
            return_value={"key_download": "DL_AA", "state_status": "nok"},
        ), patch.object(
            self.env.registry.get("l10n_ro_edi.document"),
            "_request_ciusro_download_answer",
            return_value={
                "attachment_raw": b"<xml>error</xml>",
                "key_signature": None,
                "key_certificate": None,
                "error": "XML validation failed by SPV",
            },
        ):
            invoice._l10n_ro_edi_fetch_invoice_sent_documents()

        self.assertEqual(invoice.l10n_ro_edi_state, False)
        self.assertEqual(len(invoice._l10n_ro_edi_get_failed_documents()), 1)
        self.assertEqual(invoice.l10n_ro_edi_index, "AA")  # index persists after refusal

        # Step 3: Reset to draft and resend; timeout means no index is received from SPV
        invoice.button_draft()
        invoice.action_post()

        with patch.object(
            self.env.registry.get("l10n_ro_edi.document"),
            "_request_ciusro_send_invoice",
            return_value={"key_loading": False},
        ):
            invoice._l10n_ro_edi_send_invoice(b"<xml>invoice</xml>")

        self.assertEqual(invoice.l10n_ro_edi_state, "invoice_sent")
        self.assertEqual(invoice.l10n_ro_edi_index, False)
        # Historical failed doc is preserved alongside the new sent doc (traceability)
        self.assertEqual(len(invoice.l10n_ro_edi_document_ids), 2)

        # Step 4: Synchronize returns both messages: old refusal 'AA' + new acceptance 'BB'
        # 'BB' is matched by invoice name since l10n_ro_edi_index is False
        invoice_name = invoice.name
        self.synchronize_with_mock({
            "sent_invoices_accepted_messages": [
                {
                    "data_creare": "202503271639",
                    "cif": self.env.company.vat,
                    "id_solicitare": "BB",
                    "tip": "FACTURA TRIMISA",
                    "id": "MSG_BB",
                    "answer": {
                        "signature": {
                            "attachment_raw": b"<xml>signature_bb</xml>",
                            "key_signature": "KEY_SIG_BB",
                            "key_certificate": "KEY_CERT_BB",
                        },
                        "invoice": {
                            "name": invoice_name,
                        },
                    },
                },
            ],
            "sent_invoices_refused_messages": [
                {
                    "data_creare": "202503271500",
                    "cif": self.env.company.vat,
                    "id_solicitare": "AA",
                    "tip": "ERORI FACTURA",
                    "id": "MSG_AA",
                    "answer": {
                        "signature": {
                            "attachment_raw": b"<xml>error_signature_aa</xml>",
                            "key_signature": "KEY_SIG_AA",
                            "key_certificate": "KEY_CERT_AA",
                        },
                        "invoice": {
                            "error": "XML validation failed by SPV",
                            "attachment_raw": b"<xml>error_aa</xml>",
                        },
                    },
                },
            ],
            "received_bills_messages": [],
        })

        invoice.invalidate_recordset()

        # Acceptance 'BB' matched by name, index updated and invoice validated
        self.assertEqual(invoice.l10n_ro_edi_state, "invoice_validated")
        self.assertEqual(invoice.l10n_ro_edi_index, "BB")
        # _l10n_ro_edi_create_document_invoice_validated cleans up all old docs on success
        self.assertEqual(len(invoice.l10n_ro_edi_document_ids), 1)
        self.assertEqual(invoice.l10n_ro_edi_document_ids.state, "invoice_validated")
        # Refusal 'AA' was skipped: invoice had index=False, not 'AA', when refused domain was evaluated
        self.assertFalse(invoice.l10n_ro_edi_document_ids.filtered(lambda d: d.state == "invoice_sending_failed"))
