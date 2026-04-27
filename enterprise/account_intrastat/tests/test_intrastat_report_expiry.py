# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.account_reports.tests.common import TestAccountReportsCommon
from odoo.tests import tagged
from odoo import fields, Command
from freezegun import freeze_time


@tagged('post_install', '-at_install')
class IntrastatExpiryReportTest(TestAccountReportsCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        values = [
            {
                'type': type,
                'name': f'{type}-{date[0]}',
                'start_date': date[1],
                'expiry_date': date[2],
            } for type in (
                'commodity',
                'transaction',
            ) for date in (
                ('no_date', False, False),
                ('expired', False, '2000-01-01'),
                ('premature', '2030-01-01', False),
            )
        ]
        cls.intrastat_codes = {}
        cls.env.company.totals_below_sections = False
        for i, vals in enumerate(values, 100):
            vals['code'] = str(i)
            cls.intrastat_codes[vals['name']] = cls.env['account.intrastat.code'].sudo().create(vals)

        cls.company_data['company'].country_id = cls.env.ref('base.be')

        cls.product_c = cls.env['product.product'].create({
            'name': 'product_c',
            'uom_id': cls.env.ref('uom.product_uom_unit').id,
            'lst_price': 1000.0,
            'standard_price': 800.0,
            'property_account_income_id': cls.company_data['default_account_revenue'].id,
            'property_account_expense_id': cls.company_data['default_account_expense'].id,
            'taxes_id': [Command.set(cls.tax_sale_a.ids)],
            'supplier_taxes_id': [Command.set(cls.tax_purchase_a.ids)],
            'weight': 102,
        })

        cls.product_a.update({'weight': 100})
        cls.product_b.update({'weight': 101})

    @classmethod
    def _create_invoices(cls, code_type=None):
        moves = cls.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': cls.partner_a.id,
            'invoice_date': '2022-01-01',
            'intrastat_country_id': cls.env.ref('base.de').id,
            'invoice_line_ids': [
                Command.create({
                    'name': 'line_1',
                    'product_id': cls.product_a.id,
                    'price_unit': 5.0,
                    'intrastat_transaction_id': cls.intrastat_codes[f'{code_type}-no_date'].id if code_type else None,
                    'quantity': 1.0,
                    'account_id': cls.company_data['default_account_revenue'].id,
                    'tax_ids': [],
                    'price_unit': 80.0,
                }),
                Command.create({
                    'name': 'line_2',
                    'product_id': cls.product_b.id,
                    'intrastat_transaction_id': cls.intrastat_codes[f'{code_type}-expired'].id if code_type else None,
                    'quantity': 1.0,
                    'account_id': cls.company_data['default_account_revenue'].id,
                    'tax_ids': [],
                    'price_unit': 100.0,
                }),
                Command.create({
                    'name': 'line_3',
                    'product_id': cls.product_c.id,
                    'intrastat_transaction_id': cls.intrastat_codes[f'{code_type}-premature'].id if code_type else None,
                    'quantity': 1.0,
                    'account_id': cls.company_data['default_account_revenue'].id,
                    'tax_ids': [],
                    'price_unit': 250.0,
                }),
            ],
        })
        moves.action_post()
        cls.env.flush_all()  # must flush else SQL request in report is not accurate
        return moves

    @freeze_time('2022-01-31')
    def test_intrastat_report_transaction(self):
        invoice = self._create_invoices('transaction')
        report = self.env.ref('account_intrastat.intrastat_report')
        options = self._generate_options(
            report,
            date_from=fields.Date.from_string('2022-01-01'),
            date_to=fields.Date.from_string('2022-01-31'),
            default_options={'country_format': 'code'},
        )
        report_information = report.get_report_information(options)
        lines, warnings = report_information['lines'], report_information['warnings']
        self.assertLinesValues(
            # pylint: disable=C0326
            lines,
            #    country code,  transaction code,  origin country
            [2,             3,                 6],
            [
                ('',            '',                ''),
                ('DE',          '103',             'QU'),
                ('DE',          '104',             'QU'),
                ('DE',          '105',             'QU'),
            ],
            options,
        )

        self.assertEqual(
            warnings['account_intrastat.intrastat_warning_missing_comm']['ids'],
            invoice.invoice_line_ids.product_id.ids,
        )
        self.assertEqual(
            warnings['account_intrastat.intrastat_warning_expired_trans']['ids'],
            invoice.invoice_line_ids.filtered(lambda l: l.name == 'line_2').ids,
        )
        self.assertEqual(
            warnings['account_intrastat.intrastat_warning_premature_trans']['ids'],
            invoice.invoice_line_ids.filtered(lambda l: l.name == 'line_3').ids,
        )

    @freeze_time('2022-01-31')
    def test_intrastat_report_commodity_on_products(self):
        self.product_a.intrastat_code_id = self.intrastat_codes['commodity-no_date']
        self.product_b.intrastat_code_id = self.intrastat_codes['commodity-expired']
        self.product_c.intrastat_code_id = self.intrastat_codes['commodity-premature']
        invoice = self._create_invoices()
        report = self.env.ref('account_intrastat.intrastat_report')
        options = self._generate_options(
            report,
            date_from=fields.Date.from_string('2022-01-01'),
            date_to=fields.Date.from_string('2022-01-31'),
            default_options={'country_format': 'code'},
        )
        report_information = report.get_report_information(options)
        lines, warnings = report_information['lines'], report_information['warnings']
        self.assertLinesValues(
            # pylint: disable=C0326
            lines,
            #    country code,  transaction code,  commodity code,  origin country
            [2,         3,                 5,               6],
            [
                ('',            '',                '',              ''),
                ('DE',          '',                '100',           'QU'),
                ('DE',          '',                '101',           'QU'),
                ('DE',          '',                '102',           'QU'),
            ],
            options,
        )

        self.assertEqual(warnings['account_intrastat.intrastat_warning_missing_trans']['ids'], invoice.invoice_line_ids.ids)
        self.assertEqual(warnings['account_intrastat.intrastat_warning_expired_comm']['ids'], self.product_b.ids)
        self.assertEqual(warnings['account_intrastat.intrastat_warning_premature_comm']['ids'], self.product_c.ids)
