# -*- coding: utf-8 -*-
from freezegun import freeze_time
from .common import TestAccountReportsCommon

from odoo import fields, Command
from odoo.tests import tagged
from odoo.exceptions import UserError


@tagged('post_install', '-at_install')
class TestMultiCurrenciesRevaluationReport(TestAccountReportsCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.currency_data_2 = cls.setup_multi_currency_data({
            'name': 'Dark Chocolate Coin',
            'symbol': '🍫',
            'currency_unit_label': 'Dark Choco',
            'currency_subunit_label': 'Dark Cacao Powder',
        }, rate2016=10.0, rate2017=20.0)

        cls.expense_account_1 = cls.company_data['default_account_expense']
        cls.expense_account_2 = cls.copy_account(cls.company_data['default_account_expense'])

        cls.env['res.currency.rate'].create({
            'name': '2023-01-20',
            'rate': 1,
            'currency_id': cls.currency_data['currency'].id,
            'company_id': cls.company_data['company'].id,
        })

        cls.env['res.currency.rate'].create({
            'name': '2023-01-25',
            'rate': 2,
            'currency_id': cls.currency_data['currency'].id,
            'company_id': cls.company_data['company'].id,
        })

        cls.env['res.currency.rate'].create({
            'name': '2023-01-30',
            'rate': 4,
            'currency_id': cls.currency_data['currency'].id,
            'company_id': cls.company_data['company'].id,
        })

        cls.env['res.currency.rate'].create({
            'name': '2023-01-20',
            'rate': 1,
            'currency_id': cls.currency_data_2['currency'].id,
            'company_id': cls.company_data['company'].id,
        })


        cls.report = cls.env.ref('account_reports.multicurrency_revaluation_report')

    @classmethod
    def pay_move(cls, move, amount, date, account_type='liability_payable', currency=None, partner_type=None):
        if not currency:
            currency = move.currency_id

        assert amount
        if amount > 0:
            payment_type = 'outbound'
            payment_method = 'account.account_payment_method_manual_out'
            partner_type = 'supplier' if not partner_type else partner_type
        else:
            payment_type = 'inbound'
            payment_method = 'account.account_payment_method_manual_in'
            partner_type = 'customer' if not partner_type else partner_type

        payment = cls.env['account.payment'].create({
            'payment_type': payment_type,
            'amount': abs(amount),
            'currency_id': currency.id,
            'journal_id': cls.company_data['default_journal_bank'].id,
            'date': fields.Date.from_string(date),
            'partner_id': move.partner_id.id,
            'payment_method_id': cls.env.ref(payment_method).id,
            'partner_type': partner_type,
        })
        payment.action_post()
        lines_to_reconcile = move.line_ids.filtered(lambda x: x.account_type == account_type)
        lines_to_reconcile += payment.line_ids.filtered(lambda x: x.account_type == account_type)
        lines_to_reconcile.reconcile()

    @classmethod
    def create_move_one_line(cls, move_type, journal_id, partner_id, date, invoice_date, currency_id, account_id, quantity, price_unit, payment_term_id=None):
        move = cls.env['account.move'].create({
            'move_type': move_type,
            'partner_id': partner_id,
            'date': date,
            'invoice_date': invoice_date,
            'journal_id': journal_id,
            'currency_id': currency_id,
            'invoice_payment_term_id': payment_term_id,
            'invoice_line_ids': [
                Command.create({
                    'name': 'My Super Product',
                    'account_id': account_id,
                    'quantity': quantity,
                    'price_unit': price_unit,
                    'tax_ids': [Command.clear()],
                    'currency_id': cls.currency_data['currency'].id,
                }),
            ],
        })
        move.action_post()
        return move

    def test_multi_currencies(self):
        """ In this test we will do two moves with same currency (Gol) and 3 payments for the first move with
            3 different currencies (Gol, Dar, USD)
        """
        first_bill = self.create_move_one_line(
            partner_id=self.partner_a.id,
            move_type='in_invoice',
            journal_id=self.company_data['default_journal_purchase'].id,
            date='2023-01-21',
            invoice_date='2023-01-21',
            currency_id=self.currency_data['currency'].id,
            account_id=self.company_data['default_account_expense'].id,
            quantity=1,
            price_unit=800.0
        )

        self.create_move_one_line(
            partner_id=self.partner_a.id,
            move_type='in_invoice',
            journal_id=self.company_data['default_journal_purchase'].id,
            date='2023-01-21',
            invoice_date='2023-01-21',
            currency_id=self.currency_data['currency'].id,
            account_id=self.company_data['default_account_expense'].id,
            quantity=1,
            price_unit=200.0
        )

        self.pay_move(
            first_bill,
            400,
            '2023-01-21',
            account_type=self.company_data['default_account_payable'].account_type,
            currency=self.currency_data['currency']
        )

        self.pay_move(
            first_bill,
            250,
            '2023-01-21',
            account_type=self.company_data['default_account_payable'].account_type,
            currency=self.currency_data_2['currency']
        )

        self.pay_move(
            first_bill,
            150,
            '2023-01-21',
            account_type=self.company_data['default_account_payable'].account_type,
            currency=self.company_data['currency']
        )

        # Test the report in 2023.
        options = self._generate_options(self.report, '2023-01-01', '2023-12-31')
        options['unfold_all'] = True

        self.assertLinesValues(
            # pylint: disable=C0326
            self.report._get_lines(options),
            #   Name                       Balance in foreign currency     Balance at op. rate     Balance at curr rate     Adjustment
            [   0,                                                  1,                      2,                       3,              4],
            [
                ('Accounts To Adjust',                             '',                     '',                      '',             ''),
                ('Gol (1 USD = 4.0 Gol)',                      -200.0,                 -200.0,                   -50.0,          150.0),
                ('211000 Account Payable',                     -200.0,                 -200.0,                   -50.0,          150.0),
                ('BILL/2023/01/0002',                          -200.0,                 -200.0,                   -50.0,          150.0),
                ('Total 211000 Account Payable',               -200.0,                 -200.0,                   -50.0,          150.0),
                ('Total Gol',                                  -200.0,                 -200.0,                   -50.0,          150.0),
            ],
            options,
            currency_map={
                1: {'currency': self.currency_data['currency']},
            },
        )

    def test_same_currency(self):
        """ In this test we will do two moves with same currency and a bank statement line to reconcile the first payment.
            The payment and the move have the same currency (Gol)
        """
        first_bill = self.create_move_one_line(
            partner_id=self.partner_a.id,
            move_type='in_invoice',
            journal_id=self.company_data['default_journal_purchase'].id,
            date='2023-01-21',
            invoice_date='2023-01-21',
            currency_id=self.currency_data['currency'].id,
            account_id=self.company_data['default_account_expense'].id,
            quantity=1,
            price_unit=800.0
        )

        self.create_move_one_line(
            partner_id=self.partner_a.id,
            move_type='in_invoice',
            journal_id=self.company_data['default_journal_purchase'].id,
            date='2023-01-21',
            invoice_date='2023-01-21',
            currency_id=self.currency_data['currency'].id,
            account_id=self.company_data['default_account_expense'].id,
            quantity=1,
            price_unit=200.0
        )

        bank_statement = self.env['account.bank.statement.line'].create({
            'journal_id': self.company_data['default_journal_bank'].id,
            'payment_ref': 'payment_move_line',
            'partner_id': self.partner_a.id,
            'foreign_currency_id': self.currency_data['currency'].id,
            'amount': -400,
            'amount_currency': -800,
            'date': '2023-01-01',
        })

        wizard = self.env['bank.rec.widget'].with_context(default_st_line_id=bank_statement.id).new({})
        wizard._action_add_new_amls(first_bill.line_ids.filtered(lambda account: account.account_type == 'liability_payable'))
        wizard._action_validate()

        # Test the report in 2023.
        options = self._generate_options(self.report, '2023-01-01', '2023-12-31')
        options['unfold_all'] = True

        self.assertLinesValues(
            # pylint: disable=C0326
            self.report._get_lines(options),
            #   Name                       Balance in foreign currency     Balance at op. rate     Balance at curr rate     Adjustment
            [   0,                                                  1,                      2,                       3,              4],
            [
                ('Accounts To Adjust',                             '',                    '',                       '',             ''),
                ('Gol (1 USD = 4.0 Gol)',                      -200.0,                -200.0,                    -50.0,          150.0),
                ('211000 Account Payable',                     -200.0,                -200.0,                    -50.0,          150.0),
                ('BILL/2023/01/0002',                          -200.0,                -200.0,                    -50.0,          150.0),
                ('Total 211000 Account Payable',               -200.0,                -200.0,                    -50.0,          150.0),
                ('Total Gol',                                  -200.0,                -200.0,                    -50.0,          150.0),
            ],
            options,
            currency_map={
                1: {'currency': self.currency_data['currency']},
            },
        )

    def test_exclude_account_for_adjustment_entry(self):
        """ In this test we will check if the exclude functionality of the report works as intended. We will do a bill
            and an invoice. Then we will do a bank statement line to reconcile a part of the bill.
            So the bill has a partial payment and should still be there in the report, and the invoice has no payment.
            We then exclude the rest of the bill.
        """

        first_bill = self.create_move_one_line(
            partner_id=self.partner_a.id,
            move_type='in_invoice',
            journal_id=self.company_data['default_journal_purchase'].id,
            date='2023-01-01',
            invoice_date='2023-01-01',
            currency_id=self.currency_data['currency'].id,
            account_id=self.company_data['default_account_expense'].id,
            quantity=1,
            price_unit=800.0
        )

        # Invoice
        self.create_move_one_line(
            partner_id=self.partner_a.id,
            move_type='out_invoice',
            journal_id=self.company_data['default_journal_sale'].id,
            date='2023-01-01',
            invoice_date='2023-01-01',
            currency_id=self.currency_data['currency'].id,
            account_id=self.copy_account(self.company_data['default_account_revenue']).id,
            quantity=1,
            price_unit=100.0
        )

        bank_statement = self.env['account.bank.statement.line'].create({
            'journal_id': self.company_data['default_journal_bank'].id,
            'payment_ref': 'payment_move_line',
            'partner_id': self.partner_a.id,
            'foreign_currency_id': self.currency_data['currency'].id,
            'amount': -300,
            'amount_currency': -600,
            'date': '2023-01-01',
        })

        wizard = self.env['bank.rec.widget'].with_context(default_st_line_id=bank_statement.id).new({})
        wizard._action_add_new_amls(first_bill.line_ids.filtered(lambda account: account.account_type == 'liability_payable'))
        wizard._action_validate()

        # Test the report in 2023.
        options = self._generate_options(self.report, '2023-01-01', '2023-12-31')
        options['unfold_all'] = True
        self.assertLinesValues(
            # pylint: disable=C0326
            self.report._get_lines(options),
            #   Name                       Balance in foreign currency     Balance at op. rate     Balance at curr rate     Adjustment
            [   0,                                                  1,                      2,                       3,              4],
            [
                ('Accounts To Adjust',                             '',                     '',                      '',             ''),
                ('Gol (1 USD = 4.0 Gol)',                      -100.0,                  -50.0,                   -25.0,           25.0),
                ('121000 Account Receivable',                   100.0,                   50.0,                    25.0,          -25.0),
                ('INV/2023/00001 INV/2023/00001',               100.0,                   50.0,                    25.0,          -25.0),
                ('Total 121000 Account Receivable',             100.0,                   50.0,                    25.0,          -25.0),
                ('211000 Account Payable',                     -200.0,                 -100.0,                   -50.0,           50.0),
                ('BILL/2023/01/0001',                          -200.0,                 -100.0,                   -50.0,           50.0),
                ('Total 211000 Account Payable',               -200.0,                 -100.0,                   -50.0,           50.0),
                ('Total Gol',                                  -100.0,                  -50.0,                   -25.0,           25.0),
            ],
            options,
            currency_map={
                1: {'currency': self.currency_data['currency']},
            },
        )

        oldest_line_id = self.report._get_generic_line_id('account.report.line', self.env.ref('account_reports.multicurrency_revaluation_to_adjust').id)
        old_line_id = self.report._get_generic_line_id('res.currency', self.currency_data['currency'].id, markup='groupby:currency_id', parent_line_id=oldest_line_id)
        line_id = self.report._get_generic_line_id('account.account', first_bill.line_ids.account_id.filtered(lambda account: account.account_type == 'liability_payable').id, markup='groupby:account_id', parent_line_id=old_line_id)

        self.env['account.multicurrency.revaluation.report.handler'].action_multi_currency_revaluation_toggle_provision(options, {'line_id': line_id})
        options['unfold_all'] = True

        self.assertLinesValues(
            # pylint: disable=C0326
            self.report._get_lines(options),
            #   Name                       Balance in foreign currency     Balance at op. rate     Balance at curr rate     Adjustment
            [   0,                                                  1,                      2,                       3,              4],
            [
                ('Accounts To Adjust',                             '',                     '',                      '',             ''),
                ('Gol (1 USD = 4.0 Gol)',                       100.0,                   50.0,                    25.0,          -25.0),
                ('121000 Account Receivable',                   100.0,                   50.0,                    25.0,          -25.0),
                ('INV/2023/00001 INV/2023/00001',               100.0,                   50.0,                    25.0,          -25.0),
                ('Total 121000 Account Receivable',             100.0,                   50.0,                    25.0,          -25.0),
                ('Total Gol',                                   100.0,                   50.0,                    25.0,          -25.0),

                ('Excluded Accounts',                              '',                     '',                      '',             ''),
                ('Gol (1 USD = 4.0 Gol)',                      -200.0,                 -100.0,                   -50.0,           50.0),
                ('211000 Account Payable',                     -200.0,                 -100.0,                   -50.0,           50.0),
                ('BILL/2023/01/0001',                          -200.0,                 -100.0,                   -50.0,           50.0),
                ('Total 211000 Account Payable',               -200.0,                 -100.0,                   -50.0,           50.0),
                ('Total Gol',                                  -200.0,                 -100.0,                   -50.0,           50.0),
            ],
            options,
            currency_map={
                1: {'currency': self.currency_data['currency']},
            },
        )

    def test_same_rate(self):
        """ Make sure no adjustment lines are generated if the rate is unchanged
           (i.e. do not create 0 balance adjustment lines)
        """
        self.create_move_one_line(
            partner_id=self.partner_a.id,
            move_type='in_invoice',
            journal_id=self.company_data['default_journal_purchase'].id,
            date='2023-01-21',
            invoice_date='2023-01-21',
            currency_id=self.currency_data['currency'].id,
            account_id=self.company_data['default_account_expense'].id,
            quantity=1,
            price_unit=1000.0,
        )

        options = self._generate_options(self.report, '2023-01-21', '2023-01-21')
        options['unfold_all'] = True

        # Check the gold currency.
        self.assertLinesValues(
            # pylint: disable = C0326
            self.report._get_lines(options),
            #   Name                       Balance in foreign currency     Balance at op. rate     Balance at curr rate     Adjustment
            [   0,                                                  1,                      2,                       3,              4],
            [
                ('Accounts To Adjust',                             '',                     '',                      '',             ''),
                ('Gol (1 USD = 1.0 Gol)',                     -1000.0,                -1000.0,                 -1000.0,            0.0),
                ('211000 Account Payable',                    -1000.0,                -1000.0,                 -1000.0,            0.0),
                ('BILL/2023/01/0001',                         -1000.0,                -1000.0,                 -1000.0,            0.0),
                ('Total 211000 Account Payable',              -1000.0,                -1000.0,                 -1000.0,            0.0),
                ('Total Gol',                                 -1000.0,                -1000.0,                 -1000.0,            0.0),
            ],
            options,
            currency_map={
                1: {'currency': self.currency_data['currency']},
            },
        )

        with self.assertRaises(UserError, msg="No adjustment should be needed"):
            self.env.context = {**self.env.context, 'multicurrency_revaluation_report_options': {**options, 'unfold_all': False}}
            self.env['account.multicurrency.revaluation.wizard'].create({
                'journal_id': self.company_data['default_journal_misc'].id,
                'expense_provision_account_id': self.company_data['default_account_expense'].id,
                'income_provision_account_id': self.company_data['default_account_revenue'].id,
            })

    def test_changing_rate_between_move_and_payment(self):
        """ In this test, we will do a use case where a move is created and before the payment is done, the rate of the
            currency changes. We deal with the possibility to have multiple payment for a move with different dates and rates
        """
        bill = self.create_move_one_line(
            partner_id=self.partner_a.id,
            move_type='in_invoice',
            journal_id=self.company_data['default_journal_purchase'].id,
            date='2023-01-21',
            invoice_date='2023-01-21',
            currency_id=self.currency_data['currency'].id,
            account_id=self.company_data['default_account_expense'].id,
            quantity=1,
            price_unit=1000.0,
        )

        options = self._generate_options(self.report, '2023-01-01', '2023-01-26')
        options['unfold_all'] = True
        self.assertLinesValues(
            # pylint: disable=C0326
            self.report._get_lines(options),
            #   Name                       Balance in foreign currency     Balance at op. rate     Balance at curr rate     Adjustment
            [   0,                                                  1,                      2,                       3,              4],
            [
                ('Accounts To Adjust',                              '',                    '',                      '',             ''),
                ('Gol (1 USD = 2.0 Gol)',                      -1000.0,               -1000.0,                  -500.0,          500.0),
                ('211000 Account Payable',                     -1000.0,               -1000.0,                  -500.0,          500.0),
                ('BILL/2023/01/0001',                          -1000.0,               -1000.0,                  -500.0,          500.0),
                ('Total 211000 Account Payable',               -1000.0,               -1000.0,                  -500.0,          500.0),
                ('Total Gol',                                  -1000.0,               -1000.0,                  -500.0,          500.0),
            ],
            options,
            currency_map={
                1: {'currency': self.currency_data['currency']},
            },
        )

        # First payment for the bill at the given date to check if it appears in the report when changing the date_to
        self.pay_move(
            bill,
            500,
            '2023-01-26',
            account_type=self.company_data['default_account_payable'].account_type,
            currency=self.currency_data['currency']
        )

        # Second payment at a later date to fully paid the bill
        self.pay_move(
            bill,
            500,
            '2023-02-01',
            account_type=self.company_data['default_account_payable'].account_type,
            currency=self.currency_data['currency']
        )

        options = self._generate_options(self.report, '2023-01-01', '2023-01-31')
        options['unfold_all'] = True
        self.assertLinesValues(
            # pylint: disable=C0326
            self.report._get_lines(options),
            #   Name                       Balance in foreign currency     Balance at op. rate     Balance at curr rate     Adjustment
            [   0,                                                  1,                      2,                       3,              4],
            [
                ('Accounts To Adjust',                             '',                     '',                      '',             ''),
                ('Gol (1 USD = 4.0 Gol)',                      -500.0,                 -500.0,                  -125.0,          375.0),
                ('211000 Account Payable',                     -500.0,                 -500.0,                  -125.0,          375.0),
                ('BILL/2023/01/0001',                          -500.0,                 -500.0,                  -125.0,          375.0),
                ('Total 211000 Account Payable',               -500.0,                 -500.0,                  -125.0,          375.0),
                ('Total Gol',                                  -500.0,                 -500.0,                  -125.0,          375.0),
            ],
            options,
            currency_map={
                1: {'currency': self.currency_data['currency']},
            },
        )

    @freeze_time('2023-01-26')
    def test_payment_in_company_currency_invoice_in_foreign_currency_fully_reconcile(self):
        """ In this test, we will create a move with a foreign currency and do a payment in the company currency,
            but thanks to the changing of rates, the move is fully reconcile
        """
        bill = self.create_move_one_line(
            partner_id=self.partner_a.id,
            move_type='in_invoice',
            journal_id=self.company_data['default_journal_purchase'].id,
            date='2023-01-21',
            invoice_date='2023-01-21',
            currency_id=self.currency_data['currency'].id,
            account_id=self.company_data['default_account_expense'].id,
            quantity=1,
            price_unit=1000.0,
        )

        # We pay the bill for 500 but thanks to the changing of the rate (1 --> 2), 500 become 1000 and the move is
        # fully reconciled, so we don't need to display anything on the report
        self.pay_move(
            bill,
            500,
            '2023-01-26',
            account_type=self.company_data['default_account_payable'].account_type,
            currency=self.company_data['currency'],
        )

        options = self._generate_options(self.report, '2023-01-01', '2023-02-20')
        self.assertEqual(len(self.report._get_lines(options)), 0)

    @freeze_time('2023-01-26')
    def test_payment_in_company_currency_invoice_in_foreign_currency_not_fully_reconcile(self):
        """ In this test, we will create a move with a foreign currency and do a payment in the company currency """
        bill = self.create_move_one_line(
            partner_id=self.partner_a.id,
            move_type='in_invoice',
            journal_id=self.company_data['default_journal_purchase'].id,
            date='2023-01-21',
            invoice_date='2023-01-21',
            currency_id=self.currency_data['currency'].id,
            account_id=self.company_data['default_account_expense'].id,
            quantity=1,
            price_unit=1000.0,
        )

        # We pay the first part of the bill, thanks to the changing of rates we have paid 600
        self.pay_move(
            bill,
            300,
            '2023-01-26',
            account_type=self.company_data['default_account_payable'].account_type,
            currency=self.company_data['currency'],
        )

        options = self._generate_options(self.report, '2023-01-01', '2023-01-26')
        options['unfold_all'] = True
        self.assertLinesValues(
            # pylint: disable=C0326
            self.report._get_lines(options),
            #   Name                       Balance in foreign currency     Balance at op. rate     Balance at curr rate     Adjustment
            [   0,                                                  1,                      2,                       3,              4],
            [
                ('Accounts To Adjust',                             '',                     '',                      '',             ''),
                ('Gol (1 USD = 2.0 Gol)',                      -400.0,                 -400.0,                  -200.0,          200.0),
                ('211000 Account Payable',                     -400.0,                 -400.0,                  -200.0,          200.0),
                ('BILL/2023/01/0001',                          -400.0,                 -400.0,                  -200.0,          200.0),
                ('Total 211000 Account Payable',               -400.0,                 -400.0,                  -200.0,          200.0),
                ('Total Gol',                                  -400.0,                 -400.0,                  -200.0,          200.0),
            ],
            options,
            currency_map={
                1: {'currency': self.currency_data['currency']},
            },
        )

        # We check the report again with other date to witness the new changing of rates
        options = self._generate_options(self.report, '2023-01-01', '2023-02-01')
        options['unfold_all'] = True
        self.assertLinesValues(
            # pylint: disable=C0326
            self.report._get_lines(options),
            #   Name                       Balance in foreign currency     Balance at op. rate     Balance at curr rate     Adjustment
            [   0,                                                  1,                      2,                       3,              4],
            [
                ('Accounts To Adjust',                             '',                     '',                      '',             ''),
                ('Gol (1 USD = 4.0 Gol)',                      -400.0,                 -400.0,                  -100.0,          300.0),
                ('211000 Account Payable',                     -400.0,                 -400.0,                  -100.0,          300.0),
                ('BILL/2023/01/0001',                          -400.0,                 -400.0,                  -100.0,          300.0),
                ('Total 211000 Account Payable',               -400.0,                 -400.0,                  -100.0,          300.0),
                ('Total Gol',                                  -400.0,                 -400.0,                  -100.0,          300.0),
            ],
            options,
            currency_map={
                1: {'currency': self.currency_data['currency']},
            },
        )

    @freeze_time('2023-01-28')
    def test_pay_all_move_check_before_full_payment(self):
        """ In this test we pay all the move, and then we check when coming back before the payment if the report display
            the lines.
        """
        bill = self.create_move_one_line(
            partner_id=self.partner_a.id,
            move_type='in_invoice',
            journal_id=self.company_data['default_journal_purchase'].id,
            date='2023-01-21',
            invoice_date='2023-01-21',
            currency_id=self.currency_data['currency'].id,
            account_id=self.company_data['default_account_expense'].id,
            quantity=1,
            price_unit=1000.0,
        )

        # We pay the first part of the bill, thanks to the changing of rates we have paid 600
        self.pay_move(
            bill,
            1000,
            '2023-01-28',
            account_type=self.company_data['default_account_payable'].account_type,
            currency=self.company_data['currency'],
        )

        # The report shouldn't display anything after the full payment.
        options = self._generate_options(self.report, '2023-01-01', '2023-01-29')
        options['unfold_all'] = True
        self.assertEqual(len(self.report._get_lines(options)), 0)

        # The report should display the bill before the full payment.
        options = self._generate_options(self.report, '2023-01-01', '2023-01-26')
        options['unfold_all'] = True
        self.assertLinesValues(
            # pylint: disable=C0326
            self.report._get_lines(options),
            #   Name                       Balance in foreign currency     Balance at op. rate     Balance at curr rate     Adjustment
            [   0,                                                  1,                      2,                       3,              4],
            [
                ('Accounts To Adjust',                             '',                     '',                      '',             ''),
                ('Gol (1 USD = 2.0 Gol)',                     -1000.0,                -1000.0,                  -500.0,          500.0),
                ('211000 Account Payable',                    -1000.0,                -1000.0,                  -500.0,          500.0),
                ('BILL/2023/01/0001',                         -1000.0,                -1000.0,                  -500.0,          500.0),
                ('Total 211000 Account Payable',              -1000.0,                -1000.0,                  -500.0,          500.0),
                ('Total Gol',                                 -1000.0,                -1000.0,                  -500.0,          500.0),
            ],
            options,
            currency_map={
                1: {'currency': self.currency_data['currency']},
            },
        )

    @freeze_time('2023-01-26')
    def test_move_credit_note(self):
        """ Create a credit note, change the currency rate and then the payment. Check if the report gives the correct
            values before and after the payment
        """
        bill = self.create_move_one_line(
            partner_id=self.partner_a.id,
            move_type='in_invoice',
            journal_id=self.company_data['default_journal_purchase'].id,
            date='2023-01-21',
            invoice_date='2023-01-21',
            currency_id=self.currency_data['currency'].id,
            account_id=self.company_data['default_account_expense'].id,
            quantity=1,
            price_unit=1000.0,
        )

        options = self._generate_options(self.report, '2023-01-01', '2023-01-30')
        options['unfold_all'] = True
        self.assertEqual(len(self.report._get_lines(options)), 6)

        self.pay_move(
            bill,
            1000,
            '2023-01-26',
            account_type=self.company_data['default_account_payable'].account_type,
            currency=self.company_data['currency'],
        )

        options = self._generate_options(self.report, '2023-01-01', '2023-01-30')
        options['unfold_all'] = True

        self.assertEqual(len(self.report._get_lines(options)), 0)

        move_reversal = self.env['account.move.reversal'].with_context(active_model='account.move', active_ids=bill.ids).create({
            'journal_id': bill.journal_id.id,
            'date': '2023-01-26'
        })
        reversal = move_reversal.reverse_moves()
        self.env['account.move'].browse(reversal['res_id']).action_post()

        self.assertLinesValues(
            # pylint: disable=C0326
            self.report._get_lines(options),
            #   Name                                               Balance in foreign currency     Balance at op. rate     Balance at curr rate     Adjustment
            [   0,                                                                          1,                      2,                       3,              4],
            [
                ('Accounts To Adjust',                                                     '',                     '',                      '',             ''),
                ('Gol (1 USD = 4.0 Gol)',                                              1000.0,                  500.0,                   250.0,         -250.0),
                ('211000 Account Payable',                                             1000.0,                  500.0,                   250.0,         -250.0),
                ('RBILL/2023/01/0001 (Reversal of: BILL/2023/01/0001)',                1000.0,                  500.0,                   250.0,         -250.0),
                ('Total 211000 Account Payable',                                       1000.0,                  500.0,                   250.0,         -250.0),
                ('Total Gol',                                                          1000.0,                  500.0,                   250.0,         -250.0),
            ],
            options,
            currency_map={
                1: {'currency': self.currency_data['currency']},
            },
        )

    @freeze_time('2023-01-26')
    def test_with_payment_term(self):
        """ In this test, we will create a new payment term where you need to pay 30% of the amount directly, and then
            you have 60 days for the rest. We will check the report before and after the payment to make sure it's working
            correctly.
        """
        account_payment_term_advance_60days = self.env['account.payment.term'].create({
            'name': "account_payment_term_advance_60days",
            'company_id': self.company_data['company'].id,
            'line_ids': [
                Command.create({
                    'value_amount': 30,
                    'value': 'percent',
                    'nb_days': 0,
                }),
                Command.create({
                    'value_amount': 70,
                    'value': 'percent',
                    'nb_days': 60,
                }),
            ]
        })

        bill = self.create_move_one_line(
            partner_id=self.partner_a.id,
            move_type='in_invoice',
            journal_id=self.company_data['default_journal_purchase'].id,
            date='2023-01-21',
            invoice_date='2023-01-21',
            currency_id=self.currency_data['currency'].id,
            account_id=self.company_data['default_account_expense'].id,
            quantity=1,
            price_unit=1000.0,
            payment_term_id=account_payment_term_advance_60days.id,
        )

        options = self._generate_options(self.report, '2023-01-01', '2023-01-30')
        options['unfold_all'] = True
        self.assertLinesValues(
            # pylint: disable=C0326
            self.report._get_lines(options),
            #   Name                       Balance in foreign currency     Balance at op. rate     Balance at curr rate     Adjustment
            [   0,                                                  1,                      2,                       3,              4],
            [
                ('Accounts To Adjust',                             '',                     '',                      '',             ''),
                ('Gol (1 USD = 4.0 Gol)',                     -1000.0,                -1000.0,                  -250.0,          750.0),
                ('211000 Account Payable',                    -1000.0,                -1000.0,                  -250.0,          750.0),
                ('BILL/2023/01/0001 installment #1',           -300.0,                 -300.0,                   -75.0,          225.0),
                ('BILL/2023/01/0001 installment #2',           -700.0,                 -700.0,                  -175.0,          525.0),
                ('Total 211000 Account Payable',              -1000.0,                -1000.0,                  -250.0,          750.0),
                ('Total Gol',                                 -1000.0,                -1000.0,                  -250.0,          750.0),
            ],
            options,
            currency_map={
                1: {'currency': self.currency_data['currency']},
            },
        )

        # The price is double since the rate is x2 So the amount of the payment is 300
        self.pay_move(
            bill,
            150,
            '2023-01-26',
            account_type=self.company_data['default_account_payable'].account_type,
            currency=self.company_data['currency'],
        )

        self.assertLinesValues(
            # pylint: disable=C0326
            self.report._get_lines(options),
            #   Name                       Balance in foreign currency     Balance at op. rate     Balance at curr rate     Adjustment
            [   0,                                                  1,                      2,                       3,              4],
            [
                ('Accounts To Adjust',                             '',                     '',                      '',             ''),
                ('Gol (1 USD = 4.0 Gol)',                      -700.0,                 -700.0,                  -175.0,          525.0),
                ('211000 Account Payable',                     -700.0,                 -700.0,                  -175.0,          525.0),
                ('BILL/2023/01/0001 installment #2',           -700.0,                 -700.0,                  -175.0,          525.0),
                ('Total 211000 Account Payable',               -700.0,                 -700.0,                  -175.0,          525.0),
                ('Total Gol',                                  -700.0,                 -700.0,                  -175.0,          525.0),
            ],
            options,
            currency_map={
                1: {'currency': self.currency_data['currency']},
            },
        )

        # We check when coming back before the payment the lines are ok
        options = self._generate_options(self.report, '2023-01-01', '2023-01-25')
        options['unfold_all'] = True
        self.assertLinesValues(
            # pylint: disable=C0326
            self.report._get_lines(options),
            #   Name                       Balance in foreign currency     Balance at op. rate     Balance at curr rate     Adjustment
            [   0,                                                  1,                      2,                       3,              4],
            [
                ('Accounts To Adjust',                             '',                     '',                      '',             ''),
                ('Gol (1 USD = 2.0 Gol)',                     -1000.0,                -1000.0,                  -500.0,          500.0),
                ('211000 Account Payable',                    -1000.0,                -1000.0,                  -500.0,          500.0),
                ('BILL/2023/01/0001 installment #1',           -300.0,                 -300.0,                  -150.0,          150.0),
                ('BILL/2023/01/0001 installment #2',           -700.0,                 -700.0,                  -350.0,          350.0),
                ('Total 211000 Account Payable',              -1000.0,                -1000.0,                  -500.0,          500.0),
                ('Total Gol',                                 -1000.0,                -1000.0,                  -500.0,          500.0),
            ],
            options,
            currency_map={
                1: {'currency': self.currency_data['currency']},
            },
        )

    def test_transfer_invoice_to_another_partner(self):
        """ This test verifies that we still find the bill amount in the report when payable is move
            to another partner.
        """
        bill = self.create_move_one_line(
            partner_id=self.partner_a.id,
            move_type='in_invoice',
            journal_id=self.company_data['default_journal_purchase'].id,
            date='2023-01-21',
            invoice_date='2023-01-21',
            currency_id=self.currency_data['currency'].id,
            account_id=self.company_data['default_account_expense'].id,
            quantity=1,
            price_unit=1000.0
        )

        entry = self.env['account.move'].create({
            'move_type': 'entry',
            'journal_id': self.company_data['default_journal_misc'].id,
            'date': '2023-01-22',
            'line_ids': [
                Command.create({
                    'partner_id': self.partner_a.id,
                    'currency_id': self.currency_data['currency'].id,
                    'amount_currency': 1000.0,
                    'account_id': self.company_data['default_account_payable'].id,
                }),
                Command.create({
                    'partner_id': self.partner_b.id,
                    'currency_id': self.currency_data['currency'].id,
                    'amount_currency': -1000.0,
                    'account_id': self.company_data['default_account_payable'].id,
                }),
            ]
        })
        entry.action_post()

        lines_to_reconcile = entry.line_ids.filtered(lambda line: line.partner_id == self.partner_a and line.account_type == self.company_data['default_account_payable'].account_type)
        lines_to_reconcile += bill.line_ids.filtered(lambda line: line.account_type == self.company_data['default_account_payable'].account_type)
        lines_to_reconcile.reconcile()

        options = self._generate_options(self.report, '2023-01-01', '2023-01-31')
        options['unfold_all'] = True
        self.assertLinesValues(
            # pylint: disable=C0326
            self.report._get_lines(options),
            #   Name                       Balance in foreign currency     Balance at op. rate     Balance at curr rate     Adjustment
            [   0,                                                  1,                      2,                       3,              4],
            [
                ('Accounts To Adjust',                             '',                     '',                      '',             ''),
                ('Gol (1 USD = 4.0 Gol)',                     -1000.0,                -1000.0,                  -250.0,          750.0),
                ('211000 Account Payable',                    -1000.0,                -1000.0,                  -250.0,          750.0),
                ('MISC/2023/01/0001',                         -1000.0,                -1000.0,                  -250.0,          750.0),
                ('Total 211000 Account Payable',              -1000.0,                -1000.0,                  -250.0,          750.0),
                ('Total Gol',                                 -1000.0,                -1000.0,                  -250.0,          750.0),
            ],
            options,
            currency_map={
                1: {'currency': self.currency_data['currency']},
            },
        )

    @freeze_time('2023-01-26')
    def test_refund_invoice_keep_exchange_diff_line(self):
        """ Create an invoice, cancel it with a credit note.
            Check the report, unreconcile the credit note and
            check the report again.
        """
        # Create a customer invoice with a rate of 1 USD = 1 Gol
        invoice = self.create_move_one_line(
            partner_id=self.partner_a.id,
            move_type='out_invoice',
            journal_id=self.company_data['default_journal_sale'].id,
            date='2023-01-21',
            invoice_date='2023-01-21',
            currency_id=self.currency_data['currency'].id,
            account_id=self.company_data['default_account_revenue'].id,
            quantity=1,
            price_unit=1000.0,
        )

        # Reverse the customer invoice with a rate of 1 USD = 2 Gol to create a partial credit note
        move_reversal = self.env['account.move.reversal'].with_context(active_model='account.move', active_ids=invoice.ids).create({
            'journal_id': invoice.journal_id.id,
            'date': '2023-01-26',
        })
        reversal = move_reversal.reverse_moves()
        credit_note = self.env['account.move'].browse(reversal['res_id'])
        credit_note.invoice_line_ids[0].price_unit = 300  # Only reverse for 300
        credit_note.action_post()
        line_to_reconciles = (invoice + credit_note).line_ids.filtered(lambda l: l.account_type == self.company_data['default_account_receivable'].account_type)

        #  Checking the report after reconciliation between the invoice and the credit note (Rate 1 USD = 4 Gol)
        options = self._generate_options(self.report, '2023-01-01', '2023-01-30')
        options['unfold_all'] = True
        self.assertLinesValues(
            # pylint: disable=C0326
            self.report._get_lines(options),
            #   Name                       Balance in foreign currency     Balance at op. rate     Balance at curr rate     Adjustment
            [   0,                                                  1,                      2,                       3,              4],
            [
                ('Accounts To Adjust',                             '',                     '',                      '',             ''),
                ('Gol (1 USD = 4.0 Gol)',                       700.0,                  700.0,                   175.0,         -525.0),
                ('121000 Account Receivable',                   700.0,                  700.0,                   175.0,         -525.0),
                ('INV/2023/00001 INV/2023/00001',               700.0,                  700.0,                   175.0,         -525.0),
                ('Total 121000 Account Receivable',             700.0,                  700.0,                   175.0,         -525.0),
                ('Total Gol',                                   700.0,                  700.0,                   175.0,         -525.0),
            ],
            options,
            currency_map={
                1: {'currency': self.currency_data['currency']},
            },
        )

        # Delete the reconciliation
        partial = self.env['account.partial.reconcile'].search([
            ('debit_move_id', '=', line_to_reconciles[0].id),
            ('credit_move_id', '=', line_to_reconciles[1].id),
        ])
        partial.unlink()

        # Check the report in february, the exchange diff should disappear as it was computed in january (Rate 1 USD = 4 Gol)
        options = self._generate_options(self.report, '2023-01-01', '2023-02-15')
        options['unfold_all'] = True
        self.assertLinesValues(
            # pylint: disable=C0326
            self.report._get_lines(options),
            #   Name                                           Balance in foreign currency     Balance at op. rate     Balance at curr rate     Adjustment
            [   0,                                                                      1,                      2,                       3,              4],
            [
                ('Accounts To Adjust',                                                 '',                     '',                      '',             ''),
                ('Gol (1 USD = 4.0 Gol)',                                           700.0,                  850.0,                   175.0,         -675.0),
                ('121000 Account Receivable',                                       700.0,                  850.0,                   175.0,         -675.0),
                ('RINV/2023/00001 (Reversal of: INV/2023/00001)',                  -300.0,                 -150.0,                   -75.0,           75.0),
                ('INV/2023/00001 INV/2023/00001',                                  1000.0,                 1000.0,                   250.0,         -750.0),
                ('Total 121000 Account Receivable',                                 700.0,                  850.0,                   175.0,         -675.0),
                ('Total Gol',                                                       700.0,                  850.0,                   175.0,         -675.0),
            ],
            options,
            currency_map={
                1: {'currency': self.currency_data['currency']},
            },
        )

    def test_invoice_with_different_rate_than_the_existing_one(self):
        """ This test has for purpose to check that the customized rate on an entry
            is well-kept. If a user creates an entry in multi currency and creates a
            rate for this entry specifically (by changing the debit/credit and amount_currency).
            The report should use this rate for the balance in foreign currency and the balance
            at operation rate.
        """
        # Special rate of 3
        entry = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2023-01-21',
            'journal_id': self.company_data['default_journal_misc'].id,
            'line_ids': [
                Command.create({
                    'name': 'expense line',
                    'debit': 300.0,
                    'credit': 0.0,
                    'currency_id': self.currency_data['currency'].id,
                    'amount_currency': 900,
                    'account_id': self.company_data['default_account_expense'].id,
                }),
                Command.create({
                    'name': 'payable line',
                    'partner_id': self.partner_a.id,
                    'currency_id': self.currency_data['currency'].id,
                    'debit': 0.0,
                    'credit': 300.0,
                    'amount_currency': -900.0,
                    'account_id': self.company_data['default_account_payable'].id,
                }),
            ],
        })
        entry.action_post()

        # Opening the report for a rate at 4 instead of 3
        options = self._generate_options(self.report, '2023-01-01', '2023-01-31')
        options['unfold_all'] = True
        self.assertLinesValues(
            # pylint: disable=C0326
            self.report._get_lines(options),
            #   Name                       Balance in foreign currency     Balance at op. rate     Balance at curr rate     Adjustment
            [   0,                                                  1,                      2,                       3,              4],
            [
                ('Accounts To Adjust',                             '',                     '',                      '',             ''),
                ('Gol (1 USD = 4.0 Gol)',                      -900.0,                 -300.0,                  -225.0,           75.0),
                ('211000 Account Payable',                     -900.0,                 -300.0,                  -225.0,           75.0),
                ('MISC/2023/01/0001 payable line',             -900.0,                 -300.0,                  -225.0,           75.0),
                ('Total 211000 Account Payable',               -900.0,                 -300.0,                  -225.0,           75.0),
                ('Total Gol',                                  -900.0,                 -300.0,                  -225.0,           75.0),
            ],
            options,
            currency_map={
                1: {'currency': self.currency_data['currency']},
            },
        )

    def test_current_liability_reco_bank_journal_aml(self):
        """ This test creates a reconcilable current liability account with a foreign currency,
            creates an entry with this account and reconciles it with a bank journal aml.
            Before reconciliation, the bank journal aml shouldn't impact the report
            because the amount is already realized.
            Once this aml is reconciled with the current liability aml, the report should be impacted.
        """
        special_liability_current_account = self.env['account.account'].create({
            'name': '201 GOL',
            'code': '201',
            'account_type': 'liability_current',
            'reconcile': True,
            'currency_id': self.currency_data['currency'].id
        })
        self.company_data['default_journal_bank'].currency_id = self.currency_data['currency'].id

        entry = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2023-01-21',
            'journal_id': self.company_data['default_journal_misc'].id,
            'line_ids': [
                Command.create({
                    'name': 'liability line',
                    'debit': 50.0,
                    'credit': 0.0,
                    'currency_id': self.currency_data['currency'].id,
                    'amount_currency': 100.0,
                    'account_id': special_liability_current_account.id,
                }),
                Command.create({
                    'name': 'revenue line',
                    'currency_id': self.currency_data['currency'].id,
                    'debit': 0.0,
                    'credit': 50.0,
                    'amount_currency': -100.0,
                    'account_id': self.company_data['default_account_revenue'].id,
                }),
            ],
        })
        entry.action_post()

        self.env['account.bank.statement.line'].create({
            'journal_id': self.company_data['default_journal_bank'].id,
            'payment_ref': 'payment_move_line',
            'foreign_currency_id': self.currency_data['currency'].id,
            'amount': -10.0,
            'amount_currency': -30.0,
            'date': '2023-01-23',
        })

        bank_entry = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2023-01-23',
            'journal_id': self.company_data['default_journal_bank'].id,
            'line_ids': [
                Command.create({
                    'name': 'liability line',
                    'debit': 0.0,
                    'credit': 10.0,
                    'currency_id': self.currency_data['currency'].id,
                    'amount_currency': -30.0,
                    'account_id': special_liability_current_account.id,
                }),
                Command.create({
                    'name': 'revenue line',
                    'currency_id': self.currency_data['currency'].id,
                    'debit': 10.0,
                    'credit': 0.0,
                    'amount_currency': 30.0,
                    'account_id': self.company_data['default_journal_bank'].default_account_id.id,
                }),
            ],
        })
        bank_entry.action_post()

        # Checking the report before reconciliation
        options = self._generate_options(self.report, '2023-01-01', '2023-01-31')
        options['unfold_all'] = True
        self.assertLinesValues(
            # pylint: disable=C0326
            self.report._get_lines(options),
            #   Name                       Balance in foreign currency     Balance at op. rate     Balance at curr rate     Adjustment
            [   0,                                                  1,                      2,                       3,              4],
            [
                ('Accounts To Adjust',                             '',                     '',                      '',             ''),
                ('Gol (1 USD = 4.0 Gol)',                        90.0,                   40.0,                    22.5,          -17.5),
                ('101401 Bank',                                  20.0,                    0.0,                     5.0,            5.0),
                ('BNK1/2023/00002 revenue line',                 30.0,                   10.0,                     7.5,           -2.5),
                ('BNK1/2023/00001 payment_move_line',           -10.0,                  -10.0,                    -2.5,            7.5),
                ('Total 101401 Bank',                            20.0,                    0.0,                     5.0,            5.0),
                ('201 201 GOL',                                  70.0,                   40.0,                    17.5,          -22.5),
                ('BNK1/2023/00002 liability line',              -30.0,                  -10.0,                    -7.5,            2.5),
                ('MISC/2023/01/0001 liability line',            100.0,                   50.0,                    25.0,          -25.0),
                ('Total 201 201 GOL',                            70.0,                   40.0,                    17.5,          -22.5),
                ('Total Gol',                                    90.0,                   40.0,                    22.5,          -17.5),
            ],
            options,
            currency_map={
                1: {'currency': self.currency_data['currency']},
            },
        )

        line_to_reconciles = (entry + bank_entry).line_ids.filtered(lambda l: l.account_type == special_liability_current_account.account_type)
        line_to_reconciles.reconcile()

        # After reconciliation, the bank journal aml should impact the report
        options = self._generate_options(self.report, '2023-01-01', '2023-01-31')
        options['unfold_all'] = True
        self.assertLinesValues(
            # pylint: disable=C0326
            self.report._get_lines(options),
            #   Name                       Balance in foreign currency     Balance at op. rate     Balance at curr rate     Adjustment
            [   0,                                                  1,                      2,                       3,              4],
            [
                ('Accounts To Adjust',                             '',                     '',                      '',             ''),
                ('Gol (1 USD = 4.0 Gol)',                        90.0,                   35.0,                    22.5,          -12.5),
                ('101401 Bank',                                  20.0,                    0.0,                     5.0,            5.0),
                ('BNK1/2023/00002 revenue line',                 30.0,                   10.0,                     7.5,           -2.5),
                ('BNK1/2023/00001 payment_move_line',           -10.0,                  -10.0,                    -2.5,            7.5),
                ('Total 101401 Bank',                            20.0,                    0.0,                     5.0,            5.0),
                ('201 201 GOL',                                  70.0,                   35.0,                    17.5,          -17.5),
                ('MISC/2023/01/0001 liability line',             70.0,                   35.0,                    17.5,          -17.5),
                ('Total 201 201 GOL',                            70.0,                   35.0,                    17.5,          -17.5),
                ('Total Gol',                                    90.0,                   35.0,                    22.5,          -12.5),
            ],
            options,
            currency_map={
                1: {'currency': self.currency_data['currency']},
            },
        )

    def test_no_pl_account_present(self):
        """
            When putting a currency on a p&l account, the account should NOT be present in the report.
            This test will check that the exclusion of the account_type present in a p&l are not displayed.
        """

        self.company_data['default_account_expense'].currency_id = self.currency_data['currency'].id
        self.create_move_one_line(
            partner_id=self.partner_a.id,
            move_type='in_invoice',
            journal_id=self.company_data['default_journal_purchase'].id,
            date='2023-01-21',
            invoice_date='2023-01-21',
            currency_id=self.currency_data['currency'].id,
            account_id=self.company_data['default_account_expense'].id,
            quantity=1,
            price_unit=1000.0
        )

        options = self._generate_options(self.report, '2023-01-01', '2023-01-26')
        options['unfold_all'] = True
        self.assertLinesValues(
            # pylint: disable=C0326
            self.report._get_lines(options),
            #   Name                       Balance in foreign currency     Balance at op. rate     Balance at curr rate     Adjustment
            [0,                                                     1,                       2,                       3,             4],
            [
                ('Accounts To Adjust',                             '',                      '',                      '',            ''),
                ('Gol (1 USD = 2.0 Gol)',                     -1000.0,                 -1000.0,                  -500.0,         500.0),
                ('211000 Account Payable',                    -1000.0,                 -1000.0,                  -500.0,         500.0),
                ('BILL/2023/01/0001',                         -1000.0,                 -1000.0,                  -500.0,         500.0),
                ('Total 211000 Account Payable',              -1000.0,                 -1000.0,                  -500.0,         500.0),
                ('Total Gol',                                 -1000.0,                 -1000.0,                  -500.0,         500.0),
            ],
            options,
            currency_map={
                1: {'currency': self.currency_data['currency']},
            },
        )
