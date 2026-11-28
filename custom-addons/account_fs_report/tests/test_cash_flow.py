# -*- coding: utf-8 -*-
from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestCashFlowStatement(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.report = cls.env['fs.report'].search([('code', '=', 'CFS')], limit=1)
        cls.bank_journal = cls.company_data['default_journal_bank']
        cls.cash_account = cls.bank_journal.default_account_id
        cls.receivable = cls.company_data['default_account_receivable']
        cls.revenue = cls.company_data['default_account_revenue']
        cls.expense = cls.company_data['default_account_expense']
        operating = cls.env.ref('account.account_tag_operating')
        (cls.revenue | cls.expense).write({'tag_ids': [Command.link(operating.id)]})
        # Point payment method outstanding at the bank liquidity account so Direct CF
        # sees payments the same way as bank journal entries (Enterprise liquidity set).
        for line in (
                cls.bank_journal.inbound_payment_method_line_ids
                | cls.bank_journal.outbound_payment_method_line_ids
        ):
            line.payment_account_id = cls.cash_account

    def _options(self, date_from, date_to, **extra):
        opts = {
            'company_ids': self.env.company.ids,
            'target_move': 'posted',
            'journal_ids': [],
            'unfold_all': False,
            'report_type': 'cash_flow',
            'date': {
                'string': date_to,
                'date_from': date_from,
                'date_to': date_to,
                'period_type': 'custom',
            },
            'columns': [{
                'label': date_to,
                'date_from': date_from,
                'date_to': date_to,
            }],
        }
        opts.update(extra)
        return opts

    def _amounts(self, options):
        data = self.env['fs.report.engine'].get_report_data(self.report.id, options)
        return {row['code']: row['columns'][0] for row in data['lines']}, data

    def _bank_entry(self, amount, date, post=True):
        """Liquidity journal entry on the bank account (debit = cash in)."""
        move = self.env['account.move'].create({
            'move_type': 'entry',
            'date': date,
            'journal_id': self.bank_journal.id,
            'line_ids': [
                Command.create({
                    'account_id': self.cash_account.id,
                    'debit': amount if amount > 0 else 0.0,
                    'credit': -amount if amount < 0 else 0.0,
                    'name': 'CF liquidity',
                }),
                Command.create({
                    'account_id': self.revenue.id if amount > 0 else self.expense.id,
                    'debit': -amount if amount < 0 else 0.0,
                    'credit': amount if amount > 0 else 0.0,
                    'name': 'CF liquidity',
                }),
            ],
        })
        if post:
            move.action_post()
            # Ensure stored related parent_state is written before raw SQL CF queries.
            self.env.flush_all()
        return move

    def test_cash_flow_layout_codes(self):
        self.assertTrue(self.report)
        self.assertEqual(self.report.report_type, 'cash_flow')
        amounts, data = self._amounts(self._options('2026-01-01', '2026-12-31'))
        expected = {
            'opening_balance',
            'net_increase',
            'operating_activities',
            'advance_payments_customer',
            'received_operating_activities',
            'advance_payments_suppliers',
            'paid_operating_activities',
            'investing_activities',
            'investing_activities_cash_in',
            'investing_activities_cash_out',
            'financing_activities',
            'financing_activities_cash_in',
            'financing_activities_cash_out',
            'unclassified_activities',
            'unclassified_activities_cash_in',
            'unclassified_activities_cash_out',
            'closing_balance',
        }
        self.assertTrue(expected.issubset(amounts.keys()))
        self.assertFalse(any(row.get('green_on_positive') for row in data['lines']))

    def test_cash_flow_customer_payment(self):
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2026-03-01',
            'date': '2026-03-01',
            'invoice_line_ids': [Command.create({
                'name': 'Service',
                'quantity': 1,
                'price_unit': 500.0,
                'account_id': self.revenue.id,
            })],
        })
        invoice.action_post()
        payment = self.env['account.payment'].create({
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': self.partner_a.id,
            'amount': 500.0,
            'date': '2026-03-15',
            'journal_id': self.bank_journal.id,
        })
        payment.action_post()
        (invoice.line_ids + payment.move_id.line_ids).filtered(
            lambda line: line.account_id == self.receivable and not line.reconciled
        ).reconcile()

        amounts, _data = self._amounts(self._options('2026-01-01', '2026-12-31'))
        self.assertAlmostEqual(amounts['opening_balance'], 0.0, places=2)
        self.assertAlmostEqual(amounts['closing_balance'], 500.0, places=2)
        self.assertAlmostEqual(amounts['net_increase'], 500.0, places=2)
        self.assertAlmostEqual(
            amounts['closing_balance'],
            amounts['opening_balance'] + amounts['net_increase'],
            places=2,
        )

    def test_cash_flow_filter_posted_vs_all(self):
        self._bank_entry(100.0, '2026-06-01', post=False)
        posted_amounts, _ = self._amounts(self._options('2026-01-01', '2026-12-31'))
        all_amounts, _ = self._amounts(self._options(
            '2026-01-01', '2026-12-31', target_move='all',
        ))
        self.assertAlmostEqual(posted_amounts['closing_balance'], 0.0, places=2)
        self.assertAlmostEqual(all_amounts['closing_balance'], 100.0, places=2)
        self._bank_entry(100.0, '2026-06-01', post=True)
        after, _ = self._amounts(self._options('2026-01-01', '2026-12-31'))
        # Previous draft still unposted + new posted 100.
        self.assertAlmostEqual(after['closing_balance'], 100.0, places=2)

    def test_cash_flow_date_range_filters(self):
        move = self._bank_entry(250.0, '2026-06-15', post=True)
        pay_accounts = self.env['fs.cash.flow']._get_payment_account_ids({
            'company_ids': self.env.company.ids,
            'journal_ids': [],
        })
        q1, _ = self._amounts(self._options('2026-01-01', '2026-03-31'))
        q2, _ = self._amounts(self._options('2026-04-01', '2026-06-30'))
        year, _ = self._amounts(self._options('2026-01-01', '2026-12-31'))
        self.assertAlmostEqual(q1['closing_balance'], 0.0, places=2)
        self.assertAlmostEqual(q1['net_increase'], 0.0, places=2)
        self.assertAlmostEqual(q2['closing_balance'], 250.0, places=2)
        self.assertAlmostEqual(q2['net_increase'], 250.0, places=2)
        self.assertAlmostEqual(year['closing_balance'], 250.0, places=2)

        h2, _ = self._amounts(self._options('2026-07-01', '2026-12-31'))
        self.assertAlmostEqual(h2['opening_balance'], 250.0, places=2)
        self.assertAlmostEqual(h2['closing_balance'], 250.0, places=2)
        self.assertAlmostEqual(h2['net_increase'], 0.0, places=2)

    def test_cash_flow_default_unfolded_accounts(self):
        self._bank_entry(80.0, '2026-02-01', post=True)
        _amounts, data = self._amounts(self._options('2026-01-01', '2026-12-31'))
        closing = next(row for row in data['lines'] if row['code'] == 'closing_balance')
        self.assertTrue(closing['unfoldable'])
        self.assertTrue(closing.get('accounts'))
        self.assertTrue(any(
            abs(acc['columns'][0] - 80.0) < 0.01 for acc in closing['accounts']
        ))

    def test_cash_flow_payment_accounts_include_outstanding(self):
        accounts = self.env['fs.cash.flow']._get_payment_account_ids({
            'company_ids': self.env.company.ids,
            'journal_ids': [],
        })
        self.assertIn(self.cash_account.id, accounts)
