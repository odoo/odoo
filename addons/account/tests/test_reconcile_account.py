# Copyright 2020 Camptocamp SA
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl)
from odoo.addons.account.tests.test_reconciliation import TestReconciliation
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestReconcileAccount(TestReconciliation):

    def setUp(self):
        super().setUp()
        company = self.env.ref('base.main_company')
        self.reconciliation_widget = self.env['account.reconciliation.widget']
        self.bank_journal_assets_account = self.env['account.account'].create(
            {
                'name': '1093',
                'code': '1093',
                'user_type_id': self.env.ref(
                    'account.data_account_type_current_assets'
                ).id,
                'company_id': company.id,
            }
        )
        self.bank_journal_euro.write(
            {
                'default_credit_account_id': self.bank_journal_assets_account.id,
                'default_debit_account_id': self.bank_journal_assets_account.id,
            }
        )

    def test_account_reconcile_flag(self):
        # Create invoice
        invoice = self.create_invoice(
            type='out_invoice',
            invoice_amount=100,
            currency_id=self.currency_euro_id,
        )
        # Create move 1093 (debit) to 1100 (receivable) (credit)
        move = self.env['account.move'].create(
            {
                'journal_id': self.bank_journal_euro.id,
                'line_ids': [(0, 0, {
                    'account_id': self.account_rcv.id,
                    'credit': invoice.amount_total,
                    'partner_id': invoice.partner_id.id,
                    'name': invoice.name,
                }), (0, 0, {
                    'account_id': self.bank_journal_assets_account.id,
                    'debit': invoice.amount_total,
                    'partner_id': invoice.partner_id.id,
                    'name': '123456789',
                })]
            }
        )
        move.post()
        # Reconcile
        invoice_rec_line = invoice.line_ids.filtered(
            lambda l: l.account_id == self.account_rcv
        )
        move_rec_line = move.line_ids.filtered(
            lambda l: l.account_id == self.account_rcv
        )
        to_reconcile = invoice_rec_line | move_rec_line
        to_reconcile.auto_reconcile_lines()
        # Create bank statement + bank statement line
        bank_stmt = self.acc_bank_stmt_model.create({
            'journal_id': self.bank_journal_euro.id,
            'name': 'test'
        })
        bank_stmt_line = self.acc_bank_stmt_line_model.create(
            {
                'name': '123456789',
                'statement_id': bank_stmt.id,
                'partner_id': invoice.partner_id.id,
                'amount': invoice.amount_total,
            }
        )
        move_bank_line = move.line_ids.filtered(
            lambda l: l.account_id == self.bank_journal_assets_account
        )

        # If reconcile is set on the account, we must have the proposition on
        #  move_bank_line
        self.bank_journal_assets_account.reconcile = True
        # Call reconciliation widget
        propositions_lines = \
        self.reconciliation_widget.get_bank_statement_line_data(
            bank_stmt_line.ids
        )['lines']
        # Ensure the proposition matches move_bank_line
        move_bank_prop = \
        propositions_lines[0].get('reconciliation_proposition')[0]
        read_move_bank_line = move_bank_line.read()[0]
        self.assertEqual(move_bank_prop.get('id'),
                         read_move_bank_line.get('id'))
        self.assertEqual(move_bank_prop.get('account_id'),
                         list(read_move_bank_line.get('account_id')))
        self.assertEqual(move_bank_prop.get('journal_id'),
                         list(read_move_bank_line.get('journal_id')))
        self.assertEqual(move_bank_prop.get('partner_id'),
                         read_move_bank_line.get('partner_id')[0])

        # If reconcile is NOT set on the account, we must NOT have the
        #  proposition on move_bank_line
        self.bank_journal_assets_account.reconcile = False
        # Call reconciliation widget
        propositions_lines = self.reconciliation_widget.get_bank_statement_line_data(
            bank_stmt_line.ids
        )['lines']
        # The line on 1093 should not appear
        self.assertFalse(propositions_lines[0].get('reconciliation_proposition'))
