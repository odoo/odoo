from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestAzTitReport(AccountTestInvoicingCommon):
    chart_template = 'az'
    country_code = 'AZ'

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        chart_template = cls.env['account.chart.template'].with_company(cls.env.company)
        cls.income_account = chart_template.ref('az_account_60110')
        cls.other_income_account = chart_template.ref('az_account_61199')
        cls.receivable_account = chart_template.ref('az_account_21100')

    def _post_entry(self, date, credit_account, amount):
        move = self.env['account.move'].create({
            'move_type': 'entry',
            'date': date,
            'line_ids': [
                (0, 0, {'account_id': self.receivable_account.id, 'debit': amount, 'credit': 0.0}),
                (0, 0, {'account_id': credit_account.id, 'debit': 0.0, 'credit': amount}),
            ],
        })
        move.action_post()
        return move

    def test_month_income(self):
        self._post_entry('2024-04-10', self.income_account, 100.0)
        self._post_entry('2024-05-10', self.income_account, 200.0)
        self._post_entry('2024-06-10', self.income_account, 300.0)
        # excluded: outside the quarter or not on an 'income' account
        self._post_entry('2024-07-05', self.income_account, 999.0)
        self._post_entry('2024-03-25', self.income_account, 999.0)
        self._post_entry('2024-04-15', self.other_income_account, 999.0)

        report = self.env.ref('l10n_az.tax_report_tit')
        options = {'date': {'date_to': '2024-06-30'}}
        self.assertEqual(report._l10n_az_tit_month_income(options, 1), 100.0)
        self.assertEqual(report._l10n_az_tit_month_income(options, 2), 200.0)
        self.assertEqual(report._l10n_az_tit_month_income(options, 3), 300.0)
