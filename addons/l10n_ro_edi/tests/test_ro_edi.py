from unittest.mock import patch

from odoo.addons.l10n_ro_edi.tests.common import TestROEdiCommon
from odoo.tests import tagged


@tagged("post_install_l10n", "-at_install", "post_install")
class TestRoEdi(TestROEdiCommon):
    def test_documents_only_deleted_on_validation(self):
        """Test that historical documents are preserved on failure and only cleaned up when the invoice is validated.

        Flow:
        1. Send invoice → invoice_sent doc created
        2. Fetch → SPV refuses → invoice_sent deleted, invoice_sending_failed created (1 doc)
        3. Resend → upload fails → new invoice_sending_failed added (2 docs, no deletion)
        4. Resend → upload succeeds → old invoice_sending_failed preserved, invoice_sent created (3 docs)
        5. Fetch → SPV validates → all previous docs deleted, only invoice_validated remains (1 doc)
        """
        invoice = self.create_invoice()

        # Step 1: First send succeeds, index 'AA' received
        self.send_invoice_with_mock(invoice, {"key_loading": "AA"})
        self.assertEqual(invoice.l10n_ro_edi_state, "invoice_sent")
        self.assertEqual(len(invoice.l10n_ro_edi_document_ids), 1)

        # Step 2: SPV refuses via fetch → sent doc deleted, failed doc created
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
        self.assertEqual(len(invoice.l10n_ro_edi_document_ids), 1)
        self.assertEqual(invoice.l10n_ro_edi_document_ids.state, "invoice_sending_failed")

        # Step 3: Resend fails → new failed doc added, old one preserved
        invoice.button_draft()
        invoice.action_post()
        self.send_invoice_with_mock(invoice, {"error": "SPV unavailable"})

        self.assertEqual(invoice.l10n_ro_edi_state, False)
        self.assertEqual(len(invoice.l10n_ro_edi_document_ids), 2)
        self.assertTrue(all(d.state == "invoice_sending_failed" for d in invoice.l10n_ro_edi_document_ids))

        # Step 4: Resend succeeds → failed docs preserved, new sent doc added
        self.send_invoice_with_mock(invoice, {"key_loading": "BB"})

        self.assertEqual(invoice.l10n_ro_edi_state, "invoice_sent")
        self.assertEqual(len(invoice.l10n_ro_edi_document_ids), 3)
        self.assertEqual(len(invoice._l10n_ro_edi_get_failed_documents()), 2)
        self.assertEqual(len(invoice._l10n_ro_edi_get_sent_documents()), 1)

        # Step 5: SPV validates → all old docs deleted, only invoice_validated remains
        with patch.object(
            self.env.registry.get("l10n_ro_edi.document"),
            "_request_ciusro_fetch_status",
            return_value={"key_download": "DL_BB", "state_status": "ok"},
        ), patch.object(
            self.env.registry.get("l10n_ro_edi.document"),
            "_request_ciusro_download_answer",
            return_value={
                "attachment_raw": b"<xml>signature</xml>",
                "key_signature": "KEY_SIG",
                "key_certificate": "KEY_CERT",
                "error": False,
            },
        ):
            invoice._l10n_ro_edi_fetch_invoice_sent_documents()

        self.assertEqual(invoice.l10n_ro_edi_state, "invoice_validated")
        self.assertEqual(len(invoice.l10n_ro_edi_document_ids), 1)
        self.assertEqual(invoice.l10n_ro_edi_document_ids.state, "invoice_validated")
