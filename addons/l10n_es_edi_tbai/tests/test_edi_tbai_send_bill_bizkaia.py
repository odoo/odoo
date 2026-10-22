from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests import tagged

from .common import TestEsEdiTbaiCommonBizkaia


@tagged('post_install', '-at_install', 'post_install_l10n')
class TestSendBillEdiBizkaia(TestEsEdiTbaiCommonBizkaia):

    def test_post_and_cancel_bill_tbai_success(self):
        bill = self._create_posted_bill()

        self.assertEqual(bill.l10n_es_tbai_state, 'to_send')
        self.assertFalse(bill.l10n_es_tbai_chain_index)
        self.assertFalse(bill.l10n_es_tbai_post_document_id.xml_attachment_id)

        with patch(
            'odoo.addons.l10n_es_edi_tbai.models.l10n_es_edi_tbai_document.requests.Session.request',
            return_value=self.mock_response_post_bill_success,
        ):
            bill.l10n_es_tbai_send_bill()

        self.assertEqual(bill.l10n_es_tbai_state, 'sent')
        # No chain index for vendor bills
        self.assertFalse(bill.l10n_es_tbai_chain_index)
        self.assertTrue(bill.l10n_es_tbai_post_document_id.xml_attachment_id)
        html = self.env['ir.actions.report']._render_qweb_html('account.report_invoice', bill.ids)[0]
        self.assertNotIn(b'l10n_es_tbai_qrcode', html)

        self.assertEqual(bill.state, 'posted')
        self.assertFalse(bill.l10n_es_tbai_cancel_document_id.xml_attachment_id)

        with patch(
            'odoo.addons.l10n_es_edi_tbai.models.l10n_es_edi_tbai_document.requests.Session.request',
            return_value=self.mock_response_cancel_bill_success,
        ):
            bill.l10n_es_tbai_cancel()

        self.assertEqual(bill.l10n_es_tbai_state, 'cancelled')
        self.assertEqual(bill.state, 'cancel')
        self.assertTrue(bill.l10n_es_tbai_cancel_document_id.xml_attachment_id)

    def test_post_refund_bill_without_refund_reason(self):
        bill = self._create_posted_bill()
        with patch(
            'odoo.addons.l10n_es_edi_tbai.models.l10n_es_edi_tbai_document.requests.Session.request',
            return_value=self.mock_response_post_bill_success,
        ):
            bill.l10n_es_tbai_send_bill()
        refund = bill._reverse_moves([{'invoice_date': bill.invoice_date, 'ref': 'RINV123'}])
        refund.action_post()
        self.assertFalse(refund.l10n_es_tbai_refund_reason)

        with patch(
            'odoo.addons.l10n_es_edi_tbai.models.l10n_es_edi_tbai_document.requests.Session.request',
            return_value=self.mock_response_post_bill_success,
        ) as mock_request, self.assertRaisesRegex(UserError, 'Refund reason must be specified'):
            refund.l10n_es_tbai_send_bill()
        mock_request.assert_not_called()

    def test_post_bill_tbai_failure(self):
        bill = self._create_posted_bill()

        with self.assertRaises(UserError):
            with patch(
                'odoo.addons.l10n_es_edi_tbai.models.l10n_es_edi_tbai_document.requests.Session.request',
                return_value=self.mock_response_post_bill_failure,
            ):
                bill.l10n_es_tbai_send_bill()

    def test_cancel_bill_tbai_failure(self):
        bill = self._create_posted_bill()

        with patch(
            'odoo.addons.l10n_es_edi_tbai.models.l10n_es_edi_tbai_document.requests.Session.request',
            return_value=self.mock_response_post_bill_success,
        ):
            bill.l10n_es_tbai_send_bill()

        with self.assertRaises(UserError):
            with patch(
                'odoo.addons.l10n_es_edi_tbai.models.l10n_es_edi_tbai_document.requests.Session.request',
                return_value=self.mock_response_cancel_bill_failure,
            ):
                bill.l10n_es_tbai_cancel()

    def test_post_bill_tbai_request_error(self):
        bill = self._create_posted_bill()

        with self.assertRaises(UserError):
            with patch(
                'odoo.addons.l10n_es_edi_tbai.models.l10n_es_edi_tbai_document.requests.Session.request',
                side_effect=self.mock_request_error,
            ):
                bill.l10n_es_tbai_send_bill()
