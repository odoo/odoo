# Part of Odoo. See LICENSE file for full copyright and licensing details.
from freezegun import freeze_time

from odoo import fields
from odoo.addons.account_reports.tests.account_sales_report_common import AccountSalesReportCommon
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class BelgiumGeneralLedgerTest(AccountSalesReportCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref='be_comp'):
        super().setUpClass(chart_template_ref)

    @classmethod
    def setup_company_data(cls, company_name, chart_template=None, **kwargs):
        res = super().setup_company_data(company_name, chart_template=chart_template, **kwargs)
        res['company'].update({
            'country_id': cls.env.ref('base.be').id,
            'vat': 'BE0477472701',
        })
        res['company'].partner_id.update({
            'email': 'jsmith@mail.com',
            'phone': '+32475123456',
        })
        return res

    @freeze_time('2023-01-01')
    def test_annual_account_export(self):
        moves = self.env['account.move'].create([{
            'move_type': 'entry',
            'date': fields.Date.from_string('2023-01-01'),
            'journal_id': self.company_data['default_journal_sale'].id,
            'line_ids': [
                (0, 0, {'debit': 1000.0, 'credit': 0.0, 'name': 'move_01_01',
                        'account_id': self.company_data['default_account_receivable'].id}),
                (0, 0, {'debit': 0.0, 'credit': 1000.0, 'name': 'move_01_02',
                        'account_id': self.company_data['default_account_revenue'].id}),
            ],
        }, {
            'move_type': 'entry',
            'date': fields.Date.from_string('2023-01-01'),
            'journal_id': self.company_data['default_journal_sale'].id,
            'line_ids': [
                (0, 0, {'debit': 250.0, 'credit': 0.0, 'name': 'move_02_01',
                        'account_id': self.company_data['default_account_payable'].id}),
                (0, 0, {'debit': 0.0, 'credit': 250.0, 'name': 'move_02_02',
                        'account_id': self.company_data['default_account_expense'].id}),
            ],
        }])
        moves.action_post()

        report = self.env.ref('account_reports.general_ledger_report')
        options = self._generate_options(report, '2023-01-01', '2023-01-01')
        annual_accounts_data = self.env[report.custom_handler_model_name].l10n_be_get_annual_accounts(options)
        expected = b"""400000\tCustomers\t1000,0\t0,0
440000\tSuppliers\t250,0\t0,0
600000\tPurchases of Raw Materials\t0,0\t250,0
700000\tSales in Belgium (Trade Goods)\t0,0\t1000,0"""
        self.assertEqual(annual_accounts_data['file_content'], expected)
