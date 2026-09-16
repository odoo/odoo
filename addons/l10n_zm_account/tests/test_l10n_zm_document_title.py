from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class Testl10nZMDocumentTitle(AccountTestInvoicingCommon):

    @classmethod
    @AccountTestInvoicingCommon.setup_country('zm')
    def setUpClass(cls):
        super().setUpClass()

    def test_l10n_zm_document_title(self):
        """Test the document title for ZM moves."""

        # Sale Documents
        sale_moves = (
            self._create_invoice('out_invoice')
            | self._create_invoice('out_refund')
        )

        # Draft documents
        self._assert_document_titles(
            sale_moves,
            [
                'Draft Tax Invoice',
                'Draft Credit Note',
            ],
        )

        # Posted documents
        sale_moves.action_post()
        self._assert_document_titles(
            sale_moves,
            [
                'Fiscal Tax Invoice',
                'Credit Note',
            ],
        )

        # Cencelled documents
        sale_moves.button_cancel()
        self._assert_document_titles(
            sale_moves,
            [
                'Cancelled Tax Invoice',
                'Cancelled Credit Note',
            ],
        )

        # Purchase Documents
        purchase_moves = (
            self._create_invoice('in_invoice')
            | self._create_invoice('in_refund')
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
