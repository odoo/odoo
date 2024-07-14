# -*- coding: utf-8 -*-
from unittest.mock import patch

from odoo import fields
from odoo.addons.account_reports.tests.common import TestAccountReportsCommon
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestItalianTaxReport(TestAccountReportsCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref='it'):
        super().setUpClass(chart_template_ref=chart_template_ref)
        company = cls.company_data["company"]
        AccountTax = cls.env['account.tax']
        company.update({
            'vat': 'IT78926680725',
            'country_id': cls.env.ref('base.it').id,
        })

        cls.tax_4a = cls.env.ref(f'account.{cls.env.company.id}_4am')
        cls.tax_4a.active = True
        cls.tax_4v = cls.env.ref(f'account.{cls.env.company.id}_4v')
        cls.tax_4v.tax_group_id.tax_payable_account_id = cls.company_data['default_account_payable']
        cls.tax_4v.active = True

        cls.l10n_it_tax_report_partner = cls.env['res.partner'].create({
            'name': 'Blue Interior',
            'is_company': 1,
            'street': 'Via Tenebrosa 66',
            'city': 'Milan',
            'zip': '00000',
            'phone': '029310505',
            'vat': '02730480965',
            'country_id': cls.env.ref('base.it').id,
            'email': 'blue.Interior24@example.it',
            'website': 'http://www.blue-interior.it'
        })

        cls.report = cls.env.ref('l10n_it.tax_report_vat')

    def test_tax_report_carryover_vp14_credit_period(self):
        """
        Test to have a value in line vp14 credit at a period inside the year.
        In this case, we should put that value in line vp8.
        """
        self._test_line_report_carryover(
            '2015-03-10',
            1000,
            self.tax_4a,
            self._generate_options(
                self.report,
                fields.Date.from_string('2015-03-01'),
                fields.Date.from_string('2015-03-31')),
            self._generate_options(
                self.report,
                fields.Date.from_string('2015-04-01'),
                fields.Date.from_string('2015-04-30')),
            'VP8',
            40.0)

    def test_tax_report_carryover_vp14_credit_year(self):
        """
        Test to have a value in line vp14 credit at the last period of the year.
        In this case, we should put that value in line vp9.
        """
        self._test_line_report_carryover(
            '2015-12-10',
            1000,
            self.tax_4a,
            self._generate_options(
                self.report,
                fields.Date.from_string('2015-12-01'),
                fields.Date.from_string('2015-12-31')),
            self._generate_options(
                self.report,
                fields.Date.from_string('2016-01-01'),
                fields.Date.from_string('2016-01-30')),
            'VP9',
            40.0)

    def test_tax_report_carryover_vp14_debit_valid(self):
        """
        Test to have a value in line vp14 debit between 0 and 25.82.
        In this case, we should put that value in line vp7.
        """
        self._test_line_report_carryover(
            '2015-05-10',
            500,
            self.tax_4v,
            self._generate_options(
                self.report,
                fields.Date.from_string('2015-05-01'),
                fields.Date.from_string('2015-05-31')),
            self._generate_options(
                self.report,
                fields.Date.from_string('2015-06-01'),
                fields.Date.from_string('2015-06-30')),
            'VP7',
            20.0)

    def test_tax_report_carryover_vp14_debit_invalid(self):
        """
        Test to have a value in line vp14 debit > 25.82.
        In this case, we should never put that value in line vp7.
        """
        self._test_line_report_carryover(
            '2015-05-10',
            1000,
            self.tax_4v,
            self._generate_options(
                self.report,
                fields.Date.from_string('2015-05-01'),
                fields.Date.from_string('2015-05-31')),
            self._generate_options(
                self.report,
                fields.Date.from_string('2015-06-01'),
                fields.Date.from_string('2015-06-30')),
            'VP7',
            0.0)

    def test_tax_report_carryover_vp14_debit_valid_reset(self):
        """
        Test to have a value in line vp14 that would trigger a carryover, then another one added at the second period
        to be out of bound.
        In this case, we should see the carryover back to 0 after the second month.
        """
        self._test_line_report_carryover(
            '2015-05-10',
            500,
            self.tax_4v,
            self._generate_options(
                self.report,
                fields.Date.from_string('2015-05-01'),
                fields.Date.from_string('2015-05-31')),
            self._generate_options(
                self.report,
                fields.Date.from_string('2015-06-01'),
                fields.Date.from_string('2015-06-30')),
            'VP7',
            20.0)
        self._test_line_report_carryover(
            '2015-06-10',
            500,
            self.tax_4v,
            self._generate_options(
                self.report,
                fields.Date.from_string('2015-06-01'),
                fields.Date.from_string('2015-06-30')),
            self._generate_options(
                self.report,
                fields.Date.from_string('2015-07-01'),
                fields.Date.from_string('2015-07-30')),
            'VP7',
            0.0)

    def _test_line_report_carryover(self, invoice_date, invoice_amount, tax_line,
                                    first_month_options, second_month_options,
                                    target_line_code, target_line_value):
        def _get_attachment(*args, **kwargs):
            return []

        invoice = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.l10n_it_tax_report_partner.id,
            'date': invoice_date,
            'invoice_date': invoice_date,
            'invoice_line_ids': [
                (0, 0, {
                    'name': 'Product A',
                    'account_id': self.company_data['default_account_revenue'].id,
                    'price_unit': invoice_amount,
                    'quantity': 1,
                    'tax_ids': tax_line,
                }),
            ],
        })
        invoice.action_post()

        self.env.flush_all()

        with patch.object(type(self.env['account.move']), '_get_vat_report_attachments', autospec=True, side_effect=_get_attachment):
            vat_closing_move = self.env['account.generic.tax.report.handler']._generate_tax_closing_entries(self.report, first_month_options)
            vat_closing_move.action_post()

            # Get to the next month
            report_lines = self.report._get_lines(second_month_options)
            line = [line for line in report_lines if target_line_code in line['name']][0]

            self.assertEqual(line['columns'][0]['no_format'], target_line_value)
