# -*- coding: utf-8 -*-
# pylint: disable=C0326
import json
from unittest.mock import patch

from .common import TestAccountReportsCommon
from odoo import fields, Command
from odoo.tests import tagged

@tagged('post_install', '-at_install')
class TestTaxReportCarryover(TestAccountReportsCommon):
    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.company_1 = cls.company_data['company']
        cls.company_2 = cls.company_data_2['company']

        cls.company_2.currency_id = cls.company_1.currency_id
        cls.company_1.account_tax_periodicity = cls.company_2.account_tax_periodicity = 'year'

        cls.report = cls.env['account.report'].create({
            'name': 'Test report',
            'country_id': cls.company_1.account_fiscal_country_id.id,
            'root_report_id': cls.env.ref("account.generic_tax_report").id,
            'column_ids': [Command.create({'name': 'Balance', 'sequence': 1, 'expression_label': 'balance'})],
        })

        cls.report_line = cls.env['account.report.line'].create({
            'name': 'Test carryover',
            'code': 'test_carryover',
            'report_id': cls.report.id,
            'sequence': 1,
            'expression_ids': [
                Command.create({
                    'label': 'tag',
                    'engine': 'domain',
                    'formula': [('account_id.account_type', '=', 'expense')],
                    'subformula': 'sum',
                }),
                Command.create({
                    'label': '_applied_carryover_balance',
                    'engine': 'external',
                    'formula': 'most_recent',
                    'date_scope': 'previous_tax_period',
                }),
                Command.create({
                    'label': 'balance_unbound',
                    'engine': 'aggregation',
                    'formula': 'test_carryover.tag + test_carryover._applied_carryover_balance',
                }),
                Command.create({
                    'label': '_carryover_balance',
                    'engine': 'aggregation',
                    'formula': 'test_carryover.balance_unbound',
                    'subformula': 'if_below(EUR(0))',
                }),
                Command.create({
                    'label': 'balance',
                    'engine': 'aggregation',
                    'formula': 'test_carryover.balance_unbound',
                    'subformula': 'if_above(EUR(0))',
                }),
            ],
        })

    def test_tax_report_carry_over(self):
        options = self._generate_options(self.report, '2021-01-01', '2021-12-31')

        move = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2021-03-01',
            'line_ids': [
                Command.create({
                    'debit': 0.0,
                    'credit': 1000.0,
                    'name': '2021_03_01',
                    'account_id': self.company_data['default_account_expense'].id
                }),
                Command.create({
                    'debit': 1000.0,
                    'credit': 0.0,
                    'name': '2021_03_01',
                    'account_id': self.company_data['default_account_payable'].id
                }),
            ],
        })
        move.action_post()

        self.env.flush_all()

        with patch.object(type(self.env['account.move']), '_get_vat_report_attachments', autospec=True, side_effect=lambda *args, **kwargs: []):
            vat_closing_move = self.env['account.generic.tax.report.handler']._generate_tax_closing_entries(self.report, options)
            vat_closing_move.action_post()

        # There should be an external value of -1000.0
        external_value = self.env['account.report.external.value'].search([('company_id', '=', self.company_1.id)])

        self.assertEqual(external_value.target_report_expression_label, '_applied_carryover_balance')
        self.assertEqual(external_value.date, fields.Date.from_string('2021-12-31'))
        self.assertEqual(external_value.value, -1000.0)

        # There should be no value in the report since there is a carryover
        lines = self.report._get_lines(options)
        self.assertLinesValues(
            lines,
            #   Name                                    Balance
            [   0,                                      1],
            [
                ('Test carryover',                     0.0),
            ],
            options,
        )

        # There should be a carryover pop-up of value -1000.0
        info_popup_data = json.loads(lines[0]['columns'][0]['info_popup_data'])
        self.assertEqual(info_popup_data['carryover'], '-1,000.00')

        # The carry over should be applied on the next period
        options = self._generate_options(self.report, '2022-01-01', '2022-12-31')

        lines = self.report._get_lines(options)

        self.assertLinesValues(
            lines,
            #   Name                                    Balance
            [   0,                                      1],
            [
                ('Test carryover',                     0.0),
            ],
            options,
        )

        info_popup_data = json.loads(lines[0]['columns'][0]['info_popup_data'])
        self.assertEqual(info_popup_data['carryover'], '-1,000.00')
        self.assertEqual(info_popup_data['applied_carryover'], '-1,000.00')

    def test_tax_report_carry_over_tax_unit(self):
        self.env['account.tax.unit'].create({
            'name': 'Test tax unit',
            'country_id': self.company_1.account_fiscal_country_id.id,
            'vat': 'DW1234567890',
            'company_ids': [Command.set([self.company_1.id, self.company_2.id])],
            'main_company_id': self.company_1.id,
        })

        move_company_1 = self.env['account.move'].with_company(self.company_1).create({
            'move_type': 'entry',
            'date': '2021-03-01',
            'line_ids': [
                Command.create({
                    'debit': 0.0,
                    'credit': 1000.0,
                    'name': '2021_03_01',
                    'account_id': self.company_data['default_account_expense'].id
                }),
                Command.create({
                    'debit': 1000.0,
                    'credit': 0.0,
                    'name': '2021_03_01',
                    'account_id': self.company_data['default_account_payable'].id
                }),
            ],
        })
        move_company_1.action_post()

        move_company_2 = self.env['account.move'].with_company(self.company_2).create({
            'move_type': 'entry',
            'date': '2021-03-01',
            'line_ids': [
                Command.create({
                    'debit': 2000.0,
                    'credit': 0.0,
                    'name': '2021_03_01',
                    'account_id': self.company_data_2['default_account_expense'].id
                }),
                Command.create({
                    'debit': 0.0,
                    'credit': 2000.0,
                    'name': '2021_03_01',
                    'account_id': self.company_data_2['default_account_payable'].id
                }),
            ],
        })
        move_company_2.action_post()

        self.env.flush_all()

        with patch.object(type(self.env['account.move']), '_get_vat_report_attachments', autospec=True, side_effect=lambda *args, **kwargs: []):
            # There should be no external value for company 1 at this point
            external_value_company_1 = self.env['account.report.external.value'].search_count([('company_id', '=', self.company_1.id)])
            self.assertEqual(external_value_company_1, 0)

            # Closes both companies
            options = self._generate_options(self.report, '2021-01-01', '2021-12-31')
            vat_closing_moves = self.env['account.generic.tax.report.handler']._generate_tax_closing_entries(self.report, options)
            vat_closing_moves.filtered(lambda x: x.company_id == self.company_1).action_post()

        self.assertEqual(len(vat_closing_moves), 2, "There should be one closing per company in the tax unit")
        self.assertTrue(all(closing.state == 'posted' for closing in vat_closing_moves), "Posting the main company's closing should post every other closing of this unit")

        # There should be two external value for company_1: -1000.0 and 1000.0
        external_value_company_1 = self.env['account.report.external.value'].search([('company_id', '=', self.company_1.id)])
        external_value_company_1 = sorted(external_value_company_1, key=lambda x: x.value) # To make sure they are always in the same order

        self.assertEqual(external_value_company_1[0].target_report_expression_label, '_applied_carryover_balance')
        self.assertEqual(external_value_company_1[0].date, fields.Date.from_string('2021-12-31'))
        self.assertEqual(external_value_company_1[0].value, -1000.0)

        self.assertEqual(external_value_company_1[1].target_report_expression_label, '_applied_carryover_balance')
        self.assertEqual(external_value_company_1[1].date, fields.Date.from_string('2021-12-31'))
        self.assertEqual(external_value_company_1[1].value, 1000.0)

        # There should be no external value for company_2
        external_value_company_2 = self.env['account.report.external.value'].search_count([('company_id', '=', self.company_2.id)])
        self.assertEqual(external_value_company_2, 0)

        # TAX UNIT REPORT (current period)
        # ==============================================================================================================
        # There should be a value of 1000.0 in the report since the sum of the balance of both companies is positive,
        # there is no carryover
        options = self._generate_options(self.report, '2021-01-01', '2021-12-31')

        lines_tax_unit = self.report._get_lines(options)
        self.assertLinesValues(
            lines_tax_unit,
            #   Name                                    Balance
            [   0,                                      1],
            [
                ('Test carryover',                      1000.0),
            ],
            options,
        )

        # There should be no carryover pop-up
        self.assertTrue('info_popup_data' not in lines_tax_unit[0]['columns'][0].keys())

        # COMPANY 1 REPORT (current period)
        # ==============================================================================================================
        # There should be no value in the report since there is a carryover
        report_company_1 = self.report.with_context(allowed_company_ids=self.company_1.ids)
        options = self._generate_options(report_company_1, '2021-01-01', '2021-12-31')

        lines_company_1 = report_company_1._get_lines(options)
        self.assertLinesValues(
            lines_company_1,
            #   Name                                    Balance
            [   0,                                      1],
            [
                ('Test carryover',                     0.0),
            ],
            options,
        )

        # There should be a carryover pop-up
        info_popup_data = json.loads(lines_company_1[0]['columns'][0]['info_popup_data'])
        self.assertEqual(info_popup_data['carryover'], '-1,000.00')

        # COMPANY 2 REPORT (current period)
        # ==============================================================================================================
        # There should be a value of 2000.0 in the report since there is no carryover
        report_company_2 = self.report.with_context(allowed_company_ids=self.company_2.ids)
        options = self._generate_options(report_company_2, '2021-01-01', '2021-12-31')

        lines_company_2 = report_company_2._get_lines(options)
        self.assertLinesValues(
            lines_company_2,
            #   Name                                    Balance
            [   0,                                      1],
            [
                ('Test carryover',                      2000.0),
            ],
            options,
        )

        # There should be no carryover pop-up
        self.assertTrue('info_popup_data' not in lines_company_2[0]['columns'][0].keys())

        # TAX UNIT REPORT (next period)
        # ==============================================================================================================
        options = self._generate_options(self.report, '2022-01-01', '2022-12-31')

        lines_tax_unit = self.report._get_lines(options)
        self.assertLinesValues(
            lines_tax_unit,
            #   Name                                    Balance
            [   0,                                      1],
            [
                ('Test carryover',                     0.0),
            ],
            options,
        )

        # There should be no carryover pop-up
        self.assertTrue('info_popup_data' not in lines_tax_unit[0]['columns'][0].keys())

        # COMPANY 1 REPORT (next period)
        # ==============================================================================================================
        report_company_1 = self.report.with_context(allowed_company_ids=self.company_1.ids)
        options = self._generate_options(report_company_1, '2022-01-01', '2022-12-31')

        lines_company_1 = report_company_1._get_lines(options)
        self.assertLinesValues(
            lines_company_1,
            #   Name                                    Balance
            [   0,                                      1],
            [
                ('Test carryover',                     0.0),
            ],
            options,
        )

        self.assertTrue('info_popup_data' not in lines_company_1[0]['columns'][0].keys())

        # COMPANY 2 REPORT (next period)
        # ==============================================================================================================
        report_company_2 = self.report.with_context(allowed_company_ids=self.company_2.ids)
        options = self._generate_options(report_company_2, '2022-01-01', '2022-12-31')

        lines_company_2 = report_company_2._get_lines(options)
        self.assertLinesValues(lines_company_2,
            #   Name                                    Balance
            [   0,                                      1],
            [
                ('Test carryover',                     0.0),
            ],
            options,
        )

        # There should be no carryover pop-up
        self.assertTrue('info_popup_data' not in lines_company_2[0]['columns'][0].keys())
