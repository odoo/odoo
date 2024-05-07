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
        self.assertFalse(bill.l10n_es_tbai_post_attachment_id)

        with patch(
            'odoo.addons.l10n_es_edi_tbai.models.l10n_es_edi_tbai_document.requests.Session.request',
            return_value=self.mock_response_post_bill_success,
            ):
            bill.l10n_es_tbai_send_bill()

        self.assertEqual(bill.l10n_es_tbai_state, 'sent')
        # No chain index for vendor bills
        self.assertFalse(bill.l10n_es_tbai_chain_index)
        self.assertTrue(bill.l10n_es_tbai_post_attachment_id)

        self.assertEqual(bill.state, 'posted')
        self.assertFalse(bill.l10n_es_tbai_cancel_attachment_id)

        with patch(
            'odoo.addons.l10n_es_edi_tbai.models.l10n_es_edi_tbai_document.requests.Session.request',
            return_value=self.mock_response_cancel_bill_success,
            ):
            bill.l10n_es_tbai_cancel()

        self.assertEqual(bill.l10n_es_tbai_state, 'cancelled')
        self.assertEqual(bill.state, 'cancel')
        self.assertTrue(bill.l10n_es_tbai_cancel_attachment_id)

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
