from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nAUDocumentTitle(AccountTestInvoicingCommon):

    @classmethod
    @AccountTestInvoicingCommon.setup_country('au')
    def setUpClass(cls):
        super().setUpClass()

        cls.sale_moves = (
            cls._create_invoice('out_invoice', post=True)
            | cls._create_invoice('out_refund', post=True)
        )
        cls.purchase_moves = (
            cls._create_invoice('in_invoice', post=True)
            | cls._create_invoice('in_refund', post=True)
        )

    def test_l10n_au_document_title_without_gst_registration(self):
        """Test document titles for AU documents when GST registration is disabled."""

        # Sale documents
        self._assert_document_titles(
            self.sale_moves,
            [
                'Invoice',
                'Credit Note',
            ],
        )

        # Purchase documents
        self._assert_document_titles(
            self.purchase_moves,
            [
                'Vendor Bill',
                'Vendor Credit Note',
            ],
        )

        # Self-billing documents
        self.purchase_moves.mapped('journal_id').is_self_billing = True
        self._assert_document_titles(
            self.purchase_moves,
            [
                'Self Billing',
                'Self Billing Credit Note',
            ],
        )

    def test_l10n_au_document_title_with_gst_registration(self):
        """Test document titles for AU documents when GST registration is enabled."""

        # Register the company for GST.
        self.env.company.l10n_au_is_gst_registered = True

        # Sale documents
        self._assert_document_titles(
            self.sale_moves,
            [
                'Tax Invoice',
                'Tax Credit Note',
            ],
        )

        # Purchase documents
        self._assert_document_titles(
            self.purchase_moves,
            [
                'Tax Vendor Bill',
                'Tax Vendor Credit Note',
            ],
        )

        # Self-billing documents
        self.purchase_moves.mapped('journal_id').is_self_billing = True
        self._assert_document_titles(
            self.purchase_moves,
            [
                'Self Billing',
                'Self Billing Credit Note',
            ],
        )
