# pylint: disable=C0326
from .common import TestAccountReportsCommon

from odoo import Command, fields
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestJournalReport(TestAccountReportsCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.report = cls.env.ref('account_reports.journal_report')

        ##############
        # Bank entries
        ##############

        cls.default_bank_journal = cls.company_data['default_journal_bank']
        cls.default_sale_journal = cls.company_data['default_journal_sale']

        # Entries in 2016 for company_1 to test the starting balance of bank journals.
        cls.liquidity_account = cls.default_bank_journal.default_account_id
        cls.move_bank_0 = cls.env['account.move'].create({
            'move_type': 'entry',
            'date': '2016-01-01',
            'journal_id': cls.company_data['default_journal_bank'].id,
            'line_ids': [
                Command.create({'debit': 100.0,     'credit': 0.0,      'name': '2016_1_1',     'account_id': cls.liquidity_account.id}),
                Command.create({'debit': 0.0,       'credit': 100.0,    'name': '2016_1_2',     'account_id': cls.company_data['default_account_revenue'].id}),
            ],
        })
        cls.move_bank_0.action_post()

        # Entries in 2017 for company_1 to test the bank journal at current date.
        cls.move_bank_1 = cls.env['account.move'].create({
            'move_type': 'entry',
            'date': '2017-01-01',
            'journal_id': cls.company_data['default_journal_bank'].id,
            'line_ids': [
                Command.create({'debit': 200.0,     'credit': 0.0,      'name': '2017_1_1',     'account_id': cls.liquidity_account.id}),
                Command.create({'debit': 0.0,       'credit': 200.0,    'name': '2017_1_2',     'account_id': cls.company_data['default_account_revenue'].id}),
            ],
        })
        cls.move_bank_1.action_post()

        ##############
        # Sales entries
        ##############

        # Invoice in 2017 for company_1 to test a sale journal at current date.
        cls.move_sales_0 = cls.env['account.move'].create({
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
        cls.move_sales_0.action_post()

        # Invoice in 2017 for company_1, with foreign currency to test a sale journal at current date.
        cls.other_currency = cls.setup_other_currency('EUR', rounding=0.001, rates=[('2016-01-01', 2.0), ('2017-01-01', 2.0)])

        cls.move_sales_1 = cls.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': cls.partner_a.id,
            'invoice_date': '2017-01-01',
            'journal_id': cls.company_data['default_journal_sale'].id,
            'currency_id': cls.other_currency.id,
            'payment_reference': 'ref234',
            'invoice_line_ids': [Command.create({
                'quantity': 1,
                'price_unit': 3000.0,
                'account_id': cls.company_data['default_account_revenue'].id,
                'tax_ids': [],
            })],
        })
        cls.move_sales_1.action_post()

        # Invoice in 2017 for company_1, with foreign currency but no ref.
        cls.move_sales_2 = cls.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': cls.partner_a.id,
            'invoice_date': '2017-01-01',
            'journal_id': cls.company_data['default_journal_sale'].id,
            'currency_id': cls.other_currency.id,
            'invoice_line_ids': [Command.create({
                'quantity': 1,
                'price_unit': 2000.0,
                'account_id': cls.company_data['default_account_revenue'].id,
                'tax_ids': [],
            })],
        })
        cls.move_sales_2.action_post()
        cls.move_sales_2.payment_reference = ''

        # Set up a tax report, tax report line, and all needed to get a tax with a grid.
        cls.company_data['company'].country_id = cls.env.ref('base.us')
        cls.tax_report = cls.env['account.report'].create({
            'name': 'Tax report',
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
        cls.move_sales_3 = cls.env['account.move'].create({
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
        cls.move_sales_3.action_post()

        cls.move_payment_0 = cls.env['account.payment'].create({
            'amount': 370,
            'partner_id': cls.partner_a.id,
            'payment_reference': 'PBNK1/2017/00000001',
            'payment_type': 'inbound',
            'destination_account_id': cls.company_data['default_account_revenue'].id,
            'date': '2017-01-01'
        })
        cls.move_payment_0.action_post()

    def _filter_tax_section_lines(self, lines, exclude):
        def filter_condition(line):
            markup = self.report._get_markup(line['id'])
            return exclude ^ (isinstance(markup, str) and markup.startswith('tax_report_section'))

        return list(filter(filter_condition, lines))

    def assert_journal_vals_for_export(self, report, options, actual_journal_vals, expected_journals_data):
        self.assertEqual(len(actual_journal_vals), len(expected_journals_data))
        for actual_item, expected_item in zip(actual_journal_vals, expected_journals_data):
            # Check the columns
            if 'columns' in expected_item:
                self.assertEqual(expected_item['columns'], [col['label'] for col in actual_item['columns']])

            # Check the lines
            if 'lines' in expected_item:
                self.assertEqual(len(expected_item['lines']), len(actual_item['lines']))
                for expected_line, actual_line in zip(expected_item['lines'], actual_item['lines']):
                    self.assertDictEqual(expected_line, {expected_key: actual_line.get(expected_key, {}).get('data') for expected_key in expected_line})

    def test_journal_lines(self):
        """
        Check the journal report lines for the journal of type sale within the first month of 2017
        """
        options_2016 = self._generate_options(self.report, '2016-01-01', '2016-01-31', default_options={'unfold_all': True, 'show_payment_lines': False})
        lines_2016 = self.report._get_lines(options_2016)
        self.assertLinesValues(
            self._filter_tax_section_lines(lines_2016, True),
            [   1,                 2,          3,          4],
            [
                ('',              '',         '',         ''),
                ('BNK1',         100,        100,         ''),
                ('101401',       100,          0,        100),
                ('400000',         0,        100,       -100),
            ],
            options_2016,
        )
        tax_summary_lines_2016 = self._filter_tax_section_lines(lines_2016, False)
        self.assertFalse(tax_summary_lines_2016)

        options_2017 = self._generate_options(self.report, '2017-01-01', '2017-01-31', default_options={'unfold_all': True, 'show_payment_lines': False})
        lines_2017 = self.report._get_lines(options_2017)
        self.assertLinesValues(
            self._filter_tax_section_lines(lines_2017, True),
            [   1,                 2,          3,          4],
            [
                ('',              '',         '',         ''),
                ('INV',         7150,       7150,         ''),
                ('121000',      7150,          0,       7150),
                ('400000',         0,       7150,      -7150),
                ('BNK1',         200,        200,         ''),
                ('101401',       200,          0,        200),
                ('400000',         0,        200,       -200),
            ],
            options_2017,
        )
        tax_summary_lines_2017 = self._filter_tax_section_lines(lines_2017, False)
        tax_tag = self.tax_report.line_ids.expression_ids._get_matching_tags("+")
        self.assertDictEqual(
            tax_summary_lines_2017[0]['tax_grid_summary_lines'],
            {'United States': {'c10': {'tag_ids': tax_tag.ids, '+': '$\xa0150.00', '-': '$\xa00.00', '+_no_format': 150.0, 'impact': '$\xa0150.00'}}}
        )
        self.assertEqual(tax_summary_lines_2017[1]['name'], "Global Tax Summary")
        self.assertDictEqual(
            tax_summary_lines_2017[2]['tax_grid_summary_lines'],
            {'United States': {'c10': {'tag_ids': tax_tag.ids, '+': '$\xa0150.00', '-': '$\xa00.00', '+_no_format': 150.0, 'impact': '$\xa0150.00'}}}
        )

        options_global = self._generate_options(self.report, '2016-01-01', '2017-01-31', default_options={'unfold_all': True, 'show_payment_lines': False})
        lines_global = self.report._get_lines(options_global)
        self.assertLinesValues(
            self._filter_tax_section_lines(lines_global, True),
            [   1,                 2,          3,          4],
            [
                ('',              '',         '',         ''),
                ('INV',         7150,       7150,         ''),
                ('121000',      7150,          0,       7150),
                ('400000',         0,       7150,      -7150),
                ('BNK1',         300,        300,         ''),
                ('101401',       300,          0,        300),
                ('400000',         0,        300,       -300),
            ],
            options_global,
        )
        tax_summary_lines_global = self._filter_tax_section_lines(lines_global, False)
        self.assertDictEqual(
            tax_summary_lines_global[0]['tax_grid_summary_lines'],
            {'United States': {'c10': {'tag_ids': tax_tag.ids, '+': '$\xa0150.00', '-': '$\xa00.00', '+_no_format': 150.0, 'impact': '$\xa0150.00'}}}
        )
        self.assertEqual(tax_summary_lines_global[1]['name'], "Global Tax Summary")
        self.assertDictEqual(
            tax_summary_lines_global[2]['tax_grid_summary_lines'],
            {'United States': {'c10': {'tag_ids': tax_tag.ids, '+': '$\xa0150.00', '-': '$\xa00.00', '+_no_format': 150.0, 'impact': '$\xa0150.00'}}}
        )

    def test_show_payment_lines_option(self):
        """
        Check the journal report lines of the default bank journal with payments included
        """
        options_no_payment = self._generate_options(self.report, '2017-01-01', '2017-01-31', default_options={'unfold_all': True, 'show_payment_lines': False})

        self.assertLinesValues(
            self._filter_tax_section_lines(self.report._get_lines(options_no_payment), True),
            [   1,                 2,          3,          4],
            [
                ('',              '',         '',         ''),
                ('INV',         7150,       7150,         ''),
                ('121000',      7150,          0,       7150),
                ('400000',         0,       7150,      -7150),
                ('BNK1',         200,        200,         ''),
                ('101401',       200,          0,        200),
                ('400000',         0,        200,       -200),
            ],
            options_no_payment,
        )

        options_show_payment = self._generate_options(self.report, '2017-01-01', '2017-01-31', default_options={'unfold_all': True, 'show_payment_lines': True})
        self.assertLinesValues(
            self._filter_tax_section_lines(self.report._get_lines(options_show_payment), True),
            [   1,                 2,          3,          4],
            [
                ('',              '',         '',         ''),
                ('INV',         7150,       7150,         ''),
                ('121000',      7150,          0,       7150),
                ('400000',         0,       7150,      -7150),
                ('BNK1',         570,        570,         ''),
                ('101401',       200,          0,        200),
                ('101403',       370,          0,        370),
                ('400000',         0,        570,       -570),
            ],
            options_show_payment,
        )

    def test_document_data_basic(self):
        """
        Check that the data generated by the document data generator is valid
        """
        options = self._generate_options(self.report, '2017-01-01', '2017-01-31', default_options={'show_payment_lines': False})

        journal_report_handler = self.env[self.report.custom_handler_model_name]
        move_2_pref = self.move_sales_2.payment_reference
        self.assert_journal_vals_for_export(
            self.report,
            options,
            journal_report_handler._generate_document_data_for_export(self.report, options, 'pdf')['journals_vals'],
            [
                {
                    'id': self.default_sale_journal.id,
                    'columns': ['document', 'account_label', 'name', 'debit', 'credit', 'taxes', 'tax_grids'],
                    'lines': [
                        {'name': 'partner_a ref123',          'debit': '$\xa03,000.00',             'credit': '$\xa00.00'},
                        {'name': 'ref123',          'debit': '$\xa00.00',                 'credit': '$\xa03,000.00'},

                        {'name': 'partner_a ref234',          'debit': '$\xa01,500.00',             'credit': '$\xa00.00'},
                        {'name': 'ref234',          'debit': '$\xa00.00',                 'credit': '$\xa01,500.00'},

                        {'currency_id': self.other_currency.id, 'amount': 3000},  # Special line for multicurrency

                        {'name': f'partner_a {move_2_pref}',  'debit': '$\xa01,000.00',             'credit': '$\xa00.00'},
                        {'name': move_2_pref,       'debit': '$\xa00.00',                 'credit': '$\xa01,000.00'},

                        {'currency_id': self.other_currency.id, 'amount': 2000},  # Special line for multicurrency

                        {'name': 'partner_a ref345',          'debit': '$\xa01,650.00',             'credit': '$\xa00.00'},
                        {'name': 'ref345',          'debit': '$\xa00.00',                 'credit': '$\xa01,500.00',    'taxes': 'T: Tax 10%'},
                        {'name': 'Tax 10%',         'debit': '$\xa00.00',                 'credit': '$\xa0150.00',      'taxes': 'B: $\xa01,500.00'},

                        {},  # Empty line

                        {'name': 'Total',           'debit': '$\xa07,150.00',             'credit': '$\xa07,150.00'},
                    ],
                },
                {
                    'id': self.default_bank_journal.id,
                    'columns': ['document', 'account_label', 'name', 'debit', 'credit', 'balance'],
                    'lines': [
                        {'name': 'Starting Balance',    'balance': '$\xa0100.00'},
                        {'name': '2017_1_2',            'debit': '$\xa00.00',    'credit': '$\xa0200.00',      'balance': '$\xa0300.00'},

                        {},  # Empty line

                        {'name': 'Total',               'debit': None,           'credit': None,               'balance': '$\xa0300.00'},
                    ],
                },
            ],
        )

    def test_document_data_for_bank_journal_with_show_payment_option(self):
        """
        Check that show payment affect the result of the bank journal data when this filter is changed
        """
        options = self._generate_options(self.report, '2017-01-01', '2017-01-31', default_options={'show_payment_lines': True})
        journal_report_handler = self.env[self.report.custom_handler_model_name]
        move_2_pref = self.move_sales_2.payment_reference
        self.assert_journal_vals_for_export(
            self.report,
            options,
            journal_report_handler._generate_document_data_for_export(self.report, options, 'pdf')['journals_vals'],
            [
                {
                    'id': self.default_sale_journal.id,
                    'columns': ['document', 'account_label', 'name', 'debit', 'credit', 'taxes', 'tax_grids'],
                    'lines': [
                        {'name': 'partner_a ref123',          'debit': '$\xa03,000.00',             'credit': '$\xa00.00'},
                        {'name': 'ref123',          'debit': '$\xa00.00',                 'credit': '$\xa03,000.00'},

                        {'name': 'partner_a ref234',          'debit': '$\xa01,500.00',             'credit': '$\xa00.00'},
                        {'name': 'ref234',          'debit': '$\xa00.00',                 'credit': '$\xa01,500.00'},

                        {'currency_id': self.other_currency.id, 'amount': 3000},  # Special line for multicurrency

                        {'name': f'partner_a {move_2_pref}',  'debit': '$\xa01,000.00',             'credit': '$\xa00.00'},
                        {'name': move_2_pref,       'debit': '$\xa00.00',                 'credit': '$\xa01,000.00'},

                        {'currency_id': self.other_currency.id, 'amount': 2000},  # Special line for multicurrency

                        {'name': 'partner_a ref345',          'debit': '$\xa01,650.00',             'credit': '$\xa00.00'},
                        {'name': 'ref345',          'debit': '$\xa00.00',                 'credit': '$\xa01,500.00',    'taxes': 'T: Tax 10%'},
                        {'name': 'Tax 10%',         'debit': '$\xa00.00',                 'credit': '$\xa0150.00',      'taxes': 'B: $\xa01,500.00'},

                        {},  # Empty line

                        {'name': 'Total',           'debit': '$\xa07,150.00',             'credit': '$\xa07,150.00'},
                    ],
                },
                {
                    'id': self.default_bank_journal.id,
                    'columns': ['document', 'account_label', 'name', 'debit', 'credit', 'balance'],
                    'lines': [
                        {'name': 'Starting Balance', 'balance': '$\xa0100.00'},

                        {'name': '2017_1_2',            'debit': '$\xa00.00',     'credit': '$\xa0200.00',  'balance': '$\xa0300.00'},

                        # Payment
                        {'name': 'Manual Payment',      'debit': '$\xa0370.00',   'credit': '$\xa00.00',    'balance': None},
                        {'name': 'Manual Payment',      'debit': '$\xa00.00',     'credit': '$\xa0370.00',  'balance': None},

                        {},  # Empty line

                        {'name': 'Total',               'debit': None,            'credit': None,           'balance': '$\xa0300.00'},
                    ],
                },
            ],
        )

    def test_document_data_for_bank_multicurrency(self):
        """
        Test that data from bank journal can support multi currency bank moves
        """
        options = self._generate_options(self.report, '2017-01-01', '2017-01-31', default_options={'show_payment_lines': True})
        journal_report_handler = self.env[self.report.custom_handler_model_name]
        self.assert_journal_vals_for_export(
            self.report,
            options,
            list(filter(lambda x: x['id'] == self.default_bank_journal.id, journal_report_handler._generate_document_data_for_export(self.report, options, 'pdf')['journals_vals'])),
            [
                {
                    'id': self.default_bank_journal.id,
                    'columns': ['document', 'account_label', 'name', 'debit', 'credit', 'balance'],
                    'lines': [
                        {'name': 'Starting Balance', 'balance': '$\xa0100.00'},

                        {'name': '2017_1_2',            'debit': '$\xa00.00',    'credit': '$\xa0200.00',  'balance': '$\xa0300.00'},

                        # Payment
                        {'name': 'Manual Payment',      'debit': '$\xa0370.00',  'credit': '$\xa00.00',    'balance': None},
                        {'name': 'Manual Payment',      'debit': '$\xa00.00',    'credit': '$\xa0370.00',  'balance': None},

                        {},  # Empty line

                        {'name': 'Total',               'debit': None,           'credit': None,           'balance': '$\xa0300.00'},
                    ]
                }
            ]
        )

        new_bank_move = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2017-01-01',
            'journal_id': self.company_data['default_journal_bank'].id,
            'currency_id': self.other_currency.id,
            'line_ids': [
                Command.create({
                    'debit': 100.0,
                    'credit': 0.0,
                    'name': '2017_1_3',
                    'account_id': self.liquidity_account.id,
                    'currency_id': self.other_currency.id,
                    'amount_currency': 200
                }),
                Command.create({
                    'debit': 0.0,
                    'credit': 100.0,
                    'name': '2017_1_4',
                    'account_id': self.company_data['default_account_revenue'].id,
                    'currency_id': self.other_currency.id,
                    'amount_currency': -200
                }),
            ],
        })
        new_bank_move.action_post()

        self.assert_journal_vals_for_export(
            self.report,
            options,
            list(filter(lambda x: x['id'] == self.default_bank_journal.id, journal_report_handler._generate_document_data_for_export(self.report, options, 'pdf')['journals_vals'])),
            [
                {
                    'id': self.default_bank_journal.id,
                    'columns': ['document', 'account_label', 'name', 'debit', 'credit', 'balance', 'amount_currency'],
                    'lines': [
                        {'name': 'Starting Balance', 'balance': '$\xa0100.00'},

                        {'name': '2017_1_2',            'debit': '$\xa00.00',   'credit': '$\xa0200.00',   'balance': '$\xa0300.00'},
                        {'name': '2017_1_4',            'debit': '$\xa00.00',   'credit': '$\xa0100.00',   'balance': '$\xa0400.00', 'amount_currency': '200.000\xa0€'},

                        # Payment --
                        {'name': 'Manual Payment',      'debit': '$\xa0370.00',  'credit': '$\xa00.00',    'balance': None},
                        {'name': 'Manual Payment',      'debit': '$\xa00.00',    'credit': '$\xa0370.00',  'balance': None},

                        {},  # Empty line

                        {'name': 'Total',               'debit': None,           'credit': None,           'balance': '$\xa0400.00'}
                    ],
                },
            ],
        )

    def test_global_tax_summary_rounding_unit(self):
        """ Test that Global Tax Summary applies rounding filter correctly. """
        report = self.env.ref('account_reports.journal_report')
        options = self._generate_options(report, '2017-01-01', '2017-01-31')
        options['unfold_all'] = True

        # Get tax summary lines with default formatting
        lines = report._get_lines(options)
        tax_lines = list(filter(lambda line: line.get('is_tax_section_line'), lines))

        default_balance = tax_lines[0]['tax_grid_summary_lines']['United States']['c10']['+']
        self.assertEqual(default_balance, '$\xa0150.00')  # Default: $150.00

        # Test with thousands rounding unit, call via dispatch_report_action like the frontend does
        options['rounding_unit'] = 'thousands'
        report.dispatch_report_action(options, 'format_column_values_from_client', lines)

        thousands_balance = tax_lines[0]['tax_grid_summary_lines']['United States']['c10']['+']
        self.assertEqual(thousands_balance, '$\xa00')  # Thousands: $0 (150/1000 = 0.15 rounded to 0)
