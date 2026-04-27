# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged, freeze_time
from odoo.addons.account_reports.tests.common import TestAccountReportsCommon


@freeze_time('2024-03-03')
@tagged('post_install_l10n', 'post_install', '-at_install')
class NigeriaReportTest(TestAccountReportsCommon):

    @classmethod
    @TestAccountReportsCommon.setup_country('ng')
    def setUpClass(cls):
        super().setUpClass()
        company = cls.company_data['company']
        cls.tax_tag_carryover = cls.env['account.account.tag'].with_company(company).search([('name', '=', '-100')])
        cls.purchase_tax = cls.env['account.tax'].with_company(company).search([
            ('name', '=', '7.5%'),
            ('type_tax_use', '=', 'purchase'),
        ])
        cls.sales_tax = cls.env['account.tax'].with_company(company).search([
            ('name', '=', '7.5%'),
            ('type_tax_use', '=', 'sale'),
        ])

    def _create_first_carryover_entry(self, amount):
        self.env['account.move'].create({
            'move_type': 'entry',
            'journal_id': self.company_data['default_journal_misc'].id,
            'invoice_date': '2024-03-01',
            'date': '2024-03-01',
            'line_ids': [(0, 0, {
                'account_id': self.company_data['default_account_receivable'].id,
                'debit': amount,
                'credit': 0.0,
                'tax_tag_ids': self.tax_tag_carryover.ids,
            }), (0, 0, {
                'account_id': self.company_data['default_account_revenue'].id,
                'debit': 0.0,
                'credit': amount,
            })]
        }).action_post()

    def _create_test_moves(self, move_type, tax, amount):
        self.env['account.move'].create({
            'move_type': move_type,
            'partner_id': self.partner_a.id,
            'invoice_date': '2024-03-01',
            'invoice_line_ids': [
                (0, 0, {
                    'name': 'Sonic screwdriver',
                    'price_unit': amount,
                    'quantity': 1.0,
                    'account_id': self.company_data['default_account_revenue'].id,
                    'tax_ids': tax.ids,
                }),
            ],
        }).action_post()

    def _get_report_lines(self):
        report = self.env.ref('l10n_ng.l10n_ng_tax_report')
        previous_options = {
            'date': {
                'date_from': '2024-03-01',
                'date_to': '2024-03-03',
            }
        }
        options = report.get_options(previous_options)
        return report._get_lines(options)

    def _get_lines_amounts(self, report_lines, line_indexes):
        return [report_lines[idx]['columns'][0]['no_format'] for idx in line_indexes]

    def test_first_carryover_vat_credit(self):
        """
        Tests the first value populated in line 100 of the tax report:
        Previous Unrelieved VAT Credit Brought Forward. It's a carryover line
        that is usually populated based on line 115. Unrelieved VAT Credit Carried Forward
        but when a user opens Odoo for the first time, they will need to use a tax tag
        to populate the first value in it.
        """
        self._create_first_carryover_entry(amount=100.0)
        report_lines = self._get_report_lines()

        # On the last line, since there is no VAT Payable and we only have
        # VAT credit carried forward, there is nothing to pay
        self.assertEqual(
            self._get_lines_amounts(report_lines, line_indexes=(22, 23, 25, -1)),
            [-100.0, -100.0, -100.0, 0.0]
        )

    def test_vat_payable_refundable_case_1(self):
        """
        First case:
        95. Net VAT Payable/(Refundable) Current Month              | -115
        100. Previous Unrelieved VAT Credit Brought Forward         | -500
        105. Total VAT Credit claimable                             | -615
        110. VAT Credit Relieved (expected value: negative or zero) | -400
        115. Unrelieved VAT Credit Carried Forward                  | -215
        120. VAT Payable                                            |  0
        """
        self._create_first_carryover_entry(amount=500.0)
        self._create_test_moves(move_type='in_invoice', tax=self.purchase_tax, amount=1533.3)  # amounts are going to be weird to get a specific VAT payable/refundable
        credit_relieved_expression = self.env.ref('l10n_ng.l10n_ng_tr_c_110').expression_ids
        self.env['account.report.external.value'].create({
            'name': 'Running up that hill',
            'value': -400.0,
            'date': '2024-03-03',
            'target_report_expression_id': credit_relieved_expression.id,
            'company_id': self.env.company.id,
        })

        report_lines = self._get_report_lines()
        self.assertEqual(
            self._get_lines_amounts(report_lines, line_indexes=range(21, 27)),
            [-115.0, -500.0, -615.0, -400.0, -215.0, 0.0]
        )

    def test_vat_payable_refundable_case_2(self):
        """
        Second case:
        95. Net VAT Payable/(Refundable) Current Month              |  100
        100. Previous Unrelieved VAT Credit Brought Forward         | -400
        105. Total VAT Credit claimable                             | -300
        110. VAT Credit Relieved (expected value: negative or zero) | -200
        115. Unrelieved VAT Credit Carried Forward                  | -100
        120. VAT Payable                                            |  0
        """
        self._create_first_carryover_entry(amount=400.0)
        self._create_test_moves(move_type='out_invoice', tax=self.sales_tax, amount=1333.3)
        credit_relieved_expression = self.env.ref('l10n_ng.l10n_ng_tr_c_110').expression_ids
        self.env['account.report.external.value'].create({
            'name': 'Heart of glass',
            'value': -200.0,
            'date': '2024-03-03',
            'target_report_expression_id': credit_relieved_expression.id,
            'company_id': self.env.company.id,
        })

        report_lines = self._get_report_lines()
        self.assertEqual(
            self._get_lines_amounts(report_lines, line_indexes=range(21, 27)),
            [100.0, -400.0, -300.0, -200.0, -100.0, 0.0]
        )

    def test_vat_payable_refundable_case_3(self):
        """
        Third case:
        95. Net VAT Payable/(Refundable) Current Month              |  1000
        100. Previous Unrelieved VAT Credit Brought Forward         | -400
        105. Total VAT Credit claimable                             |  0
        110. VAT Credit Relieved (expected value: negative or zero) |  0
        115. Unrelieved VAT Credit Carried Forward                  |  0
        120. VAT Payable                                            |  600
        """
        self._create_first_carryover_entry(amount=400.0)
        self._create_test_moves(move_type='out_invoice', tax=self.sales_tax, amount=13333.30)
        report_lines = self._get_report_lines()
        self.assertEqual(
            self._get_lines_amounts(report_lines, line_indexes=range(21, 27)),
            [1000.0, -400.0, 0.0, 0.0, 0.0, 600.0]
        )

    def test_report_period_warning(self):
        # the tax report date filter should always be a month
        report = self.env.ref('l10n_ng.l10n_ng_tax_report')
        previous_options = {
            'date': {
                'date_from': '2024-01-01',
                'date_to': '2024-03-03',
            }
        }
        options = report.get_options(previous_options)
        report_information = report.get_report_information(options)
        self.assertTrue('l10n_ng_reports.tax_report_period_check' in report_information['warnings'])

        # now change back to a period of one month
        previous_options = {
            'date': {
                'date_from': '2024-03-01',
                'date_to': '2024-03-31',
            }
        }
        options = report.get_options(previous_options)
        report_information = report.get_report_information(options)
        self.assertFalse('l10n_ng_reports.tax_report_period_check' in report_information['warnings'])
