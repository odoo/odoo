# -*- coding: utf-8 -*-
# pylint: disable=C0326
from .common import TestAccountReportsCommon

from odoo import Command, fields
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestJournalAuditReport(TestAccountReportsCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        ##############
        # Bank entries
        ##############

        # Entries in 2016 for company_1 to test the starting balance of bank journals.
        cls.liquidity_account = cls.company_data['default_journal_bank'].default_account_id
        cls.move_2016_1 = cls.env['account.move'].create({
            'move_type': 'entry',
            'date': '2016-01-01',
            'journal_id': cls.company_data['default_journal_bank'].id,
            'line_ids': [
                Command.create({'debit': 100.0,     'credit': 0.0,      'name': '2016_1_1',     'account_id': cls.liquidity_account.id}),
                Command.create({'debit': 0.0,       'credit': 100.0,    'name': '2016_1_2',     'account_id': cls.company_data['default_account_revenue'].id}),
            ],
        })
        cls.move_2016_1.action_post()

        # Entries in 2017 for company_1 to test the bank journal at current date.
        cls.move_2017_1 = cls.env['account.move'].create({
            'move_type': 'entry',
            'date': '2017-01-01',
            'journal_id': cls.company_data['default_journal_bank'].id,
            'line_ids': [
                Command.create({'debit': 200.0,     'credit': 0.0,      'name': '2017_1_1',     'account_id': cls.liquidity_account.id}),
                Command.create({'debit': 0.0,       'credit': 200.0,    'name': '2017_1_2',     'account_id': cls.company_data['default_account_revenue'].id}),
            ],
        })
        cls.move_2017_1.action_post()

        ##############
        # Sales entries
        ##############

        # Invoice in 2017 for company_1 to test a sale journal at current date.
        cls.move_2017_2 = cls.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': cls.partner_a.id,
            'invoice_date': '2017-01-01',
            'journal_id': cls.company_data['default_journal_sale'].id,
            'payment_reference': 'ref123',
            'invoice_line_ids': [Command.create({
                'quantity': 1,
                'price_unit': 3000.0,
                'account_id': cls.company_data['default_account_revenue'].id,
                'tax_ids': [],
            })],
        })
        cls.move_2017_2.action_post()

        # Invoice in 2017 for company_1, with foreign currency to test a sale journal at current date.
        cls.currency_data = cls.setup_multi_currency_data({
            'name': 'Dark Chocolate Coin',
            'symbol': '🍫',
            'currency_unit_label': 'Dark Choco',
            'currency_subunit_label': 'Dark Cacao Powder',
        }, rate2016=2.0, rate2017=2.0)
        cls.move_2017_3 = cls.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': cls.partner_a.id,
            'invoice_date': '2017-01-01',
            'journal_id': cls.company_data['default_journal_sale'].id,
            'currency_id': cls.currency_data['currency'].id,
            'payment_reference': 'ref234',
            'invoice_line_ids': [Command.create({
                'quantity': 1,
                'price_unit': 3000.0,
                'account_id': cls.company_data['default_account_revenue'].id,
                'tax_ids': [],
            })],
        })
        cls.move_2017_3.action_post()

        # Invoice in 2017 for company_1, with foreign currency but no ref.
        cls.move_2017_4 = cls.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': cls.partner_a.id,
            'invoice_date': '2017-01-01',
            'journal_id': cls.company_data['default_journal_sale'].id,
            'currency_id': cls.currency_data['currency'].id,
            'invoice_line_ids': [Command.create({
                'quantity': 1,
                'price_unit': 2000.0,
                'account_id': cls.company_data['default_account_revenue'].id,
                'tax_ids': [],
            })],
        })
        cls.move_2017_4.action_post()
        cls.move_2017_4.payment_reference = ''

        ####
        # Setup a tax report, tax report line, and all needed to get a tax with a grid.
        ####

        cls.company_data['company'].country_id = cls.env.ref('base.us')
        cls.tax_report = cls.env['account.report'].create({
            'name': "Tax report",
            'root_report_id': cls.env.ref('account.generic_tax_report').id,
            'country_id': cls.company_data['company'].country_id.id,
            'filter_fiscal_position': True,
            'availability_condition': 'country',
            'column_ids': [Command.create({
                'name': 'Balance',
                'expression_label': 'balance',
                'sequence': 1,
            })],
            'line_ids': [Command.create({
                'name': '10%',
                'code': 'c10',
                'sequence': 1,
                'expression_ids': [Command.create({
                    'label': 'balance',
                    'engine': 'tax_tags',
                    'formula': 'c10',
                })]
            })]
        })
        cls.test_tax = cls.env['account.tax'].create({
            'name': 'Tax 10%',
            'amount': 10.0,
            'amount_type': 'percent',
            'type_tax_use': 'sale',
            'invoice_repartition_line_ids': [
                Command.create({'repartition_type': 'base'}),
                Command.create({
                    'repartition_type': 'tax',
                    'tag_ids': [Command.link(cls.tax_report.line_ids.expression_ids._get_matching_tags("+").id)],
                })]
        })
        # Invoice in 2017 for company_1, with taxes
        cls.move_2017_5 = cls.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': cls.partner_a.id,
            'invoice_date': '2017-01-01',
            'payment_reference': 'ref345',
            'journal_id': cls.company_data['default_journal_sale'].id,
            'invoice_line_ids': [Command.create({
                'quantity': 1,
                'price_unit': 1500.0,
                'account_id': cls.company_data['default_account_revenue'].id,
                'tax_ids': [cls.test_tax.id],
            })],
        })
        cls.move_2017_5.action_post()

    def test_report_journal_sale_journal(self):
        report = self.env.ref('account_reports.journal_report')
        options = self._generate_options(report, fields.Date.from_string('2017-01-01'), fields.Date.from_string('2017-01-31'))
        options['unfolded_lines'] = [report._get_generic_line_id('account.journal', self.company_data['default_journal_sale'].id)]

        self.assertLinesValues(
            report._get_lines(options),
            #   Name                                    Invoice Date              Account                   Debit           Credit                Taxes/Balance       Amount In Currency
            [   0,                                      1,                        2,                        4,              5,                    6,                  7],
            [
                ('Customer Invoices (INV)',                                                                                                                             ),
                ('Name',                                'Invoice Date',           'Account',                'Debit',        'Credit',             'Taxes',            'Tax Grids'),
                ('INV/2017/00001',                      '2017-01-01',             '121000 partner_a',       3000.0,         0.0,                  '',                 ''),
                ('ref123',                              '',                       '400000 Product Sales',   0.0,            3000.0,               '',                 ''),
                ('INV/2017/00002',                      '2017-01-01',             '121000 partner_a',       1500.0,         0.0,                  '',                 ''),
                ('ref234',                              '',                       '400000 Product Sales',   0.0,            1500.0,               '',                 ''),
                # Because there is a payment_reference, we need to add a line for the amount in currency
                ('Amount in currency: 3,000.000\xa0🍫', ''                                                                                                              ),
                ('INV/2017/00003',                      '2017-01-01',             '121000 partner_a',       1000.0,         0.0,                  '',                 ''),
                # No payment_reference, so the amount in currency is added in the name of the second line.
                ('Amount in currency: 2,000.000\xa0🍫', '',                       '400000 Product Sales',   0.0,            1000.0,               '',                 ''),
                # Invoice with taxes
                ('INV/2017/00004',                      '2017-01-01',             '121000 partner_a',       1650.0,         0.0,                  '',                 ''),
                ('ref345',                              '',                       '400000 Product Sales',   0.0,            1500.0,               'T: Tax 10%',       ''),
                ('',                                    '',                       '400000 Product Sales',   0.0,            150.0,                'B: $\xa01,500.00', '+c10'),
                # This is the tax summary line, it's rendered in a custom way and don't have values in the name/columns
                ('',                                                                                                                                                    ),
                ('Bank (BNK1)',                                                                                                                                         ),
                ('Global Tax Summary',                                                                                                                                  ),
                ('',                                                                                                                                                    ),
            ],
            options,
        )

    def test_report_journal_sale_journal_multicurrency_disabled(self):
        # Repeat the previous test, but without multicurrency support. Ensure that we do not display the multicurrency lines.
        self.env['res.currency'].search([('id', '!=', self.company_data['currency'].id)]).with_context(force_deactivate=True).active = False
        report = self.env.ref('account_reports.journal_report')
        options = self._generate_options(report, fields.Date.from_string('2017-01-01'), fields.Date.from_string('2017-01-31'))
        options['unfolded_lines'] = [report._get_generic_line_id('account.journal', self.company_data['default_journal_sale'].id)]

        self.assertLinesValues(
            report._get_lines(options),
            #   Name                                    Invoice Date              Account                   Debit           Credit                Taxes/Balance       Amount In Currency
            [   0,                                      1,                        2,                        4,              5,                    6,                  7],
            [
                ('Customer Invoices (INV)',                                                                                                                             ),
                ('Name',                                'Invoice Date',           'Account',                'Debit',        'Credit',      'Taxes',                   'Tax Grids'),
                ('INV/2017/00001',                      '2017-01-01',             '121000 partner_a',       3000.0,         0.0,           '',                        ''),
                ('ref123',                              '',                       '400000 Product Sales',   0.0,            3000.0,        '',                        ''),
                ('INV/2017/00002',                      '2017-01-01',             '121000 partner_a',       1500.0,         0.0,           '',                        ''),
                ('ref234',                              '',                       '400000 Product Sales',   0.0,            1500.0,        '',                        ''),
                ('INV/2017/00003',                      '2017-01-01',             '121000 partner_a',       1000.0,         0.0,           '',                        ''),
                ('',                                    '',                       '400000 Product Sales',   0.0,            1000.0,        '',                        ''),
                # Invoice with taxes
                ('INV/2017/00004',                      '2017-01-01',             '121000 partner_a',       1650.0,         0.0,           '',                        ''),
                ('ref345',                              '',                       '400000 Product Sales',   0.0,            1500.0,        'T: Tax 10%',              ''),
                ('',                                    '',                       '400000 Product Sales',   0.0,            150.0,         'B: $\xa01,500.00',        '+c10'),
                # This is the tax summary line, it's rendered in a custom way and don't have values in the name/columns
                ('',                                                                                                                                                    ),
                ('Bank (BNK1)',                                                                                                                                         ),
                ('Global Tax Summary',                                                                                                                                  ),
                ('',                                                                                                                                                    ),
            ],
            options,
        )

    def test_report_journal_bank_journal(self):
        report = self.env.ref('account_reports.journal_report')
        line_id = report._get_generic_line_id('account.journal', self.company_data['default_journal_bank'].id)
        options = self._generate_options(report, fields.Date.from_string('2017-01-01'), fields.Date.from_string('2017-01-31'))
        options['unfolded_lines'] = [line_id]

        self.assertLinesValues(
            report._get_lines(options),
            #   Name                                    Invoice Date              Account                   Debit           Credit                Taxes/Balance       Amount In Currency
            [   0,                                      1,                        2,                        4,              5,                    6,                  7],
            [
                ('Customer Invoices (INV)',                                                                                                                             ),
                ('Bank (BNK1)',                                                                                                                                         ),
                ('Name',                                '',                       'Account',                'Debit',        'Credit',             'Balance',          'Amount In Currency'),
                ('',                                    '',                       '',                       '',             'Starting Balance:',  '$\xa0100.00',      ''),
                ('BNK1/2017/00001',                     '',                       '400000 Product Sales',   0.0,            200.00,               '$\xa0300.00',      ''),
                ('',                                    '',                       '',                       '',             'Ending Balance:',    '$\xa0300.00',      ''),
                ('Global Tax Summary',                                                                                                                                  ),
                ('',                                                                                                                                                    ),
            ],
            options,
        )

    def test_report_journal_bank_journal_multicurrency(self):
        report = self.env.ref('account_reports.journal_report')
        line_id = report._get_generic_line_id('account.journal', self.company_data['default_journal_bank'].id)
        options = self._generate_options(report, fields.Date.from_string('2017-01-01'), fields.Date.from_string('2017-01-31'))
        options['unfolded_lines'] = [line_id]

        move_2017_6 = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2017-01-02',
            'journal_id': self.company_data['default_journal_bank'].id,
            'line_ids': [
                Command.create({
                    'debit': 175.0,
                    'credit': 0.0,
                    'name': '2017_6_1',
                    'account_id': self.liquidity_account.id
                }),
                Command.create({
                    'debit': 0.0,
                    'credit': 175.0,
                    'name': '2017_6_2',
                    'currency_id': self.currency_data['currency'].id,
                    'amount_currency': -150,
                    'account_id': self.company_data['default_account_revenue'].id
                }),
            ],
        })
        move_2017_6.action_post()

        self.assertLinesValues(
            report._get_lines(options),
            #   Name                                    Invoice Date              Account                   Debit           Credit                Taxes/Balance       Amount In Currency
            [   0,                                      1,                        2,                        4,              5,                    6,                  7],
            [
                ('Customer Invoices (INV)',                                                                                                                             ),
                ('Bank (BNK1)',                                                                                                                                         ),
                ('Name',                                '',                       'Account',                'Debit',        'Credit',             'Balance',          'Amount In Currency'),
                ('',                                    '',                       '',                       '',             'Starting Balance:',  '$\xa0100.00',      ''),
                ('BNK1/2017/00001',                     '',                       '400000 Product Sales',   0.0,            200.00,               '$\xa0300.00',      ''),
                ('BNK1/2017/00002',                     '',                       '400000 Product Sales',   0.0,            175.00,               '$\xa0475.00',      '150.000\xa0🍫'),
                ('',                                    '',                       '',                       '',             'Ending Balance:',    '$\xa0475.00',      ''),
                ('Global Tax Summary',                                                                                                                                  ),
                ('',                                                                                                                                                    ),
            ],
            options,
        )

    def test_report_journal_bank_journal_multicurrency_disabled(self):
        # Repeat the previous test, but without multicurrency support. Ensure that we do not display the multicurrency column.
        self.env['res.currency'].search([('id', '!=', self.company_data['currency'].id)]).with_context(force_deactivate=True).active = False
        report = self.env.ref('account_reports.journal_report')
        line_id = report._get_generic_line_id('account.journal', self.company_data['default_journal_bank'].id)
        options = self._generate_options(report, fields.Date.from_string('2017-01-01'), fields.Date.from_string('2017-01-31'))
        options['unfolded_lines'] = [line_id]

        move_2017_6 = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2017-01-02',
            'journal_id': self.company_data['default_journal_bank'].id,
            'line_ids': [
                Command.create(
                    {'debit': 175.0, 'credit': 0.0, 'name': '2017_6_1', 'account_id': self.liquidity_account.id}),
                Command.create({'debit': 0.0, 'credit': 175.0, 'name': '2017_6_2',
                                'currency_id': self.currency_data['currency'].id, 'amount_currency': -150,
                                'account_id': self.company_data['default_account_revenue'].id}),
            ],
        })
        move_2017_6.action_post()

        self.assertLinesValues(
            report._get_lines(options),
            #   Name                                    Invoice Date              Account                   Debit           Credit                Taxes/Balance       Amount In Currency
            [   0,                                      1,                        2,                        4,              5,                    6,                  7],
            [
                ('Customer Invoices (INV)',                                                                                                                             ),
                ('Bank (BNK1)',                                                                                                                                         ),
                ('Name',                                '',                       'Account',                'Debit',        'Credit',             'Balance',          ''),
                ('',                                    '',                       '',                       '',             'Starting Balance:',  '$\xa0100.00',      ''),
                ('BNK1/2017/00001',                     '',                       '400000 Product Sales',   0.0,            200.00,               '$\xa0300.00',      ''),
                ('BNK1/2017/00002',                     '',                       '400000 Product Sales',   0.0,            175.00,               '$\xa0475.00',      ''),
                ('',                                    '',                       '',                       '',             'Ending Balance:',    '$\xa0475.00',      ''),
                ('Global Tax Summary',                                                                                                                                  ),
                ('',                                                                                                                                                    ),
            ],
            options,
        )

    def test_report_journal_sale_journal_group_by_months(self):
        # Add a new move with another month
        move_2017_2 = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2017-02-02',
            'journal_id': self.company_data['default_journal_sale'].id,
            'payment_reference': 'ref123',
            'invoice_line_ids': [Command.create({
                'quantity': 1,
                'price_unit': 3000.0,
                'account_id': self.company_data['default_account_revenue'].id,
                'tax_ids': [],
            })],
        })
        move_2017_2.action_post()

        report = self.env.ref('account_reports.journal_report')
        options = self._generate_options(report, fields.Date.from_string('2017-01-01'), fields.Date.from_string('2017-03-31'))
        options['group_by_months'] = True
        journal_line_id = report._get_generic_line_id('account.journal', self.company_data['default_journal_sale'].id)
        options['unfolded_lines'] = [
            journal_line_id,
            report._get_generic_line_id(None, None, parent_line_id=journal_line_id, markup='month_line 2017 1'),
            report._get_generic_line_id(None, None, parent_line_id=journal_line_id, markup='month_line 2017 2'),
        ]

        self.assertLinesValues(
            report._get_lines(options),
            #   Name                                    Invoice Date              Account                   Debit           Credit                Taxes/Balance       Amount In Currency
            [   0,                                      1,                        2,                        4,              5,                    6,                  7],
            [
                ('Customer Invoices (INV)',                                                                                                                             ),
                ('Jan 2017',                                                                                                                                            ),
                ('Name',                                'Invoice Date',           'Account',                'Debit',        'Credit',      'Taxes',                   'Tax Grids'),
                ('INV/2017/00001',                      '2017-01-01',             '121000 partner_a',       3000.0,         0.0,           '',                        ''),
                ('ref123',                              '',                       '400000 Product Sales',   0.0,            3000.0,        '',                        ''),
                ('INV/2017/00002',                      '2017-01-01',             '121000 partner_a',       1500.0,         0.0,           '',                        ''),
                ('ref234',                              '',                       '400000 Product Sales',   0.0,            1500.0,        '',                        ''),
                # Because there is a payment_reference, we need to add a line for the amount in currency
                ('Amount in currency: 3,000.000\xa0🍫',                                                                                                                 ),
                ('INV/2017/00003',                      '2017-01-01',             '121000 partner_a',       1000.0,         0.0,           '',                        ''),
                # No payment_reference, so the amount in currency is added in the name of the second line.
                ('Amount in currency: 2,000.000\xa0🍫', '',                       '400000 Product Sales',   0.0,            1000.0,        '',                        ''),
                # Invoice with taxes
                ('INV/2017/00004',                      '2017-01-01',             '121000 partner_a',       1650.0,         0.0,           '',                        ''),
                ('ref345',                              '',                       '400000 Product Sales',   0.0,            1500.0,        'T: Tax 10%',              ''),
                ('',                                    '',                       '400000 Product Sales',   0.0,            150.0,         'B: $\xa01,500.00',        '+c10'),
                # This is the tax summary line, it's rendered in a custom way and don't have values in the name/columns
                ('',                                                                                                                                                    ),
                ('Feb 2017',                                                                                                                                            ),
                ('Name',                                'Invoice Date',           'Account',                'Debit',        'Credit',      'Taxes',                   'Tax Grids'),
                ('INV/2017/00005',                      '2017-02-02',             '121000 partner_a',       3000.0,         0.0,           '',                        ''),
                ('ref123',                              '',                       '400000 Product Sales',   0.0,            3000.0,        '',                        ''),
                ('Bank (BNK1)',                                                                                                                                         ),
                ('Global Tax Summary',                                                                                                                                  ),
                ('',                                                                                                                                                    ),
            ],
            options,
        )

    def test_report_journal_sale_journal_sort_by_date(self):
        # Add a new move with another month
        move_2017_2 = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2017-02-02',
            'journal_id': self.company_data['default_journal_sale'].id,
            'payment_reference': 'ref123',
            'invoice_line_ids': [Command.create({
                'quantity': 1,
                'price_unit': 3000.0,
                'account_id': self.company_data['default_account_revenue'].id,
                'tax_ids': [],
            })],
        })
        move_2017_2.action_post()
        move_2017_1 = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2017-01-15',
            'journal_id': self.company_data['default_journal_sale'].id,
            'payment_reference': 'ref987',
            'invoice_line_ids': [Command.create({
                'quantity': 1,
                'price_unit': 1234.0,
                'account_id': self.company_data['default_account_revenue'].id,
                'tax_ids': [],
            })],
        })
        move_2017_1.action_post()

        report = self.env.ref('account_reports.journal_report')
        options = self._generate_options(report, fields.Date.from_string('2017-01-01'), fields.Date.from_string('2017-03-31'))
        options['sort_by_date'] = True
        options['unfolded_lines'] = [report._get_generic_line_id('account.journal', self.company_data['default_journal_sale'].id)]

        # Inv 6 will be before Inv 5 because inv 5 is later in terms of date
        self.assertLinesValues(
            report._get_lines(options),
            #   Name                                    Invoice Date              Account                   Debit           Credit                Taxes/Balance       Amount In Currency
            [   0,                                      1,                        2,                        4,              5,                    6,                  7],
            [
                ('Customer Invoices (INV)',                                                                                                                             ),
                ('Name',                                'Invoice Date',           'Account',                'Debit',        'Credit',             'Taxes',            'Tax Grids'),
                ('INV/2017/00001',                      '2017-01-01',             '121000 partner_a',       3000.0,         0.0,                  '',                 ''),
                ('ref123',                              '',                       '400000 Product Sales',   0.0,            3000.0,               '',                 ''),
                ('INV/2017/00002',                      '2017-01-01',             '121000 partner_a',       1500.0,         0.0,                  '',                 ''),
                ('ref234',                              '',                       '400000 Product Sales',   0.0,            1500.0,               '',                 ''),
                # Because there is a payment_reference, we need to add a line for the amount in currency
                ('Amount in currency: 3,000.000\xa0🍫',                                                                                                                 ),
                ('INV/2017/00003',                      '2017-01-01',             '121000 partner_a',       1000.0,         0.0,                  '',                 ''),
                # No payment_reference, so the amount in currency is added in the name of the second line.
                ('Amount in currency: 2,000.000\xa0🍫', '',                       '400000 Product Sales',   0.0,            1000.0,               '',                 ''),
                # Invoice with taxes
                ('INV/2017/00004',                      '2017-01-01',             '121000 partner_a',       1650.0,         0.0,                  '',                 ''),
                ('ref345',                              '',                       '400000 Product Sales',   0.0,            1500.0,               'T: Tax 10%',       ''),
                ('',                                    '',                       '400000 Product Sales',   0.0,            150.0,                'B: $\xa01,500.00', '+c10'),
                ('INV/2017/00006',                      '2017-01-15',             '121000 partner_a',       1234.0,         0.0,                  '',                 ''),
                ('ref987',                              '',                       '400000 Product Sales',   0.0,            1234.0,               '',                 ''),
                ('INV/2017/00005',                      '2017-02-02',             '121000 partner_a',       3000.0,         0.0,                  '',                 ''),
                ('ref123',                              '',                       '400000 Product Sales',   0.0,            3000.0,               '',                 ''),
                # This is the tax summary line, it's rendered in a custom way and don't have values in the name/columns
                ('',                                                                                                                                                    ),
                ('Bank (BNK1)',                                                                                                                                         ),
                ('Global Tax Summary',                                                                                                                                  ),
                ('',                                                                                                                                                    ),
            ],
            options,
        )

    def test_journal_report_zero_percent_distribution_line(self):
        # Setup data for zero percent distribution line
        # Test zero factory percent on journal report
        tax = self.env['account.tax'].create({
            'name': 'none of nothing X',
            'amount': 21,
            'amount_type': 'percent',
            'type_tax_use': 'sale',
            'invoice_repartition_line_ids': [
                Command.create({'factor_percent': 100, 'repartition_type': 'base'}),
                Command.create({'factor_percent': 0, 'repartition_type': 'tax', 'account_id': self.company_data['default_account_receivable'].id}),
            ],
            'refund_repartition_line_ids': [
                Command.create({'factor_percent': 100, 'repartition_type': 'base'}),
                Command.create({'factor_percent': 0, 'repartition_type': 'tax', 'account_id': self.company_data['default_account_payable'].id}),
            ],
        })

        move = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2024-01-01',
            'journal_id': self.company_data['default_journal_sale'].id,
            'line_ids': [
                Command.create({
                    'debit': 1000.0,
                    'credit': 0.0,
                    'account_id': self.env.company.partner_id.property_account_receivable_id.id,
                    'tax_repartition_line_id': tax.invoice_repartition_line_ids.filtered(lambda x: x.repartition_type == 'tax').id,
                }),
                Command.create({
                    'debit': 0.0,
                    'credit': 1000.0,
                    'tax_repartition_line_id': tax.invoice_repartition_line_ids.filtered(lambda x: x.repartition_type == 'tax').id,
                    'tax_ids': [Command.set([tax.id])],
                    'account_id': self.env.company.partner_id.property_account_payable_id.id,
                }),
            ],
        })

        move.action_post()

        report = self.env.ref('account_reports.journal_report')
        options = self._generate_options(report, fields.Date.from_string('2024-01-01'), fields.Date.from_string('2024-01-31'))
        options['unfolded_lines'] = [report._get_generic_line_id('account.journal', self.company_data['default_journal_sale'].id)]

        self.assertTrue(report._get_lines(options))
