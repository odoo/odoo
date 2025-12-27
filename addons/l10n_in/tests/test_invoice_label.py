from odoo import Command
from odoo.addons.l10n_in.tests.common import L10nInTestInvoicingCommon
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestInvoiceLabel(L10nInTestInvoicingCommon):
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
        )
        invoice_label = regular_taxable_invoice._get_l10n_in_invoice_label()
        self.assertEqual(invoice_label, 'Tax Invoice')

        # Regular with exempt items
        regular_exempt_invoice = self._init_inv(
            partner=self.partner_b,
            taxes=self.exempt,
            line_vals={'price_unit': 1000, 'quantity': 1},
        )
        invoice_label = regular_exempt_invoice._get_l10n_in_invoice_label()
        self.assertEqual(invoice_label, 'Bill of Supply')

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
        regular_mix_invoice.action_post()
        invoice_label = regular_mix_invoice._get_l10n_in_invoice_label()
        self.assertEqual(invoice_label, 'Invoice')

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
        unregistered_invoice.action_post()
        invoice_label = unregistered_invoice._get_l10n_in_invoice_label()
        self.assertEqual(invoice_label, 'Invoice-cum-Bill of Supply')
