# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
from datetime import date

from odoo import Command
from odoo.tests import tagged

from odoo.addons.l10n_in_reports_gstr.tests.common import L10nInTestAccountGstReportsCommon

_logger = logging.getLogger(__name__)

HSN_CHANGE_TEST_DATE = date(2025, 5, 11)


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestReports(L10nInTestAccountGstReportsCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.partner_b.l10n_in_gst_treatment = "regular"

        cls.consumer_partner = cls.partner_a.copy({
            'vat': None,
            'l10n_in_gst_treatment': "consumer",
        })

        cls.deemed_export_partner = cls.partner_a.copy({"l10n_in_gst_treatment": "deemed_export"})
        cls.composition_partner = cls.partner_a.copy({"l10n_in_gst_treatment": "composition"})
        cls.uin_holders_partner = cls.partner_a.copy({"l10n_in_gst_treatment": "uin_holders"})
        cls.large_unregistered_partner = cls.consumer_partner.copy({"state_id": cls.state_in_mh.id, "l10n_in_gst_treatment": "unregistered"})

        cls.partner_foreign.l10n_in_gst_treatment = "overseas"

        cls.comp_sgst_18 = cls._get_company_tax('sgst_sale_18')
        cls.comp_export_wp = cls._get_company_tax('igst_sale_18_sez_exp')
        cls.comp_export_wop = cls._get_company_tax('igst_sale_18_sez_lut')
        cls.exempt_tax = cls._get_company_tax('exempt_sale')
        cls.nil_rated_tax = cls._get_company_tax('nil_rated_sale')
        cls.non_gst_supplies = cls._get_company_tax('non_gst_supplies_sale')

    def _setup_moves(self, reverse_inv_func, invoice_date=False):
        if not invoice_date:
            invoice_date = self.test_date
        b2b_invoice = self._init_inv(partner=self.partner_b, taxes=self.comp_igst_18, line_vals={'price_unit': 500, 'quantity': 2}, invoice_date=invoice_date)
        reverse_inv_func(inv=b2b_invoice, line_vals={'quantity': 1})

        b2b_intrastate_invoice = self._init_inv(partner=self.partner_a, taxes=self.comp_sgst_18, line_vals={'price_unit': 500, 'quantity': 2}, invoice_date=invoice_date)
        reverse_inv_func(inv=b2b_intrastate_invoice, line_vals={'quantity': 1})

        b2c_intrastate_invoice = self._init_inv(partner=self.consumer_partner, taxes=self.comp_sgst_18, line_vals={'price_unit': 500, 'quantity': 2}, invoice_date=invoice_date)
        reverse_inv_func(inv=b2c_intrastate_invoice, line_vals={'quantity': 1})

        b2cl_invoice = self._init_inv(partner=self.large_unregistered_partner, taxes=self.comp_igst_18, line_vals={'price_unit': 250000, 'quantity': 1}, invoice_date=invoice_date)
        reverse_inv_func(inv=b2cl_invoice, line_vals={'quantity': 0.5})

        export_invoice = self._init_inv(partner=self.partner_foreign, taxes=self.comp_igst_18, line_vals={'price_unit': 500, 'quantity': 2}, invoice_date=invoice_date)
        reverse_inv_func(inv=export_invoice, line_vals={'quantity': 1})

        b2b_invoice_nilratedtax = self._init_inv(partner=self.partner_b, taxes=self.nil_rated_tax, line_vals={'price_unit': 500, 'quantity': 2}, invoice_date=invoice_date)
        reverse_inv_func(inv=b2b_invoice_nilratedtax, line_vals={'quantity': 1})

        b2b_invoice_exemptedtax = self._init_inv(partner=self.partner_b, taxes=self.exempt_tax, line_vals={'price_unit': 500, 'quantity': 2}, invoice_date=invoice_date)
        reverse_inv_func(inv=b2b_invoice_exemptedtax, line_vals={'quantity': 1})

        b2b_invoice_nongsttax = self._init_inv(partner=self.partner_b, taxes=self.non_gst_supplies, line_vals={'price_unit': 500, 'quantity': 2}, invoice_date=invoice_date)
        reverse_inv_func(inv=b2b_invoice_nongsttax, line_vals={'quantity': 1})

        b2b_invoice_deemed_export = self._init_inv(partner=self.deemed_export_partner, taxes=self.comp_igst_18, line_vals={'price_unit': 500, 'quantity': 2}, invoice_date=invoice_date)
        reverse_inv_func(inv=b2b_invoice_deemed_export, line_vals={'quantity': 1})  # Creates and posts credit note for the above invoice

        b2b_invoice_composition = self._init_inv(partner=self.composition_partner, taxes=self.comp_igst_18, line_vals={'price_unit': 500, 'quantity': 2}, invoice_date=invoice_date)
        reverse_inv_func(inv=b2b_invoice_composition, line_vals={'quantity': 1})

        b2b_invoice_uin_holders = self._init_inv(partner=self.uin_holders_partner, taxes=self.comp_igst_18, line_vals={'price_unit': 500, 'quantity': 2}, invoice_date=invoice_date)
        reverse_inv_func(inv=b2b_invoice_uin_holders, line_vals={'quantity': 1})

        # if no tax is applied then it will be out of scope and not considered in GSTR1
        self._init_inv(partner=self.partner_b, taxes=[], line_vals={'price_unit': 500, 'quantity': 2}, invoice_date=invoice_date)

        # for b2b invoice with 2 invoice_line_ids having different taxes
        b2b_invoice_gst_and_nil_rated_tax = self._init_inv(partner=self.partner_b, taxes=self.nil_rated_tax, line_vals={'price_unit': 700, 'quantity': 2}, post=False, invoice_date=invoice_date)
        existing_line_vals = b2b_invoice.invoice_line_ids[0].read(['product_id', 'account_id', 'price_unit', 'quantity', 'tax_ids'])[0]
        b2b_invoice_gst_and_nil_rated_tax.write({
            'invoice_line_ids': [
                Command.create({
                    'product_id': existing_line_vals['product_id'][0],
                    'account_id': existing_line_vals['account_id'][0],
                    'price_unit': existing_line_vals['price_unit'],
                    'quantity': existing_line_vals['quantity'],
                    'tax_ids': [(6, 0, existing_line_vals['tax_ids'])],
                })
            ]
        })
        b2b_invoice_gst_and_nil_rated_tax.action_post()

        # b2b invoice with special economic zone
        b2b_sez_invoice_gst_and_nil_rated_tax = b2b_invoice_gst_and_nil_rated_tax.copy(default={'l10n_in_gst_treatment': 'special_economic_zone', 'invoice_date': invoice_date})
        b2b_sez_invoice_gst_and_nil_rated_tax.action_post()

        # Export invoices with and without payment of IGST
        export_invoice_wp = self._init_inv(partner=self.partner_foreign, taxes=self.comp_export_wp, line_vals={'price_unit': 500, 'quantity': 2}, invoice_date=invoice_date)
        reverse_inv_func(inv=export_invoice_wp, line_vals={'quantity': 1})

        export_invoice_wop = self._init_inv(partner=self.partner_foreign, taxes=self.comp_export_wop, line_vals={'price_unit': 500, 'quantity': 2}, invoice_date=invoice_date)
        reverse_inv_func(inv=export_invoice_wop, line_vals={'quantity': 1})

    def _create_gstr_report(self, company=None, periodicity='monthly', year=None, month=None):
        return self.env['l10n_in.gst.return.period'].create({
            'company_id': (company or self.default_company).id,
            'periodicity': periodicity,
            'year': year or self.test_date.strftime('%Y'),
            'month': month or self.test_date.strftime('%m'),
        })

    def test_gstr1_json(self):
        self._setup_moves(self._create_credit_note)
        gstr_report = self._create_gstr_report()
        gstr1_expected_json = self._read_mock_json('gstr1_expected_response.json')
        self.assertDictEqual(gstr_report._get_gstr1_json(), gstr1_expected_json)

    def test_gstr1_debit_note_json(self):
        self._setup_moves(self._create_debit_note)
        gstr_report = self._create_gstr_report()
        gstr1_debit_note_expected_json = self._read_mock_json('gstr1_debit_note_expected_response.json')
        self.assertDictEqual(gstr_report._get_gstr1_json(), gstr1_debit_note_expected_json)

    def test_gstr1_credit_note_warning_pre_and_post_november(self):
        invoice_1 = self._init_inv(partner=self.partner_a, taxes=self.comp_igst_18, line_vals={'price_unit': 500, 'quantity': 2}, invoice_date=date(2022, 8, 1))

        # Case 1: Credit note created after 30th November (December 20, 2023)
        # Expected: The warning should be displayed since the credit note is created after the November 30th of invoice financial year.
        reversed_move_1 = self._create_credit_note(inv=invoice_1, line_vals={'quantity': 1}, credit_note_date=date(2023, 12, 20), post=False)
        self.assertTrue(reversed_move_1.l10n_in_reversed_entry_warning)

        # Case 2: Credit note created before 30th November (August 1, 2023)
        # Expected: The warning should not be displayed since the credit note is created before the November 30th of invoice financial year.
        reversed_move_2 = self._create_credit_note(inv=invoice_1, line_vals={'quantity': 1}, credit_note_date=date(2023, 8, 1), post=False)
        self.assertFalse(reversed_move_2.l10n_in_reversed_entry_warning)

    def test_gstr1_sez_zero_rated_tax(self):
        b2b_invoice = self._init_inv(
            partner=self.partner_a.copy({'l10n_in_gst_treatment': 'special_economic_zone'}),
            taxes=self._get_company_tax('igst_sale_0'),
            line_vals={'price_unit': 500, 'quantity': 2}
        )
        self._init_inv(
            partner=self.partner_foreign,
            taxes=self._get_company_tax('igst_sale_0'),
            line_vals={'price_unit': 500, 'quantity': 2}
        )
        self._create_credit_note(inv=b2b_invoice, line_vals={'quantity': 1})  # Creates and posts credit note for the above invoice
        gstr1_report = self._create_gstr_report()
        gstr1_json = gstr1_report._get_gstr1_json()
        self.assertDictEqual(gstr1_json, self._read_mock_json('gstr1_sez_zero_rated_expected_response.json'))

    def test_hsn_schema_change_gstr1_json(self):
        self._setup_moves(self._create_credit_note, invoice_date=HSN_CHANGE_TEST_DATE)
        gstr1_report = self._create_gstr_report(
            year=HSN_CHANGE_TEST_DATE.strftime('%Y'),
            month=HSN_CHANGE_TEST_DATE.strftime('%m')
        )
        gstr1_json = gstr1_report._get_gstr1_json()
        self.assertDictEqual(gstr1_json, self._read_mock_json('gstr1_new_hsn_schema_response.json'))

    def test_taxes_with_sez_exp_lut_and_rcm(self):
        self.invoice_with_sez_lut.invoice_date = self.test_date
        self.invoice_with_sez_lut.action_post()
        self.invoice_with_rcm.invoice_date = self.test_date
        self.invoice_with_rcm.action_post()
        gstr1_report = self._create_gstr_report()
        gstr1_json = gstr1_report._get_gstr1_json()
        self.assertDictEqual(gstr1_json, self._read_mock_json('gstr1_sez_lut_and_rcm_response.json'))
