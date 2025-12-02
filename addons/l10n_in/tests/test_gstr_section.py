from datetime import date

from odoo import Command
from odoo.addons.l10n_in.tests.common import L10nInTestInvoicingCommon
from odoo.tests import tagged

TEST_DATE = date(2025, 6, 8)


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestGstrSection(L10nInTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.partner_b.l10n_in_gst_treatment = "regular"
        cls.partner_foreign.l10n_in_gst_treatment = 'overseas'
        cls.sez_partner = cls.partner_a.copy({"l10n_in_gst_treatment": "special_economic_zone"})
        cls.large_unregistered_partner = cls.partner_a.copy({"state_id": cls.state_in_mh.id, "vat": None, "l10n_in_gst_treatment": "unregistered"})

        ChartTemplate = cls.env['account.chart.template']
        cls.nil_rated_tax = ChartTemplate.ref('nil_rated_sale')
        cls.igst_lut_sale_28_sez = ChartTemplate.ref('igst_sale_28_sez_lut')
        cls.igst_rc_sale_18 = ChartTemplate.ref('igst_sale_18_rc')
        cls.igst_exp_sale_18 = ChartTemplate.ref('igst_sale_18_sez_exp')

    def test_gstr_sections(self):
        def assert_line_sections(lines, expected_sections):
            for line in lines.filtered(lambda l: l.display_type in ('product', 'tax')):
                if line.display_type == 'product':
                    tax_types = {tax.l10n_in_tax_type for tax in line.tax_ids}
                    matched = tax_types & expected_sections.keys()
                    if matched:
                        expected = expected_sections[matched.pop()]
                    else:
                        expected = expected_sections.get('with_gst_tag')
                else:  # tax line
                    expected = expected_sections['with_gst_tag'] if line.tax_tag_ids else expected_sections['no_tag']
                self.assertEqual(line.l10n_in_gstr_section, expected)

        # SEZ without payment with Nil Rated
        sez_invoice = self._init_inv(
            partner=self.sez_partner,
            taxes=self.igst_lut_sale_28_sez,
            line_vals={'price_unit': 1000, 'quantity': 1},
            post=False,
            invoice_date=TEST_DATE,
        )
        sez_invoice.write({
            'invoice_line_ids': [Command.create({
                'product_id': self.product_b.id,
                'account_id': sez_invoice.invoice_line_ids[0].account_id.id,
                'price_unit': 500,
                'quantity': 1,
                'tax_ids': [(6, 0, [self.nil_rated_tax.id])],
            })],
        })
        sez_invoice.action_post()
        assert_line_sections(sez_invoice.line_ids, {
            'with_gst_tag': 'sale_sez_wop',
            'nil_rated': 'sale_nil_rated',
            'no_tag': 'sale_out_of_scope',
        })

        sez_credit_note = self._create_credit_note(inv=sez_invoice)
        assert_line_sections(sez_credit_note.line_ids, {
            'with_gst_tag': 'sale_cdnr_sez_wop',
            'nil_rated': 'sale_nil_rated',
            'no_tag': 'sale_out_of_scope',
        })

        # Export with payment
        exp_invoice = self._init_inv(
            partner=self.partner_foreign,
            taxes=self.igst_exp_sale_18,
            line_vals={'price_unit': 3000, 'quantity': 1},
            invoice_date=TEST_DATE,
        )
        assert_line_sections(exp_invoice.line_ids, {
            'with_gst_tag': 'sale_exp_wp',
            'no_tag': 'sale_out_of_scope',
        })

        exp_credit_note = self._create_credit_note(inv=exp_invoice)
        assert_line_sections(exp_credit_note.line_ids, {
            'with_gst_tag': 'sale_cdnur_exp_wp',
            'no_tag': 'sale_out_of_scope',
        })

        # B2B RCM
        b2b_rcm_invoice = self._init_inv(
            partner=self.partner_b,
            taxes=self.igst_rc_sale_18,
            line_vals={'price_unit': 1000, 'quantity': 1},
            invoice_date=TEST_DATE,
        )
        assert_line_sections(b2b_rcm_invoice.line_ids, {
            'with_gst_tag': 'sale_b2b_rcm',
            'no_tag': 'sale_out_of_scope',
        })

        b2b_rcm_credit_note = self._create_credit_note(inv=b2b_rcm_invoice)
        assert_line_sections(b2b_rcm_credit_note.line_ids, {
            'with_gst_tag': 'sale_cdnr_rcm',
            'no_tag': 'sale_out_of_scope',
        })

        # B2CL
        b2cl_invoice = self._init_inv(
            partner=self.large_unregistered_partner,
            taxes=self.igst_sale_18,
            line_vals={'price_unit': 220000, 'quantity': 1},
            invoice_date=TEST_DATE,
        )
        assert_line_sections(b2cl_invoice.line_ids, {
            'with_gst_tag': 'sale_b2cl',
            'no_tag': 'sale_out_of_scope',
        })

        b2cl_credit_note = self._create_credit_note(inv=b2cl_invoice, line_vals={'quantity': 0.5})
        assert_line_sections(b2cl_credit_note.line_ids, {
            'with_gst_tag': 'sale_cdnur_b2cl',
            'no_tag': 'sale_out_of_scope',
        })
