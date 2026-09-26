from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class Testl10nLKDocumentTitle(AccountTestInvoicingCommon):

    @classmethod
    @AccountTestInvoicingCommon.setup_country('lk')
    def setUpClass(cls):
        super().setUpClass()

        cls.lk_group_18 = cls.env["account.tax.group"].search(
            [("country_id.code", "=", "LK"), ("name", "=", "18%")],
            limit=1,
        )
        cls.lk_taxable_tax = cls.env["account.tax"].create(
            {
                "name": "18% (test)",
                "amount": 18,
                "amount_type": "percent",
                "tax_group_id": cls.lk_group_18.id,
                "type_tax_use": "sale",
            },
        )

    def test_l10n_lk_document_title(self):
        """Test the document title for LK moves."""

        # Sale Documents
        invoice = self.init_invoice(move_type='out_invoice', taxes=[self.lk_taxable_tax], amounts=[10], post=True)
        invoice.commercial_partner_id.l10n_lk_vat_registered = True
        sale_moves = (
            invoice
            | self._create_invoice('out_refund', post=True)
        )

        self._assert_document_titles(
            sale_moves,
            [
                'Invoice',
                'Credit Note',
            ],
        )

        # Register the company and partner for VAT and verify the document title for posted invoice.
        self.env.company.l10n_lk_vat_registered = True
        invoice.commercial_partner_id.l10n_lk_vat_registered = True
        self._assert_document_titles(invoice, ['Tax Invoice'])

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
