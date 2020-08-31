# -*- coding: utf-8 -*-
from odoo import fields
from odoo.tests import tagged
from odoo.tests.common import Form
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, date_utils
from unittest.mock import patch
import datetime
import copy
import logging

from dateutil.relativedelta import relativedelta
from odoo.addons.account_reports.tests.common import TestAccountReportsCommon

_logger = logging.getLogger(__name__)


@tagged('post_install', '-at_install')
class TestAccountReports(TestAccountReportsCommon):

    # -------------------------------------------------------------------------
    # TESTS: General Ledger
    # -------------------------------------------------------------------------

    def test_general_ledger_folded_unfolded(self):
        ''' Test folded/unfolded lines. '''
        # Init options.
        report = self.env['account.general.ledger']
        options = self._init_options(report, *date_utils.get_month(self.mar_year_minus_1))

        lines = report._get_lines(options)
        self.assertLinesValues(
            lines,
            #   Name                                    Debit           Credit          Balance
            [   0,                                      5,              6,              7],
            [
                # Accounts.
                ('101401 Bank',                         800.00,         1750.00,        -950.00),
                ('121000 Account Receivable',           2875.00,        800.00,         2075.00),
                ('131000 Tax Paid',                     705.00,         0.00,           705.00),
                ('211000 Account Payable',              1750.00,        5405.00,        -3655.00),
                ('251000 Tax Received',                 0.00,           375.00,         -375.00),
                ('400000 Product Sales',                0.00,           1300.00,        -1300.00),
                ('600000 Expenses',                     1100.00,        0.00,           1100.00),
                ('999999 Undistributed Profits/Losses', 3600.00,        1200.00,        2400.00),
                # Report Total.
                ('Total',                               10830.00,       10830.00,       0.00),
            ],
        )

        # Mark the '121000 Account Receivable' line to be unfolded.
        line_id = lines[1]['id']
        options['unfolded_lines'] = [line_id]

        self.assertLinesValues(
            report._get_lines(options, line_id=line_id),
            #   Name                                    Date            Partner         Currency    Debit           Credit          Balance
            [   0,                                      1,              3,              4,          5,              6,              7],
            [
                # Account.
                ('121000 Account Receivable',           '',             '',             '',         2875.00,        800.00,         2075.00),
                # Initial Balance.
                ('Initial Balance',                     '',             '',             '',         2185.00,        700.00,         1485.00),
                # Account Move Lines.
                ('BNK1/2017/0004',                      '03/01/2017',   'partner_c',    '',         '',             100.00,         1385.00),
                ('INV/2017/0006',                       '03/01/2017',   'partner_c',    '',         345.00,         '',             1730.00),
                ('INV/2017/0007',                       '03/01/2017',   'partner_d',    '',         345.00,         '',             2075.00),
                # Account Total.
                ('Total',                               '',             '',             '',         2875.00,        800.00,         2075.00),
            ],
        )

        # Mark the '400000 Product Sales' line to be unfolded.
        # Note: this account has user_type_id.include_initial_balance = False.
        line_id = lines[5]['id']
        options['unfolded_lines'] = [line_id]

        self.assertLinesValues(
            report._get_lines(options, line_id=line_id),
            #   Name                                    Date            Partner         Currency    Debit           Credit          Balance
            [   0,                                      1,              3,              4,          5,              6,              7],
            [
                # Account.
                ('400000 Product Sales',                '',             '',             '',         0.00,           1300.00,        -1300.00),
                # Initial Balance.
                ('Initial Balance',                     '',             '',             '',         0.00,           700.00,         -700.00),
                # Account Move Lines.
                ('INV/2017/0006',                       '03/01/2017',   'partner_c',    '',         '',             300.00,         -1000.00),
                ('INV/2017/0007',                       '03/01/2017',   'partner_d',    '',         '',             300.00,         -1300.00),
                # Account Total.
                ('Total',                               '',             '',             '',         0.00,           1300.00,        -1300.00),
            ],
        )

    def test_general_ledger_multi_company(self):
        ''' Test folded/unfolded lines in a multi-company environment. '''
        # Select both company_parent/company_child_eur companies.
        company_ids = (self.company_parent + self.company_child_eur).ids
        report = self.env['account.general.ledger'].with_context(allowed_company_ids=company_ids)
        options = self._init_options(report, *date_utils.get_month(self.mar_year_minus_1))

        lines = report._get_lines(options)
        self.assertLinesValues(
            lines,
            #   Name                                    Debit           Credit          Balance
            [   0,                                      5,              6,              7],
            [
                # Accounts.
                ('101401 Bank',                         800.00,         1750.00,        -950.00),
                ('101401 Bank',                         800.00,         1750.00,        -950.00),
                ('121000 Account Receivable',           2875.00,        800.00,         2075.00),
                ('121000 Account Receivable',           2875.00,        800.00,         2075.00),
                ('131000 Tax Paid',                     705.00,         0.00,           705.00),
                ('131000 Tax Paid',                     705.00,         0.00,           705.00),
                ('211000 Account Payable',              1750.00,        5405.00,        -3655.00),
                ('211000 Account Payable',              1750.00,        5405.00,        -3655.00),
                ('251000 Tax Received',                 0.00,           375.00,         -375.00),
                ('251000 Tax Received',                 0.00,           375.00,         -375.00),
                ('400000 Product Sales',                0.00,           1300.00,        -1300.00),
                ('400000 Product Sales',                0.00,           1300.00,        -1300.00),
                ('600000 Expenses',                     1100.00,        0.00,           1100.00),
                ('600000 Expenses',                     1100.00,        0.00,           1100.00),
                ('999999 Undistributed Profits/Losses', 3600.00,        1200.00,        2400.00),
                ('999999 Undistributed Profits/Losses', 3600.00,        1200.00,        2400.00),
                # Report Total.
                ('Total',                               21660.00,       21660.00,       0.00),
            ],
        )

        # Mark the '121000 Account Receivable' line (for the company_child_eur company) to be unfolded.
        line_id = lines[3]['id']
        options['unfolded_lines'] = [line_id]

        self.assertLinesValues(
            report._get_lines(options, line_id=line_id),
            #   Name                                    Date            Partner         Currency    Debit           Credit          Balance
            [   0,                                      1,              3,              4,          5,              6,              7],
            [
                # Account.
                ('121000 Account Receivable',           '',             '',             '',         2875.00,        800.00,         2075.00),
                # Initial Balance.
                ('Initial Balance',                     '',             '',             '',         2185.00,        700.00,         1485.00),
                # Account Move Lines.
                ('BNK1/2017/0004',                      '03/01/2017',   'partner_c',    '',         '',             100.00,         1385.00),
                ('INV/2017/0006',                       '03/01/2017',   'partner_c',    '',         345.00,         '',             1730.00),
                ('INV/2017/0007',                       '03/01/2017',   'partner_d',    '',         345.00,         '',             2075.00),
                # Account Total.
                ('Total',                               '',             '',             '',         2875.00,        800.00,         2075.00),
            ],
        )

    def test_general_ledger_load_more(self):
        ''' Test the load more feature. '''
        receivable_account = self.env['account.account'].search(
            [('company_id', '=', self.company_parent.id), ('internal_type', '=', 'receivable'), ('code', 'like', '1210%')], limit=1)
        line_id = 'account_%s' % receivable_account.id

        # Mark the '121000 Account Receivable' line to be unfolded.
        report = self.env['account.general.ledger']
        options = self._init_options(report, *date_utils.get_month(self.mar_year_minus_1))
        options['unfolded_lines'] = [line_id]

        # Force the load more to expand lines one by one.
        report.MAX_LINES = 1

        lines = report._get_lines(options, line_id=line_id)

        self.assertLinesValues(
            lines,
            #   Name                                    Date            Partner         Currency    Debit           Credit          Balance
            [   0,                                      1,              3,              4,          5,              6,              7],
            [
                # Account.
                ('121000 Account Receivable',           '',             '',             '',         2875.00,        800.00,         2075.00),
                # Initial Balance.
                ('Initial Balance',                     '',             '',             '',         2185.00,        700.00,         1485.00),
                # Account Move Lines.
                ('BNK1/2017/0004',                      '03/01/2017',   'partner_c',    '',         '',             100.00,         1385.00),
                # Load more.
                ('Load more... (2 remaining)',          '',             '',             '',         '',             '',             ''),
                # Account Total.
                ('Total',                               '',             '',             '',         2875.00,        800.00,         2075.00),
            ],
        )

        # Store the load more values inside the options.
        line_id = 'loadmore_%s' % receivable_account.id
        options.update({
            'lines_offset': lines[3]['offset'],
            'lines_progress': lines[3]['progress'],
            'lines_remaining': lines[3]['remaining'],
        })

        lines = report._get_lines(options, line_id=line_id)

        self.assertLinesValues(
            lines,
            #   Name                                    Date            Partner         Currency    Debit           Credit          Balance
            [   0,                                      1,              3,              4,          5,              6,              7],
            [
                # Account Move Lines.
                ('INV/2017/0006',                       '03/01/2017',   'partner_c',    '',         345.00,         '',             1730.00),
                # Load more.
                ('Load more... (1 remaining)',          '',             '',             '',         '',             '',             ''),
            ],
        )

        # Update the load more values inside the options.
        options.update({
            'lines_offset': lines[1]['offset'],
            'lines_progress': lines[1]['progress'],
            'lines_remaining': lines[1]['remaining'],
        })

        self.assertLinesValues(
            report._get_lines(options, line_id=line_id),
            #   Name                                    Date            Partner         Currency    Debit           Credit          Balance
            [   0,                                      1,              3,              4,          5,              6,              7],
            [
                # Account Move Lines.
                ('INV/2017/0007',                       '03/01/2017',   'partner_d',    '',         345.00,         '',             2075.00),
            ],
        )

    def test_general_ledger_tax_declaration(self):
        ''' Test the tax declaration. '''
        journal = self.env['account.journal'].search(
            [('company_id', '=', self.company_parent.id), ('type', '=', 'sale')], limit=1)

        # Select only the 'Customer Invoices' journal.
        report = self.env['account.general.ledger']
        options = self._init_options(report, *date_utils.get_month(self.mar_year_minus_1))
        options = self._update_multi_selector_filter(options, 'journals', journal.ids)

        self.assertLinesValues(
            report._get_lines(options),
            #   Name                                    Debit           Credit          Balance
            [   0,                                      5,              6,              7],
            [
                # Accounts.
                ('121000 Account Receivable',           2875.00,        0.00,           2875.00),
                ('251000 Tax Received',                 0.00,           375.00,         -375.00),
                ('400000 Product Sales',                0.00,           1300.00,        -1300.00),
                ('999999 Undistributed Profits/Losses', 0.00,           1200.00,        -1200.00),
                # Report Total.
                ('Total',                               2875.00,        2875.00,        0.00),
                # Tax Declaration.
                ('Tax Declaration',                     '',             '',             ''),
                ('Name',                                'Base Amount',  'Tax Amount',   ''),
                ('Tax 15.00% (15.0)',                   600.00,         90.0,         ''),
            ],
        )
    # -------------------------------------------------------------------------
    # TESTS: Partner Ledger
    # -------------------------------------------------------------------------

    def test_partner_ledger_folded_unfolded(self):
        ''' Test folded/unfolded lines. '''
        # Init options.
        report = self.env['account.partner.ledger']
        options = self._init_options(report, *date_utils.get_month(self.mar_year_minus_1))

        lines = report._get_lines(options)
        self.assertLinesValues(
            lines,
            #   Name                                    Init. Balance   Debit           Credit          Balance
            [   0,                                      6,              7,              8,              9],
            [
                # Partners.
                ('partner_a',                           665.00,         300.00,         345.00,         620.00),
                ('partner_b',                           65.00,          0.00,           345.00,         -280.00),
                ('partner_c',                           -1215.00,       345.00,         100.00,         -970.00),
                ('partner_d',                           -1295.00,       345.00,         0.00,           -950.00),
                # Report Total.
                ('Total',                               -1780.00,       990.00,         790.00,         -1580.00),
            ],
        )

        # Mark the 'partner_a' line to be unfolded.
        line_id = lines[0]['id']
        options['unfolded_lines'] = [line_id]

        self.assertLinesValues(
            report._get_lines(options, line_id=line_id),
            #   Name                    JRNL        Account         Due Date,       Init. Balance   Debit           Credit          Balance
            [   0,                      1,          2,              4,              6,              7,              8,              9],
            [
                # Partner.
                ('partner_a',           '',         '',             '',             665.00,         300.00,         345.00,         620.00),
                # Account Move Lines.
                ('03/01/2017',          'BILL',     '211000',       '03/01/2017',   665.00,         '',             345.00,         320.00),
                ('03/01/2017',          'BNK1',     '211000',       '03/01/2017',   320.00,         300.00,         '',             620.00),
            ],
        )

    def test_partner_ledger_multi_company(self):
        ''' Test folded/unfolded lines in a multi-company environment. '''
        # Select both company_parent/company_child_eur companies.
        company_ids = (self.company_parent + self.company_child_eur).ids
        report = self.env['account.partner.ledger'].with_context(allowed_company_ids=company_ids)
        options = self._init_options(report, *date_utils.get_month(self.mar_year_minus_1))

        lines = report._get_lines(options)
        self.assertLinesValues(
            lines,
            #   Name                                    Init. Balance   Debit           Credit          Balance
            [   0,                                      6,              7,              8,              9],
            [
                # Partners.
                ('partner_a',                           1330.00,        600.00,         690.00,         1240.00),
                ('partner_b',                           130.00,         0.00,           690.00,         -560.00),
                ('partner_c',                           -2430.00,       690.00,         200.00,         -1940.00),
                ('partner_d',                           -2590.00,       690.00,         0.00,           -1900.00),
                # Report Total.
                ('Total',                               -3560.00,       1980.00,        1580.00,        -3160.00),
            ],
        )

        # Mark the 'partner_a' line (for the company_child_eur company) to be unfolded.
        line_id = lines[0]['id']
        options['unfolded_lines'] = [line_id]

        self.assertLinesValues(
            report._get_lines(options, line_id=line_id),
            #   Name                    JRNL        Account         Due Date,       Init. Balance   Debit           Credit          Balance
            [   0,                      1,          2,              4,              6,              7,              8,              9],
            [
                # Partner.
                ('partner_a',           '',         '',             '',             1330.00,        600.00,         690.00,         1240.00),
                # Account Move Lines.
                ('03/01/2017',          'BILL',     '211000',       '03/01/2017',   1330.00,        '',             345.00,         985.00),
                ('03/01/2017',          'BNK1',     '211000',       '03/01/2017',   985.00,         300.00,         '',             1285.00),
                ('03/01/2017',          'BILL',     '211000',       '03/01/2017',   1285.00,        '',             345.00,         940.00),
                ('03/01/2017',          'BNK1',     '211000',       '03/01/2017',   940.00,         300.00,         '',             1240.00),
            ],
        )

    def test_partner_ledger_load_more(self):
        ''' Test the load more feature. '''
        line_id = 'partner_%s' % self.partner_a.id

        # Mark the 'partner_a' line to be unfolded.
        company_ids = (self.company_parent + self.company_child_eur).ids
        report = self.env['account.partner.ledger'].with_context(allowed_company_ids=company_ids)
        options = self._init_options(report, *date_utils.get_month(self.mar_year_minus_1))
        options['unfolded_lines'] = [line_id]

        # Force the load more to expand lines one by one.
        report.MAX_LINES = 1
        lines = report._get_lines(options, line_id=line_id)

        self.assertLinesValues(
            lines,
            #   Name                    JRNL        Account         Due Date,       Init. Balance   Debit           Credit          Balance
            [   0,                      1,          2,              4,              6,              7,              8,              9],
            [
                # Partner.
                ('partner_a',           '',         '',             '',             1330.00,        600.00,         690.00,         1240.00),
                # Account Move Lines.
                ('03/01/2017',          'BILL',     '211000',       '03/01/2017',   1330.00,        '',             345.00,         985.00),
                ('Load more... (3 remaining)', '',  '',             '',             '',             '',             '',             ''),
            ],
        )

        # Store the load more values inside the options.
        line_id = 'loadmore_%s' % self.partner_a.id
        options.update({
            'lines_offset': lines[2]['offset'],
            'lines_progress': lines[2]['progress'],
            'lines_remaining': lines[2]['remaining'],
        })
        report.MAX_LINES = 2
        lines = report._get_lines(options, line_id=line_id)

        self.assertLinesValues(
            report._get_lines(options, line_id=line_id),
            #   Name                    JRNL        Account         Due Date,       Init. Balance   Debit           Credit          Balance
            [   0,                      1,          2,              4,              6,              7,              8,              9],
            [
                # Account Move Lines.
                ('03/01/2017',          'BNK1',     '211000',       '03/01/2017',   985.00,         300.00,         '',             1285.00),
                ('03/01/2017',          'BILL',     '211000',       '03/01/2017',   1285.00,        '',             345.00,         940.00),
                # Load more.
                ('Load more... (1 remaining)', '',  '',             '',             '',             '',             '',             ''),
            ],
        )

        # Update the load more values inside the options.
        options.update({
            'lines_offset': lines[2]['offset'],
            'lines_progress': lines[2]['progress'],
            'lines_remaining': lines[2]['remaining'],
        })

        self.assertLinesValues(
            report._get_lines(options, line_id=line_id),
            #   Name                    JRNL        Account         Due Date,       Init. Balance   Debit           Credit          Balance
            [   0,                      1,          2,              4,              6,              7,              8,              9],
            [
                # Account Move Lines.
                ('03/01/2017',          'BNK1',     '211000',       '03/01/2017',   940.00,         300.00,         '',             1240.00),
            ],
        )

    def test_partner_ledger_account_types(self):
        ''' Test the 'account_type' filter. '''
        # Select only the account having the 'receivable' type.
        report = self.env['account.partner.ledger']
        options = self._init_options(report, *date_utils.get_month(self.mar_year_minus_1))
        options = self._update_multi_selector_filter(options, 'account_type', ['receivable'])

        lines = report._get_lines(options)
        self.assertLinesValues(
            lines,
            #   Name                                    Init. Balance   Debit           Credit          Balance
            [   0,                                      6,              7,              8,              9],
            [
                # Partners.
                ('partner_a',                           895.00,         0.00,           0.00,           895.00),
                ('partner_b',                           245.00,         0.00,           0.00,           245.00),
                ('partner_c',                           230.00,         345.00,         100.00,         475.00),
                ('partner_d',                           115.00,         345.00,         0.00,           460.00),
                # Report Total.
                ('Total',                               1485.00,        690.00,         100.00,         2075.00),
            ],
        )

        # Mark the 'partner_c' line to be unfolded.
        line_id = lines[2]['id']
        options['unfolded_lines'] = [line_id]

        self.assertLinesValues(
            report._get_lines(options, line_id=line_id),
            #   Name                    JRNL        Account         Due Date,       Init. Balance   Debit           Credit          Balance
            [   0,                      1,          2,              4,              6,              7,              8,              9],
            [
                # Partner.
                ('partner_c',           '',         '',             '',             230.00,         345.00,         100.00,         475.00),
                # Account Move Lines.
                ('03/01/2017',          'BNK1',     '121000',       '03/01/2017',   230.00,         '',             100.00,         130.00),
                ('03/01/2017',          'INV',      '121000',       '03/01/2017',   130.00,         345.00,         '',             475.00),
            ],
        )

        # Select only the account having the 'payable' type.
        report = self.env['account.partner.ledger']
        options = self._init_options(report, *date_utils.get_month(self.mar_year_minus_1))
        options = self._update_multi_selector_filter(options, 'account_type', ['payable'])

        lines = report._get_lines(options)
        self.assertLinesValues(
            lines,
            #   Name                                    Init. Balance   Debit           Credit          Balance
            [   0,                                      6,              7,              8,              9],
            [
                # Partners.
                ('partner_a',                           -230.00,        300.00,         345.00,         -275.00),
                ('partner_b',                           -180.00,        0.00,           345.00,         -525.00),
                ('partner_c',                           -1445.00,       0.00,           0.00,           -1445.00),
                ('partner_d',                           -1410.00,       0.00,           0.00,           -1410.00),
                # Report Total.
                ('Total',                               -3265.00,       300.00,         690.00,         -3655.00),
            ],
        )

        # Mark the 'partner_c' line to be unfolded.
        line_id = lines[2]['id']
        options['unfolded_lines'] = [line_id]

        self.assertLinesValues(
            report._get_lines(options, line_id=line_id),
            #   Name                                    Init. Balance   Debit           Credit          Balance
            [   0,                                      6,              7,              8,              9],
            [
                # Partners.
                ('partner_c',                           -1445.00,       0.00,           0.00,           -1445.00),
            ],
        )

    def test_partner_ledger_filter_partner(self):
        ''' Test the filter on partners/partner's categories. '''
        # Init options with modified filter_partner:
        # - partner_ids: ('partner_b', 'partner_c', 'partner_d')
        # - partner_categories: ('partner_categ_a')
        report = self.env['account.partner.ledger']
        options = self._init_options(report, *date_utils.get_month(self.mar_year_minus_1))
        options['partner_ids'] = (self.partner_b + self.partner_c + self.partner_d).ids
        options['partner_categories'] = self.partner_category_a.ids

        self.assertLinesValues(
            report._get_lines(options),
            #   Name                                    Init. Balance   Debit           Credit          Balance
            [   0,                                      6,              7,              8,              9],
            [
                # Partners.
                ('partner_b',                           65.00,          0.00,           345.00,         -280.00),
                ('partner_d',                           -1295.00,       345.00,         0.00,           -950.00),
                # Report Total.
                ('Total',                               -1230.00,       345.00,         345.00,         -1230.00),
            ],
        )

    # -------------------------------------------------------------------------
    # TESTS: Aged Receivable
    # -------------------------------------------------------------------------

    def test_aged_receivable_folded_unfolded(self):
        ''' Test folded/unfolded lines. '''
        # Init options.
        report = self.env['account.aged.receivable']
        options = self._init_options(report, *date_utils.get_month(self.mar_year_minus_1))
        report = report.with_context(report._set_context(options))

        lines = report._get_lines(options)
        self.assertLinesValues(
            lines,
            #   Name                                    Not Due On,     1 - 30          31 - 60         61 - 90         91 - 120        Older       Total
            [   0,                                      5,              6,              7,              8,              9,              10,         11],
            [
                # Partners.
                ('partner_a',                           0.00,           0.00,           0.00,           115.00,         780.00,         0.00,       895.00),
                ('partner_b',                           0.00,           0.00,           230.00,         15.00,          0.00,           0.00,       245.00),
                ('partner_c',                           0.00,           345.00,         130.00,         0.00,           0.00,           0.00,       475.00),
                ('partner_d',                           0.00,           345.00,         0.00,           115.00,         0.00,           0.00,       460.00),
                # Report Total.
                ('Total',                               0.00,           690.00,         360.00,         245.00,         780.00,         0.00,       2075.00),
            ],
        )

        # Mark the 'partner_d' line to be unfolded.
        line_id = lines[3]['id']
        options['unfolded_lines'] = [line_id]
        report = report.with_context(report._set_context(options))

        self.assertLinesValues(
            report._get_lines(options, line_id=line_id),
            #   Name                    JRNL        Account         Not Due On,     1 - 30          31 - 60         61 - 90         91 - 120        Older       Total
            [   0,                      2,          3,              5,              6,              7,              8,              9,              10,         11],
            [
                # Partner.
                ('partner_d',           '',         '',             0.00,           345.00,         0.00,           115.00,         0.00,           0.00,       460.00),
                # Account Move Lines.
                ('INV/2017/0003',    'INV',   '121000 Account Receivable', '',      '',             '',             115.00,         '',             '',         ''),
                ('INV/2017/0007',    'INV',   '121000 Account Receivable', '',      345.00,         '',             '',             '',             '',         ''),
            ],
        )

    def test_aged_receivable_multi_company(self):
        ''' Test folded/unfolded lines in a multi-company environment. '''
        # Select both company_parent/company_child_eur companies.
        company_ids = (self.company_parent + self.company_child_eur).ids
        report = self.env['account.aged.receivable'].with_context(allowed_company_ids=company_ids)
        options = self._init_options(report, *date_utils.get_month(self.mar_year_minus_1))
        report = report.with_context(report._set_context(options))

        lines = report._get_lines(options)
        self.assertLinesValues(
            lines,
            #   Name                                    Not Due On,     1 - 30          31 - 60         61 - 90         91 - 120        Older       Total
            [   0,                                      5,              6,              7,              8,              9,              10,         11],
            [
                # Partners.
                ('partner_a',                           0.00,           0.00,           0.00,           230.00,         1560.00,        0.00,       1790.00),
                ('partner_b',                           0.00,           0.00,           460.00,         30.00,          0.00,           0.00,       490.00),
                ('partner_c',                           0.00,           690.00,         260.00,         0.00,           0.00,           0.00,       950.00),
                ('partner_d',                           0.00,           690.00,         0.00,           230.00,         0.00,           0.00,       920.00),
                # Report Total.
                ('Total',                               0.00,           1380.00,        720.00,         490.00,         1560.00,        0.00,       4150.00),
            ],
        )

        # Mark the 'partner_d' line to be unfolded.
        line_id = lines[3]['id']
        options['unfolded_lines'] = [line_id]
        report = report.with_context(report._set_context(options))

        self.assertLinesValues(
            report._get_lines(options, line_id=line_id),
            #   Name                    JRNL        Account         Not Due On,     1 - 30          31 - 60         61 - 90         91 - 120        Older       Total
            [   0,                      2,          3,              5,              6,              7,              8,              9,              10,         11],
            [
                # Partner.
                ('partner_d',           '',         '',             0.00,           690.00,         0.00,           230.00,         0.00,           0.00,       920.00),
                # Account Move Lines.
                ('INV/2017/0003',    'INV', '121000 Account Receivable', '',        '',             '',             115.00,         '',             '',         ''),
                ('INV/2017/0003',    'INV', '121000 Account Receivable', '',        '',             '',             115.00,         '',             '',         ''),
                ('INV/2017/0007',    'INV', '121000 Account Receivable', '',        345.00,         '',             '',             '',             '',         ''),
                ('INV/2017/0007',    'INV', '121000 Account Receivable', '',        345.00,         '',             '',             '',             '',         ''),
            ],
        )

    def test_aged_receivable_filter_partner(self):
        ''' Test the filter on partners/partner's categories. '''
        # Init options with modified filter_partner:
        # - partner_ids: ('partner_b', 'partner_c', 'partner_d')
        # - partner_categories: ('partner_categ_a')
        report = self.env['account.aged.receivable']
        options = self._init_options(report, *date_utils.get_month(self.mar_year_minus_1))
        options['partner_ids'] = (self.partner_b + self.partner_c + self.partner_d).ids
        options['partner_categories'] = self.partner_category_a.ids
        report = report.with_context(report._set_context(options))

        self.assertLinesValues(
            report._get_lines(options),
            #   Name                                    Not Due On,     1 - 30          31 - 60         61 - 90         91 - 120        Older       Total
            [   0,                                      5,              6,              7,              8,              9,              10,         11],
            [
                # Partners.
                ('partner_b',                           0.00,           0.00,           230.00,         15.00,          0.00,           0.00,       245.00),
                ('partner_d',                           0.00,           345.00,         0.00,           115.00,         0.00,           0.00,       460.00),
                # Report Total.
                ('Total',                               0.00,           345.00,         230.00,         130.00,         0.00,           0.00,       705.00),
            ],
        )

    # -------------------------------------------------------------------------
    # TESTS: Aged Payable
    # -------------------------------------------------------------------------

    def test_aged_payable_folded_unfolded(self):
        ''' Test folded/unfolded lines. '''
        # Init options.
        report = self.env['account.aged.payable']
        options = self._init_options(report, *date_utils.get_month(self.mar_year_minus_1))
        report = report.with_context(report._set_context(options))

        lines = report._get_lines(options)
        self.assertLinesValues(
            lines,
            #   Name                                    Not Due On,     1 - 30          31 - 60         61 - 90         91 - 120        Older       Total
            [   0,                                      5,              6,              7,              8,              9,              10,         11],
            [
                # Partners.
                ('partner_a',                           0.00,           45.00,          230.00,         0.00,           0.00,           0.00,       275.00),
                ('partner_b',                           0.00,           345.00,         0.00,           0.00,           180.00,         0.00,       525.00),
                ('partner_c',                           0.00,           0.00,           0.00,           65.00,          1380.00,        0.00,       1445.00),
                ('partner_d',                           0.00,           0.00,           30.00,          0.00,           1380.00,        0.00,       1410.00),
                # Report Total.
                ('Total',                               0.00,           390.00,         260.00,         65.00,          2940.00,        0.00,       3655.00),
            ],
        )

        # Mark the 'partner_d' line to be unfolded.
        line_id = lines[3]['id']
        options['unfolded_lines'] = [line_id]
        report = report.with_context(report._set_context(options))

        self.assertLinesValues(
            report._get_lines(options, line_id=line_id),
            #   Name                    JRNL        Account         Not Due On,     1 - 30          31 - 60         61 - 90         91 - 120        Older       Total
            [   0,                      2,          3,              5,              6,              7,              8,              9,              10,         11],
            [
                # Partner.
                ('partner_d',           '',         '',             0.00,           0.00,           30.00,          0.00,           1380.00,        0.00,       1410.00),
                # Account Move Lines.
                ('BILL/2016/0003',  'BILL', '211000 Account Payable', '',           '',             '',             '',             1380.00,        '',         ''),
                ('BILL/2017/0003',  'BILL', '211000 Account Payable', '',           '',             30.00,          '',             '',             '',         ''),
            ],
        )

    def test_aged_payable_multi_company(self):
        ''' Test folded/unfolded lines in a multi-company environment. '''
        # Select both company_parent/company_child_eur companies.
        company_ids = (self.company_parent + self.company_child_eur).ids
        report = self.env['account.aged.payable'].with_context(allowed_company_ids=company_ids)
        options = self._init_options(report, *date_utils.get_month(self.mar_year_minus_1))
        report = report.with_context(report._set_context(options))

        lines = report._get_lines(options)
        self.assertLinesValues(
            lines,
            #   Name                                    Not Due On,     1 - 30          31 - 60         61 - 90         91 - 120        Older       Total
            [   0,                                      5,              6,              7,              8,              9,              10,         11],
            [
                # Partners.
                ('partner_a',                           0.00,           90.00,          460.00,         0.00,           0.00,           0.00,       550.00),
                ('partner_b',                           0.00,           690.00,         0.00,           0.00,           360.00,         0.00,       1050.00),
                ('partner_c',                           0.00,           0.00,           0.00,           130.00,         2760.00,        0.00,       2890.00),
                ('partner_d',                           0.00,           0.00,           60.00,          0.00,           2760.00,        0.00,       2820.00),
                # Report Total.
                ('Total',                               0.00,           780.00,         520.00,         130.00,         5880.00,        0.00,       7310.00),
            ],
        )

        # Mark the 'partner_d' line to be unfolded.
        line_id = lines[3]['id']
        options['unfolded_lines'] = [line_id]
        report = report.with_context(report._set_context(options))

        self.assertLinesValues(
            report._get_lines(options, line_id=line_id),
            #   Name                    JRNL        Account         Not Due On,     1 - 30          31 - 60         61 - 90         91 - 120        Older       Total
            [   0,                      2,          3,              5,              6,              7,              8,              9,              10,         11],
            [
                # Partner.
                ('partner_d',           '',         '',             0.00,           0.00,           60.00,          0.00,           2760.00,        0.00,       2820.00),
                # Account Move Lines.
                ('BILL/2016/0003',  'BILL', '211000 Account Payable', '',             '',             '',             '',             1380.00,        '',         ''),
                ('BILL/2016/0003',  'BILL', '211000 Account Payable', '',             '',             '',             '',             1380.00,        '',         ''),
                ('BILL/2017/0003',  'BILL', '211000 Account Payable', '',             '',             30.00,          '',             '',             '',         ''),
                ('BILL/2017/0003',  'BILL', '211000 Account Payable', '',             '',             30.00,          '',             '',             '',         ''),
            ],
        )

    def test_aged_payable_filter_partner(self):
        ''' Test the filter on partners/partner's categories. '''
        # Init options with modified filter_partner:
        # - partner_ids: ('partner_b', 'partner_c', 'partner_d')
        # - partner_categories: ('partner_categ_a')
        report = self.env['account.aged.payable']
        options = self._init_options(report, *date_utils.get_month(self.mar_year_minus_1))
        options['partner_ids'] = (self.partner_b + self.partner_c + self.partner_d).ids
        options['partner_categories'] = self.partner_category_a.ids
        report = report.with_context(report._set_context(options))

        self.assertLinesValues(
            report._get_lines(options),
            #   Name                                    Not Due On,     1 - 30          31 - 60         61 - 90         91 - 120        Older       Total
            [   0,                                      5,              6,              7,              8,              9,              10,          11],
            [
                # Partners.
                ('partner_b',                           0.00,           345.00,         0.00,           0.00,           180.00,         0.00,       525.00),
                ('partner_d',                           0.00,           0.00,           30.00,          0.00,           1380.00,        0.00,       1410.00),
                # Report Total.
                ('Total',                               0.00,           345.00,         30.00,          0.00,           1560.00,        0.00,       1935.00),
            ],
        )

    def test_aged_payable_order_by_column(self):
        ''' Test the ordering by column feature. '''
        report = self.env['account.aged.payable']
        options = self._init_options(report, *date_utils.get_month(self.mar_year_minus_1))
        options['unfold_all'] = True
        report = report.with_context(report._set_context(options))
        lines = report._get_lines(options)
        line_ids = [line['id'] for line in lines]
        options['unfolded_lines'] = line_ids

        op = {**options, **{'selected_column': 1}}
        self.assertLinesValues(
            report._sort_lines(report._get_lines(op), op),  # not sortable column, should give the default
            #   Name                    JRNL         Account  Not Due On,         1 - 30         31 - 60         61 - 90        91 - 120            Older          Total
            [   0,                      2,                 3,          5,              6,              7,              8,              9,              10,            11],
            [
                ('partner_a',           '',               '',       0.00,          45.00,         230.00,           0.00,           0.00,            0.00,        275.00),
                ('BILL/2017/0002',  'BILL', '211000 Account Payable', '',             '',         230.00,             '',             '',              '',            ''),
                ('BILL/2017/0004',  'BILL', '211000 Account Payable', '',          45.00,             '',             '',             '',              '',            ''),
                ('partner_b',           '',               '',       0.00,         345.00,           0.00,           0.00,         180.00,            0.00,        525.00),
                ('BILL/2016/0001',  'BILL', '211000 Account Payable', '',             '',             '',             '',         180.00,              '',            ''),
                ('BILL/2017/0005',  'BILL', '211000 Account Payable', '',         345.00,             '',             '',             '',              '',            ''),
                ('partner_c',           '',               '',       0.00,           0.00,           0.00,          65.00,        1380.00,            0.00,       1445.00),
                ('BILL/2016/0002',  'BILL', '211000 Account Payable', '',             '',             '',             '',        1380.00,              '',            ''),
                ('BILL/2017/0001',  'BILL', '211000 Account Payable', '',             '',             '',          65.00,             '',              '',            ''),
                ('partner_d',           '',               '',       0.00,           0.00,          30.00,           0.00,        1380.00,            0.00,       1410.00),
                ('BILL/2016/0003',  'BILL', '211000 Account Payable', '',             '',             '',             '',        1380.00,              '',            ''),
                ('BILL/2017/0003',  'BILL', '211000 Account Payable', '',             '',          30.00,             '',             '',              '',            ''),
                ('Total',               '',               '',       0.00,         390.00,         260.00,          65.00,        2940.00,            0.00,       3655.00),
            ],
        )
        op = {**options, **{'selected_column': 7}}
        self.assertLinesValues(
            report._sort_lines(report._get_lines(op), op),  # column 1-30 decreasing
            #   Name                    JRNL         Account  Not Due On,         1 - 30         31 - 60         61 - 90        91 - 120            Older          Total
            [   0,                      2,                 3,          5,              6,              7,              8,              9,              10,            11],
            [
                ('partner_b',           '',               '',       0.00,         345.00,           0.00,           0.00,         180.00,            0.00,        525.00),
                ('BILL/2017/0005',  'BILL', '211000 Account Payable', '',         345.00,             '',             '',             '',              '',            ''),
                ('BILL/2016/0001',  'BILL', '211000 Account Payable', '',             '',             '',             '',         180.00,              '',            ''),
                ('partner_a',           '',               '',       0.00,          45.00,         230.00,           0.00,           0.00,            0.00,        275.00),
                ('BILL/2017/0004',  'BILL', '211000 Account Payable', '',          45.00,             '',             '',             '',              '',            ''),
                ('BILL/2017/0002',  'BILL', '211000 Account Payable', '',             '',         230.00,             '',             '',              '',            ''),
                ('partner_c',           '',               '',       0.00,           0.00,           0.00,          65.00,        1380.00,            0.00,       1445.00),
                ('BILL/2016/0002',  'BILL', '211000 Account Payable', '',             '',             '',             '',        1380.00,              '',            ''),
                ('BILL/2017/0001',  'BILL', '211000 Account Payable', '',             '',             '',          65.00,             '',              '',            ''),
                ('partner_d',           '',               '',       0.00,           0.00,          30.00,           0.00,        1380.00,            0.00,       1410.00),
                ('BILL/2016/0003',  'BILL', '211000 Account Payable', '',             '',             '',             '',        1380.00,              '',            ''),
                ('BILL/2017/0003',  'BILL', '211000 Account Payable', '',             '',          30.00,             '',             '',              '',            ''),
                ('Total',               '',               '',       0.00,         390.00,         260.00,          65.00,        2940.00,            0.00,       3655.00),
            ],
        )
        op = {**options, **{'selected_column': -12}}
        self.assertLinesValues(
            report._sort_lines(report._get_lines(op), op),  # column Total increasing
            #   Name                    JRNL         Account  Not Due On,         1 - 30         31 - 60         61 - 90        91 - 120            Older          Total
            [   0,                      2,                 3,          5,              6,              7,              8,              9,              10,            11],
            [
                ('partner_a',           '',               '',       0.00,          45.00,         230.00,           0.00,           0.00,            0.00,        275.00),
                ('BILL/2017/0002',  'BILL', '211000 Account Payable', '',             '',         230.00,             '',             '',              '',            ''),
                ('BILL/2017/0004',  'BILL', '211000 Account Payable', '',          45.00,             '',             '',             '',              '',            ''),
                ('partner_b',           '',               '',       0.00,         345.00,           0.00,           0.00,         180.00,            0.00,        525.00),
                ('BILL/2016/0001',  'BILL', '211000 Account Payable', '',             '',             '',             '',         180.00,              '',            ''),
                ('BILL/2017/0005',  'BILL', '211000 Account Payable', '',         345.00,             '',             '',             '',              '',            ''),
                ('partner_d',           '',               '',       0.00,           0.00,          30.00,           0.00,        1380.00,            0.00,       1410.00),
                ('BILL/2016/0003',  'BILL', '211000 Account Payable', '',             '',             '',             '',        1380.00,              '',            ''),
                ('BILL/2017/0003',  'BILL', '211000 Account Payable', '',             '',          30.00,             '',             '',              '',            ''),
                ('partner_c',           '',               '',       0.00,           0.00,           0.00,          65.00,        1380.00,            0.00,       1445.00),
                ('BILL/2016/0002',  'BILL', '211000 Account Payable', '',             '',             '',             '',        1380.00,              '',            ''),
                ('BILL/2017/0001',  'BILL', '211000 Account Payable', '',             '',             '',          65.00,             '',              '',            ''),
                ('Total',               '',               '',       0.00,         390.00,         260.00,          65.00,        2940.00,            0.00,       3655.00),
            ],
        )

    # -------------------------------------------------------------------------
    # TESTS: Trial Balance
    # -------------------------------------------------------------------------

    def test_trial_balance_initial_state(self):
        ''' Test lines with base state. '''
        # Init options.
        report = self.env['account.coa.report']
        options = self._init_options(report, *date_utils.get_month(self.mar_year_minus_1))

        self.assertLinesValues(
            report._get_lines(options),
            #                                           [  Initial Balance   ]          [   Month Balance    ]          [       Total        ]
            #   Name                                    Debit           Credit          Debit           Credit          Debit           Credit
            [   0,                                      1,              2,              3,              4,              5,              6],
            [
                # Accounts.
                ('101401 Bank',                         '',             750.00,         100.00,         300.00,         '',             950.00),
                ('121000 Account Receivable',           1485.00,        '',             690.00,         100.00,         2075.00,        ''),
                ('131000 Tax Paid',                     615.00,         '',             90.00,          '',             705.00,         ''),
                ('211000 Account Payable',              '',             3265.00,        300.00,         690.00,         '',             3655.00),
                ('251000 Tax Received',                 '',             285.00,         '',             90.00,          '',             375.00),
                ('400000 Product Sales',                '',             700.00,         '',             600.00,         '',             1300.00),
                ('600000 Expenses',                     500.00,         '',             600,            '',             1100.00,        ''),
                ('999999 Undistributed Profits/Losses', 2400.00,        '',             '',             '',             2400.00,        ''),
                # Report Total.
                ('Total',                               5000.00,        5000.00,        1780.00,        1780.00,        6280.00,        6280.00),
            ],
        )

    def test_trial_balance_multi_company(self):
        ''' Test in a multi-company environment. '''
        # Select both company_parent/company_child_eur companies.
        company_ids = (self.company_parent + self.company_child_eur).ids
        report = self.env['account.coa.report'].with_context(allowed_company_ids=company_ids)
        options = self._init_options(report, *date_utils.get_month(self.mar_year_minus_1))

        self.assertLinesValues(
            report._get_lines(options),
            #                                           [  Initial Balance   ]          [   Month Balance    ]          [       Total        ]
            #   Name                                    Debit           Credit          Debit           Credit          Debit           Credit
            [   0,                                      1,              2,              3,              4,              5,              6],
            [
                # Accounts.
                ('101401 Bank',                         '',             750.00,         100.00,         300.00,         '',             950.00),
                ('101401 Bank',                         '',             750.00,         100.00,         300.00,         '',             950.00),
                ('121000 Account Receivable',           1485.00,        '',             690.00,         100.00,         2075.00,        ''),
                ('121000 Account Receivable',           1485.00,        '',             690.00,         100.00,         2075.00,        ''),
                ('131000 Tax Paid',                     615.00,         '',             90.00,          '',             705.00,         ''),
                ('131000 Tax Paid',                     615.00,         '',             90.00,          '',             705.00,         ''),
                ('211000 Account Payable',              '',             3265.00,        300.00,         690.00,         '',             3655.00),
                ('211000 Account Payable',              '',             3265.00,        300.00,         690.00,         '',             3655.00),
                ('251000 Tax Received',                 '',             285.00,         '',             90.00,          '',             375.00),
                ('251000 Tax Received',                 '',             285.00,         '',             90.00,          '',             375.00),
                ('400000 Product Sales',                '',             700.00,         '',             600.00,         '',             1300.00),
                ('400000 Product Sales',                '',             700.00,         '',             600.00,         '',             1300.00),
                ('600000 Expenses',                     500.00,         '',             600.00,         '',             1100.00,        ''),
                ('600000 Expenses',                     500.00,         '',             600.00,         '',             1100.00,        ''),
                ('999999 Undistributed Profits/Losses', 2400.00,        '',             '',             '',             2400.00,        ''),
                ('999999 Undistributed Profits/Losses', 2400.00,        '',             '',             '',             2400.00,        ''),
                # Report Total.
                ('Total',                               10000.00,       10000.00,       3560.00,        3560.00,        12560.00,       12560.00),
            ],
        )

    def test_trial_balance_journals_filter(self):
        ''' Test the filter on journals. '''
        journal = self.env['account.journal'].search([('company_id', '=', self.company_parent.id), ('type', '=', 'sale')])

        # Init options with only the sale journal selected.
        report = self.env['account.coa.report']
        options = self._init_options(report, *date_utils.get_month(self.mar_year_minus_1))
        options = self._update_multi_selector_filter(options, 'journals', journal.ids)

        self.assertLinesValues(
            report._get_lines(options),
            #                                           [  Initial Balance   ]          [   Month Balance    ]          [       Total        ]
            #   Name                                    Debit           Credit          Debit           Credit          Debit           Credit
            [   0,                                      1,              2,              3,              4,              5,              6],
            [
                # Accounts.
                ('121000 Account Receivable',           2185.00,        '',             690.00,         '',             2875.00,        ''),
                ('251000 Tax Received',                 '',             285.00,         '',             90.00,          '',             375.00),
                ('400000 Product Sales',                '',             700.00,         '',             600.00,         '',             1300.00),
                ('999999 Undistributed Profits/Losses', '',             1200.00,        '',             '',             '',             1200.00),
                # Report Total.
                ('Total',                               2185.00,        2185.00,        690.00,         690.00,         2875.00,        2875.00),
            ],
        )

    def test_trial_balance_comparison_filter(self):
        ''' Test folded/unfolded lines with one comparison. '''
        # Init options.
        report = self.env['account.coa.report']
        options = self._init_options(report, *date_utils.get_month(self.mar_year_minus_1))
        options = self._update_comparison_filter(options, report, 'previous_period', 1)

        self.assertLinesValues(
            report._get_lines(options),
            #                                           [  Initial Balance   ]          [ Month Balance - 1  ]          [   Month Balance    ]          [       Total        ]
            #   Name                                    Debit           Credit          Debit           Credit          Debit           Credit          Debit           Credit
            [   0,                                      1,              2,              3,              4,              5,              6,              7,              8],
            [
                # Accounts.
                ('101401 Bank',                         '',             500.00,         '',             250.00,         100.00,         300.00,         '',             950.00),
                ('121000 Account Receivable',           1025.00,        '',             460.00,         '',             690.00,         100.00,         2075.00,        ''),
                ('131000 Tax Paid',                     555.00,         '',             60.00,         '',              90.00,          '',             705.00,         ''),
                ('211000 Account Payable',              '',             3055.00,        250.00,         460.00,         300.00,         690.00,         '',             3655.00),
                ('251000 Tax Received',                 '',             225.00,         '',             60.00,          '',             90.00,          '',             375.00),
                ('400000 Product Sales',                '',             300.00,         '',             400.00,         '',             600.00,         '',             1300.00),
                ('600000 Expenses',                     100.00,         '',             400.00,         '',             600.00,         '',             1100.00,        ''),
                ('999999 Undistributed Profits/Losses', 2400.00,        '',             '',             '',             '',             '',             2400.00,        ''),
                # Report Total.
                ('Total',                               4080.00,        4080.00,        1170.00,        1170.00,        1780.00,        1780.00,        6280.00,        6280.00),
            ],
        )

    # -------------------------------------------------------------------------
    # TESTS: Tax Report
    # -------------------------------------------------------------------------

    def test_tax_report_initial_state(self):
        ''' Test taxes lines. '''
        # Init options.
        report = self.env['account.generic.tax.report']
        options = self._init_options(report, *date_utils.get_month(self.mar_year_minus_1))
        report = report.with_context(report._set_context(options))

        self.assertLinesValues(
            report._get_lines(options),
            #   Name                                    NET             TAX
            [   0,                                      1,              2],
            [
                ('Sales',                               '',             ''),
                ('Tax 15.00% (15.0)',                   600.00,         90.00),
                ('Purchases',                           '',             ''),
                ('Tax 15.00% (15.0)',                   600.00,         90.00),
            ],
        )

    # -------------------------------------------------------------------------
    # TESTS: Balance Sheet + All generic financial report features
    # -------------------------------------------------------------------------

    def test_balance_sheet_initial_state(self):
        ''' Test folded/unfolded lines plus totals_below_sections. '''
        # Init options.
        report = self.env.ref('account_reports.account_financial_report_balancesheet0')._with_correct_filters()
        options = self._init_options(report, *date_utils.get_month(self.mar_year_minus_1))
        report = report.with_context(report._set_context(options))

        lines = report._get_lines(options)
        self.assertLinesValues(
            lines,
            #   Name                                            Balance
            [   0,                                              1],
            [
                ('ASSETS',                                      ''),
                ('Current Assets',                              ''),
                ('Bank and Cash Accounts',                      -950.00),
                ('Receivables',                                 2075.00),
                ('Current Assets',                              705.00),
                ('Prepayments',                                 0.00),
                ('Total Current Assets',                        1830.00),
                ('Plus Fixed Assets',                           0.00),
                ('Plus Non-current Assets',                     0.00),
                ('Total ASSETS',                                1830.00),

                ('LIABILITIES',                                 ''),
                ('Current Liabilities',                         ''),
                ('Current Liabilities',                         375.00),
                ('Payables',                                    3655.00),
                ('Total Current Liabilities',                   4030.00),
                ('Plus Non-current Liabilities',                0.00),
                ('Total LIABILITIES',                           4030.00),

                ('EQUITY',                                      ''),
                ('Unallocated Earnings',                        ''),
                ('Current Year Unallocated Earnings',           ''),
                ('Current Year Earnings',                       200.00),
                ('Current Year Allocated Earnings',             0.00),
                ('Total Current Year Unallocated Earnings',     200.00),
                ('Previous Years Unallocated Earnings',         -2400.00),
                ('Total Unallocated Earnings',                  -2200.00),
                ('Retained Earnings',                           0.00),
                ('Total EQUITY',                                -2200.00),

                ('LIABILITIES + EQUITY',                        1830.00),
            ],
        )

        # Mark the 'Receivables' line to be unfolded.
        line_id = lines[3]['id']
        options['unfolded_lines'] = [line_id]
        report = report.with_context(report._set_context(options))

        self.assertLinesValues(
            report._get_lines(options, line_id=line_id),
            #   Name                                            Balance
            [   0,                                              1],
            [
                ('Receivables',                                 2075.00),
                ('121000 Account Receivable',                   2075.00),
                ('Total Receivables',                           2075.00),
            ],
        )

        # Uncheck the totals_below_sections boolean on the company.
        self.company_parent.totals_below_sections = False

        self.assertLinesValues(
            report._get_lines(options, line_id=line_id),
            #   Name                                            Balance
            [   0,                                              1],
            [
                ('Receivables',                                 2075.00),
                ('121000 Account Receivable',                   2075.00),
            ],
        )

    def test_balance_sheet_multi_company(self):
        ''' Test folded/unfolded lines in a multi-company environment. '''
        # Select both company_parent/company_child_eur companies.
        company_ids = (self.company_parent + self.company_child_eur).ids
        report = self.env.ref('account_reports.account_financial_report_balancesheet0')\
            .with_context(allowed_company_ids=company_ids)._with_correct_filters()
        options = self._init_options(report, *date_utils.get_month(self.mar_year_minus_1))
        report = report.with_context(report._set_context(options))

        lines = report._get_lines(options)
        self.assertLinesValues(
            lines,
            #   Name                                            Balance
            [   0,                                              1],
            [
                ('ASSETS',                                      ''),
                ('Current Assets',                              ''),
                ('Bank and Cash Accounts',                      -1900.00),
                ('Receivables',                                 4150.00),
                ('Current Assets',                              1410.00),
                ('Prepayments',                                 0.00),
                ('Total Current Assets',                        3660.00),
                ('Plus Fixed Assets',                           0.00),
                ('Plus Non-current Assets',                     0.00),
                ('Total ASSETS',                                3660.00),

                ('LIABILITIES',                                 ''),
                ('Current Liabilities',                         ''),
                ('Current Liabilities',                         750.00),
                ('Payables',                                    7310.00),
                ('Total Current Liabilities',                   8060.00),
                ('Plus Non-current Liabilities',                0.00),
                ('Total LIABILITIES',                           8060.00),

                ('EQUITY',                                      ''),
                ('Unallocated Earnings',                        ''),
                ('Current Year Unallocated Earnings',           ''),
                ('Current Year Earnings',                       400.00),
                ('Current Year Allocated Earnings',             0.00),
                ('Total Current Year Unallocated Earnings',     400.00),
                ('Previous Years Unallocated Earnings',         -4800.00),
                ('Total Unallocated Earnings',                  -4400.00),
                ('Retained Earnings',                           0.00),
                ('Total EQUITY',                                -4400.00),

                ('LIABILITIES + EQUITY',                        3660.00),
            ],
        )

        # Mark the 'Receivables' line to be unfolded.
        line_id = lines[3]['id']
        options['unfolded_lines'] = [line_id]
        report = report.with_context(report._set_context(options))

        self.assertLinesValues(
            report._get_lines(options, line_id=line_id),
            #   Name                                            Balance
            [   0,                                              1],
            [
                ('Receivables',                                 4150.00),
                ('121000 Account Receivable',                   2075.00),
                ('121000 Account Receivable',                   2075.00),
                ('Total Receivables',                           4150.00),
            ],
        )

    def test_balance_sheet_ir_filters(self):
        ''' Test folded/unfolded lines with custom groupby/domain. '''
        # Init options with the ir.filters.
        report = self.env.ref('account_reports.account_financial_report_balancesheet0')
        report.applicable_filters_ids = [(6, 0, self.groupby_partner_filter.ids)]
        report = report._with_correct_filters()
        options = self._init_options(report, *date_utils.get_month(self.mar_year_minus_1))

        # Test the group by filter.
        options = self._update_multi_selector_filter(options, 'ir_filters', self.groupby_partner_filter.ids)
        report = report.with_context(report._set_context(options))

        lines = report._get_lines(options)
        self.assertLinesValues(
            lines,
            #   Name                                            partner_a   partner_b   partner_c   partner_d
            [   0,                                              1,          2,          3,          4],
            [
                ('ASSETS',                                      '',         '',         '',         ''),
                ('Current Assets',                              '',         '',         '',         ''),
                ('Bank and Cash Accounts',                      300.00,     -1100.00,   50.00,      -200.00),
                ('Receivables',                                 895.00,     245.00,     475.00,     460.00),
                ('Current Assets',                              75.00,      225.00,     195.00,     210.00),
                ('Prepayments',                                 0.00,       0.00,       0.00,       0.00),
                ('Total Current Assets',                        1270.00,    -630.00,    720.00,     470.00),
                ('Plus Fixed Assets',                           0.00,       0.00,       0.00,       0.00),
                ('Plus Non-current Assets',                     0.00,       0.00,       0.00,       0.00),
                ('Total ASSETS',                                1270.00,    -630.00,    720.00,     470.00),

                ('LIABILITIES',                                 '',         '',         '',         ''),
                ('Current Liabilities',                         '',         '',         '',         ''),
                ('Current Liabilities',                         195.00,     45.00,      75.00,      60.00),
                ('Payables',                                    275.00,     525.00,     1445.00,    1410.00),
                ('Total Current Liabilities',                   470.00,     570.00,     1520.00,    1470.00),
                ('Plus Non-current Liabilities',                0.00,       0.00,       0.00,       0.00),
                ('Total LIABILITIES',                           470.00,     570.00,     1520.00,    1470.00),

                ('EQUITY',                                      '',         '',         '',         ''),
                ('Unallocated Earnings',                        '',         '',         '',         ''),
                ('Current Year Unallocated Earnings',           '',         '',         '',         ''),
                ('Current Year Earnings',                       -400.00,    0.00,       400.00,     200.00),
                ('Current Year Allocated Earnings',             0.00,       0.00,       0.00,       0.00),
                ('Total Current Year Unallocated Earnings',     -400.00,    0.00,       400.00,     200.00),
                ('Previous Years Unallocated Earnings',         1200.00,    -1200.00,   -1200.00,   -1200.00),
                ('Total Unallocated Earnings',                  800.00,     -1200.00,   -800.00,    -1000.00),
                ('Retained Earnings',                           0.00,       0.00,       0.00,       0.00),
                ('Total EQUITY',                                800.00,     -1200.00,   -800.00,    -1000.00),

                ('LIABILITIES + EQUITY',                        1270.00,    -630.00,    720.00,     470.00),
            ],
        )

        # Mark the 'Receivables' line to be unfolded.
        line_id = lines[3]['id']
        options['unfolded_lines'] = [line_id]
        report = report.with_context(report._set_context(options))

        self.assertLinesValues(
            report._get_lines(options, line_id=line_id),
            #   Name                                            partner_a   partner_b   partner_c   partner_d
            [   0,                                              1,          2,          3,          4],
            [
                ('Receivables',                                 895.00,     245.00,     475.00,     460.00),
                ('121000 Account Receivable',                   895.00,     245.00,     475.00,     460.00),
                ('Total Receivables',                           895.00,     245.00,     475.00,     460.00),
            ],
        )

        # Select group by ir.filters.
        options['unfolded_lines'] = []
        options = self._update_multi_selector_filter(options, 'ir_filters', self.groupby_partner_filter.ids)
        report = report.with_context(report._set_context(options))

        lines = report._get_lines(options)
        self.assertLinesValues(
            lines,
            #   Name                                            partner_a   partner_b
            [   0,                                              1,          2],
            [
                ('ASSETS',                                      '',         ''),
                ('Current Assets',                              '',         ''),
                ('Bank and Cash Accounts',                      300.00,     -1100.00),
                ('Receivables',                                 895.00,     245.00),
                ('Current Assets',                              75.00,      225.00),
                ('Prepayments',                                 0.00,       0.00),
                ('Total Current Assets',                        1270.00,    -630.00),
                ('Plus Fixed Assets',                           0.00,       0.00),
                ('Plus Non-current Assets',                     0.00,       0.00),
                ('Total ASSETS',                                1270.00,    -630.00),

                ('LIABILITIES',                                 '',         ''),
                ('Current Liabilities',                         '',         ''),
                ('Current Liabilities',                         195.00,     45.00),
                ('Payables',                                    275.00,     525.00),
                ('Total Current Liabilities',                   470.00,     570.00),
                ('Plus Non-current Liabilities',                0.00,       0.00),
                ('Total LIABILITIES',                           470.00,     570.00),

                ('EQUITY',                                      '',         ''),
                ('Unallocated Earnings',                        '',         ''),
                ('Current Year Unallocated Earnings',           '',         ''),
                ('Current Year Earnings',                       -400.00,    0.00),
                ('Current Year Allocated Earnings',             0.00,       0.00),
                ('Total Current Year Unallocated Earnings',     -400.00,    0.00),
                ('Previous Years Unallocated Earnings',         1200.00,    -1200.00),
                ('Total Unallocated Earnings',                  800.00,     -1200.00),
                ('Retained Earnings',                           0.00,       0.00),
                ('Total EQUITY',                                800.00,     -1200.00),

                ('LIABILITIES + EQUITY',                        1270.00,    -630.00),
            ],
        )

        # Mark the 'Receivables' line to be unfolded.
        line_id = lines[3]['id']
        options['unfolded_lines'] = [line_id]
        report = report.with_context(report._set_context(options))

        self.assertLinesValues(
            report._get_lines(options, line_id=line_id),
            #   Name                                            partner_a   partner_b
            [   0,                                              1,          2],
            [
                ('Receivables',                                 895.00,     245.00),
                ('121000 Account Receivable',                   895.00,     245.00),
                ('Total Receivables',                           895.00,     245.00),
            ],
        )

    def test_balance_sheet_debit_credit(self):
        ''' Test folded/unfolded lines with debit_credit checked with/without ir.filters. '''
        # Init options with debit_credit.
        report = self.env.ref('account_reports.account_financial_report_balancesheet0')
        report.debit_credit = True
        report.applicable_filters_ids = [(6, 0, self.groupby_partner_filter.ids)]
        report = report._with_correct_filters()
        options = self._init_options(report, *date_utils.get_month(self.mar_year_minus_1))
        report = report.with_context(report._set_context(options))

        lines = report._get_lines(options)
        self.assertLinesValues(
            lines,
            #   Name                                            Debit       Credit      Balance
            [   0,                                              1,          2,          3],
            [
                ('ASSETS',                                      '',         '',         ''),
                ('Current Assets',                              '',         '',         ''),
                ('Bank and Cash Accounts',                      0.00,       0.00,       -950.00),
                ('Receivables',                                 0.00,       0.00,       2075.00),
                ('Current Assets',                              0.00,       0.00,       705.00),
                ('Prepayments',                                 0.00,       0.00,       0.00),
                ('Total Current Assets',                        0.00,       0.00,       1830.00),
                ('Plus Fixed Assets',                           0.00,       0.00,       0.00),
                ('Plus Non-current Assets',                     0.00,       0.00,       0.00),
                ('Total ASSETS',                                0.00,       0.00,       1830.00),

                ('LIABILITIES',                                 '',         '',         ''),
                ('Current Liabilities',                         '',         '',         ''),
                ('Current Liabilities',                         0.00,       0.00,       375.00),
                ('Payables',                                    0.00,       0.00,       3655.00),
                ('Total Current Liabilities',                   0.00,       0.00,       4030.00),
                ('Plus Non-current Liabilities',                0.00,       0.00,       0.00),
                ('Total LIABILITIES',                           0.00,       0.00,       4030.00),

                ('EQUITY',                                      '',         '',         ''),
                ('Unallocated Earnings',                        '',         '',         ''),
                ('Current Year Unallocated Earnings',           '',         '',         ''),
                ('Current Year Earnings',                       0.00,       0.00,       200.00),
                ('Current Year Allocated Earnings',             0.00,       0.00,       0.00),
                ('Total Current Year Unallocated Earnings',     0.00,       0.00,       200.00),
                ('Previous Years Unallocated Earnings',         0.00,       0.00,       -2400.00),
                ('Total Unallocated Earnings',                  0.00,       0.00,       -2200.00),
                ('Retained Earnings',                           0.00,       0.00,       0.00),
                ('Total EQUITY',                                0.00,       0.00,       -2200.00),

                ('LIABILITIES + EQUITY',                        0.00,       0.00,       1830.00),
            ],
        )

        # Mark the 'Receivables' line to be unfolded.
        line_id = lines[3]['id']
        options['unfolded_lines'] = [line_id]
        report = report.with_context(report._set_context(options))

        self.assertLinesValues(
            report._get_lines(options, line_id=line_id),
            #   Name                                            Debit       Credit      Balance
            [   0,                                              1,          2,          3],
            [
                ('Receivables',                                 0.00,       0.00,       2075.00),
                ('121000 Account Receivable',                   2875.00,    800.00,     2075.00),
                ('Total Receivables',                           0.00,       0.00,       2075.00),
            ],
        )

        # TODO: Make sure this commented test works after the refactoring of the financial reports.
        # Combining debit_credit with a group by is buggy in stable version but very hard to debug.

        # # Select group by ir.filters.
        # options['unfolded_lines'] = []
        # options = self._update_multi_selector_filter(options, 'ir_filters', self.groupby_partner_filter.ids)
        # report = report.with_context(report._set_context(options))
        #
        # lines = report._get_lines(options)
        # self.assertLinesValues(
        #     lines,
        #     #                                                   [       Debit       ]   [       Credit      ]   [       Balance     ]
        #     #   Name                                            partner_a   partner_b   partner_a   partner_b   partner_a   partner_b
        #     [   0,                                              1,          2,          3,          4,          5,          6],
        #     [
        #         ('ASSETS',                                      '',         '',         '',         '',         '',         ''),
        #         ('Current Assets',                              '',         '',         '',         '',         '',         ''),
        #         ('Bank and Cash Accounts',                      0.00,       0.00,       0.00,       0.00,       300.00,     -1100.00),
        #         ('Receivables',                                 0.00,       0.00,       0.00,       0.00,       895.00,     245.00),
        #         ('Current Assets',                              0.00,       0.00,       0.00,       0.00,       75.00,      225.00),
        #         ('Prepayments',                                 0.00,       0.00,       0.00,       0.00,       0.00,       0.00),
        #         ('Total Current Assets',                        0.00,       0.00,       0.00,       0.00,       1270.00,    -630.00),
        #         ('Plus Fixed Assets',                           0.00,       0.00,       0.00,       0.00,       0.00,       0.00),
        #         ('Plus Non-current Assets',                     0.00,       0.00,       0.00,       0.00,       0.00,       0.00),
        #         ('Total ASSETS',                                0.00,       0.00,       0.00,       0.00,       1270.00,    -630.00),
        #
        #         ('LIABILITIES',                                 '',         '',         '',         '',         '',         ''),
        #         ('Current Liabilities',                         '',         '',         '',         '',         '',         ''),
        #         ('Current Liabilities',                         0.00,       0.00,       0.00,       0.00,       195.00,     45.00),
        #         ('Payables',                                    0.00,       0.00,       0.00,       0.00,       275.00,     525.00),
        #         ('Total Current Liabilities',                   0.00,       0.00,       0.00,       0.00,       470.00,     570.00),
        #         ('Plus Non-current Liabilities',                0.00,       0.00,       0.00,       0.00,       0.00,       0.00),
        #         ('Total LIABILITIES',                           0.00,       0.00,       0.00,       0.00,       470.00,     570.00),
        #
        #         ('EQUITY',                                      '',         '',         '',         '',         '',         ''),
        #         ('Unallocated Earnings',                        '',         '',         '',         '',         '',         ''),
        #         ('Current Year Unallocated Earnings',           '',         '',         '',         '',         '',         ''),
        #         ('Current Year Earnings',                       0.00,       0.00,       0.00,       0.00,       -400.00,    0.00),
        #         ('Current Year Allocated Earnings',             0.00,       0.00,       0.00,       0.00,       0.00,       0.00),
        #         ('Total Current Year Unallocated Earnings',     0.00,       0.00,       0.00,       0.00,       -400.00,    0.00),
        #         ('Previous Years Unallocated Earnings',         0.00,       0.00,       0.00,       0.00,       1200.00,    -1200.00),
        #         ('Total Unallocated Earnings',                  0.00,       0.00,       0.00,       0.00,       800.00,     -1200.00),
        #         ('Retained Earnings',                           0.00,       0.00,       0.00,       0.00,       0.00,       0.00),
        #         ('Total EQUITY',                                0.00,       0.00,       0.00,       0.00,       800.00,     -1200.00),
        #
        #         ('LIABILITIES + EQUITY',                        0.00,       0.00,       0.00,       0.00,       1270.00,    -630.00),
        #     ],
        # )

    def test_balance_sheet_filter_comparison(self):
        ''' Test folded/unfolded lines with one comparison plus with/without the ir.filters. '''
        # Init options with debit_credit.
        report = self.env.ref('account_reports.account_financial_report_balancesheet0')
        report.applicable_filters_ids = [(6, 0, self.groupby_partner_filter.ids)]
        report = report._with_correct_filters()
        options = self._init_options(report, *date_utils.get_month(self.mar_year_minus_1))
        options = self._update_comparison_filter(options, report, 'previous_period', 1)
        report = report.with_context(report._set_context(options))

        lines = report._get_lines(options)
        self.assertLinesValues(
            lines,
            #   Name                                            Balance     Comparison  %
            [   0,                                              1,          2,          3],
            [
                ('ASSETS',                                      '',         '',         ''),
                ('Current Assets',                              '',         '',         ''),
                ('Bank and Cash Accounts',                      -950.00,    -750.00,    '26.7%'),
                ('Receivables',                                 2075.00,    1485.00,    '39.7%'),
                ('Current Assets',                              705.00,     615.00,     '14.6%'),
                ('Prepayments',                                 0.00,       0.00,       'n/a'),
                ('Total Current Assets',                        1830.00,    1350.00,    '35.6%'),
                ('Plus Fixed Assets',                           0.00,       0.00,       'n/a'),
                ('Plus Non-current Assets',                     0.00,       0.00,       'n/a'),
                ('Total ASSETS',                                1830.00,    1350.00,    '35.6%'),

                ('LIABILITIES',                                 '',         '',         ''),
                ('Current Liabilities',                         '',         '',         ''),
                ('Current Liabilities',                         375.00,     285.00,     '31.6%'),
                ('Payables',                                    3655.00,    3265.00,    '11.9%'),
                ('Total Current Liabilities',                   4030.00,    3550.00,    '13.5%'),
                ('Plus Non-current Liabilities',                0.00,       0.00,       'n/a'),
                ('Total LIABILITIES',                           4030.00,    3550.00,    '13.5%'),

                ('EQUITY',                                      '',         '',         ''),
                ('Unallocated Earnings',                        '',         '',         ''),
                ('Current Year Unallocated Earnings',           '',         '',         ''),
                ('Current Year Earnings',                       200.00,     200.00,     '0.0%'),
                ('Current Year Allocated Earnings',             0.00,       0.00,       'n/a'),
                ('Total Current Year Unallocated Earnings',     200.00,     200.00,     '0.0%'),
                ('Previous Years Unallocated Earnings',         -2400.00,   -2400.00,   '0.0%'),
                ('Total Unallocated Earnings',                  -2200.00,   -2200.00,   '0.0%'),
                ('Retained Earnings',                           0.00,       0.00,       'n/a'),
                ('Total EQUITY',                                -2200.00,   -2200.00,   '0.0%'),

                ('LIABILITIES + EQUITY',                        1830.00,    1350.00,    '35.6%'),
            ],
        )

        # Mark the 'Receivables' line to be unfolded.
        line_id = lines[3]['id']
        options['unfolded_lines'] = [line_id]
        report = report.with_context(report._set_context(options))

        self.assertLinesValues(
            report._get_lines(options, line_id=line_id),
            #   Name                                            Balance     Previous Period
            [   0,                                              1,          2],
            [
                ('Receivables',                                 2075.00,    1485.00),
                ('121000 Account Receivable',                   2075.00,    1485.00),
                ('Total Receivables',                           2075.00,    1485.00),
            ],
        )

        # Select both ir.filters.
        options['unfolded_lines'] = []
        options = self._update_multi_selector_filter(options, 'ir_filters', self.groupby_partner_filter.ids)
        report = report.with_context(report._set_context(options))

        lines = report._get_lines(options)
        self.assertLinesValues(
            lines,
            #                                                   [                   Balance                 ]   [                  Comparison               ]
            #   Name                                            partner_a   partner_b   partner_c   partner_d   partner_a   partner_b   partner_c   partner_d
            [   0,                                              1,          2,          3,          4,          5,          6,          7,          8],
            [
                ('ASSETS',                                      '',         '',         '',         '',         '',         '',         '',         ''),
                ('Current Assets',                              '',         '',         '',         '',         '',         '',         '',         ''),
                ('Bank and Cash Accounts',                      300.00,     -1100.00,   50.00,      -200.00,    600.00,     -1100.00,   -50.00,     -200.00),
                ('Receivables',                                 895.00,     245.00,     475.00,     460.00,     895.00,     245.00,     230.00,     115.00),
                ('Current Assets',                              75.00,      225.00,     195.00,     210.00,     30.00,      180.00,     195.00,     210.00),
                ('Prepayments',                                 0.00,       0.00,       0.00,       0.00,       0.00,       0.00,       0.00,       0.00),
                ('Total Current Assets',                        1270.00,    -630.00,    720.00,     470.00,     1525.00,    -675.00,    375.00,     125.00),
                ('Plus Fixed Assets',                           0.00,       0.00,       0.00,       0.00,       0.00,       0.00,       0.00,       0.00),
                ('Plus Non-current Assets',                     0.00,       0.00,       0.00,       0.00,       0.00,       0.00,       0.00,       0.00),
                ('Total ASSETS',                                1270.00,    -630.00,    720.00,     470.00,     1525.00,    -675.00,    375.00,     125.00),

                ('LIABILITIES',                                 '',         '',         '',         '',         '',         '',         '',         ''),
                ('Current Liabilities',                         '',         '',         '',         '',         '',         '',         '',         ''),
                ('Current Liabilities',                         195.00,     45.00,      75.00,      60.00,      195.00,     45.00,      30.00,      15.00),
                ('Payables',                                    275.00,     525.00,     1445.00,    1410.00,    230.00,     180.00,     1445.00,    1410.00),
                ('Total Current Liabilities',                   470.00,     570.00,     1520.00,    1470.00,    425.00,     225.00,     1475.00,    1425.00),
                ('Plus Non-current Liabilities',                0.00,       0.00,       0.00,       0.00,       0.00,       0.00,       0.00,       0.00),
                ('Total LIABILITIES',                           470.00,     570.00,     1520.00,    1470.00,    425.00,     225.00,     1475.00,    1425.00),

                ('EQUITY',                                      '',         '',         '',         '',         '',         '',         '',         ''),
                ('Unallocated Earnings',                        '',         '',         '',         '',         '',         '',         '',         ''),
                ('Current Year Unallocated Earnings',           '',         '',         '',         '',         '',         '',         '',         ''),
                ('Current Year Earnings',                       -400.00,    0.00,       400.00,     200.00,     -100.00,    300.00,     100.00,     -100.00),
                ('Current Year Allocated Earnings',             0.00,       0.00,       0.00,       0.00,       0.00,       0.00,       0.00,       0.00),
                ('Total Current Year Unallocated Earnings',     -400.00,    0.00,       400.00,     200.00,     -100.00,    300.00,     100.00,     -100.00),
                ('Previous Years Unallocated Earnings',         1200.00,    -1200.00,   -1200.00,   -1200.00,   1200.00,    -1200.00,   -1200.00,   -1200.00),
                ('Total Unallocated Earnings',                  800.00,     -1200.00,   -800.00,    -1000.00,   1100.00,    -900.00,    -1100.00,   -1300.00),
                ('Retained Earnings',                           0.00,       0.00,       0.00,       0.00,       0.00,       0.00,       0.00,       0.00),
                ('Total EQUITY',                                800.00,     -1200.00,   -800.00,    -1000.00,   1100.00,    -900.00,    -1100.00,   -1300.00),

                ('LIABILITIES + EQUITY',                        1270.00,    -630.00,    720.00,     470.00,     1525.00,    -675.00,    375.00,     125.00),
            ]
        )


        # Mark the 'Receivables' line to be unfolded.
        line_id = lines[3]['id']
        options['unfolded_lines'] = [line_id]
        report = report.with_context(report._set_context(options))

        self.assertLinesValues(
            report._get_lines(options, line_id=line_id),
            #                                                   [                   Balance                 ]   [                  Comparison               ]
            #   Name                                            partner_a   partner_b   partner_c   partner_d   partner_a   partner_b   partner_c   partner_d
            [   0,                                              1,          2,          3,          4,          5,          6,          7,          8],
            [
                ('Receivables',                                 895.00,     245.00,     475.00,     460.00,     895.00,     245.00,     230.00,     115.00),
                ('121000 Account Receivable',                   895.00,     245.00,     475.00,     460.00,     895.00,     245.00,     230.00,     115.00),
                ('Total Receivables',                           895.00,     245.00,     475.00,     460.00,     895.00,     245.00,     230.00,     115.00),
            ],
        )

    # -------------------------------------------------------------------------
    # TESTS: Profit And Loss
    # -------------------------------------------------------------------------

    def test_profit_and_loss_initial_state(self):
        ''' Test folded/unfolded lines. '''
        # Init options.
        report = self.env.ref('account_reports.account_financial_report_profitandloss0')._with_correct_filters()
        options = self._init_options(report, *date_utils.get_month(self.mar_year_minus_1))
        report = report.with_context(report._set_context(options))

        lines = report._get_lines(options)
        self.assertLinesValues(
            lines,
            #   Name                                            Balance
            [   0,                                              1],
            [
                ('Income',                                      ''),
                ('Gross Profit',                                ''),
                ('Operating Income',                            600.00),
                ('Cost of Revenue',                             0.00),
                ('Total Gross Profit',                          600.00),
                ('Other Income',                                0.00),
                ('Total Income',                                600.00),
                 ('Expenses',                                    ''),
                ('Expenses',                                    600.00),
                ('Depreciation',                                0.00),
                ('Total Expenses',                              600.00),
                 ('Net Profit',                                 0.00),
            ],
        )

        # Mark the 'Operating Income' line to be unfolded.
        line_id = lines[2]['id']
        options['unfolded_lines'] = [line_id]
        report = report.with_context(report._set_context(options))

        self.assertLinesValues(
            report._get_lines(options, line_id=line_id),
            #   Name                                            Balance
            [   0,                                              1],
            [
                ('Operating Income',                            600.00),
                ('400000 Product Sales',                        600.00),
                ('Total Operating Income',                      600.00),
            ],
        )

    def test_profit_and_loss_filter_journals(self):
        ''' Test folded lines with a filter on journals. '''
        journal = self.env['account.journal'].search([('company_id', '=', self.company_parent.id), ('type', '=', 'sale')])

        # Init options with only the sale journal selected.
        report = self.env.ref('account_reports.account_financial_report_profitandloss0')._with_correct_filters()
        options = self._init_options(report, *date_utils.get_month(self.mar_year_minus_1))
        options = self._update_multi_selector_filter(options, 'journals', journal.ids)
        report = report.with_context(report._set_context(options))

        self.assertLinesValues(
            report._get_lines(options),
            #   Name                                            Balance
            [   0,                                              1],
            [
                ('Income',                                      ''),
                ('Gross Profit',                                ''),
                ('Operating Income',                            600.00),
                ('Cost of Revenue',                             0.00),
                ('Total Gross Profit',                          600.00),
                ('Other Income',                                0.00),
                ('Total Income',                                600.00),
                 ('Expenses',                                    ''),
                ('Expenses',                                    0.00),
                ('Depreciation',                                0.00),
                ('Total Expenses',                              0.00),
                 ('Net Profit',                                 600.00),
            ],
        )

    # -------------------------------------------------------------------------
    # TESTS: Cash Flow Statement
    # -------------------------------------------------------------------------

    def test_cash_flow_statement_1(self):
        liquidity_journal_1 = self.env['account.journal'].search([
            ('type', 'in', ('bank', 'cash')), ('company_id', '=', self.company_parent.id),
        ], limit=1)
        liquidity_account = liquidity_journal_1.default_credit_account_id
        receivable_account_1 = self.env['account.account'].search([
            ('user_type_id.type', '=', 'receivable'), ('company_id', '=', self.company_parent.id), ('code', 'like', '1210%')
        ], limit=1)
        receivable_account_2 = receivable_account_1.copy()
        receivable_account_2.name = 'Account Receivable 2'
        receivable_account_3 = receivable_account_1.copy()
        receivable_account_3.name = 'Account Receivable 3'
        other_account_1 = receivable_account_1.copy(default={'user_type_id': self.env.ref('account.data_account_type_current_assets').id, 'reconcile': True})
        other_account_1.name = 'Other account 1'
        other_account_2 = receivable_account_1.copy(default={'user_type_id': self.env.ref('account.data_account_type_current_assets').id, 'reconcile': True})
        other_account_2.name = 'Other account 2'
        other_account_2.tag_ids |= self.env.ref('account.account_tag_financing')

        def assertCashFlowValues(lines, expected_lines):
            folded_lines = []
            for line in lines:
                self.assertNotEquals(line['id'], 'cash_flow_line_unexplained_difference', 'Test failed due to an unexplained difference in the report.')
                if line.get('style') != 'display: none;':
                    folded_lines.append(line)
            self.assertLinesValues(folded_lines, [0, 1], expected_lines)

        expected_lines = [
            ['Cash and cash equivalents, beginning of period',                      0.0],
            ['Net increase in cash and cash equivalents',                           0.0],
            ['Cash flows from operating activities',                                0.0],
            ['Advance Payments received from customers',                            0.0],
            ['Cash received from operating activities',                             0.0],
            ['Advance payments made to suppliers',                                  0.0],
            ['Cash paid for operating activities',                                  0.0],
            ['Cash flows from investing & extraordinary activities',                0.0],
            ['Cash in',                                                             0.0],
            ['Cash out',                                                            0.0],
            ['Cash flows from financing activities',                                0.0],
            ['Cash in',                                                             0.0],
            ['Cash out',                                                            0.0],
            ['Cash flows from unclassified activities',                             0.0],
            ['Cash in',                                                             0.0],
            ['Cash out',                                                            0.0],
            ['Cash and cash equivalents, closing balance',                          0.0],
        ]

        # Init report / options.
        report = self.env['account.cash.flow.report'].with_context(allowed_company_ids=self.company_parent.ids)
        options = self._init_options(report, *date_utils.get_month(fields.Date.from_string('2015-01-01')))

        # ===================================================================================================
        # CASE 1:
        #
        # Invoice:
        # Id  | Account         | Debit     | Credit  | Date
        # ---------------------------------------------------
        # 1   | Receivable      | 345       |         | 2015-01-01
        # 2   | Receivable      | 805       |         | 2015-01-01
        # 3   | Tax Received    |           | 150     | 2015-01-01
        # 4   | Product Sales   |           | 1000    | 2015-01-01
        #
        # Payment 1:
        # Id  | Account         | Debit     | Credit  | Date
        # ---------------------------------------------------
        # 4   | Receivable      |           | 230     | 2015-01-15
        # 5   | Bank            | 230       |         | 2015-01-15
        #
        # Payment 2:
        # Id  | Account         | Debit     | Credit  | Date
        # ---------------------------------------------------
        # 6   | Receivable      |           | 230     | 2015-02-01
        # 7   | Bank            | 230       |         | 2015-02-01
        #
        # Payment 3:
        # Id  | Account         | Debit     | Credit  | Date
        # ---------------------------------------------------
        # 8   | Receivable      |           | 1690    | 2015-02-15
        # 9   | Bank            | 1690      |         | 2015-02-15
        #
        # Reconciliation table (account.partial.reconcile):
        # Debit id    | Credit id     | Amount
        # ---------------------------------------------------
        # 1           | 4             | 230
        # 1           | 6             | 115
        # 2           | 6             | 115
        # 2           | 8             | 690
        #
        # Summary:
        # The invoice is paid at 60% (690 / 1150).
        # All payments are fully reconciled except the third that has 1000 credit left on the receivable account.
        # ===================================================================================================

        # Init invoice.
        # self.partner_a.property_payment_term_id = self.env.ref('account.account_payment_term_advance')
        invoice = self._create_invoice(self.env, 1000, self.partner_a, 'out_invoice', '2015-01-01')

        # First payment.
        # The tricky part is there is two receivable lines on the invoice.
        self._create_payment(self.env, fields.Date.from_string('2015-01-15'), invoice, amount=230)

        options['date']['date_to'] = '2015-01-15'
        expected_lines[1][1] += 230.0               # Net increase in cash and cash equivalents         230.0
        expected_lines[2][1] += 200.0               # Cash flows from operating activities              200.0
        expected_lines[4][1] += 200.0               # Cash received from operating activities           200.0
        expected_lines[13][1] += 30.0               # Cash flows from unclassified activities           30.0
        expected_lines[14][1] += 30.0               # Cash in                                           30.0
        expected_lines[16][1] += 230.0              # Cash and cash equivalents, closing balance        230.0
        assertCashFlowValues(report._get_lines(options), expected_lines)

        # Second payment.
        # The tricky part is two partials will be generated, one for each receivable line.
        self._create_payment(self.env, fields.Date.from_string('2015-02-01'), invoice, amount=230)

        options['date']['date_to'] = '2015-02-01'
        expected_lines[1][1] += 230.0               # Net increase in cash and cash equivalents         460.0
        expected_lines[2][1] += 200.0               # Cash flows from operating activities              400.0
        expected_lines[4][1] += 200.0               # Cash received from operating activities           400.0
        expected_lines[13][1] += 30.0               # Cash flows from unclassified activities           60.0
        expected_lines[14][1] += 30.0               # Cash in                                           60.0
        expected_lines[16][1] += 230.0              # Cash and cash equivalents, closing balance        460.0
        assertCashFlowValues(report._get_lines(options), expected_lines)

        # Third payment.
        # The tricky part is this payment will generate an advance in payments.
        third_payment = self._create_payment(self.env, fields.Date.from_string('2015-02-15'), invoice, amount=1690)

        options['date']['date_to'] = '2015-02-15'
        expected_lines[1][1] += 1690.0              # Net increase in cash and cash equivalents         2150.0
        expected_lines[2][1] += 1600.0              # Cash flows from operating activities              2000.0
        expected_lines[3][1] += 1000.0              # Advance Payments received from customers          1000.0
        expected_lines[4][1] += 600.0               # Cash received from operating activities           1000.0
        expected_lines[13][1] += 90.0               # Cash flows from unclassified activities           150.0
        expected_lines[14][1] += 90.0               # Cash in                                           150.0
        expected_lines[16][1] += 1690.0             # Cash and cash equivalents, closing balance        2150.0
        assertCashFlowValues(report._get_lines(options), expected_lines)

        # Second invoice.
        # As the report date is unchanged, this reconciliation must not affect the report.
        # It ensures the residual amounts is computed dynamically depending of the report date.
        # Then, when including the invoice to the report, the advance payments must become a cash received.
        second_invoice = self._create_invoice(self.env, 1000, self.partner_a, 'out_invoice', '2015-03-01', clear_taxes=True)

        (second_invoice.line_ids + third_payment.move_line_ids)\
            .filtered(lambda line: line.account_internal_type == 'receivable')\
            .reconcile()

        assertCashFlowValues(report._get_lines(options), expected_lines)

        options['date']['date_to'] = '2015-03-15'
        expected_lines[3][1] -= 1000.0              # Advance Payments received from customers          0.0
        expected_lines[4][1] += 1000.0              # Cash received from operating activities           2000.0
        assertCashFlowValues(report._get_lines(options), expected_lines)

        # ===================================================================================================
        # CASE 2:
        # Test the variation of the reconciled percentage from 800 / 1000 = 80% to 3800 / 4000 = 95%.
        # Also test the cross-reconciliation between liquidity moves doesn't break the report.
        #
        # Liquidity move 1:
        # Id  | Account         | Debit     | Credit  | Date
        # ---------------------------------------------------
        # 5   | Receivable 1    | 800       |         | 2015-04-01
        # 6   | Receivable 3    |           | 250     | 2015-04-01
        # 7   | other 1         |           | 250     | 2015-04-01
        # 8   | Bank            |           | 300     | 2015-04-01
        #
        # Misc. move.
        # Id  | Account         | Debit     | Credit  | Date
        # ---------------------------------------------------
        # 1   | Receivable 1    |           | 1000    | 2015-04-02
        # 2   | other 1         |           | 500     | 2015-04-02
        # 3   | other 2         | 4500      |         | 2015-04-02
        # 4   | Receivable 2    |           | 3000    | 2015-04-02
        #
        # Liquidity move 2:
        # Id  | Account         | Debit     | Credit  | Date
        # ---------------------------------------------------
        # 9   | Receivable 2    | 3200      |         | 2015-04-03
        # 10  | Receivable 3    | 200       |         | 2015-04-03
        # 11  | other 2         |           | 400     | 2015-04-03
        # 12  | Bank            |           | 3000    | 2015-04-03
        #
        # Reconciliation table (account.partial.reconcile):
        # Debit id    | Credit id     | Amount
        # ---------------------------------------------------
        # 5           | 1             | 800
        # 9           | 4             | 115
        # 10          | 6             | 200
        # ===================================================================================================

        # First liquidity move.
        liquidity_move_1 = self.env['account.move'].create({
            'date': '2015-04-01',
            'line_ids': [
                (0, 0, {'debit': 800.0, 'credit': 0.0, 'account_id': receivable_account_1.id}),
                (0, 0, {'debit': 0.0, 'credit': 250.0, 'account_id': receivable_account_3.id}),
                (0, 0, {'debit': 0.0, 'credit': 250.0, 'account_id': other_account_1.id}),
                (0, 0, {'debit': 0.0, 'credit': 300.0, 'account_id': liquidity_account.id}),
            ],
        })
        liquidity_move_1.post()

        options['date']['date_to'] = '2015-04-01'
        expected_lines[1][1] -= 300.0               # Net increase in cash and cash equivalents         1850.0
        expected_lines[2][1] -= 550.0               # Cash flows from operating activities              1450.0
        expected_lines[3][1] -= 550.0               # Advance Payments received from customers          -550.0
        expected_lines[13][1] += 250.0              # Cash flows from unclassified activities           400.0
        expected_lines[14][1] += 250.0              # Cash in                                           400.0
        expected_lines[16][1] -= 300.0              # Cash and cash equivalents, closing balance        1850.0
        assertCashFlowValues(report._get_lines(options), expected_lines)

        # Misc. move.
        # /!\ This move is reconciled at 800 / (1000 + 3000) = 20%.
        misc_move = self.env['account.move'].create({
            'date': '2015-04-02',
            'line_ids': [
                (0, 0, {'debit': 0.0, 'credit': 1000.0, 'account_id': receivable_account_1.id}),
                (0, 0, {'debit': 0.0, 'credit': 500.0, 'account_id': other_account_1.id}),
                (0, 0, {'debit': 4500.0, 'credit': 0.0, 'account_id': other_account_2.id}),
                (0, 0, {'debit': 0.0, 'credit': 3000.0, 'account_id': receivable_account_2.id}),
            ],
        })
        misc_move.post()

        (liquidity_move_1.line_ids + misc_move.line_ids)\
            .filtered(lambda line: line.account_id == receivable_account_1)\
            .reconcile()

        options['date']['date_to'] = '2015-04-02'
        expected_lines[2][1] += 3200.0              # Cash flows from operating activities              4650.0
        expected_lines[3][1] += 3200.0              # Advance Payments received from customers          2650.0
        expected_lines[10][1] -= 3600.0             # Cash flows from financing activities              -3600.0
        expected_lines[12][1] -= 3600.0             # Cash out                                          -3600.0
        expected_lines[13][1] += 400.0              # Cash flows from unclassified activities           800.0
        expected_lines[14][1] += 400.0              # Cash in                                           800.0
        assertCashFlowValues(report._get_lines(options), expected_lines)

        # Second liquidity move.
        liquidity_move_2 = self.env['account.move'].create({
            'date': '2015-04-03',
            'line_ids': [
                (0, 0, {'debit': 3200.0, 'credit': 0.0, 'account_id': receivable_account_2.id}),
                (0, 0, {'debit': 200.0, 'credit': 0.0, 'account_id': receivable_account_3.id}),
                (0, 0, {'debit': 0.0, 'credit': 400.0, 'account_id': other_account_2.id}),
                (0, 0, {'debit': 0.0, 'credit': 3000.0, 'account_id': liquidity_account.id}),
            ],
        })
        liquidity_move_2.post()

        # misc_move is now paid at 95%.
        (liquidity_move_2.line_ids + misc_move.line_ids)\
            .filtered(lambda line: line.account_id == receivable_account_2)\
            .reconcile()

        options['date']['date_to'] = '2015-04-03'
        expected_lines[1][1] -= 3000.0              # Net increase in cash and cash equivalents         -1150.0
        expected_lines[2][1] -= 2800.0              # Cash flows from operating activities              1850.0
        expected_lines[3][1] -= 2800.0              # Advance Payments received from customers          -150.0
        expected_lines[10][1] -= 275.0              # Cash flows from financing activities              -3875.0
        expected_lines[11][1] += 400.0              # Cash in                                           400.0
        expected_lines[12][1] -= 675.0              # Cash out                                          -4275.0
        expected_lines[13][1] += 75.0               # Cash flows from unclassified activities           875.0
        expected_lines[14][1] += 75.0               # Cash in                                           875.0
        expected_lines[16][1] -= 3000.0             # Cash and cash equivalents, closing balance        -1150.0
        assertCashFlowValues(report._get_lines(options), expected_lines)

        # Nothing should change in the cash flow report.
        (liquidity_move_1.line_ids + liquidity_move_2.line_ids)\
            .filtered(lambda line: line.account_id == receivable_account_3)\
            .reconcile()

        assertCashFlowValues(report._get_lines(options), expected_lines)

        # ===================================================================================================
        # TEST THE UNFOLDED REPORT
        # ===================================================================================================

        self.assertLinesValues(report._get_lines(options), [0, 1], [
            ['Cash and cash equivalents, beginning of period',                      0.0],
            ['Net increase in cash and cash equivalents',                           -1150.0],
            ['Cash flows from operating activities',                                1850.0],
            ['Advance Payments received from customers',                            -150.0],
            ['121010 Account Receivable 2',                                         -200.0],
            ['121020 Account Receivable 3',                                         50.0],
            ['Total Advance Payments received from customers',                      -150.0],
            ['Cash received from operating activities',                             2000.0],
            ['400000 Product Sales',                                                2000.0],
            ['Total Cash received from operating activities',                       2000.0],
            ['Advance payments made to suppliers',                                  0.0],
            ['Cash paid for operating activities',                                  0.0],
            ['Cash flows from investing & extraordinary activities',                0.0],
            ['Cash in',                                                             0.0],
            ['Cash out',                                                            0.0],
            ['Cash flows from financing activities',                                -3875.0],
            ['Cash in',                                                             400.0],
            ['121040 Other account 2',                                              400.0],
            ['Total Cash in',                                                       400.0],
            ['Cash out',                                                            -4275.0],
            ['121040 Other account 2',                                              -4275.0],
            ['Total Cash out',                                                      -4275.0],
            ['Cash flows from unclassified activities',                             875.0],
            ['Cash in',                                                             875.0],
            ['251000 Tax Received',                                                 150.0],
            ['121030 Other account 1',                                              725.0],
            ['Total Cash in',                                                       875.0],
            ['Cash out',                                                            0.0],
            ['Cash and cash equivalents, closing balance',                          -1150.0],
            ['101401 Bank',                                                         -1150.0],
            ['Total Cash and cash equivalents, closing balance',                    -1150.0],
        ])

        # ===================================================================================================
        # CASE 3:
        #
        # Misc move 1:
        # Id  | Account         | Debit     | Credit  | Date
        # ---------------------------------------------------
        # 1   | other 1         |           | 500     | 2015-05-01
        # 2   | other 2         | 500       |         | 2015-05-01
        #
        # Liquidity move 1:
        # Id  | Account         | Debit     | Credit  | Date
        # ---------------------------------------------------
        # 3   | Bank            | 1000      |         | 2015-05-01
        # 4   | other 2         |           | 500     | 2015-05-01
        # 5   | other 2         |           | 500     | 2015-05-01
        #
        # Liquidity move 2:
        # Id  | Account         | Debit     | Credit  | Date
        # ---------------------------------------------------
        # 6   | Bank            |           | 500     | 2015-05-02
        # 7   | other 2         | 500       |         | 2015-05-02
        #
        # Reconciliation table (account.partial.reconcile):
        # Debit id    | Credit id     | Amount
        # ---------------------------------------------------
        # 2           | 4             | 500
        # 7           | 5             | 500
        # ===================================================================================================

        # Reset the report at 2015-05-01.
        options['date']['date_from'] = '2015-05-01'
        for line in expected_lines:
            line[1] = 0
        expected_lines[0][1] -= 1150.0              # Cash and cash equivalents, beginning of period    -1150.0
        expected_lines[16][1] -= 1150.0             # Cash and cash equivalents, closing balance        -1150.0

        # Init moves + reconciliation.
        moves = self.env['account.move'].create([
            {
                'date': '2015-05-01',
                'line_ids': [
                    (0, 0, {'debit': 0.0, 'credit': 500.0, 'account_id': other_account_1.id}),
                    (0, 0, {'debit': 500.0, 'credit': 0.0, 'account_id': other_account_2.id}),
                ],
            },
            {
                'date': '2015-05-01',
                'line_ids': [
                    (0, 0, {'debit': 1000.0, 'credit': 0.0, 'account_id': liquidity_account.id}),
                    (0, 0, {'debit': 0.0, 'credit': 500.0, 'account_id': other_account_2.id}),
                    (0, 0, {'debit': 0.0, 'credit': 500.0, 'account_id': other_account_2.id}),
                ],
            },
            {
                'date': '2015-05-02',
                'line_ids': [
                    (0, 0, {'debit': 0.0, 'credit': 500.0, 'account_id': liquidity_account.id}),
                    (0, 0, {'debit': 500.0, 'credit': 0.0, 'account_id': other_account_2.id}),
                ],
            },
        ])
        moves.post()

        moves.mapped('line_ids')\
            .filtered(lambda line: line.account_id == other_account_2)\
            .reconcile()

        options['date']['date_to'] = '2015-05-01'
        expected_lines[1][1] += 1000.0              # Net increase in cash and cash equivalents         1000.0
        expected_lines[10][1] += 500.0              # Cash flows from financing activities              500.0
        expected_lines[11][1] += 500.0              # Cash in                                           500.0
        expected_lines[13][1] += 500.0              # Cash flows from unclassified activities           500.0
        expected_lines[14][1] += 500.0              # Cash in                                           500.0
        expected_lines[16][1] += 1000.0             # Cash and cash equivalents, closing balance        -150.0
        assertCashFlowValues(report._get_lines(options), expected_lines)

        options['date']['date_to'] = '2015-05-02'
        expected_lines[1][1] -= 500.0               # Net increase in cash and cash equivalents         500.0
        expected_lines[10][1] -= 500.0              # Cash flows from financing activities              0.0
        expected_lines[11][1] -= 500.0              # Cash in                                           0.0
        expected_lines[16][1] -= 500.0              # Cash and cash equivalents, closing balance        -650.0
        assertCashFlowValues(report._get_lines(options), expected_lines)

        # ===================================================================================================
        # CASE 4:
        # The difficulty of this case is the liquidity move will pay the misc move at 1000 / 3000 = 1/3.
        # However, you must take care of the sign because the 3000 in credit must become 1000 in debit.
        #
        # Misc move 1:
        # Id  | Account         | Debit     | Credit  | Date
        # ---------------------------------------------------
        # 1   | other 1         |           | 3000    | 2015-06-01
        # 2   | other 2         | 5000      |         | 2015-06-01
        # 3   | other 2         |           | 1000    | 2015-06-01
        # 4   | other 2         |           | 1000    | 2015-06-01
        #
        # Liquidity move 1:
        # Id  | Account         | Debit     | Credit  | Date
        # ---------------------------------------------------
        # 5   | Bank            |           | 1000    | 2015-06-01
        # 6   | other 2         | 1000      |         | 2015-06-01
        #
        # Reconciliation table (account.partial.reconcile):
        # Debit id    | Credit id     | Amount
        # ---------------------------------------------------
        # 6           | 3             | 1000
        # ===================================================================================================

        # Init moves + reconciliation.
        moves = self.env['account.move'].create([
            {
                'date': '2015-06-01',
                'line_ids': [
                    (0, 0, {'debit': 0.0, 'credit': 3000.0, 'account_id': other_account_1.id}),
                    (0, 0, {'debit': 5000.0, 'credit': 0.0, 'account_id': other_account_2.id}),
                    (0, 0, {'debit': 0.0, 'credit': 1000.0, 'account_id': other_account_2.id}),
                    (0, 0, {'debit': 0.0, 'credit': 1000.0, 'account_id': other_account_2.id}),
                ],
            },
            {
                'date': '2015-06-01',
                'line_ids': [
                    (0, 0, {'debit': 0.0, 'credit': 1000.0, 'account_id': liquidity_account.id}),
                    (0, 0, {'debit': 1000.0, 'credit': 0.0, 'account_id': other_account_2.id}),
                ],
            },
        ])
        moves.post()

        moves.mapped('line_ids')\
            .filtered(lambda line: line.account_id == other_account_2 and abs(line.balance) == 1000.0)\
            .reconcile()

        options['date']['date_to'] = '2015-06-01'
        expected_lines[1][1] -= 1000.0              # Net increase in cash and cash equivalents         -500.0
        expected_lines[13][1] -= 1000.0             # Cash flows from unclassified activities           -500.0
        expected_lines[14][1] -= 500.0              # Cash in                                            0.0
        expected_lines[15][1] -= 500.0              # Cash out                                          -500.0
        expected_lines[16][1] -= 1000.0             # Cash and cash equivalents, closing balance        -1650.0
        assertCashFlowValues(report._get_lines(options), expected_lines)

        # ===================================================================================================
        # CASE 5:
        # Same as case 4 but this time, the liquidity move is creditor.
        #
        # Misc move 1:
        # Id  | Account         | Debit     | Credit  | Date
        # ---------------------------------------------------
        # 1   | other 1         | 3000      |         | 2015-06-02
        # 2   | other 2         |           | 5000    | 2015-06-02
        # 3   | other 2         | 1000      |         | 2015-06-02
        # 4   | other 2         | 1000      |         | 2015-06-02
        #
        # Liquidity move 1:
        # Id  | Account         | Debit     | Credit  | Date
        # ---------------------------------------------------
        # 5   | Bank            | 1000      |         | 2015-06-02
        # 6   | other 2         |           | 1000    | 2015-06-02
        #
        # Reconciliation table (account.partial.reconcile):
        # Debit id    | Credit id     | Amount
        # ---------------------------------------------------
        # 3           | 6             | 1000
        # ===================================================================================================

        # Init moves + reconciliation.
        moves = self.env['account.move'].create([
            {
                'date': '2015-06-01',
                'line_ids': [
                    (0, 0, {'debit': 3000.0, 'credit': 0.0, 'account_id': other_account_1.id}),
                    (0, 0, {'debit': 0.0, 'credit': 5000.0, 'account_id': other_account_2.id}),
                    (0, 0, {'debit': 1000.0, 'credit': 0.0, 'account_id': other_account_2.id}),
                    (0, 0, {'debit': 1000.0, 'credit': 0.0, 'account_id': other_account_2.id}),
                ],
            },
            {
                'date': '2015-06-01',
                'line_ids': [
                    (0, 0, {'debit': 1000.0, 'credit': 0.0, 'account_id': liquidity_account.id}),
                    (0, 0, {'debit': 0.0, 'credit': 1000.0, 'account_id': other_account_2.id}),
                ],
            },
        ])
        moves.post()

        moves.mapped('line_ids')\
            .filtered(lambda line: line.account_id == other_account_2 and abs(line.balance) == 1000.0)\
            .reconcile()

        options['date']['date_to'] = '2015-06-01'
        expected_lines[1][1] += 1000.0              # Net increase in cash and cash equivalents         0.0
        expected_lines[13][1] += 1000.0             # Cash flows from unclassified activities           500.0
        expected_lines[14][1] += 500.0              # Cash in                                           500.0
        expected_lines[15][1] += 500.0              # Cash out                                          0.0
        expected_lines[16][1] += 1000.0             # Cash and cash equivalents, closing balance        -650.0
        assertCashFlowValues(report._get_lines(options), expected_lines)

        # ===================================================================================================
        # CASE 6:
        # Test the additional lines on liquidity moves (e.g. bank fees) are well reported in the cash flow statement.
        #
        # Liquidity move 1:
        # Id  | Account         | Debit     | Credit  | Date
        # ---------------------------------------------------
        # 1   | Bank            | 3000      |         | 2015-07-01
        # 2   | other 2         |           | 1000    | 2015-07-01
        # 3   | Receivable 2    |           | 2000    | 2015-07-01
        #
        # Liquidity move 2:
        # Id  | Account         | Debit     | Credit  | Date
        # ---------------------------------------------------
        # 4   | Bank            |           | 3000    | 2015-07-01
        # 5   | other 1         | 1000      |         | 2015-07-01
        # 6   | Receivable 1    | 2000      |         | 2015-07-01
        #
        # Liquidity move 3:
        # Id  | Account         | Debit     | Credit  | Date
        # ---------------------------------------------------
        # 7   | Bank            | 1000      |         | 2015-07-01
        # 8   | other 1         | 1000      |         | 2015-07-01
        # 9   | Receivable 2    |           | 2000    | 2015-07-01
        #
        # Liquidity move 4:
        # Id  | Account         | Debit     | Credit  | Date
        # ---------------------------------------------------
        # 10  | Bank            |           | 1000    | 2015-07-01
        # 11  | other 2         |           | 1000    | 2015-07-01
        # 12  | Receivable 1    | 2000      |         | 2015-07-01
        #
        # Misc move 1:
        # Id  | Account         | Debit     | Credit  | Date
        # ---------------------------------------------------
        # 13  | Receivable 1    |           | 4000    | 2015-07-01
        # 14  | Receivable 2    | 4000      |         | 2015-07-01
        #
        # Reconciliation table (account.partial.reconcile):
        # Debit id    | Credit id     | Amount
        # ---------------------------------------------------
        # 13          | 12            | 2000
        # 13          | 6             | 2000
        # 14          | 3             | 2000
        # 14          | 9             | 2000
        # ===================================================================================================

        # Init moves + reconciliation.
        moves = self.env['account.move'].create([
            {
                'date': '2015-07-01',
                'line_ids': [
                    (0, 0, {'debit': 3000.0, 'credit': 0.0, 'account_id': liquidity_account.id}),
                    (0, 0, {'debit': 0.0, 'credit': 1000.0, 'account_id': other_account_2.id}),
                    (0, 0, {'debit': 0.0, 'credit': 2000.0, 'account_id': receivable_account_2.id}),
                ],
            },
            {
                'date': '2015-07-01',
                'line_ids': [
                    (0, 0, {'debit': 0.0, 'credit': 3000.0, 'account_id': liquidity_account.id}),
                    (0, 0, {'debit': 1000.0, 'credit': 0.0, 'account_id': other_account_1.id}),
                    (0, 0, {'debit': 2000.0, 'credit': 0.0, 'account_id': receivable_account_1.id}),
                ],
            },
            {
                'date': '2015-07-01',
                'line_ids': [
                    (0, 0, {'debit': 1000.0, 'credit': 0.0, 'account_id': liquidity_account.id}),
                    (0, 0, {'debit': 1000.0, 'credit': 0.0, 'account_id': other_account_1.id}),
                    (0, 0, {'debit': 0.0, 'credit': 2000.0, 'account_id': receivable_account_2.id}),
                ],
            },
            {
                'date': '2015-07-01',
                'line_ids': [
                    (0, 0, {'debit': 0.0, 'credit': 1000.0, 'account_id': liquidity_account.id}),
                    (0, 0, {'debit': 0.0, 'credit': 1000.0, 'account_id': other_account_2.id}),
                    (0, 0, {'debit': 2000.0, 'credit': 0.0, 'account_id': receivable_account_1.id}),
                ],
            },
            {
                'date': '2015-07-01',
                'line_ids': [
                    (0, 0, {'debit': 0.0, 'credit': 4000.0, 'account_id': receivable_account_1.id}),
                    (0, 0, {'debit': 4000.0, 'credit': 0.0, 'account_id': receivable_account_2.id}),
                ],
            },
        ])
        moves.post()

        moves.mapped('line_ids')\
            .filtered(lambda line: line.account_id == receivable_account_1)\
            .reconcile()
        moves.mapped('line_ids')\
            .filtered(lambda line: line.account_id == receivable_account_2)\
            .reconcile()

        options['date']['date_to'] = '2015-07-01'
        expected_lines[10][1] += 2000.0             # Cash flows from financing activities              2000.0
        expected_lines[11][1] += 2000.0             # Cash in                                           2000.0
        expected_lines[13][1] -= 2000.0             # Cash flows from unclassified activities           -1500.0
        expected_lines[15][1] -= 2000.0             # Cash out                                          -3000.0
        assertCashFlowValues(report._get_lines(options), expected_lines)

        # ===================================================================================================
        # CASE 7:
        # Liquidity moves are reconciled on the bank account.
        #
        # Liquidity move 1:
        # Id  | Account         | Debit     | Credit  | Date
        # ---------------------------------------------------
        # 1   | Bank            | 3000      |         | 2015-07-01
        # 2   | other 2         |           | 1000    | 2015-07-01
        # 3   | Receivable 2    |           | 2000    | 2015-07-01
        #
        # Liquidity move 2:
        # Id  | Account         | Debit     | Credit  | Date
        # ---------------------------------------------------
        # 4   | Bank            |           | 1500    | 2015-07-01
        # 5   | other 1         | 500       |         | 2015-07-01
        # 6   | Receivable 1    | 1000      |         | 2015-07-01
        #
        # Reconciliation table (account.partial.reconcile):
        # Debit id    | Credit id     | Amount
        # ---------------------------------------------------
        # 1           | 4             | 1500
        # ===================================================================================================

        # Reset the report at 2015-08-01.
        options['date']['date_from'] = '2015-08-01'
        for line in expected_lines:
            line[1] = 0
        expected_lines[0][1] -= 650.0               # Cash and cash equivalents, beginning of period    -650.0
        expected_lines[16][1] -= 650.0              # Cash and cash equivalents, closing balance        -650.0

        # Init moves + reconciliation.
        moves = self.env['account.move'].create([
            {
                'date': '2015-08-01',
                'line_ids': [
                    (0, 0, {'debit': 3000.0, 'credit': 0.0, 'account_id': liquidity_account.id}),
                    (0, 0, {'debit': 0.0, 'credit': 1000.0, 'account_id': other_account_2.id}),
                    (0, 0, {'debit': 0.0, 'credit': 2000.0, 'account_id': receivable_account_2.id}),
                ],
            },
            {
                'date': '2015-08-01',
                'line_ids': [
                    (0, 0, {'debit': 0.0, 'credit': 1500.0, 'account_id': liquidity_account.id}),
                    (0, 0, {'debit': 500.0, 'credit': 0.0, 'account_id': other_account_1.id}),
                    (0, 0, {'debit': 1000.0, 'credit': 0.0, 'account_id': receivable_account_1.id}),
                ],
            },
        ])
        moves.post()

        liquidity_account.reconcile = True
        moves.mapped('line_ids')\
            .filtered(lambda line: line.account_id == liquidity_account)\
            .reconcile()

        options['date']['date_to'] = '2015-08-01'
        expected_lines[1][1] += 1500.0              # Net increase in cash and cash equivalents         1500.0
        expected_lines[2][1] += 1000.0              # Cash flows from operating activities              1000.0
        expected_lines[3][1] += 1000.0              # Advance Payments received from customers          1000.0
        expected_lines[10][1] += 1000.0             # Cash flows from financing activities              1000.0
        expected_lines[11][1] += 1000.0             # Cash in                                           1000.0
        expected_lines[13][1] -= 500.0              # Cash flows from unclassified activities           -500.0
        expected_lines[15][1] -= 500.0              # Cash out                                          -500.0
        expected_lines[16][1] += 1500.0             # Cash and cash equivalents, closing balance        850.0
        assertCashFlowValues(report._get_lines(options), expected_lines)

        # Undo the reconciliation.
        moves.mapped('line_ids')\
            .filtered(lambda line: line.account_id == liquidity_account)\
            .remove_move_reconcile()
        liquidity_account.reconcile = False

        # ===================================================================================================
        # CASE 8:
        # Difficulties of these cases are:
        # - The liquidity moves are reconciled to moves having a total amount of 0.0.
        # - Double reconciliation between the liquidity and the misc moves.
        # - The reconciliations are partials.
        # - There are additional lines on the misc moves.
        #
        # Liquidity move 1:
        # Id  | Account         | Debit     | Credit  | Date
        # ---------------------------------------------------
        # 1   | Bank            |           | 100     | 2015-09-01
        # 2   | Receivable 2    | 900       |         | 2015-09-01
        # 3   | other 1         |           | 400     | 2015-09-01
        # 4   | other 2         |           | 400     | 2015-09-01
        #
        # Misc move 1:
        # Id  | Account         | Debit     | Credit  | Date
        # ---------------------------------------------------
        # 5   | other 1         | 500       |         | 2015-09-01
        # 6   | other 1         |           | 500     | 2015-09-01
        # 7   | other 2         | 500       |         | 2015-09-01
        # 8   | other 2         |           | 500     | 2015-09-01
        #
        # Reconciliation table (account.partial.reconcile):
        # Debit id    | Credit id     | Amount
        # ---------------------------------------------------
        # 5           | 3             | 400
        # 8           | 4             | 400
        # ===================================================================================================

        # Reset the report at 2015-09-01.
        options['date']['date_from'] = '2015-09-01'
        for line in expected_lines:
            line[1] = 0
        expected_lines[0][1] += 850.0               # Cash and cash equivalents, beginning of period    850.0
        expected_lines[16][1] += 850.0              # Cash and cash equivalents, closing balance        850.0

        # Init moves + reconciliation.
        moves = self.env['account.move'].create([
            {
                'date': '2015-09-01',
                'line_ids': [
                    (0, 0, {'debit': 0.0, 'credit': 100.0, 'account_id': liquidity_account.id}),
                    (0, 0, {'debit': 900.0, 'credit': 0.0, 'account_id': receivable_account_2.id}),
                    (0, 0, {'debit': 0.0, 'credit': 400.0, 'account_id': other_account_1.id}),
                    (0, 0, {'debit': 0.0, 'credit': 400.0, 'account_id': other_account_2.id}),
                ],
            },
            {
                'date': '2015-09-01',
                'line_ids': [
                    (0, 0, {'debit': 500.0, 'credit': 0.0, 'account_id': other_account_1.id}),
                    (0, 0, {'debit': 0.0, 'credit': 500.0, 'account_id': other_account_1.id}),
                    (0, 0, {'debit': 500.0, 'credit': 0.0, 'account_id': other_account_2.id}),
                    (0, 0, {'debit': 0.0, 'credit': 500.0, 'account_id': other_account_2.id}),
                ],
            },
        ])
        moves.post()

        credit_line = moves[0].line_ids.filtered(lambda line: line.account_id == other_account_1)
        debit_line = moves[1].line_ids.filtered(lambda line: line.account_id == other_account_1 and line.debit > 0.0)
        (credit_line + debit_line).reconcile()

        credit_line = moves[0].line_ids.filtered(lambda line: line.account_id == other_account_2)
        debit_line = moves[1].line_ids.filtered(lambda line: line.account_id == other_account_2 and line.debit > 0.0)
        (credit_line + debit_line).reconcile()

        options['date']['date_to'] = '2015-09-01'
        expected_lines[1][1] -= 100.0               # Net increase in cash and cash equivalents         -100.0
        expected_lines[2][1] -= 900.0               # Cash flows from operating activities              -900.0
        expected_lines[3][1] -= 900.0               # Advance Payments received from customers          -900.0
        expected_lines[10][1] += 400.0              # Cash flows from financing activities              400.0
        expected_lines[11][1] += 400.0              # Cash in                                           400.0
        expected_lines[13][1] += 400.0              # Cash flows from unclassified activities           400.0
        expected_lines[14][1] += 400.0              # Cash in                                           400.0
        expected_lines[16][1] -= 100.0              # Cash and cash equivalents, closing balance        750.0
        assertCashFlowValues(report._get_lines(options), expected_lines)

        # ===================================================================================================
        # CASE 9:
        # Same as case 8 but with inversed debit/credit.
        #
        # Liquidity move 1:
        # Id  | Account         | Debit     | Credit  | Date
        # ---------------------------------------------------
        # 1   | Bank            | 100       |         | 2015-10-01
        # 2   | Receivable 2    |           | 900     | 2015-10-01
        # 3   | other 1         | 400       |         | 2015-10-01
        # 4   | other 2         | 400       |         | 2015-10-01
        #
        # Misc move 1:
        # Id  | Account         | Debit     | Credit  | Date
        # ---------------------------------------------------
        # 6   | other 1         |           | 500     | 2015-10-01
        # 5   | other 1         | 500       |         | 2015-10-01
        # 8   | other 2         |           | 500     | 2015-10-01
        # 7   | other 2         | 500       |         | 2015-10-01
        #
        # Reconciliation table (account.partial.reconcile):
        # Debit id    | Credit id     | Amount
        # ---------------------------------------------------
        # 5           | 3             | 400
        # 8           | 4             | 400
        # ===================================================================================================

        # Reset the report at 2015-10-01.
        options['date']['date_from'] = '2015-10-01'
        for line in expected_lines:
            line[1] = 0
        expected_lines[0][1] += 750.0               # Cash and cash equivalents, beginning of period    750.0
        expected_lines[16][1] += 750.0              # Cash and cash equivalents, closing balance        750.0

        # Init moves + reconciliation.
        moves = self.env['account.move'].create([
            {
                'date': '2015-10-01',
                'line_ids': [
                    (0, 0, {'debit': 100.0, 'credit': 0.0, 'account_id': liquidity_account.id}),
                    (0, 0, {'debit': 0.0, 'credit': 900.0, 'account_id': receivable_account_2.id}),
                    (0, 0, {'debit': 400.0, 'credit': 0.0, 'account_id': other_account_1.id}),
                    (0, 0, {'debit': 400.0, 'credit': 0.0, 'account_id': other_account_2.id}),
                ],
            },
            {
                'date': '2015-10-01',
                'line_ids': [
                    (0, 0, {'debit': 0.0, 'credit': 500.0, 'account_id': other_account_1.id}),
                    (0, 0, {'debit': 500.0, 'credit': 0.0, 'account_id': other_account_1.id}),
                    (0, 0, {'debit': 0.0, 'credit': 500.0, 'account_id': other_account_2.id}),
                    (0, 0, {'debit': 500.0, 'credit': 0.0, 'account_id': other_account_2.id}),
                ],
            },
        ])
        moves.post()

        credit_line = moves[1].line_ids.filtered(lambda line: line.account_id == other_account_1 and line.credit > 0.0)
        debit_line = moves[0].line_ids.filtered(lambda line: line.account_id == other_account_1)
        (credit_line + debit_line).reconcile()

        credit_line = moves[1].line_ids.filtered(lambda line: line.account_id == other_account_2 and line.credit > 0.0)
        debit_line = moves[0].line_ids.filtered(lambda line: line.account_id == other_account_2)
        (credit_line + debit_line).reconcile()

        options['date']['date_to'] = '2015-10-01'
        expected_lines[1][1] += 100.0               # Net increase in cash and cash equivalents         100.0
        expected_lines[2][1] += 900.0               # Cash flows from operating activities              900.0
        expected_lines[3][1] += 900.0               # Advance Payments received from customers          900.0
        expected_lines[10][1] -= 400.0              # Cash flows from financing activities              -400.0
        expected_lines[12][1] -= 400.0              # Cash out                                          -400.0
        expected_lines[13][1] -= 400.0              # Cash flows from unclassified activities           -400.0
        expected_lines[15][1] -= 400.0              # Cash out                                          -400.0
        expected_lines[16][1] += 100.0              # Cash and cash equivalents, closing balance        850.0
        assertCashFlowValues(report._get_lines(options), expected_lines)

    def test_cash_flow_statement_2_multi_company_currency(self):
        # Init report / options.
        report = self.env['account.cash.flow.report'].with_context(allowed_company_ids=(self.company_parent + self.company_child_eur).ids)
        options = self._init_options(report, *date_utils.get_month(fields.Date.from_string('2015-01-01')))

        invoice = self._create_invoice(self.env, 1000, self.partner_a, 'out_invoice', '2015-01-01')
        self._create_payment(self.env, fields.Date.from_string('2015-01-15'), invoice, amount=1035)
        self.env.user.company_id = self.company_child_eur
        invoice = self._create_invoice(self.env, 1000, self.partner_a, 'out_invoice', '2015-01-01')
        self._create_payment(self.env, fields.Date.from_string('2015-01-15'), invoice, amount=1035)
        self.env.user.company_id = self.company_parent

        self.assertLinesValues(report._get_lines(options), [0, 1], [
            ['Cash and cash equivalents, beginning of period',                      0.0],
            ['Net increase in cash and cash equivalents',                           2070.0],
            ['Cash flows from operating activities',                                1800.0],
            ['Advance Payments received from customers',                            0.0],
            ['Cash received from operating activities',                             1800.0],
            ['400000 Product Sales',                                                900.0],
            ['400000 Product Sales',                                                900.0],
            ['Total Cash received from operating activities',                       1800.0],
            ['Advance payments made to suppliers',                                  0.0],
            ['Cash paid for operating activities',                                  0.0],
            ['Cash flows from investing & extraordinary activities',                0.0],
            ['Cash in',                                                             0.0],
            ['Cash out',                                                            0.0],
            ['Cash flows from financing activities',                                0.0],
            ['Cash in',                                                             0.0],
            ['Cash out',                                                            0.0],
            ['Cash flows from unclassified activities',                             270.0],
            ['Cash in',                                                             270.0],
            ['251000 Tax Received',                                                 135.0],
            ['251000 Tax Received',                                                 135.0],
            ['Total Cash in',                                                       270.0],
            ['Cash out',                                                            0.0],
            ['Cash and cash equivalents, closing balance',                          2070.0],
            ['101401 Bank',                                                         1035.0],
            ['101401 Bank',                                                         1035.0],
            ['Total Cash and cash equivalents, closing balance',                    2070.0],
        ])

    # -------------------------------------------------------------------------
    # TESTS: Reconciliation Report
    # -------------------------------------------------------------------------

    def test_reconciliation_report_initial_state(self):
        ''' Test the lines of the initial state. '''
        bank_journal = self.env['account.journal'].search([('company_id', '=', self.company_parent.id), ('type', '=', 'bank')])

        # Init options.
        report = self.env['account.bank.reconciliation.report'].with_context(active_id=bank_journal.id)
        options = self._init_options(report, *date_utils.get_month(self.mar_year_minus_1))
        report = report.with_context(report._set_context(options))

        self.assertLinesValues(
            report._get_lines(options),
            #   Name                                                            Date            Amount
            [   0,                                                              1,              3],
            [
                ('Virtual GL Balance',                                          '',             ''),
                ('Current balance of account 101401',                           '03/31/2017',   -950.00),
                ('Operations to Process',                                       '',             -100),
                ('Unreconciled Bank Statement Lines',                           '',             ''),
                ('CUST.IN/2017/0003',                                           '03/01/2017',   100.00),
                ('Validated Payments not Linked with a Bank Statement Line',    '',             ''),
                ('SUPP.OUT/2017/0003',                                          '03/01/2017',   300.00),
                ('CUST.IN/2017/0003',                                           '03/01/2017',   -100.00),
                ('SUPP.OUT/2017/0002',                                          '02/01/2017',   200.00),
                ('CUST.IN/2017/0001',                                           '01/01/2017',   -600.00),
                ('Total Virtual GL Balance',                                    '',             -1050.00),
                ('Last Bank Statement Ending Balance',                          '03/01/2017',   -1050.00),
                ('Unexplained Difference',                                      '',             0),
            ],
        )

    def test_reconciliation_report_multi_company_currency(self):
        ''' Test the lines in a multi-company/multi-currency environment. '''
        bank_journal = self.env['account.journal'].search([('company_id', '=', self.company_child_eur.id), ('type', '=', 'bank')])

        # Init options.
        report = self.env['account.bank.reconciliation.report'].with_context(active_id=bank_journal.id)
        options = self._init_options(report, *date_utils.get_month(self.mar_year_minus_1))
        report = report.with_context(report._set_context(options))
        self.assertLinesValues(
            report._get_lines(options),
            #   Name                                                            Date            Amount
            [   0,                                                              1,              3],
            [
                ('Virtual GL Balance',                                          '',             ''),
                ('Current balance of account 101401',                           '03/31/2017',   -1900.00),
                ('Operations to Process',                                       '',             -200),
                ('Unreconciled Bank Statement Lines',                           '',             ''),
                ('CUST.IN/2017/0007',                                           '03/01/2017',   200.00),
                ('Validated Payments not Linked with a Bank Statement Line',    '',             ''),
                ('SUPP.OUT/2017/0006',                                          '03/01/2017',   600.00),
                ('CUST.IN/2017/0007',                                           '03/01/2017',   -200.00),
                ('SUPP.OUT/2017/0005',                                          '02/01/2017',   400.00),
                ('CUST.IN/2017/0005',                                           '01/01/2017',   -1200.00),
                ('Total Virtual GL Balance',                                    '',             -2100.00),
                ('Last Bank Statement Ending Balance',                          '03/01/2017',   -2100.00),
                ('Unexplained Difference',                                      '',             0),
            ],
            currency=self.company_child_eur.currency_id,
        )

    def test_reconciliation_report_journal_foreign_currency(self):
        ''' Test the lines with a foreign currency on the journal. '''
        bank_journal = self.env['account.journal'].search([('company_id', '=', self.company_parent.id), ('type', '=', 'bank')])
        foreign_currency = self.env.ref('base.EUR')

        # Set up the foreign currency.
        bank_journal_eur = bank_journal.copy()
        account = bank_journal.default_debit_account_id.copy()
        account.currency_id = foreign_currency
        bank_journal_eur.default_debit_account_id = bank_journal_eur.default_credit_account_id = account
        bank_journal_eur.currency_id = foreign_currency

        invoice = self._create_invoice(self.env, 1000.0, self.partner_a, 'out_invoice', self.mar_year_minus_1)
        payment = self._create_payment(self.env, self.mar_year_minus_1, invoice, journal=bank_journal_eur)
        self._create_bank_statement(self.env, payment, amount=2300.00, reconcile=False)

        # Init options.
        report = self.env['account.bank.reconciliation.report'].with_context(active_id=bank_journal_eur.id)
        options = self._init_options(report, *date_utils.get_month(self.mar_year_minus_1))
        report = report.with_context(report._set_context(options))

        self.assertLinesValues(
            report._get_lines(options),
            #   Name                                                            Date            Amount
            [   0,                                                              1,              3],
            [
                ('Virtual GL Balance',                                          '',             ''),
                ('Current balance of account 101411',                           '03/31/2017',   2300.00),
                ('Operations to Process',                                       '',             0),
                ('Unreconciled Bank Statement Lines',                           '',             ''),
                ('CUST.IN/2017/0009',                                           '03/01/2017',   2300.00),
                ('Validated Payments not Linked with a Bank Statement Line',    '',             ''),
                ('CUST.IN/2017/0009',                                           '03/01/2017',   -2300.00),
                ('Total Virtual GL Balance',                                    '',             2300.00),
                ('Last Bank Statement Ending Balance',                          '03/01/2017',   2300.00),
                ('Unexplained Difference',                                      '',             0),
            ],
            currency=foreign_currency,
        )

    # -------------------------------------------------------------------------
    # TESTS: Consolidated Journals
    # -------------------------------------------------------------------------

    def test_consolidated_journals_folded_unfolded(self):
        ''' Test folded/unfolded lines. '''
        # Init options.
        report = self.env['account.consolidated.journal']
        options = self._init_options(report, *date_utils.get_quarter(self.mar_year_minus_1))
        report = report.with_context(report._set_context(options))

        lines = report._get_lines(options)
        self.assertLinesValues(
            lines,
            #   Name                                    Debit           Credit          Balance
            [   0,                                      1,              2,              3],
            [
                ('Customer Invoices (INV)',             1495.00,        1495.00,        0.00),
                ('Vendor Bills (BILL)',                 1265.00,        1265.00,        0.00),
                ('Bank (BNK1)',                         1350.00,        1350.00,        0.00),
                ('Total',                               4110.00,        4110.00,        0.00),
                ('',                                    '',             '',             ''),
                ('Details per month',                   '',             '',             ''),
                ('Jan 2017',                            1160.00,        1160.00,        0.00),
                ('Feb 2017',                            1170.00,        1170.00,        0.00),
                ('Mar 2017',                            1780.00,        1780.00,        0.00),
            ],
        )

        # Mark the 'Customer Invoices (INV)' line to be unfolded.
        line_id = lines[0]['id']
        options['unfolded_lines'] = [line_id]
        report = report.with_context(report._set_context(options))

        lines = report._get_lines(options, line_id=line_id)
        self.assertLinesValues(
            lines,
            #   Name                                    Debit           Credit          Balance
            [   0,                                      1,              2,              3],
            [
                ('Customer Invoices (INV)',             1495.00,        1495.00,        0.00),
                ('121000 Account Receivable',           1495.00,        0.00,           1495.00),
                ('251000 Tax Received',                 0.00,           195.00,         -195.00),
                ('400000 Product Sales',                0.00,           1300.00,        -1300.00),
            ],
        )

        # Mark the '121000 Account Receivable' line to be unfolded.
        line_id = lines[1]['id']
        options['unfolded_lines'] = [line_id]
        report = report.with_context(report._set_context(options))

        self.assertLinesValues(
            report._get_lines(options, line_id=line_id),
            #   Name                                    Debit           Credit          Balance
            [   0,                                      1,              2,              3],
            [
                ('Jan 2017',                            345.00,         0.00,           345.00),
                ('Feb 2017',                            460.00,         0.00,           460.00),
                ('Mar 2017',                            690.00,         0.00,           690.00),
            ],
        )

    def test_consolidated_journals_filter_journals(self):
        ''' Test folded/unfolded lines with a filter on journals. '''
        bank_journal = self.env['account.journal'].search([('company_id', '=', self.company_parent.id), ('type', '=', 'bank')])

        # Init options.
        report = self.env['account.consolidated.journal']
        options = self._init_options(report, *date_utils.get_quarter(self.mar_year_minus_1))
        options = self._update_multi_selector_filter(options, 'journals', bank_journal.ids)
        report = report.with_context(report._set_context(options))

        lines = report._get_lines(options)
        self.assertLinesValues(
            lines,
            #   Name                                    Debit           Credit          Balance
            [   0,                                      1,              2,              3],
            [
                ('Bank (BNK1)',                         1350.00,        1350.00,        0.00),
                ('Total',                               1350.00,        1350.00,        0.00),
                ('',                                    '',             '',             ''),
                ('Details per month',                   '',             '',             ''),
                ('Jan 2017',                            700.00,         700.00,         0.00),
                ('Feb 2017',                            250.00,         250.00,         0.00),
                ('Mar 2017',                            400.00,         400.00,         0.00),
            ],
        )

        # Mark the 'Bank (BNK1)' line to be unfolded.
        line_id = lines[0]['id']
        options['unfolded_lines'] = [line_id]
        report = report.with_context(report._set_context(options))

        lines = report._get_lines(options, line_id=line_id)
        self.assertLinesValues(
            lines,
            #   Name                                    Debit           Credit          Balance
            [   0,                                      1,              2,              3],
            [
                ('Bank (BNK1)',                         1350.00,        1350.00,        0.00),
                ('101401 Bank',                         800.00,         550.00,         250.00),
                ('121000 Account Receivable',           0.00,           800.00,         -800.00),
                ('211000 Account Payable',              550.00,         0.00,           550.00),
            ],
        )

        # Mark the '121000 Account Receivable' line to be unfolded.
        line_id = lines[2]['id']
        options['unfolded_lines'] = [line_id]
        report = report.with_context(report._set_context(options))

        self.assertLinesValues(
            report._get_lines(options, line_id=line_id),
            #   Name                                    Debit           Credit          Balance
            [   0,                                      1,              2,              3],
            [
                ('Jan 2017',                            0.00,           700.00,         -700.00),
                ('Mar 2017',                            0.00,           100.00,         -100.00),
            ],
        )

    # -------------------------------------------------------------------------
    # TESTS: VAT report
    # -------------------------------------------------------------------------

    def _close_vat_entries(self, report, options):
        ctx = report._set_context(options)
        ctx['strict_range'] = True
        report = report.with_context(ctx)
        move = report._generate_tax_closing_entry(options)
        return move

    def test_automatic_vat_closing_report_payable(self):
        def _get_attachment(*args, **kwargs):
            return []
        report = self.env['account.generic.tax.report']
        # Due to warning in runbot when printing wkhtmltopdf in the test, patch the method that fetch the pdf in order
        # to return an empty attachment.
        with patch.object(type(report), '_get_vat_report_attachments', autospec=True, side_effect=_get_attachment):
            # Try closing VAT in two different period with one invoice in each period.
            # Create an invoice in january and one in february
            january_inv_date = datetime.datetime.strptime('2018-01-10', DEFAULT_SERVER_DATE_FORMAT).date()
            february_inv_date = datetime.datetime.strptime('2018-02-12', DEFAULT_SERVER_DATE_FORMAT).date()

            # December
            self._create_invoice(self.env, 1000.0, self.partner_a, 'out_invoice', january_inv_date)
            self._create_invoice(self.env, 100.0, self.partner_a, 'out_invoice', february_inv_date)

            # Try closing vat entries for january
            options = self._init_options(report, self.january_date, self.january_end_date)
            move = self._close_vat_entries(report, options)
            # assert element on move
            self.assertEquals(len(move.line_ids), 2, 'Tax Move created should have only 2 lines')
            debit_line = move.line_ids.filtered(lambda a: a.debit > 0)
            credit_line = move.line_ids.filtered(lambda a: a.credit > 0)
            self.assertEquals(debit_line.debit, 150)
            self.assertEquals(credit_line.credit, 150)
            self.assertEquals(credit_line.name, 'Payable tax amount')
            self.assertEquals(credit_line.account_id.id, self.tax_pay_account.id)
            move.post()

            # Try closing vat entries for february
            options = self._init_options(report, self.february_date, self.february_end_date)
            move.flush()
            move = self._close_vat_entries(report, options)
            # assert element on move
            self.assertEquals(len(move.line_ids), 3, 'Tax Move created should have 3 lines')
            debit_line = move.line_ids.filtered(lambda a: a.debit == 15)
            debit_line_balanced = move.line_ids.filtered(lambda a: a.name == 'Balance tax current account (payable)')
            credit_line_total = move.line_ids.filtered(lambda a: a.credit > 0)
            self.assertEquals(debit_line.debit, 15)
            self.assertEquals(debit_line_balanced.debit, 150)
            self.assertEquals(debit_line_balanced.account_id.id, self.tax_pay_account.id)
            self.assertEquals(credit_line_total.credit, 165)
            self.assertEquals(credit_line_total.account_id.id, self.tax_pay_account.id)

    def test_automatic_vat_closing_report_receivable(self):
        def _get_attachment(*args, **kwargs):
            return []
        report = self.env['account.generic.tax.report']
        # Due to warning in runbot when printing wkhtmltopdf in the test, patch the method that fetch the pdf in order
        # to return an empty attachment.
        with patch.object(type(report), '_get_vat_report_attachments', autospec=True, side_effect=_get_attachment):
            # Try closing VAT in two different period with one invoice in each period.
            # Create an invoice in january and one in february
            january_inv_date = datetime.datetime.strptime('2018-01-10', DEFAULT_SERVER_DATE_FORMAT).date()
            february_inv_date = datetime.datetime.strptime('2018-02-12', DEFAULT_SERVER_DATE_FORMAT).date()

            # December
            self._create_invoice(self.env, 100.0, self.partner_a, 'in_invoice', january_inv_date)
            self._create_invoice(self.env, 1000.0, self.partner_a, 'out_invoice', february_inv_date)

            # Try closing vat entries for january
            options = self._init_options(report, self.january_date, self.january_end_date)
            move = self._close_vat_entries(report, options)
            # assert element on move
            self.assertEquals(len(move.line_ids), 2, 'Tax Move created should have only 2 lines')
            debit_line = move.line_ids.filtered(lambda a: a.debit > 0)
            credit_line = move.line_ids.filtered(lambda a: a.credit > 0)
            self.assertEquals(debit_line.debit, 15)
            self.assertEquals(debit_line.name, 'Receivable tax amount')
            self.assertEquals(debit_line.account_id.id, self.tax_rec_account.id)
            self.assertEquals(credit_line.credit, 15)
            move.post()
            # Try closing vat entries for february
            options = self._init_options(report, self.february_date, self.february_end_date)
            move = self._close_vat_entries(report, options)
            # assert element on move
            self.assertEquals(len(move.line_ids), 3, 'Tax Move created should have 3 lines')
            debit_line = move.line_ids.filtered(lambda a: a.debit == 150)
            credit_line_balanced = move.line_ids.filtered(lambda a: a.name == 'Balance tax current account (receivable)')
            credit_line_total = move.line_ids.filtered(lambda a: a.name == 'Payable tax amount')
            self.assertEquals(debit_line.debit, 150)
            # Should balance the 15 previous usd on tax receivable
            self.assertEquals(credit_line_balanced.credit, 15)
            self.assertEquals(credit_line_balanced.account_id.id, self.tax_rec_account.id)
            # We still need to pay 135 to the VAT
            self.assertEquals(credit_line_total.credit, 135)
            self.assertEquals(credit_line_total.account_id.id, self.tax_pay_account.id)


    # -------------------------------------------------------------------------
    # TESTS: GENERIC TAX REPORT
    # -------------------------------------------------------------------------


    def _create_tax_report_line(self, name, country, tag_name=None, parent_line=None, sequence=None, code=None, formula=None):
        """ Creates a tax report line
        """
        create_vals = {
            'name': name,
            'country_id': country.id,
        }
        if tag_name:
            create_vals['tag_name'] = tag_name
        if parent_line:
            create_vals['parent_id'] = parent_line.id
        if sequence != None:
            create_vals['sequence'] = sequence
        if code:
            create_vals['code'] = code
        if formula:
            create_vals['formula'] = formula

        return self.env['account.tax.report.line'].create(create_vals)

    def test_tax_report_grid(self):
        test_country = self.env['res.country'].create({
            'name': "L'Île de la Mouche",
            'code': 'YY',
        })

        company = self.env.user.company_id
        company.country_id = test_country
        partner = self.env['res.partner'].create({'name': 'Provençal le Gaulois'})

        # We generate a tax report with the following layout
        #/Base
        #   - Base 42%
        #   - Base 11%
        #/Tax
        #   - Tax 42%
        #       - 10.5%
        #       - 31.5%
        #   - Tax 11%
        #/Tax difference (42% - 11%)

        # We create the lines in a different order from the one they have in report,
        # so that we ensure sequence is taken into account properly when rendering the report
        tax_section =  self._create_tax_report_line('Tax', test_country, sequence=2)
        base_section =  self._create_tax_report_line('Base', test_country, sequence=1)
        base_11_line = self._create_tax_report_line('Base 11%', test_country, sequence=2, parent_line=base_section, tag_name='base_11')
        base_42_line = self._create_tax_report_line('Base 42%', test_country, sequence=1, parent_line=base_section, tag_name='base_42')
        tax_42_section = self._create_tax_report_line('Tax 42%', test_country, sequence=1, parent_line=tax_section, code='tax_42')
        tax_31_5_line = self._create_tax_report_line('Tax 31.5%', test_country, sequence=2, parent_line=tax_42_section, tag_name='tax_31_5')
        tax_10_5_line = self._create_tax_report_line('Tax 10.5%', test_country, sequence=1, parent_line=tax_42_section, tag_name='tax_10_5')
        tax_11_line = self._create_tax_report_line('Tax 10.5%', test_country, sequence=2, parent_line=tax_section, tag_name='tax_11', code='tax_11')
        tax_difference_line = self._create_tax_report_line('Tax difference (42%-11%)', test_country, sequence=3, formula='tax_42 - tax_11')

        # Create two taxes linked to report lines
        tax_template_11 = self.env['account.tax.template'].create({
            'name': 'Impôt sur les revenus',
            'amount': '11',
            'amount_type': 'percent',
            'type_tax_use': 'sale',
            'chart_template_id': company.chart_template_id.id,
            'invoice_repartition_line_ids': [
                (0,0, {
                    'factor_percent': 100,
                    'repartition_type': 'base',
                    'plus_report_line_ids': [base_11_line.id],
                }),

                (0,0, {
                    'factor_percent': 100,
                    'repartition_type': 'tax',
                    'plus_report_line_ids': [tax_11_line.id],
                }),
            ],
            'refund_repartition_line_ids': [
                (0,0, {
                    'factor_percent': 100,
                    'repartition_type': 'base',
                    'minus_report_line_ids': [base_11_line.id],
                }),

                (0,0, {
                    'factor_percent': 100,
                    'repartition_type': 'tax',
                    'minus_report_line_ids': [tax_11_line.id],
                }),
            ],
        })

        tax_template_42 = self.env['account.tax.template'].create({
            'name': 'Impôt sur les revenants',
            'amount': '42',
            'amount_type': 'percent',
            'type_tax_use': 'sale',
            'chart_template_id': company.chart_template_id.id,
            'invoice_repartition_line_ids': [
                (0,0, {
                    'factor_percent': 100,
                    'repartition_type': 'base',
                    'plus_report_line_ids': [base_42_line.id],
                }),

                (0,0, {
                    'factor_percent': 25,
                    'repartition_type': 'tax',
                    'plus_report_line_ids': [tax_10_5_line.id],
                }),

                (0,0, {
                    'factor_percent': 75,
                    'repartition_type': 'tax',
                    'plus_report_line_ids': [tax_31_5_line.id],
                }),
            ],
            'refund_repartition_line_ids': [
                (0,0, {
                    'factor_percent': 100,
                    'repartition_type': 'base',
                    'minus_report_line_ids': [base_42_line.id],
                }),

                (0,0, {
                    'factor_percent': 25,
                    'repartition_type': 'tax',
                    'minus_report_line_ids': [tax_10_5_line.id],
                }),

                (0,0, {
                    'factor_percent': 75,
                    'repartition_type': 'tax',
                    'minus_report_line_ids': [tax_31_5_line.id],
                }),
            ],
        })
        # The templates needs an xmlid in order so that we can call _generate_tax
        self.env['ir.model.data'].create({
            'name': 'account_reports.test_tax_report_tax_11',
            'module': 'account_reports',
            'res_id': tax_template_11.id,
            'model': 'account.tax.template',
        })
        tax_11_id = tax_template_11._generate_tax(self.env.user.company_id)['tax_template_to_tax'][tax_template_11.id]
        tax_11 = self.env['account.tax'].browse(tax_11_id)

        self.env['ir.model.data'].create({
            'name': 'account_reports.test_tax_report_tax_42',
            'module': 'account_reports',
            'res_id': tax_template_42.id,
            'model': 'account.tax.template',
        })
        tax_42_id = tax_template_42._generate_tax(self.env.user.company_id)['tax_template_to_tax'][tax_template_42.id]
        tax_42 = self.env['account.tax'].browse(tax_42_id)

        # Create an invoice using the tax we just made
        with Form(self.env['account.move'].with_context(default_type='out_invoice')) as invoice_form:
            invoice_form.partner_id = partner
            with invoice_form.invoice_line_ids.new() as invoice_line_form:
                invoice_line_form.name = 'Turlututu'
                invoice_line_form.quantity = 1
                invoice_line_form.price_unit = 100
                invoice_line_form.tax_ids.clear()
                invoice_line_form.tax_ids.add(tax_11)
                invoice_line_form.tax_ids.add(tax_42)
        invoice = invoice_form.save()
        invoice.post()

        # Generate the report and check the results
        report = self.env['account.generic.tax.report']
        report_opt = report._get_options({'date': {'period_type': 'custom', 'filter': 'custom', 'date_to': invoice.date, 'mode': 'range', 'date_from': invoice.date}})
        new_context = report._set_context(report_opt)

        # We check the taxes on invoice have impacted the report properly
        report.flush()
        inv_report_lines = report.with_context(new_context)._get_lines(report_opt)
        self.assertLinesValues(
            inv_report_lines,
            #   Name                                Balance
            [   0,                                  1],
            [
                (base_section.name,                 200),
                (base_42_line.name,                 100),
                (base_11_line.name,                 100),
                (tax_section.name,                  53),
                (tax_42_section.name,               42),
                (tax_10_5_line.name,                10.5),
                (tax_31_5_line.name,                31.5),
                (tax_11_line.name,                  11),
                (tax_difference_line.name,          31),
            ],
        )

        # We refund the invoice
        refund_wizard = self.env['account.move.reversal'].with_context(active_model="account.move", active_ids=invoice.ids).create({
            'reason': 'Test refund tax repartition',
            'refund_method': 'cancel',
        })
        refund_wizard.reverse_moves()

        # We check the taxes on refund have impacted the report properly (everything should be 0)
        ref_report_lines = report.with_context(new_context)._get_lines(report_opt)
        self.assertLinesValues(
            ref_report_lines,
            #   Name                                Balance
            [   0,                                  1],
            [
                (base_section.name,                 0),
                (base_42_line.name,                 0),
                (base_11_line.name,                 0),
                (tax_section.name,                  0),
                (tax_42_section.name,               0),
                (tax_10_5_line.name,                0),
                (tax_31_5_line.name,                0),
                (tax_11_line.name,                  0),
                (tax_difference_line.name,          0),
            ],
        )
