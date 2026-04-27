# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests import tagged
import logging
import json
from dateutil.relativedelta import relativedelta

from odoo.addons.l10n_in_reports_gstr.tests.common import L10nInTestAccountGstReportsCommon

_logger = logging.getLogger(__name__)

@tagged('post_install_l10n', 'post_install', '-at_install')
class TestReports(L10nInTestAccountGstReportsCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.partner_b.l10n_in_gst_treatment = "regular"
        cls.partner_foreign.l10n_in_gst_treatment = "overseas"

        cls.fully_matched_bill = cls._init_inv(move_type='in_invoice', ref='INV/001', taxes=cls.comp_igst_18, partner=cls.partner_b)
        cls.fully_matched_bill_refund = cls._create_credit_note(inv=cls.fully_matched_bill, ref='CR/001')

        cls.bill_with_conflict_date = cls._init_inv(move_type='in_invoice', ref='INV/002', taxes=cls.comp_igst_18, partner=cls.partner_b)

        cls.bill_with_conflict_amount = cls._init_inv(move_type='in_invoice', ref='INV/003', taxes=cls.comp_igst_18, partner=cls.partner_b)

        cls.bill_with_conflict_date_amount = cls._init_inv(move_type='in_invoice', ref='INV/004', taxes=cls.comp_igst_18, partner=cls.partner_b)

        cls.bill_with_conflict_type = cls._init_inv(move_type='in_invoice', ref='INV/005', taxes=cls.comp_igst_18, partner=cls.partner_b)
        cls.bill_with_conflict_type_date = cls._create_credit_note(inv=cls.bill_with_conflict_type, ref='CR/002')

        cls.bill_with_conflict_type_amount = cls._init_inv(move_type='in_invoice', ref='INV/006', taxes=cls.comp_igst_18, partner=cls.partner_b)
        cls.bill_with_conflict_type_date_amount = cls._create_credit_note(ref='CR/003', inv=cls.bill_with_conflict_type)

        cls.bill_with_conflict_vat = cls._init_inv(move_type='in_invoice', ref='INV/007', taxes=cls.comp_igst_18, partner=cls.partner_a)

        cls.bill_with_conflict_vat_date = cls._init_inv(move_type='in_invoice', ref='INV/008', taxes=cls.comp_igst_18, partner=cls.partner_a)

        cls.bill_with_conflict_vat_amount = cls._init_inv(move_type='in_invoice', ref='INV/009', taxes=cls.comp_igst_18, partner=cls.partner_a)

        cls.bill_with_conflict_vat_date_amount = cls._init_inv(move_type='in_invoice', ref='INV/010', taxes=cls.comp_igst_18, partner=cls.partner_a)

        cls.bill_with_conflict_vat_type = cls._init_inv(move_type='in_invoice', ref='INV/011', taxes=cls.comp_igst_18, partner=cls.partner_a)

        cls.bill_with_conflict_vat_type_date = cls._create_credit_note(ref='CR/004', inv=cls.bill_with_conflict_type)

        cls.bill_with_conflict_vat_type_amount = cls._init_inv(move_type='in_invoice', ref='INV/012', taxes=cls.comp_igst_18, partner=cls.partner_a)

        cls.bill_with_conflict_vat_type_date_amount = cls._create_credit_note(ref='CR/005', inv=cls.bill_with_conflict_type)

        cls.bill_with_conflict_ref = cls._init_inv(move_type='in_invoice', partner=cls.partner_b, taxes=cls.comp_igst_18, line_vals={'price_unit': 2000})

        cls.bill_not_in_gstr2b = cls.bill_with_conflict_ref = cls._init_inv(move_type='in_invoice', ref='INV/404', taxes=cls.comp_igst_18, partner=cls.partner_b)

        cls.overseas_bill = cls.bill_with_conflict_ref = cls._init_inv(move_type='in_invoice', ref='BOE/123', taxes=cls.comp_igst_18, partner=cls.partner_foreign, line_vals={'price_unit': 100000})

        cls.bill_with_no_tax = cls._init_inv(
            "in_invoice",
            products=cls.product_a,
            partner=cls.partner_b,
            ref='BILL/NO_TAX',
            post=False,
        )
        cls.bill_with_no_tax.line_ids.tax_ids.unlink()
        cls.bill_with_no_tax.action_post()
        cls.report = cls.gstr_report = cls.env['l10n_in.gst.return.period'].create({
            'company_id': cls.default_company.id,
            'periodicity': 'monthly',
            'year': cls.test_date.strftime('%Y'),
            'month': cls.test_date.strftime('%m'),
        })

    def test_gstr2b(self):

        gstr2b_json = self._read_mock_json('gstr2b_response.json')
        self.report.gstr2b_json_from_portal_ids = self.env['ir.attachment'].create({
            'name': 'gstr2b.json',
            'mimetype': 'application/json',
            'raw': json.dumps(gstr2b_json),
        })
        self.report.gstr2b_match_data()

        self.assertEqual(self.report.gstr2b_status, "partially_matched")
        self.assertEqual(self.fully_matched_bill.l10n_in_gstr2b_reconciliation_status, "matched")
        self.assertEqual(bool(self.fully_matched_bill.l10n_in_exception), False)
        self.assertEqual(self.fully_matched_bill_refund.l10n_in_gstr2b_reconciliation_status, "matched")
        self.assertEqual(self.bill_with_conflict_date.l10n_in_gstr2b_reconciliation_status, "partially_matched")
        self.assertEqual(self.bill_with_conflict_amount.l10n_in_gstr2b_reconciliation_status, "partially_matched")
        self.assertEqual(self.bill_with_conflict_date_amount.l10n_in_gstr2b_reconciliation_status, "partially_matched")

        self.assertEqual(self.bill_with_conflict_type.l10n_in_gstr2b_reconciliation_status, "partially_matched")
        self.assertEqual(self.bill_with_conflict_type_date.l10n_in_gstr2b_reconciliation_status, "partially_matched")
        self.assertEqual(self.bill_with_conflict_type_amount.l10n_in_gstr2b_reconciliation_status, "partially_matched")
        self.assertEqual(self.bill_with_conflict_type_date_amount.l10n_in_gstr2b_reconciliation_status, "partially_matched")

        self.assertEqual(self.bill_with_conflict_vat.l10n_in_gstr2b_reconciliation_status, "partially_matched")
        self.assertEqual(self.bill_with_conflict_vat_date.l10n_in_gstr2b_reconciliation_status, "partially_matched")
        self.assertEqual(self.bill_with_conflict_vat_amount.l10n_in_gstr2b_reconciliation_status, "partially_matched")
        self.assertEqual(self.bill_with_conflict_vat_date_amount.l10n_in_gstr2b_reconciliation_status, "partially_matched")

        self.assertEqual(self.bill_with_conflict_vat_type.l10n_in_gstr2b_reconciliation_status, "partially_matched")
        self.assertEqual(self.bill_with_conflict_vat_type_date.l10n_in_gstr2b_reconciliation_status, "partially_matched")
        self.assertEqual(self.bill_with_conflict_vat_type_amount.l10n_in_gstr2b_reconciliation_status, "partially_matched")
        self.assertEqual(self.bill_with_conflict_vat_type_date_amount.l10n_in_gstr2b_reconciliation_status, "partially_matched")

        self.assertEqual(self.bill_not_in_gstr2b.l10n_in_gstr2b_reconciliation_status, "bills_not_in_gstr2")
        self.assertEqual(self.overseas_bill.l10n_in_gstr2b_reconciliation_status, "matched")
        bill_not_in_odoo = self.env['account.move'].search([('ref', '=', '533515'), ('company_id', '=', self.default_company.id)])
        self.assertEqual(len(bill_not_in_odoo), 1)
        self.assertEqual(bill_not_in_odoo.l10n_in_gstr2b_reconciliation_status, 'gstr2_bills_not_in_odoo')
        self.assertEqual(bill_not_in_odoo.l10n_in_gst_treatment, 'regular')
        sez_bill = self.env['account.move'].search([('ref', '=', 'SEZ/123'), ('company_id', '=', self.default_company.id)])
        self.assertEqual(len(sez_bill), 1)
        self.assertEqual(sez_bill.l10n_in_gstr2b_reconciliation_status, "gstr2_bills_not_in_odoo")
        self.assertEqual(bool(sez_bill.l10n_in_exception), False)
        self.assertEqual(sez_bill.l10n_in_gst_treatment, "special_economic_zone")

        self.assertRecordValues(
            self.bill_with_no_tax,
            [{
                'l10n_in_gst_return_period_id': False,
                'l10n_in_gstr2b_reconciliation_status': 'pending',  # Default value
            }]
        )

    def test_gstr2b_late_reconciliation(self):
        """
        Test the GSTR-2B reconciliation process for late received invoices.

        This test verifies that when an invoice arrives with a previous month's date
        but differs from an existing invoice date, the original invoice remains unchanged.
        """
        previous_invoice = self._init_inv(move_type='in_invoice', ref='BILL/001', taxes=self.comp_igst_18, partner=self.partner_b, invoice_date=self.test_date - relativedelta(months=1), line_vals={'price_unit': 100})
        gstr2b_late_reconciliation_data = self._read_mock_json('gstr2b_late_reconciliation_data.json')
        self.report.gstr2b_json_from_portal_ids = self.env['ir.attachment'].create({
            'name': 'gstr2b.json',
            'mimetype': 'application/json',
            'raw': json.dumps(gstr2b_late_reconciliation_data),
        })
        self.report.gstr2b_match_data()

        self.assertEqual(previous_invoice.l10n_in_gstr2b_reconciliation_status, "matched")
        self.assertFalse(previous_invoice.l10n_in_exception)
        self.assertEqual(previous_invoice.l10n_in_gst_return_period_id, self.report)

    def test_gstr2b_reconciliation_different_partner(self):
        """
        Test the GSTR-2B reconciliation process for invoices with different partners.

        This test verifies that when multiple invoices with the same reference
        but different partners are processed, they are correctly matched, and
        a new bill is created for any additional invoice found in the GSTR-2B data.

        The test checks that:
        - Three invoices are matched (two existing, one new).
        - Both bills with different partners are marked as 'matched'.
        - A new bill is created and labeled as 'gstr2_bills_not_in_odoo' for
        invoices found in the GSTR-2B data but not present in Odoo.
        """
        bill_with_partner_b = self._init_inv(move_type='in_invoice', ref='BILL/001', taxes=self.comp_igst_18, partner=self.partner_b, invoice_date=self.test_date, line_vals={'price_unit': 800})
        partner_c = self.partner_b.copy({'name': 'Partner_c', 'vat': '24WXYZM1234E1ZE'})
        bill_with_partner_c = self._init_inv(move_type='in_invoice', ref='BILL/001', taxes=self.comp_igst_18, partner=partner_c, invoice_date=self.test_date, line_vals={'price_unit': 800})
        gstr2b_reconciliation_different_partner = self._read_mock_json('gstr2b_reconciliation_different_partner.json')
        self.report.gstr2b_json_from_portal_ids = self.env['ir.attachment'].create({
            'name': 'gstr2b.json',
            'mimetype': 'application/json',
            'raw': json.dumps(gstr2b_reconciliation_different_partner),
        })

        self.report.gstr2b_match_data()
        matched_invoices = self.env['account.move'].search([('ref', '=', 'BILL/001'), ('company_id', '=', self.company_data['company'].id)])
        self.assertEqual(len(matched_invoices), 3)
        self.assertEqual(bill_with_partner_b.l10n_in_gstr2b_reconciliation_status, "matched")
        self.assertEqual(bill_with_partner_c.l10n_in_gstr2b_reconciliation_status, "matched")

        new_bill = matched_invoices - bill_with_partner_b - bill_with_partner_c
        self.assertEqual(new_bill.l10n_in_gstr2b_reconciliation_status, "gstr2_bills_not_in_odoo")

    def test_bill_status_and_exception_reset_on_draft(self):
        gstr2b_draft_bill_response = self._read_mock_json('gstr2b_draft_bill_response.json')
        self.report.gstr2b_json_from_portal_ids = self.env['ir.attachment'].create({
            'name': 'gstr2b.json',
            'mimetype': 'application/json',
            'raw': json.dumps(gstr2b_draft_bill_response),
        })
        self.report.gstr2b_match_data()
        self.assertEqual(self.fully_matched_bill.l10n_in_gstr2b_reconciliation_status, "partially_matched")
        self.assertEqual(bool(self.fully_matched_bill.l10n_in_exception), True)

        self.fully_matched_bill.button_draft()
        self.assertEqual(self.fully_matched_bill.l10n_in_gstr2b_reconciliation_status, "pending")
        self.assertEqual(self.fully_matched_bill.l10n_in_gst_return_period_id.id, False)
        self.assertEqual(self.fully_matched_bill.l10n_in_exception, False)
