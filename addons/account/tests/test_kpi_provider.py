from odoo import Command
from odoo.tests import tagged, TransactionCase


@tagged('post_install', '-at_install')
class TestKpiProvider(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        company = cls.env.ref('base.main_company')
        cls.company_id = company.id
        cls.partner_id = cls.env['res.partner'].create({'name': 'Someone'})
        cls.income_account, _, cls.suspense_account = cls.env['account.account'].with_company(cls.company_id).create([
            {
                'name': 'Income',
                'code': '40000',
                'account_type': 'income',
            },
            {
                'name': 'Receivables',
                'code': '10000',
                'account_type': 'asset_receivable'
            },
            {
                'name': 'Suspense',
                'code': '20000',
                'account_type': 'asset_current'
            }
        ])
        company.account_journal_suspense_account_id = cls.suspense_account
        cls.env['account.journal'].with_company(cls.company_id).create([
            {
                'name': 'Sales',
                'type': 'sale',
            },
            {
                'name': 'Miscellaneous',
                'type': 'general'
            },
            {
                'name': 'Purchase',
                'type': 'purchase'
            }
        ]
        )
        # Clean things for the test
        cls.env['account.move'].search([
            '|', ('state', '=', 'draft'),
            ('statement_line_id.is_reconciled', '=', False),
        ])._unlink_or_reverse()

    def test_empty_kpi_summary(self):
        # Ensure that nothing gets reported when there is nothing to report
        self.assertCountEqual(self.env['kpi.provider'].get_account_kpi_summary(), [])

    def test_kpi_summary(self):
        base_move = {
            'company_id': self.company_id,
            'invoice_line_ids': [Command.create({'account_id': self.suspense_account.id, 'quantity': 15, 'price_unit': 10})],
            'partner_id': self.partner_id.id,
        }
        self.env['account.move'].create(
            [{**base_move, 'move_type': 'entry'}] * 2 +
            [{**base_move, 'move_type': 'out_invoice'}] * 3 +
            [{**base_move, 'move_type': 'out_refund'}] * 4 +
            [{**base_move, 'move_type': 'in_invoice'}] * 5 +
            [{**base_move, 'move_type': 'in_refund'}] * 6 +
            [{**base_move, 'move_type': 'out_receipt'}] * 7 +
            [{**base_move, 'move_type': 'in_receipt'}] * 8
        )
        self.assertCountEqual(self.env['kpi.provider'].get_account_kpi_summary(), [
            {'id': 'account_journal_type.general', 'name': 'Miscellaneous', 'type': 'integer', 'value': 2},
            {'id': 'account_journal_type.sale', 'name': 'Sales', 'type': 'integer', 'value': 3 + 4 + 7},
            {'id': 'account_journal_type.purchase', 'name': 'Purchase', 'type': 'integer', 'value': 5 + 6 + 8},
        ])

    def test_kpi_summary_shouldnt_report_posted_moves(self):
        move = self.env['account.move'].create({
            'company_id': self.company_id,
            'invoice_line_ids': [Command.create({'account_id': self.income_account.id, 'quantity': 15, 'price_unit': 10})],
            'partner_id': self.partner_id.id,
            'move_type': 'out_invoice',
        })
        self.assertCountEqual(self.env['kpi.provider'].get_account_kpi_summary(), [
            {'id': 'account_journal_type.sale', 'name': 'Sales', 'type': 'integer', 'value': 1},
        ])

        move.action_post()
        self.assertCountEqual(self.env['kpi.provider'].get_account_kpi_summary(), [])

    def test_kpi_summary_reports_posted_but_to_check_moves(self):
        move = self.env['account.move'].create({
            'company_id': self.company_id,
            'invoice_line_ids': [Command.create({'account_id': self.income_account.id, 'quantity': 15, 'price_unit': 10})],
            'partner_id': self.partner_id.id,
            'move_type': 'out_invoice',
        })
        move.action_post()
        move.checked = False
        self.assertCountEqual(self.env['kpi.provider'].get_account_kpi_summary(), [
            {'id': 'account_journal_type.sale', 'name': 'Sales', 'type': 'integer', 'value': 1},
        ])

        move.button_set_checked()
        self.assertCountEqual(self.env['kpi.provider'].get_account_kpi_summary(), [])

    def test_kpi_summary_reports_unreconciled_bank_statements(self):
        move = self.env['account.move'].create({
            'company_id': self.company_id,
            'line_ids': [Command.create({'account_id': self.income_account.id, 'quantity': 15, 'price_unit': 10})],
            'partner_id': self.env.user.partner_id.id,
            'move_type': 'out_invoice',
        })
        move.action_post()

        journal_id = self.env['account.journal'].create({
            'name': 'Bank',
            'type': 'bank',
        })
        bank_statement = self.env['account.bank.statement'].create({
            'name': 'test_statement',
            'line_ids': [Command.create({
                'date': '2025-09-15',
                'payment_ref': 'line_1',
                'journal_id': journal_id.id,
                'amount': move.amount_total,
            })],
        })

        self.assertEqual(bank_statement.line_ids.move_id.state, 'posted')
        self.assertFalse(bank_statement.line_ids.is_reconciled)
        self.assertCountEqual(self.env['kpi.provider'].get_account_kpi_summary(), [
            {'id': 'account_journal_type.bank', 'name': 'Bank', 'type': 'integer', 'value': 1},
        ])

        move_line = move.line_ids.filtered(lambda line: line.account_type == 'asset_receivable')
        _st_liquidity_lines, st_suspense_lines, _st_other_lines = bank_statement.line_ids._seek_for_lines()
        st_suspense_lines.account_id = move_line.account_id
        (move_line + st_suspense_lines).reconcile()
        self.assertTrue(bank_statement.line_ids.is_reconciled)
        self.assertCountEqual(self.env['kpi.provider'].get_account_kpi_summary(), [])
