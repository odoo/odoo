# -*- coding: utf-8 -*-
# pylint: disable=C0326
from odoo.tests import tagged
from odoo import fields, Command

from odoo.addons.account_reports.tests.common import TestAccountReportsCommon


@tagged('post_install', '-at_install')
class TestAccountReports(TestAccountReportsCommon):
    @classmethod
    def _reconcile_on(cls, lines, account):
        lines.filtered(lambda line: line.account_id == account and not line.reconciled).reconcile()

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.liquidity_journal_1 = cls.company_data['default_journal_bank']
        cls.liquidity_account = cls.liquidity_journal_1.default_account_id
        cls.receivable_account_1 = cls.company_data['default_account_receivable']
        cls.revenue_account_1 = cls.company_data['default_account_revenue']

        # Invoice having two receivable lines on the same account.

        invoice = cls.env['account.move'].create({
            'move_type': 'entry',
            'date': '2016-01-01',
            'journal_id': cls.company_data['default_journal_misc'].id,
            'line_ids': [
                (0, 0, {'debit': 345.0,     'credit': 0.0,      'account_id': cls.receivable_account_1.id}),
                (0, 0, {'debit': 805.0,     'credit': 0.0,      'account_id': cls.receivable_account_1.id}),
                (0, 0, {'debit': 0.0,       'credit': 1150.0,   'account_id': cls.revenue_account_1.id}),
            ],
        })
        invoice.action_post()

        # First payment (20% of the invoice).

        payment_1 = cls.env['account.move'].create({
            'move_type': 'entry',
            'date': '2016-02-01',
            'journal_id': cls.liquidity_journal_1.id,
            'line_ids': [
                (0, 0, {'debit': 0.0,       'credit': 230.0,    'account_id': cls.receivable_account_1.id}),
                (0, 0, {'debit': 230.0,     'credit': 0.0,      'account_id': cls.liquidity_account.id}),
            ],
        })
        payment_1.action_post()

        cls._reconcile_on((invoice + payment_1).line_ids, cls.receivable_account_1)

        # Second payment (also 20% but will produce two partials, one on each receivable line).

        payment_2 = cls.env['account.move'].create({
            'move_type': 'entry',
            'date': '2016-03-01',
            'journal_id': cls.liquidity_journal_1.id,
            'line_ids': [
                (0, 0, {'debit': 0.0,       'credit': 230.0,    'account_id': cls.receivable_account_1.id}),
                (0, 0, {'debit': 230.0,     'credit': 0.0,      'account_id': cls.liquidity_account.id}),
            ],
        })
        payment_2.action_post()

        cls._reconcile_on((invoice + payment_2).line_ids, cls.receivable_account_1)

        cls.env.user.groups_id += cls.env.ref('analytic.group_analytic_accounting')
        cls.analytic_plan_departments, cls.analytic_other_plan = cls.env['account.analytic.plan'].create([
            {'name': 'Departments Plan'},
            {'name': 'Other Plan'},
        ])

        cls.analytic_account_partner_a_1 = cls.env['account.analytic.account'].create({
            'name': 'analytic_account_partner_a_1',
            'partner_id': cls.partner_a.id,
            'plan_id': cls.analytic_plan_departments.id,
        })

    def test_general_ledger_cash_basis(self):
        # Check the cash basis option.
        self.env['res.currency'].search([('name', '!=', 'USD')]).with_context(force_deactivate=True).active = False
        report = self.env.ref('account_reports.general_ledger_report')
        options = self._generate_options(report, fields.Date.from_string('2016-01-01'), fields.Date.from_string('2016-12-31'))
        options['report_cash_basis'] = True

        lines = report._get_lines(options)
        self.assertLinesValues(
            lines,
            #   Name                            Debit       Credit      Balance
            [   0,                              4,          5,          6],
            [
                # Accounts.
                ('101401 Bank',                 460.0,      0.0,    460.0),
                ('121000 Account Receivable',   460.0,      460.0,    0.0),
                ('400000 Product Sales',        0.0,        460.0, -460.0),
                # Report Total.
                ('Total',                       920.0,      920.0,    0.0),
            ],
            options,
        )

        # Mark the '101200 Account Receivable' line to be unfolded.
        line_id = lines[2]['id'] # Index 2, because there is the total line for bank in position 1
        options['unfolded_lines'] = [line_id]
        self.assertLinesValues(
            report._get_lines(options),
            # pylint: disable=C0326
            #   Name                                    Date            Debit           Credit          Balance
            [   0,                                      1,                    4,             5,             6],
            [
                # Account.
                ('101401 Bank',                         '',              460.00,          0.00,        460.00),
                ('121000 Account Receivable',           '',              460.00,        460.00,          0.00),
                # Account Move Lines.from unfolded account
                ('BNK1/2016/00001',                     '02/01/2016',      0.00,        230.00,       -230.00),
                ('MISC/2016/01/0001',                   '02/01/2016',     69.00,          0.00,       -161.00),
                ('MISC/2016/01/0001',                   '02/01/2016',    161.00,          0.00,          0.00),
                ('BNK1/2016/00002',                     '03/01/2016',      0.00,        230.00,       -230.00),
                ('MISC/2016/01/0001',                   '03/01/2016',     69.00,          0.00,       -161.00),
                ('MISC/2016/01/0001',                   '03/01/2016',    161.00,          0.00,          0.00),
                # Account Total.
                ('Total 121000 Account Receivable',     '',              460.00,        460.00,          0.00),
                ('400000 Product Sales',                '',                0.00,        460.00,       -460.00),
                # Report Total.
                ('Total',                               '',              920.00,        920.00,          0.00),
            ],
            options,
        )

    def test_balance_sheet_cash_basis(self):
        # Check the cash basis option.
        report = self.env.ref('account_reports.balance_sheet')
        options = self._generate_options(report, fields.Date.from_string('2016-01-01'), fields.Date.from_string('2016-12-31'))
        options['report_cash_basis'] = True

        self.assertLinesValues(
            report._get_lines(options),
            #   Name                                            Balance
            [   0,                                              1],
            [
                ('ASSETS',                                      460.0),
                ('Current Assets',                              460.0),
                ('Bank and Cash Accounts',                      460.0),
                ('Receivables',                                   0.0),
                ('Current Assets',                                0.0),
                ('Prepayments',                                   0.0),
                ('Total Current Assets',                        460.0),
                ('Plus Fixed Assets',                             0.0),
                ('Plus Non-current Assets',                       0.0),
                ('Total ASSETS',                                460.0),

                ('LIABILITIES',                                   0.0),
                ('Current Liabilities',                           0.0),
                ('Current Liabilities',                           0.0),
                ('Payables',                                      0.0),
                ('Total Current Liabilities',                     0.0),
                ('Plus Non-current Liabilities',                  0.0),
                ('Total LIABILITIES',                             0.0),

                ('EQUITY',                                      460.0),
                ('Unallocated Earnings',                        460.0),
                ('Current Year Unallocated Earnings',           460.0),
                ('Current Year Earnings',                       460.0),
                ('Current Year Allocated Earnings',               0.0),
                ('Total Current Year Unallocated Earnings',     460.0),
                ('Previous Years Unallocated Earnings',           0.0),
                ('Total Unallocated Earnings',                  460.0),
                ('Retained Earnings',                             0.0),
                ('Total EQUITY',                                460.0),

                ('LIABILITIES + EQUITY',                        460.0),
            ],
            options,
        )

    def test_cash_basis_payment_in_the_past(self):
        self.env['res.currency'].search([('name', '!=', 'USD')]).with_context(force_deactivate=True).active = False

        payment_date = fields.Date.from_string('2010-01-01')
        invoice_date = fields.Date.from_string('2011-01-01')

        invoice = self.init_invoice('out_invoice', amounts=[100.0], taxes=self.env.company.account_sale_tax_id, partner=self.partner_a, invoice_date=invoice_date, post=True)
        self.env['account.payment.register'].with_context(active_ids=invoice.ids, active_model='account.move').create({
            'payment_date': payment_date,
        })._create_payments()

        # Make a second invoice without payment; it will allow being sure the cash basis options is well used when computing the report
        # (as it will then not appear in its lines)
        self.init_invoice('out_invoice', amounts=[100.0], partner=self.partner_a, invoice_date=invoice_date, post=True)

        # Check the impact in the reports: the invoice date should be the one the invoice appears at, since it greater than the payment's
        report = self.env.ref('account_reports.general_ledger_report')

        options = self._generate_options(report, payment_date, payment_date, default_options={'report_cash_basis': True})

        self.assertLinesValues(
            # pylint: disable=C0326
            report._get_lines(options),
            #   Name                                     Debit           Credit          Balance
            [   0,                                       4,              5,              6],
            [
                # Accounts.
                ('101403 Outstanding Receipts',        115,              0,            115),
                ('121000 Account Receivable',            0,            115,           -115),
                # Report Total.
                ('Total',                              115,            115,             0),
            ],
            options,
        )

        options = self._generate_options(report, invoice_date, invoice_date, default_options={'report_cash_basis': True})

        self.assertLinesValues(
            # pylint: disable=C0326
            report._get_lines(options),
            #   Name                                     Debit           Credit          Balance
            [   0,                                       4,              5,              6],
            [
                # Accounts.
                ('101403 Outstanding Receipts',        115,              0,            115),
                ('121000 Account Receivable',          115,            115,              0),
                ('251000 Tax Received',                  0,             15,            -15),
                ('400000 Product Sales',                 0,            100,           -100),
                # Report Total.
                ('Total',                              230,            230,             0),
            ],
            options,
        )

    def test_cash_basis_ar_ap_both_in_debit_and_credit(self):
        other_revenue = self.revenue_account_1.copy(default={'name': 'Other Income', 'code': '499000'})

        moves = self.env['account.move'].create([{
            'move_type': 'entry',
            'date': '2000-01-01',
            'journal_id': self.company_data['default_journal_misc'].id,
            'line_ids': [
                Command.create({'name': '1',   'debit': 350.0,   'credit': 0.0,     'account_id': self.receivable_account_1.id}),
                Command.create({'name': '2',   'debit': 0.0,     'credit': 150.0,   'account_id': self.receivable_account_1.id}),
                Command.create({'name': '3',   'debit': 0.0,     'credit': 200.0,   'account_id': self.revenue_account_1.id}),
            ],
        }, {
            'move_type': 'entry',
            'date': '2001-01-01',
            'journal_id': self.company_data['default_journal_misc'].id,
            'line_ids': [
                Command.create({'name': '4',   'debit': 350.0,   'credit': 0.0,     'account_id': self.liquidity_account.id}),
                Command.create({'name': '5',   'debit': 0.0,     'credit': 350.0,   'account_id': self.receivable_account_1.id}),
            ],
        }, {
            'move_type': 'entry',
            'date': '2002-01-01',
            'journal_id': self.company_data['default_journal_misc'].id,
            'line_ids': [
                Command.create({'name': '6',   'debit': 150.0,   'credit': 0.0,     'account_id': self.receivable_account_1.id}),
                Command.create({'name': '7',   'debit': 0.0,     'credit': 150.0,   'account_id': other_revenue.id}),
            ],
        }])
        moves.action_post()

        ar1 = moves.line_ids.filtered(lambda x: x.name == '1')
        ar2 = moves.line_ids.filtered(lambda x: x.name == '2')
        ar5 = moves.line_ids.filtered(lambda x: x.name == '5')
        ar6 = moves.line_ids.filtered(lambda x: x.name == '6')

        (ar1 | ar5).reconcile()
        (ar2 | ar6).reconcile()

        # Check the impact in the reports: the invoice date should be the one the invoice appears at, since it greater than the payment's
        report = self.env.ref('account_reports.general_ledger_report')

        options = self._generate_options(report, fields.Date.to_date('2000-01-01'), fields.Date.to_date('2000-01-01'))
        options['report_cash_basis'] = True

        self.assertLinesValues(
            report._get_lines(options),
            #   Name                                     Debit           Credit          Balance
            [   0,                                       5,              6,              7],
            [
                # Accounts.
                # There should be no lines in this report.

                # Report Total.
                ('Total',                                0,              0,              0),
            ],
            options,
        )

        # Delete the temporary cash basis table manually in order to run another _get_lines in the same transaction
        self.env.cr.execute("DROP TABLE cash_basis_temp_account_move_line")

        options = self._generate_options(report, fields.Date.to_date('2001-01-01'), fields.Date.to_date('2001-01-01'))
        options['report_cash_basis'] = True

        self.assertLinesValues(
            report._get_lines(options),
            #   Name                                     Debit           Credit          Balance
            [   0,                                       5,              6,              7],
            [
                # Accounts.
                ('101401 Bank',                        350,              0,            350),
                ('121000 Account Receivable',          245,            455,           -210),
                ('400000 Product Sales',                 0,            140,           -140),
                # Report Total.
                ('Total',                              595,            595,              0),
            ],
            options,
        )

        # Delete the temporary cash basis table manually in order to run another _get_lines in the same transaction
        self.env.cr.execute("DROP TABLE cash_basis_temp_account_move_line")

        options = self._generate_options(report, fields.Date.to_date('2002-01-01'), fields.Date.to_date('2002-01-01'))
        options['report_cash_basis'] = True

        self.assertLinesValues(
            report._get_lines(options),
            #   Name                                     Debit           Credit          Balance
            [   0,                                       5,              6,              7],
            [
                # Accounts.
                ('101401 Bank',                        350,              0,            350),
                ('121000 Account Receivable',          500,            500,              0),
                ('400000 Product Sales',                 0,             60,            -60),
                ('499000 Other Income',                  0,            150,           -150),
                ('999999 Undistributed Profits/Losses',  0,            140,           -140),
                # Report Total.
                ('Total',                              850,            850,              0),
            ],
            options,
        )
        # Delete the temporary cash basis table manually in order to run another _get_lines in the same transaction
        self.env.cr.execute("DROP TABLE cash_basis_temp_account_move_line")

        options = self._generate_options(report, fields.Date.to_date('2000-01-01'), fields.Date.to_date('2002-12-31'))
        options['report_cash_basis'] = True

        self.assertLinesValues(
            report._get_lines(options),
            #   Name                                     Debit           Credit          Balance
            [   0,                                       5,              6,              7],
            [
                # Accounts.
                ('101401 Bank',                        350,              0,            350),
                ('121000 Account Receivable',          500,            500,              0),
                ('400000 Product Sales',                 0,            200,           -200),
                ('499000 Other Income',                  0,            150,           -150),
                # Report Total.
                ('Total',                              850,            850,              0),
            ],
            options,
        )

    def test_cash_basis_general_ledger_load_more_lines(self):
        invoice_date = fields.Date.from_string('2023-01-01')
        invoice = self.init_invoice('out_invoice', amounts=[3000.0], taxes=[], partner=self.partner_a, invoice_date=invoice_date, post=True)
        for _ in range(3):
            self.env['account.payment.register'].with_context(active_ids=invoice.ids, active_model='account.move')\
                .create({'payment_date': invoice_date, 'amount': 1000})._create_payments()
        report = self.env.ref('account_reports.general_ledger_report')
        report.load_more_limit = 2
        options = self._generate_options(report, invoice_date, invoice_date)
        options['report_cash_basis'] = True
        lines = report._get_lines(options)
        lines_to_unfold_id = lines[5]['id'] # Mark the '101200 Account Receivable' line to be unfolded.
        options['unfolded_lines'] = [lines_to_unfold_id]
        lines = report._get_lines(options)
        self.assertLinesValues(
            lines,
            #   Name                                    Debit       Credit     Balance
            [0, 5, 6, 7],
            [
                # Accounts.
                ('101401 Bank',                         460.0,      0,          460.0),
                ('101403 Outstanding Receipts',         3000.0,     0,          3000.0),
                ('121000 Account Receivable',           3460.0,     3460.0,     0.0),
                # Expanded line
                ('400000 Product Sales',                0,          3000.0,     -3000.0),
                ('INV/2023/00001',                      0,          2000.0,     -2000.0),  # The 2 first payments are grouped
                ('Load more...',                        '',         '',          ''),
                ('Total 400000 Product Sales',          0,          3000.0,     -3000.0),
                ('999999 Undistributed Profits/Losses', 0,          460.0,      -460.0),
                # Report Total.
                ('Total',                               6920.0,     6920.0,     0),
            ],
            options,
        )

        load_more_1 = report._expand_unfoldable_line('_report_expand_unfoldable_line_general_ledger',
              lines[5]['id'], lines[7]['groupby'], options,
              lines[7]['progress'],
              lines[7]['offset'])

        self.assertLinesValues(
            load_more_1,
            #   Name, Debit, Credit, Balance
            [0, 5, 6, 7],
            [
                ('INV/2023/00001', 0, 1000.0, -3000.0),  # The last payment is displayed on another line
            ],
            options,
        )

    # ------------------------------------------------------
    # Audit Cell of Reports with Cash Basis Filter Activated
    # ------------------------------------------------------

    def _get_line_from_xml_id(self, lines, report, xml_id):
        line_id = self.env.ref(xml_id).id
        line = next(x for x in lines if report._get_model_info_from_id(x['id']) == ('account.report.line', line_id))
        return line

    def _audit_line(self, options, report, line_xml_id):
        lines = report._get_lines(options)
        line = self._get_line_from_xml_id(lines, report, line_xml_id)
        return report.action_audit_cell(options, self._get_audit_params_from_report_line(options, self.env.ref(line_xml_id), line))

    def _create_misc_entry(self, invoice_date, debit_account_id, credit_account_id):
        new_misc = self.env['account.move'].create({
            'move_type': 'entry',
            'date': invoice_date,
            'journal_id': self.company_data['default_journal_misc'].id,
            'line_ids': [
                Command.create({'debit': 1000.0, 'credit': 0.0, 'account_id': debit_account_id}),
                Command.create({'debit': 0.0, 'credit': 1000.0, 'account_id': credit_account_id}),
            ],
        })
        new_misc.action_post()
        return new_misc

    def test_cash_basis_audit_cell_invoices(self):
        # Ensure lines from invoices are part of the audit with cash basis only when a payment in linked to the invoice
        report = self.env.ref('account_reports.profit_and_loss')
        invoice_date = '2023-07-01'
        invoice_1 = self.init_invoice('out_invoice', amounts=[1000.0], taxes=[], partner=self.partner_a, invoice_date=invoice_date, post=True)
        invoice_2 = self.init_invoice('out_invoice', amounts=[1000.0], taxes=[], partner=self.partner_a, invoice_date=invoice_date, post=True)
        moves = invoice_1 + invoice_2

        self.env['account.payment.register'].with_context(active_ids=invoice_1.ids, active_model='account.move').create(
            {'payment_date': invoice_date, 'amount': 1000}
        )._create_payments()

        options = self._generate_options(report, '2023-07-01', '2023-07-31')
        audit_domain = self._audit_line(options, report, 'account_reports.account_financial_report_income0')['domain']

        expected_move_lines = moves.line_ids.filtered(lambda l: l.account_id == self.revenue_account_1)
        self.assertEqual(moves.line_ids.search(audit_domain), expected_move_lines, "Revenue lines of both move should be returned")

        options['report_cash_basis'] = True
        audit_domain = self._audit_line(options, report, 'account_reports.account_financial_report_income0')['domain']

        expected_move_lines = invoice_1.line_ids.filtered(lambda l: l.account_id == self.revenue_account_1)
        self.assertEqual(self.env['account.move.line'].search(audit_domain), expected_move_lines,
                         "Revenue line of only paid invoice should be returned")

    def test_cash_basis_audit_cell_misc_without_receivable(self):
        # Ensure lines from misc entries without receivable are always part of the audit with cash basis
        report = self.env.ref('account_reports.profit_and_loss')
        misc_without_receivable = self._create_misc_entry('2023-07-01', self.company_data['default_account_expense'].id, self.revenue_account_1.id)
        options = self._generate_options(report, '2023-07-01', '2023-07-31', default_options={'report_cash_basis': True})
        audit_domain = self._audit_line(options, report, 'account_reports.account_financial_report_income0')['domain']
        expected_move_lines = misc_without_receivable.line_ids.filtered(lambda l: l.account_id == self.revenue_account_1)
        self.assertEqual(self.env['account.move.line'].search(audit_domain), expected_move_lines,
                         "Misc entry lines should be returned, as the move has no receivable or payable line")

    def test_cash_basis_audit_cell_bank_statement(self):
        # Ensure lines from move on bank journal are displayed when auditing the balance sheet with cash basis
        report = self.env.ref('account_reports.balance_sheet')
        bank_entry = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2023-01-23',
            'journal_id': self.company_data['default_journal_bank'].id,
            'line_ids': [
                Command.create({
                    'name': 'Liability payable line',
                    'debit': 0.0,
                    'credit': 10.0,
                    'currency_id': self.currency_data['currency'].id,
                    'amount_currency': -30.0,
                    'account_id': self.company_data['default_account_payable'].id,
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
        options = self._generate_options(report, '2023-07-01', '2023-07-31', default_options={'report_cash_basis': True})
        audit_domain = self._audit_line(options, report, 'account_reports.account_financial_report_bank_view0')['domain']
        asset_cash_line = bank_entry.line_ids.filtered(lambda l: l.account_type == 'asset_cash')
        self.assertTrue(asset_cash_line in self.env['account.move.line'].search(audit_domain),
                        "Bank entry lines should be present in the audit with cash basis")

    def test_cash_basis_audit_cell_misc_with_receivable(self):
        # Ensure lines from misc entries with receivable are part of the audit with cash basis only when a payment in linked to the misc
        report = self.env.ref('account_reports.profit_and_loss')
        invoice_date = '2023-07-01'
        misc_with_receivable = self._create_misc_entry(invoice_date, self.receivable_account_1.id, self.revenue_account_1.id)
        self._create_misc_entry(invoice_date, self.receivable_account_1.id, self.revenue_account_1.id)

        options = self._generate_options(report, '2023-07-01', '2023-07-31', default_options={'report_cash_basis': True})
        audit_domain = self._audit_line(options, report, 'account_reports.account_financial_report_income0')['domain']
        self.assertEqual(self.env['account.move.line'].search(audit_domain), self.env['account.move.line'],
                         "No line should be returned, as the misc entry has a receivable line that is not reconciled")

        payment = self.env['account.move'].create({
            'move_type': 'entry',
            'date': invoice_date,
            'journal_id': self.liquidity_journal_1.id,
            'line_ids': [
                Command.create({'debit': 0.0,       'credit': 1000.0,   'account_id': self.receivable_account_1.id}),
                Command.create({'debit': 1000.0,    'credit': 0.0,      'account_id': self.liquidity_account.id}),
            ],
        })
        payment.action_post()
        self._reconcile_on((misc_with_receivable + payment).line_ids, self.receivable_account_1)

        expected_move_lines = misc_with_receivable.line_ids.filtered(lambda l: l.account_id == self.revenue_account_1)
        self.assertEqual(self.env['account.move.line'].search(audit_domain), expected_move_lines,
                         "The revenue line of the misc entry should be returned, as the misc entry has a receivable line that is reconciled")

    def test_cash_basis_audit_cell_reconcilable_tax_account(self):
        """ Ensure that when a tax account is reconcilable, and the tax line of an invoice is reconciled, then the
        lines of the invoice are not displayed in the audit of the accounting report with cash basis activated.
        Moves that contain receivable or payable lines are displayed in the audit only if the
        partial is specifically reconciled with the receivable or payable line.
        """
        report = self.env.ref('account_reports.profit_and_loss')
        invoice_date = '2023-07-01'
        tax_account = self.tax_sale_a.invoice_repartition_line_ids.account_id
        tax_account.reconcile = True

        misc = self._create_misc_entry('2023-07-01', tax_account.id, self.revenue_account_1.id)
        invoice = self.init_invoice('out_invoice', amounts=[1000.0], taxes=[self.tax_sale_a], partner=self.partner_a, invoice_date=invoice_date, post=True)
        self._reconcile_on((misc + invoice).line_ids, tax_account)

        options = self._generate_options(report, '2023-07-01', '2023-07-31', default_options={'report_cash_basis': True})
        audit_domain = self._audit_line(options, report, 'account_reports.account_financial_report_income0')['domain']

        expected_move_lines = misc.line_ids.filtered(lambda l: l.account_id == self.revenue_account_1)
        self.assertEqual(self.env['account.move.line'].search(audit_domain), expected_move_lines)
        self.assertEqual(self.env['account.move.line'].search(audit_domain), expected_move_lines,
                         "Only the misc revenue line should be returned, not the invoice one")

    def test_analytic_cash_basis_with_analytic_line_on_invoice(self):
        """
            Tests that the additional column generated by the analytic groupby contains values corresponding to
            the proportion of the amount paid on the invoice with the analytic amount
        """
        # Second entry, but with an analytic distribution on the revenue line
        entry = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2016-01-01',
            'journal_id': self.company_data['default_journal_misc'].id,
            'line_ids': [
                Command.create({'debit': 345.0, 'credit': 0.0, 'account_id': self.receivable_account_1.id}),
                Command.create({'debit': 805.0, 'credit': 0.0, 'account_id': self.receivable_account_1.id}),
                Command.create({'debit': 0.0, 'credit': 1150.0, 'account_id': self.revenue_account_1.id,
                                'analytic_distribution': {self.analytic_account_partner_a_1.id: 100}}),
            ],
        })
        entry.action_post()

        # Payment (20% of the invoice).

        payment_1 = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2016-02-01',
            'journal_id': self.liquidity_journal_1.id,
            'line_ids': [
                Command.create({'debit': 0.0, 'credit': 230.0, 'account_id': self.receivable_account_1.id}),
                Command.create({'debit': 230.0, 'credit': 0.0, 'account_id': self.liquidity_account.id}),
            ],
        })
        payment_1.action_post()

        self._reconcile_on((entry + payment_1).line_ids, self.receivable_account_1)

        # Check the cash basis option with analytic groupby on accounts.
        report = self.env.ref('account_reports.balance_sheet')
        options = self._generate_options(
            report,
            fields.Date.to_date('2016-01-01'),
            fields.Date.to_date('2016-12-31'),
            default_options={
                'analytic_accounts_groupby': [self.analytic_account_partner_a_1.id],
                'report_cash_basis': True,
            }
        )

        self.assertLinesValues(
            report._get_lines(options),
            [0, 1, 2],
            [
                ('ASSETS', 0, 690.0,),
                ('Current Assets', 0, 690.0),
                ('Bank and Cash Accounts', 0, 690.0),
                ('Receivables', 0, 0),
                ('Current Assets', 0, 0),
                ('Prepayments', 0, 0),
                ('Total Current Assets', 0, 690.0),
                ('Plus Fixed Assets', 0, 0),
                ('Plus Non-current Assets', 0, 0),
                ('Total ASSETS', 0, 690.0),

                ('LIABILITIES', 0, 0),
                ('Current Liabilities', 0, 0),
                ('Current Liabilities', 0, 0),
                ('Payables', 0, 0),
                ('Total Current Liabilities', 0, 0),
                ('Plus Non-current Liabilities', 0, 0),
                ('Total LIABILITIES', 0, 0),

                ('EQUITY', 230.0, 690.0),
                ('Unallocated Earnings', 230.0, 690.0),
                ('Current Year Unallocated Earnings', 230.0, 690.0),
                ('Current Year Earnings', 230.0, 690.0),
                ('Current Year Allocated Earnings', 0, 0),
                ('Total Current Year Unallocated Earnings', 230.0, 690.0),
                ('Previous Years Unallocated Earnings', 0, 0),
                ('Total Unallocated Earnings', 230.0, 690.0),
                ('Retained Earnings', 0, 0),
                ('Total EQUITY', 230.0, 690.0),

                ('LIABILITIES + EQUITY', 230.0, 690.0),
            ],
            options,
        )

    def test_analytic_cash_basis_analytic_line_on_payment(self):
        """
            Tests that the additional column generated by the analytic groupby contains values corresponding to
            the amount of the analytic line linked to a payment
        """
        # Second invoice, but with an analytic distribution on the revenue line
        invoice = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2016-01-01',
            'journal_id': self.company_data['default_journal_misc'].id,
            'line_ids': [
                Command.create({'debit': 345.0, 'credit': 0.0, 'account_id': self.receivable_account_1.id}),
                Command.create({'debit': 805.0, 'credit': 0.0, 'account_id': self.receivable_account_1.id}),
                Command.create({'debit': 0.0, 'credit': 1150.0, 'account_id': self.revenue_account_1.id}),
            ],
        })
        invoice.action_post()

        # Payment (20% of the invoice).

        payment_1 = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2016-02-01',
            'journal_id': self.liquidity_journal_1.id,
            'line_ids': [
                Command.create({'debit': 0.0, 'credit': 230.0, 'account_id': self.receivable_account_1.id}),
                Command.create({'debit': 230.0, 'credit': 0.0, 'account_id': self.liquidity_account.id}),
            ],
        })
        payment_1.action_post()

        self._reconcile_on((invoice + payment_1).line_ids, self.receivable_account_1)

        # Check the cash basis option with analytic groupby on accounts.
        report = self.env.ref('account_reports.balance_sheet')
        options = self._generate_options(
            report,
            fields.Date.to_date('2016-01-01'),
            fields.Date.to_date('2016-12-31'),
            default_options={
                'analytic_accounts_groupby': [self.analytic_account_partner_a_1.id],
                'report_cash_basis': True,
            }
        )

        # Checks that analytic line on a bank/cash account is reported on the report

        self.env['account.analytic.line'].create({
            'name': 'company specific account',
            'account_id': self.analytic_account_partner_a_1.id,
            'move_line_id': payment_1.line_ids[1].id,
            'amount': 100,
            'date': '2016-01-01'
        })

        self.assertLinesValues(
            report._get_lines(options),
            [0, 1, 2],
            [
                ('ASSETS', -100.0, 690.0,),
                ('Current Assets', -100.0, 690.0),
                ('Bank and Cash Accounts', -100.0, 690.0),
                ('Receivables', 0, 0),
                ('Current Assets', 0, 0),
                ('Prepayments', 0, 0),
                ('Total Current Assets', -100.0, 690.0),
                ('Plus Fixed Assets', 0, 0),
                ('Plus Non-current Assets', 0, 0),
                ('Total ASSETS', -100.0, 690.0),

                ('LIABILITIES', 0, 0),
                ('Current Liabilities', 0, 0),
                ('Current Liabilities', 0, 0),
                ('Payables', 0, 0),
                ('Total Current Liabilities', 0, 0),
                ('Plus Non-current Liabilities', 0, 0),
                ('Total LIABILITIES', 0, 0),

                ('EQUITY', 0, 690.0),
                ('Unallocated Earnings', 0, 690.0),
                ('Current Year Unallocated Earnings', 0, 690.0),
                ('Current Year Earnings', 0, 690.0),
                ('Current Year Allocated Earnings', 0, 0),
                ('Total Current Year Unallocated Earnings', 0, 690.0),
                ('Previous Years Unallocated Earnings', 0, 0),
                ('Total Unallocated Earnings', 0, 690.0),
                ('Retained Earnings', 0, 0),
                ('Total EQUITY', 0, 690.0),

                ('LIABILITIES + EQUITY', 0, 690.0),
            ],
            options,
        )

    def test_analytic_cash_basis_analytic_line_linked_to_credit_note(self):
        """
            Tests that the additional column generated by the analytic groupby contains values corresponding to
            the amount of the analytic line linked to a credit note reconciled with an invoice
        """
        # Second invoice, but with an analytic distribution on the revenue line
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2016-01-01',
            'date': '2016-01-01',
            'company_id': self.company_data['company'].id,
            'invoice_line_ids': [Command.create({
                'quantity': 1,
                'price_unit': 1000,
                'tax_ids': [],
            })]
        })
        invoice.action_post()

        reversal = self.env['account.move.reversal'].with_context(
            active_model='account.move', active_ids=invoice.ids).create({
            'reason': 'Test Partial Refund',
            'date': '2016-01-01',
            'journal_id': invoice.journal_id.id,
        })

        res = reversal.reverse_moves()
        reversal_move = self.env['account.move'].browse(res['res_id'])
        reversal_move.invoice_line_ids.price_unit = 500
        reversal_move.invoice_line_ids.analytic_distribution = {self.analytic_account_partner_a_1.id: 100}

        reversal_move.action_post()

        # Check the cash basis option with analytic groupby on accounts.
        report = self.env.ref('account_reports.balance_sheet')
        options = self._generate_options(
            report,
            fields.Date.to_date('2016-01-01'),
            fields.Date.to_date('2016-12-31'),
            default_options={
                'analytic_accounts_groupby': [self.analytic_account_partner_a_1.id],
                'report_cash_basis': True,
            }
        )

        self.assertLinesValues(
            report._get_lines(options),
            [0, 1, 2],
            [
                ('ASSETS', 0, 460.0,),
                ('Current Assets', 0, 460.0),
                ('Bank and Cash Accounts', 0, 460.0),
                ('Receivables', 0, 0),
                ('Current Assets', 0, 0),
                ('Prepayments', 0, 0),
                ('Total Current Assets', 0, 460.0),
                ('Plus Fixed Assets', 0, 0),
                ('Plus Non-current Assets', 0, 0),
                ('Total ASSETS', 0, 460.0),

                ('LIABILITIES', 0, 0),
                ('Current Liabilities', 0, 0),
                ('Current Liabilities', 0, 0),
                ('Payables', 0, 0),
                ('Total Current Liabilities', 0, 0),
                ('Plus Non-current Liabilities', 0, 0),
                ('Total LIABILITIES', 0, 0),

                ('EQUITY', -500.0, 460.0),
                ('Unallocated Earnings', -500.0, 460.0),
                ('Current Year Unallocated Earnings', -500.0, 460.0),
                ('Current Year Earnings', -500.0, 460.0),
                ('Current Year Allocated Earnings', 0, 0),
                ('Total Current Year Unallocated Earnings', -500.0, 460.0),
                ('Previous Years Unallocated Earnings', 0, 0),
                ('Total Unallocated Earnings', -500.0, 460.0),
                ('Retained Earnings', 0, 0),
                ('Total EQUITY', -500.0, 460.0),

                ('LIABILITIES + EQUITY', -500.0, 460.0),
            ],
            options,
        )

    def assert_line_values(self, report, date, list_values, analytic=True, cash_basis=True):
        additional_options = {}
        if cash_basis:
            additional_options['report_cash_basis'] = True
        if analytic:
            additional_options['analytic_accounts_groupby'] = [self.analytic_account_partner_a_1.id, self.second_account.id, self.third_account.id]
        options = self._generate_options(
            report,
            fields.Date.to_date('2016-02-01'),
            fields.Date.to_date(date),
            default_options=additional_options
        )

        # Check result of line Current Year Earnings of the report
        self.assertLinesValues(
            report._get_lines(options)[22:23],
            list(range(len(list_values) + 1)),
            [('Current Year Earnings', *list_values)],
            options,
        )

    def test_analytic_cash_basis_analytic_global(self):
        self.second_account, self.third_account = self.env['account.analytic.account'].create([
            {
                'name': 'second account',
                'plan_id': self.analytic_plan_departments.id,
            },
            {
                'name': 'third account',
                'plan_id': self.analytic_other_plan.id,
            },
        ])

        # Invoices, with different distributions on their revenue line
        invoice_1, invoice_2, _invoice_3, invoice_4 = invoices = self.env['account.move'].create([
            {
                'move_type': 'out_invoice',
                'partner_id': self.partner_a.id,
                'invoice_date': '2016-02-01',
                'date': '2016-02-01',
                'company_id': self.company_data['company'].id,
                'invoice_line_ids': [Command.create({
                    'quantity': 1,
                    'price_unit': 1000,
                    'analytic_distribution': {self.second_account.id: 100, self.third_account.id: 50},
                    'tax_ids': [],
                })]
            },
            {
                'move_type': 'out_invoice',
                'partner_id': self.partner_a.id,
                'invoice_date': '2016-02-15',
                'date': '2016-02-15',
                'company_id': self.company_data['company'].id,
                'invoice_line_ids': [Command.create({
                    'quantity': 1,
                    'price_unit': 1000,
                    'analytic_distribution': {self.second_account.id: 80},
                    'tax_ids': [],
                })]
            },
            {
                'move_type': 'out_invoice',
                'partner_id': self.partner_a.id,
                'invoice_date': '2016-02-25',
                'date': '2016-02-25',
                'company_id': self.company_data['company'].id,
                'invoice_line_ids': [Command.create({
                    'quantity': 1,
                    'price_unit': 1000,
                    'analytic_distribution': {self.third_account.id: 60},
                    'tax_ids': [],
                })]
            },
            {
                'move_type': 'out_invoice',
                'partner_id': self.partner_a.id,
                'invoice_date': '2016-03-01',
                'date': '2016-03-01',
                'company_id': self.company_data['company'].id,
                'invoice_line_ids': [Command.create({
                    'quantity': 1,
                    'price_unit': 1000,
                    'analytic_distribution': {f'{self.second_account.id},{self.third_account.id}': 10},
                    'tax_ids': [],
                })]
            },
        ])
        invoices.action_post()

        payment_invoice_1, payment_invoice_2, second_payment_invoice_2, payment_invoice_4 = self.env['account.move'].create([
            {
                'move_type': 'entry',
                'date': '2016-02-10',
                'journal_id': self.liquidity_journal_1.id,
                'line_ids': [
                    Command.create({'debit': 0.0, 'credit': 200.0, 'account_id': self.receivable_account_1.id}),
                    Command.create({'debit': 200.0, 'credit': 0.0, 'account_id': self.liquidity_account.id}),
                ],
            },
            {
                'move_type': 'entry',
                'date': '2016-02-20',
                'journal_id': self.liquidity_journal_1.id,
                'line_ids': [
                    Command.create({'debit': 0.0, 'credit': 300.0, 'account_id': self.receivable_account_1.id}),
                    Command.create({'debit': 300.0, 'credit': 0.0, 'account_id': self.liquidity_account.id}),
                ],
            },
            {
                'move_type': 'entry',
                'date': '2016-02-29',
                'journal_id': self.liquidity_journal_1.id,
                'line_ids': [
                    Command.create({'debit': 0.0, 'credit': 200.0, 'account_id': self.receivable_account_1.id}),
                    Command.create({'debit': 200.0, 'credit': 0.0, 'account_id': self.liquidity_account.id}),
                ],
            },
            {
                'move_type': 'entry',
                'date': '2016-03-10',
                'journal_id': self.liquidity_journal_1.id,
                'line_ids': [
                    Command.create({'debit': 0.0, 'credit': 200.0, 'account_id': self.receivable_account_1.id}),
                    Command.create({'debit': 200.0, 'credit': 0.0, 'account_id': self.liquidity_account.id}),
                ],
            },
        ])
        (payment_invoice_1 + payment_invoice_2 + second_payment_invoice_2 + payment_invoice_4).action_post()
        self._reconcile_on((invoice_1 + payment_invoice_1).line_ids, self.receivable_account_1)
        self._reconcile_on((invoice_2 + payment_invoice_2).line_ids, self.receivable_account_1)
        self._reconcile_on((invoice_2 + second_payment_invoice_2).line_ids, self.receivable_account_1)
        self._reconcile_on((invoice_4 + payment_invoice_4).line_ids, self.receivable_account_1)

        report = self.env.ref('account_reports.balance_sheet')

        # 4 invoices of 1000 and 1 invoices of 1150, without special filters
        self.assert_line_values(report, '2016-03-01', [5150], cash_basis=False, analytic=False)

        # ANALYTICS WITHOUT CABA
        self.assert_line_values(report, '2016-03-01', [0, 1900.0, 1200.0, 5150], cash_basis=False, analytic=True)

        # CABA WITHOUT ANALYTICS

        # only first 2 invoices, first invoice payment
        self.assert_line_values(report, '2016-02-01', [230.0], cash_basis=True, analytic=False)

        # only first 2 invoices, both partially paid
        self.assert_line_values(report, '2016-02-10', [430.0], cash_basis=True, analytic=False)

        # only first 3 invoices, first 2 partially paid
        self.assert_line_values(report, '2016-02-15', [430.0], cash_basis=True, analytic=False)

        # only first 3 invoices, all partially paid
        self.assert_line_values(report, '2016-02-20', [730.0], cash_basis=True, analytic=False)

        # only first 4 invoices, first 3 partially paid
        self.assert_line_values(report, '2016-02-25', [730.0], cash_basis=True, analytic=False)

        # only first 4 invoices, first 3 partially paid (2 payments on invoice_2)
        self.assert_line_values(report, '2016-02-29', [930.0], cash_basis=True, analytic=False)

        # All 5 invoices, first 3 partially paid (2 payments on invoice_1 and invoice_2)
        self.assert_line_values(report, '2016-03-01', [1160.0], cash_basis=True, analytic=False)

        # All 5 invoices, first 3 and last partially paid (2 payments on invoice_1 and invoice_2)
        self.assert_line_values(report, '2016-03-10', [1360.0], cash_basis=True, analytic=False)

        # WITH ANALYTICS AND CABA

        # only first 2 invoices, first invoice payment, no analytic
        self.assert_line_values(report, '2016-02-01', [0, 0, 0, 230.0], cash_basis=True, analytic=True)

        # only first 2 invoices, both paid, analytic on invoice_1 (with proportion of payment)
        self.assert_line_values(report, '2016-02-10', [0, 200, 100, 430.0], cash_basis=True, analytic=True)

        # only first 3 invoices, first 2 paid, analytic on invoice_1
        self.assert_line_values(report, '2016-02-15', [0, 200, 100, 430.0], cash_basis=True, analytic=True)

        # only first 3 invoices, all paid, analytic on invoice_1 and invoice_2
        self.assert_line_values(report, '2016-02-20', [0, 440, 100, 730.0], cash_basis=True, analytic=True)

        # only first 4 invoices, first 3 paid, analytic on invoice_1 and invoice_2
        self.assert_line_values(report, '2016-02-25', [0, 440, 100, 730.0], cash_basis=True, analytic=True)

        # only first 4 invoices, first 3 partially paid (2 payments on invoice_2)
        self.assert_line_values(report, '2016-02-29', [0, 600, 100, 930.0], cash_basis=True, analytic=True)

        # All 5 invoices, first 3 partially paid (2 payments on invoice_2)
        self.assert_line_values(report, '2016-03-01', [0, 600, 100, 1160.0], cash_basis=True, analytic=True)

        # All 5 invoices, first 3 and last partially paid (2 payments on invoice_2)
        self.assert_line_values(report, '2016-03-10', [0, 620, 120, 1360.0], cash_basis=True, analytic=True)
