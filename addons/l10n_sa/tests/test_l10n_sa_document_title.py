from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class Testl10nSADocumentTitle(AccountTestInvoicingCommon):

    @classmethod
    @AccountTestInvoicingCommon.setup_country('sa')
    def setUpClass(cls):
        super().setUpClass()

    def test_l10n_sa_document_title(self):
        """Test the document title for SA moves."""

        # Sale Documents
        sale_moves = (
            self._create_invoice('out_invoice', l10n_sa_invoice_type='tax', post=True)
            | self._create_invoice('out_refund', post=True)
        )

        self._assert_document_titles(
            sale_moves,
            [
                'Tax Invoice',
                'Credit Note',
            ],
        )

        # Set the invoice type to simplified and verify the document title for invoice.
        invoice = sale_moves[0]
        invoice.l10n_sa_invoice_type = 'simplified'
        self._assert_document_titles(invoice, ['Simplified Tax Invoice'])

        # Purchase Documents
        purchase_moves = (
            self._create_invoice('in_invoice', post=True)
            | self._create_invoice('in_refund', post=True)
        )

        self._assert_document_titles(
            purchase_moves,
            [
                'Vendor Bill',
                'Vendor Credit Note',
            ],
        )

        # Self-Billing documents
        purchase_moves.mapped('journal_id').is_self_billing = True
        self._assert_document_titles(
            purchase_moves,
            [
                'Self Billing',
                'Self Billing Credit Note',
            ],
        )
