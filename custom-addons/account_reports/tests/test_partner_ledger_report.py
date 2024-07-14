# -*- coding: utf-8 -*-
# pylint: disable=C0326
from unittest.mock import patch

from .common import TestAccountReportsCommon

from odoo import fields
from odoo.tests import tagged

import json


@tagged('post_install', '-at_install')
class TestPartnerLedgerReport(TestAccountReportsCommon):
    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.partner_category_a = cls.env['res.partner.category'].create({'name': 'partner_categ_a'})
        cls.partner_category_b = cls.env['res.partner.category'].create({'name': 'partner_categ_b'})

        cls.partner_a = cls.env['res.partner'].create(
            {'name': 'partner_a', 'company_id': False, 'category_id': [(6, 0, [cls.partner_category_a.id, cls.partner_category_b.id])]})
        cls.partner_b = cls.env['res.partner'].create(
            {'name': 'partner_b', 'company_id': False, 'category_id': [(6, 0, [cls.partner_category_a.id])]})
        cls.partner_c = cls.env['res.partner'].create(
            {'name': 'partner_c', 'company_id': False, 'category_id': [(6, 0, [cls.partner_category_b.id])]})

        # Entries in 2016 for company_1 to test the initial balance.
        cls.move_2016_1 = cls.env['account.move'].create({
            'move_type': 'entry',
            'date': fields.Date.from_string('2016-01-01'),
            'journal_id': cls.company_data['default_journal_misc'].id,
            'line_ids': [
                (0, 0, {'debit': 100.0,     'credit': 0.0,      'name': '2016_1_1',     'account_id': cls.company_data['default_account_payable'].id,       'partner_id': cls.partner_a.id}),
                (0, 0, {'debit': 200.0,     'credit': 0.0,      'name': '2016_1_1',     'account_id': cls.company_data['default_account_payable'].id,       'partner_id': cls.partner_b.id}),
                (0, 0, {'debit': 0.0,       'credit': 300.0,    'name': '2016_1_2',     'account_id': cls.company_data['default_account_receivable'].id,    'partner_id': cls.partner_c.id}),
            ],
        })
        cls.move_2016_1.action_post()

        # Entries in 2016 for company_2 to test the initial balance in multi-companies/multi-currencies.
        cls.move_2016_2 = cls.env['account.move'].create({
            'move_type': 'entry',
            'date': fields.Date.from_string('2016-06-01'),
            'journal_id': cls.company_data_2['default_journal_misc'].id,
            'line_ids': [
                (0, 0, {'debit': 100.0,     'credit': 0.0,      'name': '2016_2_1',     'account_id': cls.company_data_2['default_account_payable'].id,     'partner_id': cls.partner_a.id}),
                (0, 0, {'debit': 0.0,       'credit': 100.0,    'name': '2016_2_2',     'account_id': cls.company_data_2['default_account_receivable'].id,  'partner_id': cls.partner_c.id}),
            ],
        })
        cls.move_2016_2.action_post()

        # Entry in 2017 for company_1 to test the report at current date.
        cls.move_2017_1 = cls.env['account.move'].create({
            'move_type': 'entry',
            'date': fields.Date.from_string('2017-01-01'),
            'journal_id': cls.company_data['default_journal_misc'].id,
            'line_ids': [
                (0, 0, {'debit': 1000.0,    'credit': 0.0,      'name': '2017_1_1',     'account_id': cls.company_data['default_account_payable'].id,       'partner_id': cls.partner_b.id}),
                (0, 0, {'debit': 2000.0,    'credit': 0.0,      'name': '2017_1_2',     'account_id': cls.company_data['default_account_payable'].id,       'partner_id': cls.partner_a.id}),
                (0, 0, {'debit': 3000.0,    'credit': 0.0,      'name': '2017_1_3',     'account_id': cls.company_data['default_account_payable'].id,       'partner_id': cls.partner_a.id}),
                (0, 0, {'debit': 4000.0,    'credit': 0.0,      'name': '2017_1_4',     'account_id': cls.company_data['default_account_receivable'].id,    'partner_id': cls.partner_a.id}),
                (0, 0, {'debit': 5000.0,    'credit': 0.0,      'name': '2017_1_5',     'account_id': cls.company_data['default_account_receivable'].id,    'partner_id': cls.partner_a.id}),
                (0, 0, {'debit': 6000.0,    'credit': 0.0,      'name': '2017_1_6',     'account_id': cls.company_data['default_account_receivable'].id,    'partner_id': cls.partner_a.id}),
                (0, 0, {'debit': 0.0,       'credit': 6000.0,   'name': '2017_1_7',     'account_id': cls.company_data['default_account_receivable'].id,    'partner_id': cls.partner_c.id}),
                (0, 0, {'debit': 0.0,       'credit': 7000.0,   'name': '2017_1_8',     'account_id': cls.company_data['default_account_receivable'].id,    'partner_id': cls.partner_c.id}),
                (0, 0, {'debit': 0.0,       'credit': 8000.0,   'name': '2017_1_9',     'account_id': cls.company_data['default_account_receivable'].id,    'partner_id': cls.partner_c.id}),
            ],
        })
        cls.move_2017_1.action_post()

        # Entry in 2017 for company_2 to test the current period in multi-companies/multi-currencies.
        cls.move_2017_2 = cls.env['account.move'].create({
            'move_type': 'entry',
            'date': fields.Date.from_string('2017-06-01'),
            'journal_id': cls.company_data_2['default_journal_misc'].id,
            'line_ids': [
                (0, 0, {'debit': 400.0,     'credit': 0.0,      'name': '2017_2_1',     'account_id': cls.company_data_2['default_account_receivable'].id}),
                (0, 0, {'debit': 0.0,       'credit': 400.0,    'name': '2017_2_2',     'account_id': cls.company_data_2['default_account_receivable'].id}),
            ],
        })
        cls.move_2017_2.action_post()

        # Deactive all currencies to ensure group_multi_currency is disabled.
        cls.env['res.currency'].search([('name', '!=', 'USD')]).with_context(force_deactivate=True).active = False

        cls.report = cls.env.ref('account_reports.partner_ledger_report')

    def test_partner_ledger_unfold(self):
        ''' Test unfolding a line when rendering the whole report. '''
        options = self._generate_options(self.report, fields.Date.from_string('2017-01-01'), fields.Date.from_string('2017-12-31'))

        self.assertLinesValues(
            self.report._get_lines(options),
            #   Name                                    Debit           Credit          Balance
            [   0,                                      6,              7,              9],
            [
                ('partner_a',                           20150.0,        0.0,            20150.0),
                ('partner_b',                           1200.0,         0.0,            1200.0),
                ('partner_c',                           0.0,            21350.0,        -21350.0),
                ('Unknown Partner',                     200.0,          200.0,          0.0),
                ('Total',                               21550.0,        21550.0,        0.0),
            ],
            options,
        )

        options['unfolded_lines'] = [self.report._get_generic_line_id('res.partner', self.partner_a.id)]

        self.assertLinesValues(
            self.report._get_lines(options),
            #   Name                                    Debit           Credit          Balance
            [   0,                                      6,              7,              9],
            [
                ('partner_a',                           20150.0,        0.0,            20150.0),
                ('Initial Balance',                     150.0,          0.0,            150.0),
                ('MISC/2017/01/0001 - 2017_1_2',        2000.0,         0.0,            2150.0),
                ('MISC/2017/01/0001 - 2017_1_3',        3000.0,         0.0,            5150.0),
                ('MISC/2017/01/0001 - 2017_1_4',        4000.0,         0.0,            9150.0),
                ('MISC/2017/01/0001 - 2017_1_5',        5000.0,         0.0,            14150.0),
                ('MISC/2017/01/0001 - 2017_1_6',        6000.0,         0.0,            20150.0),
                ('Total partner_a',                     20150.0,        0.0,            20150.0),
                ('partner_b',                           1200.0,         0.0,            1200.0),
                ('partner_c',                           0.0,            21350.0,        -21350.0),
                ('Unknown Partner',                     200.0,          200.0,          0.0),
                ('Total',                               21550.0,        21550.0,        0.0),
            ],
            options,
        )

    def test_partner_ledger_load_more(self):
        ''' Test unfolding a line to use the load more. '''
        self.report.load_more_limit = 2

        options = self._generate_options(self.report, fields.Date.from_string('2017-01-01'), fields.Date.from_string('2017-12-31'))
        options['unfolded_lines'] = [self.report._get_generic_line_id('res.partner', self.partner_a.id)]

        report_lines = self.report._get_lines(options)

        self.assertLinesValues(
            report_lines,
            #   Name                                    Debit           Credit          Balance
            [   0,                                      6,              7,              9],
            [
                ('partner_a',                           20150.0,        0.0,            20150.0),
                ('Initial Balance',                     150.0,          0.0,            150.0),
                ('MISC/2017/01/0001 - 2017_1_2',        2000.0,         0.0,            2150.0),
                ('MISC/2017/01/0001 - 2017_1_3',        3000.0,         0.0,            5150.0),
                ('Load more...',                        '',             '',             ''),
                ('Total partner_a',                     20150.0,        0.0,            20150.0),
                ('partner_b',                           1200.0,         0.0,            1200.0),
                ('partner_c',                           0.0,            21350.0,        -21350.0),
                ('Unknown Partner',                     200.0,          200.0,          0.0),
                ('Total',                               21550.0,        21550.0,        0.0),
            ],
            options,
        )

        load_more_1 = self.report._expand_unfoldable_line('_report_expand_unfoldable_line_partner_ledger',
                                                          report_lines[0]['id'], report_lines[4]['groupby'], options,
                                                          report_lines[4]['progress'],
                                                          report_lines[4]['offset'])

        self.assertLinesValues(
            load_more_1,
            #   Name                                    Debit           Credit          Balance
            [   0,                                      6,              7,              9],
            [
                ('MISC/2017/01/0001 - 2017_1_4',          4000.0,         0.0,            9150.0),
                ('MISC/2017/01/0001 - 2017_1_5',          5000.0,         0.0,            14150.0),
                ('Load more...',                        '',             '',             ''),
            ],
            options,
        )

        load_more_2 = self.report._expand_unfoldable_line('_report_expand_unfoldable_line_partner_ledger',
                                                          report_lines[0]['id'], load_more_1[2]['groupby'], options,
                                                          load_more_1[2]['progress'],
                                                          load_more_1[2]['offset'])

        self.assertLinesValues(
            load_more_2,
            #   Name                                    Debit           Credit          Balance
            [   0,                                      6,              7,              9],
            [
                ('MISC/2017/01/0001 - 2017_1_6',          6000.0,         0.0,            20150.0),
            ],
            options,
        )

    def test_partner_ledger_filter_account_types(self):
        ''' Test building the report with a filter on account types.
        When filtering on receivable accounts (i.e. trade_receivable and/or non_trade_receivable), partner_b should disappear from the report.
        '''
        options = self._generate_options(self.report, fields.Date.from_string('2017-01-01'), fields.Date.from_string('2017-12-31'))
        options['unfolded_lines'] = [self.report._get_generic_line_id('res.partner', self.partner_a.id)]
        options = self._update_multi_selector_filter(options, 'account_type', ['non_trade_receivable', 'trade_receivable'])

        self.assertLinesValues(
            self.report._get_lines(options),
            #   Name                                    Debit           Credit          Balance
            [   0,                                      6,              7,              9],
            [
                ('partner_a',                           15000.0,        0.0,            15000.0),
                ('MISC/2017/01/0001 - 2017_1_4',        4000.0,         0.0,            4000.0),
                ('MISC/2017/01/0001 - 2017_1_5',        5000.0,         0.0,            9000.0),
                ('MISC/2017/01/0001 - 2017_1_6',        6000.0,         0.0,            15000.0),
                ('Total partner_a',                     15000.0,        0.0,            15000.0),
                ('partner_c',                           0.0,            21350.0,        -21350.0),
                ('Unknown Partner',                     200.0,          200.0,          0.0),
                ('Total',                               15200.0,        21550.0,        -6350.0),
            ],
            options,
        )

    def test_partner_ledger_filter_partners(self):
        ''' Test the filter on top allowing to filter on res.partner.'''
        options = self._generate_options(self.report, fields.Date.from_string('2017-01-01'), fields.Date.from_string('2017-12-31'))
        options['partner_ids'] = (self.partner_a + self.partner_c).ids

        self.assertLinesValues(
            self.report._get_lines(options),
            #   Name                                    Debit           Credit          Balance
            [   0,                                      6,              7,              9],
            [
                ('partner_a',                           20150.0,        0.0,            20150.0),
                ('partner_c',                           0.0,            21350.0,        -21350.0),
                ('Total',                               20150.0,        21350.0,        -1200.0),
            ],
            options,
        )

    def test_partner_ledger_filter_partner_categories(self):
        ''' Test the filter on top allowing to filter on res.partner.category.'''
        options = self._generate_options(self.report, fields.Date.from_string('2017-01-01'), fields.Date.from_string('2017-12-31'))
        options['partner_categories'] = self.partner_category_a.ids

        self.assertLinesValues(
            self.report._get_lines(options),
            #   Name                                    Debit           Credit          Balance
            [   0,                                      6,              7,              9],
            [
                ('partner_a',                           20150.0,        0.0,            20150.0),
                ('partner_b',                           1200.0,         0.0,            1200.0),
                ('Total',                               21350.0,        0.0,            21350.0),
            ],
            options,
        )

    def test_partner_ledger_unknown_partner(self):
        ''' Test the partner ledger for whenever a line appearing in it has no partner assigned.
        Check that reconciling this line with an invoice/bill of a partner does affect his balance.
        '''
        options = self._generate_options(self.report, fields.Date.from_string('2017-01-01'), fields.Date.from_string('2017-12-31'))

        misc_move = self.env['account.move'].create({
            'date': '2017-03-31',
            'line_ids': [
                (0, 0, {'debit': 1000.0, 'credit': 0.0,    'account_id': self.company_data['default_account_revenue'].id}),
                (0, 0, {'debit': 0.0,    'credit': 1000.0, 'account_id': self.company_data['default_account_receivable'].id}),
            ],
        })
        misc_move.action_post()

        self.assertLinesValues(
            self.report._get_lines(options),
            #   Name                                    Debit           Credit          Balance
            [   0,                                      6,              7,              9],
            [
                ('partner_a',                           20150.0,        0.0,            20150.0),
                ('partner_b',                           1200.0,         0.0,            1200.0),
                ('partner_c',                           0.0,            21350.0,        -21350.0),
                ('Unknown Partner',                     200.0,          1200.0,         -1000.0),
                ('Total',                               21550.0,        22550.0,        -1000.0),
            ],
            options,
        )

        debit_line = self.move_2017_1.line_ids.filtered(lambda line: line.debit == 4000.0)
        credit_line = misc_move.line_ids.filtered(lambda line: line.credit == 1000.0)
        (debit_line + credit_line).reconcile()

        self.assertLinesValues(
            self.report._get_lines(options),
            #   Name                                    Debit           Credit          Balance
            [   0,                                      6,              7,              9],
            [
                ('partner_a',                           20150.0,        1000.0,         19150.0),
                ('partner_b',                           1200.0,         0.0,            1200.0),
                ('partner_c',                           0.0,            21350.0,        -21350.0),
                ('Unknown Partner',                     1200.0,         1200.0,         0.0),
                ('Total',                               22550.0,        23550.0,        -1000.0),
            ],
            options,
        )

        # Unfold 'partner_a'
        options['unfolded_lines'] = [self.report._get_generic_line_id('res.partner', self.partner_a.id)]

        self.assertLinesValues(
            self.report._get_lines(options),
            #   Name                                    Debit           Credit          Balance
            [   0,                                      6,              7,              9],
            [
                ('partner_a',                           20150.0,        1000.0,         19150.0),
                ('Initial Balance',                     150.0,          0.0,            150.0),
                ('MISC/2017/01/0001 - 2017_1_2',        2000.0,         0.0,            2150.0),
                ('MISC/2017/01/0001 - 2017_1_3',        3000.0,         0.0,            5150.0),
                ('MISC/2017/01/0001 - 2017_1_4',        4000.0,         0.0,            9150.0),
                ('MISC/2017/01/0001 - 2017_1_5',        5000.0,         0.0,            14150.0),
                ('MISC/2017/01/0001 - 2017_1_6',        6000.0,         0.0,            20150.0),
                ('MISC/2017/03/0001',                   0.0,            1000.0,         19150.0),
                ('Total partner_a',                     20150.0,        1000.0,         19150.0),
                ('partner_b',                           1200.0,         0.0,            1200.0),
                ('partner_c',                           0.0,            21350.0,        -21350.0),
                ('Unknown Partner',                     1200.0,         1200.0,         0.0),
                ('Total',                               22550.0,        23550.0,        -1000.0),
            ],
            options,
        )

        # Unfold 'Unknown Partner'
        options['unfolded_lines'] = [self.report._get_generic_line_id('res.partner', None, markup='no_partner')]

        self.assertLinesValues(
            self.report._get_lines(options),
            #   Name                                    Debit           Credit          Balance
            [   0,                                      6,              7,              9],
            [
                ('partner_a',                           20150.0,        1000.0,         19150.0),
                ('partner_b',                           1200.0,         0.0,            1200.0),
                ('partner_c',                           0.0,            21350.0,        -21350.0),
                ('Unknown Partner',                     1200.0,         1200.0,         0.0),
                ('MISC/2017/03/0001',                   0.0,            1000.0,         -1000.0),
                ('MISC/2017/06/0001 - 2017_2_1',        200.0,          0.0,            -800.0),
                ('MISC/2017/06/0001 - 2017_2_2',        0.0,            200.0,          -1000.0),
                ('MISC/2017/03/0001',                   1000.0,         0.0,            0.0),
                ('Total Unknown Partner',               1200.0,         1200.0,         0.0),
                ('Total',                               22550.0,        23550.0,        -1000.0),
            ],
            options,
        )

        # Change the dates to exclude the reconciliation max date: situation is back to the beginning
        options = self._generate_options(self.report, fields.Date.from_string('2017-01-01'), fields.Date.from_string('2017-03-30'))

        self.assertLinesValues(
            self.report._get_lines(options),
            #   Name                                    Debit           Credit          Balance
            [   0,                                      6,              7,              9],
            [
                ('partner_a',                           20150.0,        0.0,            20150.0),
                ('partner_b',                           1200.0,         0.0,            1200.0),
                ('partner_c',                           0.0,            21350.0,        -21350.0),
                ('Total',                               21350.0,        21350.0,        0.0),
            ],
            options,
        )

        # Change the dates to have a date_from > to the reconciliation max date and check the initial balances are correct
        options = self._generate_options(self.report, fields.Date.from_string('2017-04-01'), fields.Date.from_string('2017-04-01'))

        self.assertLinesValues(
            self.report._get_lines(options),
            #   Name                                    Debit           Credit          Balance
            [   0,                                      6,              7,              9],
            [
                ('partner_a',                           20150.0,        1000.0,         19150.0),
                ('partner_b',                           1200.0,         0.0,            1200.0),
                ('partner_c',                           0.0,            21350.0,        -21350.0),
                ('Unknown Partner',                     1000.0,         1000.0,         0.0),
                ('Total',                               22350.0,        23350.0,        -1000.0),
            ],
            options,
        )

    def test_partner_ledger_prefix_groups(self):
        partner_names = [
            'A',
            'A partner',
            'A nice partner',
            'A new partner',
            'An original partner',
            'Another partner',
            'Anonymous partner',
            'Annoyed partner',
            'Brave partner',
        ]

        test_date = '2010-12-13'
        test_partners = self.env['res.partner']
        for name in partner_names:
            partner = self.env['res.partner'].create({'name': name})
            test_partners += partner
            invoice = self.init_invoice('out_invoice', partner=partner, invoice_date=test_date, amounts=[42.0], taxes=[], post=True)

        # Without prefix groups
        options = self._generate_options(self.report, test_date, test_date)

        self.assertLinesValues(
            self.report._get_lines(options),
            #   Name                               Journal           Debit          Credit            Balance
            [   0,                                      1,              6,              7,                9],
            [
                ('A',                                  '',           42.0,            0.0,             42.0),
                ('A new partner',                      '',           42.0,            0.0,             42.0),
                ('A nice partner',                     '',           42.0,            0.0,             42.0),
                ('A partner',                          '',           42.0,            0.0,             42.0),
                ('An original partner',                '',           42.0,            0.0,             42.0),
                ('Annoyed partner',                    '',           42.0,            0.0,             42.0),
                ('Anonymous partner',                  '',           42.0,            0.0,             42.0),
                ('Another partner',                    '',           42.0,            0.0,             42.0),
                ('Brave partner',                      '',           42.0,            0.0,             42.0),
                ('Total',                              '',          378.0,            0.0,            378.0),
            ],
            options,
        )

        # With prefix groups
        self.report.prefix_groups_threshold = 3
        options = self._generate_options(self.report, test_date, test_date, default_options={'unfold_all': True})

        self.assertLinesValues(
            self.report._get_lines(options),
            #   Name                                   Journal           Debit          Credit            Balance
            [   0,                                        1,                6,              7,                9],
            [
                ('A (8 lines)',                          '',            336.0,            0.0,            336.0),
                ('A',                                    '',             42.0,            0.0,             42.0),
                ('INV/2010/00001',                    'INV',             42.0,            0.0,             42.0),
                ('Total A',                              '',             42.0,            0.0,             42.0),
                ('A[ ] (3 lines)',                       '',            126.0,            0.0,            126.0),
                ('A N (2 lines)',                        '',             84.0,            0.0,             84.0),
                ('A new partner',                        '',             42.0,            0.0,             42.0),
                ('INV/2010/00004',                    'INV',             42.0,            0.0,             42.0),
                ('Total A new partner',                  '',             42.0,            0.0,             42.0),
                ('A nice partner',                       '',             42.0,            0.0,             42.0),
                ('INV/2010/00003',                    'INV',             42.0,            0.0,             42.0),
                ('Total A nice partner',                 '',             42.0,            0.0,             42.0),
                ('Total A N (2 lines)',                  '',             84.0,            0.0,             84.0),
                ('A P (1 line)',                         '',             42.0,            0.0,             42.0),
                ('A partner',                            '',             42.0,            0.0,             42.0),
                ('INV/2010/00002',                    'INV',             42.0,            0.0,             42.0),
                ('Total A partner',                      '',             42.0,            0.0,             42.0),
                ('Total A P (1 line)',                   '',             42.0,            0.0,             42.0),
                ('Total A[ ] (3 lines)',                 '',            126.0,            0.0,            126.0),
                ('AN (4 lines)',                         '',            168.0,            0.0,            168.0),
                ('AN[ ] (1 line)',                       '',             42.0,            0.0,             42.0),
                ('An original partner',                  '',             42.0,            0.0,             42.0),
                ('INV/2010/00005',                    'INV',             42.0,            0.0,             42.0),
                ('Total An original partner',            '',             42.0,            0.0,             42.0),
                ('Total AN[ ] (1 line)',                 '',             42.0,            0.0,             42.0),
                ('ANN (1 line)',                         '',             42.0,            0.0,             42.0),
                ('Annoyed partner',                      '',             42.0,            0.0,             42.0),
                ('INV/2010/00008',                    'INV',             42.0,            0.0,             42.0),
                ('Total Annoyed partner',                '',             42.0,            0.0,             42.0),
                ('Total ANN (1 line)',                   '',             42.0,            0.0,             42.0),
                ('ANO (2 lines)',                        '',             84.0,            0.0,             84.0),
                ('Anonymous partner',                    '',             42.0,            0.0,             42.0),
                ('INV/2010/00007',                    'INV',             42.0,            0.0,             42.0),
                ('Total Anonymous partner',              '',             42.0,            0.0,             42.0),
                ('Another partner',                      '',             42.0,            0.0,             42.0),
                ('INV/2010/00006',                    'INV',             42.0,            0.0,             42.0),
                ('Total Another partner',                '',             42.0,            0.0,             42.0),
                ('Total ANO (2 lines)',                  '',             84.0,            0.0,             84.0),
                ('Total AN (4 lines)',                   '',            168.0,            0.0,            168.0),
                ('Total A (8 lines)',                    '',            336.0,            0.0,            336.0),
                ('B (1 line)',                           '',             42.0,            0.0,             42.0),
                ('Brave partner',                        '',             42.0,            0.0,             42.0),
                ('INV/2010/00009',                    'INV',             42.0,            0.0,             42.0),
                ('Total Brave partner',                  '',             42.0,            0.0,             42.0),
                ('Total B (1 line)',                     '',             42.0,            0.0,             42.0),
                ('Total',                                '',            378.0,            0.0,            378.0),
            ],
            options,
        )

    def test_filter_unreconciled_entries_only(self):
        new_partner = self.env['res.partner'].create({'name': 'Obiwan Kenobi'})
        move_1 = self.init_invoice('out_invoice', partner=new_partner, invoice_date='2019-01-01', amounts=[1000.0], taxes=[], post=True)
        move_2 = self.init_invoice('out_invoice', partner=new_partner, invoice_date='2019-01-01', amounts=[5000.0], taxes=[], post=True)

        self.env['account.payment.register'].create({
            'payment_date': '2019-01-01',
            'line_ids': move_1.line_ids.filtered(lambda l: l.display_type == 'payment_term'),
            'amount': 700.0,
        })._create_payments()
        self.env['account.payment.register'].create({
            'payment_date': '2019-01-01',
            'line_ids': move_2.line_ids.filtered(lambda l: l.display_type == 'payment_term'),
        })._create_payments()

        self.assertEqual(move_1.payment_state, 'partial')
        self.assertEqual(move_2.payment_state, 'in_payment')

        options = self._generate_options(self.report, '2019-01-01', '2019-12-31', default_options={'partner_ids': new_partner.ids})
        self.assertLinesValues(
            self.report._get_lines(options),
            #   Name                                      Debit              Credit            Balance
            [   0,                                            6,                  7,                9],
            [
                ('Obiwan Kenobi',                        6000.0,             5700.0,             300.0),
                ('Total',                                6000.0,             5700.0,             300.0),
            ],
            options
        )

        options['unreconciled'] = True
        self.assertLinesValues(
            self.report._get_lines(options),
            #   Name                                      Debit              Credit            Balance
            [   0,                                            6,                  7,                9],
            [
                ('Obiwan Kenobi',                        1000.0,             700.0,             300.0),
                ('Total',                                1000.0,             700.0,             300.0),
            ],
            options
        )

    def test_print_pdf_exclude_partner_with_name_similar_to_another_partner_email(self):
        """
        This test verifies that when printing a PDF report, the report accurately reflects the data displayed on the view
        by excluding partners whose email addresses are similar to other partners' names if the search bar is used to filter out partners.
        """
        partner = self.env['res.partner'].create({'name': 'Great Customer', 'email': 'partner_a@test.com'})
        self.init_invoice('out_invoice', partner=partner, invoice_date='2019-02-14', amounts=[1000.0], taxes=[], post=True)
        options = self._generate_options(self.report, '2019-02-01', '2019-02-28', default_options={
                'filter_search_bar': 'partner_a',
                'export_mode': 'print',
            })
        lines = self.report._get_lines(options)
        self.assertFalse(partner.name in [line['name'] for line in lines])
