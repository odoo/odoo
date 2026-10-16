from odoo import Command
from odoo.addons.l10n_in.tests.common import L10nInTestInvoicingCommon
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestInvoiceLabel(L10nInTestInvoicingCommon):
    _test_user_groups = None  # FIXME list needed groups

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.partner_b.l10n_in_gst_treatment = "regular"
        cls.unregistered_partner = cls.partner_a.copy({"state_id": cls.state_in_mh.id, "vat": None, "l10n_in_gst_treatment": "unregistered"})

    def test_invoice_label(self):
        # Regular with taxable items
        regular_taxable_invoice = self._init_inv(
            partner=self.partner_b,
            taxes=self.igst_sale_18,
            line_vals={'price_unit': 1000, 'quantity': 1},
            post=False,
        )

        # Regular with exempt items
        regular_exempt_invoice = self._init_inv(
            partner=self.partner_b,
            taxes=self.exempt,
            line_vals={'price_unit': 1000, 'quantity': 1},
            post=False,
        )

        # Regular with taxable and exempt items
        regular_mix_invoice = self._init_inv(
            partner=self.partner_b,
            taxes=self.igst_sale_18,
            line_vals={'price_unit': 1000, 'quantity': 1},
            post=False,
        )
        regular_mix_invoice.write({
            'invoice_line_ids': [Command.create({
                'product_id': self.product_b.id,
                'account_id': regular_mix_invoice.invoice_line_ids[0].account_id.id,
                'price_unit': 500,
                'quantity': 1,
                'tax_ids': [(6, 0, [self.exempt.id])],
            })],
        })

        # unregistered with taxable and exempt items
        unregistered_invoice = self._init_inv(
            partner=self.unregistered_partner,
            taxes=self.igst_sale_18,
            line_vals={'price_unit': 220000, 'quantity': 1},
            post=False,
        )
        unregistered_invoice.write({
            'invoice_line_ids': [Command.create({
                'product_id': self.product_b.id,
                'account_id': unregistered_invoice.invoice_line_ids[0].account_id.id,
                'price_unit': 500,
                'quantity': 1,
                'tax_ids': [(6, 0, [self.exempt.id])],
            })],
        })

        # Sale Documents
        sale_moves = (
            regular_taxable_invoice
            | regular_exempt_invoice
            | regular_mix_invoice
            | unregistered_invoice
            | self._create_invoice('out_refund')
        )

        sale_moves.action_post()
        self._assert_document_titles(
            sale_moves,
            [
                'Tax Invoice',
                'Bill of Supply',
                'Invoice',
                'Invoice-cum-Bill of Supply',
                'Credit Note',

            ],
        )

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

        # Self-Invoice documents
        vendor_bill = purchase_moves[0]
        vendor_bill.journal_id.l10n_in_self_invoice = True
        self._assert_document_titles(vendor_bill, ['Tax Invoice'])
