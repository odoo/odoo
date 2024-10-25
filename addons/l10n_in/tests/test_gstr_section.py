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
        cls.igst_lut_sale_28 = ChartTemplate.ref('igst_sale_28_sez_exp_lut')
        cls.igst_rc_sale_18 = ChartTemplate.ref('igst_sale_18_rc')
        cls.igst_exp_sale_18 = ChartTemplate.ref('igst_sale_18_sez_exp')

        cls.igst_base_lut_tag = cls.env.ref('l10n_in.tax_tag_base_igst_lut')
        cls.igst_tag = cls.env.ref('l10n_in.tax_tag_igst')
        cls.nil_rated_tag = cls.env.ref('l10n_in.tax_tag_nil_rated')

    def test_gstr_sections(self):
        def assert_sections(lines, expected):
            for line in lines.filtered(lambda l: l.display_type in ('product, tax')):
                expected_section = expected.get(line.tax_tag_ids, 'sale_out_of_scope')
                self.assertEqual(line.l10n_in_gstr_section, expected_section)

        # SEZ without payment with Nil Rated
        sez_invoice = self._init_inv(
            partner=self.sez_partner,
            taxes=self.igst_lut_sale_28,  # IGST LUT Tax
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
                'tax_ids': [(6, 0, [self.nil_rated_tax.id])],  # Nil Rated Tax
            })],
        })
        sez_invoice.action_post()
        assert_sections(sez_invoice.line_ids, {
            self.igst_base_lut_tag: 'sale_sez_wop',
            self.nil_rated_tag: 'sale_nil_rated',
        })

        sez_credit_note = self._create_credit_note(inv=sez_invoice)
        assert_sections(sez_credit_note.line_ids, {
            self.igst_base_lut_tag: 'sale_cdnr_sez_wop',
            self.nil_rated_tag: 'sale_nil_rated',
        })

        # Export with payment
        exp_invoice = self._init_inv(
            partner=self.partner_foreign,
            taxes=self.igst_exp_sale_18,
            line_vals={'price_unit': 3000, 'quantity': 1},
            invoice_date=TEST_DATE,
        )
        assert_sections(exp_invoice.line_ids, {
            line.tax_tag_ids: 'sale_exp_wp' for line in exp_invoice.line_ids if line.tax_tag_ids
        })

        exp_credit_note = self._create_credit_note(inv=exp_invoice)
        assert_sections(exp_credit_note.line_ids, {
            line.tax_tag_ids: 'sale_cdnur_exp_wp' for line in exp_credit_note.line_ids if line.tax_tag_ids
        })

        # B2B RCM
        b2b_rcm_invoice = self._init_inv(
            partner=self.partner_b,
            taxes=self.igst_rc_sale_18,
            line_vals={'price_unit': 1000, 'quantity': 1},
            invoice_date=TEST_DATE,
        )
        assert_sections(b2b_rcm_invoice.line_ids, {
            line.tax_tag_ids: 'sale_b2b_rcm' for line in b2b_rcm_invoice.line_ids if line.tax_tag_ids
        })

        b2b_rcm_credit_note = self._create_credit_note(inv=b2b_rcm_invoice)
        assert_sections(b2b_rcm_credit_note.line_ids, {
            line.tax_tag_ids: 'sale_cdnr_rcm' for line in b2b_rcm_credit_note.line_ids if line.tax_tag_ids
        })

        # B2CL
        b2cl_invoice = self._init_inv(
            partner=self.large_unregistered_partner,
            taxes=self.igst_sale_18,
            line_vals={'price_unit': 220000, 'quantity': 1},
            invoice_date=TEST_DATE,
        )
        assert_sections(b2cl_invoice.line_ids, {
            line.tax_tag_ids: 'sale_b2cl' for line in b2cl_invoice.line_ids if line.tax_tag_ids
        })

        b2cl_credit_note = self._create_credit_note(inv=b2cl_invoice, line_vals={'quantity': 0.5})
        assert_sections(b2cl_credit_note.line_ids, {
            line.tax_tag_ids: 'sale_cdnur_b2cl' for line in b2cl_credit_note.line_ids if line.tax_tag_ids
        })
