# -*- coding: utf-8 -*-
# pylint: disable=C0326
from .common import TestAccountReportsCommon

from odoo import fields, Command
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestAgedReceivableReport(TestAccountReportsCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.partner_category_a = cls.env['res.partner.category'].create({'name': 'partner_categ_a'})
        cls.partner_category_b = cls.env['res.partner.category'].create({'name': 'partner_categ_b'})

        cls.partner_a = cls.env['res.partner'].create({'name': 'partner_a', 'company_id': False, 'category_id': [Command.set([cls.partner_category_a.id, cls.partner_category_b.id])]})
        cls.partner_b = cls.env['res.partner'].create({'name': 'partner_b', 'company_id': False, 'category_id': [Command.set([cls.partner_category_a.id])]})

        receivable_1 = cls.company_data['default_account_receivable']
        receivable_2 = cls.copy_account(cls.company_data['default_account_receivable'])
        receivable_3 = cls.copy_account(cls.company_data['default_account_receivable'])
        receivable_4 = cls.company_data_2['default_account_receivable']
        receivable_5 = cls.copy_account(cls.company_data_2['default_account_receivable'])
        receivable_6 = cls.copy_account(cls.company_data_2['default_account_receivable'])
        misc_1 = cls.company_data['default_account_revenue']
        misc_2 = cls.company_data_2['default_account_revenue']

        # Test will use the following dates:
        # As of                  2017-02-01
        # 1 - 30:   2017-01-31 - 2017-01-02
        # 31 - 60:  2017-01-01 - 2016-12-03
        # 61 - 90:  2016-12-02 - 2016-11-03
        # 91 - 120: 2016-11-02 - 2016-10-04
        # Older:    2016-10-03

        # ==== Journal entries in company_1 for partner_a ====

        move_1 = cls.env['account.move'].create({
            'move_type': 'entry',
            'date': fields.Date.from_string('2016-11-03'),
            'invoice_date': fields.Date.from_string('2016-11-03'),
            'journal_id': cls.company_data['default_journal_sale'].id,
            'line_ids': [
                # 1000.0 in 61 - 90.
                Command.create({'debit': 1000.0,    'credit': 0.0,      'date_maturity': False,         'account_id': receivable_1.id,      'partner_id': cls.partner_a.id}),
                # -800.0 in 31 - 60
                Command.create({'debit': 0.0,       'credit': 800.0,    'date_maturity': '2017-01-01',  'account_id': receivable_2.id,      'partner_id': cls.partner_a.id}),
                # Ignored line.
                Command.create({'debit': 0.0,       'credit': 200.0,    'date_maturity': False,         'account_id': misc_1.id,            'partner_id': cls.partner_a.id}),
            ],
        })

        move_2 = cls.env['account.move'].create({
            'move_type': 'entry',
            'date': fields.Date.from_string('2016-10-05'),
            'invoice_date': fields.Date.from_string('2016-10-05'),
            'journal_id': cls.company_data['default_journal_sale'].id,
            'line_ids': [
                # -200.0 in 61 - 90
                Command.create({'debit': 0.0,       'credit': 200.0,    'date_maturity': '2016-12-02',  'account_id': receivable_1.id,      'partner_id': cls.partner_a.id}),
                # -300.0 in 31 - 60
                Command.create({'debit': 0.0,       'credit': 300.0,    'date_maturity': '2016-12-03',  'account_id': receivable_1.id,      'partner_id': cls.partner_a.id}),
                # 1000.0 in 91 - 120
                Command.create({'debit': 1000.0,    'credit': 0.0,      'date_maturity': False,         'account_id': receivable_2.id,      'partner_id': cls.partner_a.id}),
                # 100.0 in all dates
                Command.create({'debit': 100.0,     'credit': 0.0,      'date_maturity': '2017-02-01',  'account_id': receivable_3.id,      'partner_id': cls.partner_a.id}),
                Command.create({'debit': 100.0,     'credit': 0.0,      'date_maturity': '2017-01-02',  'account_id': receivable_3.id,      'partner_id': cls.partner_a.id}),
                Command.create({'debit': 100.0,     'credit': 0.0,      'date_maturity': '2016-12-03',  'account_id': receivable_3.id,      'partner_id': cls.partner_a.id}),
                Command.create({'debit': 100.0,     'credit': 0.0,      'date_maturity': '2016-11-03',  'account_id': receivable_3.id,      'partner_id': cls.partner_a.id}),
                Command.create({'debit': 100.0,     'credit': 0.0,      'date_maturity': '2016-10-04',  'account_id': receivable_3.id,      'partner_id': cls.partner_a.id}),
                Command.create({'debit': 100.0,     'credit': 0.0,      'date_maturity': '2016-01-01',  'account_id': receivable_3.id,      'partner_id': cls.partner_a.id}),
                # Ignored line.
                Command.create({'debit': 0.0,       'credit': 1100.0,   'date_maturity': '2016-10-05',  'account_id': misc_1.id,            'partner_id': cls.partner_a.id}),
            ],
        })
        (move_1 + move_2).action_post()
        (move_1 + move_2).line_ids.filtered(lambda line: line.account_id == receivable_1).reconcile()
        (move_1 + move_2).line_ids.filtered(lambda line: line.account_id == receivable_2).reconcile()

        # ==== Journal entries in company_2 for partner_b ====

        move_3 = cls.env['account.move'].create({
            'move_type': 'entry',
            'date': fields.Date.from_string('2016-11-03'),
            'invoice_date': fields.Date.from_string('2016-11-03'),
            'journal_id': cls.company_data_2['default_journal_sale'].id,
            'line_ids': [
                # 1000.0 in 61 - 90.
                Command.create({'debit': 1000.0,    'credit': 0.0,      'date_maturity': False,         'account_id': receivable_4.id,      'partner_id': cls.partner_b.id}),
                # -200.0 in 31 - 60
                Command.create({'debit': 0.0,       'credit': 800.0,    'date_maturity': '2017-01-01',  'account_id': receivable_5.id,      'partner_id': cls.partner_b.id}),
                # Ignored line.
                Command.create({'debit': 0.0,       'credit': 200.0,    'date_maturity': False,         'account_id': misc_2.id,            'partner_id': cls.partner_b.id}),
            ],
        })

        move_4 = cls.env['account.move'].create({
            'move_type': 'entry',
            'date': fields.Date.from_string('2016-10-05'),
            'invoice_date': fields.Date.from_string('2016-10-05'),
            'journal_id': cls.company_data_2['default_journal_sale'].id,
            'line_ids': [
                # -200.0 in 61 - 90
                Command.create({'debit': 0.0,       'credit': 200.0,    'date_maturity': '2016-12-02',  'account_id': receivable_4.id,      'partner_id': cls.partner_b.id}),
                # -300.0 in 31 - 60
                Command.create({'debit': 0.0,       'credit': 300.0,    'date_maturity': '2016-12-03',  'account_id': receivable_4.id,      'partner_id': cls.partner_b.id}),
                # 1000.0 in 91 - 120
                Command.create({'debit': 1000.0,    'credit': 0.0,      'date_maturity': False,         'account_id': receivable_5.id,      'partner_id': cls.partner_b.id}),
                # 100.0 in all dates
                Command.create({'debit': 100.0,     'credit': 0.0,      'date_maturity': '2017-02-01',  'account_id': receivable_6.id,      'partner_id': cls.partner_b.id}),
                Command.create({'debit': 100.0,     'credit': 0.0,      'date_maturity': '2017-01-02',  'account_id': receivable_6.id,      'partner_id': cls.partner_b.id}),
                Command.create({'debit': 100.0,     'credit': 0.0,      'date_maturity': '2016-12-03',  'account_id': receivable_6.id,      'partner_id': cls.partner_b.id}),
                Command.create({'debit': 100.0,     'credit': 0.0,      'date_maturity': '2016-11-03',  'account_id': receivable_6.id,      'partner_id': cls.partner_b.id}),
                Command.create({'debit': 100.0,     'credit': 0.0,      'date_maturity': '2016-10-04',  'account_id': receivable_6.id,      'partner_id': cls.partner_b.id}),
                Command.create({'debit': 100.0,     'credit': 0.0,      'date_maturity': '2016-01-01',  'account_id': receivable_6.id,      'partner_id': cls.partner_b.id}),
                # Ignored line.
                Command.create({'debit': 0.0,       'credit': 1100.0,   'date_maturity': False,         'account_id': misc_2.id,            'partner_id': cls.partner_b.id}),
            ],
        })
        (move_3 + move_4).action_post()
        (move_3 + move_4).line_ids.filtered(lambda line: line.account_id == receivable_4).reconcile()
        (move_3 + move_4).line_ids.filtered(lambda line: line.account_id == receivable_5).reconcile()
        cls.env['res.currency'].search([('name', '!=', 'USD')]).with_context(force_deactivate=True).active = False
        cls.env.companies = cls.company_data['company'] + cls.company_data_2['company']
        cls.report = cls.env.ref('account_reports.aged_receivable_report')
        cls.parent_line_id = cls._get_basic_line_dict_id_from_report_line_ref("account_reports.aged_receivable_line")

    def test_aged_receivable_unfold_1_whole_report(self):
        """ Test unfolding a line when rendering the whole report. """
        options = self._generate_options(self.report, fields.Date.from_string('2017-02-01'), fields.Date.from_string('2017-02-01'))
        partner_a_line_id = self.report._get_generic_line_id('res.partner', self.partner_a.id, parent_line_id=self.parent_line_id, markup='groupby:partner_id')
        options['unfolded_lines'] = [partner_a_line_id]

        # Sort by Expected Date (usually the same as the due date)
        options['order_column'] = {
            'expression_label': 'expected_date',
            'direction': 'ASC',
        }

        report_lines = self.report._get_lines(options)

        sorted_report_lines = self.report.sort_lines(report_lines, options)
        self.assertLinesValues(
            # pylint: disable=C0326
            sorted_report_lines,
            #   Name                    Expected Date   Not Due On      1 - 30     31 - 60     61 - 90    91 - 120       Older        Total
            [   0,                                 3,           4,          5,          6,          7,          8,         9,           10],
            [
                ('Aged Receivable',               '',       150.0,      150.0,      150.0,      900.0,      450.0,      150.0,      1950.0),
                ('partner_a',                     '',       100.0,      100.0,      100.0,      600.0,      300.0,      100.0,      1300.0),
                ('INV/2016/00002',      '01/01/2016',         0.0,        0.0,        0.0,        0.0,        0.0,      100.0,          ''),
                ('INV/2016/00002',      '10/04/2016',         0.0,        0.0,        0.0,        0.0,      100.0,        0.0,          ''),
                ('INV/2016/00002',      '10/05/2016',         0.0,        0.0,        0.0,        0.0,      200.0,        0.0,          ''),
                ('INV/2016/00001',      '11/03/2016',         0.0,        0.0,        0.0,      500.0,        0.0,        0.0,          ''),
                ('INV/2016/00002',      '11/03/2016',         0.0,        0.0,        0.0,      100.0,        0.0,        0.0,          ''),
                ('INV/2016/00002',      '12/03/2016',         0.0,        0.0,      100.0,        0.0,        0.0,        0.0,          ''),
                ('INV/2016/00002',      '01/02/2017',         0.0,      100.0,        0.0,        0.0,        0.0,        0.0,          ''),
                ('INV/2016/00002',      '02/01/2017',       100.0,        0.0,        0.0,        0.0,        0.0,        0.0,          ''),
                ('Total partner_a',               '',       100.0,      100.0,      100.0,       600.0,     300.0,      100.0,      1300.0),
                ('partner_b',                     '',        50.0,      50.0,        50.0,       300.0,     150.0,       50.0,       650.0),
                ('Total Aged Receivable',         '',       150.0,      150.0,      150.0,      900.0,      450.0,      150.0,      1950.0),
            ],
            options,
        )

        # Sort 61 - 90 decreasing.
        options['order_column'] = {
            'expression_label': 'period3',
            'direction': 'DESC',
        }

        self.assertLinesValues(
            # pylint: disable=C0326
            self.report.sort_lines(sorted_report_lines, options),
            #   Name                    Expected Date   Not Due On      1 - 30     31 - 60     61 - 90    91 - 120       Older        Total
            [   0,                                 3,           4,          5,          6,          7,          8,          9,          10],
            [
                ('Aged Receivable',               '',       150.0,      150.0,      150.0,      900.0,      450.0,      150.0,      1950.0),
                ('partner_a',                     '',       100.0,      100.0,      100.0,      600.0,      300.0,      100.0,      1300.0),
                ('INV/2016/00001',      '11/03/2016',         0.0,        0.0,        0.0,      500.0,        0.0,        0.0,          ''),
                ('INV/2016/00002',      '11/03/2016',         0.0,        0.0,        0.0,      100.0,        0.0,        0.0,          ''),
                ('INV/2016/00002',      '01/01/2016',         0.0,        0.0,        0.0,        0.0,        0.0,      100.0,          ''),
                ('INV/2016/00002',      '10/04/2016',         0.0,        0.0,        0.0,        0.0,      100.0,        0.0,          ''),
                ('INV/2016/00002',      '10/05/2016',         0.0,        0.0,        0.0,        0.0,      200.0,        0.0,          ''),
                ('INV/2016/00002',      '12/03/2016',         0.0,        0.0,      100.0,        0.0,        0.0,        0.0,          ''),
                ('INV/2016/00002',      '01/02/2017',         0.0,      100.0,        0.0,        0.0,        0.0,        0.0,          ''),
                ('INV/2016/00002',      '02/01/2017',       100.0,        0.0,        0.0,        0.0,        0.0,        0.0,          ''),
                ('Total partner_a',               '',       100.0,      100.0,      100.0,      600.0,      300.0,      100.0,      1300.0),
                ('partner_b',                     '',        50.0,       50.0,       50.0,      300.0,      150.0,       50.0,       650.0),
                ('Total Aged Receivable',         '',       150.0,      150.0,      150.0,      900.0,      450.0,      150.0,      1950.0),
            ],
            options,
        )

        # Sort 61 - 90 increasing.
        options['order_column'] = {
            'expression_label': 'period3',
            'direction': 'ASC',
        }

        self.assertLinesValues(
            # pylint: disable=C0326
            self.report.sort_lines(sorted_report_lines, options),
            #   Name                   Expected Date    Not Due On      1 - 30     31 - 60      61 - 90    91 - 120       Older        Total
            [   0,                                 3,           4,          5,          6,           7,          8,          9,          10],
            [
                ('Aged Receivable',               '',       150.0,      150.0,      150.0,       900.0,      450.0,      150.0,      1950.0),
                ('partner_b',                     '',        50.0,       50.0,       50.0,       300.0,      150.0,       50.0,       650.0),
                ('partner_a',                     '',       100.0,      100.0,      100.0,       600.0,      300.0,      100.0,      1300.0),
                ('INV/2016/00002',      '01/01/2016',         0.0,        0.0,        0.0,         0.0,        0.0,      100.0,          ''),
                ('INV/2016/00002',      '10/04/2016',         0.0,        0.0,        0.0,         0.0,      100.0,        0.0,          ''),
                ('INV/2016/00002',      '10/05/2016',         0.0,        0.0,        0.0,         0.0,      200.0,        0.0,          ''),
                ('INV/2016/00002',      '12/03/2016',         0.0,        0.0,      100.0,         0.0,        0.0,        0.0,          ''),
                ('INV/2016/00002',      '01/02/2017',         0.0,      100.0,        0.0,         0.0,        0.0,        0.0,          ''),
                ('INV/2016/00002',      '02/01/2017',       100.0,        0.0,        0.0,         0.0,        0.0,        0.0,          ''),
                ('INV/2016/00002',      '11/03/2016',         0.0,        0.0,        0.0,       100.0,        0.0,        0.0,          ''),
                ('INV/2016/00001',      '11/03/2016',         0.0,        0.0,        0.0,       500.0,        0.0,        0.0,          ''),
                ('Total partner_a',               '',       100.0,      100.0,      100.0,       600.0,      300.0,      100.0,      1300.0),
                ('Total Aged Receivable',         '',       150.0,      150.0,      150.0,       900.0,      450.0,      150.0,      1950.0),
            ],
            options,
        )

    def test_aged_receivable_unfold_all(self):
        default_options = {
            'unfold_all': True,
            'order_column': {
                'expression_label': 'expected_date',
                'direction': 'ASC',
            }
        }
        options = self._generate_options(self.report, '2017-02-01', '2017-02-01', default_options=default_options)

        report_lines = self.report._get_lines(options)

        self.assertLinesValues(
            # pylint: disable=C0326
            self.report.sort_lines(report_lines, options),
            #   Name                    Expected Date   Not Due On   1 - 30     31 - 60     61 - 90    91 - 120       Older         Total
            [   0,                                 3,       4,          5,          6,          7,          8,          9,          10],
            [
                ('Aged Receivable',               '',   150.0,      150.0,      150.0,       900.0,     450.0,      150.0,      1950.0),
                ('partner_a',                     '',   100.0,      100.0,      100.0,       600.0,     300.0,      100.0,      1300.0),
                ('INV/2016/00002',      '01/01/2016',     0.0,        0.0,        0.0,        0.0,        0.0,      100.0,          ''),
                ('INV/2016/00002',      '10/04/2016',     0.0,        0.0,        0.0,        0.0,      100.0,        0.0,          ''),
                ('INV/2016/00002',      '10/05/2016',     0.0,        0.0,        0.0,        0.0,      200.0,        0.0,          ''),
                ('INV/2016/00001',      '11/03/2016',     0.0,        0.0,        0.0,      500.0,        0.0,        0.0,          ''),
                ('INV/2016/00002',      '11/03/2016',     0.0,        0.0,        0.0,      100.0,        0.0,        0.0,          ''),
                ('INV/2016/00002',      '12/03/2016',     0.0,        0.0,      100.0,        0.0,        0.0,        0.0,          ''),
                ('INV/2016/00002',      '01/02/2017',     0.0,      100.0,        0.0,        0.0,        0.0,        0.0,          ''),
                ('INV/2016/00002',      '02/01/2017',   100.0,        0.0,        0.0,        0.0,        0.0,        0.0,          ''),
                ('Total partner_a',               '',   100.0,      100.0,      100.0,       600.0,     300.0,      100.0,      1300.0),
                ('partner_b',                     '',    50.0,       50.0,       50.0,       300.0,     150.0,       50.0,       650.0),
                ('INV/2016/00002',      '01/01/2016',     0.0,        0.0,        0.0,         0.0,       0.0,       50.0,          ''),
                ('INV/2016/00002',      '10/04/2016',     0.0,        0.0,        0.0,         0.0,      50.0,        0.0,          ''),
                ('INV/2016/00002',      '10/05/2016',     0.0,        0.0,        0.0,         0.0,     100.0,        0.0,          ''),
                ('INV/2016/00001',      '11/03/2016',     0.0,        0.0,        0.0,       250.0,       0.0,        0.0,          ''),
                ('INV/2016/00002',      '11/03/2016',     0.0,        0.0,        0.0,        50.0,       0.0,        0.0,          ''),
                ('INV/2016/00002',      '12/03/2016',     0.0,        0.0,       50.0,         0.0,       0.0,        0.0,          ''),
                ('INV/2016/00002',      '01/02/2017',     0.0,       50.0,        0.0,         0.0,       0.0,        0.0,          ''),
                ('INV/2016/00002',      '02/01/2017',    50.0,        0.0,        0.0,         0.0,       0.0,        0.0,          ''),
                ('Total partner_b',               '',    50.0,       50.0,       50.0,       300.0,     150.0,       50.0,       650.0),
                ('Total Aged Receivable',         '',   150.0,      150.0,      150.0,      900.0,      450.0,      150.0,      1950.0),
            ],
            options
        )

    def test_aged_receivable_unknown_partner(self):
        """ Test that journal items without a partner in the receivable account appear as unknown partner. """

        misc_move = self.env['account.move'].create({
            'date': '2017-03-31',
            'line_ids': [
                Command.create({'debit': 1000.0, 'credit': 0.0, 'account_id': self.company_data['default_account_revenue'].id}),
                Command.create({'debit': 0.0, 'credit': 1000.0, 'account_id': self.company_data['default_account_receivable'].id}),
            ],
        })
        misc_move.action_post()

        options = self._generate_options(self.report, fields.Date.from_string('2017-03-01'), fields.Date.from_string('2017-04-01'))
        self.env.company.totals_below_sections = False

        self.assertLinesValues(
            # pylint: disable=C0326
            self.report._get_lines(options),
            #   Name          Expected Date     Not Due On      1 - 30     31 - 60     61 - 90    91 - 120       Older        Total
            [   0,                       3,             4,          5,          6,          7,          8,          9,          10],
            [
                ('Aged Receivable',     '',           0.0,    -1000.0,      150.0,      150.0,      150.0,     1500.0,       950.0),
                ('partner_a',           '',           0.0,        0.0,      100.0,      100.0,      100.0,     1000.0,      1300.0),
                ('partner_b',           '',           0.0,        0.0,       50.0,       50.0,       50.0,      500.0,       650.0),
                ('Unknown',             '',           0.0,    -1000.0,        0.0,        0.0,        0.0,        0.0,     -1000.0),
            ],
            options,
        )

    def test_aged_receivable_filter_partners(self):
        """ Test the filter on top allowing to filter on res.partner. """
        options = self._generate_options(self.report, fields.Date.from_string('2017-02-01'), fields.Date.from_string('2017-02-01'))
        options['partner_ids'] = self.partner_a.ids
        self.env.company.totals_below_sections = False

        self.assertLinesValues(
            # pylint: disable=C0326
            self.report._get_lines(options),
            #   Name          Expected Date      Not Due On      1 - 30     31 - 60     61 - 90    91 - 120       Older        Total
            [   0,                       3,             4,          5,          6,          7,          8,          9,          10],
            [
                ('Aged Receivable',     '',         100.0,      100.0,      100.0,      600.0,      300.0,      100.0,      1300.0),
                ('partner_a',           '',         100.0,      100.0,      100.0,      600.0,      300.0,      100.0,      1300.0),
            ],
            options,
        )

    def test_aged_receivable_filter_partner_categories(self):
        """ Test the filter on top allowing to filter on res.partner.category. """
        options = self._generate_options(self.report, fields.Date.from_string('2017-02-01'), fields.Date.from_string('2017-02-01'))
        options['partner_categories'] = self.partner_category_a.ids
        self.env.company.totals_below_sections = False

        self.assertLinesValues(
            # pylint: disable=C0326
            self.report._get_lines(options),
            #   Name          Expected Date     Not Due On      1 - 30     31 - 60     61 - 90    91 - 120       Older        Total
            [   0,                       3,             4,          5,          6,          7,          8,          9,          10],
            [
                ('Aged Receivable',     '',         150.0,      150.0,      150.0,      900.0,      450.0,      150.0,      1950.0),
                ('partner_a',           '',         100.0,      100.0,      100.0,      600.0,      300.0,      100.0,      1300.0),
                ('partner_b',           '',          50.0,       50.0,       50.0,      300.0,      150.0,       50.0,       650.0),
            ],
            options,
        )

    def test_aged_receivable_reconciliation_date(self):
        """ Check the values at a date before some reconciliations are done. """
        options = self._generate_options(self.report, fields.Date.from_string('2016-10-31'), fields.Date.from_string('2016-10-31'))
        self.env.company.totals_below_sections = False

        self.assertLinesValues(
            # pylint: disable=C0326
            self.report._get_lines(options),
            #   Name          Expected Date  Not Due On      1 - 30     31 - 60     61 - 90    91 - 120       Older       Total
            [   0,                       3,         4,          5,          6,          7,          8,          9,          10],
            [
                ('Aged Receivable',     '',   -133.35,    1466.66,        0.0,        0.0,        0.0,     133.33,     1466.64),
                ('partner_a',           '',   -100.00,    1100.00,        0.0,        0.0,        0.0,     100.00,     1100.00),
                ('partner_b',           '',    -33.35,     366.66,        0.0,        0.0,        0.0,      33.33,      366.64),
            ],
            options,
        )

    # TODO: move these tests into a generic report test class
    def test_aged_receivable_sort_lines_by_date(self):
        """ Test the sort_lines function using date as sort key. """
        options = self._generate_options(self.report, fields.Date.from_string('2017-02-01'), fields.Date.from_string('2017-02-01'))
        partner_a_line_id = self.report._get_generic_line_id('res.partner', self.partner_a.id, parent_line_id=self.parent_line_id, markup='groupby:partner_id')
        partner_b_line_id = self.report._get_generic_line_id('res.partner', self.partner_b.id, parent_line_id=self.parent_line_id, markup='groupby:partner_id')
        options['unfolded_lines'] = [partner_a_line_id, partner_b_line_id]

        # Sort by Expected Date increasing
        options['order_column'] = {
            'expression_label': 'expected_date',
            'direction': 'ASC',
        }

        report_lines = self.report._get_lines(options)

        self.assertLinesValues(
            # pylint: disable=C0326
            self.report.sort_lines(report_lines, options),
            #   Name                    Invoice Date  Expected Date   Not Due On   1 - 30     31 - 60     61 - 90    91 - 120        Older        Total
            [   0,                                 1,            3,       4,          5,          6,          7,          8,          9,          10],
            [
                ('Aged Receivable',              '',            '',   150.0,      150.0,      150.0,      900.0,      450.0,      150.0,      1950.0),
                ('partner_a',                    '',            '',   100.0,      100.0,      100.0,      600.0,      300.0,      100.0,      1300.0),
                ('INV/2016/00002',      '10/05/2016', '01/01/2016',     0.0,        0.0,        0.0,        0.0,        0.0,      100.0,          ''),
                ('INV/2016/00002',      '10/05/2016', '10/04/2016',     0.0,        0.0,        0.0,        0.0,      100.0,        0.0,          ''),
                ('INV/2016/00002',      '10/05/2016', '10/05/2016',     0.0,        0.0,        0.0,        0.0,      200.0,        0.0,          ''),
                ('INV/2016/00001',      '11/03/2016', '11/03/2016',     0.0,        0.0,        0.0,      500.0,        0.0,        0.0,          ''),
                ('INV/2016/00002',      '10/05/2016', '11/03/2016',     0.0,        0.0,        0.0,      100.0,        0.0,        0.0,          ''),
                ('INV/2016/00002',      '10/05/2016', '12/03/2016',     0.0,        0.0,      100.0,        0.0,        0.0,        0.0,          ''),
                ('INV/2016/00002',      '10/05/2016', '01/02/2017',     0.0,      100.0,        0.0,        0.0,        0.0,        0.0,          ''),
                ('INV/2016/00002',      '10/05/2016', '02/01/2017',   100.0,        0.0,        0.0,        0.0,        0.0,        0.0,          ''),
                ('Total partner_a',               '',           '',   100.0,      100.0,      100.0,       600.0,     300.0,      100.0,      1300.0),
                ('partner_b',                     '',           '',    50.0,       50.0,       50.0,       300.0,     150.0,       50.0,       650.0),
                ('INV/2016/00002',      '10/05/2016', '01/01/2016',     0.0,        0.0,        0.0,         0.0,       0.0,       50.0,          ''),
                ('INV/2016/00002',      '10/05/2016', '10/04/2016',     0.0,        0.0,        0.0,         0.0,      50.0,        0.0,          ''),
                ('INV/2016/00002',      '10/05/2016', '10/05/2016',     0.0,        0.0,        0.0,         0.0,     100.0,        0.0,          ''),
                ('INV/2016/00001',      '11/03/2016', '11/03/2016',     0.0,        0.0,        0.0,       250.0,       0.0,        0.0,          ''),
                ('INV/2016/00002',      '10/05/2016', '11/03/2016',     0.0,        0.0,        0.0,        50.0,       0.0,        0.0,          ''),
                ('INV/2016/00002',      '10/05/2016', '12/03/2016',     0.0,        0.0,       50.0,         0.0,       0.0,        0.0,          ''),
                ('INV/2016/00002',      '10/05/2016', '01/02/2017',     0.0,       50.0,        0.0,         0.0,       0.0,        0.0,          ''),
                ('INV/2016/00002',      '10/05/2016', '02/01/2017',    50.0,        0.0,        0.0,         0.0,       0.0,        0.0,          ''),
                ('Total partner_b',               '',           '',    50.0,       50.0,       50.0,       300.0,     150.0,       50.0,       650.0),
                ('Total Aged Receivable',         '',           '',   150.0,      150.0,      150.0,      900.0,      450.0,      150.0,      1950.0),
            ],
            options,
        )

        # Sort by Expected Date decreasing
        options['order_column'] = {
            'expression_label': 'expected_date',
            'direction': 'DESC',
        }

        self.assertLinesValues(
            # pylint: disable=C0326
            self.report.sort_lines(report_lines, options),
            #   Name                   Expected Date     Not Due On     1 - 30     31 - 60     61 - 90    91 - 120       Older         Total
            [   0,                                 3,            4,          5,          6,          7,          8,          9,          10],
            [
                ('Aged Receivable',               '',        150.0,      150.0,      150.0,      900.0,      450.0,      150.0,      1950.0),
                ('partner_a',                     '',        100.0,      100.0,      100.0,      600.0,      300.0,      100.0,      1300.0),
                ('INV/2016/00002',      '02/01/2017',        100.0,        0.0,        0.0,        0.0,        0.0,        0.0,          ''),
                ('INV/2016/00002',      '01/02/2017',          0.0,      100.0,        0.0,        0.0,        0.0,        0.0,          ''),
                ('INV/2016/00002',      '12/03/2016',          0.0,        0.0,      100.0,        0.0,        0.0,        0.0,          ''),
                ('INV/2016/00001',      '11/03/2016',          0.0,        0.0,        0.0,      500.0,        0.0,        0.0,          ''),
                ('INV/2016/00002',      '11/03/2016',          0.0,        0.0,        0.0,      100.0,        0.0,        0.0,          ''),
                ('INV/2016/00002',      '10/05/2016',          0.0,        0.0,        0.0,        0.0,      200.0,        0.0,          ''),
                ('INV/2016/00002',      '10/04/2016',          0.0,        0.0,        0.0,        0.0,      100.0,        0.0,          ''),
                ('INV/2016/00002',      '01/01/2016',          0.0,        0.0,        0.0,        0.0,        0.0,      100.0,          ''),
                ('Total partner_a',               '',        100.0,      100.0,      100.0,       600.0,     300.0,      100.0,      1300.0),
                ('partner_b',                     '',         50.0,       50.0,       50.0,       300.0,     150.0,       50.0,       650.0),
                ('INV/2016/00002',      '02/01/2017',         50.0,        0.0,        0.0,         0.0,       0.0,        0.0,          ''),
                ('INV/2016/00002',      '01/02/2017',          0.0,       50.0,        0.0,         0.0,       0.0,        0.0,          ''),
                ('INV/2016/00002',      '12/03/2016',          0.0,        0.0,       50.0,         0.0,       0.0,        0.0,          ''),
                ('INV/2016/00001',      '11/03/2016',          0.0,        0.0,        0.0,       250.0,       0.0,        0.0,          ''),
                ('INV/2016/00002',      '11/03/2016',          0.0,        0.0,        0.0,        50.0,       0.0,        0.0,          ''),
                ('INV/2016/00002',      '10/05/2016',          0.0,        0.0,        0.0,         0.0,     100.0,        0.0,          ''),
                ('INV/2016/00002',      '10/04/2016',          0.0,        0.0,        0.0,         0.0,      50.0,        0.0,          ''),
                ('INV/2016/00002',      '01/01/2016',          0.0,        0.0,        0.0,         0.0,       0.0,       50.0,          ''),
                ('Total partner_b',               '',         50.0,       50.0,       50.0,       300.0,     150.0,       50.0,       650.0),
                ('Total Aged Receivable',         '',        150.0,      150.0,      150.0,      900.0,      450.0,      150.0,      1950.0),
            ],
            options,
        )

    def test_aged_receivablesort_lines_by_numeric_value(self):
        """ Test the sort_lines function using float as sort key. """
        options = self._generate_options(self.report, fields.Date.from_string('2017-02-01'), fields.Date.from_string('2017-02-01'))
        partner_a_line_id = self.report._get_generic_line_id('res.partner', self.partner_a.id, parent_line_id=self.parent_line_id, markup='groupby:partner_id')
        partner_b_line_id = self.report._get_generic_line_id('res.partner', self.partner_b.id, parent_line_id=self.parent_line_id, markup='groupby:partner_id')
        options['unfolded_lines'] = [partner_a_line_id, partner_b_line_id]

        # Sort by Not Due On increasing
        options['order_column'] = {
            'expression_label': 'period0',
            'direction': 'ASC',
        }

        report_lines = self.report._get_lines(options)

        self.assertLinesValues(
            # pylint: disable=C0326
            self.report.sort_lines(report_lines, options),
            #   Name                   Expected Date     Not Due On     1 - 30     31 - 60     61 - 90    91 - 120       Older         Total
            [   0,                                 3,            4,          5,          6,          7,          8,          9,          10],
            [
                ('Aged Receivable',               '',        150.0,      150.0,      150.0,      900.0,      450.0,      150.0,      1950.0),
                ('partner_b',                     '',         50.0,       50.0,       50.0,      300.0,      150.0,       50.0,       650.0),
                ('INV/2016/00001',      '11/03/2016',          0.0,        0.0,        0.0,      250.0,        0.0,        0.0,          ''),
                ('INV/2016/00002',      '10/05/2016',          0.0,        0.0,        0.0,        0.0,      100.0,        0.0,          ''),
                ('INV/2016/00002',      '01/02/2017',          0.0,       50.0,        0.0,        0.0,        0.0,        0.0,          ''),
                ('INV/2016/00002',      '12/03/2016',          0.0,        0.0,       50.0,        0.0,        0.0,        0.0,          ''),
                ('INV/2016/00002',      '11/03/2016',          0.0,        0.0,        0.0,       50.0,        0.0,        0.0,          ''),
                ('INV/2016/00002',      '10/04/2016',          0.0,        0.0,        0.0,        0.0,       50.0,        0.0,          ''),
                ('INV/2016/00002',      '01/01/2016',          0.0,        0.0,        0.0,        0.0,        0.0,       50.0,          ''),
                ('INV/2016/00002',      '02/01/2017',         50.0,        0.0,        0.0,        0.0,        0.0,        0.0,          ''),
                ('Total partner_b',               '',         50.0,       50.0,       50.0,      300.0,      150.0,       50.0,       650.0),
                ('partner_a',                     '',        100.0,      100.0,      100.0,      600.0,      300.0,      100.0,      1300.0),
                ('INV/2016/00001',      '11/03/2016',          0.0,        0.0,        0.0,      500.0,        0.0,        0.0,          ''),
                ('INV/2016/00002',      '10/05/2016',          0.0,        0.0,        0.0,        0.0,      200.0,        0.0,          ''),
                ('INV/2016/00002',      '01/02/2017',          0.0,      100.0,        0.0,        0.0,        0.0,        0.0,          ''),
                ('INV/2016/00002',      '12/03/2016',          0.0,        0.0,      100.0,        0.0,        0.0,        0.0,          ''),
                ('INV/2016/00002',      '11/03/2016',          0.0,        0.0,        0.0,      100.0,        0.0,        0.0,          ''),
                ('INV/2016/00002',      '10/04/2016',          0.0,        0.0,        0.0,        0.0,      100.0,        0.0,          ''),
                ('INV/2016/00002',      '01/01/2016',          0.0,        0.0,        0.0,        0.0,        0.0,      100.0,          ''),
                ('INV/2016/00002',      '02/01/2017',        100.0,        0.0,        0.0,        0.0,        0.0,        0.0,          ''),
                ('Total partner_a',               '',        100.0,      100.0,      100.0,       600.0,     300.0,      100.0,      1300.0),
                ('Total Aged Receivable',         '',        150.0,      150.0,      150.0,      900.0,      450.0,      150.0,      1950.0),
            ],
            options,
        )

        # Sort by Not Due On decreasing
        options['order_column'] = {
            'expression_label': 'period0',
            'direction': 'DESC',
        }

        self.assertLinesValues(
            # pylint: disable=C0326
            self.report.sort_lines(report_lines, options),
            #   Name                 Expected Date     Not Due On     1 - 30     31 - 60     61 - 90    91 - 120       Older       Total
            [   0,                                 3,       4,          5,          6,          7,          8,          9,          10],
            [
                ('Aged Receivable',               '',   150.0,      150.0,      150.0,      900.0,      450.0,      150.0,      1950.0),
                ('partner_a',                     '',   100.0,      100.0,      100.0,      600.0,      300.0,      100.0,      1300.0),
                ('INV/2016/00002',      '02/01/2017',   100.0,        0.0,        0.0,        0.0,        0.0,        0.0,          ''),
                ('INV/2016/00001',      '11/03/2016',     0.0,        0.0,        0.0,      500.0,        0.0,        0.0,          ''),
                ('INV/2016/00002',      '10/05/2016',     0.0,        0.0,        0.0,        0.0,      200.0,        0.0,          ''),
                ('INV/2016/00002',      '01/02/2017',     0.0,      100.0,        0.0,        0.0,        0.0,        0.0,          ''),
                ('INV/2016/00002',      '12/03/2016',     0.0,        0.0,      100.0,        0.0,        0.0,        0.0,          ''),
                ('INV/2016/00002',      '11/03/2016',     0.0,        0.0,        0.0,      100.0,        0.0,        0.0,          ''),
                ('INV/2016/00002',      '10/04/2016',     0.0,        0.0,        0.0,        0.0,      100.0,        0.0,          ''),
                ('INV/2016/00002',      '01/01/2016',     0.0,        0.0,        0.0,        0.0,        0.0,      100.0,          ''),
                ('Total partner_a',               '',   100.0,      100.0,      100.0,       600.0,     300.0,      100.0,      1300.0),
                ('partner_b',                     '',    50.0,       50.0,       50.0,      300.0,      150.0,       50.0,       650.0),
                ('INV/2016/00002',      '02/01/2017',    50.0,        0.0,        0.0,        0.0,        0.0,        0.0,          ''),
                ('INV/2016/00001',      '11/03/2016',     0.0,        0.0,        0.0,      250.0,        0.0,        0.0,          ''),
                ('INV/2016/00002',      '10/05/2016',     0.0,        0.0,        0.0,        0.0,      100.0,        0.0,          ''),
                ('INV/2016/00002',      '01/02/2017',     0.0,       50.0,        0.0,        0.0,        0.0,        0.0,          ''),
                ('INV/2016/00002',      '12/03/2016',     0.0,        0.0,       50.0,        0.0,        0.0,        0.0,          ''),
                ('INV/2016/00002',      '11/03/2016',     0.0,        0.0,        0.0,       50.0,        0.0,        0.0,          ''),
                ('INV/2016/00002',      '10/04/2016',     0.0,        0.0,        0.0,        0.0,       50.0,        0.0,          ''),
                ('INV/2016/00002',      '01/01/2016',     0.0,        0.0,        0.0,        0.0,        0.0,       50.0,          ''),
                ('Total partner_b',               '',    50.0,       50.0,       50.0,      300.0,      150.0,       50.0,       650.0),
                ('Total Aged Receivable',         '',   150.0,      150.0,      150.0,      900.0,      450.0,      150.0,      1950.0),
            ],
            options,
        )

    def test_aged_receivable_zero_balanced_without_reconciliation(self):
        options = self._generate_options(self.report, '2010-01-01', '2010-01-01', default_options={'unfold_all': True})
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2010-01-01',
            'invoice_date_due': '2010-01-01',
            'payment_reference': 'I',
            'invoice_line_ids': [Command.create({
                'name': 'test invoice',
                'price_unit': 100,
                'tax_ids': [],
            })]
        })
        invoice.action_post()

        refund = self.env['account.move'].create({
            'move_type': 'out_refund',
            'partner_id': self.partner_a.id,
            'invoice_date': '2010-01-01',
            'invoice_date_due': '2010-01-01',
            'payment_reference': 'R',
            'invoice_line_ids': [Command.create({
                'name': 'test refund',
                'price_unit': 100,
                'tax_ids': [],
            })]
        })
        refund.action_post()

        self.assertLinesValues(
            # pylint: disable=C0326
            self.report._get_lines(options),
            #   Name                    Expected Date  Not Due On      1 - 30     31 - 60     61 - 90    91 - 120       Older       Total
            [   0,                                3,         4,          5,          6,          7,          8,          9,          10],
            [
                ('Aged Receivable',              '',       0.0,        0.0,        0.0,        0.0,        0.0,        0.0,         0.0),
                ('partner_a',                    '',       0.0,        0.0,        0.0,        0.0,        0.0,        0.0,         0.0),
                (f"{refund.name} R",   '01/01/2010',    -100.0,        0.0,        0.0,        0.0,        0.0,        0.0,          ''),
                (f"{invoice.name} I",  '01/01/2010',     100.0,        0.0,        0.0,        0.0,        0.0,        0.0,          ''),
                ('Total partner_a',              '',       0.0,        0.0,        0.0,        0.0,        0.0,        0.0,         0.0),
                ('Total Aged Receivable',        '',       0.0,        0.0,        0.0,        0.0,        0.0,        0.0,         0.0),
            ],
            options,
        )

        # It should still work if both  invoice and refund are partially reconciled with the same amount
        self.env['account.payment.register'].with_context(active_ids=invoice.ids, active_model='account.move').create({
            'amount': 42,
            'payment_date': '2010-01-01',
            'payment_method_line_id': self.outbound_payment_method_line.id,
        })._create_payments()

        self.env['account.payment.register'].with_context(active_ids=refund.ids, active_model='account.move').create({
            'amount': 42,
            'payment_date': '2010-01-01',
            'payment_method_line_id': self.outbound_payment_method_line.id,
        })._create_payments()

        self.assertLinesValues(
            # pylint: disable=C0326
            self.report._get_lines(options),
            #   Name                    Expected Date  Not Due On      1 - 30     31 - 60     61 - 90    91 - 120       Older       Total
            [   0,                                3,         4,          5,          6,          7,          8,          9,          10],
            [
                ('Aged Receivable',              '',       0.0,        0.0,        0.0,        0.0,        0.0,        0.0,         0.0),
                ('partner_a',                    '',       0.0,        0.0,        0.0,        0.0,        0.0,        0.0,         0.0),
                (f"{refund.name} R",   '01/01/2010',     -58.0,        0.0,        0.0,        0.0,        0.0,        0.0,          ''),
                (f"{invoice.name} I",  '01/01/2010',      58.0,        0.0,        0.0,        0.0,        0.0,        0.0,          ''),
                ('Total partner_a',              '',       0.0,        0.0,        0.0,        0.0,        0.0,        0.0,         0.0),
                ('Total Aged Receivable',        '',       0.0,        0.0,        0.0,        0.0,        0.0,        0.0,         0.0),
            ],
            options,
        )

        # It should still work if both  invoice and refund are fully reconciled in the future
        self.env['account.payment.register'].with_context(active_ids=invoice.ids, active_model='account.move').create({
            'amount': 58,
            'payment_date': '2020-01-01',
            'payment_method_line_id': self.outbound_payment_method_line.id,
        })._create_payments()

        self.env['account.payment.register'].with_context(active_ids=refund.ids, active_model='account.move').create({
            'amount': 58,
            'payment_date': '2020-01-01',
            'payment_method_line_id': self.outbound_payment_method_line.id,
        })._create_payments()

        self.assertLinesValues(
            # pylint: disable=C0326
            self.report._get_lines(options),
            #   Name                    Expected Date  Not Due On      1 - 30     31 - 60     61 - 90    91 - 120       Older       Total
            [   0,                                3,         4,          5,          6,          7,          8,          9,          10],
            [
                ('Aged Receivable',              '',       0.0,        0.0,        0.0,        0.0,        0.0,        0.0,         0.0),
                ('partner_a',                    '',       0.0,        0.0,        0.0,        0.0,        0.0,        0.0,         0.0),
                (f"{refund.name} R",   '01/01/2010',     -58.0,        0.0,        0.0,        0.0,        0.0,        0.0,          ''),
                (f"{invoice.name} I",  '01/01/2010',      58.0,        0.0,        0.0,        0.0,        0.0,        0.0,          ''),
                ('Total partner_a',              '',       0.0,        0.0,        0.0,        0.0,        0.0,        0.0,         0.0),
                ('Total Aged Receivable',        '',       0.0,        0.0,        0.0,        0.0,        0.0,        0.0,         0.0),
            ],
            options,
        )

    def test_aged_receivable_prefix_groups(self):
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
        invoices_map = {}
        for name in partner_names:
            partner = self.env['res.partner'].create({'name': name})
            invoice = self.init_invoice('out_invoice', partner=partner, invoice_date=test_date, amounts=[42.0], taxes=[], post=True)
            invoices_map[name] = f'{invoice.name} {invoice.payment_reference}'

        # Without prefix groups
        options = self._generate_options(self.report, test_date, test_date)

        self.assertLinesValues(
            self.report._get_lines(options),
            #   Name                  Not Due On      1 - 30     31 - 60     61 - 90    91 - 120       Older         Total
            [   0,                            4,          5,          6,          7,          8,          9,          10],
            [
                ('Aged Receivable',       378.0,        0.0,        0.0,        0.0,        0.0,        0.0,       378.0),
                ('A',                      42.0,        0.0,        0.0,        0.0,        0.0,        0.0,        42.0),
                ('A new partner',          42.0,        0.0,        0.0,        0.0,        0.0,        0.0,        42.0),
                ('A nice partner',         42.0,        0.0,        0.0,        0.0,        0.0,        0.0,        42.0),
                ('A partner',              42.0,        0.0,        0.0,        0.0,        0.0,        0.0,        42.0),
                ('An original partner',    42.0,        0.0,        0.0,        0.0,        0.0,        0.0,        42.0),
                ('Annoyed partner',        42.0,        0.0,        0.0,        0.0,        0.0,        0.0,        42.0),
                ('Anonymous partner',      42.0,        0.0,        0.0,        0.0,        0.0,        0.0,        42.0),
                ('Another partner',        42.0,        0.0,        0.0,        0.0,        0.0,        0.0,        42.0),
                ('Brave partner',          42.0,        0.0,        0.0,        0.0,        0.0,        0.0,        42.0),
                ('Total Aged Receivable', 378.0,        0.0,        0.0,        0.0,        0.0,        0.0,       378.0),
            ],
            options,
        )

        # With prefix groups
        self.report.prefix_groups_threshold = 3
        options = self._generate_options(self.report, test_date, test_date, default_options={'unfold_all': True})

        self.assertLinesValues(
            self.report._get_lines(options),
            #   Name                             Not Due On    1 - 30     31 - 60     61 - 90    91 - 120       Older         Total
            [   0,                                       4,        5,          6,          7,          8,          9,          10],
            [
                ('Aged Receivable',                  378.0,      0.0,        0.0,        0.0,        0.0,        0.0,       378.0),
                ('A (8 lines)',                      336.0,      0.0,        0.0,        0.0,        0.0,        0.0,       336.0),
                ('A',                                 42.0,      0.0,        0.0,        0.0,        0.0,        0.0,        42.0),
                (invoices_map['A'],                   42.0,      0.0,        0.0,        0.0,        0.0,        0.0,          ''),
                ('Total A',                           42.0,      0.0,        0.0,        0.0,        0.0,        0.0,        42.0),
                ('A[ ] (3 lines)',                   126.0,      0.0,        0.0,        0.0,        0.0,        0.0,       126.0),
                ('A N (2 lines)',                     84.0,      0.0,        0.0,        0.0,        0.0,        0.0,        84.0),
                ('A new partner',                     42.0,      0.0,        0.0,        0.0,        0.0,        0.0,        42.0),
                (invoices_map['A new partner'],       42.0,      0.0,        0.0,        0.0,        0.0,        0.0,          ''),
                ('Total A new partner',               42.0,      0.0,        0.0,        0.0,        0.0,        0.0,        42.0),
                ('A nice partner',                    42.0,      0.0,        0.0,        0.0,        0.0,        0.0,        42.0),
                (invoices_map['A nice partner'],      42.0,      0.0,        0.0,        0.0,        0.0,        0.0,          ''),
                ('Total A nice partner',              42.0,      0.0,        0.0,        0.0,        0.0,        0.0,        42.0),
                ('Total A N (2 lines)',               84.0,      0.0,        0.0,        0.0,        0.0,        0.0,        84.0),
                ('A P (1 line)',                      42.0,      0.0,        0.0,        0.0,        0.0,        0.0,        42.0),
                ('A partner',                         42.0,      0.0,        0.0,        0.0,        0.0,        0.0,        42.0),
                (invoices_map['A partner'],           42.0,      0.0,        0.0,        0.0,        0.0,        0.0,          ''),
                ('Total A partner',                   42.0,      0.0,        0.0,        0.0,        0.0,        0.0,        42.0),
                ('Total A P (1 line)',                42.0,      0.0,        0.0,        0.0,        0.0,        0.0,        42.0),
                ('Total A[ ] (3 lines)',             126.0,      0.0,        0.0,        0.0,        0.0,        0.0,       126.0),
                ('AN (4 lines)',                     168.0,      0.0,        0.0,        0.0,        0.0,        0.0,       168.0),
                ('AN[ ] (1 line)',                    42.0,      0.0,        0.0,        0.0,        0.0,        0.0,        42.0),
                ('An original partner',               42.0,      0.0,        0.0,        0.0,        0.0,        0.0,        42.0),
                (invoices_map['An original partner'], 42.0,      0.0,        0.0,        0.0,        0.0,        0.0,          ''),
                ('Total An original partner',         42.0,      0.0,        0.0,        0.0,        0.0,        0.0,        42.0),
                ('Total AN[ ] (1 line)',              42.0,      0.0,        0.0,        0.0,        0.0,        0.0,        42.0),
                ('ANN (1 line)',                      42.0,      0.0,        0.0,        0.0,        0.0,        0.0,        42.0),
                ('Annoyed partner',                   42.0,      0.0,        0.0,        0.0,        0.0,        0.0,        42.0),
                (invoices_map['Annoyed partner'],     42.0,      0.0,        0.0,        0.0,        0.0,        0.0,          ''),
                ('Total Annoyed partner',             42.0,      0.0,        0.0,        0.0,        0.0,        0.0,        42.0),
                ('Total ANN (1 line)',                42.0,      0.0,        0.0,        0.0,        0.0,        0.0,        42.0),
                ('ANO (2 lines)',                     84.0,      0.0,        0.0,        0.0,        0.0,        0.0,        84.0),
                ('Anonymous partner',                 42.0,      0.0,        0.0,        0.0,        0.0,        0.0,        42.0),
                (invoices_map['Anonymous partner'],   42.0,      0.0,        0.0,        0.0,        0.0,        0.0,          ''),
                ('Total Anonymous partner',           42.0,      0.0,        0.0,        0.0,        0.0,        0.0,        42.0),
                ('Another partner',                   42.0,      0.0,        0.0,        0.0,        0.0,        0.0,        42.0),
                (invoices_map['Another partner'],     42.0,      0.0,        0.0,        0.0,        0.0,        0.0,          ''),
                ('Total Another partner',             42.0,      0.0,        0.0,        0.0,        0.0,        0.0,        42.0),
                ('Total ANO (2 lines)',               84.0,      0.0,        0.0,        0.0,        0.0,        0.0,        84.0),
                ('Total AN (4 lines)',               168.0,      0.0,        0.0,        0.0,        0.0,        0.0,       168.0),
                ('Total A (8 lines)',                336.0,      0.0,        0.0,        0.0,        0.0,        0.0,       336.0),
                ('B (1 line)',                        42.0,      0.0,        0.0,        0.0,        0.0,        0.0,        42.0),
                ('Brave partner',                     42.0,      0.0,        0.0,        0.0,        0.0,        0.0,        42.0),
                (invoices_map['Brave partner'],       42.0,      0.0,        0.0,        0.0,        0.0,        0.0,          ''),
                ('Total Brave partner',               42.0,      0.0,        0.0,        0.0,        0.0,        0.0,        42.0),
                ('Total B (1 line)',                  42.0,      0.0,        0.0,        0.0,        0.0,        0.0,        42.0),
                ('Total Aged Receivable',            378.0,      0.0,        0.0,        0.0,        0.0,        0.0,       378.0),
            ],
            options,
        )

    def test_aged_receivable_partial_reconcile_currency(self):
        """ Check that 'Amount Currency' column values are displayed and computed correctly. """
        foreign_partner = self.env['res.partner'].create({'name': 'foreign_partner'})
        currency = self.currency_data['currency']
        currency.active = True
        self.env.company.totals_below_sections = False

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'invoice_date': '2023-05-01',
            'invoice_date_due': '2023-05-01',
            'partner_id': foreign_partner.id,
            'currency_id': currency.id,
            'invoice_line_ids': [Command.create({
                'name': 'test',
                'quantity': 1,
                'price_unit': 100.0,
                'tax_ids': [],
            })],
        })
        invoice.action_post()

        self.env['account.payment.register'].with_context(
            active_model='account.move',
            active_ids=invoice.ids,
        ).create({
            'amount': 10.0,
            'currency_id': currency.id,
            'payment_date': '2023-05-05',
            'partner_id': foreign_partner.id,
        })._create_payments()

        line_id = self.report._get_generic_line_id('res.partner', foreign_partner.id, markup='groupby:partner_id', parent_line_id=self.parent_line_id)
        options = self._generate_options(self.report, '2023-01-01', '2023-05-01')
        options['unfolded_lines'] = [line_id]

        self.assertLinesValues(
            # pylint: disable=C0326
            self.report._get_unfolded_lines(self.report._get_lines(options), line_id),
            #   Name                                      Due Date     Amount Currency     Currency     As Of     Total
            [   0,                                               1,                  2,           3,        6,       12],
            [
                ('foreign_partner',                             '',                 '',          '',     50.0,     50.0),
                ('INV/2023/00001 INV/2023/00001',     '05/01/2023',              100.0,       'Gol',     50.0,       ''),
            ],
			options,
            currency_map={
                2: {'currency': currency},
            },
        )

        new_options = self._generate_options(self.report, '2023-01-01', '2023-05-05')
        new_options['unfolded_lines'] = [line_id]

        self.assertLinesValues(
            # pylint: disable=C0326
            self.report._get_unfolded_lines(self.report._get_lines(new_options), line_id),
            #   Name                                      Due Date     Amount Currency     Currency     As Of     1-30     Total
            [   0,                                               1,                  2,           3,        6,       7,       12],
            [
                ('foreign_partner',                             '',                 '',          '',      0.0,    45.0,     45.0),
                ('INV/2023/00001 INV/2023/00001',     '05/01/2023',               90.0,       'Gol',      0.0,    45.0,       ''),
            ],
			options,
            currency_map={
                2: {'currency': currency},
            },
        )
