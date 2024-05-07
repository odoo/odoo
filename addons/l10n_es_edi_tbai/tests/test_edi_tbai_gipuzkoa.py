from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests import tagged

from .common import TestEsEdiTbaiCommonGipuzkoa


@tagged('post_install', '-at_install', 'post_install_l10n')
class TestSendAndPrintEdiGipuzkoa(TestEsEdiTbaiCommonGipuzkoa):

    def test_post_and_cancel_invoice_tbai_success(self):
        invoice = self._create_posted_invoice()
        invoice_send_wizard = self._get_invoice_send_wizard(invoice)

        self.assertEqual(invoice.l10n_es_tbai_state, 'to_send')
        self.assertFalse(invoice.l10n_es_tbai_chain_index)
        self.assertFalse(invoice.l10n_es_tbai_post_attachment_id)

        with patch(
            'odoo.addons.l10n_es_edi_tbai.models.l10n_es_edi_tbai_document.requests.Session.request',
            return_value=self.mock_response_post_invoice_success,
            ):
            invoice_send_wizard.action_send_and_print()

        self.assertEqual(invoice.l10n_es_tbai_state, 'sent')
        self.assertTrue(invoice.l10n_es_tbai_chain_index)
        self.assertTrue(invoice.l10n_es_tbai_post_attachment_id)

        self.assertEqual(invoice.state, 'posted')
        self.assertFalse(invoice.l10n_es_tbai_cancel_attachment_id)

        with patch(
            'odoo.addons.l10n_es_edi_tbai.models.l10n_es_edi_tbai_document.requests.Session.request',
            return_value=self.mock_response_cancel_invoice_success,
            ):
            invoice.l10n_es_tbai_cancel()

        self.assertEqual(invoice.l10n_es_tbai_state, 'cancelled')
        self.assertEqual(invoice.state, 'cancel')
        self.assertTrue(invoice.l10n_es_tbai_cancel_attachment_id)

    def test_post_invoice_tbai_failure(self):
        invoice = self._create_posted_invoice()
        invoice_send_wizard = self._get_invoice_send_wizard(invoice)

        with self.assertRaises(UserError):
            with patch(
                'odoo.addons.l10n_es_edi_tbai.models.l10n_es_edi_tbai_document.requests.Session.request',
                return_value=self.mock_response_failure,
                ):
                invoice_send_wizard.action_send_and_print()

    def test_cancel_invoice_tbai_failure(self):
        invoice = self._create_posted_invoice()
        invoice_send_wizard = self._get_invoice_send_wizard(invoice)

        with patch(
            'odoo.addons.l10n_es_edi_tbai.models.l10n_es_edi_tbai_document.requests.Session.request',
            return_value=self.mock_response_post_invoice_success,
            ):
            invoice_send_wizard.action_send_and_print()

        with self.assertRaises(UserError):
            with patch(
                'odoo.addons.l10n_es_edi_tbai.models.l10n_es_edi_tbai_document.requests.Session.request',
                return_value=self.mock_response_failure,
                ):
                invoice.l10n_es_tbai_cancel()

    def test_post_invoice_tbai_request_error(self):
        invoice = self._create_posted_invoice()
        invoice_send_wizard = self._get_invoice_send_wizard(invoice)

        with self.assertRaises(UserError):
            with patch(
                'odoo.addons.l10n_es_edi_tbai.models.l10n_es_edi_tbai_document.requests.Session.request',
                side_effect=self.mock_request_error,
                ):
                invoice_send_wizard.action_send_and_print()
