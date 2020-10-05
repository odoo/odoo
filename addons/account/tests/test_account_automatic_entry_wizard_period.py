# -*- coding: utf-8 -*-
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo import fields
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestAccountAutomaticEntryWizardPeriod(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.invoice = cls.env['account.move'].create({
            'move_type': 'out_invoice',
            'date': '2017-01-01',
            'partner_id': cls.partner_a.id,
            'invoice_date': '2017-01-01',
            'invoice_line_ids': [
                (0, 0, {
                    'name': "line1",
                    'quantity': 1,
                    'price_unit': 1000.0,
                    'account_id': cls.company_data['default_account_revenue'].id,
                }),
                (0, 0, {
                    'name': "line2",
                    'quantity': 1,
                    'price_unit': 200.0,
                    'account_id': cls.company_data['default_account_revenue'].id,
                }),
            ]
        })
        cls.invoice.action_post()

        cls.accrual_account = cls.env['account.account'].create({
            'name': "test_accrual_account",
            'code': "TEST",
            'user_type_id': cls.env.ref('account.data_account_type_revenue').id,
            'reconcile': True,
            'company_id': cls.company_data['company'].id,
        })
        cls.income_account = cls.company_data['default_account_revenue']

        cls.Wizard = cls.env['account.automatic.entry.wizard']\
            .with_context(active_model='account.move.line', active_ids=cls.invoice.invoice_line_ids.ids)

    def test_chg_period_100_percent_no_time_division(self):
        ''' Test smoothing the invoice in the period without the time division. '''
        to_date = lambda string: fields.Date.from_string(string)

        wizard = self.Wizard.create({
            'action': 'change_period',
            'journal_id': self.company_data['default_journal_misc'].id,
            'revenue_accrual_account': self.accrual_account.id,
            'chg_period_date_from': '2017-06-01',
            'chg_period_date_to': '2017-12-31',     # Large period to check the rounding issues.
            'chg_period_percentage': 100.0,
            'chg_period_time_division': False,
        })
        wizard_res = wizard.do_action()

        lines = self.env['account.move'].browse(wizard_res['domain'][0][2]).line_ids.sorted(lambda line: (line.date, -abs(line.balance), -line.balance))
        dest_lines = lines.filtered(lambda line: line.date == self.invoice.date)
        accrual_lines = lines.filtered(lambda line: line.date != self.invoice.date)
        self.assertRecordValues(dest_lines, [
            {'debit': 1000.0,   'credit': 0.0,      'account_id': self.income_account.id,   'reconciled': False,    'date': to_date('2017-01-01')},
            {'debit': 0.0,      'credit': 1000.0,   'account_id': self.accrual_account.id,  'reconciled': True,     'date': to_date('2017-01-01')},
            {'debit': 200.0,    'credit': 0.0,      'account_id': self.income_account.id,   'reconciled': False,    'date': to_date('2017-01-01')},
            {'debit': 0.0,      'credit': 200.0,    'account_id': self.accrual_account.id,  'reconciled': True,     'date': to_date('2017-01-01')},
        ])
        self.assertRecordValues(accrual_lines, [
            {'debit': 142.86,   'credit': 0.0,      'account_id': self.accrual_account.id,  'reconciled': True,     'date': to_date('2017-06-30')},
            {'debit': 0.0,      'credit': 142.86,   'account_id': self.income_account.id,   'reconciled': False,    'date': to_date('2017-06-30')},
            {'debit': 28.57,    'credit': 0.0,      'account_id': self.accrual_account.id,  'reconciled': True,     'date': to_date('2017-06-30')},
            {'debit': 0.0,      'credit': 28.57,    'account_id': self.income_account.id,   'reconciled': False,    'date': to_date('2017-06-30')},
            {'debit': 142.86,   'credit': 0.0,      'account_id': self.accrual_account.id,  'reconciled': True,     'date': to_date('2017-07-31')},
            {'debit': 0.0,      'credit': 142.86,   'account_id': self.income_account.id,   'reconciled': False,    'date': to_date('2017-07-31')},
            {'debit': 28.57,    'credit': 0.0,      'account_id': self.accrual_account.id,  'reconciled': True,     'date': to_date('2017-07-31')},
            {'debit': 0.0,      'credit': 28.57,    'account_id': self.income_account.id,   'reconciled': False,    'date': to_date('2017-07-31')},
            {'debit': 142.86,   'credit': 0.0,      'account_id': self.accrual_account.id,  'reconciled': True,     'date': to_date('2017-08-31')},
            {'debit': 0.0,      'credit': 142.86,   'account_id': self.income_account.id,   'reconciled': False,    'date': to_date('2017-08-31')},
            {'debit': 28.57,    'credit': 0.0,      'account_id': self.accrual_account.id,  'reconciled': True,     'date': to_date('2017-08-31')},
            {'debit': 0.0,      'credit': 28.57,    'account_id': self.income_account.id,   'reconciled': False,    'date': to_date('2017-08-31')},
            {'debit': 142.86,   'credit': 0.0,      'account_id': self.accrual_account.id,  'reconciled': True,     'date': to_date('2017-09-30')},
            {'debit': 0.0,      'credit': 142.86,   'account_id': self.income_account.id,   'reconciled': False,    'date': to_date('2017-09-30')},
            {'debit': 28.57,    'credit': 0.0,      'account_id': self.accrual_account.id,  'reconciled': True,     'date': to_date('2017-09-30')},
            {'debit': 0.0,      'credit': 28.57,    'account_id': self.income_account.id,   'reconciled': False,    'date': to_date('2017-09-30')},
            {'debit': 142.86,   'credit': 0.0,      'account_id': self.accrual_account.id,  'reconciled': True,     'date': to_date('2017-10-31')},
            {'debit': 0.0,      'credit': 142.86,   'account_id': self.income_account.id,   'reconciled': False,    'date': to_date('2017-10-31')},
            {'debit': 28.57,    'credit': 0.0,      'account_id': self.accrual_account.id,  'reconciled': True,     'date': to_date('2017-10-31')},
            {'debit': 0.0,      'credit': 28.57,    'account_id': self.income_account.id,   'reconciled': False,    'date': to_date('2017-10-31')},
            {'debit': 142.86,   'credit': 0.0,      'account_id': self.accrual_account.id,  'reconciled': True,     'date': to_date('2017-11-30')},
            {'debit': 0.0,      'credit': 142.86,   'account_id': self.income_account.id,   'reconciled': False,    'date': to_date('2017-11-30')},
            {'debit': 28.57,    'credit': 0.0,      'account_id': self.accrual_account.id,  'reconciled': True,     'date': to_date('2017-11-30')},
            {'debit': 0.0,      'credit': 28.57,    'account_id': self.income_account.id,   'reconciled': False,    'date': to_date('2017-11-30')},
            {'debit': 142.84,   'credit': 0.0,      'account_id': self.accrual_account.id,  'reconciled': True,     'date': to_date('2017-12-31')},
            {'debit': 0.0,      'credit': 142.84,   'account_id': self.income_account.id,   'reconciled': False,    'date': to_date('2017-12-31')},
            {'debit': 28.58,    'credit': 0.0,      'account_id': self.accrual_account.id,  'reconciled': True,     'date': to_date('2017-12-31')},
            {'debit': 0.0,      'credit': 28.58,    'account_id': self.income_account.id,   'reconciled': False,    'date': to_date('2017-12-31')},
        ])

    def test_chg_period_100_percent_time_division(self):
        ''' Same as test_chg_period_100_percent_no_time_division using the time division meaning the smoothing is made
        to different months considering their number of days.
        '''
        to_date = lambda string: fields.Date.from_string(string)

        wizard = self.Wizard.create({
            'action': 'change_period',
            'journal_id': self.company_data['default_journal_misc'].id,
            'revenue_accrual_account': self.accrual_account.id,
            'chg_period_date_from': '2017-06-01',
            'chg_period_date_to': '2017-12-31',     # Large period to check the rounding issues.
            'chg_period_percentage': 100.0,
            'chg_period_time_division': True,
        })
        wizard_res = wizard.do_action()

        lines = self.env['account.move'].browse(wizard_res['domain'][0][2]).line_ids.sorted(lambda line: (line.date, -abs(line.balance), -line.balance))
        dest_lines = lines.filtered(lambda line: line.date == self.invoice.date)
        accrual_lines = lines.filtered(lambda line: line.date != self.invoice.date)
        self.assertRecordValues(dest_lines, [
            {'debit': 1000.0,   'credit': 0.0,      'account_id': self.income_account.id,   'reconciled': False,    'date': to_date('2017-01-01')},
            {'debit': 0.0,      'credit': 1000.0,   'account_id': self.accrual_account.id,  'reconciled': True,     'date': to_date('2017-01-01')},
            {'debit': 200.0,    'credit': 0.0,      'account_id': self.income_account.id,   'reconciled': False,    'date': to_date('2017-01-01')},
            {'debit': 0.0,      'credit': 200.0,    'account_id': self.accrual_account.id,  'reconciled': True,     'date': to_date('2017-01-01')},
        ])
        self.assertRecordValues(accrual_lines, [
            {'debit': 140.1,    'credit': 0.0,      'account_id': self.accrual_account.id,  'reconciled': True,     'date': to_date('2017-06-30')},
            {'debit': 0.0,      'credit': 140.1,    'account_id': self.income_account.id,   'reconciled': False,    'date': to_date('2017-06-30')},
            {'debit': 28.02,    'credit': 0.0,      'account_id': self.accrual_account.id,  'reconciled': True,     'date': to_date('2017-06-30')},
            {'debit': 0.0,      'credit': 28.02,    'account_id': self.income_account.id,   'reconciled': False,    'date': to_date('2017-06-30')},
            {'debit': 144.93,   'credit': 0.0,      'account_id': self.accrual_account.id,  'reconciled': True,     'date': to_date('2017-07-31')},
            {'debit': 0.0,      'credit': 144.93,   'account_id': self.income_account.id,   'reconciled': False,    'date': to_date('2017-07-31')},
            {'debit': 28.99,    'credit': 0.0,      'account_id': self.accrual_account.id,  'reconciled': True,     'date': to_date('2017-07-31')},
            {'debit': 0.0,      'credit': 28.99,    'account_id': self.income_account.id,   'reconciled': False,    'date': to_date('2017-07-31')},
            {'debit': 144.93,   'credit': 0.0,      'account_id': self.accrual_account.id,  'reconciled': True,     'date': to_date('2017-08-31')},
            {'debit': 0.0,      'credit': 144.93,   'account_id': self.income_account.id,   'reconciled': False,    'date': to_date('2017-08-31')},
            {'debit': 28.99,    'credit': 0.0,      'account_id': self.accrual_account.id,  'reconciled': True,     'date': to_date('2017-08-31')},
            {'debit': 0.0,      'credit': 28.99,    'account_id': self.income_account.id,   'reconciled': False,    'date': to_date('2017-08-31')},
            {'debit': 140.1,    'credit': 0.0,      'account_id': self.accrual_account.id,  'reconciled': True,     'date': to_date('2017-09-30')},
            {'debit': 0.0,      'credit': 140.1,    'account_id': self.income_account.id,   'reconciled': False,    'date': to_date('2017-09-30')},
            {'debit': 28.02,    'credit': 0.0,      'account_id': self.accrual_account.id,  'reconciled': True,     'date': to_date('2017-09-30')},
            {'debit': 0.0,      'credit': 28.02,    'account_id': self.income_account.id,   'reconciled': False,    'date': to_date('2017-09-30')},
            {'debit': 144.93,   'credit': 0.0,      'account_id': self.accrual_account.id,  'reconciled': True,     'date': to_date('2017-10-31')},
            {'debit': 0.0,      'credit': 144.93,   'account_id': self.income_account.id,   'reconciled': False,    'date': to_date('2017-10-31')},
            {'debit': 28.99,    'credit': 0.0,      'account_id': self.accrual_account.id,  'reconciled': True,     'date': to_date('2017-10-31')},
            {'debit': 0.0,      'credit': 28.99,    'account_id': self.income_account.id,   'reconciled': False,    'date': to_date('2017-10-31')},
            {'debit': 140.1,    'credit': 0.0,      'account_id': self.accrual_account.id,  'reconciled': True,     'date': to_date('2017-11-30')},
            {'debit': 0.0,      'credit': 140.1,    'account_id': self.income_account.id,   'reconciled': False,    'date': to_date('2017-11-30')},
            {'debit': 28.02,    'credit': 0.0,      'account_id': self.accrual_account.id,  'reconciled': True,     'date': to_date('2017-11-30')},
            {'debit': 0.0,      'credit': 28.02,    'account_id': self.income_account.id,   'reconciled': False,    'date': to_date('2017-11-30')},
            {'debit': 144.91,   'credit': 0.0,      'account_id': self.accrual_account.id,  'reconciled': True,     'date': to_date('2017-12-31')},
            {'debit': 0.0,      'credit': 144.91,   'account_id': self.income_account.id,   'reconciled': False,    'date': to_date('2017-12-31')},
            {'debit': 28.97,    'credit': 0.0,      'account_id': self.accrual_account.id,  'reconciled': True,     'date': to_date('2017-12-31')},
            {'debit': 0.0,      'credit': 28.97,    'account_id': self.income_account.id,   'reconciled': False,    'date': to_date('2017-12-31')},
        ])

    def test_chg_period_manual_periods(self):
        ''' Test the smoothing by manual lines. '''
        to_date = lambda string: fields.Date.from_string(string)

        wizard = self.Wizard.create({
            'action': 'change_period',
            'journal_id': self.company_data['default_journal_misc'].id,
            'revenue_accrual_account': self.accrual_account.id,
            'chg_period_line_ids': [
                (0, 0, {'date': '2017-06-01', 'balance': 120.0}),
                (0, 0, {'date': '2017-07-01', 'balance': 300.0}),
                (0, 0, {'date': '2017-08-01', 'balance': 700.0}),
                (0, 0, {'date': '2017-09-01', 'balance': 80.0}),
            ],
        })
        wizard_res = wizard.do_action()


        lines = self.env['account.move'].browse(wizard_res['domain'][0][2]).line_ids.sorted(lambda line: (line.date, -abs(line.balance), -line.balance))
        dest_lines = lines.filtered(lambda line: line.date == self.invoice.date)
        accrual_lines = lines.filtered(lambda line: line.date != self.invoice.date)
        self.assertRecordValues(dest_lines, [
            {'debit': 1000.0,   'credit': 0.0,      'account_id': self.income_account.id,   'reconciled': False,    'date': to_date('2017-01-01')},
            {'debit': 0.0,      'credit': 1000.0,   'account_id': self.accrual_account.id,  'reconciled': True,     'date': to_date('2017-01-01')},
            {'debit': 200.0,    'credit': 0.0,      'account_id': self.income_account.id,   'reconciled': False,    'date': to_date('2017-01-01')},
            {'debit': 0.0,      'credit': 200.0,    'account_id': self.accrual_account.id,  'reconciled': True,     'date': to_date('2017-01-01')},
        ])
        self.assertRecordValues(accrual_lines, [
            {'debit': 100.0,    'credit': 0.0,      'account_id': self.accrual_account.id,  'reconciled': True,     'date': to_date('2017-06-01')},
            {'debit': 0.0,      'credit': 100.0,    'account_id': self.income_account.id,   'reconciled': False,    'date': to_date('2017-06-01')},
            {'debit': 20.0,     'credit': 0.0,      'account_id': self.accrual_account.id,  'reconciled': True,     'date': to_date('2017-06-01')},
            {'debit': 0.0,      'credit': 20.0,     'account_id': self.income_account.id,   'reconciled': False,    'date': to_date('2017-06-01')},
            {'debit': 250.0,    'credit': 0.0,      'account_id': self.accrual_account.id,  'reconciled': True,     'date': to_date('2017-07-01')},
            {'debit': 0.0,      'credit': 250.0,    'account_id': self.income_account.id,   'reconciled': False,    'date': to_date('2017-07-01')},
            {'debit': 50.0,     'credit': 0.0,      'account_id': self.accrual_account.id,  'reconciled': True,     'date': to_date('2017-07-01')},
            {'debit': 0.0,      'credit': 50.0,     'account_id': self.income_account.id,   'reconciled': False,    'date': to_date('2017-07-01')},
            {'debit': 583.33,   'credit': 0.0,      'account_id': self.accrual_account.id,  'reconciled': True,     'date': to_date('2017-08-01')},
            {'debit': 0.0,      'credit': 583.33,   'account_id': self.income_account.id,   'reconciled': False,    'date': to_date('2017-08-01')},
            {'debit': 116.67,   'credit': 0.0,      'account_id': self.accrual_account.id,  'reconciled': True,     'date': to_date('2017-08-01')},
            {'debit': 0.0,      'credit': 116.67,   'account_id': self.income_account.id,   'reconciled': False,    'date': to_date('2017-08-01')},
            {'debit': 66.67,    'credit': 0.0,      'account_id': self.accrual_account.id,  'reconciled': True,     'date': to_date('2017-09-01')},
            {'debit': 0.0,      'credit': 66.67,    'account_id': self.income_account.id,   'reconciled': False,    'date': to_date('2017-09-01')},
            {'debit': 13.33,    'credit': 0.0,      'account_id': self.accrual_account.id,  'reconciled': True,     'date': to_date('2017-09-01')},
            {'debit': 0.0,      'credit': 13.33,    'account_id': self.income_account.id,   'reconciled': False,    'date': to_date('2017-09-01')},
        ])
