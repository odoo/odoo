# pylint: disable=C0326
from .common import TestAccountReportsCommon
from odoo import fields, Command
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestReconciliationReport(TestAccountReportsCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.other_currency = cls.setup_other_currency('EUR')
        cls.other_currency_2 = cls.setup_other_currency('GBP', rates=[('2016-01-01', 10.0), ('2017-01-01', 20.0)])

    def test_reconciliation_report_single_currency(self):
        """
            Tests the impact of positive/negative payments/statements on the reconciliation report in a single-currency
            environment.
        """
        bank_journal = self.env['account.journal'].create({
            'name': 'Bank',
            'code': 'BNKKK',
            'type': 'bank',
            'company_id': self.company_data['company'].id,
        })

        # ==== Statements ====

        self.env['account.bank.statement'].create({
            'name': 'statement_1',
            'date': '2014-12-31',
            'balance_start': 0.0,
            'balance_end_real': 100.0,
            'line_ids': [
                Command.create({'payment_ref': 'line_1', 'amount': 600.0, 'date': '2014-12-31', 'journal_id': bank_journal.id}),
                Command.create({'payment_ref': 'line_2', 'amount': -500.0, 'date': '2014-12-31', 'journal_id': bank_journal.id}),
            ],
        })

        statement_2 = self.env['account.bank.statement'].create({
            'name': 'statement_2',
            'date': '2015-01-05',
            'balance_start': 200.0,  # create an unexplained difference of 100.0.
            'balance_end_real': - 200.0,
            'journal_id': bank_journal.id,
            'line_ids': [
                Command.create({'payment_ref': 'line_1',    'amount': 100.0,    'date': '2015-01-01',    'partner_id': self.partner_a.id, 'journal_id': bank_journal.id}),
                Command.create({'payment_ref': 'line_2',    'amount': 200.0,    'date': '2015-01-02',                                    'journal_id': bank_journal.id}),
                Command.create({'payment_ref': 'line_3',    'amount': -300.0,    'date': '2015-01-03',    'partner_id': self.partner_a.id, 'journal_id': bank_journal.id}),
                Command.create({'payment_ref': 'line_4',    'amount': -400.0,    'date': '2015-01-04',                                    'journal_id': bank_journal.id}),
            ],
        })

        # ==== Payments ====
        self.inbound_payment_method_line.journal_id = bank_journal.id
        self.outbound_payment_method_line.journal_id = bank_journal.id
        payment_1 = self.env['account.payment'].create({
            'amount': 150.0,
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'date': '2015-01-01',
            'journal_id': bank_journal.id,
            'partner_id': self.partner_a.id,
            'payment_method_line_id': self.inbound_payment_method_line.id,
        })

        payment_2 = self.env['account.payment'].create({
            'amount': 250.0,
            'payment_type': 'outbound',
            'partner_type': 'supplier',
            'date': '2015-01-02',
            'journal_id': bank_journal.id,
            'partner_id': self.partner_a.id,
            'payment_method_line_id': self.outbound_payment_method_line.id,
        })

        payment_3 = self.env['account.payment'].create({
            'amount': 350.0,
            'payment_type': 'outbound',
            'partner_type': 'customer',
            'date': '2015-01-03',
            'journal_id': bank_journal.id,
            'partner_id': self.partner_a.id,
            'payment_method_line_id': self.inbound_payment_method_line.id,
        })

        payment_4 = self.env['account.payment'].create({
            'amount': 450.0,
            'payment_type': 'inbound',
            'partner_type': 'supplier',
            'date': '2015-01-04',
            'journal_id': bank_journal.id,
            'partner_id': self.partner_a.id,
            'payment_method_line_id': self.outbound_payment_method_line.id,
        })

        (payment_1 + payment_2 + payment_3 + payment_4).action_post()

        # ==== Reconciliation ====

        st_line = statement_2.line_ids.filtered(lambda line: line.payment_ref == 'line_1')
        payment_line = payment_1.move_id.line_ids.filtered(lambda line: line.account_id == payment_1.payment_method_line_id.payment_account_id)
        wizard = self.env['bank.rec.widget'].with_context(default_st_line_id=st_line.id).new({})
        wizard._action_add_new_amls(payment_line, allow_partial=False)
        wizard._action_validate()

        st_line = statement_2.line_ids.filtered(lambda line: line.payment_ref == 'line_3')
        payment_line = payment_2.move_id.line_ids.filtered(lambda line: line.account_id == payment_2.payment_method_line_id.payment_account_id)
        wizard = self.env['bank.rec.widget'].with_context(default_st_line_id=st_line.id).new({})
        wizard._action_add_new_amls(payment_line, allow_partial=False)
        wizard._action_validate()

        # ==== Report ====

        report = self.env.ref('account_reports.bank_reconciliation_report').with_context(
            active_id=bank_journal.id,
            active_model=bank_journal._name
        )

        options = self._generate_options(report, '2016-01-02', '2016-01-02')
        options['unfold_all'] = True
        lines = report._get_lines(options)

        self.assertLinesValues(
            lines,
            #   Name                                            Date            Amount
            [0,                                                   1,                3],
            [
                ('Balance of \'101405 Bank\'',                   '',           -200.0),
                ('Last statement balance',                       '',           -200.0),
                ('Including Unreconciled Receipts',              '',            200.0),
                ('BNKKK/2015/00002',                   '01/02/2015',            200.0),
                ('Including Unreconciled Payments',              '',           -400.0),
                ('BNKKK/2015/00004',                   '01/04/2015',           -400.0),
                ('Transactions without statement',               '',              0.0),
                ('Including Unreconciled Receipts',              '',              0.0),
                ('Including Unreconciled Payments',              '',              0.0),
                ('Misc. operations',                             '',              0.0),
                ('Outstanding Receipts/Payments',                '',            100.0),
                ('(+) Outstanding Receipts',                     '',            450.0),
                ('PBNKKK/2015/00004',                  '01/04/2015',            450.0),
                ('(-) Outstanding Payments',                     '',           -350.0),
                ('PBNKKK/2015/00003',                  '01/03/2015',           -350.0),
            ],
            options,
            currency_map={3: {'currency': bank_journal.currency_id}},
            ignore_folded=False,
        )

    def test_reconciliation_report_multi_currencies(self):
        """ Tests the management of multi-currencies in the reconciliation report. """
        self.env.user.groups_id |= self.env.ref('base.group_multi_currency')
        self.env.user.groups_id |= self.env.ref('base.group_no_one')

        company_currency = self.company_data['currency']  # USD
        journal_currency = self.other_currency  # EUR
        choco_currency = self.other_currency_2  # GBP

        # ==== Journal with a foreign currency ====

        bank_journal = self.env['account.journal'].create({
            'name': 'Bank',
            'code': 'BNKKK',
            'type': 'bank',
            'company_id': self.company_data['company'].id,
            'currency_id': journal_currency.id
        })

        # ==== Statement ====

        bank_statement = self.env['account.bank.statement'].create({
            'name': 'statement',
            'line_ids': [

                # Transaction in the company currency.
                (0, 0, {
                    'payment_ref': 'line_1',
                    'date': '2016-01-01',
                    'amount': 100.0,
                    'journal_id': bank_journal.id,
                    'amount_currency': 50.01,
                    'foreign_currency_id': company_currency.id,
                }),

                # Transaction in a third currency.
                (0, 0, {
                    'payment_ref': 'line_3',
                    'date': '2016-01-01',
                    'amount': 100.0,
                    'journal_id': bank_journal.id,
                    'amount_currency': 999.99,
                    'foreign_currency_id': choco_currency.id,
                }),

            ],
        })

        # Partially reconcile the suspense amount associated with each bank statement line
        suspense_account = bank_journal.suspense_account_id
        other_account = bank_journal.company_id.default_cash_difference_income_account_id

        # the first is in company currency
        bank_move_1 = bank_statement.line_ids[0].move_id
        bank_move_1_suspense_line = bank_move_1.line_ids.filtered(lambda l: l.account_id == suspense_account)
        bank_move_1.button_draft()
        bank_move_1.write({'line_ids': [
            Command.create({'account_id': other_account.id, 'credit': 10.00}),
            Command.update(bank_move_1_suspense_line.id, {'credit': 40.01}),
        ]})
        bank_move_1.action_post()

        # the second is in neither company nor journal currency
        bank_move_2 = bank_statement.line_ids[1].move_id
        bank_move_2_suspense_line = bank_move_2.line_ids.filtered(lambda l: l.account_id == suspense_account)
        bank_move_2.button_draft()
        bank_move_2.write({'line_ids': [
            Command.create({
                'account_id': other_account.id,
                'currency_id': bank_move_2_suspense_line.currency_id.id,
                'credit': 3.33,
                'amount_currency': -99.99
            }),
            Command.update(bank_move_2_suspense_line.id, {
                'credit': 30.0,
                'amount_currency': -900.0
            }),
        ]})
        bank_move_2.action_post()

        # ==== Payments ====
        self.inbound_payment_method_line.journal_id = bank_journal.id
        # Payment in the company's currency.
        payment_1 = self.env['account.payment'].create({
            'amount': 1000.0,
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'date': '2016-01-01',
            'journal_id': bank_journal.id,
            'partner_id': self.partner_a.id,
            'currency_id': company_currency.id,
            'payment_method_line_id': self.inbound_payment_method_line.id,
        })

        # Payment in the same foreign currency as the journal.
        payment_2 = self.env['account.payment'].create({
            'amount': 2000.0,
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'date': '2016-01-01',
            'journal_id': bank_journal.id,
            'partner_id': self.partner_a.id,
            'currency_id': journal_currency.id,
            'payment_method_line_id': self.inbound_payment_method_line.id,
        })

        # Payment in a third foreign currency.
        payment_3 = self.env['account.payment'].create({
            'amount': 3000.0,
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'date': '2016-01-01',
            'journal_id': bank_journal.id,
            'partner_id': self.partner_a.id,
            'currency_id': choco_currency.id,
            'payment_method_line_id': self.inbound_payment_method_line.id,
        })
        (payment_1 + payment_2 + payment_3).action_post()

        # ==== Misc Entry ====

        move = self.env['account.move'].create({
            'journal_id': self.company_data['default_journal_misc'].id,
            'date': '2016-01-01',
            'line_ids': [
                Command.create({
                    'name': 'Line1',
                    'debit': 100,
                    'credit': 0,
                    'amount_currency': 200,
                    'account_id': bank_journal.default_account_id.id,
                    'currency_id': journal_currency.id
                }),
                Command.create({
                    'name': 'Line2',
                    'debit': 0,
                    'credit': 100,
                    'account_id': other_account.id,
                }),
            ]
        })
        move.action_post()

        # ==== Report ====

        report = self.env.ref('account_reports.bank_reconciliation_report').with_context(
            active_id=bank_journal.id,
            active_model=bank_journal._name
        )

        with self.debug_mode():
            options = self._generate_options(report, '2016-01-02', '2016-01-02')
            options['unfold_all'] = True
            lines = report._get_lines(options)

            self.assertLinesValues(
                lines,
                #   Name                                                Date   Am. Cur.                  Cur.       Amount
                [0,                                                       1,       3,                      4,           5],
                [
                    ('Balance of \'101405 Bank\'',                       '',      '',                     '',       400.0),
                    ('Last statement balance',                           '',      '',                     '',       200.0),
                    ('Including Unreconciled Receipts',                  '',      '',                     '',       170.005),
                    ('BNKKK/2016/00002',                       '01/01/2016',  900.00,    choco_currency.name,        90.001),
                    ('BNKKK/2016/00001',                       '01/01/2016',   40.01,  company_currency.name,        80.004),
                    ('Including Unreconciled Payments',                  '',      '',                     '',         0.0),
                    ('Transactions without statement',                   '',      '',                     '',         0.0),
                    ('Including Unreconciled Receipts',                  '',      '',                     '',         0.0),
                    ('Including Unreconciled Payments',                  '',      '',                     '',         0.0),
                    ('Misc. operations',                                 '',      '',                     '',       200.0),
                    ('Outstanding Receipts/Payments',                    '',      '',                     '',      5900.0),
                    ('(+) Outstanding Receipts',                         '',      '',                     '',      5900.0),
                    ('PBNKKK/2016/00003',                      '01/01/2016',  3000.0,    choco_currency.name,       900.0),
                    ('PBNKKK/2016/00002',                      '01/01/2016',      '',                     '',      2000.0),
                    ('PBNKKK/2016/00001',                      '01/01/2016',  1000.0,  company_currency.name,      3000.0),
                    ('(-) Outstanding Payments',                         '',      '',                     '',         0.0),
                ],
                options,
                currency_map={
                    3: {'currency_code_index': 4},
                    5: {'currency': journal_currency},
                },
                ignore_folded=False,
            )

    def test_reconciliation_change_date(self):
        """
            Tests the impact of positive/negative payments/statements on the reconciliation report in a single-currency
            environment.
        """
        bank_journal = self.company_data['default_journal_bank']

        statement = self.env['account.bank.statement'].create({
            'name': 'statement_1',
            'date': '2019-01-10',
            'balance_start': 0.0,
            'balance_end_real': 130.0,
            'line_ids': [
                (0, 0, {'payment_ref': 'line_1', 'amount': 10.0, 'date': '2019-01-01', 'journal_id': bank_journal.id}),
                (0, 0, {'payment_ref': 'line_2', 'amount': 20.0, 'date': '2019-01-02', 'journal_id': bank_journal.id}),
                (0, 0, {'payment_ref': 'line_3', 'amount': 30.0, 'date': '2019-01-03', 'journal_id': bank_journal.id}),
                (0, 0, {'payment_ref': 'line_4', 'amount': -40.0, 'date': '2019-01-04', 'journal_id': bank_journal.id}),
                (0, 0, {'payment_ref': 'line_5', 'amount': 50.0, 'date': '2019-01-05', 'journal_id': bank_journal.id}),
                (0, 0, {'payment_ref': 'line_6', 'amount': 60.0, 'date': '2019-01-06', 'journal_id': bank_journal.id}),
            ],
        })

        # This will allow to test if the balance of the bank account is changed
        statement['balance_end_real'] = 140.0

        payment = self.env['account.payment'].create({
            'amount': 1000.0,
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'date': '2019-01-03',
            'journal_id': bank_journal.id,
            'partner_id': self.partner_a.id,
        })
        payment.action_post()

        report = self.env.ref('account_reports.bank_reconciliation_report').with_context(
            active_id=bank_journal.id,
            active_model='account.journal'
        )

        options = self._generate_options(report, fields.Date.from_string('2019-01-01'), fields.Date.from_string('2019-01-01'))
        options['all_entries'] = True
        options['unfold_all'] = True

        # The last statement is taken into account cause it has a line corresponding to the date of the report.
        lines = report._get_lines(options)
        self.assertLinesValues(
            lines,
            #   Name                                                             Date            Amount
            [0,                                                                    1,               3],
            [
                ('Balance of \'101401 Bank\'',                                    '',           140.0),
                ('Last statement balance',                                        '',           140.0),
                ('Including Unreconciled Receipts',                               '',            10.0),
                ('BNK1/2019/00001',                                     '01/01/2019',            10.0),
                ('Including Unreconciled Payments',                               '',             0.0),
                ('Transactions without statement',                                '',             0.0),
                ('Including Unreconciled Receipts',                               '',             0.0),
                ('Including Unreconciled Payments',                               '',             0.0),
                ('Misc. operations',                                              '',             0.0),
                ('Outstanding Receipts/Payments',                                 '',             0.0),
                ('(+) Outstanding Receipts',                                      '',             0.0),
                ('(-) Outstanding Payments',                                      '',             0.0),
            ],
            options,
            currency_map={3: {'currency': bank_journal.currency_id}},
            ignore_folded=False,
        )

        options = self._generate_options(report, fields.Date.from_string('2019-01-01'), fields.Date.from_string('2019-01-04'))
        options['all_entries'] = True
        options['unfold_all'] = True
        lines = report._get_lines(options)
        self.assertLinesValues(
            lines,
            #   Name                                                             Date            Amount
            [0,                                                                    1,               3],
            [
                ('Balance of \'101401 Bank\'',                                    '',           140.0),
                ('Last statement balance',                                        '',           140.0),
                ('Including Unreconciled Receipts',                               '',            60.0),
                ('BNK1/2019/00003',                                     '01/03/2019',            30.0),
                ('BNK1/2019/00002',                                     '01/02/2019',            20.0),
                ('BNK1/2019/00001',                                     '01/01/2019',            10.0),
                ('Including Unreconciled Payments',                               '',           -40.0),
                ('BNK1/2019/00004',                                     '01/04/2019',           -40.0),
                ('Transactions without statement',                                '',             0.0),
                ('Including Unreconciled Receipts',                               '',             0.0),
                ('Including Unreconciled Payments',                               '',             0.0),
                ('Misc. operations',                                              '',             0.0),
                ('Outstanding Receipts/Payments',                                 '',          1000.0),
                ('(+) Outstanding Receipts',                                      '',          1000.0),
                ('PBNK1/2019/00001',                                    '01/03/2019',          1000.0),
                ('(-) Outstanding Payments',                                      '',             0.0),
            ],
            options,
            currency_map={3: {'currency': bank_journal.currency_id}},
            ignore_folded=False,
        )

    def test_reconciliation_report_non_statement_payment(self):
        """
            Test that moves not linked to a bank statement/payment but linked for example to expenses are all showing in the
            report
        """
        bank_journal = self.env['account.journal'].create({
            'name': 'Bank',
            'code': 'BNKKK',
            'type': 'bank',
            'company_id': self.company_data['company'].id,
        })
        bank_journal.inbound_payment_method_line_ids.payment_account_id = self.inbound_payment_method_line.payment_account_id

        # ==== Misc ====
        self.env['account.move'].create({
            'journal_id': bank_journal.id,
            'date': '2014-12-31',
            'line_ids': [
                (0, 0, {
                    'name': 'Source',
                    'debit': 800,
                    'credit': 0,
                    'account_id': self.company_data['default_account_expense'].id,
                }),
                (0, 0, {
                    'name': 'Destination',
                    'debit': 0,
                    'credit': 800,
                    'account_id': self.inbound_payment_method_line.payment_account_id.id,
                }),
            ]
        }).action_post()

        self.env['account.move'].create({
            'journal_id': bank_journal.id,
            'date': '2015-12-31',
            'line_ids': [
                (0, 0, {
                    'name': 'Source',
                    'debit': 500,
                    'credit': 0,
                    'account_id': self.company_data['default_account_expense'].id,
                }),
                (0, 0, {
                    'name': 'Destination',
                    'debit': 0,
                    'credit': 500,
                    'account_id': self.inbound_payment_method_line.payment_account_id.id,
                }),
            ]
        }).action_post()

        # ==== Report ====

        report = self.env.ref('account_reports.bank_reconciliation_report').with_context(
            active_id=bank_journal.id,
            active_model='account.journal'
        )

        options = self._generate_options(report, '2016-01-02', '2016-01-02')
        options['unfold_all'] = True
        lines = report._get_lines(options)

        self.assertLinesValues(
            lines,
            #   Name                                                  Date         Amount
            [0,                                                         1,             3],
            [
                ('Balance of \'101405 Bank\'',                         '',           0.0),
                ('Last statement balance',                             '',           0.0),
                ('Including Unreconciled Receipts',                    '',           0.0),
                ('Including Unreconciled Payments',                    '',           0.0),
                ('Transactions without statement',                     '',           0.0),
                ('Including Unreconciled Receipts',                    '',           0.0),
                ('Including Unreconciled Payments',                    '',           0.0),
                ('Misc. operations',                                   '',           0.0),
                ('Outstanding Receipts/Payments',                      '',       -1300.0),
                ('(+) Outstanding Receipts',                           '',           0.0),
                ('(-) Outstanding Payments',                           '',       -1300.0),
                ('BNKKK/2015/00001',                         '12/31/2015',       -500.00),
                ('BNKKK/2014/00001',                         '12/31/2014',       -800.00),
            ],
            options,
            currency_map={3: {'currency': bank_journal.currency_id}},
            ignore_folded=False,
        )

    def test_reconciliation_report_misc_entry(self):
        """ This test will check if the report correctly display the misc entry """
        bank_journal = self.env['account.journal'].create({
            'name': 'Bank',
            'code': 'BNKKK',
            'type': 'bank',
            'company_id': self.company_data['company'].id,
        })

        # ==== Misc ====
        self.env['account.move'].create({
            'journal_id': bank_journal.id,
            'date': '2016-01-02',
            'line_ids': [
                (0, 0, {
                    'name': 'Source',
                    'debit': 800,
                    'credit': 0,
                    'account_id': bank_journal.default_account_id.id,
                }),
                (0, 0, {
                    'name': 'Destination',
                    'debit': 0,
                    'credit': 800,
                    'account_id': self.company_data['default_account_expense'].id,
                }),
            ]
        }).action_post()

        report = self.env.ref('account_reports.bank_reconciliation_report').with_context(
            active_id=bank_journal.id,
            active_model='account.journal'
        )

        options = self._generate_options(report, '2016-01-02', '2016-01-02')
        options['unfold_all'] = True
        lines = report._get_lines(options)

        self.assertLinesValues(
            lines,
            #   Name                                                  Date         Amount
            [0,                                                         1,             3],
            [
                ('Balance of \'101405 Bank\'',                         '',         800.0),
                ('Last statement balance',                             '',           0.0),
                ('Including Unreconciled Receipts',                    '',           0.0),
                ('Including Unreconciled Payments',                    '',           0.0),
                ('Transactions without statement',                     '',           0.0),
                ('Including Unreconciled Receipts',                    '',           0.0),
                ('Including Unreconciled Payments',                    '',           0.0),
                ('Misc. operations',                                   '',         800.0),
                ('Outstanding Receipts/Payments',                      '',           0.0),
                ('(+) Outstanding Receipts',                           '',           0.0),
                ('(-) Outstanding Payments',                           '',           0.0),
            ],
            options,
            currency_map={3: {'currency': bank_journal.currency_id}},
            ignore_folded=False,
        )

        # With the domain, since the date of the misc is not in the same year, the misc is not present
        options = self._generate_options(report, '2014-01-02', '2014-01-02')
        options['unfold_all'] = True
        lines = report._get_lines(options)

        self.assertLinesValues(
            lines,
            #   Name                                                  Date         Amount
            [0,                                                         1,             3],
            [
                ('Balance of \'101405 Bank\'',                         '',           0.0),
                ('Last statement balance',                             '',           0.0),
                ('Including Unreconciled Receipts',                    '',           0.0),
                ('Including Unreconciled Payments',                    '',           0.0),
                ('Transactions without statement',                     '',           0.0),
                ('Including Unreconciled Receipts',                    '',           0.0),
                ('Including Unreconciled Payments',                    '',           0.0),
                ('Misc. operations',                                   '',           0.0),
                ('Outstanding Receipts/Payments',                      '',           0.0),
                ('(+) Outstanding Receipts',                           '',           0.0),
                ('(-) Outstanding Payments',                           '',           0.0),
            ],
            options,
            currency_map={3: {'currency': bank_journal.currency_id}},
            ignore_folded=False,
        )

    def test_reconciliation_report_delete_statement(self):
        """ This test will do a basic flow where we create a statement and then we delete it to see how the report react"""

        bank_journal = self.company_data['default_journal_bank']

        statement = self.env['account.bank.statement'].create({
            'name': 'statement_1',
            'date': '2019-01-10',
            'balance_start': 0.0,
            'balance_end_real': 130.0,
            'line_ids': [
                (0, 0, {'payment_ref': 'line_1', 'amount': 10.0, 'date': '2019-01-01', 'journal_id': bank_journal.id}),
                (0, 0, {'payment_ref': 'line_2', 'amount': 20.0, 'date': '2019-01-02', 'journal_id': bank_journal.id}),
                (0, 0, {'payment_ref': 'line_3', 'amount': 30.0, 'date': '2019-01-03', 'journal_id': bank_journal.id}),
                (0, 0, {'payment_ref': 'line_4', 'amount': -40.0, 'date': '2019-01-04', 'journal_id': bank_journal.id}),
                (0, 0, {'payment_ref': 'line_5', 'amount': 50.0, 'date': '2019-01-05', 'journal_id': bank_journal.id}),
                (0, 0, {'payment_ref': 'line_6', 'amount': 60.0, 'date': '2019-01-06', 'journal_id': bank_journal.id}),
            ],
        })

        report = self.env.ref('account_reports.bank_reconciliation_report').with_context(
            active_id=bank_journal.id,
            active_model='account.journal'
        )

        options = self._generate_options(report, fields.Date.from_string('2019-01-01'), fields.Date.from_string('2019-01-12'))
        options['all_entries'] = True
        options['unfold_all'] = True

        lines = report._get_lines(options)
        self.assertLinesValues(
            lines,
            #   Name                                                             Date            Amount
            [0,                                                                     1,              3],
            [
                ('Balance of \'101401 Bank\'',                                     '',          130.0),
                ('Last statement balance',                                         '',          130.0),
                ('Including Unreconciled Receipts',                                '',          170.0),
                ('BNK1/2019/00006',                                      '01/06/2019',           60.0),
                ('BNK1/2019/00005',                                      '01/05/2019',           50.0),
                ('BNK1/2019/00003',                                      '01/03/2019',           30.0),
                ('BNK1/2019/00002',                                      '01/02/2019',           20.0),
                ('BNK1/2019/00001',                                      '01/01/2019',           10.0),
                ('Including Unreconciled Payments',                                '',          -40.0),
                ('BNK1/2019/00004',                                      '01/04/2019',          -40.0),
                ('Transactions without statement',                                 '',            0.0),
                ('Including Unreconciled Receipts',                                '',            0.0),
                ('Including Unreconciled Payments',                                '',            0.0),
                ('Misc. operations',                                               '',            0.0),
                ('Outstanding Receipts/Payments',                                  '',            0.0),
                ('(+) Outstanding Receipts',                                       '',            0.0),
                ('(-) Outstanding Payments',                                       '',            0.0),
            ],
            options,
            currency_map={3: {'currency': bank_journal.currency_id}},
            ignore_folded=False,
        )

        statement.unlink()

        options = self._generate_options(report, fields.Date.from_string('2019-01-01'), fields.Date.from_string('2019-01-12'))
        options['all_entries'] = True
        options['unfold_all'] = True

        lines = report._get_lines(options)
        self.assertLinesValues(
            lines,
            #   Name                                                             Date            Amount
            [0,                                                                    1,                3],
            [
                ('Balance of \'101401 Bank\'',                                    '',            130.0),
                ('Last statement balance',                                        '',              0.0),
                ('Including Unreconciled Receipts',                               '',              0.0),
                ('Including Unreconciled Payments',                               '',              0.0),
                ('Transactions without statement',                                '',            130.0),
                ('Including Unreconciled Receipts',                               '',            170.0),
                ('BNK1/2019/00006',                                     '01/06/2019',             60.0),
                ('BNK1/2019/00005',                                     '01/05/2019',             50.0),
                ('BNK1/2019/00003',                                     '01/03/2019',             30.0),
                ('BNK1/2019/00002',                                     '01/02/2019',             20.0),
                ('BNK1/2019/00001',                                     '01/01/2019',             10.0),
                ('Including Unreconciled Payments',                               '',            -40.0),
                ('BNK1/2019/00004',                                     '01/04/2019',            -40.0),
                ('Misc. operations',                                              '',              0.0),
                ('Outstanding Receipts/Payments',                                 '',              0.0),
                ('(+) Outstanding Receipts',                                      '',              0.0),
                ('(-) Outstanding Payments',                                      '',              0.0),
            ],
            options,
            currency_map={3: {'currency': bank_journal.currency_id}},
            ignore_folded=False,
        )

    def test_reconciliation_report_transaction_without_statement(self):
        """
            This test will ensure that the section transaction without statement section contains the reconcile entries.
            So the section should not always be the sum of his children.
        """
        bank_journal = self.company_data['default_journal_bank']

        bank_statement_lines = self.env['account.bank.statement.line'].create([
            {
                'payment_ref': 'Initial balance',
                'journal_id': bank_journal.id,
                'partner_id': self.partner_a.id,
                'amount': 1000.0,
                'date': '2019-01-01',
            },
            {
                'payment_ref': 'To be reconciled',
                'journal_id': bank_journal.id,
                'partner_id': self.partner_a.id,
                'amount': 100.0,
                'date': '2019-01-01',
            }
        ])

        report = self.env.ref('account_reports.bank_reconciliation_report').with_context(
            active_id=bank_journal.id,
            active_model='account.journal'
        )
        options = self._generate_options(report, '2019-01-01', '2019-01-12')
        options['all_entries'] = True
        options['unfold_all'] = True

        lines = report._get_lines(options)
        self.assertLinesValues(
            lines,
            #   Name                                                             Date            Amount
            [0, 1, 3],
            [
                ('Balance of \'101401 Bank\'',                                      '',         1100.0),
                ('Last statement balance',                                          '',            0.0),
                ('Including Unreconciled Receipts',                                 '',            0.0),
                ('Including Unreconciled Payments',                                 '',            0.0),
                ('Transactions without statement',                                  '',         1100.0),
                ('Including Unreconciled Receipts',                                 '',         1100.0),
                ('BNK1/2019/00002',                                       '01/01/2019',          100.0),
                ('BNK1/2019/00001',                                       '01/01/2019',         1000.0),
                ('Including Unreconciled Payments',                                 '',            0.0),
                ('Misc. operations',                                                '',            0.0),
                ('Outstanding Receipts/Payments',                                   '',            0.0),
                ('(+) Outstanding Receipts',                                        '',            0.0),
                ('(-) Outstanding Payments',                                        '',            0.0),
            ],
            options,
            currency_map={3: {'currency': bank_journal.currency_id}},
            ignore_folded=False,
        )

        payment = self.env['account.payment'].create({
            'amount': 100.0,
            'payment_type': 'inbound',
            'date': '2019-01-01',
            'journal_id': bank_journal.id,
            'partner_id': self.partner_a.id,
        })
        payment.action_post()

        payment_line = payment.move_id.line_ids.filtered(lambda line: line.account_id == payment.payment_method_line_id.payment_account_id)
        wizard = self.env['bank.rec.widget'].with_context(default_st_line_id=bank_statement_lines[1].id).new({})
        wizard._action_add_new_amls(payment_line, allow_partial=False)
        wizard._action_validate()

        options = self._generate_options(report, '2019-01-01', '2019-01-12')
        options['all_entries'] = True
        options['unfold_all'] = True

        lines = report._get_lines(options)
        self.assertLinesValues(
            lines,
            #   Name                                                             Date            Amount
            [0,                                                                    1,               3],
            [
                ('Balance of \'101401 Bank\'',                                    '',          1100.0),
                ('Last statement balance',                                        '',             0.0),
                ('Including Unreconciled Receipts',                               '',             0.0),
                ('Including Unreconciled Payments',                               '',             0.0),
                ('Transactions without statement',                                '',          1100.0),
                ('Including Unreconciled Receipts',                               '',          1000.0),
                ('BNK1/2019/00001',                                     '01/01/2019',          1000.0),
                ('Including Unreconciled Payments',                               '',             0.0),
                ('Misc. operations',                                              '',             0.0),
                ('Outstanding Receipts/Payments',                                 '',             0.0),
                ('(+) Outstanding Receipts',                                      '',             0.0),
                ('(-) Outstanding Payments',                                      '',             0.0),
            ],
            options,
            currency_map={3: {'currency': bank_journal.currency_id}},
            ignore_folded=False,
        )

    def test_reconciliation_report_exchange_entry(self):
        """ This test will check that misc entries reported in the exchange journal
            do not figure in the report
        """

        bank_journal = self.company_data['default_journal_bank']
        exchange_journal = self.env.company.currency_exchange_journal_id

        move_a = self.env['account.move'].create({
                'journal_id': exchange_journal.id,
                'move_type': 'entry',
                'date': '2019-01-01',
                'line_ids': [
                    Command.create({
                        'name': 'line_a_1',
                        'account_id': bank_journal.default_account_id.id,
                        'debit': 1000.0,
                        'credit': 0.0,
                    }),
                    Command.create({
                        'name': 'line_a_2',
                        'account_id': self.company_data['default_account_expense'].id,
                        'debit': 0.0,
                        'credit': 1000.0,
                    }),
                ]
        })
        move_a.action_post()
        report = self.env.ref('account_reports.bank_reconciliation_report').with_context(
            active_id=bank_journal.id,
            active_model='account.journal'
        )

        options = self._generate_options(report, fields.Date.from_string('2019-01-01'), fields.Date.from_string('2019-01-12'))

        lines = report._get_lines(options)
        self.assertLinesValues(
            lines,
            #   Name                                                             Date            Amount
            [0,                                                                     1,              3],
            [
                ('Balance of \'101401 Bank\'',                                     '',            0.0),
                ('Last statement balance',                                         '',            0.0),
                ('Including Unreconciled Receipts',                                '',            0.0),
                ('Including Unreconciled Payments',                                '',            0.0),
                ('Transactions without statement',                                 '',            0.0),
                ('Including Unreconciled Receipts',                                '',            0.0),
                ('Including Unreconciled Payments',                                '',            0.0),
                ('Misc. operations',                                               '',            0.0),
                ('Outstanding Receipts/Payments',                                  '',            0.0),
                ('(+) Outstanding Receipts',                                       '',            0.0),
                ('(-) Outstanding Payments',                                       '',            0.0),
            ],
            options,
            currency_map={3: {'currency': bank_journal.currency_id}},
            ignore_folded=False,
        )
