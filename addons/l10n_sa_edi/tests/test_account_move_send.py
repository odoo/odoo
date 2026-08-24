# Part of Odoo. See LICENSE file for full copyright and licensing details.
from unittest.mock import patch

from odoo.exceptions import LockError, UserError
from odoo.tests import tagged
from odoo.addons.l10n_sa_edi.tests.common import TestSaEdiCommon

ZATCA_POST_METHOD = 'odoo.addons.l10n_sa_edi.models.l10n_sa_edi_document.L10nSaEdiDocument._l10n_sa_post_zatca_edi'
LOCK_METHOD = 'odoo.orm.models.BaseModel.lock_for_update'


@tagged('post_install_l10n', '-at_install', 'post_install')
class TestSaEdiAccountMoveSend(TestSaEdiCommon):

    def _create_posted_invoice(self):
        invoice = self._create_test_invoice(
            partner_id=self.partner_sa,
            invoice_line_ids=[{
                'product_id': self.product_a.id,
                'price_unit': 100.0,
                'tax_ids': self.tax_15.ids,
            }],
        )
        invoice.action_post()
        self.assertTrue(invoice.l10n_sa_edi_document_id, "Posting should have created a ZATCA document.")
        return invoice

    def _create_accepted_invoice(self):
        """ Post an invoice and bring its document to the state it has once ZATCA accepted it. """
        invoice = self._create_posted_invoice()
        invoice.l10n_sa_edi_document_id.write({
            'state': 'accepted',
            'l10n_sa_chain_index': 1,
        })
        return invoice

    def _get_invoices_data(self, invoice):
        invoices_data = {invoice: self.env['account.move.send']._get_default_sending_settings(invoice)}
        self.assertTrue(
            {'sa_edi', 'sa_edi_test'} & set(invoices_data[invoice]['extra_edis']),
            "The invoice should be sent to ZATCA, otherwise the tests below prove nothing.",
        )
        return invoices_data

    def _send_to_zatca(self, invoices_data):
        """ Run the send hook with the submission itself mocked out. """
        with patch(ZATCA_POST_METHOD) as mock_post_zatca:
            self.env['account.move.send']._call_web_service_before_invoice_pdf_render(invoices_data)
        return mock_post_zatca

    def _lock_taken_elsewhere(self):
        """ Another transaction holds the records, so FOR UPDATE SKIP LOCKED returns no row. """
        return patch(LOCK_METHOD, side_effect=LockError("Cannot grab a lock on records"))

    def test_zatca_sent_when_posted(self):
        invoice = self._create_posted_invoice()

        mock_post_zatca = self._send_to_zatca(self._get_invoices_data(invoice))

        mock_post_zatca.assert_called_once()

    def test_zatca_skipped_when_locked_by_another_transaction(self):
        """ Batch sending runs in a cron, so the invoice may be reset to draft while it is being sent. """
        invoice = self._create_posted_invoice()
        invoices_data = self._get_invoices_data(invoice)

        with self._lock_taken_elsewhere():
            mock_post_zatca = self._send_to_zatca(invoices_data)

        mock_post_zatca.assert_not_called()

    def test_reset_to_draft_refused_while_being_sent(self):
        """ The reset must be refused, not applied once the submission it races with has committed. """
        invoice = self._create_posted_invoice()

        with self._lock_taken_elsewhere(), self.assertRaisesRegex(UserError, "being sent by another process"):
            invoice.button_draft()

        self.assertEqual(invoice.state, 'posted')

    def test_reset_to_draft_allowed_when_accepted_in_testing_mode(self):
        """ Accepted test invoices stay resettable, so they can be deleted or resubmitted in Production. """
        invoice = self._create_accepted_invoice()
        self.assertTrue(invoice.show_reset_to_draft_button)

        invoice.button_draft()

        self.assertRecordValues(invoice, [{
            'state': 'draft',
            'l10n_sa_edi_state': 'to_send',
            'l10n_sa_chain_index': 0,
        }])

    def test_reset_to_draft_refused_when_accepted_in_production_mode(self):
        invoice = self._create_accepted_invoice()
        self.company.l10n_sa_edi_is_production = True

        self.assertFalse(invoice.show_reset_to_draft_button)
        with self.assertRaisesRegex(UserError, "cannot be modified according to ZATCA rules"):
            invoice.button_draft()
        self.assertEqual(invoice.state, 'posted')
